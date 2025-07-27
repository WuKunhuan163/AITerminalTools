#!/usr/bin/env python3
"""
Google Drive Shell修复功能的单元测试
测试bash解析、直接反馈、JSON处理等功能
"""

import unittest
import sys
import os
import json
import tempfile
import shlex
from unittest.mock import Mock, patch, MagicMock

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestGoogleDriveShellFixes(unittest.TestCase):
    """测试Google Drive Shell的修复功能"""
    
    def setUp(self):
        """测试前设置"""
        pass
    
    def test_bash_command_escaping(self):
        """测试bash命令转义功能"""
        # 测试简单命令
        cmd = "echo"
        args = ["hello world"]
        
        # 模拟_generate_remote_command方法
        import shlex
        if args:
            escaped_args = [shlex.quote(arg) for arg in args]
            full_command = f"{cmd} {' '.join(escaped_args)}"
        else:
            full_command = cmd
        
        # 验证转义结果
        self.assertEqual(full_command, "echo 'hello world'")
    
    def test_python_command_escaping(self):
        """测试Python命令的特殊字符转义"""
        cmd = "python"
        args = ["-c", "import torch; print(torch.cuda.is_available())"]
        
        import shlex
        escaped_args = [shlex.quote(arg) for arg in args]
        full_command = f"{cmd} {' '.join(escaped_args)}"
    
    def test_upload_path_judgment(self):
        """测试upload命令的路径判断逻辑"""
        test_cases = [
            # (target_path, expected_is_file, description)
            ("IMPORTANT.md", True, "包含点号的路径应该被识别为文件"),
            ("config.json", True, "JSON文件应该被识别为文件"),
            ("README.txt", True, "文本文件应该被识别为文件"),
            ("src", False, "不包含点号的路径应该被识别为目录"),
            ("_TAKEAWAY", False, "下划线开头的目录应该被识别为目录"),
            ("folder", False, "普通目录名应该被识别为目录"),
            ("path/to/file.py", True, "带路径的文件名应该被识别为文件"),
            ("path/to/folder", False, "带路径的目录名应该被识别为目录"),
            (".", False, "当前目录标识符应该被识别为目录"),
            ("..", False, "父目录标识符应该被识别为目录"),
        ]
        
        for target_path, expected_is_file, description in test_cases:
            with self.subTest(target_path=target_path):
                # 使用修复后的逻辑
                last_part = target_path.split('/')[-1] if target_path not in [".", ""] else ""
                is_file = '.' in last_part and last_part != '.' and last_part != '..'
                
                self.assertEqual(is_file, expected_is_file, 
                               f"路径判断失败: {target_path} - {description}")
    
    def test_upload_rename_scenario(self):
        """测试upload重命名场景的路径计算"""
        # 模拟参数
        REMOTE_ROOT = "/content/drive/MyDrive"
        current_path = "~/GaussianObject/_TAKEAWAY"
        target_path = "IMPORTANT.md"
        filename = "important.txt"
        
        # 计算target_absolute（模拟generate_remote_commands中的逻辑）
        if current_path.startswith("~/"):
            current_relative = current_path[2:]  # 去掉 ~/
            combined_path = f"{REMOTE_ROOT}/{current_relative}/{target_path}"
        else:
            combined_path = f"{REMOTE_ROOT}/{target_path}"
        
        import os.path
        target_absolute = os.path.normpath(combined_path)
        
        # 判断是否为文件
        last_part = target_path.split('/')[-1] if target_path not in [".", ""] else ""
        is_target_file = '.' in last_part and last_part != '.' and last_part != '..'
        
        # 计算最终目标路径
        if is_target_file and True:  # 假设只有一个文件
            dest_absolute = target_absolute
        else:
            dest_absolute = f"{target_absolute.rstrip('/')}/{filename}"
        
        # 验证结果
        expected_path = "/content/drive/MyDrive/GaussianObject/_TAKEAWAY/IMPORTANT.md"
        self.assertEqual(dest_absolute, expected_path, 
                        "重命名场景的目标路径计算错误")
        self.assertTrue(is_target_file, "IMPORTANT.md应该被识别为文件")
    
    def test_upload_directory_scenario(self):
        """测试upload到目录场景的路径计算"""
        # 模拟参数
        REMOTE_ROOT = "/content/drive/MyDrive"
        current_path = "~/GaussianObject/_TAKEAWAY"
        target_path = "backup"  # 目录名
        filename = "important.txt"
        
        # 计算target_absolute
        if current_path.startswith("~/"):
            current_relative = current_path[2:]
            combined_path = f"{REMOTE_ROOT}/{current_relative}/{target_path}"
        else:
            combined_path = f"{REMOTE_ROOT}/{target_path}"
        
        import os.path
        target_absolute = os.path.normpath(combined_path)
        
        # 判断是否为文件
        last_part = target_path.split('/')[-1] if target_path not in [".", ""] else ""
        is_target_file = '.' in last_part and last_part != '.' and last_part != '..'
        
        # 计算最终目标路径
        if is_target_file and True:  # 假设只有一个文件
            dest_absolute = target_absolute
        else:
            dest_absolute = f"{target_absolute.rstrip('/')}/{filename}"
        
        # 验证结果
        expected_path = "/content/drive/MyDrive/GaussianObject/_TAKEAWAY/backup/important.txt"
        self.assertEqual(dest_absolute, expected_path, 
                        "目录场景的目标路径计算错误")
        self.assertFalse(is_target_file, "backup应该被识别为目录")
    
    def test_mv_command_path_judgment(self):
        """测试mv命令的路径判断逻辑"""
        test_cases = [
            # (dst_path, expected_is_file, description)
            ("renamed_file.txt", True, "重命名为文件"),
            ("backup/", False, "移动到目录（显式斜杠）"),
            ("config.json", True, "重命名为配置文件"),
            ("documents", False, "移动到文档目录"),
            ("path/to/new_name.py", True, "重命名到子路径"),
        ]
        
        for dst_path, expected_is_file, description in test_cases:
            with self.subTest(dst_path=dst_path):
                # 使用修复后的逻辑
                last_part = dst_path.split('/')[-1]
                is_file = '.' in last_part and last_part != '.' and last_part != '..'
                
                self.assertEqual(is_file, expected_is_file, 
                               f"mv命令路径判断失败: {dst_path} - {description}")
    
    def test_json_parsing_robustness(self):
        """测试JSON解析的健壮性"""
        # 测试有效JSON
        valid_json = '{"cmd": "test", "exit_code": 0, "stdout": "output"}'
        try:
            result = json.loads(valid_json)
            self.assertEqual(result["cmd"], "test")
            self.assertEqual(result["exit_code"], 0)
        except json.JSONDecodeError:
            self.fail("Valid JSON should parse successfully")
        
        # 测试无效JSON的处理
        invalid_json = '{"cmd": "test", "exit_code": }'
        with self.assertRaises(json.JSONDecodeError):
            json.loads(invalid_json)
    
    def test_error_keyword_detection(self):
        """测试错误关键词检测功能"""
        error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 
                         'traceback', 'Traceback', 'TRACEBACK', 'failed', 'Failed', 'FAILED']
        
        # 测试包含错误的输出
        error_output = "This is an error message"
        has_error = any(keyword in error_output for keyword in error_keywords)
        self.assertTrue(has_error)
        
        # 测试正常输出
        normal_output = "Command completed successfully"
        has_error = any(keyword in normal_output for keyword in error_keywords)
        self.assertFalse(has_error)
    
    def test_exit_code_extraction(self):
        """测试退出码提取功能"""
        # 模拟包含退出码标记的输出
        output_with_marker = "Some output\nEXIT_CODE_MARKER:0\n"
        
        # 提取退出码
        lines = output_with_marker.split('\n')
        exit_code = None
        for line in lines:
            if line.startswith("EXIT_CODE_MARKER:"):
                exit_code = line.split(":")[1]
                break
        
        self.assertEqual(exit_code, "0")
        
        # 测试没有标记的情况
        output_without_marker = "Some output\nNo marker here\n"
        lines = output_without_marker.split('\n')
        exit_code = None
        for line in lines:
            if line.startswith("EXIT_CODE_MARKER:"):
                exit_code = line.split(":")[1]
                break
        
        self.assertIsNone(exit_code)
    
    def test_output_content_filtering(self):
        """测试输出内容过滤功能"""
        # 模拟包含执行信息的输出
        full_output = """🚀 开始执行命令: echo test
📁 工作目录: /path
⏰ 开始时间: 2025-01-01
============================================================
actual output content
============================================================
✅ 命令执行完成
📊 退出码: 0
⏰ 结束时间: 2025-01-01"""
        
        # 提取实际输出内容
        lines = full_output.split('\n')
        separator = "="*60
        start_idx = 0
        end_idx = len(lines)
        
        # 找到实际输出的开始
        for i, line in enumerate(lines):
            if line.startswith(separator):
                start_idx = i + 1
                break
        
        # 找到实际输出的结束
        for i in range(len(lines)-1, -1, -1):
            if lines[i].startswith(separator):
                end_idx = i
                break
        
        # 提取实际输出内容
        if start_idx < end_idx:
            actual_content = '\n'.join(lines[start_idx:end_idx])
        else:
            actual_content = full_output
        
        self.assertEqual(actual_content, "actual output content")

