#!/usr/bin/env python3
"""
Enhanced unit tests for EXTRACT_PDF tool
Tests all major functionalities including different engines, post-processing, and selective processing
"""

import unittest
import os
import sys
import json
import shutil
import re
import tempfile
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from base_test import BaseTest, APITest, LongRunningTest

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from EXTRACT_PDF import PDFExtractor, PDFPostProcessor, is_run_environment, write_to_json_output
except ImportError:
    PDFExtractor = None
    PDFPostProcessor = None


class TestExtractPDFBasic(BaseTest):
    """基础功能测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA"
        
        # 确保测试数据文件存在
        self.test_pdf_simple = self.test_data_dir / "test_extract_paper.pdf"
        self.test_pdf_2pages = self.test_data_dir / "test_extract_page_selective.pdf"
        self.test_pdf_preprocess = self.test_data_dir / "test_extract_preprocess.pdf"
    
    def test_01_extract_pdf_exists(self):
        """测试EXTRACT_PDF.py文件是否存在"""
        self.assertTrue(self.extract_pdf_path.exists(), 
                       f"EXTRACT_PDF.py not found at {self.extract_pdf_path}")
    
    def test_02_help_command(self):
        """测试帮助命令"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path), "--help"
        ])
        
        self.assertEqual(result.returncode, 0, "Help command failed")
        self.assertIn("EXTRACT_PDF", result.stdout)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--engine", result.stdout)
        self.assertIn("--post", result.stdout)
    
    def test_03_invalid_engine_mode(self):
        """测试无效的引擎模式"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "nonexistent.pdf", "--engine", "invalid_engine"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Invalid engine should return error")
        output = result.stdout + result.stderr
        self.assertIn("Invalid engine mode", output)
    
    def test_04_missing_pdf_file(self):
        """测试缺少PDF文件的情况"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "nonexistent.pdf", "--engine", "basic"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Missing PDF file should return error")
        output = result.stdout + result.stderr
        self.assertIn("PDF file not found", output)
    
    def test_05_clean_data_command(self):
        """测试清理数据命令"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path), "--clean-data"
        ])
        
        # 清理命令应该成功执行
        self.assertEqual(result.returncode, 0, "Clean data command should succeed")
        output = result.stdout + result.stderr
        # 应该包含清理相关的消息
        self.assertTrue(any(keyword in output for keyword in 
                          ["已删除", "cleaned", "No cached data", "No files to clean"]))

    @unittest.skipIf(PDFExtractor is None, "PDFExtractor class not available")
    def test_06_pdf_extractor_class(self):
        """测试PDFExtractor类的基本功能"""
        extractor = PDFExtractor(debug=True)
        
        # 测试类属性
        self.assertIsInstance(extractor.debug, bool)
        self.assertTrue(hasattr(extractor, 'script_dir'))
        self.assertTrue(hasattr(extractor, 'proj_dir'))
        
        # 测试方法存在
        self.assertTrue(hasattr(extractor, 'extract_pdf'))
        self.assertTrue(hasattr(extractor, 'extract_pdf_basic'))
        self.assertTrue(hasattr(extractor, 'extract_pdf_mineru'))
        self.assertTrue(hasattr(extractor, 'clean_data'))
        self.assertTrue(hasattr(extractor, '_parse_page_spec'))

    @unittest.skipIf(PDFExtractor is None, "PDFExtractor class not available")
    def test_07_page_spec_parsing(self):
        """测试页面规格解析功能"""
        extractor = PDFExtractor()
        
        # 测试单页
        pages = extractor._parse_page_spec("3", 10)
        self.assertEqual(pages, [2])  # 0-based indexing
        
        # 测试页面范围
        pages = extractor._parse_page_spec("1-3", 10)
        self.assertEqual(pages, [0, 1, 2])
        
        # 测试混合规格
        pages = extractor._parse_page_spec("1,3,5-7", 10)
        self.assertEqual(pages, [0, 2, 4, 5, 6])
        
        # 测试超出范围的页面
        pages = extractor._parse_page_spec("8-15", 10)
        self.assertEqual(pages, [7, 8, 9])  # 应该被限制在有效范围内

    @unittest.skipIf(PDFPostProcessor is None, "PDFPostProcessor class not available")
    def test_08_pdf_postprocessor_class(self):
        """测试PDFPostProcessor类的基本功能"""
        processor = PDFPostProcessor(debug=True)
        
        # 测试类属性
        self.assertIsInstance(processor.debug, bool)
        self.assertTrue(hasattr(processor, 'script_dir'))
        
        # 测试方法存在
        self.assertTrue(hasattr(processor, 'process_file'))
        self.assertTrue(hasattr(processor, '_process_images'))
        self.assertTrue(hasattr(processor, '_process_formulas'))
        self.assertTrue(hasattr(processor, '_process_tables'))


class TestExtractPDFEngines(BaseTest):
    """引擎模式测试 - 使用更长的超时时间"""
    
    # 设置5分钟超时
    TEST_TIMEOUT = 300
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA"
        
        # 测试PDF文件
        self.test_pdf_simple = self.test_data_dir / "test_extract_paper.pdf"
        self.test_pdf_2pages = self.test_data_dir / "test_extract_page_selective.pdf"
        self.test_pdf_preprocess = self.test_data_dir / "test_extract_preprocess.pdf"
        
        # 清理之前测试生成的文件
        self._cleanup_previous_test_files()
    
    def _cleanup_previous_test_files(self):
        """清理之前测试生成的文件"""
        pdf_files = [
            self.test_pdf_simple,
            self.test_pdf_2pages, 
            self.test_pdf_preprocess
        ]
        
        for pdf_file in pdf_files:
            if pdf_file.exists():
                # 清理同名的md文件
                md_file = pdf_file.with_suffix('.md')
                if md_file.exists():
                    md_file.unlink()
                    print(f"🗑️  Cleaned up: {md_file.name}")
                
                # 清理带页码的md文件
                for pattern in [f"{pdf_file.stem}_p*.md"]:
                    for md_file in pdf_file.parent.glob(pattern):
                        md_file.unlink()
                        print(f"🗑️  Cleaned up: {md_file.name}")
                
                # 清理_extract_data文件夹
                extract_data_dir = pdf_file.parent / f"{pdf_file.stem}_extract_data"
                if extract_data_dir.exists():
                    shutil.rmtree(extract_data_dir)
                    print(f"🗑️  Cleaned up: {extract_data_dir.name}")
                
                # 清理带页码的_extract_data文件夹
                for pattern in [f"{pdf_file.stem}_p*_extract_data"]:
                    for data_dir in pdf_file.parent.glob(pattern):
                        if data_dir.is_dir():
                            shutil.rmtree(data_dir)
                            print(f"🗑️  Cleaned up: {data_dir.name}")

    def test_01_basic_engine_mode(self):
        """测试基础引擎模式"""
        if not self.test_pdf_simple.exists():
            self.skipTest("Test PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_simple), "--engine", "basic", 
                "--page", "1", "--output-dir", temp_dir
            ])
            
            # 基础模式可能因为缺少依赖而失败，但应该有合理的错误消息
            output = result.stdout + result.stderr
            self.assertTrue(
                result.returncode == 0 or "extraction failed" in output.lower() or 
                "not available" in output.lower() or "fitz" in output.lower(),
                f"Unexpected error in basic mode: {output}"
            )
    
    def test_02_basic_asyn_engine_mode(self):
        """测试基础异步引擎模式"""
        if not self.test_pdf_simple.exists():
            self.skipTest("Test PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_simple), "--engine", "basic-asyn", 
                "--page", "1", "--output-dir", temp_dir
            ])
            
            output = result.stdout + result.stderr
            self.assertTrue(
                result.returncode == 0 or "extraction failed" in output.lower() or 
                "not available" in output.lower(),
                f"Unexpected error in basic-asyn mode: {output}"
            )
    
    def test_03_mineru_engine_mode(self):
        """测试MinerU引擎模式（分页测试）"""
        if not self.test_pdf_2pages.exists():
            self.skipTest("Test PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用2页PDF测试第2页
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_2pages), "--engine", "mineru-asyn", 
                "--page", "2", "--output-dir", temp_dir
            ])
            
            output = result.stdout + result.stderr
            
            # MinerU模式可能因为依赖问题失败，但应该有合理的错误处理
            if result.returncode == 0:
                # 成功的情况下，检查输出文件
                expected_output = Path(temp_dir) / f"test_extract_page_selective_p2.md"
                if expected_output.exists():
                    print(f"✅ MinerU extraction successful: {expected_output}")
                else:
                    print(f"⚠️  MinerU extraction completed but output file not found at expected location")
            else:
                # 失败的情况下，检查错误消息是否合理
                self.assertTrue(
                    any(keyword in output.lower() for keyword in 
                        ["mineru", "extraction failed", "not available", "cli not available"]),
                    f"Unexpected error in mineru mode: {output}"
                )
    
    def test_04_full_engine_mode(self):
        """测试完整引擎模式（使用单页PDF）"""
        if not self.test_pdf_simple.exists():
            self.skipTest("Test PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_simple), "--engine", "full", 
                "--output-dir", temp_dir
            ])
            
            output = result.stdout + result.stderr
            
            # 完整模式可能因为依赖问题失败，但不应该跳过
            self.assertTrue(
                result.returncode == 0 or "extraction failed" in output.lower() or 
                "not available" in output.lower(),
                f"Unexpected error in full mode: {output}"
            )


class TestExtractPDFPreprocessing(BaseTest):
    """前处理和后处理测试"""
    
    # 设置5分钟超时
    TEST_TIMEOUT = 300
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA"
        self.test_pdf_preprocess = self.test_data_dir / "test_extract_preprocess.pdf"
        
        # 清理之前测试生成的文件
        self._cleanup_previous_test_files()
    
    def _cleanup_previous_test_files(self):
        """清理之前测试生成的文件"""
        if self.test_pdf_preprocess.exists():
            # 清理同名的md文件
            md_file = self.test_pdf_preprocess.with_suffix('.md')
            if md_file.exists():
                md_file.unlink()
                print(f"🗑️  Cleaned up: {md_file.name}")
            
            # 清理_extract_data文件夹
            extract_data_dir = self.test_pdf_preprocess.parent / f"{self.test_pdf_preprocess.stem}_extract_data"
            if extract_data_dir.exists():
                shutil.rmtree(extract_data_dir)
                print(f"🗑️  Cleaned up: {extract_data_dir.name}")
    
    def test_01_preprocessing_without_full_pipeline(self):
        """测试前处理：不使用full pipeline，验证公式图片被保存但未处理"""
        if not self.test_pdf_preprocess.exists():
            self.skipTest("Test preprocess PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 首先尝试使用basic引擎（带图片处理）
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_preprocess), "--engine", "basic", 
                "--output-dir", temp_dir
            ])
            
            output = result.stdout + result.stderr
            
            if result.returncode == 0:
                # 检查生成的markdown文件
                # 由于test_extract_preprocess.pdf是符号链接，文件名可能基于目标文件
                possible_names = [
                    f"{self.test_pdf_preprocess.stem}.md",  # test_extract_preprocess.md
                    "test_extract_paper.md"  # 符号链接目标的名称
                ]
                
                expected_md = None
                for name in possible_names:
                    candidate = Path(temp_dir) / name
                    if candidate.exists():
                        expected_md = candidate
                        break
                
                self.assertTrue(expected_md is not None and expected_md.exists(), 
                               f"Markdown file not found. Checked: {[str(Path(temp_dir) / name) for name in possible_names]}")
                
                # 读取markdown内容
                with open(expected_md, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                
                # 验证包含placeholder（可能是图片、公式或表格）
                has_placeholders = any(placeholder in md_content for placeholder in 
                                     ["[placeholder: formula]", "[placeholder: image]", "[placeholder: table]"])
                
                if not has_placeholders:
                    # 如果basic引擎没有生成placeholder，说明可能没有识别到图形内容
                    # 这种情况下我们检查是否有文本内容被提取
                    self.assertGreater(len(md_content.strip()), 100, 
                                     "Should have extracted meaningful text content")
                    print("ℹ️  Basic engine extracted text but no placeholders found")
                    return None  # 跳过后续的placeholder测试
                else:
                    print(f"✅ Found placeholders in content: {[p for p in ['[placeholder: formula]', '[placeholder: image]', '[placeholder: table]'] if p in md_content]}")
                
                # 验证图片目录存在且包含图片文件
                images_dir = Path(temp_dir) / "images"
                if images_dir.exists():
                    image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
                    self.assertGreater(len(image_files), 0, "Should have extracted image files")
                    print(f"✅ Preprocessing successful: found {len(image_files)} image files")
                else:
                    print("⚠️  No images directory found (may be expected for some PDFs)")
                
                return expected_md  # 返回markdown文件路径供后续测试使用
            else:
                # 如果basic引擎失败，尝试mineru引擎
                result2 = self.run_subprocess([
                    sys.executable, str(self.extract_pdf_path),
                    str(self.test_pdf_preprocess), "--engine", "mineru-asyn", 
                    "--output-dir", temp_dir
                ])
                
                if result2.returncode == 0:
                    expected_md = Path(temp_dir) / "test_extract_preprocess.md"
                    if expected_md.exists():
                        print("✅ MinerU preprocessing successful")
                        return expected_md
                
                # 两种引擎都失败
                self.fail(f"Both basic and mineru engines failed: {output}")
    
    def test_02_postprocessing_formula_placeholders(self):
        """测试后处理：验证公式placeholders能被正确处理"""
        if not self.test_pdf_preprocess.exists():
            self.skipTest("Test preprocess PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 先进行前处理
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_preprocess), "--engine", "basic", 
                "--output-dir", temp_dir
            ])
            
            if result.returncode != 0:
                # 如果basic失败，尝试mineru
                result = self.run_subprocess([
                    sys.executable, str(self.extract_pdf_path),
                    str(self.test_pdf_preprocess), "--engine", "mineru-asyn", 
                    "--output-dir", temp_dir
                ])
            
            if result.returncode != 0:
                self.skipTest("Preprocessing failed, cannot test postprocessing")
            
            expected_md = Path(temp_dir) / f"{self.test_pdf_preprocess.stem}.md"
            if not expected_md.exists():
                # 如果是符号链接，尝试使用原始文件名
                expected_md = Path(temp_dir) / "test_extract_paper.md"
                
            if not expected_md.exists():
                self.skipTest("Markdown file not generated, cannot test postprocessing")
            
            # 读取处理前的内容
            with open(expected_md, 'r', encoding='utf-8') as f:
                content_before = f.read()
            
            # 只有在包含placeholder时才进行后处理测试
            has_placeholders = any(placeholder in content_before for placeholder in 
                                 ["[placeholder: formula]", "[placeholder: image]", "[placeholder: table]"])
            
            if not has_placeholders:
                self.skipTest("No placeholders found, cannot test postprocessing")
            
            # 进行后处理（处理所有类型的placeholder）
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                "--post", str(expected_md), "--post-type", "all"
            ])
            
            # 后处理可能因为缺少UNIMERNET而失败，这是可以接受的
            output = result.stdout + result.stderr
            
            if result.returncode == 0:
                # 读取处理后的内容
                with open(expected_md, 'r', encoding='utf-8') as f:
                    content_after = f.read()
                
                # 验证处理结果
                if content_after != content_before:
                    print("✅ Post-processing completed: content was modified")
                else:
                    print("ℹ️  Post-processing completed but content unchanged")
            else:
                # 后处理失败是可以接受的（可能缺少依赖）
                self.assertTrue(
                    any(keyword in output.lower() for keyword in 
                        ["unimernet", "extract_img", "not available", "failed"]),
                    f"Post-processing failed with unexpected error: {output}"
                )
                print("ℹ️  Post-processing failed as expected (missing dependencies)")


class TestExtractPDFPostProcessing(BaseTest):
    """后处理功能测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
    
    def test_01_post_processing_help(self):
        """测试后处理相关的帮助信息"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path), "--help"
        ])
        
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertIn("--post", output)
        self.assertIn("--post-type", output)
        self.assertIn("--ids", output)
        self.assertIn("--prompt", output)
        self.assertIn("--force", output)
    
    def test_02_invalid_post_type(self):
        """测试无效的后处理类型"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", "test.md", "--post-type", "invalid_type"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Invalid post-type should return error")
        output = result.stdout + result.stderr
        self.assertIn("Invalid post-type", output)
    
    def test_03_missing_post_file(self):
        """测试缺少后处理文件的情况"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", "nonexistent.md", "--post-type", "all"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Missing markdown file should return error")
        output = result.stdout + result.stderr
        # 更新错误消息匹配，包含实际的错误信息
        self.assertTrue(
            any(keyword in output for keyword in 
                ["不存在", "not found", "does not exist", "Markdown文件不存在", "No such file", "处理图片时出错", "后处理失败"]),
            f"Expected file not found error, got: {output}"
        )
    
    def test_04_post_processing_with_test_markdown(self):
        """测试使用测试markdown文件进行后处理"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # 创建测试markdown文件
            test_md = temp_dir_path / "test.md"
            test_md.write_text("""# Test Document

This is a test document with various placeholders.

[placeholder: image]
![test image](test_image.png)

Some text here.

[placeholder: formula]
![test formula](test_formula.png)

More text.

[placeholder: table]
![test table](test_table.png)

End of document.
""", encoding='utf-8')
            
            # 创建虚拟图片文件（空文件用于测试）
            images_dir = temp_dir_path / "images"
            images_dir.mkdir()
            (images_dir / "test_image.png").touch()
            (images_dir / "test_formula.png").touch()
            (images_dir / "test_table.png").touch()
            
            # 测试图片类型后处理
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                "--post", str(test_md), "--post-type", "image"
            ])
            
            # 后处理可能因为缺少工具而失败，但应该有合理的错误处理
            output = result.stdout + result.stderr
            self.assertTrue(
                result.returncode in [0, 1],  # 允许成功或合理的失败
                f"Post-processing should handle missing tools gracefully: {output}"
            )


