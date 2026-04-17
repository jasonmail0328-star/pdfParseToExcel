"""
OCR引擎 - 线程安全版本（使用互斥锁）
"""

import numpy as np
import threading
from paddleocr import PaddleOCR
from extractor.logger import logger
from config import OCR_LANG, OCR_USE_GPU, OCR_ANGLE_CLS, OCR_SCORE_THRESHOLD

class OCREngine:
    """OCR引擎 - 单例模式 + 线程安全"""
    
    _instance = None
    _lock = threading.Lock()  # ✅ 添加全局锁
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        logger.info("初始化OCR引擎（线程安全模式）...")
        
        try:
            # 创建OCR实例（非线程安全）
            self.ocr = PaddleOCR(
                use_angle_cls=OCR_ANGLE_CLS,
                lang=OCR_LANG,
                show_log=False,
                use_gpu=OCR_USE_GPU,
                enable_mkldnn=True,
                cpu_threads=4,
            )
            
            # 创建OCR操作的互斥锁
            self.ocr_lock = threading.Lock()
            
            self._initialized = True
            logger.info("✅ OCR引擎初始化成功（线程安全）")
        except Exception as e:
            logger.error(f"❌ OCR初始化失败: {e}")
            self.ocr = None
            self._initialized = True
    
    def run(self, image_array: np.ndarray) -> str:
        """
        运行OCR - 线程安全版本
        
        使用互斥锁确保同一时间只有一个线程调用OCR
        """
        
        if self.ocr is None:
            logger.warning("OCR引擎未初始化，跳过OCR")
            return ""
        
        if not isinstance(image_array, np.ndarray):
            logger.warning("输入不是numpy数组")
            return ""
        
        if image_array.size == 0:
            return ""
        
        # ✅ 使用锁保护OCR调用
        with self.ocr_lock:
            try:
                logger.debug("开始OCR识别...")
                
                # 快速模式：cls=False, 不进行角度分类
                result = self.ocr.ocr(image_array, cls=False)
                
                texts = []
                
                if result and result[0]:
                    for line in result[0]:
                        if not line:
                            continue
                        
                        try:
                            text = line[1][0]
                            score = line[1][1]
                            
                            # 降低阈值，接受更多候选（Ollama会清理）
                            if score > OCR_SCORE_THRESHOLD:
                                texts.append(text)
                        except (IndexError, TypeError):
                            continue
                
                logger.debug(f"✅ OCR完成: {len(texts)} 行文本")
                return "\n".join(texts) if texts else ""
            
            except Exception as e:
                logger.error(f"❌ OCR识别失败: {e}")
                return ""