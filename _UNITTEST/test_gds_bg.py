#!/usr/bin/env python3
"""
GDS --bg (Background Tasks) 单元测试

测试GDS后台任务功能的完整性，包括：
- 基础后台任务执行
- 状态查询和结果获取
- 日志查看和清理功能
- 错误处理和边缘情况
- 引号处理和复杂命令
- 直接反馈功能
"""

import unittest
import subprocess
import sys
import time
import json
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class GDSBackgroundTest(unittest.TestCase):
    """GDS --bg 功能测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        print(f"设置GDS --bg测试环境...")
        
        # 设置路径
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GDS_CMD = ["python3", str(cls.BIN_DIR / "GOOGLE_DRIVE.py")]
        cls.TEST_DATA_DIR = Path(__file__).parent / "_DATA"
        
        # 确保GDS可用
        try:
            result = subprocess.run(
                cls.GDS_CMD + ["--shell", "pwd"], 
                capture_output=True, 
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"GDS不可用: {result.stderr}")
        except Exception as e:
            raise Exception(f"GDS测试环境设置失败: {e}")
    
    def run_gds_bg_command(self, command):
        """运行GDS --bg命令并返回结果 - 无timeout限制，允许用户手动操作"""
        cmd = self.GDS_CMD + ["--shell", f"--bg {command}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    
    def run_gds_bg_status(self, task_id):
        """查询GDS --bg任务状态 - 无timeout限制，允许用户手动操作"""
        cmd = self.GDS_CMD + ["--shell", f"--bg --status {task_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    
    def run_gds_bg_result(self, task_id):
        """获取GDS --bg任务结果 - 无timeout限制，允许用户手动操作"""
        cmd = self.GDS_CMD + ["--shell", f"--bg --result {task_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    
    def run_gds_bg_cleanup(self, task_id):
        """清理GDS --bg任务 - 无timeout限制，允许用户手动操作"""
        cmd = self.GDS_CMD + ["--shell", f"--bg --cleanup {task_id}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result
    
    def extract_task_id(self, output):
        """从--bg命令输出中提取任务ID"""
        # 查找 "Background task started with ID: XXXXXXXXXX_XXXX" 模式
        match = re.search(r'Background task started with ID: (\d+_\d+)', output)
        if match:
            return match.group(1)
        return None
    
    def wait_for_task_completion(self, task_id, max_wait=30):
        """等待任务完成"""
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_result = self.run_gds_bg_status(task_id)
            
            if status_result.returncode == 0 and "Status: completed" in status_result.stdout:
                return True
            elif status_result.returncode == 0 and "Status: running" in status_result.stdout:
                pass  # Continue waiting
            else:
                print(f"WARNING: 任务 {task_id} 状态异常，返回码: {status_result.returncode}")
                print(f"WARNING: 输出内容: {status_result.stdout}")
            
            time.sleep(1)
        
        print(f"ERROR: 任务 {task_id} 在 {max_wait} 秒内未完成")
        return False
    
    def test_01_basic_echo_command(self):
        """测试基础echo命令"""
        print("\n测试1: 基础echo命令")
        
        # 执行后台任务
        result = self.run_gds_bg_command("echo 'Hello GDS Background'")
        self.assertEqual(result.returncode, 0, f"后台任务创建失败: {result.stderr}")
        
        # 提取任务ID
        task_id = self.extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, f"无法提取任务ID: {result.stdout}")
        print(f"任务ID: {task_id}")
        
        # 等待任务完成
        completed = self.wait_for_task_completion(task_id, max_wait=10)
        self.assertTrue(completed, "任务未在预期时间内完成")
        
        # 检查结果
        result_output = self.run_gds_bg_result(task_id)
        self.assertEqual(result_output.returncode, 0, f"获取结果失败: {result_output.stderr}")
        self.assertIn("Hello GDS Background", result_output.stdout, "结果内容不正确")
        
        # 清理任务
        cleanup_result = self.run_gds_bg_cleanup(task_id)
        self.assertEqual(cleanup_result.returncode, 0, f"清理任务失败: {cleanup_result.stderr}")
        
        print("✅ 基础echo命令测试通过")
    
    def test_02_complex_command_with_quotes(self):
        """测试包含引号的复杂命令"""
        print("\n测试2: 包含引号的复杂命令")
        
        # 测试包含单引号的命令
        result = self.run_gds_bg_command("echo 'Complex command with \"double quotes\" and single quotes'")
        self.assertEqual(result.returncode, 0, f"复杂命令创建失败: {result.stderr}")
        
        task_id = self.extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, "无法提取任务ID")
        print(f"任务ID: {task_id}")
        
        # 等待完成并检查结果
        completed = self.wait_for_task_completion(task_id, max_wait=10)
        self.assertTrue(completed, "复杂命令未完成")
        
        result_output = self.run_gds_bg_result(task_id)
        self.assertEqual(result_output.returncode, 0, "获取复杂命令结果失败")
        self.assertIn("double quotes", result_output.stdout, "复杂命令结果不正确")
        
        # 清理
        self.run_gds_bg_cleanup(task_id)
        print("✅ 复杂命令测试通过")
    
    def test_03_multi_command_pipeline(self):
        """测试多命令管道"""
        print("\n测试3: 多命令管道")
        
        # 测试命令管道
        result = self.run_gds_bg_command("echo 'line1'; echo 'line2'; echo 'line3'")
        self.assertEqual(result.returncode, 0, f"管道命令创建失败: {result.stderr}")
        
        task_id = self.extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, "无法提取管道任务ID")
        print(f"任务ID: {task_id}")
        
        # 等待完成
        completed = self.wait_for_task_completion(task_id, max_wait=15)
        self.assertTrue(completed, "管道命令未完成")
        
        # 检查结果包含所有行
        result_output = self.run_gds_bg_result(task_id)
        self.assertEqual(result_output.returncode, 0, "获取管道结果失败")
        
        output_lines = result_output.stdout.strip().split('\n')
        self.assertIn("line1", result_output.stdout, "管道结果缺少line1")
        self.assertIn("line2", result_output.stdout, "管道结果缺少line2") 
        self.assertIn("line3", result_output.stdout, "管道结果缺少line3")
        
        # 清理
        self.run_gds_bg_cleanup(task_id)
        print("✅ 多命令管道测试通过")
    
    def test_04_error_command_handling(self):
        """测试错误命令处理"""
        print("\n测试4: 错误命令处理")
        
        # 执行一个会失败的命令
        result = self.run_gds_bg_command("ls /nonexistent/directory/that/should/not/exist")
        self.assertEqual(result.returncode, 0, "错误命令任务创建应该成功")
        
        task_id = self.extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, "无法提取错误任务ID")
        print(f"任务ID: {task_id}")
        
        # 等待完成
        completed = self.wait_for_task_completion(task_id, max_wait=10)
        self.assertTrue(completed, "错误命令未完成")
        
        # 检查状态显示完成（即使命令失败）
        status_result = self.run_gds_bg_status(task_id)
        self.assertEqual(status_result.returncode, 0, "状态查询失败")
        self.assertIn("Status: completed", status_result.stdout, "错误命令状态不正确")
        
        # 清理
        self.run_gds_bg_cleanup(task_id)
        print("✅ 错误命令处理测试通过")
    
    def test_05_status_query_functionality(self):
        """测试状态查询功能"""
        print("\n测试5: 状态查询功能")
        
        # 创建一个较长的任务
        result = self.run_gds_bg_command("echo 'Starting...'; sleep 3; echo 'Done'")
        self.assertEqual(result.returncode, 0, "长任务创建失败")
        
        task_id = self.extract_task_id(result.stdout)
        self.assertIsNotNone(task_id, "无法提取长任务ID")
        print(f"任务ID: {task_id}")
        
        # 立即查询状态（应该是running或completed）
        status_result = self.run_gds_bg_status(task_id)
        self.assertEqual(status_result.returncode, 0, "状态查询失败")
        
        # 状态应该包含基本信息
        self.assertIn("Status:", status_result.stdout, "状态输出缺少Status字段")
        self.assertIn("Command:", status_result.stdout, "状态输出缺少Command字段")
        
        # 等待完成
        completed = self.wait_for_task_completion(task_id, max_wait=15)
        self.assertTrue(completed, "长任务未完成")
        
        # 再次查询状态，应该是completed
        final_status = self.run_gds_bg_status(task_id)
        self.assertEqual(final_status.returncode, 0, "最终状态查询失败")
        self.assertIn("Status: completed", final_status.stdout, "最终状态不正确")
        
        # 清理
        self.run_gds_bg_cleanup(task_id)
        print("✅ 状态查询功能测试通过")
    
    def test_06_nonexistent_task_handling(self):
        """测试不存在任务的处理"""
        print("\n测试6: 不存在任务的处理")
        
        fake_task_id = "9999999999_9999"
        
        # 查询不存在任务的状态
        status_result = self.run_gds_bg_status(fake_task_id)
        self.assertNotEqual(status_result.returncode, 0, "不存在任务的状态查询应该失败")
        
        # 获取不存在任务的结果
        result_output = self.run_gds_bg_result(fake_task_id)
        self.assertNotEqual(result_output.returncode, 0, "不存在任务的结果获取应该失败")
        
        # 清理不存在的任务
        cleanup_result = self.run_gds_bg_cleanup(fake_task_id)
        self.assertNotEqual(cleanup_result.returncode, 0, "不存在任务的清理应该失败")
        
        print("✅ 不存在任务处理测试通过")
    
    def test_07_concurrent_tasks(self):
        """测试并发任务"""
        print("\n测试7: 并发任务")
        
        task_ids = []
        
        # 创建多个并发任务
        for i in range(3):
            result = self.run_gds_bg_command(f"echo 'Task {i}'; sleep 2; echo 'Task {i} done'")
            self.assertEqual(result.returncode, 0, f"任务{i}创建失败")
            
            task_id = self.extract_task_id(result.stdout)
            self.assertIsNotNone(task_id, f"无法提取任务{i}的ID")
            task_ids.append(task_id)
            print(f"任务{i} ID: {task_id}")
        
        # 等待所有任务完成
        for i, task_id in enumerate(task_ids):
            completed = self.wait_for_task_completion(task_id, max_wait=20)
            self.assertTrue(completed, f"任务{i}未完成")
            
            # 检查结果
            result_output = self.run_gds_bg_result(task_id)
            self.assertEqual(result_output.returncode, 0, f"任务{i}结果获取失败")
            self.assertIn(f"Task {i}", result_output.stdout, f"任务{i}结果不正确")
        
        # 清理所有任务
        for task_id in task_ids:
            self.run_gds_bg_cleanup(task_id)
        
        print("✅ 并发任务测试通过")

def run_tests():
    """运行所有测试"""
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(GDSBackgroundTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()

if __name__ == "__main__":
    print("=" * 60)
    print("GDS --bg (Background Tasks) 单元测试")
    print("=" * 60)
    
    success = run_tests()
    
    if success:
        print("\n🎉 所有GDS --bg测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分GDS --bg测试失败")
        sys.exit(1)
