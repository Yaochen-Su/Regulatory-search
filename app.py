import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS 美化 (仿照图片门户风格) ---
st.set_page_config(page_title="法规标准查阅平台", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .header-banner {
        background: #ffffff; padding: 20px; border-bottom: 3px solid #1e3a8a;
        margin-bottom: 20px; text-align: center;
    }
    .full-text-area {
        background: white; padding: 50px; border-radius: 4px; line-height: 2;
        color: #1a1a1a; font-family: "Microsoft YaHei", sans-serif;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .clause-card {
        background: white; padding: 20px; border-radius: 8px; border-left: 5px solid #2563eb;
        margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .chapter-header { background: #eef2ff; padding: 10px; font-weight: bold; color: #1e40af; border-radius: 4px; margin-top: 20px; }
    mark { background: #fde047; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库同步逻辑 ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    if not db_df.empty:
        db_df = db_df[db_df['来源文件'].isin(current_files)]
    
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        new_entries = []
        with st.status("🚀 正在解析新规章...", expanded=True):
            for f in new_files:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
    return db_df

df = sync_database()

# --- 3. 侧边栏布局 (下载置顶 + Logo) ---
with st.sidebar:
    # 修复 Logo
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("法规文件中心")
    
    # 1. 下载按钮置顶
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化库 (CSV)", data=file, file_name="law_database.csv", use_container_width=True)
    st.divider()

    # 2. 选择规章
    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅规章", std_list)
        
        st.markdown("### 📍 章节索引")
        toc_view = df[df['标准号'] == selected_std]
        
        # 树状章节索引
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.info(f"📁 {row['章']}")
                last_chapter = row['章']
            # 使用唯一 Key 解决 DuplicateElementKey 报错
            if st.button(f"▫️ {row['编号']}", key=f"side_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']
                st.session_state.search_mode = False

    st.divider()
    if st.button("🔥 重置系统内容"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

# --- 4. 主界面：展示原文与检索 ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; color:#1e3a8a;'>{selected_std if not df.empty else "请选择文件"}</h1>
        <p style='color:#64748b;'>当前位置：首页 > 法规文件 > {selected_std if not df.empty else ""}</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 搜索条
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        query = st.text_input("🔍 模糊搜索关键词或精准输入条款编号（如：第一条）", placeholder="输入搜索内容...", label_visibility="collapsed")
    with sc2:
        precise = st.toggle("精准匹配", value=False)

    current_law_df = df[df['标准号'] == selected_std]

    # --- 内容渲染逻辑 ---
    if query:
        # A. 搜索结果模式
        st.subheader("🎯 检索匹配结果")
        if precise:
            results = current_law_df[current_law_df['编号'] == query]
        else:
            results = current_law_df[current_law_df['全文'].str.contains(query, case=False, na=False) | current_law_df['编号'].str.contains(query, na=False)]
        
        if not results.empty:
            for idx, row in results.iterrows():
                highlight = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['全文']), flags=re.IGNORECASE)
                st.markdown(f'<div class="clause-card"><div class="std-badge">{row["章"]}</div><div style="font-weight:bold; margin:10px 0;">{row["编号"]}</div><div>{highlight}</div></div>', unsafe_allow_html=True)
        else: st.warning("未找到匹配内容。")

    elif st.session_state.get('jump_target'):
        # B. 条款点击模式
        target = st.session_state.get('jump_target')
        st.subheader(f"📍 条款详情: {target}")
        row = current_law_df[current_law_df['编号'] == target].iloc[0]
        st.markdown(f'<div class="clause-card" style="border-left-color:#f59e0b;"><div class="chapter-header">{row["章"]}</div><div style="font-weight:bold; margin:15px 0; font-size:1.2rem;">{row["编号"]}</div><div style="font-size:1.1rem; line-height:1.8;">{row["全文"]}</div><div style="margin-top:20px;"><small>📊 提取参数: {row["技术参数"]}</small></div></div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回显示原文全文"):
            st.session_state.jump_target = None
            st.rerun()

    else:
        # C. 默认原文浏览模式
        st.subheader("📖 法规原文浏览")
        full_doc_html = f"<center><h2>{selected_std}</h2></center><hr>"
        last_chapter = ""
        for idx, row in current_law_df.iterrows():
            if row['章'] != last_chapter:
                full_doc_html += f'<div class="chapter-header" style="text-align:center; margin:30px 0;">{row["章"]}</div>'
                last_chapter = row['章']
            full_doc_html += f'<p><b>{row["编号"]}</b> {row["全文"]}</p>'
        
        st.markdown(f'<div class="full-text-area">{full_doc_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请将法规 PDF 或 Word 放入 data 文件夹开始使用。")import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS 美化 (仿照图片门户风格) ---
st.set_page_config(page_title="法规标准查阅平台", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f0f2f5; }
    .header-banner {
        background: #ffffff; padding: 20px; border-bottom: 3px solid #1e3a8a;
        margin-bottom: 20px; text-align: center;
    }
    .full-text-area {
        background: white; padding: 50px; border-radius: 4px; line-height: 2;
        color: #1a1a1a; font-family: "Microsoft YaHei", sans-serif;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .clause-card {
        background: white; padding: 20px; border-radius: 8px; border-left: 5px solid #2563eb;
        margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .chapter-header { background: #eef2ff; padding: 10px; font-weight: bold; color: #1e40af; border-radius: 4px; margin-top: 20px; }
    mark { background: #fde047; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库同步逻辑 ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    if not db_df.empty:
        db_df = db_df[db_df['来源文件'].isin(current_files)]
    
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        new_entries = []
        with st.status("🚀 正在解析新规章...", expanded=True):
            for f in new_files:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
    return db_df

df = sync_database()

# --- 3. 侧边栏布局 (下载置顶 + Logo) ---
with st.sidebar:
    # 修复 Logo
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("法规文件中心")
    
    # 1. 下载按钮置顶
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化库 (CSV)", data=file, file_name="law_database.csv", use_container_width=True)
    st.divider()

    # 2. 选择规章
    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅规章", std_list)
        
        st.markdown("### 📍 章节索引")
        toc_view = df[df['标准号'] == selected_std]
        
        # 树状章节索引
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.info(f"📁 {row['章']}")
                last_chapter = row['章']
            # 使用唯一 Key 解决 DuplicateElementKey 报错
            if st.button(f"▫️ {row['编号']}", key=f"side_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']
                st.session_state.search_mode = False

    st.divider()
    if st.button("🔥 重置系统内容"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

# --- 4. 主界面：展示原文与检索 ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; color:#1e3a8a;'>{selected_std if not df.empty else "请选择文件"}</h1>
        <p style='color:#64748b;'>当前位置：首页 > 法规文件 > {selected_std if not df.empty else ""}</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 搜索条
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        query = st.text_input("🔍 模糊搜索关键词或精准输入条款编号（如：第一条）", placeholder="输入搜索内容...", label_visibility="collapsed")
    with sc2:
        precise = st.toggle("精准匹配", value=False)

    current_law_df = df[df['标准号'] == selected_std]

    # --- 内容渲染逻辑 ---
    if query:
        # A. 搜索结果模式
        st.subheader("🎯 检索匹配结果")
        if precise:
            results = current_law_df[current_law_df['编号'] == query]
        else:
            results = current_law_df[current_law_df['全文'].str.contains(query, case=False, na=False) | current_law_df['编号'].str.contains(query, na=False)]
        
        if not results.empty:
            for idx, row in results.iterrows():
                highlight = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['全文']), flags=re.IGNORECASE)
                st.markdown(f'<div class="clause-card"><div class="std-badge">{row["章"]}</div><div style="font-weight:bold; margin:10px 0;">{row["编号"]}</div><div>{highlight}</div></div>', unsafe_allow_html=True)
        else: st.warning("未找到匹配内容。")

    elif st.session_state.get('jump_target'):
        # B. 条款点击模式
        target = st.session_state.get('jump_target')
        st.subheader(f"📍 条款详情: {target}")
        row = current_law_df[current_law_df['编号'] == target].iloc[0]
        st.markdown(f'<div class="clause-card" style="border-left-color:#f59e0b;"><div class="chapter-header">{row["章"]}</div><div style="font-weight:bold; margin:15px 0; font-size:1.2rem;">{row["编号"]}</div><div style="font-size:1.1rem; line-height:1.8;">{row["全文"]}</div><div style="margin-top:20px;"><small>📊 提取参数: {row["技术参数"]}</small></div></div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回显示原文全文"):
            st.session_state.jump_target = None
            st.rerun()

    else:
        # C. 默认原文浏览模式
        st.subheader("📖 法规原文浏览")
        full_doc_html = f"<center><h2>{selected_std}</h2></center><hr>"
        last_chapter = ""
        for idx, row in current_law_df.iterrows():
            if row['章'] != last_chapter:
                full_doc_html += f'<div class="chapter-header" style="text-align:center; margin:30px 0;">{row["章"]}</div>'
                last_chapter = row['章']
            full_doc_html += f'<p><b>{row["编号"]}</b> {row["全文"]}</p>'
        
        st.markdown(f'<div class="full-text-area">{full_doc_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请将法规 PDF 或 Word 放入 data 文件夹开始使用。")
