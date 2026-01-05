import streamlit as st
import pandas as pd
import os
import re
import time
import altair as alt
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

# --- 3. 增强型同步逻辑 (解决 KeyError) ---
def sync_database(ocr_enabled):
    if not os.path.exists("data"): os.makedirs("data")
    
    # 获取物理文件元数据
    current_files_meta = {f: int(os.path.getmtime(os.path.join("data", f))) 
                          for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))}

    # 加载数据库并检查列完整性
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            # 核心修复：如果缺少关键列，则强制清空并重新解析，防止 KeyError
            required_cols = ['来源文件', '最后修改时间', '编号', '全文']
            if not all(col in db_df.columns for col in required_cols):
                db_df = pd.DataFrame()
            else:
                db_df = db_df[db_df['来源文件'].isin(current_files_meta.keys())]
        except: 
            db_df = pd.DataFrame()
    else:
        db_df = pd.DataFrame()

    # 判定待处理文件
    to_parse = []
    for f, mtime in current_files_meta.items():
        if db_df.empty:
            to_parse.append(f)
        else:
            exist = db_df[db_df['来源文件'] == f]
            # 安全获取时间戳，避免 KeyError
            if exist.empty or int(exist.iloc[0].get('最后修改时间', 0)) != mtime:
                to_parse.append(f)
                db_df = db_df[db_df['来源文件'] != f]

    if to_parse:
        new_entries = []
        total_files = len(to_parse)
        pdf_count = sum(1 for f in to_parse if f.lower().endswith('.pdf'))
        docx_count = sum(1 for f in to_parse if f.lower().endswith('.docx'))
        
        start_time = time.time()
        success_count = 0
        
        with st.status(f"🚀 正在数字化处理 {total_files} 个文件...", expanded=True) as status:
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
        
        total_duration = time.time() - start_time
        st.session_state.last_report = {
            "total": total_files, "success": success_count,
            "time": f"{total_duration:.1f}s", "pdf": pdf_count, "docx": docx_count
        }
        notify_desktop("解析完成", f"成功处理 {success_count} 份文件。")
        st.rerun()
    return db_df

# --- 4. 侧边栏渲染 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化数据库", data=file, file_name="law_db.csv", use_container_width=True)
    st.divider()

    ocr_mode = st.toggle("🔍 强制 OCR 识别模式", value=False)
    df = sync_database(ocr_mode)

    # 📊 解析报告图表显示 (增加安全防护)
    if 'last_report' in st.session_state:
        with st.expander("📊 上次解析报告", expanded=True):
            r = st.session_state.last_report
            st.markdown(f"""
            <div class='report-card'>
            <b>处理总数:</b> {r.get('total', 0)} (PDF: {r.get('pdf', 0)}, Word: {r.get('docx', 0)})<br>
            <b>成功导入:</b> {r.get('success', 0)}<br>
            <b>总计耗时:</b> {r.get('time', '0s')}<br>
            </div>
            """, unsafe_allow_html=True)
            
            # 只有当数据存在时才绘制图表，防止绘图引起的 KeyError
            chart_data = pd.DataFrame({
                '类型': ['PDF', 'Word'],
                '数量': [r.get('pdf', 0), r.get('docx', 0)]
            })
            chart = alt.Chart(chart_data).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                x=alt.X('类型:N', axis=alt.Axis(labelAngle=0)),
                y='数量:Q',
                color=alt.Color('类型:N', scale=alt.Scale(range=['#2563eb', '#10b981']), legend=None)
            ).properties(height=120)
            st.altair_chart(chart, use_container_width=True)
            
            if st.button("清除报告记录", use_container_width=True):
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
            # 使用 标准号+索引 确保 Key 唯一
            if st.button(f"▫️ {row['编号']}", key=f"btn_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

    st.divider()
    if st.button("🔥 重置系统存档"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

# --- 5. 主界面渲染 (保持原有逻辑) ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; color:#1e3a8a;'>{selected_std if not df.empty else "法规库加载中"}</h1>
        <p style='color:#64748b; margin-top:5px;'>数字化工作站 | 自动更新检测已启用</p>
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
