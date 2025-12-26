import fitz
import docx
import re
import pandas as pd
import os

def clean_text(text):
    """清理文本干扰，合并被意外切断的行"""
    return re.sub(r'\s+', ' ', text).strip()

def extract_std_no(text, filename):
    """
    多重策略提取标准号
    """
    # 策略 1: 严格匹配 (如 GB/T 4857.5-92)
    patterns = [
        r'([A-Z]{1,}/[A-Z]\s?\d+\.?\d*-\d{2,4})', # GB/T 格式
        r'([A-Z]{2,}\s?\d+\.?\d*-\d{2,4})',      # GB, ISO 格式
        r'(T/[A-Z]{2,}\s?\d+-\d{4})'             # 团体标准格式
    ]
    
    for p in patterns:
        match = re.search(p, text)
        if match:
            return match.group(1).replace(" ", "")

    # 策略 2: 关键字辅助 (寻找“标准号：”之后的字符)
    keyword_match = re.search(r'(?:标准号|标准编号)[:：]\s*([A-Za-z0-9\./-]{5,})', text)
    if keyword_match:
        return keyword_match.group(1).strip()

    # 策略 3: 最终保底 - 使用去后缀的文件名
    return os.path.splitext(filename)[0]

def process_document_to_dataframe(file_path):
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    
    # 1. 提取全文
    try:
        if ext == '.pdf':
            doc = fitz.open(file_path)
            # 使用 blocks 模式保留更好的物理结构
            full_text = "\n".join([page.get_text("text") for page in doc])
        elif ext == '.docx':
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    # 2. 确定标准号
    std_no = extract_std_no(full_text[:2000], filename) # 只在前2000字找编号

    # 3. 条款提取逻辑 - 增强版
    # 匹配规则：1. 1.1 4.1 5.6.1 这种典型的标准层级
    # 同时也匹配常见的“第X条”
    clause_pattern = r'\n(\d+(?:\.\d+){0,2})\s+(.*?)(?=\n\d+(?:\.\d+){0,2}\s+|$)'
    clauses = re.findall(clause_pattern, full_text, re.DOTALL)

    structured_data = []
    
    # 如果正则没抓到，说明排版非常特殊，启动“段落语义拆分”
    if len(clauses) < 3:
        # 寻找包含“应”、“不得”、“要求”等合规词汇的长句子
        paragraphs = full_text.split('\n')
        for i, p in enumerate(paragraphs):
            p = p.strip()
            if len(p) > 20 and any(keyword in p for keyword in ['应', '不', '要求', '必须', '误差']):
                structured_data.append({
                    "标准号": std_no,
                    "条款号": f"文本段-{i}",
                    "内容": p,
                    "技术参数": "自动识别中"
                })
    else:
        for cid, content in clauses:
            clean_content = clean_text(content)
            # 提取数字和单位 (如 10kg, 2mm, ±2%) [cite: 1, 10]
            params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|MPa|s|min|h)', clean_content)
            
            structured_data.append({
                "标准号": std_no,
                "条款号": cid,
                "内容": clean_content,
                "技术参数": ", ".join(set(params)) if params else "见详情"
            })

    return pd.DataFrame(structured_data)