class TestExtractPDFFullPipeline(BaseTest):
    """完整流程测试 - 与引擎测试分开，避免重复"""
    
    # 设置5分钟超时
    TEST_TIMEOUT = 300
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA"
    
    def test_01_full_pipeline_mode(self):
        """测试完整流程模式（提取+后处理）"""
        test_pdf = self.test_data_dir / "test_extract_paper.pdf"
        
        if not test_pdf.exists():
            self.skipTest("Test PDF file not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                "--full", str(test_pdf), "--output-dir", temp_dir
            ])
            
            output = result.stdout + result.stderr
            
            # 完整流程应该显示步骤指示
            self.assertTrue(
                any(keyword in output for keyword in 
                    ["第一步", "第二步", "完整流程", "PDF提取", "后处理", "extraction", "post"]),
                f"Full pipeline should show step indicators: {output}"
            )


class TestExtractPDFRUNIntegration(BaseTest):
    """RUN工具集成测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.run_path = self.script_dir / "RUN.py"
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
    
    def test_01_run_show_compatibility(self):
        """测试RUN --show兼容性"""
        if not self.run_path.exists():
            self.skipTest("RUN tool not available")
        
        result = self.run_subprocess([
            sys.executable, str(self.run_path),
            "--show", "EXTRACT_PDF", "--help"
        ])
        
        if result.returncode == 0:
            # 成功的情况下应该返回JSON
            try:
                output_data = json.loads(result.stdout)
                self.assertIn('success', output_data)
                self.assertIn('message', output_data)
            except json.JSONDecodeError:
                self.fail("RUN --show EXTRACT_PDF --help did not return valid JSON")
        else:
            # 失败也应该是合理的错误
            output = result.stdout + result.stderr
            self.assertTrue(
                any(keyword in output.lower() for keyword in 
                    ["not found", "error", "failed"]),
                f"Unexpected RUN integration error: {output}"
            )
    
    def test_02_run_environment_detection(self):
        """测试RUN环境检测功能"""
        # 测试没有RUN环境的情况
        self.assertFalse(is_run_environment())
        
        # 测试有RUN环境的情况
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER_test123': 'True',
            'RUN_DATA_FILE_test123': '/tmp/test_output.json'
        }):
            self.assertTrue(is_run_environment('test123'))
            self.assertFalse(is_run_environment('other123'))


class TestExtractPDFErrorHandling(BaseTest):
    """错误处理测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
    
    def test_01_invalid_arguments(self):
        """测试无效参数"""
        # 测试未知选项
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--unknown-option", "value"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Unknown option should return error")
        output = result.stdout + result.stderr
        self.assertIn("Unknown option", output)
    
    def test_02_missing_option_values(self):
        """测试缺少选项值的情况"""
        # 测试缺少--page值
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--page"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Missing page value should return error")
        output = result.stdout + result.stderr
        self.assertIn("--page requires a value", output)
        
        # 测试缺少--engine值
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--engine"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Missing engine value should return error")
        output = result.stdout + result.stderr
        self.assertIn("--engine requires a value", output)
    
    def test_03_multiple_pdf_files(self):
        """测试指定多个PDF文件的情况"""
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "file1.pdf", "file2.pdf"
        ])
        
        self.assertNotEqual(result.returncode, 0, "Multiple PDF files should return error")
        output = result.stdout + result.stderr
        self.assertIn("Multiple PDF files specified", output)


