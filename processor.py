import fitz  # PyMuPDF
import docx  # python-docx
import re
import pandas as pd
import os

def process_document_to_dataframe(file_path):
    """
    极简文本解析器：仅处理文本型PDF和Word
    """
    filename = os.path.basename(file_path)
    ext = os.path.splitext(filename)[1].lower()
    full_text = ""

    try:
        # 1. 文本提取
        if ext == '.pdf':
            with fitz.open(file_path) as doc:
                full_text = "\n".join([page.get_text() for page in doc])
        elif ext == '.docx':
            doc_obj = docx.Document(file_path)
            full_text = "\n".join([p.text for p in doc_obj.paragraphs])
        else:
            return pd.DataFrame()

        # 如果提取出的文本太少，判定为无效或扫描件，直接返回空
        if len(full_text.strip()) < 50:
            return pd.DataFrame()

        # 2. 识别标准号 (如 GB/T 4857.5)
        std_match = re.search(r'([A-Z/]{2,}\s?\d+\.?\d*-\d{2,4})', full_text[:1500].replace('\n', ' '))
        std_no = std_match.group(1).strip() if std_match else os.path.splitext(filename)[0]

        # 3. 提取条款 (识别 4.1, 5.6.1 等层级)
        clause_pattern = r'\n(\d+(?:\.\d+)*)\s+(.*?)(?=\n\d+(?:\.\d+)*\s+|$)'
        clauses = re.findall(clause_pattern, full_text, re.DOTALL)

        structured_data = []
        if not clauses:
            # 语义切分保底
            paragraphs = [p.strip() for p in full_text.split('\n') if len(p.strip()) > 20]
            for i, p in enumerate(paragraphs):
                structured_data.append({
                    "标准号": std_no, "条款号": f"段落-{i+1}", 
                    "内容": p, "技术参数": "文本内容", "来源文件": filename
                })
        else:
            for cid, content in clauses:
                clean_content = content.replace('\n', ' ').strip()
                # 抓取物理量 (如 ±2%, 10kg)
                params = re.findall(r'±?\d+(?:\.\d+)?(?:%|°|mm|kg|MPa)', clean_content)
                structured_data.append({
                    "标准号": std_no, "条款号": cid, 
                    "内容": clean_content, 
                    "技术参数": ", ".join(set(params)) if params else "见详情",
                    "来源文件": filename
                })
        
        return pd.DataFrame(structured_data)

    except Exception as e:
        print(f"解析 {filename} 失败: {e}")
        return pd.DataFrame()
