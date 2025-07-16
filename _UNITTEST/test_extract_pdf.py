#!/usr/bin/env python3
"""
Unit tests for EXTRACT_PDF tool
"""

import unittest
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import EXTRACT_PDF
except ImportError:
    EXTRACT_PDF = None

class TestExtractPDF(unittest.TestCase):
    """Test cases for EXTRACT_PDF tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a dummy PDF file for testing
        self.test_pdf_file = self.test_dir / "test.pdf"
        # Create a minimal PDF content (just for testing file existence)
        with open(self.test_pdf_file, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(EXTRACT_PDF.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_OUTPUT_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(EXTRACT_PDF.is_run_environment())
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = EXTRACT_PDF.create_json_output(
            success=True,
            message="Extraction successful",
            output_file="test_output.md",
            extracted_text="Sample extracted text"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('output_file', result)
        self.assertIn('extracted_text', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    def test_file_validation(self):
        """Test PDF file validation"""
        # Test valid PDF file
        self.assertTrue(EXTRACT_PDF.validate_pdf_file(str(self.test_pdf_file)))
        
        # Test non-existent file
        self.assertFalse(EXTRACT_PDF.validate_pdf_file("nonexistent.pdf"))
        
        # Test non-PDF file
        text_file = self.test_dir / "test.txt"
        with open(text_file, 'w') as f:
            f.write("This is not a PDF")
        self.assertFalse(EXTRACT_PDF.validate_pdf_file(str(text_file)))
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test page argument
        args = EXTRACT_PDF.parse_arguments(['--page', '1', 'test.pdf'])
        self.assertEqual(args.page, 1)
        self.assertEqual(args.pdf_file, 'test.pdf')
        
        # Test output argument
        args = EXTRACT_PDF.parse_arguments(['--output', 'output.md', 'test.pdf'])
        self.assertEqual(args.output, 'output.md')
        
        # Test image API flags
        args = EXTRACT_PDF.parse_arguments(['--with-image-api', 'test.pdf'])
        self.assertTrue(args.with_image_api)
        
        args = EXTRACT_PDF.parse_arguments(['--no-image-api', 'test.pdf'])
        self.assertFalse(args.with_image_api)
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    @patch('subprocess.run')
    def test_mineru_extraction_success(self, mock_run):
        """Test successful MinerU extraction"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Extraction completed successfully",
            stderr=""
        )
        
        result = EXTRACT_PDF.extract_with_mineru(
            str(self.test_pdf_file),
            output_dir=str(self.test_dir),
            page=1,
            with_image_api=False
        )
        
        self.assertTrue(result['success'])
        mock_run.assert_called()
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    @patch('subprocess.run')
    def test_mineru_extraction_failure(self, mock_run):
        """Test failed MinerU extraction"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: MinerU extraction failed"
        )
        
        result = EXTRACT_PDF.extract_with_mineru(
            str(self.test_pdf_file),
            output_dir=str(self.test_dir),
            page=1,
            with_image_api=False
        )
        
        self.assertFalse(result['success'])
        self.assertIn('failed', result['message'].lower())
    
    @unittest.skipIf(EXTRACT_PDF is None, "EXTRACT_PDF module not available")
    @patch('tkinter.filedialog.askopenfilename')
    def test_gui_file_selection(self, mock_filedialog):
        """Test GUI file selection when no arguments provided"""
        mock_filedialog.return_value = str(self.test_pdf_file)
        
        with patch('sys.argv', ['EXTRACT_PDF.py']):
            with patch.object(EXTRACT_PDF, 'extract_with_mineru') as mock_extract:
                mock_extract.return_value = {
                    'success': True,
                    'message': 'Test extraction',
                    'output_file': 'test_output.md',
                    'extracted_text': 'Sample text'
                }
                
                try:
                    EXTRACT_PDF.main()
                except SystemExit:
                    pass
                
                mock_filedialog.assert_called_once()
                mock_extract.assert_called_once()

class TestExtractPDFIntegration(unittest.TestCase):
    """Integration tests for EXTRACT_PDF tool"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        
        # Create test PDF file
        self.test_pdf_file = self.test_dir / "integration_test.pdf"
        with open(self.test_pdf_file, 'wb') as f:
            f.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n')
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_command_line_execution(self):
        """Test command line execution of EXTRACT_PDF"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'EXTRACT_PDF.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Extract text from PDF', result.stdout)
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'EXTRACT_PDF'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show EXTRACT_PDF did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 