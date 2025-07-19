#!/usr/bin/env python3
"""
Unit tests for UNIMERNET tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

UNIMERNET_PATH = str(Path(__file__).parent.parent / 'UNIMERNET')
UNIMERNET_PY = str(Path(__file__).parent.parent / 'UNIMERNET.py')
EXTRACT_PDF_PY = str(Path(__file__).parent.parent / 'EXTRACT_PDF.py')
TEST_DATA_DIR = Path(__file__).parent / '_DATA'

class TestUnimernet(unittest.TestCase):
    """Test cases for UNIMERNET tool"""

    def setUp(self):
        """Set up test environment"""
        self.test_formula = TEST_DATA_DIR / 'test_formula.png'
        self.test_table = TEST_DATA_DIR / 'test_table.png'
        self.test_academic_image = TEST_DATA_DIR / 'test_academic_image.png'

    def test_check_availability(self):
        """Test UNIMERNET availability check"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--check'
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        self.assertIn('✅ UnimerNet is available and ready', result.stdout)
        self.assertEqual(result.returncode, 0)

    def test_formula_recognition_with_extract_pdf(self):
        """Test formula recognition using EXTRACT_PDF with test_formula.png"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # Create a temporary markdown file with formula placeholder
        test_hash = "test_formula_hash"
        temp_md_content = f"""# Test Formula Recognition

This is a test document with a formula placeholder.

[placeholder: formula]
![](images/{test_hash}.jpg)

