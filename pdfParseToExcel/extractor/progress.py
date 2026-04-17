"""
进度管理器 - 显示详细的进度条和时间估算
"""

import time
from typing import Optional
from datetime import datetime, timedelta
from extractor.logger import logger

class ProgressBar:
    """进度条"""
    
    def __init__(self, total: int, desc: str = ""):
        self.total = total
        self.current = 0
        self.desc = desc
        self.start_time = time.time()
        self.last_update = self.start_time
    
    def update(self, n: int = 1):
        """更新进度"""
        
        self.current += n
        now = time.time()
        
        # 每0.5秒更新一次显示
        if now - self.last_update < 0.5 and self.current < self.total:
            return
        
        self.last_update = now
        self._display()
    
    def _display(self):
        """显示进度条"""
        
        elapsed = time.time() - self.start_time
        
        if self.current == 0:
            eta = 0
        else:
            eta = elapsed * (self.total - self.current) / self.current
        
        percentage = self.current / self.total * 100
        
        # 进度条宽度
        bar_width = 40
        filled = int(bar_width * self.current / self.total)
        bar = '█' * filled + '░' * (bar_width - filled)
        
        # 时间格式化
        elapsed_str = self._format_time(elapsed)
        eta_str = self._format_time(eta)
        
        # 输出进度条
        progress_line = (
            f"\r{self.desc} |{bar}| "
            f"{self.current}/{self.total} "
            f"({percentage:6.2f}%) "
            f"已用: {elapsed_str} "
            f"预计: {eta_str}"
        )
        
        logger.info(progress_line)
    
    def finish(self):
        """完成"""
        
        elapsed = time.time() - self.start_time
        elapsed_str = self._format_time(elapsed)
        
        bar_width = 40
        bar = '█' * bar_width
        
        finish_line = (
            f"\r{self.desc} |{bar}| "
            f"{self.total}/{self.total} "
            f"(100.00%) "
            f"总用时: {elapsed_str}"
        )
        
        logger.info(finish_line)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间"""
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

class TimeTracker:
    """时间追踪器"""
    
    def __init__(self):
        self.checkpoints = {}
        self.overall_start = time.time()
    
    def checkpoint(self, name: str):
        """记录检查点"""
        
        self.checkpoints[name] = time.time()
    
    def get_elapsed(self, name: str) -> float:
        """获取耗时"""
        
        if name not in self.checkpoints:
            return 0
        
        return time.time() - self.checkpoints[name]
    
    def get_overall_elapsed(self) -> float:
        """获取总耗时"""
        
        return time.time() - self.overall_start
    
    def format_elapsed(self, name: str) -> str:
        """格式化耗时"""
        
        elapsed = self.get_elapsed(name)
        return self._format_time(elapsed)
    
    def format_overall(self) -> str:
        """格式化总耗时"""
        
        elapsed = self.get_overall_elapsed()
        return self._format_time(elapsed)
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间"""
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            mins = (seconds % 3600) / 60
            return f"{int(hours)}h{int(mins)}m"

class StepTimer:
    """步骤计时器"""
    
    def __init__(self, step_name: str, total_items: int = 0):
        self.step_name = step_name
        self.total_items = total_items
        self.start_time = time.time()
        self.items_completed = 0
        self.progress_bar: Optional[ProgressBar] = None
        
        if total_items > 0:
            self.progress_bar = ProgressBar(
                total_items,
                desc=f"{step_name}"
            )
    
    def update(self, n: int = 1):
        """更新进度"""
        
        self.items_completed += n
        
        if self.progress_bar:
            self.progress_bar.update(n)
    
    def finish(self):
        """完成步骤"""
        
        elapsed = time.time() - self.start_time
        
        if self.progress_bar:
            self.progress_bar.finish()
        
        # 计算速度
        if self.items_completed > 0 and elapsed > 0:
            speed = self.items_completed / elapsed
            
            logger.info(
                f"✅ {self.step_name} 完成"
                f" | 处理: {self.items_completed} "
                f" | 耗时: {self._format_time(elapsed)}"
                f" | 速度: {speed:.2f} 项/秒"
            )
        else:
            logger.info(
                f"✅ {self.step_name} 完成"
                f" | 耗时: {self._format_time(elapsed)}"
            )
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """格式化时间"""
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            mins = (seconds % 3600) / 60
            return f"{int(hours)}h{int(mins)}m"

# 全局实例
time_tracker = TimeTracker()