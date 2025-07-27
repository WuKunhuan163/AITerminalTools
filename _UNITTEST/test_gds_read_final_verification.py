#!/usr/bin/env python3
"""
Final verification test for GDS read command fix
验证GDS read命令修复的最终测试
"""

import subprocess
import sys

def run_gds_command(command):
    """运行GDS命令并返回结果"""
    try:
        gds_path = "/Users/wukunhuan/.local/bin/GOOGLE_DRIVE"
        result = subprocess.run(
            f"{gds_path} --shell \"{command}\"",
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
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """主测试函数"""
    print("=== GDS Read Command Final Verification ===\n")
    
    # 测试用例 - 所有这些都应该成功
    success_cases = [
        {
            "name": "Relative path from root",
            "command": "read GaussianObject/README.md",
            "expected": "Should read the README.md file from subdirectory"
        },
        {
            "name": "Explicit relative path with ./",
            "command": "read ./GaussianObject/README.md",
            "expected": "Should read the README.md file with explicit relative path"
        },
        {
            "name": "Absolute path with ~",
            "command": "read ~/GaussianObject/README.md",
            "expected": "Should read the README.md file from absolute path"
        },
        {
            "name": "Relative path with line range",
            "command": "read GaussianObject/README.md 1 3",
            "expected": "Should read lines 1-3"
        },
        {
            "name": "Absolute path with line range",
            "command": "read ~/GaussianObject/README.md 5 7",
            "expected": "Should read lines 5-7 from absolute path"
        },
        {
            "name": "Different file type",
            "command": "read ~/GaussianObject/requirements.txt 1 2",
            "expected": "Should read requirements.txt"
        }
    ]
    
    # 测试用例 - 这些应该失败但有适当的错误消息
    error_cases = [
        {
            "name": "Non-existent file",
            "command": "read nonexistent_file.txt",
            "expected": "Should show file not found error"
        },
        {
            "name": "Non-existent path",
            "command": "read ~/NonExistentDir/file.txt",
            "expected": "Should show directory not found error"
        }
    ]
    
    print("Testing SUCCESS cases (should all work):")
    success_count = 0
    for i, case in enumerate(success_cases, 1):
        print(f"{i}. {case['name']}")
        print(f"   Command: {case['command']}")
        
        result = run_gds_command(case['command'])
        
        if result["success"]:
            print("   ✅ SUCCESS")
            success_count += 1
            # 显示前50个字符的输出
            output_preview = result["stdout"][:50] + "..." if len(result["stdout"]) > 50 else result["stdout"]
            print(f"   Output: {output_preview}")
        else:
            print("   ❌ FAILED")
            print(f"   Error: {result.get('stderr', result.get('error', 'Unknown error'))}")
        print()
    
    print(f"Success cases passed: {success_count}/{len(success_cases)}\n")
    
    print("Testing ERROR cases (should fail gracefully):")
    error_count = 0
    for i, case in enumerate(error_cases, 1):
        print(f"{i}. {case['name']}")
        print(f"   Command: {case['command']}")
        
        result = run_gds_command(case['command'])
        
        if not result["success"]:
            print("   ✅ FAILED AS EXPECTED")
            error_count += 1
            print(f"   Error: {result.get('stderr', result.get('error', 'Unknown error'))}")
        else:
            print("   ❌ UNEXPECTED SUCCESS")
            print(f"   Output: {result['stdout']}")
        print()
    
    print(f"Error cases handled correctly: {error_count}/{len(error_cases)}\n")
    
    # 总结
    total_success = success_count + error_count
    total_cases = len(success_cases) + len(error_cases)
    
    print("=== FINAL RESULT ===")
    print(f"Total test cases: {total_cases}")
    print(f"Passed: {total_success}")
    print(f"Failed: {total_cases - total_success}")
    
    if total_success == total_cases:
        print("🎉 ALL TESTS PASSED! GDS read command is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 