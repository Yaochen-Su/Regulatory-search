import streamlit as st
import pandas as pd
import os
from processor import process_document_to_dataframe

st.set_page_config(page_title="标准数字化系统", layout="wide")

# --- 环境检查区 ---
with st.sidebar:
    st.header("⚙️ 环境诊断")
    tess_exists = os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    if tess_exists:
        st.success("Tesseract 引擎已就绪")
    else:
        st.error("未找到 Tesseract！请检查路径")

DB_FILE = "processed_database.csv"

# --- 核心同步逻辑 (单线程最稳版) ---
def sync_data():
    if not os.path.exists("data"):
        os.makedirs("data")
        return pd.DataFrame()

    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        progress_text = st.empty()
        pbar = st.progress(0)
        new_data = []
        
        for i, f in enumerate(new_files):
            progress_text.text(f"正在处理 ({i+1}/{len(new_files)}): {f}")
            df_item = process_document_to_dataframe(os.path.join("data", f))
            if not df_item.empty:
                new_data.append(df_item)
            pbar.progress((i + 1) / len(new_files))
        
        if new_data:
            db_df = pd.concat([db_df] + new_data, ignore_index=True)
            # 检查 CSV 是否被占用
            try:
                db_df.to_csv(DB_FILE, index=False)
                st.success("数据库更新成功！")
            except Exception as e:
                st.error(f"无法保存数据库，请关闭已打开的 Excel 文件！错误: {e}")
        progress_text.empty()
        pbar.empty()
    
    return db_df

# --- 界面展示 ---
st.title("⚖️ 数字化规程查阅平台")

try:
    df = sync_data()
except Exception as e:
    st.exception(e) # 这会将详细的错误栈显示在网页上
    st.stop()

if not df.empty:
    search_query = st.text_input("🔍 输入关键词或条款号搜索")
    
    if search_query:
        display_df = df[df['内容'].str.contains(search_query, case=False, na=False) | (df['条款号'] == search_query)]
        st.subheader(f"找到 {len(display_df)} 条结果")
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("👈 请在左侧选择标准，或在上方搜索。目前库内已有数据：")
        st.write(df.groupby('标准号').size().reset_index(name='条款数量'))
else:
    st.info("请将文件放入 data 文件夹。")
