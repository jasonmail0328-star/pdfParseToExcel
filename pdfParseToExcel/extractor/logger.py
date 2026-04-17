"""
日志系统
"""

import logging
import sys
from pathlib import Path
from config import LOG_LEVEL, LOG_FILE

def setup_logger(name):
    """设置日志系统"""
    
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # 清除已有处理器
    logger.handlers.clear()
    
    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    try:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.encoding = 'utf-8'
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"设置控制台日志失败: {e}")
    
    # 文件处理器
    try:
        file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"无法创建日志文件: {e}")
    
    return logger

# 全局日志对象
logger = setup_logger("PDF-Extractor")