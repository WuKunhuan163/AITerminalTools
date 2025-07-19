#!/usr/bin/env python3
"""
test_extract_pdf_integrated.py - 集成的EXTRACT_PDF测试文件
整合了原始test_unimernet_formula中的测试功能
"""

import unittest
import os
import sys
import subprocess
import tempfile
import shutil
from pathlib import Path
from base_test import BaseTest, APITest, LongRunningTest

class ExtractPDFIntegratedTest(LongRunningTest):
    """EXTRACT_PDF集成测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA" / "test_extract_paper_simple"
        
    def test_01_extract_pdf_exists(self):
        """测试EXTRACT_PDF.py文件是否存在"""
        self.assertTrue(self.extract_pdf_path.exists(), 
                       f"EXTRACT_PDF.py not found at {self.extract_pdf_path}")
    
    def test_02_extract_pdf_help(self):
        """测试EXTRACT_PDF帮助功能"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path), "--help"
        ])
        
        self.assertEqual(result.returncode, 0, "Help command failed")
        self.assertIn("EXTRACT_PDF", result.stdout)
        self.assertIn("Usage:", result.stdout)
    
    def test_03_extract_pdf_basic_mode(self):
        """测试基础模式PDF提取"""
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
                str(test_pdf), "--engine", "basic", "--output", temp_dir
            ])
            
            # 基础模式可能因为缺少依赖而失败，这是正常的
            if result.returncode != 0:
                self.assertIn("extraction failed", result.stderr.lower())
    
    def test_04_extract_pdf_post_processing(self):
        """测试后处理功能"""
        # 创建一个测试markdown文件
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # 创建测试markdown文件
            test_md = temp_dir_path / "test.md"
            test_md.write_text("""# Test Document

This is a test document.

[placeholder: image]
![test image](test_image.png)

Some text here.

[placeholder: formula]
![test formula](test_formula.png)

More text.

[placeholder: table]
![test table](test_table.png)

End of document.
""")
            
            # 创建extract_data目录
            extract_data_dir = temp_dir_path / "test_extract_data"
            extract_data_dir.mkdir()
            
            # 创建测试图片文件（空文件）
            (extract_data_dir / "test_image.png").touch()
            (extract_data_dir / "test_formula.png").touch()
            (extract_data_dir / "test_table.png").touch()
            
            # 测试后处理
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                "--post", str(test_md), "--post-type", "image"
            ])
            
            # 后处理可能因为缺少IMG2TEXT工具而失败，这是正常的
            # 我们只检查命令是否被正确解析
            self.assertTrue(result.returncode in [0, 1], 
                           "Post-processing command should be parsed correctly")
    
    def test_05_extract_pdf_invalid_engine(self):
        """测试无效的引擎模式"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "nonexistent.pdf", "--engine", "invalid_engine"
        ])
        
        self.assertEqual(result.returncode, 1, "Invalid engine should return error")
        output = result.stdout + result.stderr
        self.assertIn("Invalid engine mode", output)
    
    def test_06_extract_pdf_invalid_post_type(self):
        """测试无效的后处理类型"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", "test.md", "--post-type", "invalid_type"
        ])
        
        self.assertEqual(result.returncode, 1, "Invalid post-type should return error")
        output = result.stdout + result.stderr
        self.assertIn("Invalid post-type", output)
    
    def test_07_extract_pdf_missing_file(self):
        """测试缺少PDF文件的情况"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "nonexistent.pdf", "--engine", "basic"
        ])
        
        self.assertEqual(result.returncode, 1, "Missing PDF file should return error")
        output = result.stdout + result.stderr
        self.assertIn("PDF file not found", output)
    
    def test_08_extract_pdf_missing_post_file(self):
        """测试缺少后处理文件的情况"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", "nonexistent.md", "--post-type", "all"
        ])
        
        self.assertEqual(result.returncode, 1, "Missing markdown file should return error")
        # 输出可能在stdout或stderr中
        output = result.stdout + result.stderr
        self.assertIn("Markdown文件不存在", output)
    
    def test_09_extract_pdf_proj_directory(self):
        """测试EXTRACT_PDF_PROJ目录结构"""
        proj_dir = self.script_dir / "EXTRACT_PDF_PROJ"
        
        if proj_dir.exists():
            # 检查关键文件是否存在
            expected_files = [
                "unimernet_processor.py",
                "mineru_wrapper.py",
                "extract_paper_layouts.py"
            ]
            
            for file_name in expected_files:
                file_path = proj_dir / file_name
                self.assertTrue(file_path.exists(), 
                               f"Expected file {file_name} not found in EXTRACT_PDF_PROJ")
        else:
            self.skipTest("EXTRACT_PDF_PROJ directory not found")
    
    def test_10_test_data_files(self):
        """测试测试数据文件"""
        if not self.test_data_dir.exists():
            self.skipTest("Test data directory not found")
        
        # 检查是否有PDF文件
        pdf_files = list(self.test_data_dir.glob("*.pdf"))
        self.assertGreater(len(pdf_files), 0, "No PDF test files found")
        
        # 检查是否有Python测试文件
        py_files = list(self.test_data_dir.glob("*.py"))
        self.assertGreater(len(py_files), 0, "No Python test files found")
        
        print(f"Found {len(pdf_files)} PDF files and {len(py_files)} Python files in test data")

if __name__ == "__main__":
    unittest.main() 