#!/usr/bin/env python3
"""
GDS测试并行运行脚本
使用BACKGROUND_CMD批量运行GDS单元测试，支持指定ID范围，控制并发数
"""

import os
import sys
import time
import subprocess
import json
import argparse
from pathlib import Path

# 完整的GDS测试列表（从0开始编号）
ALL_GDS_TESTS = [
    "test_gds.GDSTest.test_01_echo_basic",                           # 0
    "test_gds.GDSTest.test_02_echo_advanced",                        # 1
    "test_gds.GDSTest.test_03_ls_basic",                            # 2
    "test_gds.GDSTest.test_04_ls_advanced",                         # 3
    "test_gds.GDSTest.test_05_file_ops_mixed",                      # 4
    "test_gds.GDSTest.test_06_navigation",                          # 5
    "test_gds.GDSTest.test_07_upload",                              # 6
    "test_gds.GDSTest.test_08_grep",                                # 7
    "test_gds.GDSTest.test_09_edit",                                # 8
    "test_gds.GDSTest.test_10_read",                                # 9
    "test_gds.GDSTest.test_11_project_development",                 # 10
    "test_gds.GDSTest.test_12_project_deployment",                  # 11
    "test_gds.GDSTest.test_13_code_execution",                      # 12
    "test_gds.GDSTest.test_14_venv_basic",                          # 13
    "test_gds.GDSTest.test_15_venv_package",                        # 14
    "test_gds.GDSTest.test_16_linter",                              # 15
    "test_gds.GDSTest.test_17_edit_linter",                         # 16
    "test_gds.GDSTest.test_18_pipe",                                # 17
    "test_gds.GDSTest.test_19_pip_deps_analysis",                   # 18
    "test_gds.GDSTest.test_20_shell_mode_continuous_operations",    # 19
    "test_gds.GDSTest.test_21_shell_mode_vs_direct_consistency",    # 20
    "test_gds.GDSTest.test_22_shell_switching_and_state",           # 21
    "test_gds.GDSTest.test_23_shell_mode_error_handling",           # 22
    "test_gds.GDSTest.test_24_shell_mode_performance",              # 23
    "test_gds.GDSTest.test_25_shell_prompt_improvements",           # 24
    "test_gds.GDSTest.test_26_shell_command_routing",               # 25
    "test_gds.GDSTest.test_27_shell_state_persistence",             # 26
    "test_gds.GDSTest.test_28_pyenv_basic",                         # 27
    "test_gds.GDSTest.test_29_pyenv_version_management",            # 28
    "test_gds.GDSTest.test_30_pyenv_integration_with_python_execution", # 29
    "test_gds.GDSTest.test_31_pyenv_error_handling",                # 30
    "test_gds.GDSTest.test_32_pyenv_concurrent_operations",         # 31
    "test_gds.GDSTest.test_33_pyenv_state_persistence",             # 32
    "test_gds.GDSTest.test_34_pyenv_integration_with_existing_python", # 33
    "test_gds.GDSTest.test_35_pyenv_edge_cases_and_stress_test",    # 34
    "test_gds.GDSTest.test_36_pyenv_real_world_scenarios",          # 35
    "test_gds.GDSTest.test_37_pyenv_performance_and_reliability",   # 36
    "test_gds.GDSTest.test_38_pyenv_functional_verification",       # 37
    "test_gds.GDSTest.test_39_redirection_commands_reinforcement",  # 38
    "test_gds.GDSTest.test_40_regex_validation",                    # 39
    "test_gds.GDSTest.test_41_edge_cases_comprehensive"             # 40
]

