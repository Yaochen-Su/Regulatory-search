import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级 CSS 美化 (保留原设计) ---
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
        margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s;
    }
    .clause-card:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.1); }
    .highlight-active { border-left: 6px solid #f59e0b !important; background-color: #fffbeb !important; }
    .std-badge { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 50px; font-size: 0.75rem; font-weight: 700; }
    .param-tag { background: #ecfdf5; color: #065f46; padding: 4px 10px; border-radius: 6px; font-family: monospace; font-weight: bold; }
    .toc-item { padding: 10px; border-bottom: 1px solid #edf2f7; cursor: pointer; }
    .toc-item:hover { background-color: #f8fafc; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 增强型增量同步逻辑 ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            # 自动清理已物理删除的文件
            db_df = db_df[db_df['来源文件'].isin(current_files)]
        except Exception:
            db_df = pd.DataFrame()
    else:
        db_df = pd.DataFrame()

    processed_files = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    new_files = [f for f in current_files if f not in processed_files]

    if new_files:
        new_entries = []
        with st.status("🚀 正在数字化处理新标准...", expanded=True) as status:
            for f in new_files:
                st.write(f"解析中: {f}")
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
            status.update(label="✅ 库同步完成", state="complete", expanded=False)
    return db_df

df = sync_database()

# --- 3. 侧边栏：标准导航与快速索引 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/law.png", width=60)
    st.title("数字化控制台")
    
    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅标准", std_list)
        
        st.markdown("### 📍 章节快速索引")
        toc_df = df[df['标准号'] == selected_std]
        
        # 侧边栏快速跳转按钮
        for idx, row in toc_df.iterrows():
            if st.button(f"▫️ 条款 {row['条款号']}", key=f"sidebar_toc_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 下载数据库 (CSV)", data=file, file_name="standard_db.csv", use_container_width=True)

# --- 4. 主界面：搜索模式与目录展示 ---
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准智慧化数字化查阅平台</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>数字化章节索引 | 双模式智慧检索</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # Dashboard 指标显示
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-container"><small>标准总数</small><br><b>{len(df["标准号"].unique())}</b></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-container"><small>条款总计</small><br><b>{len(df)}</b></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-container"><small>参数识别率</small><br><b>{len(df[df["技术参数"]!="见详情内容"])/len(df):.1%}</b></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-container"><small>同步状态</small><br><b style="color:#10b981;">已就绪</b></div>', unsafe_allow_html=True)

    # 搜索功能区：增加模糊/精准切换
    st.write("")
    s_col1, s_col2 = st.columns([4, 1])
    with s_col1:
        search_query = st.text_input("🔍 搜索标准内容或条款号...", placeholder="例如：跌落、5.6.1、MPa...", label_visibility="collapsed")
    with s_col2:
        search_mode = st.toggle("精准模式", value=False, help="开启后将完全匹配条款号或特定短语")

    # --- 核心逻辑：搜索结果 vs 数字化目录页 ---
    if search_query:
        st.subheader(f"🎯 搜索结果")
        if search_mode:
            # 精准搜索：完全匹配条款号或使用正则边界匹配单词
            results = df[
                (df['条款号'].str.fullmatch(search_query, na=False)) | 
                (df['内容'].str.contains(rf'\b{re.escape(search_query)}\b', case=False, na=False))
            ]
        else:
            # 模糊搜索：包含关键词即可
            results = df[(df['内容'].str.contains(search_query, case=False, na=False)) | (df['条款号'].str.contains(search_query, na=False))]
        
        if not results.empty:
            for _, row in results.iterrows():
                highlight = re.sub(f"({re.escape(search_query)})", r"<mark>\1</mark>", str(row['内容']), flags=re.IGNORECASE)
                st.markdown(f"""
                    <div class="clause-card">
                        <span class="std-badge">{row['标准号']}</span>
                        <div style="font-weight:bold; margin: 10px 0; color:#1e3a8a;">条款 {row['条款号']}</div>
                        <div style="color:#374151; line-height:1.7;">{highlight}</div>
                        <div style="margin-top:15px;"><span class="param-tag">📊 核心参数: {row['技术参数']}</span></div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("未找到匹配内容，请尝试模糊搜索。")
    else:
        # 【替换内容】：主界面在无搜索时，展示数字化的目录页（条款详情）
        st.subheader(f"📖 标准目录：{selected_std}")
        for _, row in toc_df.iterrows():
            # 检测是否是侧边栏选中的跳转目标
            is_jump = st.session_state.get('jump_target') == row['条款号']
            card_style = "clause-card highlight-active" if is_jump else "clause-card"
            
            st.markdown(f"""
                <div class="{card_style}" id="clause-{row['条款号']}">
                    <div style="font-weight:bold; color:#1e3a8a;">条款 {row['条款号']}</div>
                    <div style="margin-top:10px; color:#374151; line-height:1.7;">{row['内容']}</div>
                    <div style="margin-top:15px;"><span class="param-tag">📊 参数摘要: {row['技术参数']}</span></div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请在 data/ 文件夹中放入 Word 或 PDF 标准文件开始使用。")
