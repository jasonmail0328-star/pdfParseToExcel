"""
诊断脚本 - 查看OCR原始输出（从第10页开始）
"""

import fitz
import numpy as np
from extractor.ocr_engine import OCREngine
from extractor.logger import logger
from config import PDF_PATH, PDF_DPI, PDF_REGION_CROP

def diagnose_ocr(pdf_path, start_page=10, num_pages=3):
    """诊断指定页数的OCR输出"""
    
    logger.info(f"从第 {start_page} 页开始诊断 {num_pages} 页的OCR输出...")
    
    doc = fitz.open(pdf_path)
    ocr_engine = OCREngine()
    
    output = []
    
    total_pages = len(doc)
    end_page = min(start_page + num_pages - 1, total_pages)
    
    for page_num in range(start_page - 1, end_page):
        page = doc[page_num]
        
        logger.info(f"\n{'='*70}")
        logger.info(f"第 {page_num + 1} 页")
        logger.info(f"{'='*70}")
        
        # 纯文本
        text = page.get_text()
        logger.info(f"\n【纯文本内容】:")
        if text:
            logger.info(text[:800])
        else:
            logger.info("(空)")
        
        # OCR
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(PDF_DPI / 72, PDF_DPI / 72))
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            
            h, w = img_array.shape[:2]
            left = int(w * PDF_REGION_CROP[0])
            top = int(h * PDF_REGION_CROP[1])
            right = int(w * PDF_REGION_CROP[2])
            bottom = int(h * PDF_REGION_CROP[3])
            
            img_cropped = img_array[top:bottom, left:right]
            
            ocr_text = ocr_engine.run(img_cropped)
            
            logger.info(f"\n【OCR输出】:")
            if ocr_text:
                logger.info(ocr_text[:800])
            else:
                logger.info("(空)")
        
        except Exception as e:
            logger.error(f"OCR处理失败: {e}")
        
        output.append({
            "page": page_num + 1,
            "text": text,
            "ocr": ocr_text
        })
    
    doc.close()
    
    return output

if __name__ == "__main__":
    # 从第10页开始，诊断10页
    diagnose_ocr(PDF_PATH, start_page=10, num_pages=10)