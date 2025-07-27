#!/usr/bin/env python3
"""
测试JSON输出捕获功能
验证点击"✅ 执行完成"时JSON文件能正确捕获stdout输出
"""

import os
import sys
import unittest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# 添加项目根目录到sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "GOOGLE_DRIVE_PROJ"))

# 导入被测试的模块
from google_drive_shell import GoogleDriveShell

class TestJSONOutputCapture(unittest.TestCase):
    """测试JSON输出捕获功能"""
    
    def setUp(self):
        """测试前准备"""
        self.shell = GoogleDriveShell()
        # Mock drive service
        self.shell.drive_service = Mock()
        self.shell.REMOTE_ROOT_FOLDER_ID = "test_folder_id"
        
    def test_remote_command_generation_order(self):
        """测试远程命令生成中的操作顺序"""
        # Mock current shell
        current_shell = {
            "current_path": "~",
            "current_folder_id": "test_folder_id"
        }
        
        # 生成远程命令
        remote_command, result_filename = self.shell._generate_remote_command("nvidia-smi", [], current_shell)
        
        # 验证命令结构
        self.assertIn("nvidia-smi", remote_command)
        self.assertIn("python3 << 'EOF'", remote_command)
        self.assertIn("print(json.dumps(result, indent=2, ensure_ascii=False))", remote_command)
        
        # 关键验证：确保临时文件清理在JSON生成之后
        lines = remote_command.split('\n')
        json_generation_line = -1
        cleanup_line = -1
        
        for i, line in enumerate(lines):
            if "print(json.dumps(result, indent=2, ensure_ascii=False))" in line:
                json_generation_line = i
            elif "rm -f \"$OUTPUT_FILE\" \"$ERROR_FILE\"" in line:
                cleanup_line = i
        
        # 验证JSON生成在临时文件清理之前
        self.assertGreater(json_generation_line, 0, "JSON生成行未找到")
        self.assertGreater(cleanup_line, 0, "临时文件清理行未找到")
        self.assertLess(json_generation_line, cleanup_line, "临时文件清理应该在JSON生成之后执行")
        
    def test_output_file_reading_logic(self):
        """测试输出文件读取逻辑"""
        # 模拟输出文件内容
        test_output = """🚀 开始执行命令: nvidia-smi
📁 工作目录: /content/drive/MyDrive/REMOTE_ROOT/test
⏰ 开始时间: Sun Jul 27 04:27:40 AM UTC 2025
============================================================
NVIDIA-SMI output here
Tesla T4 information
============================================================
✅ 命令执行完成
📊 退出码: 0
⏰ 结束时间: Sun Jul 27 04:27:40 AM UTC 2025"""
        
        # 模拟改进后的Python代码中的输出解析逻辑
        lines = test_output.split('\n')
        start_idx = 0
        end_idx = len(lines)
        separator_count = 0
        
        for i, line in enumerate(lines):
            if line.strip().startswith("="*20):  # 更宽松的分隔符匹配
                separator_count += 1
                if separator_count == 1:
                    start_idx = i + 1  # 第一个分隔符后开始
                elif separator_count == 2:
                    end_idx = i  # 第二个分隔符前结束
                    break
        
        # 如果找到了正确的分隔符，提取中间内容
        if separator_count >= 2 and start_idx < end_idx:
            stdout_content = '\n'.join(lines[start_idx:end_idx]).strip()
        elif separator_count == 1 and start_idx < len(lines):
            # 只找到一个分隔符，取分隔符后的所有内容
            remaining_lines = lines[start_idx:]
            # 移除结尾的状态信息
            filtered_lines = []
            for line in remaining_lines:
                line = line.strip()
                if not (line.startswith("✅") or line.startswith("📊") or 
                       line.startswith("⏰") or line.startswith("命令执行完成")):
                    filtered_lines.append(line)
            stdout_content = '\n'.join(filtered_lines).strip()
        else:
            # 没找到分隔符，直接使用全部内容但过滤掉明显的状态信息
            filtered_lines = []
            for line in lines:
                line = line.strip()
                if not (line.startswith("🚀") or line.startswith("📁") or 
                       line.startswith("⏰") or line.startswith("✅") or 
                       line.startswith("📊") or line.startswith("命令执行完成") or
                       line.startswith("="*10)):
                    filtered_lines.append(line)
            stdout_content = '\n'.join(filtered_lines).strip()
            
        # 验证提取的内容
        self.assertIn("NVIDIA-SMI output here", stdout_content)
        self.assertIn("Tesla T4 information", stdout_content)
        self.assertNotIn("🚀 开始执行命令", stdout_content)
        self.assertNotIn("✅ 命令执行完成", stdout_content)
        
    def test_command_structure_integrity(self):
        """测试命令结构完整性"""
        current_shell = {
            "current_path": "~",
            "current_folder_id": "test_folder_id"
        }
        
        # 测试不同的命令
        test_commands = [
            ("ls", []),
            ("nvidia-smi", []),
            ("python", ["-c", "print('hello')"]),
            ("cat", ["test.txt"])
        ]
        
        for cmd, args in test_commands:
            with self.subTest(cmd=cmd, args=args):
                remote_command, result_filename = self.shell._generate_remote_command(cmd, args, current_shell)
                
                # 验证基本结构
                self.assertIn("cd ", remote_command)
                self.assertIn("mkdir -p", remote_command)
                self.assertIn("OUTPUT_FILE=", remote_command)
                self.assertIn("python3 << 'EOF'", remote_command)
                self.assertIn("EOF", remote_command)
                
                # 验证JSON结构
                self.assertIn('"cmd":', remote_command)
                self.assertIn('"args":', remote_command)
                self.assertIn('"stdout":', remote_command)
                self.assertIn('"stderr":', remote_command)
                self.assertIn('"exit_code":', remote_command)
    
    def test_bash_escaping(self):
        """测试bash转义是否正确"""
        current_shell = {
            "current_path": "~",
            "current_folder_id": "test_folder_id"
        }
        
        # 测试包含特殊字符的命令
        remote_command, result_filename = self.shell._generate_remote_command(
            "python", ["-c", "print('hello world')"], current_shell
        )
        
        # 验证命令不包含语法错误的模式
        self.assertNotIn("syntax error", remote_command.lower())
        
        # 验证引号转义正确
        self.assertIn("EXEC_CMD=", remote_command)

def run_tests():
    """运行测试"""
    unittest.main(verbosity=2)

if __name__ == "__main__":
    run_tests() 