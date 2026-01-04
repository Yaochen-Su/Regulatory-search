import streamlit as st
import pandas as pd
import os
import re
import time
from processor import process_document_to_dataframe

# --- 1. 页面配置与 CSS 美化 ---
st.set_page_config(page_title="法规标准智慧工作站", page_icon="⚖️", layout="wide")

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
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #e5e7eb;
    }
    .clause-card {
        background: white; padding: 25px; border-radius: 8px; border-left: 6px solid #2563eb;
        margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .chapter-tag { background: #eff6ff; color: #1e40af; padding: 4px 12px; border-radius: 4px; font-weight: bold; margin-bottom: 10px; display: inline-block; }
    mark { background: #fde047; font-weight: bold; padding: 0 2px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 增强型同步逻辑：支持内容更新检测 ---
DB_FILE = "processed_database.csv"

def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    
    # 获取当前文件夹内所有物理文件及其修改时间
    current_files = {}
    for f in os.listdir("data"):
        if f.lower().endswith(('.pdf', '.docx')):
            mtime = os.path.getmtime(os.path.join("data", f))
            current_files[f] = mtime

    # 加载数据库
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE)
            # 清理已物理删除的文件
            db_df = db_df[db_df['来源文件'].isin(current_files.keys())]
        except:
            db_df = pd.DataFrame()
    else:
        db_df = pd.DataFrame()

    # 判定需要解析的文件：1. 新文件 2. 修改时间发生变动的文件
    new_or_updated_files = []
    for f, mtime in current_files.items():
        if db_df.empty:
            new_or_updated_files.append(f)
        else:
            # 查找该文件在库中的记录
            file_records = db_df[db_df['来源文件'] == f]
            if file_records.empty:
                new_or_updated_files.append(f)
            else:
                # 检查时间戳是否匹配（取第一条记录的时间戳对比）
                recorded_time = file_records.iloc[0].get('最后修改时间', 0)
                if abs(float(recorded_time) - float(mtime)) > 1.0: # 允许 1 秒以内的误差
                    new_or_updated_files.append(f)
                    # 先删除旧的变动记录，防止重复
                    db_df = db_df[db_df['来源文件'] != f]

    if new_or_updated_files:
        new_entries = []
        with st.status(f"🚀 正在检测并解析 {len(new_or_updated_files)} 个变动文件...", expanded=True):
            for f in new_or_updated_files:
                st.write(f"处理中: {f}")
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['来源文件'] = f
                    item_df['最后修改时间'] = current_files[f] # 存入当前时间戳
                    new_entries.append(item_df)
            
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True)
                db_df.to_csv(DB_FILE, index=False)
                st.cache_data.clear()
        st.rerun()
    
    return db_df

df = sync_database()

# --- 3. 侧边栏布局 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="80"></div>', unsafe_allow_html=True)
    st.title("法规查阅中心")
    
    st.divider()
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as file:
            st.download_button("📥 导出数字化数据库 (CSV)", data=file, file_name="law_db.csv", use_container_width=True)
    st.divider()

    if not df.empty:
        std_list = sorted(list(df['标准号'].unique()))
        selected_std = st.selectbox("📂 选择查阅规章", std_list)
        
        st.markdown("### 📍 条文索引")
        toc_view = df[df['标准号'] == selected_std]
        
        last_chapter = ""
        for idx, row in toc_view.iterrows():
            if row['章'] != last_chapter:
                st.caption(f"📁 {row['章']}")
                last_chapter = row['章']
            if st.button(f"▫️ {row['编号']}", key=f"btn_{selected_std}_{idx}", use_container_width=True):
                st.session_state.jump_target = row['编号']

    st.divider()
    if st.button("🔥 重置系统存档"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.rerun()

# --- 4. 主界面渲染 ---
st.markdown(f"""
    <div class="header-banner">
        <h1 style='margin:0; color:#1e3a8a;'>{selected_std if not df.empty else "法规库加载中"}</h1>
        <p style='color:#64748b; margin-top:5px;'>数字化条文查阅工作站 (支持内容更新自动同步)</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    sc1, sc2 = st.columns([4, 1])
    with sc1:
        query = st.text_input("🔍 搜索关键词或条文编号", placeholder="输入关键词后回车...", label_visibility="collapsed")
    with sc2:
        precise = st.toggle("精准模式", value=False)

    current_law_df = df[df['标准号'] == selected_std]

    if query:
        st.subheader("🎯 搜索匹配条文")
        results = current_law_df[current_law_df['编号'] == query] if precise else \
                  current_law_df[current_law_df['全文'].str.contains(query, case=False, na=False) | current_law_df['编号'].str.contains(query, na=False)]
        
        if not results.empty:
            for idx, row in results.iterrows():
                highlight = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['全文']), flags=re.IGNORECASE)
                st.markdown(f'<div class="clause-card"><div class="chapter-tag">{row["章"]}</div><div style="font-weight:bold; margin-bottom:10px;">{row["编号"]}</div><div>{highlight}</div></div>', unsafe_allow_html=True)
        else: st.warning("未找到匹配内容。")

    elif st.session_state.get('jump_target'):
        target = st.session_state.get('jump_target')
        row = current_law_df[current_law_df['编号'] == target].iloc[0]
        st.subheader(f"📍 条文详情：{target}")
        st.markdown(f'<div class="clause-card" style="border-left-color:#f59e0b;"><div class="chapter-tag">{row["章"]}</div><div style="font-weight:bold; margin:15px 0; font-size:1.3rem; color:#1e3a8a;">{row["编号"]}</div><div style="font-size:1.2rem; line-height:2;">{row["全文"]}</div></div>', unsafe_allow_html=True)
        if st.button("⬅️ 返回查阅原文全文"):
            st.session_state.jump_target = None
            st.rerun()

    else:
        st.subheader("📖 原文浏览模式")
        full_html = f"<div style='text-align:center;'><h2>{selected_std}</h2></div><br>"
        last_chapter = ""
        for idx, row in current_law_df.iterrows():
            if row['章'] != last_chapter:
                full_html += f"<h3 style='text-align:center; color:#1e40af; margin-top:40px;'>{row['章']}</h3>"
                last_chapter = row['章']
            full_html += f"<p><b>{row['编号']}</b> {row['全文']}</p>"
        st.markdown(f'<div class="full-text-area">{full_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 请将文件放入 data 文件夹开始使用。")
