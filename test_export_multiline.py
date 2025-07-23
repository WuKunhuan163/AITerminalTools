#!/usr/bin/env python3
"""
测试 EXPORT 工具处理多行字符串
"""

import subprocess
import sys
import tempfile
import os

# 模拟的多行私钥（简化版）
test_private_key = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC00CGmKYnUaXG3
DAoGVEnMjuax/jrul09RjEyV/2fzA48ISBd5dADdUn6FvLPHlsc+r8lWVFxS4IlS
w/6Fog6bEmdNEATjPbtGvBDWet1dUXbPJLTRbdW+QNVUdwT/YQCkOFy3/C6PKx8q
-----END PRIVATE KEY-----"""

def test_export_multiline():
    """测试导出多行字符串"""
    print("🧪 测试 EXPORT 工具处理多行字符串...")
    
    try:
        # 使用 EXPORT 工具导出测试私钥
        result = subprocess.run([
            sys.executable, "EXPORT.py", 
            "TEST_PRIVATE_KEY", test_private_key
        ], capture_output=True, text=True)
        
        print(f"EXPORT 返回码: {result.returncode}")
        print(f"EXPORT 输出: {result.stdout}")
        if result.stderr:
            print(f"EXPORT 错误: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ EXPORT 成功")
            
            # 检查环境变量是否正确设置
            env_value = os.environ.get('TEST_PRIVATE_KEY', '')
            if env_value:
                print(f"✅ 环境变量设置成功")
                print(f"📋 环境变量内容前50字符: {env_value[:50]}...")
                
                # 验证换行符是否保留
                if '\n' in env_value:
                    print("✅ 换行符正确保留")
                else:
                    print("❌ 换行符丢失")
                    
                # 验证开始和结束标记
                if env_value.startswith('-----BEGIN PRIVATE KEY-----'):
                    print("✅ 开始标记正确")
                else:
                    print("❌ 开始标记错误")
                    
                if env_value.strip().endswith('-----END PRIVATE KEY-----'):
                    print("✅ 结束标记正确")
                else:
                    print("❌ 结束标记错误")
                    
            else:
                print("❌ 环境变量未设置")
        else:
            print("❌ EXPORT 失败")
            
    except Exception as e:
        print(f"❌ 测试出错: {e}")

if __name__ == "__main__":
    test_export_multiline() 