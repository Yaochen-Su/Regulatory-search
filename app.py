import streamlit as st
import pandas as pd
import os
from processor import process_pdf_to_dataframe

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="法规标准查阅系统", 
    page_icon="📘", 
    layout="wide"
)

# --- 2. 核心数据加载逻辑 ---
@st.cache_data
def load_and_process_data(data_folder="data"):
    """
    遍历 data 文件夹，解析所有 PDF 并整合数据
    """
    all_data = []
    if not os.path.exists(data_folder):
        return pd.DataFrame()
    
    files = [f for f in os.listdir(data_folder) if f.endswith('.pdf')]
    
    for file in files:
        pdf_path = os.path.join(data_folder, file)
        # 调用 processor.py 中的解析函数
        df_single = process_pdf_to_dataframe(pdf_path)
        all_data.append(df_single)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()

# 加载解析后的数据
df = load_and_process_data()

# --- 3. 侧边栏设计 ---
with st.sidebar:
    st.title("⚙️ 系统管理")
    if not df.empty:
        st.success(f"已成功解析 {len(df['标准号'].unique())} 份标准")
        st.write("**当前库内标准：**")
        for std in df['标准号'].unique():
            st.write(f"- {std}")
    else:
        st.warning("未在 data 文件夹下找到 PDF 文件")
    
    st.divider()
    st.markdown("""
    **功能说明：**
    1. 自动提取章节号与条款内容。
    2. 自动识别关键技术参数（如误差范围）。
    3. 支持全文关键字检索。
    """)

# --- 4. 主界面展示 ---
st.title("📘 法规标准结构化查阅平台")

# 搜索区域
col_search, col_filter = st.columns([3, 1])
with col_search:
    query = st.text_input("🔍 输入关键词（如：高度、误差、撞击面）", placeholder="搜索条款内容...")
with col_filter:
    if not df.empty:
        selected_std = st.selectbox("筛选标准", ["全部"] + list(df['标准号'].unique()))
    else:
        selected_std = "全部"

# 数据过滤逻辑
if not df.empty:
    display_df = df.copy()
    
    # 按标准筛选
    if selected_std != "全部":
        display_df = display_df[display_df['标准号'] == selected_std]
    
    # 按关键词搜索
    if query:
        display_df = display_df[
            display_df['内容'].str.contains(query, case=False, na=False) |
            display_df['条款号'].str.contains(query, case=False, na=False)
        ]

    # 结果展示
    st.subheader(f"找到 {len(display_df)} 条相关条款")
    
    for _, row in display_df.iterrows():
        # 根据你提供的文档内容，这里会展示如 ±2%  等关键参数
        with st.expander(f"📌 {row['标准号']} - 条款 {row['条款号']}"):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**条款原文：**\n{row['内容']}")
            with c2:
                st.info(f"**关键参数：**\n{row['技术参数']}")
            
            # 针对特定标准（如 GB/T 4857.5）的补充信息 
            if "4857.5" in row['标准号']:
                st.caption("注：本标准等效采用 ISO 2248-1985 ")
else:
    st.info("请在 GitHub 的 data 文件夹中上传标准 PDF 文件并重新部署。")

# --- 5. 底部数据预览 ---
if st.checkbox("查看解析后的原始数据表"):
    st.dataframe(df, use_container_width=True)