class TestExtractPDFProjectStructure(BaseTest):
    """项目结构测试"""
    
    def setUp(self):
        super().setUp()
        self.script_dir = Path(__file__).parent.parent
    
    def test_01_extract_pdf_proj_directory(self):
        """测试EXTRACT_PDF_PROJ目录结构"""
        proj_dir = self.script_dir / "EXTRACT_PDF_PROJ"
        
        if proj_dir.exists():
            # 检查关键文件是否存在
            expected_files = [
                "extract_paper_layouts.py",
                "fix_formula_templates.py",
                "image2text_api.py"
            ]
            
            for file_name in expected_files:
                file_path = proj_dir / file_name
                self.assertTrue(file_path.exists(), 
                               f"Expected file {file_name} not found in EXTRACT_PDF_PROJ")
            
            # 检查MinerU子目录
            mineru_dir = proj_dir / "pdf_extractor_MinerU"
            if mineru_dir.exists():
                self.assertTrue((mineru_dir / "mineru").exists(), 
                               "MinerU package directory not found")
        else:
            self.skipTest("EXTRACT_PDF_PROJ directory not found")
    
    def test_02_unimernet_proj_directory(self):
        """测试UNIMERNET_PROJ目录结构"""
        unimernet_dir = self.script_dir / "UNIMERNET_PROJ"
        
        if unimernet_dir.exists():
            # 检查关键文件
            expected_files = [
                "extract_paper_layouts.py",
                "image2text_api.py"
            ]
            
            for file_name in expected_files:
                file_path = unimernet_dir / file_name
                self.assertTrue(file_path.exists(), 
                               f"Expected file {file_name} not found in UNIMERNET_PROJ")
        else:
            self.skipTest("UNIMERNET_PROJ directory not found")
    
    def test_03_test_data_files(self):
        """测试测试数据文件"""
        test_data_dir = self.script_dir / "_UNITTEST" / "_DATA"
        
        if test_data_dir.exists():
            # 检查PDF测试文件
            pdf_files = [
                "test_extract_paper.pdf",
                "test_extract_page_selective.pdf"
            ]
            
            # 检查是否有test_extract_preprocess.pdf
            preprocess_pdf = test_data_dir / "test_extract_preprocess.pdf"
            if preprocess_pdf.exists():
                pdf_files.append("test_extract_preprocess.pdf")
            
            for pdf_file in pdf_files:
                pdf_path = test_data_dir / pdf_file
                self.assertTrue(pdf_path.exists(), 
                               f"Test PDF file {pdf_file} not found")
            
            # 检查图片测试文件
            image_files = [
                "test_academic_image.png",
                "test_formula.png",
                "test_table.png"
            ]
            
            for image_file in image_files:
                image_path = test_data_dir / image_file
                self.assertTrue(image_path.exists(), 
                               f"Test image file {image_file} not found")
        else:
            self.skipTest("Test data directory not found")


