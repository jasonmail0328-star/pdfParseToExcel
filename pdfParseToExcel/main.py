def step2_parse_pages(pages):
    """Step2: 解析页面 - 支持多线程"""
    
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
    timer = StepTimer("���析页面", len(pages))
    
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