import fitz  # PyMuPDF
import docx  # python-docx
import re
import pandas as pd
import os

def extract_text_from_pdf(pdf_path):
    """提取 PDF 文本"""
    doc = fitz.open(pdf_path)
    return "".join([page.get_text() for page in doc])

def extract_text_from_word(word_path):
    """提取 Word (.docx) 文本"""
    doc = docx.Document(word_path)
    return "\n".join([para.text for para in doc.paragraphs])

def process_document_to_dataframe(file_path):
    """
    统一处理函数：支持 PDF 和 Word
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    # 1. 根据格式提取全文
    try:
        if ext == '.pdf':
            full_text = extract_text_from_pdf(file_path)
        elif ext == '.docx':
            full_text = extract_text_from_word(file_path)
        else:
            return pd.DataFrame() # 不支持的格式
    except Exception as e:
        print(f"解析 {filename} 失败: {e}")
        return pd.DataFrame()

    # 2. 增强标准号识别 (针对 GB/T 4857.5 等格式 [cite: 3])
    # 逻辑：先匹配文本，失败则回退到文件名
    std_no_pattern = r'([A-Z/]{2,}\s?\d+\.?\d*-\d+)'
    std_no_match = re.search(std_no_pattern, full_text.replace('\n', ' '))
    std_no = std_no_match.group(1).strip() if std_no_match else os.path.splitext(filename)[0]

    # 3. 条款拆分逻辑
    # 匹配章节号如 4.1, 5.6.1 [cite: 1, 8]
    clause_pattern = r'\n(\d+\.\d+(?:\.\d+)?)\s+(.*?)(?=\n\d+\.\d+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []
    
    if not clauses:
        # 保底方案：按段落拆分
        paragraphs = full_text.split('\n')
        for i, p in enumerate(paragraphs):
            if len(p.strip()) > 15:
                structured_data.append({
                    "标准号": std_no,
                    "条款号": f"段落-{i+1}",
                    "内容": p.strip(),
                    "技术参数": "需人工核对"
                })
    else:
        for cid, content in clauses:
            clean_content = content.replace('\n', ' ').strip()
            # 自动抓取技术参数：如 ±2%, 5°, 10kg 等 [cite: 1, 10, 14]
            params = re.findall(r'±\d+%|±\d+°|\d+kg|\d+mm|\d+mm²|\d+%', clean_content)
            
            structured_data.append({
                "标准号": std_no,
                "条款号": cid,
                "内容": clean_content,
                "技术参数": ", ".join(params) if params else "见全文"
            })

    return pd.DataFrame(structured_data)
