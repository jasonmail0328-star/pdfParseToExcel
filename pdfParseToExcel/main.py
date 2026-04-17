# -*- coding: utf-8 -*-
"""
主入口脚本 - 4步管道
支持：多线程 GPT 解析 + OCR 串行（加锁） + checkpoint 恢复
"""

import time
from extractor.logger import logger
from extractor.progress import time_tracker, StepTimer
from extractor.pipeline import pipeline
from extractor.smart_parser import parse_page_smart
from extractor.pdf_parser import extract_pdf_pages
from extractor.normalizer import normalize
from extractor.excel_writer import write_excel
from config import (
    PDF_PATH, OUTPUT_EXCEL, ENABLE_THREADING, MAX_WORKERS, 
    CHECKPOINT_INTERVAL
)


def step1_extract_pdf():
    """Step1: 提取PDF页面
    
    使用 extract_pdf_pages 中的多线程逻辑：
    - PDF 文本提取并行
    - OCR 串行（用锁保护）
    """
    
    logger.info("\n" + "=" * 120)
    logger.info("Step1: 提取PDF页面")
    logger.info("=" * 120)
    
    time_tracker.checkpoint("step1")
    
    # 尝试加载已提取的数据
    pages = pipeline.load_temp_pages()
    
    if pages:
        logger.info(f"✅ 使用已提取的PDF: {len(pages)} 页")
        return pages
    
    # 提取PDF
    try:
        pages = extract_pdf_pages(PDF_PATH)
        
        if not pages:
            logger.error("❌ 未能提取任何页面")
            return []
        
        # 保存临时数据
        pipeline.save_temp_pages(pages)
        
        elapsed = time_tracker.get_elapsed("step1")
        logger.info(f"✅ Step1完成: {len(pages)} 页，耗时 {time_tracker._format_time(elapsed)}")
        
        return pages
    
    except Exception as e:
        logger.error(f"❌ PDF提取失败: {e}", exc_info=True)
        return []


def step2_parse_pages(pages):
    """Step2: 解析页面 - 支持多线程
    
    使用 parse_page_smart 中的多线程逻辑：
    - Ollama 多线程解析
    - OCR 结果已串行保证
    """
    
    logger.info("\n" + "=" * 120)
    logger.info("Step2: 解析页面内容")
    logger.info("=" * 120)
    
    time_tracker.checkpoint("step2")
    
    # 尝试加载已解析的数据
    vulns = pipeline.load_temp_vulns()
    
    if vulns:
        logger.info(f"✅ 使用已解析的漏洞数据: {len(vulns)} 条")
        logger.info(f"⏭️  跳过页面解析，直接进入下一步")
        return vulns
    
    # 解析页面
    logger.info(f"📖 开始解析 {len(pages)} 个页面")
    
    # 创建进度条
    timer = StepTimer("解析页面", len(pages))
    
    all_vulns = []
    successful_pages = 0
    failed_pages = 0
    
    start_time = time.time()
    
    # 使用多线程处理页面
    if ENABLE_THREADING and MAX_WORKERS > 1:
        all_vulns, successful_pages, failed_pages = _parse_pages_threaded(
            pages, timer, start_time
        )
    else:
        all_vulns, successful_pages, failed_pages = _parse_pages_sequential(
            pages, timer, start_time
        )
    
    timer.finish()
    
    # 最终统计
    elapsed = time_tracker.get_elapsed("step2")
    
    logger.info(f"\n📊 Step2统计:")
    logger.info(f"   总页数: {len(pages)}")
    logger.info(f"   成功页: {successful_pages} ({successful_pages/len(pages)*100:.1f}%)")
    logger.info(f"   失败页: {failed_pages} ({failed_pages/len(pages)*100:.1f}%)")
    logger.info(f"   提取漏洞: {len(all_vulns)} 条")
    logger.info(f"   耗时: {time_tracker._format_time(elapsed)}")
    
    if all_vulns:
        avg_per_page = len(all_vulns) / successful_pages if successful_pages > 0 else 0
        logger.info(f"   平均每页: {avg_per_page:.1f} 条")
    
    if not all_vulns:
        logger.warning("⚠️  没有提取到任何漏洞")
        return []
    
    # 保存临时数据
    pipeline.save_temp_vulns(all_vulns)
    
    return all_vulns


def _parse_pages_sequential(pages, timer, start_time):
    """顺序处理页面"""
    
    logger.info(f"使用顺序处理 (1个线程)")
    
    all_vulns = []
    successful_pages = 0
    failed_pages = 0
    
    for page_num, page in enumerate(pages, 1):
        try:
            vulns_page = parse_page_smart(page['text'], page['ocr'])
            
            if vulns_page:
                all_vulns.extend(vulns_page)
                successful_pages += 1
            else:
                failed_pages += 1
            
            timer.update(1)
            
            # 定期保存checkpoint
            if page_num % CHECKPOINT_INTERVAL == 0:
                pipeline.save_checkpoint("parse", all_vulns, page_num)
                pipeline.save_temp_vulns(all_vulns)
                
                elapsed = time.time() - start_time
                items_per_sec = page_num / elapsed
                remaining = len(pages) - page_num
                eta = remaining / items_per_sec if items_per_sec > 0 else 0
                
                logger.info(
                    f"📊 Checkpoint保存 @ 第{page_num}页"
                    f" | 已提取: {len(all_vulns)} 条"
                    f" | 成功页: {successful_pages}"
                    f" | 失败页: {failed_pages}"
                    f" | 速度: {items_per_sec:.2f} 页/秒"
                    f" | 预计剩余: {StepTimer._format_time(eta) if eta > 0 else '计算中...'}"
                )
        
        except KeyboardInterrupt:
            logger.warning("⚠️  用户中断")
            pipeline.save_temp_vulns(all_vulns)
            raise
        
        except Exception as e:
            logger.debug(f"❌ 第{page_num}页解析失败: {e}")
            failed_pages += 1
            timer.update(1)
            continue
    
    return all_vulns, successful_pages, failed_pages


