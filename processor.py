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
    except Exception as e:
        print(f"读取文件失败 {filename}: {e}")
        return pd.DataFrame()

    # 清洗文本
    full_text = full_text.strip()
    if not full_text:
        return pd.DataFrame()

    # 1. 提取标题 (保底方案)
    title_search = re.search(r'([^\n]{2,50}(?:条例|办法|标准|规定|文件|通知))', full_text[:2000])
    std_no = title_search.group(1).strip() if title_search else os.path.splitext(filename)[0]

    # 2. 识别“第X条”或“第X章”
    articles = re.split(r'\n(第[一二三四五六七八九十百]+条)', full_text)
    
    data = []
    if len(articles) <= 1:
        # 如果没有识别到“第X条”，则进行段落保底切分
        paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 30]
        for i, p in enumerate(paragraphs):
            data.append({
                "标准号": std_no,
                "章": "全文内容",
                "编号": f"段落-{i+1}",
                "全文": p,
                "展示名称": f"{std_no} ({filename})"
            })
    else:
        # 正常的法规解析逻辑
        current_chapter = "总则"
        chapter_init = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', articles[0])
        if chapter_init: current_chapter = chapter_init.group(1).strip()

        for i in range(1, len(articles), 2):
            article_no = articles[i] 
            article_content = articles[i+1].strip()
            # 检查是否有新章节
            new_chapter = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', article_content)
            
            data.append({
                "标准号": std_no,
                "章": current_chapter,
                "编号": article_no,
                "全文": article_content.split('\n第')[0], # 防止章节标题混入
                "展示名称": f"{std_no} ({filename})"
            })
            if new_chapter:
                current_chapter = new_chapter.group(1).strip()

    return pd.DataFrame(data)
