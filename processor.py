import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """OCR 识别逻辑"""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes()))
        full_text += pytesseract.image_to_string(img, lang='chi_sim+eng') + "\n"
    doc.close()
    return full_text

def process_document_to_dataframe(file_path, ocr_enabled=False):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        if ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        elif ext == '.pdf':
            if ocr_enabled:
                full_text = extract_text_with_ocr(file_path)
            else:
                doc = fitz.open(file_path)
                full_text = "\n".join([page.get_text() for page in doc])
                doc.close()
        else: return pd.DataFrame()
    except: return pd.DataFrame()

    if not full_text.strip(): return pd.DataFrame()

    # 提取规章标题
    title_search = re.search(r'([^\n]{2,50}(?:条例|办法|标准|规定|文件))', full_text[:2000])
    std_no = title_search.group(1).strip() if title_search else os.path.splitext(filename)[0]

    # 条文识别 (第X条)
    articles = re.split(r'\n(第[一二三四五六七八九十百]+条)', full_text)
    data = []
    current_chapter = "总则"
    chapter_init = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', articles[0])
    if chapter_init: current_chapter = chapter_init.group(1).strip()

    for i in range(1, len(articles), 2):
        article_no = articles[i] 
        article_content = articles[i+1].strip()
        new_chapter = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', article_content)
        data.append({"标准号": std_no, "章": current_chapter, "编号": article_no, "内容": article_content.split('\n')[0][:120], "全文": article_content})
        if new_chapter: current_chapter = new_chapter.group(1).strip()

    return pd.DataFrame(data)
