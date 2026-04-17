"""
数据规范化器
"""

from extractor.logger import logger

def normalize(item: dict) -> dict:
    """
    规范化数据项
    
    清理和标准化各个字段
    """
    
    if not isinstance(item, dict):
        return {}
    
    cleaned = {}
    
    for key, value in item.items():
        try:
            v = str(value or "").strip()
            
            # 替换特殊字符
            v = v.replace("\r\n", " ")
            v = v.replace("\n", " ")
            v = v.replace("\t", " ")
            
            # 合并多个空格
            v = " ".join(v.split())
            
            # 限制长度
            if len(v) > 500:
                v = v[:497] + "..."
            
            cleaned[key] = v
        
        except Exception as e:
            logger.debug(f"规范化失败 {key}: {e}")
            cleaned[key] = ""
    
    return cleaned