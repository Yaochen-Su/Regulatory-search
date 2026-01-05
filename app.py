import streamlit as st
import pandas as pd
import os
import re
import time
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级美化 ---
st.set_page_config(page_title="法规标准数字化查阅平台", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; }
    /* 顶部横幅 */
    .header-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 30px; border-radius: 15px; color: white; margin-bottom: 30px;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    /* 统计看板 */
    .metric-card {
        background: white; padding: 20px; border-radius: 12px; border: 1px solid #e5e7eb;
        text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .metric-val { color: #1e40af; font-size: 1.8rem; font-weight: bold; }
    /* 法规卡片 */
    .clause-card {
        background: white; padding: 30px; border-radius: 12px; border-left: 6px solid #2563eb;
        margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .tag-blue { background: #dbeafe; color: #1e40af; padding: 3px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; margin-right: 5px; }
    .tag-green { background: #d1fae5; color: #065f46; padding: 3px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; }
    .keyword-pill { background: #f3f4f6; border: 1px solid #d1d5db; color: #374151; padding: 2px 8px; border-radius: 50px; font-size: 0.75rem; margin-right: 5px; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 数据引擎 ---
def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    
    db_df = pd.DataFrame()
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            db_df = db_df[db_df['来源文件'].isin(all_files)]
        except: db_df = pd.DataFrame()

    current_meta = {f: f"{f}_{int(os.path.getmtime(os.path.join('data', f)))}_{os.path.getsize(os.path.join('data', f))}" for f in all_files}
    parsed_fps = set(db_df['指纹'].unique()) if not db_df.empty else set()
    to_parse = [f for f, fp in current_meta.items() if fp not in parsed_fps]

    if to_parse:
        new_entries = []
        with st.status(f"🚀 数字化同步中 (剩余 {len(to_parse)})...", expanded=True):
            for f in to_parse:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'], item_df['指纹'] = f, current_meta[f]
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.rerun()
    return db_df

df = sync_database()

# --- 3. 侧边栏 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    if st.button("🔥 强制重置数字化全库", type="primary", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    if not df.empty:
        display_list = sorted(list(df['展示名称'].unique()))
        selected_display = st.selectbox("📂 当前查阅规章", display_list)
        current_df = df[df['展示名称'] == selected_display]
        
        # 显示当前文件的基础信息
        st.info(f"📍 **版本**: {current_df['版本'].iloc[0]}")
        st.success(f"📅 **实施日期**: {current_df['实施日期'].iloc[0]}")

# --- 4. 主界面：数字化看板 ---
st.markdown('<div class="header-banner"><h1>法规标准智慧化数字化查阅平台</h1></div>', unsafe_allow_html=True)

if not df.empty:
    # 看板统计
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><small>总规章数</small><div class="metric-val">{len(df["标准号"].unique())}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><small>总条文数</small><div class="metric-val">{len(df)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><small>参数识别量</small><div class="metric-val">{len(df[df["关键词"]!=""])}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><small>系统状态</small><div class="metric-val" style="color:#10b981;">运行良好</div></div>', unsafe_allow_html=True)

    st.write("")
    query = st.text_input("🔍 智慧搜索", placeholder="输入关键词、条文编号或技术参数 (如: 0.5mm)...")

    # --- 5. 内容展示 (总分总结构) ---
    if query:
        st.subheader("🎯 检索结果")
        res = current_df[current_df['全文'].str.contains(query, case=False, na=False) | current_df['编号'].str.contains(query, na=False)]
        for _, row in res.iterrows():
            st.markdown(f'<div class="clause-card"><b>{row["编号"]}</b><br>{row["全文"]}</div>', unsafe_allow_html=True)
    else:
        # 显示规章详细页眉
        st.subheader(f"📖 {selected_display}")
        st.markdown(f"""
            <div style="display:flex; gap:10px; margin-bottom:20px;">
                <span class="tag-blue">发布: {current_df['发布日期'].iloc[0]}</span>
                <span class="tag-green">实施: {current_df['实施日期'].iloc[0]}</span>
                <span class="tag-blue">版本: {current_df['版本'].iloc[0]}</span>
            </div>
        """, unsafe_allow_html=True)

        full_html = ""
        last_chapter = ""
        for _, row in current_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f"<h3 style='color:#1e40af; border-bottom:1px solid #ddd; padding-bottom:10px; margin-top:30px;'>{row['章']}</h3>"
                last_chapter = row['章']
            
            # 生成关键词条标签
            keyword_html = "".join([f'<span class="keyword-pill">{k}</span>' for k in str(row['关键词']).split(', ') if k])
            
            full_html += f"""
                <div style="margin-bottom:20px;">
                    <div style="font-weight:bold; color:#1e3a8a;">{row['编号']}</div>
                    <div style="color:#334155; line-height:1.8;">{row['全文']}</div>
                    <div style="margin-top:8px;">{keyword_html}</div>
                </div>
            """
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！系统正在等待您在 data/ 文件夹中放入法规文件。")
