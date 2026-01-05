import streamlit as st
import pandas as pd
import os
import re
import time
import altair as alt
import streamlit.components.v1 as components
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS (保留门户设计) ---
st.set_page_config(page_title="法规标准智慧工作站", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .header-banner {
        background: white; padding: 25px; border-bottom: 4px solid #1e40af;
        margin-bottom: 25px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .full-text-area {
        background: white; padding: 40px 60px; border-radius: 4px; line-height: 2.2;
        color: #1f2937; font-family: "SimSun", "STSong", serif; font-size: 1.1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;
    }
    .clause-card {
        background: white; padding: 25px; border-radius: 8px; border-left: 6px solid #2563eb;
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .chapter-tag { background: #eff6ff; color: #1e40af; padding: 4px 12px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; display: inline-block; }
    mark { background: #fde047; font-weight: bold; padding: 0 2px; }
    .report-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 8px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 桌面通知脚本 ---
def notify_desktop(title, message):
    js_code = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("{title}", {{ body: "{message}", icon: "https://img.icons8.com/fluency/96/law.png" }});
    }}
    </script>
    """
    components.html(js_code, height=0)

# --- 3. 增强型同步逻辑 (引入文件大小校验与逻辑断路) ---
def sync_database(ocr_enabled):
    if not os.path.exists("data"): 
        os.makedirs("data")
        return pd.DataFrame()
    
    # 1. 采集物理文件指纹 (文件名 + 整数时间戳 + 文件大小)
    current_files_fingerprint = {}
    for f in os.listdir("data"):
        if f.lower().endswith(('.pdf', '.docx')):
            path = os.path.join("data", f)
            current_files_fingerprint[f] = {
                "time": int(os.path.getmtime(path)),
                "size": os.path.getsize(path)
            }

    # 2. 读取数据库
    db_df = pd.DataFrame()
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            # 强制类型转换，防止比对失败
            if not db_df.empty and '最后修改时间' in db_df.columns:
                db_df['最后修改时间'] = db_df['最后修改时间'].fillna(0).astype(int)
                db_df['文件大小'] = db_df.get('文件大小', pd.Series(0)).fillna(0).astype(int)
            # 剔除已删除文件的记录
            db_df = db_df[db_df['来源文件'].isin(current_files_fingerprint.keys())]
        except:
            db_df = pd.DataFrame()

    # 3. 筛选真正需要更新的文件 (指纹比对)
    to_parse = []
    for f, info in current_files_fingerprint.items():
        if db_df.empty:
            to_parse.append(f)
        else:
            exist = db_df[db_df['来源文件'] == f]
            if exist.empty:
                to_parse.append(f)
            else:
                # 只有时间或大小任一不符时才重扫
                if int(exist.iloc[0]['最后修改时间']) != info['time'] or \
                   int(exist.iloc[0].get('文件大小', 0)) != info['size']:
                    to_parse.append(f)
                    db_df = db_df[db_df['来源文件'] != f]

    # 4. 执行解析 (仅当 to_parse 不为空时)
    if to_parse:
        new_entries = []
        total = len(to_parse)
        start_t = time.time()
        
        with st.status(f"🚀 数字化同步中 (剩余 {total} 个)...", expanded=True) as status:
            for i, f in enumerate(to_parse):
                elapsed = time.time() - start_t
                rem = f"{int(elapsed / i * (total - i))}s" if i > 0 else "计算中..."
                status.update(label=f"🚀 正在处理 ({i+1}/{total}) | 预计: {rem}")
                
                item_df = process_document_to_dataframe(os.path.join("data", f), ocr_enabled=ocr_enabled)
                if not item_df.empty:
                    item_df['来源文件'] = f
                    item_df['最后修改时间'] = int(current_files_fingerprint[f]['time'])
                    item_df['文件大小'] = int(current_files_fingerprint[f]['size'])
                    new_entries.append(item_df)
                st.write(f"✅ 完成: {f}")
            
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
        
        # 解析完成后记录报告并重启一次
        st.session_state.last_report = {"total": total, "time": f"{time.time()-start_t:.1f}s"}
        st.rerun()
        
    return db_df

# --- 4. 侧边栏布局 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    # 下载按钮
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化数据库", data=file, file_name="law_db.csv", use_container_width=True)
    
    ocr_mode = st.toggle("🔍 强制 OCR 识别模式", value=False)
    
    # 同步并加载数据
    df = sync_database(ocr_mode)

    # 报告展示
    if 'last_report' in st.session_state:
        with st.expander("📊 同步简报", expanded=True):
            r = st.session_state.last_report
            st.success(f"同步完成！耗时: {r['time']}")
            if st.button("关闭简报"): del st.session_state.last_report; st.rerun()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择规章文件", std_list)
        st.markdown("### 📍 条文索引")
        toc_view = df[df['标准号'] == selected_std]
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.caption(f"📁 {row['章']}")
                last_chapter = row['章']
            if st.button(f"▫️ {row['编号']}", key=f"btn_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

    # 【常驻重置按钮】：即使出错也能点击
    st.divider()
    st.warning("⚠️ 如下载异常或循环解析，请点击下方重置")
    if st.button("🔥 强制清空云端存档", type="primary", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.cache_data.clear()
        st.rerun()

# --- 5. 主界面渲染 ---
if not df.empty:
    st.markdown(f"""
        <div class="header-banner">
            <h1 style='margin:0; color:#1e3a8a;'>{selected_std}</h1>
            <p style='color:#64748b; margin-top:5px;'>数字化条文查阅工作站</p>
        </div>
        """, unsafe_allow_html=True)

    sc1, sc2 = st.columns([4, 1])
    with sc1: query = st.text_input("🔍 搜索关键词或条文编号", placeholder="回车开始检索...", label_visibility="collapsed")
    with sc2: precise = st.toggle("精准模式", value=False)

    current_law_df = df[df['标准号'] == selected_std]

    if query:
        st.subheader("🎯 检索结果")
        results = current_law_df[current_law_df['编号'] == query] if precise else \
                  current_law_df[current_law_df['全文'].str.contains(query, case=False, na=False) | current_law_df['编号'].str.contains(query, na=False)]
        for idx, row in results.iterrows():
            highlight = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['全文']), flags=re.IGNORECASE)
            st.markdown(f'<div class="clause-card"><div class="chapter-tag">{row["章"]}</div><div style="font-weight:bold; margin-bottom:10px;">{row["编号"]}</div><div>{highlight}</div></div>', unsafe_allow_html=True)
    elif st.session_state.get('jump_target'):
        target = st.session_state.get('jump_target')
        row = current_law_df[current_law_df['编号'] == target].iloc[0]
        st.subheader(f"📍 详情：{target}")
        st.markdown(f'<div class="clause-card" style="border-left-color:#f59e0b;"><div class="chapter-tag">{row["章"]}</div><div style="font-weight:bold; margin:15px 0; font-size:1.3rem; color:#1e3a8a;">{row["编号"]}</div><div style="font-size:1.2rem; line-height:2;">{row["全文"]}</div></div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回全文"): st.session_state.jump_target = None; st.rerun()
    else:
        st.subheader("📖 原文浏览模式")
        full_html = f"<div style='text-align:center;'><h2>{selected_std}</h2></div><br>"
        last_chapter = ""
        for idx, row in current_law_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f"<h3 style='text-align:center; color:#1e40af; margin-top:40px;'>{row['章']}</h3>"
                last_chapter = row['章']
            full_html += f"<p><b>{row['编号']}</b> {row['全文']}</p>"
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 请将 PDF 或 Word 放入 data 文件夹。")