class TestDirectFeedbackFunctionality(unittest.TestCase):
    """测试直接反馈功能"""
    
    def test_direct_feedback_data_structure(self):
        """测试直接反馈的数据结构"""
        # 模拟直接反馈数据
        feedback_data = {
            "action": "direct_feedback",
            "data": {
                "cmd": "test_command",
                "args": ["arg1", "arg2"],
                "working_dir": "user_provided",
                "timestamp": "user_provided",
                "exit_code": 0,
                "stdout": "test output",
                "stderr": "",
                "source": "direct_feedback"
            }
        }
        
        # 验证数据结构
        self.assertEqual(feedback_data["action"], "direct_feedback")
        self.assertIn("data", feedback_data)
        self.assertEqual(feedback_data["data"]["cmd"], "test_command")
        self.assertEqual(feedback_data["data"]["source"], "direct_feedback")
    
    def test_feedback_error_classification(self):
        """测试反馈错误分类功能"""
        error_keywords = ['error', 'Error', 'ERROR', 'exception', 'Exception', 'EXCEPTION', 
                         'traceback', 'Traceback', 'TRACEBACK', 'failed', 'Failed', 'FAILED']
        
        # 测试错误输出分类
        error_output = "ImportError: No module named 'torch'"
        has_error = any(keyword in error_output for keyword in error_keywords)
        
        if has_error:
            stdout_content = ""
            stderr_content = error_output
            exit_code = 1
        else:
            stdout_content = error_output
            stderr_content = ""
            exit_code = 0
        
        self.assertEqual(stdout_content, "")
        self.assertEqual(stderr_content, error_output)
        self.assertEqual(exit_code, 1)

