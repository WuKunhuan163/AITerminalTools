#!/usr/bin/env python3
"""
简单的GDS ls修复验证测试
专门测试我们修复的核心功能
"""
import subprocess
import sys
import os

def run_gds_command(command):
    """运行GDS命令并返回结果"""
    try:
        cmd = ['python3', 'GOOGLE_DRIVE.py', '--shell', command]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result
    except subprocess.TimeoutExpired:
        print(f"❌ 命令超时: {command}")
        return None
    except Exception as e:
        print(f"❌ 命令执行异常: {command} - {e}")
        return None

def test_ls_fixes():
    """测试GDS ls修复的功能"""
    print("🧪 开始测试GDS ls修复功能")
    
    tests = [
        ("ls", "基本ls命令"),
        ("ls .", "当前目录ls"),
        ("ls ~", "根目录ls（关键修复）"),
        ("ls -R ~", "根目录递归ls（关键修复）"),
    ]
    
    passed = 0
    failed = 0
    
    for command, description in tests:
        print(f"\n📋 测试: {description}")
        print(f"🔧 命令: {command}")
        
        result = run_gds_command(command)
        if result is None:
            print("❌ 测试失败（超时或异常）")
            failed += 1
            continue
            
        if result.returncode == 0:
            print("✅ 测试通过")
            passed += 1
        else:
            print(f"❌ 测试失败（返回码: {result.returncode}）")
            print(f"错误输出: {result.stderr}")
            failed += 1
    
    print(f"\n🎯 测试总结:")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"📊 成功率: {passed}/{passed+failed} ({passed/(passed+failed)*100:.1f}%)")
    
    return failed == 0

if __name__ == "__main__":
    success = test_ls_fixes()
    sys.exit(0 if success else 1)
