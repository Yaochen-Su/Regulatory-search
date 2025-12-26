import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# 1. 页面配置与美化
st.set_page_config(page_title="标准数字化阅览室", layout="wide")
st.markdown("""
    <style>
    .toc-btn { text-align: left !important; border-bottom: 1px solid #eee !important; font-size: 0.85em !important; }
    .content-box { padding: 20px; border-radius: 8px; border: 1px solid #e0e0e0; margin-bottom: 15px; background: #fff; }
    .highlight { background-color: #fff9c4; border: 2px solid #ffd600; }
    mark { background: #ffeb3b; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. 数据加载
@st.cache_data(show_spinner=False)
def load_data():
    files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    all_data = []
    
    # 进度展示
    progress_container = st.empty()
    for i, f in enumerate(files):
        with progress_container.container():
            st.info(f"正在分析第 {i+1}/{len(files)} 份文档: {f} (扫描件可能耗时较长...)")
        
        df_item = process_document_to_dataframe(os.path.join("data", f))
        if not df_item.empty: all_data.append(df_item)
    
    progress_container.empty()
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

df = load_data()

# 3. 侧边栏：选择文件与目录树
with st.sidebar:
    st.title("🗂️ 标准库目录")
    if not df.empty:
        std_list = list(df['标准号'].unique())
        selected_std = st.selectbox("当前查阅标准：", std_list)
        
        st.divider()
        st.write("📍 **快速跳转章节**")
        # 提取当前标准的目录结构 [cite: 1, 21]
        current_toc = df[df['标准号'] == selected_std]
        for idx, row in current_toc.iterrows():
            if st.button(f" {row['条款号']}", key=f"t_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    else:
        st.warning("data/ 文件夹为空")

# 4. 主界面：检索区域
st.title("📘 数字化查阅与检索平台")
search_input = st.text_input("🔍 全文模糊搜索或输入具体条款号（如：5.6.1）", placeholder="输入内容点击回车...")

# 5. 核心逻辑：全文 vs 搜索视图切换
if not df.empty:
    if search_input:
        # --- 视图 A：搜索模式 (仅显示搜索内容) ---
        st.subheader(f"🎯 搜索结果：'{search_input}'")
        # 支持模糊搜索内容或精确匹配条款号 [cite: 1, 8, 21]
        results = df[
            (df['内容'].str.contains(search_input, case=False, na=False)) | 
            (df['条款号'] == search_input)
        ]
        
        if not results.empty:
            for _, row in results.iterrows():
                # 高亮匹配词 
                highlighted_content = re.sub(f"({search_input})", r"<mark>\1</mark>", row['内容'], flags=re.IGNORECASE)
                st.markdown(f"""
                    <div class="content-box">
                        <small>{row['标准号']} - 条款 {row['条款号']}</small>
                        <div style="margin-top:10px;">{highlighted_content}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.error("未找到相关条目")
    else:
        # --- 视图 B：全文查阅模式 ---
        st.subheader(f"📖 全文查阅：{selected_std}")
        current_view = df[df['标准号'] == selected_std]
        
        for _, row in current_view.iterrows():
            # 跳转锚点判断
            is_target = "jump_target" in st.session_state and st.session_state.jump_target == row['条款号']
            card_class = "content-box highlight" if is_target else "content-box"
            
            st.markdown(f"""
                <div class="{card_class}">
                    <div style="font-weight:bold; color:#1565C0;">[{row['条款号']}]</div>
                    <div style="margin-top:8px;">{row['内容']}</div>
                    <div style="margin-top:10px;"><small>📊 技术参数：{row['技术参数']}</small></div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("请在 GitHub 的 data/ 文件夹上传标准文件以开始。")
