import fitz  # PyMuPDF
import re
import pandas as pd

def process_pdf_to_dataframe(pdf_path):
    """
    解析标准 PDF 并将其转化为结构化的 DataFrame
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()

    # 1. 提取标准号 (例如 GB/T 4857.5)
    std_no_match = re.search(r'(GB/T\s?\d+\.\d+-\d+|GB\s?\d+\.\d+-\d+)', full_text)
    std_no = std_no_match.group(1) if std_no_match else "未知编号"

    # 2. 正则表达式定义：匹配条款号 (如 4.1, 5.6.1)
    # 匹配规则：行首的数字点号组合
    clause_pattern = r'\n(\d+\.\d+(?:\.\d+)?)\s+(.*?)(?=\n\d+\.\d+|$)'
    
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []

    for cid, content in clauses:
        clean_content = content.replace('\n', ' ').strip()
        
        # 3. 自动提取技术参数 (基于你上传文档中的关键特征)
        # 例如匹配 ±2%, ±5°, 10kg 等 [cite: 1, 10, 14]
        params = []
        if '±' in clean_content or '%' in clean_content:
            found_params = re.findall(r'±\d+%|±\d+°|\d+kg|\d+mm', clean_content)
            params = ", ".join(found_params)
        
        structured_data.append({
            "标准号": std_no,
            "条款号": cid,
            "内容": clean_content,
            "技术参数": params if params else "见详情"
        })

    return pd.DataFrame(structured_data)

def save_to_csv(df, output_path="data/structured_standards.csv"):
    """保存解析结果供 app.py 静态读取"""
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
