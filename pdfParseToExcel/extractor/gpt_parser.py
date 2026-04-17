"""
Ollama大模型解析器 - 支持多线程并发
"""

import re
import json
import time
import requests
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from extractor.logger import logger
from config import (
    MODEL, OLLAMA_URL, AI_TEMPERATURE, AI_TIMEOUT,
    AI_MAX_RETRY, AI_BATCH_SIZE, AI_MAX_TEXT_LEN, FORCE_MODEL,
    MAX_WORKERS, ENABLE_THREADING, OLLAMA_WORKERS  # ✅ 添加
)

# 优化的系统提示
SYSTEM_PROMPT = """你是一个安全漏洞信息提取专家。

你的任务是从混乱的OCR文本中精确提取漏洞信息。
OCR文本可能包含：
- 字符识别错误
- 格式混乱
- 缺少部分内容
- 重复内容

需要你：
1. 理解OCR的意图，自动纠正明显错误
2. 提取所有能找到的漏洞信息
3. 返回结构化的JSON格式
4. 对无法确定的字段返回空字符串

【关键字段说明】
- 问题：漏洞名称或标题
- 严重性：紧急、高、中、低
- URL：以 http:// 或 https:// 开头的网址
- 实体：参数名、变量名或受影响的具体位置
- 风险：这个漏洞的危害和影响
- 原因：为什么会有这个漏洞
- CVSS：漏洞评分，格式为数字（如 8.6）

【返回格式】
只返回有效的JSON对象或数组，不要任何其他内容。
如果输入包含多个漏洞，返回JSON数组。

【重要】
- 字段值要短而精
- 不要解释，只提取
- 如果不确定，返回空字符串
- 必须返回有效的JSON"""

def get_actual_model() -> str:
    """获取实际使用的模型"""
    
    if FORCE_MODEL:
        logger.info(f"使用强制指定的模型: {FORCE_MODEL}")
        return FORCE_MODEL
    
    logger.debug(f"使用配置的模型: {MODEL}")
    return MODEL

def split_text_smart(text: str, max_len: int = AI_MAX_TEXT_LEN) -> List[str]:
    """智能分割文本 - 不截断，而是按逻辑分割"""
    
    if len(text) <= max_len:
        return [text]
    
    chunks = []
    
    # 策略1: 按漏洞块分割
    pattern = r'(?=问题\s+\d+\s*/\s*\d+)'
    splits = re.split(pattern, text)
    
    if len(splits) > 1:
        for split in splits:
            if len(split.strip()) > 0:
                if len(split) > max_len:
                    chunks.extend(split_text_smart(split, max_len))
                else:
                    chunks.append(split.strip())
        
        logger.debug(f"按漏洞块分割: {len(chunks)} 个部分")
        return chunks
    
    # 策略2: 按段落分割（多个换行符）
    paragraphs = re.split(r'\n\n+', text)
    
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) <= max_len:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            
            if len(para) > max_len:
                chunks.extend(split_text_smart(para, max_len))
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    logger.debug(f"按段落分割: {len(chunks)} 个部分")
    return chunks if chunks else [text[:max_len]]

def safe_json_parse(text: str) -> Optional[Dict | List]:
    """安全的JSON解析"""
    
    if not text:
        return None
    
    text = text.strip()
    
    # 尝试1: 直接解析
    try:
        result = json.loads(text)
        if isinstance(result, (dict, list)):
            return result
    except:
        pass
    
    # 尝试2: 从```json```中提取
    try:
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    
    # 尝试3: 从```中提取
    try:
        match = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
    except:
        pass
    
    # 尝试4: 找第一个{...}或[...]
    try:
        start = text.find('{')
        if start != -1:
            level = 0
            for i in range(start, len(text)):
                if text[i] == '{':
                    level += 1
                elif text[i] == '}':
                    level -= 1
                    if level == 0:
                        return json.loads(text[start:i+1])
        
        start = text.find('[')
        if start != -1:
            level = 0
            for i in range(start, len(text)):
                if text[i] == '[':
                    level += 1
                elif text[i] == ']':
                    level -= 1
                    if level == 0:
                        return json.loads(text[start:i+1])
    except:
        pass
    
    logger.debug(f"无法解析JSON: {text[:100]}...")
    return None

