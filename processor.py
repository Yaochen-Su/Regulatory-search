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

    dates = re.findall(r'(\d{4}年\d{1,2}月\d{1,2}日)', full_text[:2000])
    pub_date = dates[0] if len(dates) > 0 else ""
    impl_date = dates[1] if len(dates) > 1 else (dates[0] if dates else "")
    ver_match = re.search(r'(第[一二三四五]次修订|\d{4}年修订)', full_text[:2000])
    version = ver_match.group(1) if ver_match else "正式版"

    # 技术关键词匹配
    keyword_regex = r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|MPa|mg/L|kPa|min|℃|kV|A)'
    
    # 按“条”切分
    articles = re.split(r'\n(第[一二三四五六七八九十百]+条)', full_text)
    data = []

    if len(articles) <= 1:
        # 全文模式：不强制添加“段落”编号
        keywords = re.findall(keyword_regex, full_text)
        data.append({
            "文件名": filename,
            "章": "正文",
            "编号": "",
            "全文": full_text,
            "发布日期": pub_date,
            "实施日期": impl_date,
            "版本": version,
            "关键词": ",".join(set(keywords)) if keywords else ""
        })
    else:
        current_chapter = "正文"
        chapter_match = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', articles[0])
        if chapter_match: current_chapter = chapter_match.group(1).strip()

        for i in range(1, len(articles), 2):
            article_no = articles[i] 
            article_content = articles[i+1].strip()
            new_chapter = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', article_content)
            keywords = re.findall(keyword_regex, article_content)
            data.append({
                "文件名": filename,
                "章": current_chapter,
                "编号": article_no,
                "全文": article_content.split('\n第')[0],
                "发布日期": pub_date,
                "实施日期": impl_date,
                "版本": version,
                "关键词": ",".join(set(keywords)) if keywords else ""
            })
            if new_chapter: current_chapter = new_chapter.group(1).strip()

    return pd.DataFrame(data)
