import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """针对纯扫描版 PDF 执行 OCR"""
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
    except Exception as e:
        print(f"解析文件 {filename} 失败: {e}")
        return pd.DataFrame()

    # 1. 更加灵活的标题提取逻辑
    # 优先匹配含有“条例/办法/规定”的行，若无则使用文件名
    title_search = re.search(r'([^\n]{2,50}(?:条例|办法|标准|规定|文件))', full_text[:2000])
    std_no = title_search.group(1).strip() if title_search else os.path.splitext(filename)[0]

    # 2. 识别“第X条”层级
    articles = re.split(r'\n(第[一二三四五六七八九十百]+条)', full_text)
    
    data = []
    current_chapter = "总则"
    
    # 解析首段中的章节信息
    chapter_init = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', articles[0])
    if chapter_init: current_chapter = chapter_init.group(1).strip()

    for i in range(1, len(articles), 2):
        article_no = articles[i] 
        article_content = articles[i+1].strip()
        
        # 检查内容中是否包含新的章节标题
        new_chapter = re.search(r'(第[一二三四五六七八九十百]+章\s*[^\n]*)', article_content)
        
        # 提取关键日期或技术参数
        params = re.findall(r'(\d{4}年\d{1,2}月\d{1,2}日|±?\d+(?:\.\d+)?(?:%|°|mm|kg))', article_content)
        
        data.append({
            "标准号": std_no,
            "章": current_chapter,
            "编号": article_no,
            "内容": article_content.split('\n')[0][:120],
            "全文": article_content,
            "技术参数": ", ".join(set(params)) if params else "见原文",
            "来源文件": filename
        })
        
        if new_chapter:
            current_chapter = new_chapter.group(1).strip()

    return pd.DataFrame(data)
