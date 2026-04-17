"""
高效PDF解析器 - 针对扫描报告优化
使用多进程 + 并行OCR
"""

import numpy as np
import fitz
from concurrent.futures import ProcessPoolExecutor, as_completed
from extractor.ocr_engine import OCREngine
from extractor.logger import logger
from config import MAX_WORKERS, PDF_DPI, PDF_REGION_CROP

def process_single_page(page_data):
    """处理单个页面（在子进程中运行）"""
    
    page_num = page_data['page_num']
    page_bytes = page_data['page_bytes']
    
    try:
        # 重新打开PDF并转到指定页面
        doc = fitz.open(stream=page_bytes, filetype="pdf")
        page = doc[page_num - 1]
        
        # 提取纯文本
        text = page.get_text()
        
        # 渲染为图像
        pix = page.get_pixmap(matrix=fitz.Matrix(PDF_DPI / 72, PDF_DPI / 72))
        
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, pix.n
        )
        
        # 裁剪
        h, w = img_array.shape[:2]
        left = int(w * PDF_REGION_CROP[0])
        top = int(h * PDF_REGION_CROP[1])
        right = int(w * PDF_REGION_CROP[2])
        bottom = int(h * PDF_REGION_CROP[3])
        
        img_cropped = img_array[top:bottom, left:right]
        
        # OCR
        ocr_engine = OCREngine()
        ocr_text = ocr_engine.run(img_cropped)
        
        doc.close()
        
        return {
            "page": page_num,
            "text": text,
            "ocr": ocr_text,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"❌ 处理第 {page_num} 页失败: {e}")
        return {
            "page": page_num,
            "text": "",
            "ocr": "",
            "success": False
        }

def extract_pdf_pages_parallel(pdf_path: str):
    """使用多进程并行提取PDF页面"""
    
    logger.info(f"📖 打开PDF: {pdf_path}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"❌ 无法打开PDF: {e}")
        raise
    
    total_pages = len(doc)
    logger.info(f"📊 总页数: {total_pages}")
    
    # 将PDF读入内存
    pdf_bytes = open(pdf_path, 'rb').read()
    
    pages_data = []
    
    # 多进程处理
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        
        futures = {}
        
        for page_num in range(1, total_pages + 1):
            page_data = {
                'page_num': page_num,
                'page_bytes': pdf_bytes
            }
            
            future = executor.submit(process_single_page, page_data)
            futures[future] = page_num
        
        # 收集结果
        completed = 0
        for future in as_completed(futures):
            page_num = futures[future]
            completed += 1
            
            try:
                result = future.result()
                pages_data.append(result)
                
                progress = (completed / total_pages) * 100
                logger.info(f"📄 第 {page_num} 页完成 ({progress:.0f}%)")
            
            except Exception as e:
                logger.error(f"❌ 第 {page_num} 页处理失败: {e}")
    
    # 按页码排序
    pages_data.sort(key=lambda x: x['page'])
    
    doc.close()
    logger.info(f"✅ PDF提取完成，共 {len(pages_data)} 页")
    
    return pages_data