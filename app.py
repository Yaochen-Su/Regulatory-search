import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS ---
st.set_page_config(page_title="法规标准数字化查阅平台", page_icon="⚖️", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    .header-banner {
        background: white; padding: 25px; border-bottom: 4px solid #1e40af;
        margin-bottom: 25px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .full-text-area {
        background: white; padding: 40px 60px; border-radius: 4px; line-height: 2.2;
        color: #1f2937; font-family: "SimSun", "STSong", serif; font-size: 1.1rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;
    }
    .clause-card {
        background: white; padding: 25px; border-radius: 8px; border-left: 6px solid #2563eb;
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .chapter-tag { background: #eff6ff; color: #1e40af; padding: 4px 12px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; display: inline-block; }
    mark { background: #fde047; font-weight: bold; padding: 0 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据同步 ---
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
        with st.status("🚀 正在构建法规数据库...", expanded=True):
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

# --- 3. 侧边栏：下载置顶 & 目录 ---
with st.sidebar:
    # Logo 修复
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("法规查阅中心")
    
    # 下载按钮置顶
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化数据库 (CSV)", data=file, file_name="law_db.csv", use_container_width=True)
    st.divider()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅文件", std_list)
        
        st.markdown("### 📍 条文索引")
        toc_view = df[df['标准号'] == selected_std]
        
        # 章-条 树状索引
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.caption(f"📁 {row['章']}")
                last_chapter = row['章']
            if st.button(f"▫️ {row['编号']}", key=f"sidebar_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

    st.divider()
    if st.button("🔥 重置系统存档"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

# --- 4. 主界面：原文与检索分流 ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; color:#1e3a8a;'>{selected_std if not df.empty else "请上传法规文件"}</h1>
        <p style='color:#64748b; margin-top:5px;'>当前位置：首页 > 法规文件 > {selected_std if not df.empty else "未选择"}</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    # 搜索条
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        query = st.text_input("🔍 模糊搜索关键词或精准输入编号（如：第五条）", placeholder="输入内容后回车...", label_visibility="collapsed")
    with sc2:
        precise = st.toggle("精准模式", value=False)

    current_law_df = df[df['标准号'] == selected_std]

    # --- 内容分流展示逻辑 ---
    if query:
        # A. 搜索结果模式
        st.subheader("🎯 搜索匹配条文")
        if precise:
            results = current_law_df[current_law_df['编号'] == query]
        else:
            results = current_law_df[current_law_df['全文'].str.contains(query, case=False, na=False) | current_law_df['编号'].str.contains(query, na=False)]
        
        if not results.empty:
            for idx, row in results.iterrows():
                highlight = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['全文']), flags=re.IGNORECASE)
                st.markdown(f'<div class="clause-card"><div class="chapter-tag">{row["章"]}</div><div style="font-weight:bold; margin-bottom:10px; font-size:1.1rem;">{row["编号"]}</div><div>{highlight}</div></div>', unsafe_allow_html=True)
        else: st.warning("未找到匹配条文，请尝试更换关键词。")

    elif st.session_state.get('jump_target'):
        # B. 侧边栏跳转模式
        target = st.session_state.get('jump_target')
        row = current_law_df[current_law_df['编号'] == target].iloc[0]
        st.subheader(f"📍 条文详情：{target}")
        st.markdown(f'<div class="clause-card" style="border-left-color:#f59e0b;"><div class="chapter-tag">{row["章"]}</div><div style="font-weight:bold; margin:15px 0; font-size:1.3rem; color:#1e3a8a;">{row["编号"]}</div><div style="font-size:1.2rem; line-height:2;">{row["全文"]}</div><div style="margin-top:20px; color:#64748b;"><hr>📊 提取参数：{row["技术参数"]}</div></div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回查阅原文全文"):
            st.session_state.jump_target = None
            st.rerun()

    else:
        # C. 默认：原文全文浏览模式
        st.subheader("📖 法规原文浏览")
        full_html = f"<div style='text-align:center;'><h2>{selected_std}</h2></div><br>"
        last_chapter = ""
        for idx, row in current_law_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f"<h3 style='text-align:center; color:#1e40af; margin-top:40px;'>{row['章']}</h3>"
                last_chapter = row['章']
            full_html += f"<p><b>{row['编号']}</b> {row['全文']}</p>"
        
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请将法规 PDF 或 Word 放入 data 文件夹开始使用。")