def call_ollama(text: str, retry_count: int = 0) -> str:
    """调用Ollama - 带重试机制"""
    
    if not text or not text.strip():
        return ""
    
    actual_model = get_actual_model()
    
    # 智能分割长文本而不是截断
    if len(text) > AI_MAX_TEXT_LEN:
        logger.warning(f"文本过长 ({len(text)})，使用智能分割而非截断")
        chunks = split_text_smart(text, AI_MAX_TEXT_LEN)
        
        # 分别处理每个chunk，然后合并结果
        results = []
        for i, chunk in enumerate(chunks):
            logger.debug(f"处理分割部分 {i+1}/{len(chunks)}")
            result = call_ollama(chunk, 0)
            if result:
                results.append(result)
        
        if results:
            return "\n".join(results)
        else:
            return ""
    
    payload = {
        "model": actual_model,
        "prompt": f"{SYSTEM_PROMPT}\n\n【输入文本】\n{text}",
        "stream": False,
        "options": {
            "temperature": AI_TEMPERATURE,
            "top_k": 30,
            "top_p": 0.8,
            "num_predict": 800,
        }
    }
    
    try:
        logger.debug(f"调用Ollama ({actual_model})...")
        
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=AI_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json().get("response", "")
            logger.debug(f"✅ Ollama响应成功 ({len(result)} 字符)")
            return result
        else:
            logger.warning(f"Ollama错误: {response.status_code}")
            if response.status_code == 404:
                logger.warning(f"❌ 模型未找到或API地址错误")
                logger.warning(f"   模型: {actual_model}")
                logger.warning(f"   地址: {OLLAMA_URL}")
            return ""
    
    except requests.Timeout:
        logger.warning(f"Ollama超时 (尝试 {retry_count + 1}/{AI_MAX_RETRY})")
    except requests.ConnectionError:
        logger.warning(f"无法连接Ollama (尝试 {retry_count + 1}/{AI_MAX_RETRY})")
        if retry_count == 0:
            logger.info(f"  请启动Ollama: ollama serve")
            logger.info(f"  URL: {OLLAMA_URL}")
    except Exception as e:
        logger.warning(f"Ollama错误: {e} (尝试 {retry_count + 1}/{AI_MAX_RETRY})")
    
    # 重试
    if retry_count < AI_MAX_RETRY - 1:
        wait_time = 2 ** retry_count
        logger.debug(f"等待 {wait_time}秒后重试...")
        time.sleep(wait_time)
        return call_ollama(text, retry_count + 1)
    
    return ""

def parse_single(text: str) -> Optional[Dict]:
    """解析单个文本块"""
    
    if not text or len(text.strip()) < 30:
        return None
    
    response = call_ollama(text)
    
    if not response:
        logger.warning("Ollama未返回结果")
        return None
    
    result = safe_json_parse(response)
    
    if not result:
        return None
    
    if isinstance(result, list):
        if result:
            result = result[0]
        else:
            return None
    
    return result

def parse_blocks(blocks: List[str]) -> List[Dict]:
    """批量解析文本块 - 支持多线程"""
    
    if not blocks:
        logger.warning("没有文本块需要解析")
        return []
    
    total = len(blocks)
    
    # 获取实际模型
    actual_model = get_actual_model()
    
    logger.info(f"\n开始Ollama解析: {total}个块")
    logger.info(f"模型: {actual_model} | 温度: {AI_TEMPERATURE} | 超时: {AI_TIMEOUT}秒")
    
    if ENABLE_THREADING and MAX_WORKERS > 1:
        return _parse_blocks_threaded(blocks, actual_model)
    else:
        return _parse_blocks_sequential(blocks, actual_model)

def _parse_blocks_sequential(blocks: List[str], model: str) -> List[Dict]:
    """顺序解析 - 单线程"""
    
    results = []
    processed = 0
    total = len(blocks)
    
    logger.info(f"使用顺序处理 (1个线程)")
    
    for i, block in enumerate(blocks):
        try:
            parsed = parse_single(block)
            
            if parsed:
                if (parsed.get('严重性') or 
                    parsed.get('URL') or 
                    parsed.get('问题')):
                    results.append(parsed)
                    processed += 1
                    logger.debug(f"  ✅ 块{i+1}: 解析成功")
                else:
                    logger.debug(f"  ⚠️  块{i+1}: 关键字段为空")
            else:
                logger.debug(f"  ❌ 块{i+1}: 解析失败")
        
        except Exception as e:
            logger.warning(f"  块{i+1}处理失败: {e}")
    
    logger.info(f"\n✅ 解析完成: {processed}/{total}个块成功")
    
    return results

def _parse_blocks_threaded(blocks: List[str], model: str) -> List[Dict]:
    """多线程解析 - 使用Ollama专用线程数"""
    
    results = [None] * len(blocks)
    processed = 0
    total = len(blocks)
    
    # ✅ 使用 OLLAMA_WORKERS 而非 MAX_WORKERS
    num_workers = OLLAMA_WORKERS if OLLAMA_WORKERS > 0 else 1
    
    logger.info(f"使用多线程处理 ({num_workers}个线程)")
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # 提交所有任务
        future_to_index = {
            executor.submit(parse_single, block): i 
            for i, block in enumerate(blocks)
        }
        
        # 处理完成的任务
        for future in as_completed(future_to_index):
            index = future_to_index[future]
            
            try:
                parsed = future.result()
                
                if parsed:
                    if (parsed.get('严重性') or 
                        parsed.get('URL') or 
                        parsed.get('问题')):
                        results[index] = parsed
                        processed += 1
                        logger.debug(f"  ✅ 块{index+1}: 解析成功")
                    else:
                        logger.debug(f"  ⚠️  块{index+1}: 关键字段为空")
                else:
                    logger.debug(f"  ❌ 块{index+1}: 解析失败")
            
            except Exception as e:
                logger.warning(f"  块{index+1}处理失败: {e}")
    
    # 过滤掉失败的项
    results = [r for r in results if r is not None]
    
    logger.info(f"\n✅ 解析完成: {processed}/{total}个块成功")
    
    return results