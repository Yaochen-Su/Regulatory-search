import streamlit as st
import pandas as pd
import os
import re
import time
from processor import process_document_to_dataframe

# --- 1. 页面基础配置 ---
st.set_page_config(page_title="法规智慧工作站", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .header-banner {
        background: white; padding: 25px; border-bottom: 4px solid #1e40af;
        margin-bottom: 25px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .full-text-area {
        background: white; padding: 40px 60px; border-radius: 4px; line-height: 2.2;
        color: #1f2937; font-family: "SimSun", "STSong", serif; font-size: 1.1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;
    }
    .clause-card {
        background: white; padding: 25px; border-radius: 8px; border-left: 6px solid #2563eb;
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    mark { background: #fde047; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 侧边栏：优先渲染控制组件 ---
with st.sidebar:
    # A. Logo 修复
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    # B. 【强制清空按钮】置顶 - 确保无论解析是否报错都能看到
    st.error("系统维护工具")
    if st.button("🔥 强制清空并重置存档", type="primary", use_container_width=True):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.cache_data.clear()
        st.success("存档已清空，请刷新页面")
        st.stop()
    
    st.divider()
    
    # C. 下载按钮
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化库 (CSV)", data=file, file_name="law_db.csv", use_container_width=True)

    ocr_mode = st.toggle("🔍 强制 OCR 识别模式", value=False)

# --- 3. 核心同步逻辑 (防循环设计) ---
def sync_database(ocr_enabled):
    if not os.path.exists("data"): 
        os.makedirs("data")
        return pd.DataFrame()
    
    # 生成当前文件指纹库
    physical_files = {}
    for f in os.listdir("data"):
        if f.lower().endswith(('.pdf', '.docx')):
            p = os.path.join("data", f)
            # 唯一标识符：文件名 + 整数时间 + 大小
            fingerprint = f"{f}_{int(os.path.getmtime(p))}_{os.path.getsize(p)}"
            physical_files[f] = fingerprint

    # 加载现有数据库
    db_df = pd.DataFrame()
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            if '指纹' not in db_df.columns: db_df = pd.DataFrame()
        except:
            db_df = pd.DataFrame()

    # 确定待处理文件
    parsed_fingerprints = set(db_df['指纹'].unique()) if not db_df.empty else set()
    to_parse = [f for f, fp in physical_files.items() if fp not in parsed_fingerprints]

    if to_parse:
        new_entries = []
        with st.status(f"🚀 正在解析新文件 ({len(to_parse)})...") as status:
            for f in to_parse:
                st.write(f"正在处理: {f}")
                item_df = process_document_to_dataframe(os.path.join("data", f), ocr_enabled=ocr_enabled)
                if not item_df.empty:
                    item_df['来源文件'] = f
                    item_df['指纹'] = physical_files[f]
                    new_entries.append(item_df)
            
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.success("同步完成，请手动刷新页面或操作搜索")
        # 移除自动 rerun，改为通过交互触发界面更新
    
    return db_df

df = sync_database(ocr_mode)

# --- 4. 侧边栏后续：文件选择与索引 ---
with st.sidebar:
    if not df.empty:
        st.divider()
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择规章文件", std_list)
        
        st.markdown("### 📍 条文索引")
        toc_view = df[df['标准号'] == selected_std]
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.caption(f"📁 {row['章']}")
                last_chapter = row['章']
            if st.button(f"▫️ {row['编号']}", key=f"btn_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

# --- 5. 主界面渲染 ---
if not df.empty:
    st.markdown(f'<div class="header-banner"><h1>{selected_std}</h1></div>', unsafe_allow_html=True)
    
    query = st.text_input("🔍 检索条文...", placeholder="输入关键词或编号")
    current_law_df = df[df['标准号'] == selected_std]

    if query:
        # 搜索逻辑
        results = current_law_df[current_law_df['全文'].str.contains(query, case=False, na=False) | current_law_df['编号'].str.contains(query, na=False)]
        for _, row in results.iterrows():
            st.markdown(f'<div class="clause-card"><b>{row["编号"]}</b><br>{row["全文"]}</div>', unsafe_allow_html=True)
    elif st.session_state.get('jump_target'):
        # 跳转逻辑
        target = st.session_state.get('jump_target')
        row = current_law_df[current_law_df['编号'] == target].iloc[0]
        st.markdown(f'<div class="clause-card" style="border-left-color:orange;"><b>{row["编号"]}</b><br>{row["全文"]}</div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回全文"): st.session_state.jump_target = None; st.rerun()
    else:
        # 全文浏览
        full_html = ""
        last_chapter = ""
        for _, row in current_law_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f"<h3 style='text-align:center;'>{row['章']}</h3>"
                last_chapter = row['章']
            full_html += f"<p><b>{row['编号']}</b> {row['全文']}</p>"
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 正在扫描 data 文件夹，请稍候...")
