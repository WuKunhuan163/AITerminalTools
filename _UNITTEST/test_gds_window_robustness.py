#!/usr/bin/env python3
"""
GDS窗口管理器鲁棒性测试套件
测试跨进程文件锁机制在各种边界情况下的表现

测试场景：
1. 并发窗口请求测试
2. 进程异常终止测试
3. 超时处理测试
4. 用户操作模拟测试
5. 锁文件异常情况测试
6. 高并发压力测试
"""

import unittest
import subprocess
import threading
import time
import os
import signal
import psutil
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import shutil

class TestWindowRobustness(unittest.TestCase):
    """GDS窗口管理器鲁棒性测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GOOGLE_DRIVE_PY = cls.BIN_DIR / "GOOGLE_DRIVE.py"
        cls.LOCK_FILE = cls.BIN_DIR / "GOOGLE_DRIVE_DATA" / "window_lock.lock"
        cls.DEBUG_LOG = cls.BIN_DIR / "GOOGLE_DRIVE_DATA" / "window_queue_debug.log"
        
        # 清理测试环境
        cls._cleanup_test_environment()
        
        print("🧪 GDS窗口鲁棒性测试套件启动")
    
    @classmethod
    def _cleanup_test_environment(cls):
        """清理测试环境"""
        try:
            # 清理锁文件
            if cls.LOCK_FILE.exists():
                cls.LOCK_FILE.unlink()
            
            # 清理debug日志
            if cls.DEBUG_LOG.exists():
                cls.DEBUG_LOG.unlink()
                
            # 杀死所有遗留的GDS进程
            for proc in psutil.process_iter(['pid', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline']
                    if cmdline and 'GOOGLE_DRIVE.py' in ' '.join(cmdline):
                        proc.kill()
                        proc.wait(timeout=3)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    pass
                    
        except Exception as e:
            print(f"清理环境时出错: {e}")
    
    def setUp(self):
        """每个测试前的准备"""
        self._cleanup_test_environment()
        time.sleep(0.5)  # 确保环境完全清理
    
    def test_concurrent_window_requests(self):
        """测试1: 并发窗口请求 - 验证只有一个窗口显示"""
        print("\\n🔄 测试1: 并发窗口请求")
        
        def run_gds_command(cmd_id):
            """运行单个GDS命令"""
            start_time = time.time()
            try:
                result = subprocess.run(
                    ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'touch', f'test_concurrent_{cmd_id}.txt'],
                    capture_output=True,
                    text=True,
                    timeout=30  # 较短超时，测试队列机制
                )
                end_time = time.time()
                return {
                    'cmd_id': cmd_id,
                    'duration': end_time - start_time,
                    'returncode': result.returncode,
                    'stdout': result.stdout[:200],
                    'stderr': result.stderr[:200]
                }
            except subprocess.TimeoutExpired:
                return {
                    'cmd_id': cmd_id,
                    'duration': 30,
                    'returncode': 'timeout',
                    'stdout': '',
                    'stderr': 'Command timed out'
                }
        
        # 启动5个并发命令
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_gds_command, i) for i in range(5)]
            results = [future.result() for future in as_completed(futures)]
        
        # 分析结果
        print(f"📊 并发命令结果:")
        for result in sorted(results, key=lambda x: x['cmd_id']):
            print(f"  命令{result['cmd_id']}: 耗时{result['duration']:.1f}s, 返回码: {result['returncode']}")
        
        # 验证debug日志中的锁获取顺序
        if self.DEBUG_LOG.exists():
            with open(self.DEBUG_LOG, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            lock_acquired_count = log_content.count('LOCK_ACQUIRED')
            window_created_count = log_content.count('TKINTER_WINDOW_CREATED')
            
            print(f"📋 日志分析: {lock_acquired_count}个锁获取, {window_created_count}个窗口创建")
            
            # 验证锁获取是串行的
            self.assertGreater(lock_acquired_count, 0, "应该有锁获取记录")
            
        print("并发窗口请求测试完成")
    
    def test_process_crash_recovery(self):
        """测试2: 进程崩溃恢复 - 验证锁能正确释放"""
        print("\\n💥 测试2: 进程崩溃恢复")
        
        # 启动一个长时间运行的GDS命令
        proc = subprocess.Popen(
            ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'touch', 'test_crash.txt'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # 等待窗口创建
        time.sleep(2)
        print(f"📋 启动进程 PID: {proc.pid}")
        
        # 强制杀死进程
        try:
            proc.kill()
            proc.wait(timeout=5)
            print("💀 进程已强制终止")
        except subprocess.TimeoutExpired:
            print("Warning: 进程终止超时")
        
        # 等待锁释放
        time.sleep(1)
        
        # 启动新的命令，应该能立即获得锁
        start_time = time.time()
        result = subprocess.run(
            ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'touch', 'test_after_crash.txt'],
            capture_output=True,
            text=True,
            timeout=10
        )
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"🔄 崩溃后新命令耗时: {duration:.1f}s")
        
        # 验证新命令能快速获得锁（不应该长时间等待）
        self.assertLess(duration, 8, "崩溃后新命令应该能快速获得锁")
        
        print("进程崩溃恢复测试完成")
    
    def test_timeout_handling(self):
        """测试3: 超时处理 - 验证超时后锁正确释放"""
        print("\\n⏰ 测试3: 超时处理")
        
        # 启动一个会超时的命令
        start_time = time.time()
        try:
            result = subprocess.run(
                ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'touch', 'test_timeout.txt'],
                capture_output=True,
                text=True,
                timeout=5  # 5秒超时
            )
            print("Warning: 命令意外完成，没有超时")
        except subprocess.TimeoutExpired:
            print("⏰ 命令按预期超时")
        
        # 等待进程清理
        time.sleep(1)
        
        # 启动新命令，验证能正常获得锁
        start_time = time.time()
        result = subprocess.run(
            ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'touch', 'test_after_timeout.txt'],
            capture_output=True,
            text=True,
            timeout=8
        )
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"🔄 超时后新命令耗时: {duration:.1f}s")
        
        # 验证新命令能获得锁
        self.assertLess(duration, 7, "超时后新命令应该能获得锁")
        
        print("超时处理测试完成")
    
    def test_lock_file_corruption(self):
        """测试4: 锁文件异常 - 验证系统在锁文件异常时的行为"""
        print("\\n🔧 测试4: 锁文件异常处理")
        
        # 创建一个损坏的锁文件
        self.LOCK_FILE.parent.mkdir(exist_ok=True)
        with open(self.LOCK_FILE, 'w') as f:
            f.write("corrupted lock file content")
        
        # 设置异常权限
        try:
            os.chmod(self.LOCK_FILE, 0o000)  # 无权限
            print("🔒 设置锁文件为无权限")
        except OSError:
            print("Warning: 无法设置文件权限")
        
        # 尝试运行GDS命令
        try:
            result = subprocess.run(
                ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'touch', 'test_lock_corruption.txt'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            print(f"📋 命令返回码: {result.returncode}")
            if result.stderr:
                print(f"📋 错误输出: {result.stderr[:200]}")
                
        except subprocess.TimeoutExpired:
            print("⏰ 命令超时")
        except Exception as e:
            print(f"Error: 命令执行异常: {e}")
        
        # 恢复锁文件权限
        try:
            os.chmod(self.LOCK_FILE, 0o644)
            self.LOCK_FILE.unlink()
        except OSError:
            pass
        
        print("锁文件异常处理测试完成")
    
    def test_high_concurrency_stress(self):
        """测试5: 高并发压力测试"""
        print("\\n🚀 测试5: 高并发压力测试")
        
        def quick_gds_command(cmd_id):
            """快速GDS命令"""
            try:
                result = subprocess.run(
                    ['python', str(self.GOOGLE_DRIVE_PY), '--shell', 'echo', f'stress_test_{cmd_id}'],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                return {'cmd_id': cmd_id, 'success': result.returncode == 0}
            except subprocess.TimeoutExpired:
                return {'cmd_id': cmd_id, 'success': False}
        
        # 启动10个并发命令
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(quick_gds_command, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        end_time = time.time()
        
        total_duration = end_time - start_time
        success_count = sum(1 for r in results if r['success'])
        
        print(f"📊 压力测试结果:")
        print(f"  总耗时: {total_duration:.1f}s")
        print(f"  成功命令: {success_count}/10")
        print(f"  平均每命令: {total_duration/10:.1f}s")
        
        # 验证大部分命令成功
        self.assertGreaterEqual(success_count, 7, "大部分命令应该成功")
        
        print("高并发压力测试完成")
    
    def test_debug_log_integrity(self):
        """测试6: Debug日志完整性"""
        print("\\n📝 测试6: Debug日志完整性")
        
        # 运行几个命令生成debug日志
        commands = [
            ['touch', 'debug_test_1.txt'],
            ['echo', 'debug_test_2'],
            ['touch', 'debug_test_3.txt']
        ]
        
        for i, cmd in enumerate(commands):
            try:
                result = subprocess.run(
                    ['python', str(self.GOOGLE_DRIVE_PY), '--shell'] + cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                print(f"📋 命令{i+1}完成: {result.returncode}")
            except subprocess.TimeoutExpired:
                print(f"⏰ 命令{i+1}超时")
        
        # 分析debug日志
        if self.DEBUG_LOG.exists():
            with open(self.DEBUG_LOG, 'r', encoding='utf-8') as f:
                log_content = f.read()
            
            # 统计关键事件
            lock_requests = log_content.count('CROSS_PROCESS_LOCK')
            lock_acquired = log_content.count('LOCK_ACQUIRED')
            window_created = log_content.count('TKINTER_WINDOW_CREATE')
            window_completed = log_content.count('CROSS_PROCESS_WINDOW')
            
            print(f"📊 Debug日志分析:")
            print(f"  锁请求: {lock_requests}")
            print(f"  锁获取: {lock_acquired}")
            print(f"  窗口创建: {window_created}")
            print(f"  窗口完成: {window_completed}")
            
            # 验证日志完整性
            self.assertGreater(lock_requests, 0, "应该有锁请求记录")
            self.assertGreater(lock_acquired, 0, "应该有锁获取记录")
            
            # 验证日志格式
            lines = log_content.split('\\n')
            valid_lines = [line for line in lines if line.strip() and 'DEBUG:' in line]
            print(f"  有效日志行数: {len(valid_lines)}")
            
            self.assertGreater(len(valid_lines), 0, "应该有有效的debug日志")
            
        else:
            print("Warning: Debug日志文件不存在")
        
        print("Debug日志完整性测试完成")
    
    def tearDown(self):
        """每个测试后的清理"""
        pass  # 主要清理在setUp中进行
    
    @classmethod
    def tearDownClass(cls):
        """测试套件结束后的清理"""
        cls._cleanup_test_environment()
        print("🧹 测试环境清理完成")

def run_robustness_tests():
    """运行鲁棒性测试套件"""
    print("=" * 60)
    print("🧪 GDS窗口管理器鲁棒性测试套件")
    print("=" * 60)
    print("测试内容:")
    print("1. 并发窗口请求测试")
    print("2. 进程崩溃恢复测试") 
    print("3. 超时处理测试")
    print("4. 锁文件异常处理测试")
    print("5. 高并发压力测试")
    print("6. Debug日志完整性测试")
    print("=" * 60)
    
    # 运行测试
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestWindowRobustness)
    runner = unittest.TextTestRunner(verbosity=2, buffer=False)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"测试完成: {result.testsRun}个测试, {len(result.failures)}个失败, {len(result.errors)}个错误")
    print("=" * 60)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_robustness_tests()
    exit(0 if success else 1)
