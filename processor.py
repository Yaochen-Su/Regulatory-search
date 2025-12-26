import fitz  # PyMuPDF
import docx  # python-docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

# ==========================================
# 💡 本地运行必读：配置 Tesseract 路径
# ==========================================
# 如果你在 Windows 本地运行且报错找不到 Tesseract，请取消下面这行的注释并修改为你的安装路径
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_text_with_ocr(pdf_path):
    """扫描件 OCR 识别逻辑"""
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            # 提高分辨率以确保 ±2% 等微小符号被识别
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes()))
            # 识别简体中文和英文
            full_text += pytesseract.image_to_string(img, lang='chi_sim+eng') + "\n"
        doc.close()
        return full_text
    except Exception as e:
        return f"OCR 解析失败: {str(e)}"

def process_document_to_dataframe(file_path):
    """单文件解析核心逻辑"""
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        # 1. 提取文字
        if ext == '.pdf':
            doc = fitz.open(file_path)
            # 检查前 2 页文字密度
            check_text = "".join([doc[i].get_text() for i in range(min(2, len(doc)))])
            if len(check_text.strip()) < 80: # 判定为扫描件
                doc.close()
                full_text = extract_text_with_ocr(file_path)
            else:
                full_text = "\n".join([page.get_text() for page in doc])
                doc.close()
        elif ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        else:
            return pd.DataFrame()

        # 2. 识别标准号
        std_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})'
        std_match = re.search(std_pattern, full_text[:1500].replace('\n', ' '))
        std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

        # 3. 条款提取 (如 4.1, 5.6.1)
        clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
        clauses = re.findall(clause_pattern, full_text, re.DOTALL)

        data = []
        if not clauses:
            # 兜底分段逻辑
            for i, p in enumerate(full_text.split('\n')):
                if len(p.strip()) > 20:
                    data.append({"标准号": std_no, "条款号": f"P{i}", "内容": p.strip(), "技术参数": "全文", "来源文件": filename})
        else:
            for cid, content in clauses:
                clean_content = content.replace('\n', ' ').strip()
                # 抓取关键物理量 (±2%, 10kg, 2mm等)
                params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|MPa)', clean_content)
                data.append({
                    "标准号": std_no, "条款号": cid, 
                    "内容": clean_content, 
                    "技术参数": ", ".join(set(params)) if params else "见详情",
                    "来源文件": filename
                })
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()