def get_running_background_processes():
    """获取当前运行中的后台进程数量"""
    try:
        result = subprocess.run(
            ["../BACKGROUND_CMD", "--status", "--json"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            running_count = sum(1 for proc in data.get('processes', []) 
                              if proc.get('status') == 'running')
            return running_count
        return 0
    except Exception:
        return 0

def start_test(test_name):
    """启动一个测试"""
    # 创建输出文件名
    test_short_name = test_name.split('.')[-1]
    output_file = f"tmp/{test_short_name}_output.txt"
    
    # 确保tmp目录存在
    tmp_dir = Path(__file__).parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    
    # 修改命令以重定向输出到文件
    cmd = f'cd {Path(__file__).parent} && /usr/bin/python3 -m unittest {test_name} -v > {output_file} 2>&1'
    
    try:
        result = subprocess.run(
            ["../BACKGROUND_CMD", cmd],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        if result.returncode == 0:
            # 从输出中提取PID
            output = result.stdout.strip()
            if "Process started: PID" in output:
                pid = output.split("PID ")[1].split(",")[0]
                print(f"▶️ Started {test_short_name} (PID: {pid}) -> {output_file}")
                return int(pid), output_file
        print(f"❌ Failed to start {test_name}: {result.stderr}")
        return None, None
    except Exception as e:
        print(f"❌ Error starting {test_name}: {e}")
        return None, None

def list_tests():
    """列出所有测试及其ID"""
    print("📋 GDS Test List (ID: Test Name)")
    print("=" * 60)
    for i, test in enumerate(ALL_GDS_TESTS):
        test_name = test.split('.')[-1]  # 只显示测试方法名
        print(f"{i:2d}: {test_name}")
    print(f"\nTotal: {len(ALL_GDS_TESTS)} tests")

def run_tests_range(start_id, end_id, max_concurrent=3):
    """运行指定范围的测试"""
    if start_id < 0 or end_id >= len(ALL_GDS_TESTS) or start_id > end_id:
        print(f"❌ Invalid range: {start_id}-{end_id}. Valid range: 0-{len(ALL_GDS_TESTS)-1}")
        return
    
    test_queue = ALL_GDS_TESTS[start_id:end_id+1]
    
    print(f"🚀 Running tests {start_id}-{end_id} ({len(test_queue)} tests)")
    print(f"⚡ Max concurrent: {max_concurrent}")
    print("=" * 60)
    
    completed_tests = []
    failed_tests = []
    running_pids = {}  # {pid: (test_name, output_file)}
    test_results = {}  # {test_name: {"status": "pass/fail", "output_file": "path", "content": "..."}}
    
    while test_queue or running_pids:
        # 启动新测试（如果有空闲槽位）
        current_running = get_running_background_processes()
        
        while len(running_pids) < max_concurrent and test_queue and current_running < max_concurrent:
            test_name = test_queue.pop(0)
            pid, output_file = start_test(test_name)
            if pid:
                running_pids[pid] = (test_name, output_file)
                current_running += 1
            else:
                failed_tests.append(test_name)
        
        # 检查已完成的测试
        completed_pids = []
        for pid, (test_name, output_file) in running_pids.items():
            try:
                result = subprocess.run(
                    ["../BACKGROUND_CMD", "--status", str(pid), "--json"],
                    capture_output=True,
                    text=True,
                    cwd=Path(__file__).parent
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if data.get('success') and data.get('status', {}).get('status') == 'completed':
                        completed_pids.append(pid)
                        completed_tests.append(test_name)
                        
                        # 读取测试结果
                        test_short_name = test_name.split('.')[-1]
                        output_path = Path(__file__).parent / output_file
                        test_content = ""
                        test_status = "unknown"
                        
                        try:
                            if output_path.exists():
                                test_content = output_path.read_text(encoding='utf-8')
                                # 简单判断测试是否通过
                                if "OK" in test_content and "FAILED" not in test_content:
                                    test_status = "pass"
                                elif "FAILED" in test_content or "ERROR" in test_content:
                                    test_status = "fail"
                                else:
                                    test_status = "unknown"
                            else:
                                test_content = "Output file not found"
                                test_status = "fail"
                        except Exception as e:
                            test_content = f"Error reading output: {e}"
                            test_status = "fail"
                        
                        test_results[test_name] = {
                            "status": test_status,
                            "output_file": output_file,
                            "content": test_content
                        }
                        
                        status_icon = "✅" if test_status == "pass" else "❌" if test_status == "fail" else "❓"
                        print(f"{status_icon} Completed {test_short_name} (PID: {pid}) - {test_status.upper()}")
            except Exception:
                pass
        
        # 移除已完成的进程
        for pid in completed_pids:
            del running_pids[pid]
        
        # 显示进度
        total = len(ALL_GDS_TESTS[start_id:end_id+1])
        done = len(completed_tests) + len(failed_tests)
        running = len(running_pids)
        remaining = len(test_queue)
        
        print(f"📈 Progress: {done}/{total} done, {running} running, {remaining} queued")
        
        if running_pids or test_queue:
            time.sleep(5)  # 等待5秒再检查
    
    # 最终报告
    print(f"\n{'='*60}")
    print(f"🏁 Test execution completed!")
    
    # 统计结果
    passed_tests = [name for name, result in test_results.items() if result["status"] == "pass"]
    failed_test_results = [name for name, result in test_results.items() if result["status"] == "fail"]
    unknown_tests = [name for name, result in test_results.items() if result["status"] == "unknown"]
    
    print(f"✅ Passed: {len(passed_tests)}")
    print(f"❌ Failed: {len(failed_test_results) + len(failed_tests)}")
    print(f"❓ Unknown: {len(unknown_tests)}")
    
    # 显示失败的测试详情
    all_failed = failed_tests + failed_test_results
    if all_failed:
        print(f"\n❌ Failed tests:")
        for test in all_failed:
            test_short = test.split('.')[-1]
            print(f"  - {test_short}")
            if test in test_results:
                output_file = test_results[test]["output_file"]
                print(f"    📄 Output: {output_file}")
    
    # 显示通过的测试
    if passed_tests:
        print(f"\n✅ Passed tests:")
        for test in passed_tests:
            test_short = test.split('.')[-1]
            output_file = test_results[test]["output_file"]
            print(f"  - {test_short} (📄 {output_file})")
    
    print(f"\n📊 All test outputs saved in tmp/ folder")
    print(f"📊 Use '../BACKGROUND_CMD --status' to see process details")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='GDS并行测试运行器',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 run_gds_tests_parallel.py --list                    # 列出所有测试
  python3 run_gds_tests_parallel.py --range 0 4               # 运行测试0-4 (5个测试)
  python3 run_gds_tests_parallel.py --range 10 14 --max 2     # 运行测试10-14，最大并发2
        """
    )
    
    parser.add_argument('--list', action='store_true', help='列出所有测试及其ID')
    parser.add_argument('--range', nargs=2, type=int, metavar=('START', 'END'), 
                       help='指定测试ID范围 (包含START和END)')
    parser.add_argument('--max', type=int, default=3, metavar='N',
                       help='最大并发数 (默认: 3)')
    
    args = parser.parse_args()
    
    if args.list:
        list_tests()
    elif args.range:
        start_id, end_id = args.range
        run_tests_range(start_id, end_id, args.max)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
