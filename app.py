import streamlit as st
import pandas as pd
import os
import pytesseract
from processor import process_document_to_dataframe

# --- 1. 强制环境检测 ---
st.set_page_config(page_title="调试模式")
st.title("🛠️ 系统环境诊断")

# 检查 Tesseract 是否可用
tess_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe' # 请确保这是你的实际安装路径
pytesseract.pytesseract.tesseract_cmd = tess_path

st.subheader("第一步：环境检查")
if os.path.exists(tess_path):
    st.success(f"✅ 找到 Tesseract 引擎: {tess_path}")
    try:
        ver = pytesseract.get_tesseract_version()
        st.write(f"引擎版本: {ver}")
    except Exception as e:
        st.error(f"❌ 引擎无法运行: {e}")
else:
    st.error(f"❌ 未找到 Tesseract 引擎！请检查路径是否为: {tess_path}")

# --- 2. 顺序解析逻辑 (不再使用多线程/多进程) ---
DB_FILE = "processed_database.csv"

def simple_sync():
    if not os.path.exists("data"):
        os.makedirs("data")
        st.warning("data 文件夹为空")
        return pd.DataFrame()

    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in files if f not in processed]

    if new_files:
        st.subheader("第二步：逐步解析文件")
        new_data = []
        for f in new_files:
            st.write(f"正在处理: {f} ...")
            try:
                # 顺序处理，一个一个来
                df_item = process_document_to_dataframe(os.path.join("data", f))
                if not df_item.empty:
                    df_item['来源文件'] = f
                    new_data.append(df_item)
                    st.write(f"✅ {f} 解析成功")
            except Exception as e:
                st.error(f"❌ {f} 解析崩溃! 错误详情: {e}")
                # 即使一个错，也继续下一个
                continue
        
        if new_data:
            combined = pd.concat([db_df] + new_data, ignore_index=True)
            combined.to_csv(DB_FILE, index=False)
            st.success("所有文件处理完毕！")
            return combined
    return db_df

# 运行同步
df = simple_sync()

if not df.empty:
    st.subheader("第三步：数据显示")
    st.dataframe(df.head(20))