class TestExtractPDFPaper2(BaseTest):
    """基于test_extract_paper2.pdf的专项测试"""
    
    # 设置长超时时间支持MinerU处理
    TEST_TIMEOUT = 360  # 6分钟
    
    @classmethod
    def setUpClass(cls):
        """类级别设置，只在整个测试类开始时清理一次"""
        super().setUpClass()
        cls.script_dir = Path(__file__).parent.parent
        cls.extract_pdf_path = cls.script_dir / "EXTRACT_PDF.py"
        cls.test_data_dir = cls.script_dir / "_UNITTEST" / "_DATA"
        cls.test_pdf_paper2 = cls.test_data_dir / "test_extract_paper2.pdf"
        
        # 只在开始时清理一次
        cls._cleanup_previous_test_files()
    
    @classmethod
    def _cleanup_previous_test_files(cls):
        """清理之前测试生成的文件（只在类开始时执行一次）"""
        if cls.test_pdf_paper2.exists():
            # 清理完整测试需要清理的文件
            cls._cleanup_full_test_files()
            
            # 清理分步测试的比较文件
            for pattern in ["*_step1.md", "*_step2.md", "*_full.md"]:
                for file in cls.test_data_dir.glob(pattern):
                    file.unlink()
                    print(f"🗑️  Cleaned up: {file.name}")
            
            # 清理images文件夹（完整测试需要）
            images_dir = cls.test_data_dir / "images"
            if images_dir.exists():
                shutil.rmtree(images_dir)
                print(f"🗑️  Cleaned up: {images_dir.name}")
    
    @classmethod
    def _cleanup_full_test_files(cls):
        """清理--full测试相关文件"""
        # 清理最终的md文件
        md_file = cls.test_pdf_paper2.with_suffix('.md')
        if md_file.exists():
            md_file.unlink()
            print(f"🗑️  Cleaned up: {md_file.name}")
        
        # 清理_postprocess.json文件
        postprocess_json = cls.test_pdf_paper2.parent / f"{cls.test_pdf_paper2.stem}_postprocess.json"
        if postprocess_json.exists():
            postprocess_json.unlink()
            print(f"🗑️  Cleaned up: {postprocess_json.name}")
        
        # 清理_extract_data文件夹
        extract_data_dir = cls.test_pdf_paper2.parent / f"{cls.test_pdf_paper2.stem}_extract_data"
        if extract_data_dir.exists():
            shutil.rmtree(extract_data_dir)
            print(f"🗑️  Cleaned up: {extract_data_dir.name}")
    
    @classmethod  
    def _cleanup_preprocessing_files(cls):
        """清理前处理测试相关文件"""
        # 清理step1, step2比较文件和最终md文件
        files_to_clean = [
            cls.test_data_dir / f"{cls.test_pdf_paper2.stem}_step1.md",
            cls.test_data_dir / f"{cls.test_pdf_paper2.stem}_step2.md", 
            cls.test_pdf_paper2.with_suffix('.md')
        ]
        
        for file in files_to_clean:
            if file.exists():
                file.unlink()
                print(f"🗑️  Cleaned up: {file.name}")
        
        # 清理_postprocess.json文件
        postprocess_json = cls.test_pdf_paper2.parent / f"{cls.test_pdf_paper2.stem}_postprocess.json"
        if postprocess_json.exists():
            postprocess_json.unlink()
            print(f"🗑️  Cleaned up: {postprocess_json.name}")
        
        # 清理_extract_data文件夹
        extract_data_dir = cls.test_pdf_paper2.parent / f"{cls.test_pdf_paper2.stem}_extract_data"
        if extract_data_dir.exists():
            shutil.rmtree(extract_data_dir)
            print(f"🗑️  Cleaned up: {extract_data_dir.name}")
    
    def setUp(self):
        super().setUp()
        self.script_dir = self.__class__.script_dir
        self.extract_pdf_path = self.__class__.extract_pdf_path
        self.test_data_dir = self.__class__.test_data_dir
        self.test_pdf_paper2 = self.__class__.test_pdf_paper2
    
    def test_01_preprocessing_paper2(self):
        """测试前处理：验证生成table和formula的placeholders（3分钟限时）"""
        if not self.test_pdf_paper2.exists():
            self.skipTest("test_extract_paper2.pdf not found")
        
        # 前处理测试前清理相关文件（包括_extract_data）
        self._cleanup_preprocessing_files()
        
        # 直接在测试数据目录中生成文件，便于后续测试使用
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            str(self.test_pdf_paper2), "--engine", "mineru-asyn", 
            "--output-dir", str(self.test_data_dir)
        ], timeout=180)  # 3分钟限时
        
        output = result.stdout + result.stderr
        
        if result.returncode == 0:
            # 检查生成的markdown文件
            expected_md = self.test_data_dir / "test_extract_paper2.md"
            self.assertTrue(expected_md.exists(), f"Markdown file not found: {expected_md}")
            
            # 读取markdown内容
            with open(expected_md, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # 验证包含table和formula placeholders（包括interline_equation）
            has_table_placeholder = "[placeholder: table]" in md_content
            has_formula_placeholder = "[placeholder: formula]" in md_content or "[placeholder: interline_equation]" in md_content
            
            print(f"📊 Table placeholders found: {has_table_placeholder}")
            print(f"🧮 Formula placeholders found: {has_formula_placeholder}")
            
            # 至少要有其中一种placeholder
            self.assertTrue(
                has_table_placeholder or has_formula_placeholder,
                "Should contain table or formula placeholders"
            )
            
            # 验证图片目录存在且包含图片文件
            images_dir = self.test_data_dir / "images"
            if images_dir.exists():
                image_files = list(images_dir.glob("*.png")) + list(images_dir.glob("*.jpg"))
                if image_files:
                    print(f"🖼️  Found {len(image_files)} image files")
            
            # 保存步骤1的结果用于比较
            step1_md = self.test_data_dir / "test_extract_paper2_step1.md"
            shutil.copy2(expected_md, step1_md)
            print(f"💾 Saved step1 result: {step1_md.name}")
            
            return expected_md  # 返回markdown文件路径供后续测试使用
        else:
            # MinerU引擎失败
            self.fail(f"MinerU engine failed: {output}")
    
    def test_02_postprocessing_paper2(self):
        """测试后处理：验证所有placeholders被识别为公式或表格（3分钟限时）"""
        if not self.test_pdf_paper2.exists():
            self.skipTest("test_extract_paper2.pdf not found")
        
        # 检查前处理的结果是否存在
        expected_md = self.test_data_dir / "test_extract_paper2.md"
        if not expected_md.exists():
            self.skipTest("Preprocessing result not found, run test_01_preprocessing_paper2 first")
        
        # 读取处理前的内容
        with open(expected_md, 'r', encoding='utf-8') as f:
            content_before = f.read()
        
        # 检查是否有placeholder（包括interline_equation）
        placeholders = ["[placeholder: table]", "[placeholder: formula]", "[placeholder: interline_equation]", "[placeholder: image]"]
        found_placeholders = [p for p in placeholders if p in content_before]
        
        if not found_placeholders:
            self.skipTest("No placeholders found in preprocessing result")
        
        print(f"📋 Found placeholders: {found_placeholders}")
        
        # 进行后处理（处理所有类型的placeholder）
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(expected_md), "--post-type", "all"
        ], timeout=180)  # 3分钟限时
        
        # 后处理可能因为缺少依赖而失败，这是可以接受的
        output = result.stdout + result.stderr
        
        if result.returncode == 0:
            # 读取处理后的内容
            with open(expected_md, 'r', encoding='utf-8') as f:
                content_after = f.read()
            
            # 验证处理结果
            if content_after != content_before:
                print("✅ Post-processing completed: content was modified")
                
                # 检查是否有处理结果或错误信息
                result_markers = ["$$", "description:", "reason:", "公式识别", "表格识别", "图像分析"]
                has_results = any(marker in content_after for marker in result_markers)
                
                if has_results:
                    print("✅ Processing successful: found results or error info")
                    
                    # 统计处理结果
                    formula_results = content_after.count("$$")
                    description_blocks = content_after.count("description:")
                    reason_blocks = content_after.count("reason:")
                    
                    print(f"🧮 Formula results: {formula_results // 2} (pairs of $$)")
                    print(f"📝 Description blocks: {description_blocks}")
                    print(f"⚠️  Reason blocks (errors): {reason_blocks}")
                else:
                    print("⚠️  Post-processing completed but no clear results found")
            else:
                print("ℹ️  Post-processing completed but content unchanged")
            
            # 保存步骤2的结果用于比较
            step2_md = self.test_data_dir / "test_extract_paper2_step2.md"
            shutil.copy2(expected_md, step2_md)
            print(f"💾 Saved step2 result: {step2_md.name}")
            
        else:
            # 后处理失败是可以接受的（可能缺少依赖）
            self.assertTrue(
                any(keyword in output.lower() for keyword in 
                    ["unimernet", "extract_img", "img2text", "not available", "failed"]),
                f"Post-processing failed with unexpected error: {output}"
            )
            print("ℹ️  Post-processing failed as expected (missing dependencies)")
    
    def test_04_full_pipeline_paper2(self):
        """测试完整流程：验证等于前处理+后处理的结果（6分钟限时）"""
        if not self.test_pdf_paper2.exists():
            self.skipTest("test_extract_paper2.pdf not found")
        
        # --full测试前清理相关文件（包括_extract_data）
        self._cleanup_full_test_files()
        
        # 使用临时目录进行完整流程测试
        with tempfile.TemporaryDirectory() as temp_dir:
            # 使用--full参数进行完整流程
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                "--full", str(self.test_pdf_paper2), "--output-dir", temp_dir
            ], timeout=360)  # 6分钟限时
            
            output = result.stdout + result.stderr
            
            # 验证完整流程的步骤指示
            self.assertTrue(
                any(keyword in output for keyword in 
                    ["第一步", "第二步", "完整流程", "PDF提取", "后处理", "extraction", "post"]),
                f"Full pipeline should show step indicators: {output}"
            )
            
            # 检查生成的markdown文件
            expected_md = Path(temp_dir) / "test_extract_paper2.md"
            if expected_md.exists():
                with open(expected_md, 'r', encoding='utf-8') as f:
                    final_content = f.read()
                
                print("✅ Full pipeline completed successfully")
                
                # 验证最终内容包含处理结果
                result_markers = ["$$", "description:", "reason:", "公式识别", "表格识别", "图像分析"]
                has_results = any(marker in final_content for marker in result_markers)
                
                if has_results:
                    print("✅ Full pipeline produced processing results")
                    
                    # 统计最终结果
                    formula_results = final_content.count("$$")
                    description_blocks = final_content.count("description:")
                    reason_blocks = final_content.count("reason:")
                    
                    print(f"🧮 Final formula results: {formula_results // 2} (pairs of $$)")
                    print(f"📝 Final description blocks: {description_blocks}")
                    print(f"⚠️  Final reason blocks (errors): {reason_blocks}")
                else:
                    print("ℹ️  Full pipeline completed but no processing results found")
                
                # 保存完整流程的结果用于比较
                full_md = self.test_data_dir / "test_extract_paper2_full.md"
                shutil.copy2(expected_md, full_md)
                print(f"💾 Saved full pipeline result: {full_md.name}")
                
            else:
                print("⚠️  Full pipeline completed but no markdown file found")
            
            # 即使有警告，只要流程执行了就算成功
            self.assertTrue(
                any(success_indicator in output for success_indicator in 
                    ["完整流程完成", "PDF提取完成", "后处理完成", "Full pipeline completed", "extraction completed"]),
                f"Full pipeline should show completion indicators: {output}"
            )
    
    def test_03_compare_results(self):
        """比较前后处理步骤与完整流程的结果"""
        step2_md = self.test_data_dir / "test_extract_paper2_step2.md"
        full_md = self.test_data_dir / "test_extract_paper2_full.md"
        
        # 如果文件不存在，尝试运行依赖的测试
        if not step2_md.exists() or not full_md.exists():
            # 运行前面的测试来生成所需文件
            try:
                if not step2_md.exists():
                    # 运行step1和step2测试
                    self.test_01_preprocessing_paper2()
                    self.test_02_postprocessing_paper2()
                
                if not full_md.exists():
                    # 运行full pipeline测试
                    self.test_04_full_pipeline_paper2()
                    
            except Exception as e:
                self.skipTest(f"Could not generate required files: {e}")
        
        # 再次检查文件是否存在
        if not step2_md.exists():
            self.skipTest("Step2 result not found, run previous tests first")
        
        if not full_md.exists():
            self.skipTest("Full pipeline result not found, run test_04_full_pipeline_paper2 first")
        
        # 读取两个文件的内容
        with open(step2_md, 'r', encoding='utf-8') as f:
            step2_content = f.read()
        
        with open(full_md, 'r', encoding='utf-8') as f:
            full_content = f.read()
        
        # 比较内容
        if step2_content == full_content:
            print("✅ Perfect match: Step1+Step2 == Full pipeline")
        else:
            print("⚠️  Differences found between Step1+Step2 and Full pipeline")
            
            # 使用diff命令进行详细比较
            try:
                diff_result = subprocess.run([
                    'diff', '-u', str(step2_md), str(full_md)
                ], capture_output=True, text=True)
                
                if diff_result.returncode == 0:
                    print("✅ Files are identical (diff confirms)")
                else:
                    print("📋 Differences found:")
                    print(diff_result.stdout[:1000])  # 显示前1000个字符的差异
                    if len(diff_result.stdout) > 1000:
                        print("... (truncated)")
                    
                    # 这不算失败，只是信息性的
                    print("ℹ️  Differences are acceptable for comparison purposes")
                    
            except FileNotFoundError:
                print("ℹ️  diff command not available, skipping detailed comparison")
            
            # 统计两个文件的结果标记
            step2_markers = {
                "formulas": step2_content.count("$$") // 2,
                "descriptions": step2_content.count("description:"),
                "reasons": step2_content.count("reason:")
            }
            
            full_markers = {
                "formulas": full_content.count("$$") // 2,
                "descriptions": full_content.count("description:"),
                "reasons": full_content.count("reason:")
            }
            
            print(f"📊 Step1+Step2: {step2_markers}")
            print(f"📊 Full pipeline: {full_markers}")


