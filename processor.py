import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """针对扫描件进行 OCR 识别"""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        # 将 PDF 页面渲染为图像
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 放大2倍提高识别率
        img = Image.open(io.BytesIO(pix.tobytes()))
        # 调用 Tesseract 识别中文和英文
        page_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
        full_text += page_text + "\n"
    return full_text

def process_document_to_dataframe(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            # 先尝试快速提取
            fast_text = "\n".join([page.get_text() for page in doc])
            
            # 判断逻辑：如果字数过少（比如 5 页纸少于 100 字），则视为扫描件
            if len(fast_text.strip()) < 100:
                full_text = extract_text_with_ocr(file_path)
            else:
                full_text = fast_text
        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
        else: return pd.DataFrame()
    except Exception as e:
        print(f"解析失败: {e}")
        return pd.DataFrame()

    # 标准号识别 (针对 GB/T 4857.5 [cite: 3])
    std_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})'
    std_match = re.search(std_pattern, full_text[:1500].replace('\n', ' '))
    std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

    # 目录识别逻辑：匹配行首章节号，如 4.1, 5.6.1
    clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []
    if not clauses:
        paragraphs = full_text.split('\n')
        for i, p in enumerate(paragraphs):
            if len(p.strip()) > 15:
                structured_data.append({"标准号": std_no, "条款号": f"P{i}", "内容": p.strip(), "技术参数": "全文搜索"})
    else:
        for cid, content in clauses:
            clean_content = content.replace('\n', ' ').strip()
            # 识别类似 ±2%, 5°, 10kg 的技术指标
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²)', clean_content)
            structured_data.append({
                "标准号": std_no,
                "条款号": cid,
                "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "见详情"
            })

    return pd.DataFrame(structured_data)
