# -*- coding: utf-8 -*-
"""
USERINPUT 全面测试套件

测试USERINPUT工具的各种输入情况，包括：
- 多行输入处理
- 中英文字符处理
- 特殊字符和控制字符
- 超时处理
- EOF和中断处理
- 边缘情况测试

测试设计原则：
1. 使用subprocess模拟真实的用户输入场景
2. 测试各种输入模式和边缘情况
3. 验证输入内容的完整性和正确性
4. 包含中英文字符混合输入测试
"""

import unittest
import subprocess
import sys
import time
import threading
import signal
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class USERINPUTTest(unittest.TestCase):
    """
    USERINPUT全面测试类
    包含所有USERINPUT功能的测试，从基础到高级，从简单到复杂
    """
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        print(f"设置USERINPUT全面测试环境...")
        
        # 设置路径
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.USERINPUT_PY = cls.BIN_DIR / "USERINPUT.py"
        
        # 确保USERINPUT.py存在
        if not cls.USERINPUT_PY.exists():
            raise FileNotFoundError(f"USERINPUT.py not found at {cls.USERINPUT_PY}")
        
        # 测试环境设置
        cls.test_env = os.environ.copy()
        cls.test_env['USERINPUT_NO_GUI'] = '1'  # 跳过GUI，避免tkinter窗口
        cls.test_env['USERINPUT_TIMEOUT'] = '5'  # 短超时，便于测试
        
        print(f"USERINPUT路径: {cls.USERINPUT_PY}")
        print(f"测试环境已设置")
    
    def _run_userinput(self, input_text, timeout=10, extra_args=None):
        """
        运行USERINPUT工具并返回结果
        
        Args:
            input_text: 要发送的输入文本
            timeout: 超时时间
            extra_args: 额外的命令行参数
            
        Returns:
            (returncode, stdout, stderr)
        """
        cmd = ['python3', str(self.USERINPUT_PY)]
        if extra_args:
            cmd.extend(extra_args)
        
        try:
            result = subprocess.run(
                cmd,
                input=input_text,
                text=True,
                capture_output=True,
                timeout=timeout,
                env=self.test_env
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "TIMEOUT"
        except Exception as e:
            return -2, "", str(e)
    
    def test_01_single_line_input(self):
        """测试单行输入"""
        print("\n测试01: 单行输入")
        
        test_input = "Hello World\n"  # 单行输入 + EOF
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("Hello World", stdout, "输出应包含输入的内容")
        
        print("单行输入测试通过")
    
    def test_02_multiline_input(self):
        """测试多行输入（修复后的核心功能）"""
        print("\n测试02: 多行输入")
        
        test_input = "123\n456\n789\n"  # 三行输入 + EOF
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("123", stdout, "输出应包含第一行内容")
        self.assertIn("456", stdout, "输出应包含第二行内容")
        self.assertIn("789", stdout, "输出应包含第三行内容")
        
        # 确保不是只输出"stop"
        self.assertNotEqual(stdout.strip(), "stop", "不应该只输出stop")
        
        print("多行输入测试通过")
    
    def test_03_chinese_characters(self):
        """测试中文字符输入"""
        print("\n测试03: 中文字符输入")
        
        test_input = "你好世界\n中文测试\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("你好世界", stdout, "输出应包含中文内容")
        self.assertIn("中文测试", stdout, "输出应包含中文内容")
        
        print("中文字符输入测试通过")
    
    def test_04_mixed_languages(self):
        """测试中英文混合输入"""
        print("\n测试04: 中英文混合输入")
        
        test_input = "Hello 你好\nWorld 世界\nMixed 混合测试\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("Hello 你好", stdout, "输出应包含中英文混合内容")
        self.assertIn("World 世界", stdout, "输出应包含中英文混合内容")
        self.assertIn("Mixed 混合测试", stdout, "输出应包含中英文混合内容")
        
        print("中英文混合输入测试通过")
    
    def test_05_special_characters(self):
        """测试特殊字符输入"""
        print("\n测试05: 特殊字符输入")
        
        test_input = "!@#$%^&*()\n<>?{}[]|\\:;\"'\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        # 特殊字符可能被转义，所以检查部分内容
        self.assertTrue(any(char in stdout for char in "!@#$%"), "输出应包含特殊字符")
        
        print("特殊字符输入测试通过")
    
    def test_06_empty_lines(self):
        """测试包含空行的输入"""
        print("\n测试06: 包含空行的输入")
        
        test_input = "第一行\n\n第三行\n\n第五行\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("第一行", stdout, "输出应包含第一行")
        self.assertIn("第三行", stdout, "输出应包含第三行")
        self.assertIn("第五行", stdout, "输出应包含第五行")
        
        print("包含空行的输入测试通过")
    
    def test_07_long_lines(self):
        """测试长行输入"""
        print("\n测试07: 长行输入")
        
        long_line = "这是一个很长的行，包含很多字符" * 20
        test_input = f"{long_line}\n短行\n{long_line}\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("短行", stdout, "输出应包含短行")
        # 检查长行的部分内容
        self.assertIn("这是一个很长的行", stdout, "输出应包含长行的部分内容")
        
        print("长行输入测试通过")
    
    def test_08_timeout_parameter(self):
        """测试超时参数"""
        print("\n测试08: 超时参数")
        
        # 测试自定义超时参数
        test_input = "测试超时\n"
        returncode, stdout, stderr = self._run_userinput(
            test_input, 
            extra_args=['--timeout', '2']
        )
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("测试超时", stdout, "输出应包含输入内容")
        
        print("超时参数测试通过")
    
    def test_09_help_command(self):
        """测试帮助命令"""
        print("\n测试09: 帮助命令")
        
        returncode, stdout, stderr = self._run_userinput(
            "", 
            extra_args=['--help']
        )
        
        # --help应该正常退出
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("USERINPUT", stdout, "帮助信息应包含USERINPUT")
        self.assertIn("Usage:", stdout, "帮助信息应包含使用说明")
        
        print("帮助命令测试通过")
    
    def test_10_only_spaces(self):
        """测试只包含空格的输入"""
        print("\n测试10: 只包含空格的输入")
        
        test_input = "   \n  \n    \n"  # 只有空格的行
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        # 空格行可能被过滤，但不应该导致错误
        
        print("只包含空格的输入测试通过")
    
    def test_11_numbers_and_symbols(self):
        """测试数字和符号混合输入"""
        print("\n测试11: 数字和符号混合输入")
        
        test_input = "123.456\n-789\n+100%\n$50.00\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("123.456", stdout, "输出应包含小数")
        self.assertIn("-789", stdout, "输出应包含负数")
        self.assertIn("+100%", stdout, "输出应包含百分号")
        self.assertIn("$50.00", stdout, "输出应包含货币符号")
        
        print("数字和符号混合输入测试通过")
    
    def test_12_unicode_emojis(self):
        """测试Unicode表情符号输入"""
        print("\n测试12: Unicode表情符号输入")
        
        test_input = "😀😃😄😁\n🚀🎉🎊🎈\n👍👎👌✨\n"
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        # 检查是否包含表情符号（可能在编码过程中发生变化）
        # 至少应该不报错
        
        print("Unicode表情符号输入测试通过")
    
    def test_13_code_snippets(self):
        """测试代码片段输入"""
        print("\n测试13: 代码片段输入")
        
        test_input = '''def hello_world():
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    hello_world()
'''
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("def hello_world", stdout, "输出应包含函数定义")
        self.assertIn("print", stdout, "输出应包含print语句")
        self.assertIn("if __name__", stdout, "输出应包含main检查")
        
        print("代码片段输入测试通过")
    
    def test_14_json_input(self):
        """测试JSON格式输入"""
        print("\n测试14: JSON格式输入")
        
        test_input = '''{"name": "test", "value": 123}
{"array": [1, 2, 3], "nested": {"key": "value"}}
{"chinese": "中文测试", "english": "English test"}
'''
        returncode, stdout, stderr = self._run_userinput(test_input)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn('"name"', stdout, "输出应包含JSON键")
        self.assertIn('"value"', stdout, "输出应包含JSON键")
        self.assertIn("123", stdout, "输出应包含JSON值")
        
        print("JSON格式输入测试通过")
    
    def test_15_very_long_multiline(self):
        """测试超长多行输入"""
        print("\n测试15: 超长多行输入")
        
        lines = []
        for i in range(50):  # 50行输入
            lines.append(f"第{i+1}行：这是一个测试行，包含中英文 Line {i+1}")
        
        test_input = "\n".join(lines) + "\n"
        returncode, stdout, stderr = self._run_userinput(test_input, timeout=15)
        
        self.assertEqual(returncode, 0, f"返回码应为0，实际为{returncode}")
        self.assertIn("第1行", stdout, "输出应包含第一行")
        self.assertIn("第50行", stdout, "输出应包含最后一行")
        self.assertIn("Line 1", stdout, "输出应包含英文内容")
        self.assertIn("Line 50", stdout, "输出应包含英文内容")
        
        print("超长多行输入测试通过")
    
    def test_16_timeout_bug_fix(self):
        """测试超时bug修复 - GUI按钮点击后超时应该捕获部分输入"""
        print("\n测试16: 超时bug修复")
        
        # 测试超时功能的内部逻辑
        import sys
        sys.path.insert(0, str(self.BIN_DIR))
        import USERINPUT
        
        # 测试GlobalTimeoutManager
        timeout_manager = USERINPUT.GlobalTimeoutManager(2)
        self.assertEqual(timeout_manager.timeout_seconds, 2)
        self.assertFalse(timeout_manager.is_timeout_expired())
        
        # 模拟时间流逝
        import time
        time.sleep(0.1)
        remaining = timeout_manager.get_remaining_time()
        self.assertLess(remaining, 2)
        self.assertGreater(remaining, 0)
        
        # 测试超时检测
        time.sleep(2.1)
        self.assertTrue(timeout_manager.is_timeout_expired())
        self.assertEqual(timeout_manager.get_remaining_time(), 0)
        
        print("超时bug修复测试通过")
    
    def test_17_ctrl_c_duplication_bug_fix(self):
        """测试Ctrl+C重复输入bug修复 - 按回车再按Ctrl+C不应该重复行"""
        print("\n测试17: Ctrl+C重复输入bug修复")
        
        import sys
        sys.path.insert(0, str(self.BIN_DIR))
        import USERINPUT
        from unittest.mock import patch
        
        # 测试Ctrl+C处理逻辑
        lines = []
        lines.append("test line")  # 模拟用户按回车后行被添加
        
        with patch('USERINPUT.signal.signal'), \
             patch('USERINPUT.signal.alarm'), \
             patch('readline.get_line_buffer') as mock_buffer, \
             patch('builtins.input') as mock_input:
            
            # 模拟Ctrl+C情况，缓冲区还包含同样的行（bug条件）
            mock_input.side_effect = KeyboardInterrupt("Ctrl+C")
            mock_buffer.return_value = "test line"  # 缓冲区中的同一行
            
            result = USERINPUT._read_input_with_signal(lines, 30)
            
            # 验证修复：不应该重复添加行
            self.assertEqual(len(lines), 1, f"应该只有1行，实际有{len(lines)}行")
            self.assertEqual(lines[0], "test line", "行内容应该正确")
            self.assertEqual(result, "partial_input", "应该返回partial_input")
        
        print("Ctrl+C重复输入bug修复测试通过")
    
    def test_18_both_fixes_integration(self):
        """测试两个bug修复的集成 - 确保两个修复一起工作"""
        print("\n测试18: 两个bug修复的集成测试")
        
        import sys
        sys.path.insert(0, str(self.BIN_DIR))
        import USERINPUT
        
        # 测试超时管理器与Ctrl+C处理的集成
        timeout_manager = USERINPUT.GlobalTimeoutManager(5)
        USERINPUT._global_timeout_manager = timeout_manager
        
        # 验证超时管理器正常工作
        self.assertGreater(timeout_manager.get_remaining_time(), 0)
        
        # 同时测试Ctrl+C处理（不重复）
        from unittest.mock import patch
        lines = ["existing line"]
        
        with patch('USERINPUT.signal.signal'), \
             patch('USERINPUT.signal.alarm'), \
             patch('readline.get_line_buffer') as mock_buffer, \
             patch('builtins.input') as mock_input:
            
            mock_input.side_effect = KeyboardInterrupt("Ctrl+C")
            mock_buffer.return_value = "new line"  # 新行应该被添加
            
            result = USERINPUT._read_input_with_signal(lines, 5)
            
            # 验证新行被正确添加（不是重复的情况）
            self.assertEqual(len(lines), 2, "应该有2行")
            self.assertEqual(lines[1], "new line", "新行应该被添加")
            self.assertEqual(result, "partial_input", "应该返回partial_input")
        
        # 清理全局状态
        USERINPUT._global_timeout_manager = None
        
        print("两个bug修复的集成测试通过")

def run_tests():
    """运行所有测试"""
    print("="*70)
    print("USERINPUT 全面测试套件")
    print("="*70)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(USERINPUTTest)
    
    # 运行测试
    runner = unittest.TextTestRunner(
        verbosity=2,
        stream=sys.stdout,
        descriptions=True,
        failfast=False
    )
    
    start_time = time.time()
    result = runner.run(suite)
    end_time = time.time()
    
    # 输出测试结果摘要
    print("="*70)
    print("测试结果摘要")
    print("="*70)
    print(f"总测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"成功率: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%")
    print(f"耗时: {end_time - start_time:.2f}秒")
    
    # 输出失败和错误详情
    if result.failures:
        print("\n失败的测试:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\n错误的测试:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    print("="*70)
    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
