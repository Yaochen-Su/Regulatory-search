import fitz  # PyMuPDF
import docx  # python-docx
import re
import pandas as pd
import os
import pytesseract
from PIL import Image
import io

def extract_text_with_ocr(pdf_path):
    """
    针对扫描版 PDF 执行 OCR 识别。
    在并行模式下，为每个页面独立创建图像流，确保进程安全。
    """
    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            # 使用 2.0 的缩放倍数兼顾速度与识别率
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.open(io.BytesIO(pix.tobytes()))
            # 识别中文简体和英文
            page_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
            full_text += page_text + "\n"
        doc.close() # 显式关闭文件句柄
        return full_text
    except Exception as e:
        return f"OCR 错误: {str(e)}"

def process_document_to_dataframe(file_path):
    """
    并行调用的核心函数。处理单个文件并返回 DataFrame。
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        # 1. 提取文本内容
        if ext == '.pdf':
            doc = fitz.open(file_path)
            # 快速检查前 2 页判定是否为扫描件
            check_text = "".join([doc[i].get_text() for i in range(min(2, len(doc)))])
            
            if len(check_text.strip()) < 50:
                doc.close() # 关闭后交给 OCR 处理
                full_text = extract_text_with_ocr(file_path)
            else:
                full_text = "\n".join([page.get_text() for page in doc])
                doc.close()
                
        elif ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        else:
            return pd.DataFrame()

        # 2. 识别标准号 (如 GB/T 4857.5-92)
        # 匹配模式：字母前缀 + 数字 + 年份
        std_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})'
        std_match = re.search(std_pattern, full_text[:1500].replace('\n', ' '))
        std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

        # 3. 捕捉条款层级 (匹配如 4.1, 5.6.1)
        clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
        clauses = re.findall(clause_pattern, full_text, re.DOTALL)

        structured_data = []
        if not clauses:
            # 针对无编号文档的语义拆分
            paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 15]
            for i, p in enumerate(paragraphs):
                structured_data.append({
                    "标准号": std_no, "条款号": f"P{i+1}", 
                    "内容": p, "技术参数": "全文搜索", "来源文件": filename
                })
        else:
            for cid, content in clauses:
                clean_content = content.replace('\n', ' ').strip()
                # 识别关键参数指标：±2%, 10kg, 2mm 等
                params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²|MPa)', clean_content)
                structured_data.append({
                    "标准号": std_no, "条款号": cid, 
                    "内容": clean_content, 
                    "技术参数": ", ".join(set(params)) if params else "见详情",
                    "来源文件": filename
                })
        
        return pd.DataFrame(structured_data)

    except Exception as e:
        # 在并行模式下，打印错误但不中断主进程
        print(f"处理文件 {filename} 时发生未知错误: {e}")
        return pd.DataFrame()
