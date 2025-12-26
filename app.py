import streamlit as st
import pandas as pd
import os
import re
from concurrent.futures import ProcessPoolExecutor, as_completed
from processor import process_document_to_dataframe

# --- 配置 ---
DB_FILE = "processed_database.csv"

# --- 1. 将同步逻辑封装，并增加异常捕获 ---
def run_sync():
    if not os.path.exists("data"):
        os.makedirs("data")
        return pd.DataFrame()

    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed_files = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in all_files if f not in processed_files]

    if new_files:
        st.info(f"正在准备解析 {len(new_files)} 份新文件...")
        new_entries = []
        
        # 调试建议：如果依然报错，先将 max_workers 改为 1
        # 在 Windows 上，Streamlit 运行多进程有时不稳定
        with ProcessPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(process_document_to_dataframe, os.path.join("data", f)): f 
                for f in new_files
            }
            
            pbar = st.progress(0)
            for i, future in enumerate(as_completed(futures)):
                fname = futures[future]
                try:
                    df_item = future.result()
                    if df_item is not None and not df_item.empty:
                        df_item['来源文件'] = fname
                        new_entries.append(df_item)
                except Exception as e:
                    st.error(f"解析 {fname} 时发生错误: {e}")
                pbar.progress((i + 1) / len(new_files))

        if new_entries:
            new_df = pd.concat(new_entries, ignore_index=True)
            db_df = pd.concat([db_df, new_df], ignore_index=True)
            db_df.to_csv(DB_FILE, index=False)
            st.cache_data.clear()
            st.success("同步完成！")
    
    return db_df

# --- 2. 主页面渲染 ---
def main():
    st.set_page_config(page_title="标准数字化系统", layout="wide")
    
    # 标题等 UI
    st.title("⚖️ 数字化规程查阅平台")

    # 执行同步
    try:
        df = run_sync()
    except Exception as e:
        st.error(f"致命错误：{e}")
        st.stop() # 停止运行，防止报错刷屏

    # ... 这里放你之前的搜索和展示逻辑 ...
    if not df.empty:
        st.write(f"当前库内共有 {len(df)} 条记录")
        # 搜索框等...

# --- 3. 核心修复：Windows 入口保护 ---
if __name__ == '__main__':
    main()
