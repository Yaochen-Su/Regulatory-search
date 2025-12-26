import streamlit as st
import pandas as pd
import os
# 导入同步后的函数名
from processor import process_document_to_dataframe

# 页面基础设置
st.set_page_config(page_title="标准库查询系统", layout="wide")

# 自定义样式
st.markdown("""
    <style>
    .stApp { background-color: #FDFDFD; }
    .std-card {
        padding: 20px;
        border-radius: 10px;
        border-left: 6px solid #1E40AF;
        background-color: #FFFFFF;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    .tag {
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.85em;
    }
    </style>
""", unsafe_allow_html=True)

# 数据加载函数
@st.cache_data
def load_all_data(folder="data"):
    all_dfs = []
    if not os.path.exists(folder):
        return pd.DataFrame()
    
    files = [f for f in os.listdir(folder) if f.lower().endswith(('.pdf', '.docx'))]
    
    if not files:
        return pd.DataFrame()

    progress_bar = st.progress(0)
    for i, file in enumerate(files):
        path = os.path.join(folder, file)
        df_item = process_document_to_dataframe(path)
        if not df_item.empty:
            all_dfs.append(df_item)
        progress_bar.progress((i + 1) / len(files))
    
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# 主程序
st.title("📘 法规与标准查阅平台")
st.caption("支持 PDF 及 Word 格式，自动识别 GB/T 条款及核心技术参数")

data = load_all_data()

if not data.empty:
    # 搜索与筛选
    search_col, filter_col = st.columns([3, 1])
    with search_col:
        query = st.text_input("🔍 搜索标准号或内容关键字", placeholder="例如：跌落、±2%、5.6.1...")
    with filter_col:
        std_list = ["全部标准"] + list(data['标准号'].unique())
        selected_std = st.selectbox("筛选标准", std_list)

    # 逻辑处理
    filtered_data = data.copy()
    if selected_std != "全部标准":
        filtered_data = filtered_data[filtered_data['标准号'] == selected_std]
    if query:
        filtered_data = filtered_data[
            filtered_data['内容'].str.contains(query, case=False, na=False) |
            filtered_data['标准号'].str.contains(query, case=False, na=False)
        ]

    # 结果展示
    st.subheader(f"共匹配到 {len(filtered_data)} 条结果")
    for _, row in filtered_data.iterrows():
        st.markdown(f"""
            <div class="std-card">
                <div style="font-weight:bold; color:#1E3A8A; font-size:1.1em;">📌 {row['标准号']} - 条款 {row['条款号']}</div>
                <div style="margin: 10px 0; line-height:1.6;">{row['内容']}</div>
                <div><span class="tag">📏 技术参数要求：{row['技术参数']}</span></div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("请在 GitHub 的 data/ 文件夹中上传 .pdf 或 .docx 文件。")
