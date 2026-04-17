"""
Pipeline管理器 - 支持分步执行和断点恢复
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from extractor.logger import logger
from config import (
    ENABLE_CHECKPOINT, CHECKPOINT_INTERVAL, CHECKPOINT_DIR,
    TEMP_PDF_PAGES, TEMP_VULNS
)

class Pipeline:
    """Pipeline执行器"""
    
    def __init__(self, name: str):
        self.name = name
        self.checkpoint_dir = Path(CHECKPOINT_DIR)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save_checkpoint(self, step: str, data: Any, page_num: int = 0):
        """保存checkpoint"""
        
        if not ENABLE_CHECKPOINT:
            return
        
        try:
            checkpoint_file = self.checkpoint_dir / f"{self.name}_{step}_{page_num}.json"
            
            # 处理不同数据类型
            if isinstance(data, list):
                json_data = data
            elif isinstance(data, dict):
                json_data = data
            else:
                json_data = str(data)
            
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ Checkpoint保存: {checkpoint_file.name}")
        
        except Exception as e:
            logger.warning(f"保存checkpoint失败: {e}")
    
    def load_checkpoint(self, step: str, page_num: int = 0) -> Optional[Any]:
        """加载checkpoint"""
        
        if not ENABLE_CHECKPOINT:
            return None
        
        try:
            checkpoint_file = self.checkpoint_dir / f"{self.name}_{step}_{page_num}.json"
            
            if checkpoint_file.exists():
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                logger.info(f"✅ Checkpoint加载: {checkpoint_file.name}")
                return data
        
        except Exception as e:
            logger.debug(f"加载checkpoint失败: {e}")
        
        return None
    
    def save_temp_pages(self, pages: List[Dict]):
        """保存临时页面数据"""
        
        try:
            with open(TEMP_PDF_PAGES, 'w', encoding='utf-8') as f:
                json.dump(pages, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ 临时页面保存: {len(pages)} 页")
        except Exception as e:
            logger.warning(f"保存临时页面失败: {e}")
    
    def load_temp_pages(self) -> Optional[List[Dict]]:
        """加载临时页面数据"""
        
        try:
            if TEMP_PDF_PAGES.exists():
                with open(TEMP_PDF_PAGES, 'r', encoding='utf-8') as f:
                    pages = json.load(f)
                
                logger.info(f"✅ 加载已提取的PDF: {len(pages)} 页")
                return pages
        except Exception as e:
            logger.debug(f"加载临时页面失败: {e}")
        
        return None
    
    def save_temp_vulns(self, vulns: List[Dict]):
        """保存临时漏洞数据"""
        
        try:
            with open(TEMP_VULNS, 'w', encoding='utf-8') as f:
                json.dump(vulns, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"✅ 临时漏洞保存: {len(vulns)} 条")
        except Exception as e:
            logger.warning(f"保存临时漏洞失败: {e}")
    
    def load_temp_vulns(self) -> Optional[List[Dict]]:
        """加载临时漏洞数据"""
        
        try:
            if TEMP_VULNS.exists():
                with open(TEMP_VULNS, 'r', encoding='utf-8') as f:
                    vulns = json.load(f)
                
                logger.info(f"✅ 加载已解析的漏洞: {len(vulns)} 条")
                return vulns
        except Exception as e:
            logger.debug(f"加载临时漏洞失败: {e}")
        
        return None
    
    def clear_temp_files(self):
        """清理临时文件"""
        
        try:
            if TEMP_PDF_PAGES.exists():
                TEMP_PDF_PAGES.unlink()
            if TEMP_VULNS.exists():
                TEMP_VULNS.unlink()
            
            logger.debug("✅ 临时文件已清理")
        except Exception as e:
            logger.warning(f"清理临时文件失败: {e}")

# 全局pipeline实例
pipeline = Pipeline("pdf_extraction")