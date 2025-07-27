#!/usr/bin/env python3
"""
测试GDS read命令的各种用法
Test GDS read command functionality with different path formats
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

def run_gds_command(command):
    """运行GDS命令并返回结果"""
    try:
        # 使用GOOGLE_DRIVE --shell命令
        gds_path = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE"
        result = subprocess.run(
            f"{gds_path} --shell {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_read_functionality():
    """测试read命令的各种用法"""
    print("=== GDS Read Functionality Test ===\n")
    
    # 1. 测试pwd确认当前位置
    print("1. Testing current directory...")
    pwd_result = run_gds_command("pwd")
    print(f"Current directory: {pwd_result}")
    
    if not pwd_result["success"]:
        print("❌ Failed to get current directory")
        return
    
    current_dir = pwd_result["stdout"]
    print(f"Current directory: {current_dir}\n")
    
    # 2. 测试ls查看可用文件
    print("2. Testing ls to see available files...")
    ls_result = run_gds_command("ls")
    print(f"Available files: {ls_result['stdout'][:200]}...\n")
    
    # 3. 测试不同的read用法
    test_cases = [
        {
            "name": "Read with relative path (README.md)",
            "command": "read README.md",
            "description": "Should work if README.md exists in current directory"
        },
        {
            "name": "Read with explicit relative path (./README.md)",
            "command": "read ./README.md", 
            "description": "Should work if README.md exists in current directory"
        },
        {
            "name": "Read with absolute path (~/GaussianObject/README.md)",
            "command": "read ~/GaussianObject/README.md",
            "description": "Should work if in GaussianObject directory"
        },
        {
            "name": "Read with line range (README.md 1 10)",
            "command": "read README.md 1 10",
            "description": "Should read lines 1-10 from README.md"
        },
        {
            "name": "Read with absolute path and line range",
            "command": "read ~/GaussianObject/README.md 1 5",
            "description": "Should read lines 1-5 from absolute path"
        },
        {
            "name": "Read non-existent file",
            "command": "read nonexistent.txt",
            "description": "Should fail gracefully"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 3):
        print(f"{i}. {test_case['name']}")
        print(f"   Command: GDS {test_case['command']}")
        print(f"   Description: {test_case['description']}")
        
        result = run_gds_command(test_case['command'])
        
        if result["success"]:
            print("   ✅ SUCCESS")
            # 限制输出长度
            output = result["stdout"][:300] + "..." if len(result["stdout"]) > 300 else result["stdout"]
            print(f"   Output: {output}")
        else:
            print("   ❌ FAILED")
            print(f"   Error: {result.get('stderr', result.get('error', 'Unknown error'))}")
        
        print()
    
    # 4. 测试特殊情况
    print("4. Testing edge cases...")
    
    edge_cases = [
        {
            "name": "Read with invalid line range",
            "command": "read README.md abc def",
            "description": "Should handle invalid line numbers gracefully"
        },
        {
            "name": "Read with --detailed flag (should fail)",
            "command": "read README.md --detailed",
            "description": "Should show error about unsupported flag"
        }
    ]
    
    for case in edge_cases:
        print(f"   {case['name']}: GDS {case['command']}")
        result = run_gds_command(case['command'])
        
        if result["success"]:
            print("   ✅ Unexpected success")
        else:
            print("   ❌ Failed as expected")
            print(f"   Error: {result.get('stderr', result.get('error', 'Unknown error'))}")
        print()

def main():
    """主函数"""
    print("Starting GDS read functionality tests...\n")
    test_read_functionality()
    print("Test completed.")

if __name__ == "__main__":
    main() 