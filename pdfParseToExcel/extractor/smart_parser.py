"""
智能解析器 - 支持多线程
"""

import re
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from extractor.logger import logger
from extractor.block_splitter import split_blocks
from extractor.field_parser import parse_block
from extractor.gpt_parser import parse_blocks as gpt_parse_blocks
from config import MAX_WORKERS, ENABLE_THREADING

def parse_page_smart(page_text: str, page_ocr: str = "") -> List[Dict]:
    """
    智能解析页面
    
    策略：
    1. 合并内容
    2. 分割成块
    3. 用Ollama解析
    """
    
    if not page_text and not page_ocr:
        return []
    
    # 合并文本（OCR优先，因为图片内容更完整）
    full_text = (page_ocr or "") + "\n" + (page_text or "")
    
    if not full_text.strip():
        return []
    
    # 分割块
    blocks = split_blocks(full_text, min_length=50)
    
    if not blocks:
        return []
    
    logger.debug(f"分割得到 {len(blocks)} 个块，总大小 {sum(len(b) for b in blocks)} 字符")
    
    # 直接用Ollama解析
    try:
        results = gpt_parse_blocks(blocks)
        
        if results:
            logger.debug(f"Ollama解析: {len(results)} 成功")
            return results
        else:
            logger.debug(f"Ollama解析: 0个成功")
            
            # 备选：尝试字段解析
            logger.debug(f"使用字段解析作为备选...")
            results = []
            
            # 使用多线程加速字段解析
            if ENABLE_THREADING and MAX_WORKERS > 1 and len(blocks) > 5:
                results = _parse_blocks_field_threaded(blocks)
            else:
                for block in blocks:
                    vuln = parse_block(block)
                    if vuln:
                        results.append(vuln)
            
            return results
    
    except Exception as e:
        logger.error(f"解析失败: {e}")
        
        # 最后备选：字段解析
        try:
            results = []
            for block in blocks:
                vuln = parse_block(block)
                if vuln:
                    results.append(vuln)
            
            return results
        except:
            return []

def _parse_blocks_field_threaded(blocks: List[str]) -> List[Dict]:
    """多线程进行字段解析"""
    
    results = [None] * len(blocks)
    
    logger.debug(f"使用 {MAX_WORKERS} 个线程进行字段解析")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        futures = {
            executor.submit(parse_block, block): i 
            for i, block in enumerate(blocks)
        }
        
        # 处理完成的任务
        from concurrent.futures import as_completed
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception as e:
                logger.debug(f"块{index+1}字段解析失败: {e}")
    
    # 过滤掉None
    return [r for r in results if r is not None]