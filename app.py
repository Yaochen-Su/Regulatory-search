import streamlit as st
import pandas as pd
import os
import re
import time
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级 CSS (保持政府门户风格) ---
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
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 侧边栏：紧急重置与诊断工具 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    # 【置顶重置】
    if st.button("🔥 强制清空并重扫全库", type="primary", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    # 【文件诊断器】：让你知道系统看到了多少文件
    if not os.path.exists("data"): os.makedirs("data")
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    st.write(f"📁 文件夹检测到: **{len(all_files)}** 份文件")
    with st.expander("🔍 查看文件列表"):
        for f in all_files: st.write(f"• {f}")

# --- 3. 核心同步逻辑 (增强 ID 独立性) ---
def sync_database():
    # 建立指纹库
    physical_files = {}
    for f in all_files:
        p = os.path.join("data", f)
        # 强制指纹包含文件名，防止内容相似导致合并
        fingerprint = f"{f}_{int(os.path.getmtime(p))}_{os.path.getsize(p)}"
        physical_files[f] = fingerprint

    # 加载数据库
    db_df = pd.DataFrame()
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            # 清理数据库中已不存在的物理文件
            db_df = db_df[db_df['来源文件'].isin(all_files)]
        except:
            db_df = pd.DataFrame()

    parsed_fingerprints = set(db_df['指纹'].unique()) if not db_df.empty else set()
    to_parse = [f for f, fp in physical_files.items() if fp not in parsed_fingerprints]

    if to_parse:
        new_entries = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, f in enumerate(to_parse):
            status_text.text(f"🚀 正在解析 ({i+1}/{len(to_parse)}): {f}")
            # 传入文件名作为备份 ID
            item_df = process_document_to_dataframe(os.path.join("data", f))
            if not item_df.empty:
                item_df['来源文件'] = f
                item_df['指纹'] = physical_files[f]
                # 强制增加一个展示名称，避免多文件同名
                if '展示名称' not in item_df.columns:
                    item_df['展示名称'] = f"{item_df['标准号'].iloc[0]} ({f})"
                new_entries.append(item_df)
            progress_bar.progress((i + 1) / len(to_parse))
        
        if new_entries:
            db_df = pd.concat([db_df] + new_entries, ignore_index=True)
            db_df.to_csv(DB_FILE, index=False)
            st.success("同步已完成！请在下方选择文件查看。")
            time.sleep(1)
            st.rerun()
    
    return db_df

df = sync_database()

# --- 4. 侧边栏：文件选择 (修复 12 份文件不显示的 Bug) ---
with st.sidebar:
    if not df.empty:
        st.divider()
        # 按照“展示名称”列进行选择，确保每份文件独立
        display_list = sorted(list(df['展示名称'].unique()))
        selected_display = st.selectbox("📂 选择查阅规章", display_list)
        
        # 获取选中的 DataFrame
        current_df = df[df['展示名称'] == selected_display]
        
        st.markdown("### 📍 编号快速索引")
        for idx, row in current_df.iterrows():
            # 使用唯一 Key 避免冲突
            if st.button(f"▫️ {row['编号']}", key=f"btn_{idx}_{row['指纹'][:8]}", use_container_width=True):
                st.session_state.jump_target = row['编号']
    else:
        st.warning("⚠️ 暂无解析成功的数据，请检查 data 文件夹。")

# --- 5. 主界面渲染 ---
if not df.empty and 'selected_display' in locals():
    st.markdown(f'<div class="header-banner"><h1>{selected_display}</h1></div>', unsafe_allow_html=True)
    
    query = st.text_input("🔍 智慧检索关键词...", placeholder="输入内容后回车")
    
    if query:
        # 搜索结果
        results = current_df[current_df['全文'].str.contains(query, case=False, na=False) | current_df['编号'].str.contains(query, na=False)]
        for _, row in results.iterrows():
            st.markdown(f'<div class="clause-card"><b>{row["编号"]}</b><br>{row["全文"]}</div>', unsafe_allow_html=True)
    elif st.session_state.get('jump_target'):
        # 跳转详情
        target = st.session_state.get('jump_target')
        # 确保只选当前文件的条目
        match = current_df[current_df['编号'] == target]
        if not match.empty:
            row = match.iloc[0]
            st.markdown(f'<div class="clause-card" style="border-left-color:orange;"><b>{row["编号"]}</b><br>{row["全文"]}</div>', unsafe_allow_html=True)
            if st.button("⬅️ 返回全文内容"):
                st.session_state.jump_target = None
                st.rerun()
    else:
        # 默认全文浏览
        full_html = ""
        last_chapter = ""
        for _, row in current_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f"<h3 style='text-align:center; color:#1e40af; margin-top:30px;'>{row['章']}</h3>"
                last_chapter = row['章']
            full_html += f"<p><b>{row['编号']}</b> {row['全文']}</p>"
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请确保 data 文件夹中有 PDF 或 DOCX 文件，系统将自动开始数字化解析。")
