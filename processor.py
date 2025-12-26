import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """针对扫描版 PDF 执行 OCR 识别"""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        # 提高分辨率以增加 OCR 准确度
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(io.BytesIO(pix.tobytes()))
        # 识别中文和英文
        full_text += pytesseract.image_to_string(img, lang='chi_sim+eng') + "\n"
    return full_text

def process_document_to_dataframe(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            # 尝试直接提取文本
            fast_text = "\n".join([page.get_text() for page in doc])
            # 如果文字密度极低，则触发 OCR [cite: 1]
            if len(fast_text.strip()) < 100:
                full_text = extract_text_with_ocr(file_path)
            else:
                full_text = fast_text
        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"解析 {filename} 失败: {e}")
        return pd.DataFrame()

    # 识别标准号 (如 GB/T 4857.5) [cite: 3]
    std_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})'
    std_match = re.search(std_pattern, full_text[:1500].replace('\n', ' '))
    std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

    # 捕捉条款编号 (如 4.1, 5.6.1) [cite: 1, 8, 19]
    clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []
    if not clauses:
        # 无明确编号时的保底分段
        for i, p in enumerate(full_text.split('\n')):
            if len(p.strip()) > 20:
                structured_data.append({
                    "标准号": std_no, "条款号": f"P{i+1}", 
                    "内容": p.strip(), "技术参数": "查看全文", "来源文件": filename
                })
    else:
        for cid, content in clauses:
            clean_content = content.replace('\n', ' ').strip()
            # 自动抓取技术参数：如 ±2%, 5°, 10kg, 100mm²
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²|MPa)', clean_content)
            structured_data.append({
                "标准号": std_no, "条款号": cid, "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "见详情内容",
                "来源文件": filename
            })

    return pd.DataFrame(structured_data)
