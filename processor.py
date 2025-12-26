import fitz
import docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

# 💡 请在此处修正您的 Tesseract 路径
TESS_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(TESS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESS_PATH

def process_document_to_dataframe(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
            with fitz.open(file_path) as doc:
                # 先尝试提取文本
                full_text = "\n".join([page.get_text() for page in doc])
                # 如果是扫描件（字数太少），尝试 OCR
                if len(full_text.strip()) < 100:
                    ocr_text = ""
                    for page in doc:
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                        img = Image.open(io.BytesIO(pix.tobytes()))
                        ocr_text += pytesseract.image_to_string(img, lang='chi_sim+eng') + "\n"
                    full_text = ocr_text
        elif ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        
        # 提取标准号
        std_match = re.search(r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})', full_text[:1000].replace('\n', ' '))
        std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

        # 提取条款
        clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
        clauses = re.findall(clause_pattern, full_text, re.DOTALL)

        results = []
        if not clauses:
            results.append({"标准号": std_no, "条款号": "全文", "内容": full_text[:2000], "技术参数": "查看原件", "来源文件": filename})
        else:
            for cid, content in clauses:
                clean_content = content.replace('\n', ' ').strip()
                params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg)', clean_content)
                results.append({
                    "标准号": std_no, "条款号": cid, "内容": clean_content, 
                    "技术参数": ", ".join(set(params)) if params else "见详情",
                    "来源文件": filename
                })
        return pd.DataFrame(results)
    except Exception as e:
        # 返回一个包含错误信息的单行数据，而不是崩溃
        return pd.DataFrame([{"标准号": "错误", "条款号": "N/A", "内容": f"解析失败: {str(e)}", "技术参数": "N/A", "来源文件": filename}])
