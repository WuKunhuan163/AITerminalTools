#!/usr/bin/env python3
"""
简单的测试监控脚本
"""

import subprocess
import json
import time
import sys
from pathlib import Path

def get_test_status():
    """获取测试状态"""
    try:
        result = subprocess.run(
            ["../BACKGROUND_CMD", "--status", "--json"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return data.get('processes', [])
        return []
    except Exception:
        return []

def main():
    """主函数"""
    print("🔍 GDS Test Monitor")
    print("=" * 50)
    
    processes = get_test_status()
    
    # 过滤GDS测试进程
    gds_tests = [p for p in processes if 'test_gds.GDSTest' in p.get('command', '')]
    
    if not gds_tests:
        print("No GDS tests found in background processes")
        return
    
    running_tests = [p for p in gds_tests if p.get('status') == 'running']
    completed_tests = [p for p in gds_tests if p.get('status') == 'completed']
    
    print(f"🔄 Running tests: {len(running_tests)}")
    for test in running_tests:
        pid = test['pid']
        runtime = test['runtime']
        cmd = test['command']
        # 提取测试名称
        if 'test_gds.GDSTest.' in cmd:
            test_name = cmd.split('test_gds.GDSTest.')[1].split()[0]
            print(f"  PID {pid}: {test_name} ({runtime})")
    
    print(f"\n✅ Completed tests: {len(completed_tests)}")
    for test in completed_tests[-5:]:  # 只显示最近5个
        pid = test['pid']
        runtime = test['runtime']
        cmd = test['command']
        if 'test_gds.GDSTest.' in cmd:
            test_name = cmd.split('test_gds.GDSTest.')[1].split()[0]
            print(f"  PID {pid}: {test_name} ({runtime})")
    
    if len(completed_tests) > 5:
        print(f"  ... and {len(completed_tests) - 5} more")
    
    print(f"\n📊 Total GDS tests tracked: {len(gds_tests)}")

if __name__ == "__main__":
    main()
