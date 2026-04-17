"""
PDF解析器 - 优化为快速处理（OCR串行，内容提取并行）
"""

import numpy as np
import fitz
from concurrent.futures import ThreadPoolExecutor
from extractor.ocr_engine import OCREngine
from extractor.logger import logger
from config import PDF_DPI, PDF_REGION_CROP, MAX_WORKERS, ENABLE_THREADING

def extract_pdf_pages(pdf_path: str):
    """
    提取PDF - 优化版本
    
    策略：
    - 文本提取并行
    - OCR串行（用锁保护）
    """
    
    logger.info(f"打开PDF: {pdf_path}")
    logger.info(f"DPI: {PDF_DPI}")
    
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"无法打开PDF: {e}")
        raise
    
    total_pages = len(doc)
    logger.info(f"总页数: {total_pages}")
    
    pages_data = []
    ocr_count = 0
    text_only_count = 0
    
    ocr_engine = OCREngine()
    
    # 使用多线程提取页面
    if ENABLE_THREADING and MAX_WORKERS > 1 and total_pages > 10:
        logger.info(f"使用 {MAX_WORKERS} 个线程提取页面")
        
        # 将页面分成多个batch
        batch_size = max(1, total_pages // (MAX_WORKERS * 2))
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            
            for page_num in range(total_pages):
                future = executor.submit(
                    _extract_single_page,
                    doc,
                    page_num,
                    ocr_engine
                )
                futures.append(future)
            
            for future in futures:
                try:
                    page_info, is_ocr = future.result()
                    pages_data.append(page_info)
                    
                    if is_ocr:
                        ocr_count += 1
                    else:
                        text_only_count += 1
                
                except Exception as e:
                    logger.error(f"提取页面失败: {e}")
                    continue
    else:
        logger.info("使用顺序处理提取页面")
        
        for page_num in range(total_pages):
            try:
                page_info, is_ocr = _extract_single_page(doc, page_num, ocr_engine)
                pages_data.append(page_info)
                
                if is_ocr:
                    ocr_count += 1
                else:
                    text_only_count += 1
            
            except Exception as e:
                logger.error(f"处理第{page_num+1}页失败: {e}")
                continue
    
    doc.close()
    
    logger.info(f"\n✅ PDF提取完成")
    logger.info(f"   纯文本页: {text_only_count}")
    logger.info(f"   OCR页: {ocr_count}")
    logger.info(f"   总页: {len(pages_data)}")
    
    return pages_data

def _extract_single_page(doc, page_num: int, ocr_engine):
    """
    提取单个页面
    
    返回: (page_data, is_ocr_used)
    """
    
    page = doc[page_num]
    
    try:
        # 提取纯文本（这个是线程安全的）
        text = page.get_text()
        
        # 判断是否需要OCR
        text_len = len(text.strip())
        
        if text_len > 300:  # 纯文本充足
            return {
                "page": page_num + 1,
                "text": text,
                "ocr": ""
            }, False
        
        # 需要进行OCR
        logger.debug(f"第{page_num+1}页: 纯文本不足({text_len}字符)，进行OCR...")
        
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(PDF_DPI / 72, PDF_DPI / 72))
            
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                pix.height, pix.width, pix.n
            )
            
            # 裁剪区域
            h, w = img_array.shape[:2]
            left = int(w * PDF_REGION_CROP[0])
            top = int(h * PDF_REGION_CROP[1])
            right = int(w * PDF_REGION_CROP[2])
            bottom = int(h * PDF_REGION_CROP[3])
            
            img_cropped = img_array[top:bottom, left:right]
            
            # OCR调用（会使用锁保护）
            ocr_text = ocr_engine.run(img_cropped)
        
        except Exception as e:
            logger.warning(f"第{page_num+1}页OCR失败: {e}")
            ocr_text = ""
        
        return {
            "page": page_num + 1,
            "text": text,
            "ocr": ocr_text
        }, True
    
    except Exception as e:
        logger.error(f"处理第{page_num+1}页失败: {e}")
        return {
            "page": page_num + 1,
            "text": "",
            "ocr": ""
        }, False