"""
核心处理模块
"""

def process_data(config):
    """处理数据的核心函数"""
    if config.get("debug", False):
        print("🐛 调试模式已启用")
    
    # 模拟数据处理
    data = [1, 2, 3, 4, 5]
    result = sum(x * x for x in data)
    
    return {
        "processed": True,
        "result": result,
        "version": config.get("version", "unknown")
    }
