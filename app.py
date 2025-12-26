import streamlit as st
import pandas as pd
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from processor import process_document_to_dataframe

# --- 1. 页面配置与专业 UI 样式 ---
st.set_page_config(page_title="法规标准数字化智慧平台", layout="wide", page_icon="⚖️")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .main-title { background: linear-gradient(90deg, #1e3a8a, #3b82f6); color: white; padding: 20px; border-radius: 10px; margin-bottom: 25px; }
    .card { background: white; padding: 20px; border-radius: 12px; border-left: 6px solid #2563eb; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 15px; }
    .highlight-target { border-left: 6px solid #f59e0b !important; background-color: #fffbeb !important; }
    .param-badge { background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 5px; font-weight: bold; font-size: 0.85em; }
    mark { background: #fde047; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心增量同步逻辑 ---
DB_FILE = "processed_database.csv"

def sync_data():
    if not os.path.exists("data"): os.makedirs("data")
    
    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        st.warning(f"检测到 {len(new_files)} 份新文档，正在进行深度 OCR 解析...")
        new_entries = []
        
        # 使用 ThreadPoolExecutor 确保在 Streamlit 中不崩溃
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(process_document_to_dataframe, os.path.join("data", f)): f for f in new_files}
            pbar = st.progress(0)
            for i, future in enumerate(as_completed(futures)):
                fname = futures[future]
                try:
                    df_item = future.result()
                    if not df_item.empty:
                        new_entries.append(df_item)
                except Exception as e:
                    st.error(f"解析 {fname} 失败: {e}")
                pbar.progress((i + 1) / len(new_files))

        if new_entries:
            db_df = pd.concat([db_df] + new_entries, ignore_index=True)
            db_df.to_csv(DB_FILE, index=False)
            st.cache_data.clear()
            st.success("同步完成！")
            st.rerun()
    return db_df

df = sync_data()

# --- 3. 侧边栏及功能控制 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/books.png", width=60)
    st.title("导航面板")
    if not df.empty:
        selected_std = st.selectbox("📂 选择当前标准：", sorted(df['标准号'].unique()))
        st.divider()
        st.write("📑 **章节快速跳转**")
        toc_df = df[df['标准号'] == selected_std]
        for idx, row in toc_df.iterrows():
            if st.button(f"条款 {row['条款号']}", key=f"toc_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    
    st.divider()
    with st.expander("🛠️ 系统维护"):
        if st.checkbox("授权重置"):
            if st.button("🔥 重新解析全库", type="primary"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.cache_data.clear()
                st.rerun()

# --- 4. 主界面：多维检索与全文查阅 ---
st.markdown('<div class="main-title"><h1>法规标准智慧化数字化工作站</h1></div>', unsafe_allow_html=True)

if not df.empty:
    search_q = st.text_input("🔍 搜索关键词或条款号 (例如: 跌落、±2%、5.6.1)", placeholder="输入内容后按回车...")

    if search_q:
        st.subheader(f"🎯 搜索结果: {search_q}")
        res = df[(df['内容'].str.contains(search_q, case=False, na=False)) | (df['条款号'] == search_q)]
        for _, row in res.iterrows():
            text = re.sub(f"({search_q})", r"<mark>\1</mark>", row['内容'], flags=re.IGNORECASE)
            st.markdown(f'<div class="card"><small>{row["标准号"]}</small><br><b>条款 {row["条款号"]}</b><br>{text}<br><span class="param-badge">参数: {row["技术参数"]}</span></div>', unsafe_allow_html=True)
    else:
        st.subheader(f"📖 全文浏览: {selected_std}")
        for _, row in toc_df.iterrows():
            is_target = st.session_state.get('jump_target') == row['条款号']
            card_cls = "card highlight-target" if is_target else "card"
            st.markdown(f'<div class="{card_cls}"><b>条款 {row["条款号"]}</b><br>{row["内容"]}<br><div style="margin-top:8px;"><span class="param-badge">参数: {row["技术参数"]}</span></div></div>', unsafe_allow_html=True)
else:
    st.info("请将 PDF/Word 文件放入 data 文件夹以启动解析。")
