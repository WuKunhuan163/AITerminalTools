#!/usr/bin/env python3
"""
BACKGROUND_CMD 单元测试
"""

import os
import sys
import json
import time
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from BACKGROUND_CMD import ProcessManager
except ImportError:
    # 如果直接导入失败，尝试加载模块
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "BACKGROUND_CMD", 
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "BACKGROUND_CMD.py")
    )
    background_cmd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(background_cmd)
    ProcessManager = background_cmd.ProcessManager


class TestBackgroundCmd(unittest.TestCase):
    """BACKGROUND_CMD 测试类"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = os.path.join(self.temp_dir, "logs")
        self.manager = ProcessManager(max_processes=10, log_dir=self.log_dir)
        
    def tearDown(self):
        """测试后清理"""
        # 清理所有进程
        try:
            self.manager.cleanup_all()
        except:
            pass
        
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_process_creation(self):
        """测试进程创建"""
        result = self.manager.create_process("sleep 1", shell="bash")
        self.assertIsNotNone(result)
        
        pid, log_file = result
        self.assertIsInstance(pid, int)
        self.assertTrue(pid > 0)
        self.assertTrue(os.path.exists(log_file))
        
        # 等待进程结束
        time.sleep(2)
        
    def test_process_listing(self):
        """测试进程列表"""
        # 创建一个长时间运行的进程
        result = self.manager.create_process("sleep 5", shell="zsh")
        self.assertIsNotNone(result)
        
        # 列出进程
        processes = self.manager.list_processes()
        self.assertIsInstance(processes, list)
        self.assertGreater(len(processes), 0)
        
        # 检查进程信息
        proc = processes[0]
        self.assertIn('pid', proc)
        self.assertIn('command', proc)
        self.assertIn('shell', proc)
        self.assertIn('status', proc)
        
    def test_process_termination(self):
        """测试进程终止"""
        # 创建一个长时间运行的进程
        result = self.manager.create_process("sleep 10", shell="bash")
        self.assertIsNotNone(result)
        
        pid, _ = result
        
        # 终止进程
        success = self.manager.kill_process(pid)
        self.assertTrue(success)
        
        # 等待一下
        time.sleep(1)
        
        # 检查进程是否已从列表中移除
        processes = self.manager.list_processes()
        pids = [p['pid'] for p in processes]
        self.assertNotIn(pid, pids)
        
    def test_max_processes_limit(self):
        """测试最大进程数限制"""
        # 设置较小的限制
        small_manager = ProcessManager(max_processes=2, log_dir=self.log_dir)
        
        # 创建进程直到达到限制
        results = []
        for i in range(3):
            result = small_manager.create_process(f"sleep {i+1}", shell="bash")
            if result:
                results.append(result)
        
        # 应该只能创建2个进程
        self.assertLessEqual(len(results), 2)
        
        # 清理
        small_manager.cleanup_all()
        
    def test_shell_types(self):
        """测试不同shell类型"""
        # 测试bash
        result_bash = self.manager.create_process("echo 'test'", shell="bash")
        self.assertIsNotNone(result_bash)
        
        # 测试zsh
        result_zsh = self.manager.create_process("echo 'test'", shell="zsh")
        self.assertIsNotNone(result_zsh)
        
        # 等待进程完成
        time.sleep(2)
        
    def test_invalid_shell(self):
        """测试无效shell类型"""
        result = self.manager.create_process("echo 'test'", shell="invalid_shell")
        self.assertIsNone(result)
        
    def test_cleanup_all(self):
        """测试清理所有进程"""
        # 创建多个进程
        pids = []
        for i in range(3):
            result = self.manager.create_process(f"sleep {i+5}", shell="bash")
            if result:
                pids.append(result[0])
        
        # 清理所有进程
        count = self.manager.cleanup_all()
        self.assertEqual(count, len(pids))
        
        # 检查进程列表为空
        processes = self.manager.list_processes()
        self.assertEqual(len(processes), 0)
        
    def test_log_files(self):
        """测试日志文件创建"""
        result = self.manager.create_process("echo 'Hello World'", shell="bash")
        self.assertIsNotNone(result)
        
        pid, log_file = result
        
        # 等待进程完成
        time.sleep(2)
        
        # 检查日志文件存在且有内容
        self.assertTrue(os.path.exists(log_file))
        with open(log_file, 'r') as f:
            content = f.read()
            self.assertIn('Hello World', content)
            
    def test_dead_process_cleanup(self):
        """测试死亡进程自动清理"""
        # 创建一个短时间进程
        result = self.manager.create_process("sleep 1", shell="bash")
        self.assertIsNotNone(result)
        
        pid, _ = result
        
        # 等待进程结束
        time.sleep(3)
        
        # 调用清理，应该自动移除死亡进程
        processes = self.manager.list_processes()
        pids = [p['pid'] for p in processes]
        self.assertNotIn(pid, pids)


class TestBackgroundCmdCLI(unittest.TestCase):
    """BACKGROUND_CMD 命令行接口测试"""
    
    def setUp(self):
        """测试前准备"""
        self.cmd_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "BACKGROUND_CMD.py")
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """测试后清理"""
        # 清理临时目录
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            
        # 清理可能创建的进程
        try:
            subprocess.run([
                "python3", self.cmd_path, "--cleanup"
            ], capture_output=True, timeout=10)
        except:
            pass
    
    def test_help_command(self):
        """测试帮助命令"""
        result = subprocess.run([
            "python3", self.cmd_path, "--help"
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("BACKGROUND_CMD", result.stdout)
        self.assertIn("usage:", result.stdout)
        
    def test_create_process_command(self):
        """测试创建进程命令"""
        result = subprocess.run([
            "python3", self.cmd_path, "sleep 1", 
            "--log-dir", self.temp_dir
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("Process started: PID", result.stdout)
        
    def test_list_processes_json(self):
        """测试JSON格式列出进程"""
        result = subprocess.run([
            "python3", self.cmd_path, "--list", "--json",
            "--log-dir", self.temp_dir
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        
        # 解析JSON输出
        try:
            data = json.loads(result.stdout)
            self.assertIn('success', data)
            self.assertIn('processes', data)
            self.assertIn('total_count', data)
        except json.JSONDecodeError:
            self.fail("输出不是有效的JSON格式")
            
    def test_invalid_command(self):
        """测试无效命令"""
        result = subprocess.run([
            "python3", self.cmd_path, "nonexistent_command_xyz",
            "--log-dir", self.temp_dir
        ], capture_output=True, text=True, timeout=10)
        
        # 命令应该能创建，但会很快失败
        # 这里主要测试不会崩溃
        self.assertIn(result.returncode, [0, 1])


def run_tests():
    """运行所有测试"""
    print("=== BACKGROUND_CMD Unit Tests ===")
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestBackgroundCmd))
    suite.addTests(loader.loadTestsFromTestCase(TestBackgroundCmdCLI))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print()
    print("=== Test Results ===")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\nSuccess rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
