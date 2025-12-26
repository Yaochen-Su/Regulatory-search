import fitz
import docx
import re
import pandas as pd
import os

def process_document_to_dataframe(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            full_text = "\n".join([page.get_text() for page in doc])
        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
        else: return pd.DataFrame()
    except: return pd.DataFrame()

    # 1. 识别标准号 (如 GB/T 4857.5-92) [cite: 3]
    std_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})'
    std_match = re.search(std_pattern, full_text[:1000].replace('\n', ' '))
    std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

    # 2. 增强版目录识别正则
    # 匹配模式：行首的 1, 4.1, 5.6.1 等
    clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []
    if not clauses:
        # 保底拆分
        for i, p in enumerate(full_text.split('\n')):
            if len(p.strip()) > 20:
                structured_data.append({"标准号": std_no, "条款号": f"P{i}", "内容": p.strip(), "技术参数": "全文内容"})
    else:
        for cid, content in clauses:
            clean_content = content.replace('\n', ' ').strip()
            # 提取百分比、度数等参数 [cite: 10, 12, 14, 15]
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|mm²)', clean_content)
            structured_data.append({
                "标准号": std_no,
                "条款号": cid,
                "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "核心条文"
            })

    return pd.DataFrame(structured_data)
