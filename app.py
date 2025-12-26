import streamlit as st
import pandas as pd
import os
import re
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
# 导入解析引擎
from processor import process_document_to_dataframe

# --- 1. 页面配置与 UI 样式 ---
st.set_page_config(page_title="法规标准智慧工作站", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .header-banner {
        background: linear-gradient(90deg, #0f172a 0%, #1e40af 100%);
        padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px;
    }
    .metric-card {
        background: white; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0;
        text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
    }
    .clause-card {
        background: white; padding: 20px; border-radius: 12px;
        border-left: 6px solid #2563eb; margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .highlight-active { border-left: 6px solid #f59e0b !important; background-color: #fffbeb !important; }
    .param-tag {
        background: #f0fdf4; color: #166534; padding: 3px 8px;
        border-radius: 6px; border: 1px solid #bbf7d0; font-weight: bold;
    }
    mark { background: #fde047; font-weight: bold; padding: 0 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心逻辑：并行增量同步 ---
DB_FILE = "processed_database.csv"

def sync_database_parallel():
    """使用多进程并行解析新文件"""
    if not os.path.exists("data"):
        os.makedirs("data")
        return pd.DataFrame()

    # 读取旧数据
    db_df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    processed_files = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    
    # 扫描文件夹
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    new_files = [f for f in all_files if f not in processed_files]

    if new_files:
        st.toast(f"检测到 {len(new_files)} 份新标准，启动并行加速解析...")
        new_entries = []
        
        with st.status("🚀 正在并行处理文档 (OCR 识别中)...", expanded=True) as status:
            # 获取 CPU 核心数，建议使用 4 个进程并行（兼顾速度与稳定性）
            # 在 Streamlit Cloud 上通常限制为 2-4 核
            with ProcessPoolExecutor(max_workers=4) as executor:
                # 提交所有任务
                future_to_file = {
                    executor.submit(process_document_to_dataframe, os.path.join("data", f)): f 
                    for f in new_files
                }
                
                progress_bar = st.progress(0)
                for i, future in enumerate(as_completed(future_to_file)):
                    fname = future_to_file[future]
                    try:
                        df_item = future.result()
                        if not df_item.empty:
                            df_item['来源文件'] = fname
                            new_entries.append(df_item)
                        st.write(f"✅ 已完成: {fname}")
                    except Exception as exc:
                        st.error(f"❌ {fname} 解析出错: {exc}")
                    
                    # 更新进度条
                    progress_bar.progress((i + 1) / len(new_files))

            if new_entries:
                new_combined = pd.concat(new_entries, ignore_index=True)
                db_df = pd.concat([db_df, new_combined], ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear() # 更新后清除缓存
                status.update(label="🎉 所有新标准解析完成！", state="complete", expanded=False)
            else:
                status.update(label="⚠️ 未能提取有效内容", state="error")

    return db_df

# 加载数据
df = sync_database_parallel()

# --- 3. 侧边栏：目录与管理 ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/briefcase.png", width=60)
    st.title("控制台")
    
    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 当前查阅标准", std_list)
        
        st.markdown("### 📍 章节快速索引")
        toc_df = df[df['标准号'] == selected_std]
        # 目录树
        for idx, row in toc_df.iterrows():
            if st.button(f"▫️ {row['条款号']}", key=f"toc_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    
    st.divider()
    with st.expander("🛠️ 系统维护"):
        if st.checkbox("开启重置权限"):
            if st.button("🔥 彻底清空缓存并重扫", type="primary"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.cache_data.clear()
                st.rerun()

# --- 4. 主界面展示 ---
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准数字化智慧工作站</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>支持并行 OCR 加速、增量存档与多维检索</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 统计数据
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f'<div class="metric-card"><small>收录标准</small><br><b>{len(df["标准号"].unique())}</b></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="metric-card"><small>结构化条款</small><br><b>{len(df)}</b></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="metric-card"><small>解析引擎</small><br><b>OCR+Parallel</b></div>', unsafe_allow_html=True)
    c4.markdown(f'<div class="metric-card"><small>同步状态</small><br><b style="color:#22c55e;">实时更新</b></div>', unsafe_allow_html=True)

    st.write("")
    search_query = st.text_input("🔍 智慧检索 (输入关键词、标准号或条款号)", placeholder="搜索内容...", label_visibility="collapsed")

    # 逻辑：搜索模式 vs 全文模式
    if search_query:
        st.subheader(f"🎯 检索结果: {search_query}")
        # 模糊匹配内容或精确匹配条款
        res = df[(df['内容'].str.contains(search_query, case=False, na=False)) | (df['条款号'] == search_query)]
        if not res.empty:
            for _, row in res.iterrows():
                # 高亮
                highlighted = re.sub(f"({search_query})", r"<mark>\1</mark>", row['内容'], flags=re.IGNORECASE)
                st.markdown(f"""
                    <div class="clause-card">
                        <span style="color:#64748b; font-size:0.8rem;">{row['标准号']}</span>
                        <div style="font-weight:bold; color:#1e3a8a; margin:5px 0;">条款 {row['条款号']}</div>
                        <div style="line-height:1.6;">{highlighted}</div>
                        <div style="margin-top:10px;"><span class="param-tag">📏 参数: {row['技术参数']}</span></div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("无相关匹配结果。")
    else:
        # 显示全文
        st.subheader(f"📖 浏览模式：{selected_std}")
        for _, row in toc_df.iterrows():
            is_jump = st.session_state.get('jump_target') == row['条款号']
            card_style = "clause-card highlight-active" if is_jump else "clause-card"
            st.markdown(f"""
                <div class="{card_style}">
                    <div style="font-weight:bold; color:#1e3a8a;">条款 {row['条款号']}</div>
                    <div style="margin-top:8px; line-height:1.6;">{row['内容']}</div>
                    <div style="margin-top:10px;"><span class="param-tag">📏 参数: {row['技术参数']}</span></div>
                </div>
            """, unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请将 PDF 或 Word 标准放入 data/ 文件夹启动自动同步。")
