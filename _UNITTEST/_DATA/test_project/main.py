"""
测试项目主文件
"""
import json
import sys
from datetime import datetime

def main():
    print("🚀 测试项目启动")
    print(f"📅 当前时间: {datetime.now()}")
    print(f"🐍 Python版本: {sys.version}")
    
    # 读取配置文件
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
        print(f"⚙️ 配置: {config}")
    except FileNotFoundError:
        print("⚠️ 配置文件不存在，使用默认配置")
        config = {"debug": True, "version": "1.0.0"}
    
    # 执行核心逻辑
    from core import process_data
    result = process_data(config)
    print(f"✅ 处理结果: {result}")

if __name__ == "__main__":
    main()
