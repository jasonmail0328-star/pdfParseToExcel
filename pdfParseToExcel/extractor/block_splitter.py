"""
文本块分割器 - 按各种规则分割文本
"""

import re
from typing import List
from extractor.logger import logger

def split_blocks(text: str, min_length: int = 50) -> List[str]:
    """
    分割文本块
    
    按多种规则分割，优先级从高到低
    """
    
    if not text or not text.strip():
        return []
    
    blocks = []
    
    # 规则1: 按"问题 X / Y"分割
    pattern = r'(?=问题\s+\d+\s*/\s*\d+)'
    blocks = re.split(pattern, text)
    
    if len(blocks) > 1:
        blocks = [b.strip() for b in blocks if len(b.strip()) > min_length]
        logger.debug(f"规则1分割: {len(blocks)} 个块")
        return blocks
    
    # 规则2: 按严重性开头分割
    pattern = r'(?=(?:紧急|紧|高|中|低)\s*(?:\n|$))'
    blocks = re.split(pattern, text)
    
    if len(blocks) > 1:
        blocks = [b.strip() for b in blocks if len(b.strip()) > min_length]
        logger.debug(f"规则2分割: {len(blocks)} 个块")
        return blocks
    
    # 规则3: 按多个换行符分割
    blocks = re.split(r'\n\n\n+', text)
    
    if len(blocks) > 1:
        blocks = [b.strip() for b in blocks if len(b.strip()) > min_length * 1.5]
        logger.debug(f"规则3分割: {len(blocks)} 个块")
        return blocks
    
    # 规则4: 按空行分割
    blocks = re.split(r'\n\n', text)
    
    if len(blocks) > 1:
        blocks = [b.strip() for b in blocks if len(b.strip()) > min_length * 2]
        logger.debug(f"规则4分割: {len(blocks)} 个块")
        return blocks
    
    # 没有分割，返回整个文本
    logger.debug(f"未进行分割，返回整个文本")
    return [text]