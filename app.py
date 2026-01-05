import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 页面配置与高级 CSS ---
st.set_page_config(page_title="法规标准数字化查阅平台", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f8fafc; }
    .header-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 25px; border-radius: 12px; color: white; margin-bottom: 25px; text-align: center;
    }
    .full-text-area {
        background: white; padding: 35px; border-radius: 8px; line-height: 2.2;
        color: #1f2937; font-family: "SimSun", serif; font-size: 1.1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #e5e7eb;
    }
    .clause-block { margin-bottom: 25px; padding-bottom: 10px; }
    .clause-no { color: #1e3a8a; font-weight: bold; margin-bottom: 8px; font-size: 1.15rem; }
    .tag-blue { background: #eff6ff; color: #1e40af; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-right: 10px; }
    .tag-green { background: #ecfdf5; color: #065f46; padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; }
    .keyword-pill { 
        background: #f3f4f6; color: #4b5563; padding: 2px 10px; border-radius: 50px; 
        font-size: 0.75rem; margin-right: 6px; border: 1px solid #d1d5db; display: inline-block;
    }
    mark { background-color: #fde047; font-weight: bold; padding: 0 2px; }
</style>
""", unsafe_allow_html=True)

DB_FILE = "processed_database.csv"

# --- 2. 数据库同步逻辑 ---
def sync_database():
    if not os.path.exists("data"): os.makedirs("data")
    all_files = [f for f in os.listdir("data") if f.lower().endswith(('.pdf', '.docx'))]
    
    db_df = pd.DataFrame()
    if os.path.exists(DB_FILE):
        try:
            db_df = pd.read_csv(DB_FILE).fillna("")
            db_df = db_df[db_df['文件名'].isin(all_files)]
        except: db_df = pd.DataFrame()

    current_meta = {f: f"{f}_{int(os.path.getmtime(os.path.join('data', f)))}" for f in all_files}
    parsed_fps = set(db_df['指纹'].unique()) if not db_df.empty else set()
    to_parse = [f for f, fp in current_meta.items() if fp not in parsed_fps]

    if to_parse:
        new_entries = []
        with st.status(f"🚀 正在数字化解析新规章..."):
            for f in to_parse:
                item_df = process_document_to_dataframe(os.path.join("data", f))
                if not item_df.empty:
                    item_df['指纹'] = current_meta[f]
                    new_entries.append(item_df)
            if new_entries:
                db_df = pd.concat([db_df] + new_entries, ignore_index=True).fillna("")
                db_df.to_csv(DB_FILE, index=False)
                st.rerun()
    return db_df

df = sync_database()

# --- 3. 侧边栏：文件选择逻辑优化 ---
with st.sidebar:
    st.markdown('<div style="text-align: center;"><img src="https://img.icons8.com/fluency/96/law.png" width="60"></div>', unsafe_allow_html=True)
    st.title("数字化控制台")
    
    if st.button("🔥 重置数字化全库", type="primary", use_container_width=True):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    if not df.empty:
        # 【关键改动】：剥离文件格式后缀
        raw_file_list = sorted(list(df['文件名'].unique()))
        # 创建映射：{不带后缀的名字: 带后缀的原始文件名}
        display_map = {os.path.splitext(f)[0]: f for f in raw_file_list}
        
        selected_display_name = st.selectbox("📂 当前查阅规章", list(display_map.keys()))
        selected_real_file = display_map[selected_display_name]
        
        current_df = df[df['文件名'] == selected_real_file]
        
        st.info(f"📍 版本: {current_df['版本'].iloc[0] or '正式版'}")
        st.success(f"📅 实施日期: {current_df['实施日期'].iloc[0] or '待核实'}")

# --- 4. 主界面渲染 ---
st.markdown('<div class="header-banner"><h1>法规标准数字化查阅平台</h1></div>', unsafe_allow_html=True)

if not df.empty:
    # 统计看板
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("总规章数", len(df["文件名"].unique()))
    with c2: st.metric("总条文数", len(df))
    with c3: st.metric("参数提取量", len(df[df["关键词"] != ""]))
    with c4: st.metric("系统状态", "运行良好")

    st.write("")
    query = st.text_input("🔍 搜索关键词或条文编号...", placeholder="搜索后将高亮显示匹配内容")

    if query:
        st.subheader(f"🎯 搜索结果: {query}")
        res = current_df[current_df['全文'].str.contains(query, case=False, na=False) | current_df['编号'].str.contains(query, na=False)]
        for _, row in res.iterrows():
            text = re.sub(f"({re.escape(query)})", r"<mark>\1</mark>", str(row['全文']), flags=re.IGNORECASE)
            st.markdown(f'<div class="clause-block"><div class="clause-no">{row["编号"]}</div><div>{text}</div></div>', unsafe_allow_html=True)
    else:
        # 【关键改动】：主标题也不显示后缀
        st.subheader(f"📖 {selected_display_name}")
        st.markdown(f'<div style="margin-bottom:20px;"><span class="tag-blue">发布日期: {current_df["发布日期"].iloc[0] or "待核实"}</span><span class="tag-green">实施日期: {current_df["实施日期"].iloc[0] or "待核实"}</span></div>', unsafe_allow_html=True)

        # 构建正文 HTML
        content_html = ""
        last_chapter = ""
        for _, row in current_df.iterrows():
            if row['章'] != last_chapter and row['章'] != "正文":
                content_html += f'<h3 style="color:#1e40af; border-bottom:2px solid #e5e7eb; padding-bottom:5px; margin-top:30px;">{row["章"]}</h3>'
                last_chapter = row['章']
            
            # 过滤 nan 标签
            keywords = [k.strip() for k in str(row['关键词']).split(',') if k.strip() and k.lower() != 'nan']
            keyword_html = "".join([f'<span class="keyword-pill">{k}</span>' for k in keywords])
            
            # 紧凑拼接，防止误判为代码块
            content_html += f'<div class="clause-block">'
            if row["编号"]: 
                content_html += f'<div class="clause-no">{row["编号"]}</div>'
            content_html += f'<div style="color:#374151;">{row["全文"]}</div>'
            if keyword_html:
                content_html += f'<div style="margin-top:8px;">{keyword_html}</div>'
            content_html += '</div>'
            
        st.markdown(f'<div class="full-text-area">{content_html}</div>', unsafe_allow_html=True)
else:
    st.info("👋 欢迎！请在 data/ 文件夹中放入文件开始同步。")
