import streamlit as st
import pandas as pd

# --- 1. 页面基本配置 ---
st.set_page_config(page_title="法规标准查阅系统", layout="wide")

# --- 2. 模拟数据库 (基于上传的 GB/T 4857.5 关键内容) ---
# 在实际应用中，这里可以改为读取 CSV 或 JSON 文件
def get_standard_data():
    data = [
        {
            "标准号": "GB/T 4857.5-92",
            "条款号": "4.1",
            "内容": "试验设备要求：撞击面为水平平面，不移动，不倾斜。质量至少为试验样品质量的50倍，面积应使试验样品完全落在撞击面上。",
            "技术参数": "质量 > 50倍样品重; 面积 > 100mm²; 水平误差 < 2mm" # 
        },
        {
            "标准号": "GB/T 4857.5-92",
            "条款号": "5.6.1",
            "内容": "提起试验样品至预定高度。其实际高度与预定高度之差不得超过预定高度的 ±2%。", # [cite: 8, 10]
            "技术参数": "高度误差 ±2%"
        },
        {
            "标准号": "GB/T 4857.5-92",
            "条款号": "5.6.2",
            "内容": "跌落姿态误差：预定状态与实际状态夹角误差不大于 5°。棱跌落时，夹角误差不大于 2°。", # [cite: 12, 13, 14]
            "技术参数": "面跌落 < 5°; 棱跌落 < 2°"
        },
        {
            "标准号": "GB/T 4857.5-92",
            "条款号": "6",
            "内容": "试验报告内容：包含样品数量、说明、试验高度、温湿度、跌落姿态、试验结果分析等记录。", # [cite: 21, 22, 28]
            "技术参数": "涵盖 a. 至 m. 共13项记录内容" # [cite: 22, 34]
        }
    ]
    return pd.DataFrame(data)

df = get_standard_data()

# --- 3. 侧边栏：筛选功能 ---
with st.sidebar:
    st.title("📂 标准库导航")
    st.info("当前载入标准：GB/T 4857.5 (包装运输跌落试验方法)") # [cite: 2, 3]
    selected_std = st.multiselect("过滤标准号", options=df["标准号"].unique(), default=df["标准号"].unique())
    st.markdown("---")
    st.write("💡 **使用提示**：\n支持按标准号(如 4857.5)或具体内容(如 误差)搜索。")

# --- 4. 主界面：搜索与展示 ---
st.title("📘 法规标准结构化查阅平台")

# 搜索框
search_query = st.text_input("🔍 输入关键词搜索条款内容（例如：高度、误差、设备）", "")

# 过滤逻辑
filtered_df = df[df["标准号"].isin(selected_std)]
if search_query:
    filtered_df = filtered_df[
        filtered_df["内容"].str.contains(search_query) | 
        filtered_df["条款号"].str.contains(search_query) |
        filtered_df["技术参数"].str.contains(search_query)
    ]

# 结果展示
st.subheader(f"共找到 {len(filtered_df)} 条相关条款")

if not filtered_df.empty:
    for _, row in filtered_df.iterrows():
        with st.expander(f"📌 {row['标准号']} - 条款 {row['条款号']}"):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**条款内容：**\n{row['content'] if 'content' in row else row['内容']}")
            with col2:
                st.warning(f"**核心参数要求：**\n{row['技术参数']}")
            
            # 模拟引用关系展示
            st.caption("关联标准: GB/T 4857.1, GB/T 4857.2, GB/T 4857.17") # 
else:
    st.write("❌ 未找到匹配的内容，请尝试更改关键词。")

# --- 5. 底部：原始数据表 ---
if st.checkbox("查看原始数据清单"):
    st.dataframe(df, use_container_width=True)
