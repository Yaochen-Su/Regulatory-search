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
    .level-1 { font-weight: bold; font-size: 1.25rem; color: #1e3a8a; margin-top: 25px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
    .level-2 { font-weight: 600; font-size: 1.1rem; color: #334155; margin-left: 15px; margin-top: 15px; }
    .level-3 { font-size: 1rem; color: #475569; margin-left: 30px; margin-top: 10px; }
    .std-badge { background: #eff6ff; color: #1e40af; padding: 3px 10px; border-radius: 4px; font-size: 0.8rem; font-weight: bold; }
    mark { background: #fde047; font-weight: bold; border-radius: 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库同步逻辑 ---
DB_FILE = "processed_database.csv"

def get_level(no):
    """根据编号点数判定层级"""
    if not no or not str(no)[0].isdigit(): return 1
    return str(no).count('.') + 1

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    current_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    
    if os.path.exists(DB_FILE):
        db_df = pd.read_csv(DB_FILE)
        # 自动清理已删除文件
        db_df = db_df[db_df['来源文件'].isin(current_files)]
    else:
        db_df = pd.DataFrame()
    
    processed = set(db_df['来源文件'].unique()) if not db_df.empty else set()
    new_files = [f for f in current_files if f not in processed]

    if new_files:
        new_entries = []
        with st.status("🚀 正在构建结构化索引...", expanded=True):
            for f in new_files:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    item_df['层级'] = item_df['编号'].apply(get_level)
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
    return db_df

df = sync_database()

# --- 3. 侧边栏：下载置顶与层级索引 ---
with st.sidebar:
    # 修复 Logo 显示
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="70"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    # 下载按钮置顶
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 下载结构化数据库 (CSV)", data=file, file_name="standard_db.csv", use_container_width=True)
    st.divider()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅标准", std_list)
        
        st.markdown("### 📍 编号层级索引")
        toc_view = df[df['标准号'] == selected_std].sort_values(by='编号')
        
        # 树状缩进索引 (修复 Key 重复问题)
        for idx, row in toc_view.iterrows():
            indent = "　" * (int(row['层级']) - 1)
            icon = "● " if row['层级'] == 1 else "○ "
            # 使用 标准号 + 索引 作为唯一 key
            if st.button(f"{indent}{icon}{row['编号']}", key=f"side_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

    st.divider()
    with st.expander("🛠️ 管理员工具"):
        if st.button("🔥 重置并重新扫描", type="primary"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.rerun()

# --- 4. 主界面：总分总展示逻辑 ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 1.8rem;'>法规标准智慧化数字化查阅平台</h1>
        <p style='margin:5px 0 0 0; opacity: 0.8;'>标准：{selected_std if not df.empty else "未加载"}</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 搜索区
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        query = st.text_input("🔍 检索编号或关键词...", placeholder="模糊搜索内容，或输入精准编号", label_visibility="collapsed")
    with sc2:
        precise = st.toggle("精准模式", value=False)

    target_id = st.session_state.get('jump_target')
    current_std_df = df[df['标准号'] == selected_std].sort_values(by='编号')

    # A. 搜索模式 (分)
    if query:
        st.subheader("🎯 匹配结果")
        if precise:
            results = current_std_df[current_std_df['编号'] == query]
        else:
            results = current_std_df[current_std_df['内容'].str.contains(query, case=False, na=False) | current_std_df['编号'].str.contains(query, na=False)]
        
        for idx, row in results.iterrows():
            text = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['内容']), flags=re.IGNORECASE)
            st.markdown(f'<div class="clause-card"><div class="std-badge">编号 {row["编号"]}</div><div style="margin-top:10px;">{text}</div><div style="margin-top:10px;"><small>📊 参数: {row["技术参数"]}</small></div></div>', unsafe_allow_html=True)

    # B. 点击索引后的“总-分”模式
    elif target_id:
        st.subheader(f"📍 章节查阅: {target_id}")
        # 查找该编号及其所有子孙项
        sub_df = current_std_df[current_std_df['编号'].astype(str).str.startswith(str(target_id))]
        for idx, row in sub_df.iterrows():
            level = int(row['层级'])
            margin = min((level - 1) * 25, 60)
            if level == 1:
                st.markdown(f'<div class="level-1">[{row["编号"]}]</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="clause-card" style="margin-left:{margin}px;"><b>{row["编号"]}</b><br>{row["内容"]}<br><small style="color:#64748b;">参数：{row["技术参数"]}</small></div>', unsafe_allow_html=True)
        
        if st.button("⬅️ 返回全文通读", key="back_to_full"):
            st.session_state.jump_target = None
            st.rerun()

    # C. 全文模式 (总)
    else:
        st.subheader("📖 全文浏览")
        full_html = ""
        for idx, row in current_std_df.iterrows():
            level = int(row['层级'])
            margin = min((level - 1) * 25, 60)
            if level == 1:
                full_html += f'<div class="level-1">[{row["编号"]}]</div>'
            elif level == 2:
                full_html += f'<div class="level-2">{row["编号"]}</div>'
            else:
                full_html += f'<div class="level-3">{row["编号"]}</div>'
            
            full_html += f'<div style="margin: 5px 0 20px {margin}px; color:#334155;">{row["内容"]}</div>'
        
        st.markdown(f'<div class="full-text-container">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请在 data/ 文件夹中放入文件开始同步。")
