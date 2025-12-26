import fitz  # PyMuPDF
import docx  # python-docx
import re
import pandas as pd
import os

def process_document_to_dataframe(file_path):
    """
    统一解析函数：支持 PDF 和 Word，并提取标准号、条款及关键参数
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    # 1. 提取文本
    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            full_text = "\n".join([page.get_text() for page in doc])
        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"解析错误 {filename}: {e}")
        return pd.DataFrame()

    # 2. 识别标准号 (如 GB/T 4857.5-92) 
    # 策略：正则匹配 -> 关键词寻找 -> 最终回退到文件名
    std_no_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})'
    std_no_match = re.search(std_no_pattern, full_text[:2000].replace('\n', ' '))
    std_no = std_no_match.group(1).strip() if std_no_match else os.path.splitext(filename)[0]

    # 3. 提取条款 (识别 4.1, 5.6.1 等层级) [cite: 1, 19]
    clause_pattern = r'\n(\d+(?:\.\d+){1,2})\s+(.*?)(?=\n\d+(?:\.\d+){1,2}\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []
    
    if not clauses:
        # 保底方案：按长段落切分
        paragraphs = full_text.split('\n')
        for i, p in enumerate(paragraphs):
            if len(p.strip()) > 20:
                structured_data.append({
                    "标准号": std_no,
                    "条款号": f"段落-{i+1}",
                    "内容": p.strip(),
                    "技术参数": "查看全文"
                })
    else:
        for cid, content in clauses:
            clean_content = content.replace('\n', ' ').strip()
            # 提取数字和单位 (如 ±2%, 5°, 10kg, 100mm²) [cite: 1, 10, 14]
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²)', clean_content)
            
            structured_data.append({
                "标准号": std_no,
                "条款号": cid,
                "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "见详情"
            })

    return pd.DataFrame(structured_data)
