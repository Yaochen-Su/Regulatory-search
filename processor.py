import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """OCR 识别 (仅针对扫描件)"""
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
        # 1. Word 文档：绝对不走 OCR，秒级提取
        if ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        
        # 2. PDF 文档：文字层检测
        elif ext == '.pdf':
            doc = fitz.open(file_path)
            fast_text = "\n".join([page.get_text() for page in doc])
            # 文字密度极低判定为扫描件
            if len(fast_text.strip()) < 100:
                full_text = extract_text_with_ocr(file_path)
            else:
                full_text = fast_text
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    # 识别标准号
    std_match = re.search(r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})', full_text[:1500].replace('\n', ' '))
    std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

    # 条款识别正则
    clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    data = []
    if not clauses:
        for i, p in enumerate(full_text.split('\n')):
            if len(p.strip()) > 20:
                data.append({"标准号": std_no, "条款号": f"P{i+1}", "内容": p.strip(), "技术参数": "全文内容", "来源文件": filename})
    else:
        for cid, content in clauses:
            clean_content = content.replace('\n', ' ').strip()
            # 物理参数识别要求 (±2%, 10kg 等)
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²|MPa)', clean_content)
            data.append({
                "标准号": std_no, "条款号": cid, "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "见详情内容",
                "来源文件": filename
            })

    return pd.DataFrame(data)
