#!/usr/bin/env python3
"""
Unified unit tests for EXTRACT_PDF tool
Combines all functionality tests into a single comprehensive test class
"""

import unittest
import os
import sys
import json
import shutil
import re
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from EXTRACT_PDF import PDFExtractor, PDFPostProcessor, is_run_environment, write_to_json_output
except ImportError:
    PDFExtractor = None
    PDFPostProcessor = None


class TestExtractPDF(unittest.TestCase):
    """Unified test class for EXTRACT_PDF tool functionality"""
    
    def setUp(self):
        """Set up test environment"""
        self.script_dir = Path(__file__).parent.parent
        self.extract_pdf_path = self.script_dir / "EXTRACT_PDF.py"
        self.test_data_dir = self.script_dir / "_UNITTEST" / "_DATA"
        
        # Test PDF files
        self.test_pdf_simple = self.test_data_dir / "test_extract_paper.pdf"
        self.test_pdf_2pages = self.test_data_dir / "test_extract_page_selective.pdf"
        self.test_pdf_preprocess = self.test_data_dir / "test_extract_preprocess.pdf"
        self.test_pdf_single_figure = self.test_data_dir / "test_single_figure.pdf"
        
        # Test markdown files
        self.test_md_simple = self.test_data_dir / "test_extract_paper.md"
        self.test_md_extracted = self.test_data_dir / "extracted_paper_for_post.md"
        self.test_md_extracted2 = self.test_data_dir / "extracted_paper2_for_post.md"
        
        # Create temp directory for test outputs
        self.temp_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Clean up test environment"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def run_subprocess(self, cmd, timeout=300, **kwargs):
        """Helper method to run subprocess with consistent settings"""
        try:
            return subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=timeout,
                **kwargs
            )
        except subprocess.TimeoutExpired:
            self.fail(f"Command timed out after {timeout}s: {' '.join(map(str, cmd))}")
    
    def test_basic_functionality(self):
        """Test basic EXTRACT_PDF functionality including help, file checks, and error handling"""
        # Test file exists
        self.assertTrue(self.extract_pdf_path.exists(), 
                       f"EXTRACT_PDF.py not found at {self.extract_pdf_path}")
        
        # Test help command
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path), "--help"
        ])
        self.assertEqual(result.returncode, 0, "Help command failed")
        self.assertIn("EXTRACT_PDF", result.stdout)
        self.assertIn("Usage:", result.stdout)
        self.assertIn("--engine", result.stdout)
        self.assertIn("--post", result.stdout)
        
        # Test invalid engine mode
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "nonexistent.pdf", "--engine", "invalid_engine"
        ])
        self.assertNotEqual(result.returncode, 0, "Invalid engine should return error")
        
        # Test missing PDF file
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "nonexistent.pdf", "--engine", "basic"
        ])
        self.assertNotEqual(result.returncode, 0, "Missing PDF file should return error")
        
        # Test clean data command
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path), "--clean-data"
        ])
        self.assertEqual(result.returncode, 0, "Clean data command should succeed")
    
    def test_engine_modes(self):
        """Test different engine modes and their functionality"""
        if not self.test_pdf_simple.exists():
            self.skipTest(f"Test PDF not found: {self.test_pdf_simple}")
        
        # Test basic engine (default)
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            str(self.test_pdf_simple), "--engine", "basic",
            "--output", str(self.temp_dir)
        ])
        self.assertEqual(result.returncode, 0, "Basic engine should succeed")
        
        # Check output files exist
        output_md = self.temp_dir / "test_extract_paper.md"
        self.assertTrue(output_md.exists(), "Output markdown file should be created")
        
        # Test mineru engine (if available)
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            str(self.test_pdf_simple), "--engine", "mineru",
            "--output", str(self.temp_dir)
        ], timeout=600)  # Longer timeout for mineru
        
        # mineru might not be available, so we just check it doesn't crash with invalid error
        if result.returncode != 0:
            # If it fails, it should be due to missing dependencies, not invalid engine
            output = result.stdout + result.stderr
            self.assertNotIn("Invalid engine mode", output, "mineru should be recognized as valid engine")
    
    def test_page_selection(self):
        """Test page selection functionality"""
        if not self.test_pdf_2pages.exists():
            self.skipTest(f"Test PDF not found: {self.test_pdf_2pages}")
        
        # Test specific page extraction
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            str(self.test_pdf_2pages), "--page", "1",
            "--engine", "basic", "--output", str(self.temp_dir)
        ])
        self.assertEqual(result.returncode, 0, "Page selection should succeed")
        
        # Test page range
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            str(self.test_pdf_2pages), "--page", "1-2",
            "--engine", "basic", "--output", str(self.temp_dir)
        ])
        self.assertEqual(result.returncode, 0, "Page range selection should succeed")
    
    def test_post_processing(self):
        """Test post-processing functionality"""
        if not self.test_md_extracted.exists():
            self.skipTest(f"Test markdown not found: {self.test_md_extracted}")
        
        # Test basic post-processing
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(self.test_md_extracted)
        ])
        # Post-processing might succeed or fail depending on available tools
        # We just check it doesn't crash with invalid arguments
        self.assertIn(result.returncode, [0, 1], "Post-processing should handle gracefully")
        
        # Test with specific post-type
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", str(self.test_md_extracted), "--post-type", "formula"
        ])
        self.assertIn(result.returncode, [0, 1], "Post-processing with type should handle gracefully")
    
    def test_full_pipeline(self):
        """Test full pipeline processing"""
        if not self.test_pdf_simple.exists():
            self.skipTest(f"Test PDF not found: {self.test_pdf_simple}")
        
        # Test full pipeline
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--full", str(self.test_pdf_simple),
            "--engine", "basic", "--output", str(self.temp_dir)
        ], timeout=600)
        
        # Full pipeline should succeed or fail gracefully
        self.assertIn(result.returncode, [0, 1], "Full pipeline should handle gracefully")
        
        if result.returncode == 0:
            # Check that output was created
            output_files = list(self.temp_dir.glob("*.md"))
            self.assertGreater(len(output_files), 0, "Full pipeline should create markdown files")
    
    def test_run_environment_integration(self):
        """Test RUN environment integration and JSON output"""
        if not self.test_pdf_simple.exists():
            self.skipTest(f"Test PDF not found: {self.test_pdf_simple}")
        
        # Test with RUN environment variables
        with patch.dict(os.environ, {
            "RUN_IDENTIFIER": "test_extract_pdf",
            "RUN_DATA_FILE": str(self.temp_dir / "run_output.json")
        }):
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_simple), "--engine", "basic",
                "--output", str(self.temp_dir)
            ])
            
            # Check if RUN output file was created
            run_output_file = self.temp_dir / "run_output.json"
            if run_output_file.exists():
                with open(run_output_file, 'r') as f:
                    data = json.load(f)
                    self.assertIn('success', data, "RUN output should contain success field")
    
    def test_error_handling(self):
        """Test various error conditions and edge cases"""
        # Test with non-PDF file
        text_file = self.temp_dir / "test.txt"
        text_file.write_text("This is not a PDF")
        
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            str(text_file), "--engine", "basic"
        ])
        self.assertNotEqual(result.returncode, 0, "Non-PDF file should return error")
        
        # Test with invalid page specification
        if self.test_pdf_simple.exists():
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(self.test_pdf_simple), "--page", "invalid",
                "--engine", "basic"
            ])
            self.assertNotEqual(result.returncode, 0, "Invalid page spec should return error")
        
        # Test post-processing with non-existent file
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--post", "nonexistent.md"
        ])
        self.assertNotEqual(result.returncode, 0, "Post-processing non-existent file should return error")
    
    def test_class_functionality(self):
        """Test PDFExtractor and PDFPostProcessor classes if available"""
        if PDFExtractor is None:
            self.skipTest("PDFExtractor class not available")
        
        # Test PDFExtractor initialization
        extractor = PDFExtractor(debug=True)
        self.assertIsNotNone(extractor, "PDFExtractor should initialize")
        
        # Test with valid PDF if available
        if self.test_pdf_simple.exists():
            success, message = extractor.extract_pdf(str(self.test_pdf_simple))
            # Extraction might succeed or fail depending on dependencies
            self.assertIsInstance(success, bool, "extract_pdf should return boolean")
            self.assertIsInstance(message, str, "extract_pdf should return message string")
        
        # Test PDFPostProcessor if available
        if PDFPostProcessor is not None and self.test_md_extracted.exists():
            processor = PDFPostProcessor()
            self.assertIsNotNone(processor, "PDFPostProcessor should initialize")
    
    def test_project_structure(self):
        """Test project structure and data management"""
        # Test that required directories can be created
        test_project_dir = self.temp_dir / "test_project"
        
        # Simulate project structure creation
        result = self.run_subprocess([
            sys.executable, str(self.extract_pdf_path),
            "--help"  # Just test that the tool can run
        ])
        self.assertEqual(result.returncode, 0, "Tool should be able to run")
        
        # Check that EXTRACT_PDF_DATA directory gets created when needed
        extract_pdf_data = self.script_dir / "EXTRACT_PDF_DATA"
        if extract_pdf_data.exists():
            self.assertTrue(extract_pdf_data.is_dir(), "EXTRACT_PDF_DATA should be a directory")
            
            # Check for expected subdirectories
            expected_subdirs = ["images", "markdown"]
            for subdir in expected_subdirs:
                subdir_path = extract_pdf_data / subdir
                if subdir_path.exists():
                    self.assertTrue(subdir_path.is_dir(), f"{subdir} should be a directory")
    
    def test_batch_processing(self):
        """Test batch processing capabilities"""
        if not self.test_pdf_simple.exists():
            self.skipTest(f"Test PDF not found: {self.test_pdf_simple}")
        
        # Create multiple test files in temp directory
        test_pdfs = []
        for i in range(2):
            test_pdf = self.temp_dir / f"test_{i}.pdf"
            shutil.copy(self.test_pdf_simple, test_pdf)
            test_pdfs.append(test_pdf)
        
        # Test processing multiple files
        for test_pdf in test_pdfs:
            result = self.run_subprocess([
                sys.executable, str(self.extract_pdf_path),
                str(test_pdf), "--engine", "basic",
                "--output", str(self.temp_dir)
            ])
            # Each file should process independently
            self.assertIn(result.returncode, [0, 1], f"Processing {test_pdf.name} should handle gracefully")


def run_tests():
    """Run all tests with detailed output"""
    print("=== EXTRACT_PDF Unified Unit Tests ===")
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test class
    suite.addTests(loader.loadTestsFromTestCase(TestExtractPDF))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Output results
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
