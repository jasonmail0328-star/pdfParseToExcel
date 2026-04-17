"""
线程池管理器 - 支持并发处理
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Any, Optional
from extractor.logger import logger
from config import MAX_WORKERS

class ThreadPool:
    """线程池包装器"""
    
    def __init__(self, max_workers: int = MAX_WORKERS):
        self.max_workers = max_workers if max_workers > 0 else 1
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.lock = threading.Lock()
    
    def map(self, func: Callable, items: List[Any], desc: str = "") -> List[Any]:
        """
        并发执行函数
        
        Args:
            func: 执行的函数
            items: 输入列表
            desc: 描述
        
        Returns:
            结果列表
        """
        
        if self.max_workers <= 1:
            # 单线程模式，直接执行
            return [func(item) for item in items]
        
        logger.info(f"使用 {self.max_workers} 个线程处理 {len(items)} 个项目 ({desc})")
        
        results = [None] * len(items)
        completed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(func, item): i 
                for i, item in enumerate(items)
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                
                try:
                    results[index] = future.result()
                    completed += 1
                    
                    # 进度输出
                    if completed % max(1, len(items) // 10) == 0:
                        progress = completed / len(items) * 100
                        logger.debug(f"进度: {completed}/{len(items)} ({progress:.1f}%)")
                
                except Exception as e:
                    logger.warning(f"项目 {index} 处理失败: {e}")
                    results[index] = None
        
        return results
    
    def shutdown(self):
        """关闭线程池"""
        
        self.executor.shutdown(wait=True)