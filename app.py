import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 初始化与样式 ---
st.set_page_config(page_title="法规标准数字化工作站", layout="wide")
DB_FILE = "processed_database.csv"

st.markdown("""
    <style>
    .toc-btn { text-align: left !important; font-size: 0.85em !important; margin-bottom: 2px !important; }
    .content-box { padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 15px; background: white; }
    .highlight-card { border: 2px solid #fbbf24; background-color: #fffbeb; }
    mark { background-color: #fef08a; font-weight: bold; border-radius: 2px; }
    .param-label { background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 增量加载逻辑 ---
def load_and_sync_data():
    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    
    # 扫描 data 文件夹
    if not os.path.exists("data"): os.makedirs("data")
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        new_entries = []
        status = st.empty()
        pbar = st.progress(0)
        for i, f in enumerate(new_files):
            status.info(f"正在增量解析 ({i+1}/{len(new_files)}): {f} ...")
            df_item = process_document_to_dataframe(os.path.join("data", f))
            if not df_item.empty: new_entries.append(df_item)
            pbar.progress((i + 1) / len(new_files))
        
        if new_entries:
            combined = pd.concat([db_df, pd.concat(new_entries)], ignore_index=True)
            combined.to_csv(DB_FILE, index=False)
            st.cache_data.clear()
            status.success("🎉 数据库已同步更新！")
            return combined
    return db_df

df = load_and_sync_data()

# --- 3. 侧边栏：标准选择与目录树 ---
with st.sidebar:
    st.title("📚 标准目录")
    if not df.empty:
        std_list = list(df['标准号'].unique())
        selected_std = st.selectbox("选择要查阅的标准：", std_list)
        
        st.divider()
        st.write("📍 **快速跳转章节**")
        # 提取当前选定标准的目录
        toc_view = df[df['标准号'] == selected_std]
        for idx, row in toc_view.iterrows():
            if st.button(f" {row['条款号']}", key=f"btn_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    
    st.markdown("---")
    if st.checkbox("管理员重置权限"):
        if st.button("🔥 清空存档并全库重扫", type="primary"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.cache_data.clear()
            st.rerun()

# --- 4. 主界面：检索与展示逻辑 ---
st.title("⚖️ 法规标准数字化查阅平台")
search_input = st.text_input("🔍 全文搜索或输入条款号（例如：跌落高度、5.6.1）", "")

if not df.empty:
    if search_input:
        # 搜索视图：仅显示匹配结果
        st.subheader(f"🎯 搜索结果：'{search_input}'")
        # 条款号精确匹配或正文模糊匹配
        results = df[(df['内容'].str.contains(search_input, case=False)) | (df['条款号'] == search_input)]
        
        if not results.empty:
            for _, row in results.iterrows():
                # 高亮关键词
                text = re.sub(f"({search_input})", r"<mark>\1</mark>", row['内容'], flags=re.IGNORECASE)
                st.markdown(f"""
                    <div class="content-box">
                        <small>{row['标准号']}</small><br>
                        <b>[{row['条款号']}]</b> {text}<br>
                        <div style="margin-top:10px;"><span class="param-label">参数：{row['技术参数']}</span></div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("未找到匹配内容。")
    else:
        # 全文视图：显示选定标准的完整内容 [cite: 1, 19, 21]
        st.subheader(f"📖 全文浏览：{selected_std}")
        for _, row in toc_view.iterrows():
            is_target = st.session_state.get('jump_target') == row['条款号']
            card_style = "content-box highlight-card" if is_target else "content-box"
            st.markdown(f"""
                <div class="{card_style}">
                    <div style="font-weight:bold; color:#1e40af;">[{row['条款号']}]</div>
                    <div style="margin-top:10px;">{row['内容']}</div>
                    <div style="margin-top:10px;"><span class="tag">参数：{row['技术参数']}</span></div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("请在 data/ 文件夹中放入标准文件（PDF 或 Word）。")
