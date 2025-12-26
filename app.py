import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级 CSS 美化 ---
st.set_page_config(page_title="法规标准智慧工作站", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    /* 全局背景与字体 */
    .stApp { background-color: #f4f7f9; }
    
    /* 顶部横幅 */
    .header-banner {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* 统计卡片 */
    .metric-container {
        background: white;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* 条款卡片美化 */
    .clause-card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        border-left: 6px solid #3b82f6;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    .clause-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    }
    
    /* 跳转高亮状态 */
    .highlight-active {
        border-left: 6px solid #f59e0b !important;
        background-color: #fffbeb !important;
    }

    /* 标签与参数样式 */
    .std-badge {
        background: #dbeafe;
        color: #1e40af;
        padding: 4px 12px;
        border-radius: 50px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
    }
    .param-tag {
        background: #ecfdf5;
        color: #065f46;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #a7f3d0;
        font-family: monospace;
        font-weight: bold;
    }
    
    /* 搜索框图标与间距 */
    .search-area { margin-bottom: 30px; }
    
    /* 自定义侧边栏按钮 */
    .stButton>button {
        border-radius: 8px;
        text-align: left;
        padding: 5px 15px;
        background-color: transparent;
        border: 1px solid transparent;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 增量同步逻辑 (DB_FILE 管理) ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        new_entries = []
        with st.status("🚀 正在同步标准库...", expanded=True) as status:
            for f in new_files:
                st.write(f"正在解析: {f}")
                df_item = process_document_to_dataframe(os.path.join("data", f))
                if not df_item.empty:
                    df_item['来源文件'] = f
                    new_entries.append(df_item)
            if new_entries:
                db_df = pd.concat([db_df, pd.concat(new_entries)], ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
            status.update(label="✅ 同步完成", state="complete", expanded=False)
    return db_df

df = sync_database()

# --- 3. 侧边栏设计 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/law.png", width=60)
    st.title("工作站控制台")
    
    if not df.empty:
        std_list = list(df['标准号'].unique())
        selected_std = st.selectbox("📂 选择查阅标准", std_list)
        
        st.markdown("### 📍 章节快速索引")
        toc_df = df[df['标准号'] == selected_std]
        # 创建更美观的目录树列表
        for idx, row in toc_df.iterrows():
            if st.button(f"▫️ 条款 {row['条款号']}", key=f"toc_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    
    st.divider()
    st.write("💾 **数据备份**")
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button(
                label="📥 下载解析后的数据库 (CSV)",
                data=file,
                file_name="processed_database.csv",
                mime="text/csv",
                use_container_width=True
            )

    with st.expander("🛠️ 管理员工具"):
        if st.checkbox("授权重置权限"):
            if st.button("🔥 清空并全库重扫", type="primary"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.cache_data.clear()
                st.rerun()

# --- 4. 主界面：顶部 Dashboard ---
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准智慧化数字化查阅平台</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>基于 OCR 与结构化解析的技术标准工作站</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-container"><small>标准总数</small><br><b>{len(df["标准号"].unique())}</b></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-container"><small>条款总计</small><br><b>{len(df)}</b></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-container"><small>参数识别率</small><br><b>{len(df[df["技术参数"]!="见详情"])/len(df):.1%}</b></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-container"><small>系统状态</small><br><b style="color:#10b981;">运行良好</b></div>', unsafe_allow_html=True)

    st.markdown("<div class='search-area'></div>", unsafe_allow_html=True)
    search_input = st.text_input("🔍 智慧检索", placeholder="请输入关键字、条款号或标准编号...", label_visibility="collapsed")

    # --- 5. 核心逻辑：视图切换 ---
    if search_input:
        # 搜索模式
        st.subheader(f"🎯 检索匹配结果")
        results = df[(df['内容'].str.contains(search_input, case=False, na=False)) | (df['条款号'] == search_input)]
        
        if not results.empty:
            for _, row in results.iterrows():
                # 高亮逻辑
                highlighted_text = re.sub(f"({search_input})", r"<mark>\1</mark>", row['内容'], flags=re.IGNORECASE)
                st.markdown(f"""
                    <div class="clause-card">
                        <span class="std-badge">{row['标准号']}</span>
                        <div style="font-weight:bold; margin: 10px 0; color:#1e3a8a;">条款 {row['条款号']}</div>
                        <div style="color:#374151; line-height:1.7;">{highlighted_text}</div>
                        <div style="margin-top:15px;"><span class="param-tag">📊 核心参数: {row['技术参数']}</span></div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("未匹配到相关结果，请尝试简化关键词。")
    else:
        # 全文阅读模式
        st.subheader(f"📖 顺序查阅：{selected_std}")
        for _, row in toc_view.iterrows():
            is_target = st.session_state.get('jump_target') == row['条款号']
            card_class = "clause-card highlight-active" if is_target else "clause-card"
            
            st.markdown(f"""
                <div class="{card_class}">
                    <div style="font-weight:bold; color:#1e3a8a;">条款 {row['条款号']}</div>
                    <div style="margin-top:10px; color:#374151; line-height:1.7;">{row['内容']}</div>
                    <div style="margin-top:15px;"><span class="param-tag">📊 核心参数: {row['技术参数']}</span></div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("👋 欢迎使用！请在 data/ 文件夹中放入标准文件以启动解析。")
