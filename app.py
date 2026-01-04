import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级 CSS 美化 ---
st.set_page_config(page_title="法规标准智慧工作站", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .header-banner {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 20px; border-radius: 12px; color: white; margin-bottom: 25px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-container {
        background: white; padding: 15px; border-radius: 10px; border: 1px solid #e5e7eb;
        text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .clause-card {
        background: white; padding: 25px; border-radius: 12px; border-left: 6px solid #3b82f6;
        margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .full-text-container {
        background: white; padding: 40px; border-radius: 12px; line-height: 1.8; color: #334155;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); white-space: pre-wrap;
    }
    .std-badge { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 50px; font-size: 0.75rem; font-weight: 700; }
    .param-tag { background: #ecfdf5; color: #065f46; padding: 4px 10px; border-radius: 6px; font-family: monospace; font-weight: bold; }
    mark { background: #fde047; font-weight: bold; padding: 0 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库同步逻辑 ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            db_df = db_df[db_df['来源文件'].isin(current_files)]
        except: db_df = pd.DataFrame()
    else: db_df = pd.DataFrame()

    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        new_entries = []
        with st.status("🚀 正在数字化处理新标准...", expanded=True):
            for f in new_files:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
    return db_df

df = sync_database()

# --- 3. 侧边栏：布局重整 ---
with st.sidebar:
    # 修复 Logo 显示 (使用更稳定的图标源)
    st.markdown(f'<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    # 【需求：下载数据库放在最上面】
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 下载解析库 (CSV)", data=file, file_name="standard_db.csv", use_container_width=True)
    st.divider()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        # 标准切换时重置跳转目标
        if 'last_std' not in st.session_state: st.session_state.last_std = std_list[0]
        selected_std = st.selectbox("📂 选择查阅标准", std_list)
        if selected_std != st.session_state.last_std:
            st.session_state.jump_target = None
            st.session_state.last_std = selected_std

        st.markdown("### 📍 章节快速索引")
        toc_df = df[df['标准号'] == selected_std]
        # 章节点击逻辑
        for idx, row in toc_df.iterrows():
            if st.button(f"▫️ 条款 {row['条款号']}", key=f"btn_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
                # 点击条款时清空搜索框 (通过 experimental_rerun 实现比较复杂，这里采用逻辑覆盖)
    
    st.divider()
    with st.expander("🛠️ 管理员工具"):
        if st.checkbox("重置数据库权限"):
            if st.button("🔥 彻底清除并重扫", type="primary"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.cache_data.clear()
                st.rerun()

# --- 4. 主界面：智慧检索与内容分流 ---
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准智慧化数字化查阅平台</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>全文通读模式 | 数字化章节索引 | 智慧检索</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 统计 Dashboard
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-container"><small>标准总数</small><br><b>{len(df["标准号"].unique())}</b></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-container"><small>条款总计</small><br><b>{len(df)}</b></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-container"><small>参数识别率</small><br><b>{len(df[df["技术参数"]!="见详情内容"])/len(df):.1%}</b></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-container"><small>状态</small><br><b style="color:#10b981;">已就绪</b></div>', unsafe_allow_html=True)

    # 搜索区
    st.write("")
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        search_query = st.text_input("🔍 输入搜索关键词...", placeholder="搜索后将单独显示相应条款内容...", label_visibility="collapsed")
    with sc2:
        search_mode = st.toggle("精准模式", value=False)

    # --- 核心内容展示逻辑 ---
    if search_query:
        # A. 搜索模式：显示搜索结果卡片
        st.subheader("🎯 搜索结果")
        if search_mode:
            results = df[(df['条款号'].str.fullmatch(search_query, na=False)) | (df['内容'].str.contains(rf'\b{re.escape(search_query)}\b', case=False, na=False))]
        else:
            results = df[(df['内容'].str.contains(search_query, case=False, na=False)) | (df['条款号'].str.contains(search_query, na=False))]
        
        if not results.empty:
            for _, row in results.iterrows():
                highlight = re.sub(f"({re.escape(search_query)})", r"<mark>\1</mark>", str(row['内容']), flags=re.IGNORECASE)
                st.markdown(f'<div class="clause-card"><span class="std-badge">{row["标准号"]}</span><div style="font-weight:bold; margin: 10px 0; color:#1e3a8a;">条款 {row["条款号"]}</div><div style="color:#374151; line-height:1.7;">{highlight}</div><div style="margin-top:15px;"><span class="param-tag">📊 核心参数: {row["技术参数"]}</span></div></div>', unsafe_allow_html=True)
        else: st.warning("未找到匹配内容。")

    elif st.session_state.get('jump_target'):
        # B. 条款选中模式：单独显示选中的条款内容
        target = st.session_state.get('jump_target')
        st.subheader(f"📍 条款详情: {target}")
        item = toc_df[toc_df['条款号'] == target]
        if not item.empty:
            row = item.iloc[0]
            st.markdown(f'<div class="clause-card" style="border-left: 6px solid #f59e0b; background-color: #fffbeb;"><span class="std-badge">{row["标准号"]}</span><div style="font-weight:bold; margin: 10px 0; color:#1e3a8a;">条款 {row["条款号"]}</div><div style="color:#374151; line-height:1.8; font-size:1.1rem;">{row["内容"]}</div><div style="margin-top:20px;"><span class="param-tag">📊 参数摘要: {row["技术参数"]}</span></div></div>', unsafe_allow_html=True)
            if st.button("⬅️ 返回显示全文"):
                st.session_state.jump_target = None
                st.rerun()
    
    else:
        # C. 初始/全文模式：显示标准全文内容
        st.subheader(f"📖 标准全文阅读: {selected_std}")
        # 拼接该标准下所有条款内容形成“全文”
        full_text_content = ""
        for _, row in toc_df.iterrows():
            full_text_content += f"### 条款 {row['条款号']}\n{row['内容']}\n\n"
        
        st.markdown(f'<div class="full-text-container">{full_text_content}</div>', unsafe_allow_html=True)

else:
    st.info("👋 库为空。请在 data/ 文件夹中放入文件。")
