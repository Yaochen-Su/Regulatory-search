import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """OCR识别扫描件"""
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
            full_text = extract_text_with_ocr(file_path) if len(fast_text.strip()) < 100 else fast_text
        else: return pd.DataFrame()
    except: return pd.DataFrame()

    # 标准号识别 (GB/T 4857.5)
    std_match = re.search(r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})', full_text[:1500].replace('\n', ' '))
    std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

    # 修改后的核心正则：匹配层级编号 (1, 1.1, 1.1.1 等)
    clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    data = []
    if not clauses:
        paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 30]
        for i, p in enumerate(paragraphs):
            data.append({"标准号": std_no, "编号": f"{i+1}", "内容": p.strip(), "技术参数": "全文", "层级": 1})
    else:
        for cid, content in clauses:
            clean_content = re.sub(r'\s+', ' ', content).strip()
            # 技术参数自动提取 (±2%, 10kg 等)
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²|MPa)', clean_content)
            data.append({
                "标准号": std_no, "编号": cid, "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "见详情",
                "层级": cid.count('.') + 1 # 自动计算层级
            })

    return pd.DataFrame(data)
