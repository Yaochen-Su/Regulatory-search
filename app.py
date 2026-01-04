import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级 CSS 美化 ---
st.set_page_config(page_title="法规标准数字化工作站", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f4f7f9; }
    .header-banner {
        background: linear-gradient(90deg, #0f172a 0%, #1e40af 100%);
        padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px;
    }
    .full-text-container {
        background: white; padding: 40px; border-radius: 12px; line-height: 2; 
        color: #1e293b; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .clause-card {
        background: white; padding: 25px; border-radius: 12px; border-left: 5px solid #3b82f6;
        margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .level-1 { font-weight: bold; font-size: 1.2rem; color: #1e3a8a; margin-top: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 5px; }
    .level-2 { font-weight: 600; font-size: 1.05rem; color: #334155; margin-left: 15px; margin-top: 10px; }
    .level-3 { font-size: 0.95rem; color: #475569; margin-left: 30px; }
    .std-badge { background: #eff6ff; color: #1e40af; padding: 3px 10px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    mark { background: #fde047; font-weight: bold; border-radius: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据处理与层级判定 ---
DB_FILE = "processed_database.csv"

def get_level(no):
    """根据编号点数判定层级"""
    if not no or not str(no)[0].isdigit(): return 1
    return str(no).count('.') + 1

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
        with st.status("🚀 正在构建层级索引...", expanded=True):
            for f in new_files:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    # 增加层级列
                    item_df['层级'] = item_df['编号'].apply(get_level)
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
    return db_df

df = sync_database()

# --- 3. 侧边栏：功能置顶与层级索引 ---
with st.sidebar:
    st.markdown(f'<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("数字化工作站")
    
    # 下载置顶
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 下载结构化数据库 (CSV)", data=file, file_name="standard_structure.csv", use_container_width=True)
    st.divider()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择标准", std_list)
        
        st.markdown("### 📍 章节层级索引")
        toc_view = df[df['标准号'] == selected_std].sort_values(by='编号')
        
        # 树状缩进显示索引
        for _, row in toc_view.iterrows():
            indent = "　" * (int(row['层级']) - 1)
            icon = "● " if row['层级'] == 1 else "○ "
            if st.button(f"{indent}{icon}{row['编号']}", key=f"side_{row['编号']}", use_container_width=True):
                st.session_state.jump_target = row['编号']

    st.divider()
    with st.expander("🛠️ 系统维护"):
        if st.button("🔥 彻底重置数据库", type="primary"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.rerun()

# --- 4. 主界面：总分总展示逻辑 ---
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准数字化查阅平台</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>层级化结构展示 | 自动化参数提取</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 智慧检索
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        query = st.text_input("🔍 检索编号或关键词...", placeholder="模糊搜索内容，或输入精准编号", label_visibility="collapsed")
    with sc2:
        precise = st.toggle("精准匹配", value=False)

    target_id = st.session_state.get('jump_target')
    current_std_df = df[df['标准号'] == selected_std].sort_values(by='编号')

    if query:
        # A. 搜索结果模式
        st.subheader("🎯 匹配结果")
        if precise:
            results = current_std_df[current_std_df['编号'] == query]
        else:
            results = current_std_df[current_std_df['内容'].str.contains(query, case=False, na=False) | current_std_df['编号'].str.contains(query, na=False)]
        
        for _, row in results.iterrows():
            text = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['内容']), flags=re.IGNORECASE)
            st.markdown(f'<div class="clause-card"><div class="std-badge">编号 {row["编号"]}</div><div style="margin-top:10px;">{text}</div><div style="margin-top:10px;"><small>📊 参数: {row["技术参数"]}</small></div></div>', unsafe_allow_html=True)

    elif target_id:
        # B. 选中章节及其子项模式 (总分总 - 分)
        st.subheader(f"📍 章节查阅: {target_id}")
        # 查找该编号及其所有子编号 (如点击 1，显示 1, 1.1, 1.1.1)
        sub_df = current_std_df[current_std_df['编号'].str.startswith(str(target_id))]
        for _, row in sub_df.iterrows():
            level_cls = f"level-{min(int(row['层级']), 3)}"
            st.markdown(f'<div class="{level_cls}">[{row["编号"]}]</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="clause-card" style="margin-left:{min(int(row["层级"]-1)*20, 40)}px;">{row["内容"]}<br><small style="color:#64748b;">参数：{row["技术参数"]}</small></div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回全文阅读"):
            st.session_state.jump_target = None
            st.rerun()

    else:
        # C. 全文模式 (总分总 - 总)
        st.subheader(f"📖 {selected_std} 全文浏览")
        with st.container():
            full_html = ""
            for _, row in current_std_df.iterrows():
                level_cls = f"level-{min(int(row['层级']), 3)}"
                full_html += f'<div class="{level_cls}">[{row["编号"]}]</div>'
                full_html += f'<div style="margin: 10px 0 20px {min(int(row["层级"]-1)*20, 40)}px; color:#334155; line-height:1.8;">{row["内容"]}</div>'
            st.markdown(f'<div class="full-text-container">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("请在 data/ 文件夹中放入文件。")
