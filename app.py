import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置 ---
st.set_page_config(page_title="标准数字化检索(纯净版)", layout="wide")

st.markdown("""
    <style>
    .reportview-container { background: #f0f2f6; }
    .stMetric { background: white; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .std-card { background: white; padding: 20px; border-radius: 10px; border-left: 5px solid #1e3a8a; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    mark { background: #ffeb3b; padding: 0 2px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心逻辑 ---
DB_FILE = "processed_database.csv"

def load_data():
    if not os.path.exists("data"): 
        os.makedirs("data")
        return pd.DataFrame()

    # 读取/初始化数据库
    if os.path.exists(DB_FILE):
        db_df = pd.read_csv(DB_FILE)
    else:
        db_df = pd.DataFrame()

    processed_files = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in all_files if f not in processed_files]

    if new_files:
        st.info(f"✨ 发现 {len(new_files)} 份新文档，正在同步...")
        new_data_list = []
        pbar = st.progress(0)
        
        for i, f in enumerate(new_files):
            df_item = process_document_to_dataframe(os.path.join("data", f))
            if not df_item.empty:
                new_data_list.append(df_item)
            pbar.progress((i + 1) / len(new_files))

        if new_data_list:
            db_df = pd.concat([db_df] + new_data_list, ignore_index=True)
            db_df.to_csv(DB_FILE, index=False)
            st.success("同步完成！")
            st.rerun()
            
    return db_df

# --- 3. 界面渲染 ---
st.title("⚖️ 标准法规纯文本检索平台")
st.caption("提示：当前版本已禁用OCR，仅支持文本型PDF及Word文件。")

df = load_data()

if not df.empty:
    # 顶部统计
    col1, col2 = st.columns(2)
    col1.metric("已收录标准", len(df['标准号'].unique()))
    col2.metric("已解析条款", len(df))

    # 搜索区
    query = st.text_input("🔍 在全库中搜索关键词（如：跌落高度、±2%、4.1）")

    if query:
        # 模糊匹配
        search_results = df[df['内容'].str.contains(query, case=False, na=False) | (df['条款号'] == query)]
        st.subheader(f"找到 {len(search_results)} 条匹配结果")
        
        for _, row in search_results.iterrows():
            # 关键词高亮
            highlighted_content = re.sub(f"({query})", r"<mark>\1</mark>", row['content' if 'content' in row else '内容'], flags=re.IGNORECASE)
            st.markdown(f"""
                <div class="std-card">
                    <small style="color: #666;">{row['标准号']} | 条款 {row['条款号']}</small>
                    <div style="margin-top:10px; line-height:1.6;">{highlighted_content}</div>
                    <div style="margin-top:10px;"><span style="background:#e3f2fd; color:#0d47a1; padding:2px 8px; border-radius:5px; font-size:0.8em;">📏 技术参数: {row['技术参数']}</span></div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # 默认显示说明
        st.info("💡 请在上方搜索框输入关键词开始查询。扫描件及图片格式PDF暂不支持搜索。")
else:
    st.info("请确保 data/ 文件夹中存有文本型标准文件。")
