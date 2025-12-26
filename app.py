import streamlit as st
import pandas as pd
import os
# 导入你之前编写的解析逻辑
from processor import process_pdf_to_dataframe

# ==========================================
# 1. 页面配置与美化 (CSS)
# ==========================================
st.set_page_config(
    page_title="法规标准结构化查阅系统",
    page_icon="📘",
    layout="wide"
)

# 自定义 CSS 样式，提升前端视觉体验
st.markdown("""
    <style>
    /* 搜索框美化 */
    .stTextInput > div > div > input {
        border-radius: 10px;
    }
    /* 条款卡片容器样式 */
    .clause-card {
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4A90E2;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        color: #31333F;
    }
    /* 条款标题样式 */
    .clause-header {
        color: #1E3A8A;
        margin-bottom: 10px;
        font-weight: bold;
        font-size: 1.1em;
    }
    /* 关键参数标签样式 */
    .param-tag {
        display: inline-block;
        background-color: #E0F2FE;
        color: #0369A1;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 600;
        margin-top: 10px;
        border: 1px solid #BAE6FD;
    }
    /* 侧边栏样式优化 */
    .css-1d391kg {
        background-color: #F8FAFC;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 数据处理核心逻辑
# ==========================================
@st.cache_data
def load_all_standards(data_folder="data"):
    """
    自动扫描 data 文件夹，解析所有 PDF 并合并
    """
    all_dfs = []
    if not os.path.exists(data_folder):
        return pd.DataFrame()
    
    # 获取文件夹内所有 PDF
    pdf_files = [f for f in os.listdir(data_folder) if f.endswith('.pdf')]
    
    if not pdf_files:
        return pd.DataFrame()

    for file in pdf_files:
        pdf_path = os.path.join(data_folder, file)
        try:
            # 调用 processor.py 里的函数
            df_item = process_pdf_to_dataframe(pdf_path)
            all_dfs.append(df_item)
        except Exception as e:
            st.error(f"解析文件 {file} 时出错: {e}")
            
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()

# 加载数据
df = load_all_standards()

# ==========================================
# 3. 侧边栏设计 (Sidebar)
# ==========================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/law.png", width=80)
    st.title("系统导航")
    
    if not df.empty:
        st.success(f"✅ 已收录 {len(df['标准号'].unique())} 份标准")
        st.write("**标准清单：**")
        for s in df['标准号'].unique():
            st.caption(f"• {s}")
    else:
        st.warning("⚠️ 库内暂无数据")
        st.info("请在 data/ 文件夹上传 PDF 并刷新。")

    st.divider()
    st.write("### 🛠️ 工具说明")
    st.write("本系统可自动识别标准中的条款编号及技术参数（如误差、量值）。")
    st.caption("技术栈：Streamlit + PyMuPDF")

# ==========================================
# 4. 主界面设计 (Main UI)
# ==========================================
st.title("📘 法规标准结构化查阅平台")
st.markdown("---")

# 4.1 搜索与过滤区
col_search, col_filter = st.columns([3, 1])

with col_search:
    query = st.text_input(
        "🔍 全文搜索", 
        placeholder="输入关键词（如：高度、误差、撞击面、4.1）...",
        label_visibility="collapsed"
    )

with col_filter:
    if not df.empty:
        std_list = ["全部标准"] + list(df['标准号'].unique())
        selected_std = st.selectbox("筛选特定标准", std_list, label_visibility="collapsed")
    else:
        selected_std = "全部标准"

# 4.2 数据过滤逻辑
if not df.empty:
    filtered_df = df.copy()
    
    # 按标准筛选
    if selected_std != "全部标准":
        filtered_df = filtered_df[filtered_df['标准号'] == selected_std]
    
    # 按搜索词筛选 (全文模糊匹配)
    if query:
        # 同时匹配条款号和内容
        filtered_df = filtered_df[
            filtered_df['内容'].str.contains(query, case=False, na=False) |
            filtered_df['条款号'].str.contains(query, case=False, na=False) |
            filtered_df['技术参数'].str.contains(query, case=False, na=False)
        ]

    # 4.3 结果展示区
    st.subheader(f"查询结果 ({len(filtered_df)} 条)")
    
    if len(filtered_df) > 0:
        for _, row in filtered_df.iterrows():
            # 使用 HTML 渲染卡片样式
            st.markdown(f"""
                <div class="clause-card">
                    <div class="clause-header">📌 {row['标准号']} - 条款 {row['条款号']}</div>
                    <div style="line-height: 1.6;">{row['内容']}</div>
                    <div class="param-tag">📏 核心参数：{row['技术参数']}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # 针对特定标准的特殊提醒 (可选)
            if "4857.5" in row['标准号']:
                st.caption("💡 提示：该条款涉及运输包装件的垂直冲击/跌落试验精度要求。")
    else:
        st.info("💡 未找到匹配条款，请尝试缩短搜索词或检查拼写。")
else:
    st.error("❌ 系统中未检测到数据，请检查 data/ 文件夹下的 PDF 文件。")

# 4.4 底部信息
st.markdown("---")
if st.checkbox("📊 显示底层数据表（调试用）"):
    st.dataframe(df, use_container_width=True)
