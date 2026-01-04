import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """仅针对纯扫描版 PDF 执行 OCR"""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes()))
        full_text += pytesseract.image_to_string(img, lang='chi_sim+eng') + "\n"
    return full_text

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
            fast_text = "\n".join([page.get_text() for page in doc])
            # 文字层检测判定
            full_text = extract_text_with_ocr(file_path) if len(fast_text.strip()) < 100 else fast_text
        else: return pd.DataFrame()
    except: return pd.DataFrame()

    # 1. 提取法规/标准标题
    title_search = re.search(r'^(.{2,50}条例|.{2,50}办法|.{2,50}标准)', full_text.strip().split('\n')[0])
    std_no = title_search.group(1).strip() if title_search else os.path.splitext(filename)[0]

    # 2. 识别章、条层级
    # 支持 "第一章 总则" 和 "第一条 为了..." 这种格式
    articles = re.split(r'\n(第[一二三四五六七八九十百]+条)', full_text)
    
    data = []
    current_chapter = "未分类"
    
    # 处理分割后的文本
    # articles[0] 通常是前言或第一章标题
    chapter_match = re.search(r'(第[一二三四五六七八九十百]+章\s*.*)', articles[0])
    if chapter_match: current_chapter = chapter_match.group(1).strip()

    for i in range(1, len(articles), 2):
        article_no = articles[i] # "第一条"
        article_content = articles[i+1].strip() # 内容
        
        # 检查内容中是否包含新的“章”标题
        new_chapter = re.search(r'(第[一二三四五六七八九十百]+章\s*.*)', article_content)
        
        # 提取参数 (如日期、百分比等)
        params = re.findall(r'(\d{4}年\d{1,2}月\d{1,2}日|±?\d+(?:\.\d+)?(?:%|mm|kg))', article_content)
        
        data.append({
            "标准号": std_no,
            "章": current_chapter,
            "编号": article_no,
            "内容": article_content.split('\n')[0], # 仅取第一段作为主要内容
            "全文": article_content,
            "技术参数": ", ".join(set(params)) if params else "见原文",
            "层级": 2
        })
        
        if new_chapter:
            current_chapter = new_chapter.group(1).strip()

    return pd.DataFrame(data)
