import streamlit as st
import pandas as pd
import os
import re
from processor import process_document_to_dataframe

# --- 1. 初始化设置与 CSS ---
st.set_page_config(page_title="法规标准数字化工作站", layout="wide")

# 注入自定义样式，实现左侧目录树的视觉效果
st.markdown("""
    <style>
    .toc-item { cursor: pointer; padding: 5px; border-bottom: 1px solid #f0f0f0; font-size: 0.9em; }
    .toc-item:hover { background-color: #e0f2fe; color: #0369a1; }
    .content-body { background: white; padding: 30px; border-radius: 5px; border: 1px solid #ddd; line-height: 1.8; }
    mark { background-color: #ffeb3b; padding: 0 2px; border-radius: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 数据加载 (带缓存) ---
@st.cache_data
def load_all_data():
    folder = "data"
    all_dfs = []
    if not os.path.exists(folder): return pd.DataFrame()
    files = [f for f in os.listdir(folder) if f.lower().endswith(('.pdf', '.docx'))]
    for file in files:
        df_item = process_document_to_dataframe(os.path.join(folder, file))
        if not df_item.empty: all_dfs.append(df_item)
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

df_all = load_all_data()

# --- 3. 状态管理 ---
if 'selected_std' not in st.session_state: st.session_state.selected_std = None
if 'jump_to_clause' not in st.session_state: st.session_state.jump_to_clause = None

# --- 4. 侧边栏：结构化目录树 ---
with st.sidebar:
    st.title("📚 标准目录")
    if not df_all.empty:
        # 先选择标准
        std_options = list(df_all['标准号'].unique())
        selected = st.selectbox("请先选择一份标准：", ["请选择..."] + std_options)
        
        if selected != "请选择...":
            st.session_state.selected_std = selected
            st.divider()
            st.write(f"**{selected} 目录结构**")
            
            # 提取当前标准的目录树
            current_std_df = df_all[df_all['标准号'] == selected]
            for idx, row in current_std_df.iterrows():
                # 创建点击跳转按钮
                if st.button(f"第 {row['条款号']} 条", key=f"toc_{idx}", use_container_width=True):
                    st.session_state.jump_to_clause = row['条款号']
    else:
        st.info("请在 data/ 文件夹上传标准。")

# --- 5. 主界面：多维检索区 ---
st.title("⚖️ 法规标准数字化工作站")

# 精确/模糊/条款 检索选项卡
search_tab1, search_tab2, search_tab3 = st.tabs(["🎯 精确编号检索", "🔍 全文模糊搜索", "📜 条款号快速定位"])

with search_tab1:
    exact_query = st.text_input("输入完整标准号 (如: GB/T 4857.5-92)")
with search_tab2:
    fuzzy_query = st.text_input("输入关键词（支持模糊语义，如：跌落高度误差）")
with search_tab3:
    clause_query = st.text_input("直接定位条款 (如: 5.6.1)")

# --- 6. 数据过滤逻辑 ---
results = df_all.copy()
if exact_query:
    results = results[results['标准号'].str.contains(exact_query, case=False)]
elif fuzzy_query:
    results = results[results['内容'].str.contains(fuzzy_query, case=False)]
elif clause_query:
    results = results[results['条款号'] == clause_query]

# --- 7. 内容展示区 (结构化查看) ---
if st.session_state.selected_std:
    st.subheader(f"📖 当前查阅：{st.session_state.selected_std}")
    
    # 筛选当前标准的内容
    display_df = df_all[df_all['标准号'] == st.session_state.selected_std]
    
    # 如果用户通过目录跳转，则高亮该条款
    for _, row in display_df.iterrows():
        # 判断是否为当前跳转的条款
        is_jump = (st.session_state.jump_to_clause == row['条款号'])
        bg_color = "#fff9c4" if is_jump else "transparent"
        border_style = "2px solid #fbc02d" if is_jump else "1px solid #eee"

        # 全文查看并标注
        content_html = row['内容']
        if fuzzy_query: # 全文搜索时的标注逻辑
            content_html = re.sub(f"({fuzzy_query})", r"<mark>\1</mark>", content_html, flags=re.IGNORECASE)

        st.markdown(f"""
            <div style="background:{bg_color}; border:{border_style}; padding:15px; margin-bottom:10px; border-radius:5px;">
                <span style="font-weight:bold; color:#1565c0;">[条款 {row['条款号']}]</span> 
                <span style="float:right;" class="tag">参数：{row['技术参数']}</span>
                <div style="margin-top:10px;">{content_html}</div>
            </div>
        """, unsafe_allow_html=True)
else:
    # 首页默认展示搜索结果
    if not results.empty and (exact_query or fuzzy_query or clause_query):
        st.write(f"搜索到 {len(results)} 条相关结果：")
        st.dataframe(results[['标准号', '条款号', '内容', '技术参数']])
    else:
        st.info("👈 请在左侧侧边栏选择一份标准开始查阅，或在上方进行搜索。")
