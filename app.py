import streamlit as st
import pandas as pd
import os
import re
import time
import streamlit.components.v1 as components
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS ---
st.set_page_config(page_title="法规标准数字化工作站", page_icon="⚖️", layout="wide")

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
    .report-card { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 桌面通知脚本 ---
def notify_desktop(title, message):
    """通过浏览器发送桌面通知"""
    js_code = f"""
    <script>
    if (Notification.permission === "granted") {{
        new Notification("{title}", {{ body: "{message}", icon: "https://img.icons8.com/fluency/96/law.png" }});
    }} else if (Notification.permission !== "denied") {{
        Notification.requestPermission().then(permission => {{
            if (permission === "granted") {{
                new Notification("{title}", {{ body: "{message}" }});
            }}
        }});
    }}
    </script>
    """
    components.html(js_code, height=0)

# --- 3. 增强型同步逻辑：增加报告与通知 ---
def sync_database(ocr_enabled):
    if not os.path.exists("data"): os.makedirs("data")
    
    current_files_meta = {f: int(os.path.getmtime(os.path.join("data", f))) 
                          for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))}

    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            db_df = db_df[db_df['来源文件'].isin(current_files_meta.keys())]
        except: db_df = pd.DataFrame()
    else: db_df = pd.DataFrame()

    to_parse = [f for f, mtime in current_files_meta.items() if db_df.empty or 
                db_df[db_df['来源文件'] == f].empty or 
                int(db_df[db_df['来源文件'] == f].iloc[0].get('最后修改时间', 0)) != mtime]

    if to_parse:
        # 清除即将重扫的文件旧记录
        db_df = db_df[~db_df['来源文件'].isin(to_parse)]
        
        new_entries = []
        total_files = len(to_parse)
        start_time = time.time()
        success_count = 0
        
        with st.status(f"🚀 正在同步 {total_files} 个文件...", expanded=True) as status:
            for i, f in enumerate(to_parse):
                elapsed = time.time() - start_time
                time_str = f"{int(elapsed / i * (total_files - i))}秒" if i > 0 else "计算中..."
                status.update(label=f"🚀 正在解析 ({i+1}/{total_files}) | 预计剩余：{time_str}")
                
                item_df = process_document_to_dataframe(os.path.join("data", f), ocr_enabled=ocr_enabled)
                if not item_df.empty:
                    item_df['来源文件'] = f
                    item_df['最后修改时间'] = current_files_meta[f]
                    new_entries.append(item_df)
                    success_count += 1
                st.write(f"✅ 已完成: `{f}`")
            
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
        
        # 任务完成：记录报告并发送通知
        total_duration = time.time() - start_time
        st.session_state.last_report = {
            "total": total_files,
            "success": success_count,
            "time": f"{total_duration:.1f}秒",
            "avg": f"{total_duration/total_files:.2f}秒" if total_files > 0 else "0秒"
        }
        notify_desktop("解析任务已完成", f"成功数字化 {success_count} 份规章文件，总耗时 {int(total_duration)} 秒。")
        st.rerun()
    return db_df

# --- 4. 侧边栏与报告展示 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    st.divider()
    ocr_mode = st.toggle("🔍 强制 OCR 识别模式", value=False)
    st.divider()

    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化数据库", data=file, file_name="law_db.csv", use_container_width=True)
    st.divider()

    df = sync_database(ocr_mode)

    # 显示解析报告统计
    if 'last_report' in st.session_state:
        with st.expander("📊 上次解析报告", expanded=True):
            r = st.session_state.last_report
            st.markdown(f"""
            <div class='report-card'>
            <b>处理总数:</b> {r['total']}<br>
            <b>成功导入:</b> {r['success']}<br>
            <b>总计耗时:</b> {r['time']}<br>
            <b>平均耗时:</b> {r['avg']}
            </div>
            """, unsafe_allow_html=True)
            if st.button("清除报告记录"):
                del st.session_state.last_report
                st.rerun()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅规章", std_list)
        st.markdown("### 📍 条文索引")
        toc_view = df[df['标准号'] == selected_std]
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.caption(f"📁 {row['章']}")
                last_chapter = row['章']
            if st.button(f"▫️ {row['编号']}", key=f"btn_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

# --- 5. 主界面渲染 ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; color:#1e3a8a;'>{selected_std if not df.empty else "法规库加载中"}</h1>
        <p style='color:#64748b; margin-top:5px;'>数字化工作站 | 已启用桌面通知功能</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    sc1, sc2 = st.columns([4, 1])
    with sc1: query = st.text_input("🔍 搜索关键词或编号", placeholder="回车开始检索...", label_visibility="collapsed")
    with sc2: precise = st.toggle("精准模式", value=False)

    current_law_df = df[df['标准号'] == selected_std]

    if query:
        st.subheader("🎯 搜索匹配条文")
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
        if st.button("⬅️ 返回全文"):
            st.session_state.jump_target = None
            st.rerun()
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
    st.info("👋 请将文件放入 data 文件夹并确保浏览器已允许通知权限。")
