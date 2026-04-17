"""
硬件检测器 - 自动选择最优模型
"""

import subprocess
import re
from extractor.logger import logger

class HardwareDetector:
    """硬件检测"""
    
    def __init__(self):
        self.gpu_available = False
        self.gpu_vram = 0
        self.cpu_cores = 0
        self.system_ram = 0
        self.detect()
    
    def detect(self):
        """检测硬件"""
        
        logger.info("检测硬件配置...")
        
        # 检测GPU
        self.check_gpu()
        
        # 检测CPU和内存
        self.check_cpu_ram()
        
        logger.info(f"  GPU: {'✅ 可用' if self.gpu_available else '❌ 不可用'}")
        if self.gpu_available:
            logger.info(f"  GPU显存: {self.gpu_vram}GB")
        logger.info(f"  CPU核心: {self.cpu_cores}")
        logger.info(f"  系统内存: {self.system_ram}GB")
    
    def check_gpu(self):
        """检测GPU是否可用"""
        
        try:
            # 尝试检测NVIDIA GPU
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,nounits,noheader"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                # 获取第一个GPU的显存（单位：MB）
                vram_mb = int(result.stdout.strip().split('\n')[0])
                self.gpu_vram = vram_mb // 1024  # 转换为GB
                self.gpu_available = True
                logger.debug(f"检测到NVIDIA GPU: {self.gpu_vram}GB显存")
        
        except FileNotFoundError:
            logger.debug("未找到nvidia-smi，GPU不可用")
        except Exception as e:
            logger.debug(f"GPU检测失败: {e}")
    
    def check_cpu_ram(self):
        """检测CPU和内存"""
        
        try:
            import psutil
            
            # 获取CPU核心数
            self.cpu_cores = psutil.cpu_count(logical=True)
            
            # 获取系统内存
            self.system_ram = psutil.virtual_memory().total // (1024**3)  # 转换为GB
            
            logger.debug(f"检测到CPU: {self.cpu_cores}核")
            logger.debug(f"检测到内存: {self.system_ram}GB")
        
        except ImportError:
            logger.debug("psutil未安装，无法检测CPU/内存")
        except Exception as e:
            logger.debug(f"CPU/内存检测失败: {e}")
    
    def recommend_model(self) -> str:
        """推荐最优模型"""
        
        logger.info("\n推荐模型选择:")
        
        # 基于GPU显存决策
        if self.gpu_available:
            if self.gpu_vram >= 10:
                logger.info("  GPU显存充足 (≥10GB) → 推荐 qwen:14b")
                return "qwen:14b"
            elif self.gpu_vram >= 6:
                logger.info("  GPU显存充足 (≥6GB) → 推荐 qwen:7b")
                return "qwen:7b"
            else:
                logger.warning(f"  GPU显存不足 ({self.gpu_vram}GB) → 用 qwen:7b")
                return "qwen:7b"
        else:
            # 基于CPU和内存
            if self.system_ram >= 32:
                logger.info("  无GPU但内存充足 (≥32GB) → 推荐 qwen:7b")
                return "qwen:7b"
            else:
                logger.warning(f"  内存不足 ({self.system_ram}GB) → 用 qwen:7b")
                return "qwen:7b"

# 全局实例
detector = HardwareDetector()