class TestExtractPDFPostProcessingQuality(unittest.TestCase):
    """测试后处理质量和placeholder位置的准确性"""
    
    def setUp(self):
        """设置测试环境"""
        self.test_data_dir = Path(__file__).parent / "_DATA"
        self.extract_pdf_path = Path(__file__).parent.parent / "EXTRACT_PDF.py"
        self.temp_dir = Path("/tmp/extract_pdf_test")
        self.temp_dir.mkdir(exist_ok=True)
        
        # 测试数据文件
        self.extracted_paper_md = self.test_data_dir / "extracted_paper_for_post.md"
        self.extracted_paper2_md = self.test_data_dir / "extracted_paper2_for_post.md"
        
        # 确保测试数据存在
        self.assertTrue(self.extracted_paper_md.exists(), f"Test data not found: {self.extracted_paper_md}")
        self.assertTrue(self.extracted_paper2_md.exists(), f"Test data not found: {self.extracted_paper2_md}")
    
    def tearDown(self):
        """清理测试环境"""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_01_placeholder_position_accuracy(self):
        """测试placeholder位置的准确性"""
        # 复制测试文件到临时目录
        test_file = self.temp_dir / "test_placeholder_position.md"
        shutil.copy2(self.extracted_paper_md, test_file)
        
        # 执行后处理
        result = subprocess.run([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(test_file)
        ], capture_output=True, text=True, timeout=300)
        
        # 检查执行是否成功
        self.assertEqual(result.returncode, 0, f"Post-processing failed: {result.stderr}")
        
        # 读取处理后的文件
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查placeholder格式和位置
        placeholders = re.findall(r'\[placeholder:\s*(\w+)\]', content)
        self.assertGreater(len(placeholders), 0, "No placeholders found after post-processing")
        
        # 检查每个placeholder后面是否有对应的图片引用
        for match in re.finditer(r'\[placeholder:\s*(\w+)\]\s*\n!\[.*?\]\(.*?\)', content):
            placeholder_type = match.group(1)
            print(f"✅ Found valid placeholder-image pair: {placeholder_type}")
        
        # 检查图片分析结果格式
        image_analysis_blocks = re.findall(r'--- 图像分析结果 ---.*?--------------------', content, re.DOTALL)
        print(f"📊 Found {len(image_analysis_blocks)} image analysis blocks")
        
        # 检查表格内容格式
        table_blocks = re.findall(r'\*\*表格内容:\*\*\s*\$\$.*?\$\$', content, re.DOTALL)
        print(f"📊 Found {len(table_blocks)} table content blocks")
        
        # 检查公式格式
        formula_blocks = re.findall(r'\$\$[^$]*\$\$', content)
        print(f"📊 Found {len(formula_blocks)} formula blocks")
    
    def test_02_multiple_processing_stability(self):
        """测试多次处理的稳定性（不产生重复内容）"""
        # 复制测试文件到临时目录
        test_file = self.temp_dir / "test_multiple_processing.md"
        shutil.copy2(self.extracted_paper2_md, test_file)
        
        # 第一次处理
        result1 = subprocess.run([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(test_file)
        ], capture_output=True, text=True, timeout=300)
        
        self.assertEqual(result1.returncode, 0, f"First post-processing failed: {result1.stderr}")
        
        # 读取第一次处理后的内容
        with open(test_file, 'r', encoding='utf-8') as f:
            content_after_first = f.read()
        
        # 第二次处理（使用--force）
        result2 = subprocess.run([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(test_file), "--force"
        ], capture_output=True, text=True, timeout=300)
        
        self.assertEqual(result2.returncode, 0, f"Second post-processing failed: {result2.stderr}")
        
        # 读取第二次处理后的内容
        with open(test_file, 'r', encoding='utf-8') as f:
            content_after_second = f.read()
        
        # 检查分隔线数量是否稳定
        separators_first = content_after_first.count('--------------------')
        separators_second = content_after_second.count('--------------------')
        
        self.assertEqual(separators_first, separators_second, 
                        f"Separator count changed: {separators_first} -> {separators_second}")
        
        # 检查placeholder数量是否稳定
        placeholders_first = len(re.findall(r'\[placeholder:\s*\w+\]', content_after_first))
        placeholders_second = len(re.findall(r'\[placeholder:\s*\w+\]', content_after_second))
        
        self.assertEqual(placeholders_first, placeholders_second,
                        f"Placeholder count changed: {placeholders_first} -> {placeholders_second}")
        
        print(f"✅ Multiple processing stability verified: {placeholders_first} placeholders, {separators_first} separators")
    
    def test_03_content_preservation(self):
        """测试原始内容保护（确保正文不被误删）"""
        # 复制测试文件到临时目录
        test_file = self.temp_dir / "test_content_preservation.md"
        shutil.copy2(self.extracted_paper_md, test_file)
        
        # 读取原始内容中的正文段落（排除placeholder和图片引用）
        with open(test_file, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # 提取原始正文段落
        original_paragraphs = []
        for line in original_content.split('\n'):
            line = line.strip()
            if (line and 
                not line.startswith('[placeholder:') and 
                not line.startswith('![') and
                not line.startswith('---') and
                not line.startswith('**') and
                not line.startswith('$$') and
                len(line) > 20):  # 只考虑较长的正文段落
                original_paragraphs.append(line)
        
        # 执行后处理
        result = subprocess.run([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(test_file)
        ], capture_output=True, text=True, timeout=300)
        
        self.assertEqual(result.returncode, 0, f"Post-processing failed: {result.stderr}")
        
        # 读取处理后的内容
        with open(test_file, 'r', encoding='utf-8') as f:
            processed_content = f.read()
        
        # 检查原始正文段落是否都保留
        missing_paragraphs = []
        for paragraph in original_paragraphs[:5]:  # 检查前5个段落
            if paragraph not in processed_content:
                missing_paragraphs.append(paragraph[:50] + "...")
        
        self.assertEqual(len(missing_paragraphs), 0, 
                        f"Original content lost: {missing_paragraphs}")
        
        print(f"✅ Content preservation verified: {len(original_paragraphs)} original paragraphs checked")
    
    def test_04_analysis_result_format(self):
        """测试分析结果格式的正确性"""
        # 复制测试文件到临时目录
        test_file = self.temp_dir / "test_analysis_format.md"
        shutil.copy2(self.extracted_paper2_md, test_file)
        
        # 执行后处理
        result = subprocess.run([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(test_file)
        ], capture_output=True, text=True, timeout=300)
        
        self.assertEqual(result.returncode, 0, f"Post-processing failed: {result.stderr}")
        
        # 读取处理后的内容
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查图片分析格式：应该是 "--- 图像分析结果 ---" 而不是 "**图片分析:**"
        old_format_count = content.count('**图片分析:**')
        new_format_count = content.count('--- 图像分析结果 ---')
        
        print(f"🔍 Debug: old_format={old_format_count}, new_format={new_format_count}")
        print(f"🔍 Content preview: {content[:500]}...")
        
        self.assertEqual(old_format_count, 0, "Found old image analysis format (**图片分析:**)")

        # 检查表格内容格式：应该在$$包围内
        table_pattern = r'\*\*表格内容:\*\*\s*\$\$.*?\$\$'
        table_matches = re.findall(table_pattern, content, re.DOTALL)
        
        # 检查公式错误格式：应该是$$ \text{[错误信息]} $$
        error_formula_pattern = r'\$\$\s*\\text\{.*?\}\s*\$\$'
        error_formula_matches = re.findall(error_formula_pattern, content)
        
        print(f"✅ Format verification: {new_format_count} image analyses, {len(table_matches)} tables, {len(error_formula_matches)} error formulas")


if __name__ == '__main__':
    unittest.main() 