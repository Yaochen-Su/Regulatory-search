import streamlit as st
import pandas as pd
import os
import re
import time
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS ---
st.set_page_config(page_title="法规标准数字化查阅平台", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .header-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 30px; border-radius: 12px; color: white; margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center;
    }
    .metric-card {
        background: white; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb;
        text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-val { color: #1e40af; font-size: 1.6rem; font-weight: bold; }
    .full-text-area {
        background: white; padding: 40px; border-radius: 8px; line-height: 2.1;
        color: #1f2937; font-family: "SimSun", "STSong", serif; font-size: 1.05rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
    }
    .clause-block { margin-bottom: 25px; border-bottom: 1px solid #f3f4f6; padding-bottom: 15px; }
    .clause-no { color: #1e3a8a; font-weight: bold; margin-bottom: 8px; font-size: 1.1rem; }
    .tag-blue { background: #eff6ff; color: #1e40af; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; }
    .tag-green { background: #ecfdf5; color: #065f46; padding: 4px 12px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; }
    .keyword-pill { 
        background: #f3f4f6; color: #4b5563; padding: 2px 10px; border-radius: 50px; 
        font-size: 0.75rem; margin-right: 6px; border: 1px solid #d1d5db; display: inline-block;
    }
    mark { background-color: #fde047; font-weight: bold; padding: 0 2px; border-radius: 2px; color: black; }
    </style>
    """, unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 数据库同步引擎 ---
def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    db_df = pd.DataFrame()
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE).fillna("")
            db_df = db_df[db_df['来源文件'].isin(all_files)]
        except: db_df = pd.DataFrame()
    current_meta = {f: f"{f}_{int(os.path.getmtime(os.path.join('data', f)))}_{os.path.getsize(os.path.join('data', f))}" for f in all_files}
    parsed_fps = set(db_df['指纹'].unique()) if not db_df.empty else set()
    to_parse = [f for f, fp in current_meta.items() if fp not in parsed_fps]
    if to_parse:
        new_entries = []
        with st.status(f"🚀 数字化同步中 (剩余 {len(to_parse)})..."):
            for f in to_parse:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'], item_df['指纹'] = f, current_meta[f]
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True).fillna("")
                db_df.to_csv(DB_FILE, index=False)
                st.rerun()
    return db_df

df = sync_database()

# --- 3. 侧边栏 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    if st.button("🔥 强制重置全库存档", type="primary", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.cache_data.clear()
        st.rerun()
    st.divider()
    if not df.empty:
        display_list = sorted(list(df['展示名称'].unique()))
        selected_display = st.selectbox("📂 当前查阅规章", display_list)
        current_df = df[df['展示名称'] == selected_display]
        st.info(f"📍 **版本**: {current_df['版本'].iloc[0] or '正式版'}")
        st.success(f"📅 **实施日期**: {current_df['实施日期'].iloc[0] or '待核实'}")

# --- 4. 主界面：看板与搜索 ---
st.markdown('<div class="header-banner"><h1>法规标准智慧化数字化查阅平台</h1></div>', unsafe_allow_html=True)

if not df.empty:
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-card"><small>总规章数</small><div class="metric-val">{len(df["标准号"].unique())}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-card"><small>总条文数</small><div class="metric-val">{len(df)}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-card"><small>参数识别量</small><div class="metric-val">{len(df[df["关键词"] != ""])}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="metric-card"><small>系统状态</small><div class="metric-val" style="color:#10b981;">运行良好</div></div>', unsafe_allow_html=True)

    st.write("")
    
    # 【需求升级】：搜索区域增加模式切换
    search_col, mode_col = st.columns([4, 1])
    with search_col:
        query = st.text_input("🔍 智慧检索", placeholder="支持多关键词模糊匹配...", label_visibility="collapsed")
    with mode_col:
        is_fuzzy = st.checkbox("模糊搜索", value=True, help="开启后：搜索'医疗管理'可匹配'医疗器械监督管理'")

    if query:
        st.subheader(f"🎯 检索结果：'{query}'")
        
        # --- 模糊搜索核心逻辑 ---
        if is_fuzzy:
            # 1. 拆分关键词
            keywords = [k.strip() for k in query.replace(' ', ',').replace('，', ',').split(',') if k.strip()]
            # 2. 构建前瞻匹配正则：(?=.*词1)(?=.*词2)
            fuzzy_pattern = "".join([f"(?=.*{re.escape(k)})" for k in keywords])
            res = current_df[current_df['全文'].str.contains(fuzzy_pattern, case=False, na=False, regex=True)]
        else:
            # 精准搜索模式
            res = current_df[current_df['全文'].str.contains(query, case=False, na=False) | current_df['编号'].str.contains(query, na=False)]
        
        if not res.empty:
            for _, row in res.iterrows():
                text = str(row['全文'])
                no = str(row['编号'])
                
                # 【多词高亮逻辑】：模糊模式下高亮所有拆分的词，精准模式高亮全词
                words_to_highlight = keywords if is_fuzzy else [query]
                for w in words_to_highlight:
                    text = re.sub(f"({re.escape(w)})", r"<mark>\1</mark>", text, flags=re.IGNORECASE)
                    no = re.sub(f"({re.escape(w)})", r"<mark>\1</mark>", no, flags=re.IGNORECASE)
                
                st.markdown(f'<div class="clause-block"><div class="clause-no">{no}</div><div>{text}</div></div>', unsafe_allow_html=True)
        else:
            st.warning("未找到匹配内容。")
    else:
        # 默认全文展示逻辑 (保持不变)
        st.subheader(f"📖 {selected_display}")
        st.markdown(f'<div style="display:flex; gap:15px; margin-bottom:25px;"><span class="tag-blue">发布日期：{current_df["发布日期"].iloc[0] or "待核实"}</span><span class="tag-green">实施日期：{current_df["实施日期"].iloc[0] or "待核实"}</span></div>', unsafe_allow_html=True)
        full_html = ""
        last_chapter = ""
        for _, row in current_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f'<h3 style="color:#1e40af; border-bottom:2px solid #e5e7eb; padding-bottom:10px; margin-top:35px;">{row["章"]}</h3>'
                last_chapter = row['章']
            keywords_tags = [k.strip() for k in str(row['关键词']).split(',') if k.strip() and k.lower() != 'nan']
            keyword_html = "".join([f'<span class="keyword-pill">{k}</span>' for k in keywords_tags])
            full_html += f'<div class="clause-block"><div class="clause-no">{row["编号"]}</div><div style="color:#374151;">{row["全文"]}</div>'
            if keyword_html: full_html += f'<div style="margin-top:10px;">{keyword_html}</div>'
            full_html += '</div>'
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请在 data/ 文件夹中放入文件开始同步。")
