import fitz
import docx
import re
import pandas as pd
import os

def process_document_to_dataframe(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""
    
    try:
        if ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        elif ext == '.pdf':
            doc = fitz.open(file_path)
            full_text = "\n".join([page.get_text() for page in doc])
            doc.close()
    except: return pd.DataFrame()

    full_text = full_text.strip()
    if not full_text: return pd.DataFrame()

    # 1. 提取元数据 (标题、日期、版本)
    title_search = re.search(r'([^\n]{2,50}(?:条例|办法|标准|规定|文件|通知))', full_text[:2000])
    std_no = title_search.group(1).strip() if title_search else os.path.splitext(filename)[0]
    
    # 提取实施日期和发布日期
    dates = re.findall(r'(\d{4}年\d{1,2}月\d{1,2}日)', full_text[:3000])
    pub_date = dates[0] if len(dates) > 0 else "待核实"
    impl_date = dates[1] if len(dates) > 1 else (dates[0] if dates else "待核实")
    
    # 提取版本/修订信息
    ver_match = re.search(r'(第[一二三四五]次修订|\d{4}年修订)', full_text[:2000])
    version = ver_match.group(1) if ver_match else "正式版"

    # 2. 条文切分
    articles = re.split(r'\n(第[一二三四五六七八九十百]+条)', full_text)
    data = []
    
    if len(articles) <= 1:
        paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 30]
        for i, p in enumerate(paragraphs):
            # 提取段落中的关键词条 (单位/参数)
            keywords = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²|MPa|mg/L)', p)
            data.append({
                "标准号": std_no, "章": "全文内容", "编号": f"段落-{i+1}",
                "全文": p, "展示名称": f"{std_no} ({filename})",
                "发布日期": pub_date, "实施日期": impl_date, "版本": version,
                "关键词": ", ".join(set(keywords)) if keywords else ""
            })
    else:
        current_chapter = "总则"
        chapter_init = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', articles[0])
        if chapter_init: current_chapter = chapter_init.group(1).strip()

        for i in range(1, len(articles), 2):
            article_no = articles[i] 
            article_content = articles[i+1].strip()
            new_chapter = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', article_content)
            
            # 提取条文中的技术参数
            keywords = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²|MPa|mg/L)', article_content)
            
            data.append({
                "标准号": std_no, "章": current_chapter, "编号": article_no,
                "全文": article_content.split('\n第')[0],
                "展示名称": f"{std_no} ({filename})",
                "发布日期": pub_date, "实施日期": impl_date, "版本": version,
                "关键词": ", ".join(set(keywords)) if keywords else ""
            })
            if new_chapter: current_chapter = new_chapter.group(1).strip()

    return pd.DataFrame(data)
