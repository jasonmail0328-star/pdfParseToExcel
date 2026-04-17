"""
配置文件 - 包含pipeline和硬件检测
"""

import os
from pathlib import Path

# ==================== 路径配置 ====================
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = OUTPUT_DIR / "logs"
RESULTS_DIR = OUTPUT_DIR / "results"
TEMP_DIR = OUTPUT_DIR / "temp"
CHECKPOINT_DIR = OUTPUT_DIR / "checkpoint"

for d in [OUTPUT_DIR, LOGS_DIR, RESULTS_DIR, TEMP_DIR, CHECKPOINT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ==================== PDF配置 ====================
PDF_PATH = os.getenv("PDF_PATH", "report.pdf")

# ==================== OCR配置 ====================
OCR_LANG = "ch"
OCR_USE_GPU = False
OCR_ANGLE_CLS = False
OCR_SCORE_THRESHOLD = 0.5

# ==================== PDF处理配置 ====================
PDF_DPI = 200
PDF_REGION_CROP = (0.05, 0.1, 0.95, 0.9)

# ==================== 解析配置 ====================
MIN_VULN_TEXT_LENGTH = 30
MAX_VULN_TEXT_LENGTH = 15000

# ==================== Ollama 配置 ====================
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# 模型配置 - 直接指定而非 "auto"
# 选项: "qwen:7b" 或 "qwen:14b"
MODEL = os.getenv("OLLAMA_MODEL", "qwen:7b")

# 强制模型覆盖（环境变量或命令行参数会覆盖这个）
FORCE_MODEL = os.getenv("FORCE_MODEL", None)

# Ollama API 参数
AI_TEMPERATURE = 0.1
AI_TIMEOUT = 120
AI_MAX_RETRY = 5
AI_BATCH_SIZE = 3
AI_MAX_TEXT_LEN = 6000

# ==================== 线程配置 ====================
# 总线程数（用于多个模块）
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "4"))

# 是否启用多线程
ENABLE_THREADING = os.getenv("ENABLE_THREADING", "True").lower() == "true"

# ✅ OCR线程配置（建议：单线程或最多2个）
# OCR由于内存和显存限制，不建议过多并发
OCR_WORKERS = int(os.getenv("OCR_WORKERS", "1"))  # OCR专用线程数

# Ollama API线程配置（可以较多）
OLLAMA_WORKERS = int(os.getenv("OLLAMA_WORKERS", str(MAX_WORKERS)))

# ==================== Pipeline配置 ====================
ENABLE_CHECKPOINT = True
CHECKPOINT_INTERVAL = 100

PIPELINE_STEPS = [
    "extract_pdf",
    "parse_pages",
    "normalize_data",
    "write_excel"
]

# ==================== 输出配置 ====================
OUTPUT_EXCEL = RESULTS_DIR / "漏洞报告.xlsx"

# 临时文件
TEMP_PDF_PAGES = TEMP_DIR / "pages.json"
TEMP_VULNS = TEMP_DIR / "vulnerabilities.json"

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FILE = LOGS_DIR / "extraction.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ==================== 调试配置 ====================
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"