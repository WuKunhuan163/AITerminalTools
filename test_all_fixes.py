#!/usr/bin/env python3
"""
完整的GDS修复验证测试
测试所有我们修复的功能
"""
import subprocess
import sys
import os
import time

def run_gds_command(command, timeout=30):
    """运行GDS命令并返回结果"""
    try:
        cmd = ['python3', 'GOOGLE_DRIVE.py', '--shell', command]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result
    except subprocess.TimeoutExpired:
        print(f"⏰ 命令超时: {command}")
        return None
    except Exception as e:
        print(f"❌ 命令执行异常: {command} - {e}")
        return None

def test_all_fixes():
    """测试所有GDS修复的功能"""
    print("🧪 开始测试GDS所有修复功能")
    
    # 测试分组
    test_groups = [
        {
            "name": "LS命令修复",
            "tests": [
                ("ls", "基本ls命令", 30),
                ("ls .", "当前目录ls", 30),
                ("ls ~", "根目录ls（关键修复）", 30),
            ]
        },
        {
            "name": "MKDIR命令修复",
            "tests": [
                ("mkdir -p ~/test_fix_dir", "创建根目录下的目录", 60),
                ("ls ~/test_fix_dir", "验证目录创建成功", 30),
                ("mkdir -p ~/test_fix_dir/subdir", "创建嵌套目录", 60),
            ]
        },
        {
            "name": "路径解析修复",
            "tests": [
                ("ls ~/test_fix_dir/subdir", "访问嵌套目录", 30),
            ]
        }
    ]
    
    total_passed = 0
    total_failed = 0
    
    for group in test_groups:
        print(f"\n📂 测试组: {group['name']}")
        print("=" * 50)
        
        group_passed = 0
        group_failed = 0
        
        for command, description, timeout in group["tests"]:
            print(f"\n📋 测试: {description}")
            print(f"🔧 命令: {command}")
            
            result = run_gds_command(command, timeout)
            if result is None:
                print("❌ 测试失败（超时或异常）")
                group_failed += 1
                continue
                
            if result.returncode == 0:
                print("✅ 测试通过")
                group_passed += 1
            else:
                print(f"❌ 测试失败（返回码: {result.returncode}）")
                if result.stderr:
                    print(f"错误输出: {result.stderr[:200]}...")
                group_failed += 1
        
        print(f"\n📊 {group['name']} 结果: {group_passed}通过, {group_failed}失败")
        total_passed += group_passed
        total_failed += group_failed
    
    # 清理测试文件
    print(f"\n🧹 清理测试文件")
    cleanup_result = run_gds_command("rm -rf ~/test_fix_dir", 30)
    if cleanup_result and cleanup_result.returncode == 0:
        print("✅ 清理完成")
    else:
        print("⚠️ 清理可能不完整")
    
    print(f"\n🎯 总测试结果:")
    print(f"✅ 总通过: {total_passed}")
    print(f"❌ 总失败: {total_failed}")
    if total_passed + total_failed > 0:
        success_rate = total_passed / (total_passed + total_failed) * 100
        print(f"📊 成功率: {total_passed}/{total_passed+total_failed} ({success_rate:.1f}%)")
    
    return total_failed == 0

if __name__ == "__main__":
    success = test_all_fixes()
    sys.exit(0 if success else 1)