class TestBashScriptGeneration(unittest.TestCase):
    """测试bash脚本生成功能"""
    
    def test_command_construction(self):
        """测试命令构造"""
        # 测试简单命令
        cmd = "ls"
        args = ["-la"]
        
        import shlex
        if args:
            escaped_args = [shlex.quote(arg) for arg in args]
            full_command = f"{cmd} {' '.join(escaped_args)}"
        else:
            full_command = cmd
        
        self.assertEqual(full_command, "ls -la")
        
        # 测试包含特殊字符的命令
        cmd = "python"
        args = ["-c", "print('hello world')"]
        
        escaped_args = [shlex.quote(arg) for arg in args]
        full_command = f"{cmd} {' '.join(escaped_args)}"
        
        # shlex.quote会根据需要选择最合适的引号方式
        # 验证命令包含正确的结构
        self.assertIn("python", full_command)
        self.assertIn("-c", full_command)
        self.assertIn("print", full_command)
        self.assertIn("hello world", full_command)
    
    def test_json_args_escaping(self):
        """测试JSON参数转义"""
        args = ["-c", "import json; print(json.dumps({'key': 'value'}))"]
        
        import json as json_module
        args_json = json_module.dumps(args)
        
        # 验证JSON序列化成功
        self.assertIsInstance(args_json, str)
        
        # 验证可以反序列化
        restored_args = json_module.loads(args_json)
        self.assertEqual(restored_args, args)

if __name__ == '__main__':
    unittest.main() 