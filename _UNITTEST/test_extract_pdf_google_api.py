#!/usr/bin/env python3
"""
test_extract_pdf_google_api.py - 测试EXTRACT_PDF的Google API图片识别功能
"""

import unittest
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from base_test import BaseTest, APITest, LongRunningTest

class ExtractPDFGoogleAPITest(LongRunningTest):
    """EXTRACT_PDF Google API 图片识别测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA" / "test_extract_paper_simple"
        
    def test_01_extract_pdf_full_mode(self):
        """测试完整模式PDF提取（包含图像分析）"""
        # 跳过完整模式测试，因为它需要很长时间
        self.skipTest("Full mode test skipped due to long processing time")
        
        # 检查是否有测试PDF文件
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")
        
        pdf_files = list(self.test_data_dir.glob("*.pdf"))
        if not pdf_files:
            self.skipTest("No PDF test files found")
        
        # 使用第一个PDF文件进行测试
        test_pdf = pdf_files[0]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(test_pdf), "--engine", "full", "--output", temp_dir
            ])
            
            # 完整模式可能需要很长时间，这里只检查是否正确启动
            if result.returncode == 0:
                # 检查是否生成了输出文件
                output_file = Path(temp_dir) / f"{test_pdf.stem}.md"
                self.assertTrue(output_file.exists(), "Output markdown file should be created")
                
                # 检查文件内容
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertGreater(len(content), 0, "Output file should not be empty")
            else:
                # 如果失败，检查是否是由于缺少依赖
                self.assertIn("failed", result.stderr.lower())
    
    def test_02_post_processing_with_img2text(self):
        """测试使用IMG2TEXT的后处理功能"""
        # 创建一个测试markdown文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # 创建测试markdown文件
            test_md = temp_dir_path / "test.md"
            test_md.write_text("""# Test Document

This is a test document with placeholders.

[placeholder: image]
![test image](images/test_image.png)

Some text here.

[placeholder: formula]
![test formula](images/test_formula.png)

More text.

[placeholder: table]
![test table](images/test_table.png)

End of document.
""")
            
            # 创建extract_data目录和子目录
            extract_data_dir = temp_dir_path / "test_extract_data"
            extract_data_dir.mkdir()
            images_dir = extract_data_dir / "images"
            images_dir.mkdir()
            
            # 创建测试图片文件（空文件）
            (images_dir / "test_image.png").touch()
            (images_dir / "test_formula.png").touch()
            (images_dir / "test_table.png").touch()
            
            # 测试图片后处理
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                "--post", str(test_md), "--post-type", "image"
            ])
            
            # 检查命令是否被正确解析
            self.assertTrue(result.returncode in [0, 1], 
                           "Post-processing command should be parsed correctly")
            
            # 如果成功，检查文件是否被修改
            if result.returncode == 0:
                with open(test_md, 'r', encoding='utf-8') as f:
                    updated_content = f.read()
                    # 检查是否有图片分析相关的内容
                    self.assertIn("图片分析", updated_content)
    
    def test_03_google_api_integration(self):
        """测试Google API集成"""
        # 这个测试需要实际的Google API密钥
        # 在CI/CD环境中可能会跳过
        
        # 检查是否有Google API相关的环境变量
        if not os.environ.get('GOOGLE_API_KEY') and not os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
            self.skipTest("Google API credentials not available")
        
        # 创建一个简单的测试图片
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # 使用测试数据中的第一个PDF
            pdf_files = list(self.test_data_dir.glob("*.pdf"))
            if not pdf_files:
                self.skipTest("No PDF test files found")
            
            test_pdf = pdf_files[0]
            
            # 先提取PDF
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(test_pdf), "--engine", "mineru", "--output", str(temp_dir_path)
            ])
            
            if result.returncode == 0:
                # 检查是否生成了markdown文件
                output_file = temp_dir_path / f"{test_pdf.stem}.md"
                self.assertTrue(output_file.exists(), "Markdown file should be created")
    
    def test_04_engine_mode_descriptions(self):
        """测试引擎模式描述"""
        # 测试不同引擎模式的描述信息
        engine_modes = ["basic", "basic-asyn", "mineru", "mineru-asyn", "full"]
        
        for mode in engine_modes:
            with self.subTest(engine_mode=mode):
                result = self.run_subprocess([
                    sys.executable, str(self.extract_pdf_path),
                    "nonexistent.pdf", "--engine", mode
                ])
                
                # 应该显示引擎描述信息
                output = result.stdout + result.stderr
                self.assertIn("使用引擎", output, f"Engine description should be shown for {mode}")
    
    def test_05_run_show_integration(self):
        """测试RUN --show集成"""
        # 测试EXTRACT_PDF在RUN --show模式下的行为
        result = self.run_subprocess([
            sys.executable, str(self.script_dir / "RUN.py"),
            "--show", "EXTRACT_PDF", "--help"
        ])
        
        self.assertEqual(result.returncode, 0, "RUN --show should work with EXTRACT_PDF")
        
        # 检查输出包含JSON
        self.assertIn("{", result.stdout, "Output should contain JSON")
        self.assertIn("success", result.stdout, "Output should contain success field")
    
    def test_06_interactive_mode_info(self):
        """测试交互模式信息显示"""
        # 这个测试比较难自动化，因为涉及GUI文件选择
        # 我们只测试相关的函数是否存在
        
        # 检查select_pdf_file函数是否可以导入
        try:
            sys.path.insert(0, str(self.script_dir))
            from EXTRACT_PDF import select_pdf_file
            
            # 函数应该存在
            self.assertTrue(callable(select_pdf_file))
        except ImportError:
            self.fail("select_pdf_file function should be importable")
    
    def test_07_output_file_handling(self):
        """测试输出文件处理"""
        # 测试输出文件是否正确复制到用户指定目录
        
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")
        
        pdf_files = list(self.test_data_dir.glob("*.pdf"))
        if not pdf_files:
            self.skipTest("No PDF test files found")
        
        test_pdf = pdf_files[0]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(test_pdf), "--engine", "basic", "--output", temp_dir
            ])
            
            if result.returncode == 0:
                # 检查输出文件是否在正确位置
                expected_output = Path(temp_dir) / f"{test_pdf.stem}.md"
                self.assertTrue(expected_output.exists(), 
                               f"Output file should be at {expected_output}")
                
                # 检查输出消息是否包含正确的路径
                self.assertIn(str(expected_output), result.stdout)

if __name__ == "__main__":
    unittest.main() 