End of document.
"""
        
        # Create temporary directory structure
        import tempfile
        import shutil
        from datetime import datetime
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Create markdown file
            temp_md = temp_dir / "test_formula.md"
            temp_md.write_text(temp_md_content)
            
            # Create a dummy PDF file
            temp_pdf = temp_dir / "test_formula.pdf"
            temp_pdf.write_bytes(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
            
            # Create extract_data directory structure to simulate post-processing
            extract_data_dir = temp_dir / "test_formula_extract_data"
            extract_data_dir.mkdir()
            extract_images_dir = extract_data_dir / "images"
            extract_images_dir.mkdir()
            
            # Copy formula image with a hash name
            shutil.copy(self.test_formula, extract_images_dir / f"{test_hash}.jpg")
            
            # Create postprocess JSON file with correct format
            postprocess_data = {
                "pdf_file": "test_formula.pdf",
                "created_at": datetime.now().isoformat(),
                "total_items": 1,
                "counts": {
                    "images": 0,
                    "formulas": 1,
                    "tables": 0
                },
                "items": [{
                    "type": "formula",
                    "page": 1,
                    "block_index": 0,
                    "image_path": f"{test_hash}.jpg",
                    "bbox": [],
                    "processed": False,
                    "processor": None,
                    "id": test_hash
                }]
            }
            postprocess_json = temp_dir / "test_formula_postprocess.json"
            postprocess_json.write_text(json.dumps(postprocess_data, indent=2))
            
            # Debug: Print directory structure
            print(f"Temp dir: {temp_dir}")
            print(f"Files in temp dir: {list(temp_dir.iterdir())}")
            print(f"Extract data dir exists: {extract_data_dir.exists()}")
            print(f"Extract images dir exists: {extract_images_dir.exists()}")
            print(f"Image file exists: {(extract_images_dir / f'{test_hash}.jpg').exists()}")
            print(f"PDF file exists: {temp_pdf.exists()}")
            print(f"Postprocess JSON exists: {postprocess_json.exists()}")
            
            # Test all possible image locations that _find_image_file checks
            possible_locations = [
                temp_dir / f"{test_hash}.jpg",
                temp_dir / "images" / f"{test_hash}.jpg", 
                temp_dir / f"test_formula_extract_data" / "images" / f"{test_hash}.jpg",
                Path(__file__).parent.parent / "EXTRACT_PDF_PROJ" / "pdf_extractor_data" / "images" / f"{test_hash}.jpg"
            ]
            print("Checking possible image locations:")
            for i, loc in enumerate(possible_locations):
                print(f"  {i+1}. {loc} - exists: {loc.exists()}")
            
            # Also copy the image to the direct location that might be expected
            shutil.copy(self.test_formula, temp_dir / f"{test_hash}.jpg")
            
            # Test EXTRACT_PDF post-processing with specific ID
            result = subprocess.run([
                sys.executable, EXTRACT_PDF_PY, 
                "--post", str(temp_md),
                "--ids", test_hash,
                "--post-type", "formula"
            ], capture_output=True, text=True, timeout=300, cwd=temp_dir)  # 5 minutes timeout
            
            print(f"EXTRACT_PDF output:\n{result.stdout}")
            print(f"EXTRACT_PDF stderr:\n{result.stderr}")
            
            # Check if the process completed successfully
            self.assertEqual(result.returncode, 0, f"EXTRACT_PDF failed with error: {result.stderr}")
            
            # Check for successful processing
            self.assertIn("处理", result.stdout, "Should show processing activity")
            
            # For RUN environment, check for structured results
            if "RUN_IDENTIFIER" in os.environ:
                # Should have JSON output with recognition results
                self.assertIn("success", result.stdout.lower())
            
            # Check that formula recognition completed successfully
            output_text = result.stdout + result.stderr
            
            # Verify that UnimerNet recognition was successful
            has_recognition_success = "Recognition successful:" in output_text
            has_unimernet_success = "UnimerNet公式识别成功" in output_text
            has_placeholder_replacement = "替换placeholder:" in output_text
            
            # Check that the formula recognition workflow completed successfully
            self.assertTrue(has_recognition_success, 
                          f"UnimerNet should show 'Recognition successful:' in output. Output: {output_text}")
            self.assertTrue(has_unimernet_success, 
                          f"Should show '✅ UnimerNet公式识别成功' in output. Output: {output_text}")
            self.assertTrue(has_placeholder_replacement, 
                          f"Should show placeholder replacement in output. Output: {output_text}")
            
            # Report the model weight initialization warning if present
            has_weight_warning = "Some weights of UnimernetModel were not initialized from the model checkpoint" in output_text
            if has_weight_warning:
                print(f"⚠️  Model weight initialization warning detected - this needs to be fixed")
            else:
                print(f"✅ No model weight initialization warnings")
            
            print(f"✅ Formula recognition workflow test passed - UnimerNet integration working")
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir)

    def test_formula_recognition(self):
        """Test formula recognition with test_formula.png"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # 检查是否有识别结果
        self.assertIn('Recognition successful', result.stdout)

    def test_table_recognition(self):
        """Test table recognition with test_table.png"""
        if not self.test_table.exists():
            self.skipTest(f"Test image {self.test_table} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_table)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # 检查是否有识别结果
        self.assertIn('Recognition successful', result.stdout)

    def test_academic_image_recognition(self):
        """Test academic image recognition with test_academic_image.png"""
        if not self.test_academic_image.exists():
            self.skipTest(f"Test image {self.test_academic_image} not found")
        
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_academic_image)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 检查是否成功执行
        self.assertEqual(result.returncode, 0)
        # 检查是否有识别结果
        self.assertIn('Recognition successful', result.stdout)

    def test_run_show_json_output(self):
        """Test RUN --show compatibility (JSON output)"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        with patch.dict(os.environ, {
            "RUN_IDENTIFIER": "test_run", "RUN_DATA_FILE": "/tmp/test_unimernet_run.json"
        }):
            result = subprocess.run([
                sys.executable, UNIMERNET_PY, str(self.test_formula)
            ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
            
            # 检查JSON文件内容
            if os.path.exists('/tmp/test_unimernet_run.json'):
                with open('/tmp/test_unimernet_run.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.assertTrue(data['success'])
                self.assertIn('Recognition successful', data['output'])

    def test_image_path_not_exist(self):
        """Test error when image path does not exist"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, 'not_exist.png'
        ], capture_output=True, text=True, timeout=20)
        self.assertIn('图片路径不存在', result.stdout)

    def test_help_output(self):
        """Test help output"""
        result = subprocess.run([
            sys.executable, UNIMERNET_PY, '--help'
        ], capture_output=True, text=True, timeout=10)
        self.assertIn('UNIMERNET - UnimerNet Formula and Table Recognition Tool', result.stdout)

    def test_cache_functionality(self):
        """Test cache functionality with repeated calls"""
        if not self.test_formula.exists():
            self.skipTest(f"Test image {self.test_formula} not found")
        
        # 第一次调用
        result1 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 第二次调用应该从缓存获取
        result2 = subprocess.run([
            sys.executable, UNIMERNET_PY, str(self.test_formula)
        ], capture_output=True, text=True, timeout=180)  # 3 minutes timeout
        
        # 两次调用都应该成功
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)
        
        # 第二次调用应该显示从缓存获取
        self.assertIn('From cache: True', result2.stdout)

if __name__ == '__main__':
    unittest.main() 