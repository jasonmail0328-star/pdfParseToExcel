"""
字段解析器 - 从文本中提取特定字段
"""

import re
from typing import Optional
from extractor.logger import logger

def safe_get(pattern: str, text: str, default: str = "", flags=re.IGNORECASE | re.MULTILINE) -> str:
    """安全的正则提取"""
    
    try:
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else default
    except Exception as e:
        logger.debug(f"正则提取失败: {e}")
        return default

def parse_block(block: str) -> Optional[dict]:
    """
    解析文本块为结构化数据
    
    提取：
    - 问题名称
    - 严重性
    - URL
    - 实体
    - 风险
    - 原因
    - CVSS
    """
    
    if not block or len(block.strip()) < 50:
        return None
    
    lines = [l.strip() for l in block.split("\n") if l.strip()]
    
    result = {
        "问题": "",
        "严重性": "",
        "URL": "",
        "实体": "",
        "风险": "",
        "原因": "",
        "CVSS": "",
    }
    
    # 提取问题标题
    for line in lines:
        if (len(line) > 10 and len(line) < 100
            and not any(kw in line for kw in ['严重性', '户重性', 'CVSS', 'URL', '实体', '风险', '原因', '：'])):
            result["问题"] = line
            break
    
    # 提取严重性
    result["严重性"] = safe_get(r'(?:户重性|严重性)[：:]\s*\n?\s*(\S+)', block)
    if not result["严重性"]:
        result["严重性"] = safe_get(r'(?:户重性|严重性)[：:]\s*(\S+)', block)
    
    # 提取URL
    result["URL"] = safe_get(r'URL[：:]\s*\n?\s*(https?://[^\n\s]+)', block)
    if not result["URL"]:
        result["URL"] = safe_get(r'(https?://[^\n\s]+)', block)
    
    # 提取实体
    result["实体"] = safe_get(r'实体[：:]\s*\n?\s*(.+?)(?:\n|$)', block)
    
    # 提取风险
    result["风险"] = safe_get(r'风险[：:]\s*\n?\s*(.+?)(?:\n|$)', block)
    
    # 提取原因
    result["原因"] = safe_get(r'原因[：:]\s*\n?\s*(.+?)(?:\n|$)', block, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    # 提取CVSS
    result["CVSS"] = safe_get(r'CVSS\s*(?:分数)?[：:]\s*([\d.]+)', block)
    
    # 验证结果
    if not result["严重性"] and not result["URL"]:
        return None
    
    return result