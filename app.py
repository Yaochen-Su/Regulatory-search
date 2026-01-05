import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与【保留高级 CSS 美化】 ---
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
    .clause-card:hover { transform: translateY(-3px); box-shadow: 0 6px 15px rgba(0,0,0,0.1); }
    .highlight-active { border-left: 6px solid #f59e0b !important; background-color: #fffbeb !important; }
    .std-badge { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 50px; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; }
    .param-tag { background: #ecfdf5; color: #065f46; padding: 4px 10px; border-radius: 6px; border: 1px solid #a7f3d0; font-family: monospace; font-weight: bold; }
    .stButton>button { border-radius: 8px; text-align: left; padding: 5px 15px; background-color: transparent; transition: all 0.2s; }
    .stButton>button:hover { background-color: #eff6ff; color: #1e40af; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 强化的增量同步逻辑 ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    
    # 1. 获取物理文件清单并统一格式
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    
    # 2. 尝试读取现有数据库
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            # 自动剔除已被物理删除的文件记录
            db_df = db_df[db_df['来源文件'].isin(current_files)]
        except Exception:
            db_df = pd.DataFrame()
    else:
        db_df = pd.DataFrame()

    # 3. 找出真正需要“解析”的新文件
    processed_files = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    new_files = [f for f in current_files if f not in processed_files]

    # 4. 执行解析 (仅针对 new_files)
    if new_files:
        new_entries = []
        with st.status("🚀 发现新文档，正在同步数据...", expanded=True) as status:
            for f in new_files:
                st.write(f"正在读取内容: {f}")
                # 调用处理器，processor 内部已针对 docx 优化
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f # 确保标记文件名以便下次跳过
                    new_entries.append(item_df)
            
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                # 写入 CSV 前确保来源文件列不丢失
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
            status.update(label="✅ 同步及存档更新完成", state="complete", expanded=False)
    
    return db_df

df = sync_database()

# --- 3. 侧边栏与主界面（保留原有美化） ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/law.png", width=60)
    st.title("工作站控制台")
    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅标准", std_list)
        st.markdown("### 📍 章节快速索引")
        toc_df = df[df['标准号'] == selected_std]
        for idx, row in toc_df.iterrows():
            if st.button(f"▫️ 条款 {row['条款号']}", key=f"t_{idx}", use_container_width=True):
                st.session_state.jump_target = row['条款号']
    
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button(label="📥 下载已解析库 (CSV)", data=file, file_name="processed_database.csv", mime="text/csv", use_container_width=True)
    
    with st.expander("🛠️ 管理员工具"):
        if st.checkbox("重置数据库权限"):
            if st.button("🔥 彻底清除并重新解析", type="primary"):
                if os.path.exists(DB_FILE): os.remove(DB_FILE)
                st.cache_data.clear()
                st.rerun()

st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准智慧化数字化查阅平台</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>基于智能缓存技术 | 已解析文件实现 0 秒秒传</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 仪表盘统计
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-container"><small>标准总数</small><br><b>{len(df["标准号"].unique())}</b></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-container"><small>条款总计</small><br><b>{len(df)}</b></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-container"><small>参数识别率</small><br><b>{len(df[df["技术参数"]!="见详情内容"])/len(df):.1%}</b></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-container"><small>系统状态</small><br><b style="color:#10b981;">解析缓存生效中</b></div>', unsafe_allow_html=True)

    query = st.text_input("🔍 智慧检索", placeholder="搜索关键字、条款号或标准编号...", label_visibility="collapsed")

    if query:
        st.subheader("🎯 检索匹配结果")
        res = df[(df['内容'].str.contains(query, case=False, na=False)) | (df['条款号'] == query)]
        for _, row in res.iterrows():
            highlight = re.sub(f"({query})", r"<mark>\1</mark>", str(row['内容']), flags=re.IGNORECASE)
            st.markdown(f'<div class="clause-card"><span class="std-badge">{row["标准号"]}</span><div style="font-weight:bold; margin: 10px 0; color:#1e3a8a;">条款 {row["条款号"]}</div><div style="color:#374151; line-height:1.7;">{highlight}</div><div style="margin-top:15px;"><span class="param-tag">📊 核心参数: {row["技术参数"]}</span></div></div>', unsafe_allow_html=True)
    else:
        st.subheader(f"📖 顺序查阅：{selected_std}")
        for _, row in toc_df.iterrows():
            is_jump = st.session_state.get('jump_target') == row['条款号']
            card_cls = "clause-card highlight-active" if is_jump else "clause-card"
            st.markdown(f'<div class="{card_cls}"><div style="font-weight:bold; color:#1e3a8a;">条款 {row["条款号"]}</div><div style="color:#374151; line-height:1.7;">{row["内容"]}</div><div style="margin-top:15px;"><span class="param-tag">📊 核心参数: {row["技术参数"]}</span></div></div>', unsafe_allow_html=True)
else:
    st.info("👋 当前数据库为空，请在 data/ 文件夹中放入文件。")