def _parse_pages_threaded(pages, timer, start_time):
    """多线程处理页面"""
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    logger.info(f"使用多线程处理 ({MAX_WORKERS}个线程)")
    
    all_vulns = []
    successful_pages = 0
    failed_pages = 0
    
    completed = 0
    total = len(pages)
    
    # 创建线程池
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(parse_page_smart, page['text'], page['ocr']): i
            for i, page in enumerate(pages)
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            page_num = index + 1
            
            try:
                vulns_page = future.result()
                
                if vulns_page:
                    all_vulns.extend(vulns_page)
                    successful_pages += 1
                else:
                    failed_pages += 1
                
                completed += 1
                timer.update(1)
                
                # 定期保存checkpoint
                if completed % CHECKPOINT_INTERVAL == 0:
                    pipeline.save_checkpoint("parse", all_vulns, page_num)
                    pipeline.save_temp_vulns(all_vulns)
                    
                    elapsed = time.time() - start_time
                    items_per_sec = completed / elapsed
                    remaining = total - completed
                    eta = remaining / items_per_sec if items_per_sec > 0 else 0
                    
                    logger.info(
                        f"📊 Checkpoint保存 @ 第{completed}/{total}页"
                        f" | 已提取: {len(all_vulns)} 条"
                        f" | 成功页: {successful_pages}"
                        f" | 失败页: {failed_pages}"
                        f" | 速度: {items_per_sec:.2f} 页/秒"
                        f" | 预计剩余: {StepTimer._format_time(eta) if eta > 0 else '计算中...'}"
                    )
            
            except KeyboardInterrupt:
                logger.warning("⚠️  用户中断")
                pipeline.save_temp_vulns(all_vulns)
                raise
            
            except Exception as e:
                logger.debug(f"❌ 第{page_num}页解析失败: {e}")
                failed_pages += 1
                completed += 1
                timer.update(1)
                continue
    
    return all_vulns, successful_pages, failed_pages


def step3_normalize(vulns):
    """Step3: 数据规范化
    
    清理和标准化各个字段
    """
    
    logger.info("\n" + "=" * 120)
    logger.info("Step3: 数据规范化")
    logger.info("=" * 120)
    
    time_tracker.checkpoint("step3")
    
    if not vulns:
        logger.warning("⚠️  没有数据需要规范化")
        return []
    
    logger.info(f"📊 规范化 {len(vulns)} 条数据")
    
    normalized = []
    
    for i, vuln in enumerate(vulns, 1):
        try:
            norm_vuln = normalize(vuln)
            if norm_vuln:
                normalized.append(norm_vuln)
        except Exception as e:
            logger.debug(f"规范化第{i}条失败: {e}")
            continue
    
    elapsed = time_tracker.get_elapsed("step3")
    logger.info(f"✅ 规范化完成: {len(normalized)} 条，耗时 {time_tracker._format_time(elapsed)}")
    
    return normalized


def step4_write_excel(vulns):
    """Step4: 写入Excel
    
    包括数据去重、按严重性排序、统计分布
    """
    
    logger.info("\n" + "=" * 120)
    logger.info("Step4: 写入Excel")
    logger.info("=" * 120)
    
    time_tracker.checkpoint("step4")
    
    if not vulns:
        logger.warning("⚠️  没有数据需要写入")
        return
    
    try:
        write_excel(vulns, OUTPUT_EXCEL)
        elapsed = time_tracker.get_elapsed("step4")
        logger.info(f"✅ Excel写入完成，耗时 {time_tracker._format_time(elapsed)}")
    except Exception as e:
        logger.error(f"❌ Excel写入失败: {e}", exc_info=True)
        raise


def main():
    """主函数 - 4步管道执行"""
    
    logger.info("\n" + "=" * 120)
    logger.info("🚀 PDF提取系统 - 启动")
    logger.info("=" * 120)
    logger.info(f"📋 配置:")
    logger.info(f"   PDF路径: {PDF_PATH}")
    logger.info(f"   输出文件: {OUTPUT_EXCEL}")
    logger.info(f"   多线程: {'✅ 启用' if ENABLE_THREADING else '❌ 禁用'}")
    logger.info(f"   工作线程: {MAX_WORKERS}")
    
    try:
        # Step1: 提取PDF
        pages = step1_extract_pdf()
        if not pages:
            logger.error("❌ Step1失败，无法继续")
            return False
        
        # Step2: 解析页面
        vulns = step2_parse_pages(pages)
        if not vulns:
            logger.error("❌ Step2失败，未提取到任何漏洞")
            return False
        
        # Step3: 规范化
        normalized = step3_normalize(vulns)
        if not normalized:
            logger.error("❌ Step3失败，规范化后无数据")
            return False
        
        # Step4: 写入Excel
        step4_write_excel(normalized)
        
        # 总统计
        overall_elapsed = time_tracker.format_overall()
        logger.info("\n" + "=" * 120)
        logger.info("✅ 完成！")
        logger.info(f"   总耗时: {overall_elapsed}")
        logger.info(f"   输出文件: {OUTPUT_EXCEL}")
        logger.info(f"   总漏洞数: {len(normalized)}")
        logger.info("=" * 120)
        
        return True
    
    except KeyboardInterrupt:
        logger.warning("\n⚠️  被用户中断")
        return False
    except Exception as e:
        logger.error(f"\n❌ 执行出错: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)