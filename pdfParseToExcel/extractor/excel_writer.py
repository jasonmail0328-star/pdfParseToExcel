"""
Excel写入器
"""

import pandas as pd
from pathlib import Path
from extractor.logger import logger

SEVERITY_ORDER = {
    "紧急": 0,
    "高": 1,
    "中": 2,
    "低": 3,
}

def write_excel(data: list, output_file):
    """
    写入Excel文件
    
    包括：
    - 数据去重
    - 按严重性排序
    - 统计分布
    """
    
    if not data:
        logger.warning("没有数据需要写入")
        return
    
    try:
        logger.info(f"准备写入 Excel: {output_file}")
        
        # 创建 DataFrame
        df = pd.DataFrame(data)
        
        logger.info(f"原始行数: {len(df)}")
        
        # 去重
        before_dup = len(df)
        df = df.drop_duplicates(subset=["URL", "问题"], keep="first")
        after_dup = len(df)
        
        logger.info(f"去重: {before_dup} -> {after_dup} 行 (删除 {before_dup - after_dup} 条)")
        
        # 按严重性排序
        if "严重性" in df.columns:
            df["_sort"] = df["严重性"].map(lambda x: SEVERITY_ORDER.get(x, 999))
            df = df.sort_values(by="_sort")
            df = df.drop(columns=["_sort"])
        
        # 创建输出目录
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入 Excel
        df.to_excel(output_file, index=False, engine='openpyxl')
        
        logger.info(f"✅ Excel 写入成功: {output_file}")
        logger.info(f"📊 总记录数: {len(df)}")
        
        # 统计严重性分布
        if "严重性" in df.columns:
            logger.info("📊 严重性分布:")
            for severity, count in df["严重性"].value_counts().items():
                logger.info(f"   {severity}: {count} 条")
    
    except Exception as e:
        logger.error(f"❌ Excel 写入失败: {e}")
        raise