import streamlit as st
import pandas as pd
import os
# 关键：导入更新后的统一处理函数
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS ---
st.set_page_config(page_title="法规标准库", page_icon="📘", layout="wide")

st.markdown("""
    <style>
    .clause-card {
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2E7D32;
        background-color: #f8f9fa;
        margin-bottom: 10px;
    }
    .param-tag {
        background-color: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.9em;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心加载逻辑 ---
@st.cache_data
def load_data(data_folder="data"):
    all_dfs = []
    errors = []
    
    if not os.path.exists(data_folder):
        return pd.DataFrame(), ["data 文件夹不存在"]
    
    # 获取 PDF 和 Word 文件
    files = [f for f in os.listdir(data_folder) if f.lower().endswith(('.pdf', '.docx'))]
    
    if not files:
        return pd.DataFrame(), ["未发现 .pdf 或 .docx 文件"]

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, file in enumerate(files):
        path = os.path.join(data_folder, file)
        status_text.text(f"正在解析 ({i+1}/{len(files)}): {file}")
        try:
            # 调用更新后的函数名
            df_item = process_document_to_dataframe(path)
            if not df_item.empty:
                all_dfs.append(df_item)
        except Exception as e:
            errors.append(f"{file}: {str(e)}")
        progress_bar.progress((i + 1) / len(files))
    
    status_text.text("✅ 数据加载完成")
    
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True), errors
    return pd.DataFrame(), errors

# --- 3. 界面展示 ---
st.title("📘 数字化法规标准查阅平台")

df, errs = load_data()

# 侧边栏
with st.sidebar:
    st.header("统计信息")
    if not df.empty:
        st.metric("已收录标准", len(df['标准号'].unique()))
        st.metric("总条款数", len(df))
    if errs:
        with st.expander("⚠️ 解析警报"):
            for e in errs: st.error(e)

# 主搜索区
if not df.empty:
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("🔍 输入标准号、名称或条款内容关键词", placeholder="搜索...")
    with col2:
        std_list = ["全部"] + list(df['标准号'].unique())
        selected = st.selectbox("按标准号筛选", std_list)

    # 过滤
    res = df.copy()
    if selected != "全部":
        res = res[res['标准号'] == selected]
    if query:
        res = res[res['内容'].str.contains(query, case=False) | res['标准号'].str.contains(query, case=False)]

    # 展示结果
    st.subheader(f"找到 {len(res)} 条匹配结果")
    for _, row in res.iterrows():
        st.markdown(f"""
            <div class="clause-card">
                <div style="color:#1b5e20; font-weight:bold;">📌 {row['标准号']} - 条款 {row['条款号']}</div>
                <div style="margin:10px 0;">{row['内容']}</div>
                <div>关键参数识别：<span class="param-tag">{row['技术参数']}</span></div>
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("请在 data/ 文件夹中上传标准文件。")
