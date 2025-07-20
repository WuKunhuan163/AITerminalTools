#!/usr/bin/env python3
"""
Practical Integration Test Suite for Bin Tools
Tests tools with real data and handles interactive modes
"""

import os
import sys
import json
import subprocess
import tempfile
import shutil
import unittest
import argparse
from pathlib import Path
from datetime import datetime

class BinToolsIntegrationTest(unittest.TestCase):
    """Integration tests for bin tools with practical data"""
    
    # Class variable to track which tools to test
    tools_to_test = None
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        cls.test_dir = Path(tempfile.mkdtemp(prefix="bin_test_"))
        cls.original_cwd = os.getcwd()
        cls.base_dir = Path(__file__).parent.parent
        
        # Create test data directory
        cls.test_data_dir = cls.test_dir / "test_data"
        cls.test_data_dir.mkdir(exist_ok=True)
        
        print(f"Test environment: {cls.test_dir}")
        
        # Create test files
        cls.test_tex_file = cls.create_test_latex_file()
        cls.ref_md_file = cls.create_reference_markdown()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        os.chdir(cls.original_cwd)
        shutil.rmtree(cls.test_dir)
    
    def should_run_test(self, tool_name):
        """Check if a test should run based on tools_to_test"""
        if self.tools_to_test is None:
            return True  # Run all tests if no specific tools specified
        return tool_name in self.tools_to_test
    
    @classmethod
    def create_test_latex_file(cls):
        """Create a test LaTeX file for OVERLEAF and EXTRACT_PDF testing"""
        latex_content = r"""
\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}
\usepackage{amssymb}

\title{Test Document for PDF Extraction}
\author{Test Author}
\date{\today}

\begin{document}

\maketitle

\section{Introduction}
This is a test document created for testing PDF extraction capabilities.

\section{Mathematical Formulas}
Here are some mathematical expressions:

\begin{equation}
E = mc^2
\end{equation}

\begin{equation}
\sum_{i=1}^{n} i = \frac{n(n+1)}{2}
\end{equation}

\section{Lists and Tables}
\subsection{Bullet Points}
\begin{itemize}
\item First item
\item Second item
\item Third item
\end{itemize}

\subsection{Numbered List}
\begin{enumerate}
\item First numbered item
\item Second numbered item
\item Third numbered item
\end{enumerate}

\section{Conclusion}
This document contains various elements that should be extractable from PDF format.

\end{document}
"""
        
        test_tex_file = cls.test_data_dir / "test_document.tex"
        with open(test_tex_file, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        return test_tex_file
    
    @classmethod
    def create_reference_markdown(cls):
        """Create reference markdown for comparison with PDF extraction"""
        markdown_content = """# Test Document for PDF Extraction

**Author:** Test Author

## Introduction
This is a test document created for testing PDF extraction capabilities.

## Mathematical Formulas
Here are some mathematical expressions:

E = mc²

∑(i=1 to n) i = n(n+1)/2

## Lists and Tables
### Bullet Points
- First item
- Second item  
- Third item

### Numbered List
1. First numbered item
2. Second numbered item
3. Third numbered item

## Conclusion
This document contains various elements that should be extractable from PDF format.
"""
        
        ref_file = cls.test_data_dir / "test_document_ref.md"
        with open(ref_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return ref_file
    
    def test_01_file_existence(self):
        """Test that all required tool files exist"""
        print("\n" + "="*50)
        print("TESTING FILE EXISTENCE")
        print("="*50)
        
        expected_tools = [
            'OVERLEAF', 'EXTRACT_PDF', 'GOOGLE_DRIVE', 'SEARCH_PAPER',
            'EXPORT', 'DOWNLOAD', 'RUN', 'FILEDIALOG'
        ]
        
        for tool in expected_tools:
            with self.subTest(tool=tool):
                # Check Python file
                py_file = self.base_dir / f"{tool}.py"
                self.assertTrue(py_file.exists(), f"Python file missing: {py_file}")
                
                # Check shell script
                sh_file = self.base_dir / tool
                self.assertTrue(sh_file.exists(), f"Shell script missing: {sh_file}")
                
                # Check markdown documentation
                md_file = self.base_dir / f"{tool}.md"
                self.assertTrue(md_file.exists(), f"Documentation missing: {md_file}")
                
                print(f"✅ {tool} - All files exist")
    
    def test_02_bin_json_registry(self):
        """Test _bin.json registry file"""
        print("\n" + "="*50)
        print("TESTING _BIN.JSON REGISTRY")
        print("="*50)
        
        bin_json_path = self.base_dir / '_bin.json'
        self.assertTrue(bin_json_path.exists(), "_bin.json file not found")
        
        with open(bin_json_path, 'r') as f:
            data = json.load(f)
        
        self.assertIsInstance(data, dict, "_bin.json should contain a dictionary")
        self.assertIn('tools', data, "_bin.json should contain 'tools' key")
        
        # Check that all expected tools are registered
        expected_tools = ['OVERLEAF', 'EXTRACT_PDF', 'GOOGLE_DRIVE', 'SEARCH_PAPER',
                         'EXPORT', 'DOWNLOAD', 'RUN']
        
        tools_data = data['tools']
        for tool in expected_tools:
            with self.subTest(tool=tool):
                self.assertIn(tool, tools_data, f"Tool {tool} not found in _bin.json")
                tool_data = tools_data[tool]
                self.assertIn('description', tool_data, f"Tool {tool} missing description")
                self.assertIn('run_compatible', tool_data, f"Tool {tool} missing run_compatible flag")
        
        print(f"✅ _bin.json registry validated with {len(tools_data)} tools")
    
    def test_03_bin_py_management(self):
        """Test _bin.py management tool"""
        print("\n" + "="*50)
        print("TESTING _BIN.PY MANAGEMENT TOOL")
        print("="*50)
        
        bin_py_path = self.base_dir / '_bin.py'
        self.assertTrue(bin_py_path.exists(), "_bin.py file not found")
        
        # Check file size (should be substantial)
        file_size = bin_py_path.stat().st_size
        self.assertGreater(file_size, 1000, "_bin.py file appears to be too small")
        
        print(f"✅ _bin.py management tool validated ({file_size} bytes)")
    
    def test_04_RUN_DATA_directory(self):
        """Test RUN output directory"""
        print("\n" + "="*50)
        print("TESTING RUN OUTPUT DIRECTORY")
        print("="*50)
        
        RUN_DATA_dir = self.base_dir / 'RUN_DATA'
        self.assertTrue(RUN_DATA_dir.exists(), "RUN_DATA directory not found")
        self.assertTrue(RUN_DATA_dir.is_dir(), "RUN_DATA should be a directory")
        
        # Count JSON files
        json_files = list(RUN_DATA_dir.glob('*.json'))
        print(f"✅ RUN_DATA directory validated with {len(json_files)} JSON files")
    
    def test_05_overleaf_compilation(self):
        """Test OVERLEAF LaTeX compilation"""
        if not self.should_run_test('OVERLEAF'):
            self.skipTest("OVERLEAF not in tools_to_test")
            
        print("\n" + "="*50)
        print("TESTING OVERLEAF COMPILATION")
        print("="*50)
        
        # Test 1: Check if LaTeX is installed
        latex_check = subprocess.run(['latexmk', '--version'], 
                                   capture_output=True, text=True, timeout=10)
        
        if latex_check.returncode != 0:
            self.skipTest("LaTeX not installed - skipping compilation test")
            print("⚠️  OVERLEAF - LaTeX not installed, skipping test")
            return
        
        print("✅ OVERLEAF - LaTeX installation confirmed")
        
        # Test 2: File not found error
        result = subprocess.run([
            sys.executable, 
            str(self.base_dir / 'OVERLEAF.py'),
            'nonexistent_file.tex'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "OVERLEAF with nonexistent file should fail")
        self.assertIn('Error', result.stdout, "Should show error for nonexistent file")
        
        print("✅ OVERLEAF - Error handling for nonexistent file")
        
        # Test 3: Actual LaTeX compilation
        result = subprocess.run([
            sys.executable, 
            str(self.base_dir / 'OVERLEAF.py'),
            str(self.test_tex_file)
        ], capture_output=True, text=True, timeout=60, cwd=self.test_dir)
        
        # Check if compilation was successful
        pdf_file = self.test_tex_file.with_suffix('.pdf')
        
        if result.returncode == 0 and pdf_file.exists():
            print("✅ OVERLEAF - LaTeX compilation successful")
            print(f"   Generated PDF: {pdf_file}")
            print(f"   PDF size: {pdf_file.stat().st_size} bytes")
            # Store PDF file for next test
            self.__class__.generated_pdf = pdf_file
            
            # Verify PDF file is not empty
            self.assertGreater(pdf_file.stat().st_size, 1000, "PDF file should be substantial")
            
        else:
            print("❌ OVERLEAF - LaTeX compilation failed")
            print(f"   Return code: {result.returncode}")
            print(f"   Stdout: {result.stdout}")
            print(f"   Stderr: {result.stderr}")
            # Still continue with tests, but mark as failed
            self.__class__.generated_pdf = None
            
            # Fail the test if compilation failed
            self.fail(f"LaTeX compilation failed with return code {result.returncode}")
        
        print("✅ OVERLEAF - All tests completed")
    
    def test_06_extract_pdf(self):
        """Test EXTRACT_PDF tool"""
        print("\n" + "="*50)
        print("TESTING EXTRACT_PDF")
        print("="*50)
        
        # Check if we have a PDF from previous test
        if not hasattr(self.__class__, 'generated_pdf') or self.__class__.generated_pdf is None:
            self.skipTest("No PDF available from OVERLEAF test - skipping PDF extraction")
        
        pdf_file = self.__class__.generated_pdf
        if not pdf_file.exists():
            self.skipTest("Generated PDF file not found - skipping PDF extraction")
        
        # Test PDF extraction
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'EXTRACT_PDF.py'),
            str(pdf_file),
            '--no-image-api'
        ], capture_output=True, text=True, timeout=120, cwd=self.test_dir)
        
        # Look for output markdown file
        output_files = list(self.test_data_dir.glob("*.md"))
        extracted_file = None
        
        for f in output_files:
            if f.name != "test_document_ref.md":
                extracted_file = f
                break
        
        if result.returncode == 0 and extracted_file and extracted_file.exists():
            print("✅ EXTRACT_PDF - PDF extraction successful")
            print(f"   Generated file: {extracted_file}")
            
            # Compare with reference
            similarity = self.compare_extraction_results(extracted_file, self.ref_md_file)
            print(f"   Similarity with reference: {similarity:.2f}")
            
            # Assert that extraction produced some output
            self.assertIsNotNone(extracted_file, "PDF extraction should produce output file")
            self.assertTrue(extracted_file.exists(), "Extracted file should exist")
            
            # Basic content check
            with open(extracted_file, 'r', encoding='utf-8') as f:
                content = f.read()
            self.assertGreater(len(content), 100, "Extracted content should not be empty")
            
        else:
            print("❌ EXTRACT_PDF - PDF extraction failed")
            print(f"   Error: {result.stderr}")
            
            # Check if MinerU is available or other dependency issues
            if ("mineru" in result.stderr.lower() or 
                "magic-pdf" in result.stderr.lower() or
                "command not found" in result.stderr.lower() or
                "no module named" in result.stderr.lower() or
                result.stderr.strip() == ""):
                self.skipTest("MinerU or dependencies not available - skipping PDF extraction test")
            else:
                self.fail(f"PDF extraction failed: {result.stderr}")
    
    def compare_extraction_results(self, extracted_file, reference_file):
        """Compare extracted text with reference markdown"""
        try:
            with open(extracted_file, 'r', encoding='utf-8') as f:
                extracted_text = f.read().lower()
            
            with open(reference_file, 'r', encoding='utf-8') as f:
                reference_text = f.read().lower()
            
            # Simple similarity check based on common words
            extracted_words = set(extracted_text.split())
            reference_words = set(reference_text.split())
            
            if len(reference_words) == 0:
                return 0.0
            
            common_words = extracted_words.intersection(reference_words)
            similarity = len(common_words) / len(reference_words)
            
            return similarity
            
        except Exception as e:
            print(f"Warning: Could not compare extraction results: {e}")
            return 0.0
    
    def test_07_google_drive(self):
        """Test GOOGLE_DRIVE tool"""
        if not self.should_run_test('GOOGLE_DRIVE'):
            self.skipTest("GOOGLE_DRIVE not in tools_to_test")
            
        print("\n" + "="*50)
        print("TESTING GOOGLE_DRIVE")
        print("="*50)
        
        # Test 1: Help output
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'GOOGLE_DRIVE.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0, "GOOGLE_DRIVE --help should succeed")
        self.assertIn('Google Drive', result.stdout, "Help should mention Google Drive")
        self.assertIn('Usage:', result.stdout, "Help should show usage")
        self.assertIn('Examples:', result.stdout, "Help should show examples")
        
        print("✅ GOOGLE_DRIVE - Help output successful")
        
        # Test 2: Error handling - Too many arguments
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'GOOGLE_DRIVE.py'),
            'arg1', 'arg2', 'arg3'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "GOOGLE_DRIVE with too many args should fail")
        self.assertIn('Error', result.stdout, "Should show error message")
        
        print("✅ GOOGLE_DRIVE - Error handling for too many arguments")
        
        # Test 3: Default behavior (should try to open browser)
        # Note: This test only checks that the command runs without error
        # It doesn't actually verify that a browser opens since that's system-dependent
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'GOOGLE_DRIVE.py')
        ], capture_output=True, text=True, timeout=30)
        
        # Should return 0 (success) or 1 (browser failed to open)
        # Both are acceptable in a test environment
        self.assertIn(result.returncode, [0, 1], "GOOGLE_DRIVE should return 0 or 1")
        
        if result.returncode == 0:
            print("✅ GOOGLE_DRIVE - Default behavior successful (browser opened)")
        else:
            print("✅ GOOGLE_DRIVE - Default behavior handled (browser may not be available)")
        
        # Test 4: -my option
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'GOOGLE_DRIVE.py'),
            '-my'
        ], capture_output=True, text=True, timeout=30)
        
        # Should return 0 (success) or 1 (browser failed to open)
        self.assertIn(result.returncode, [0, 1], "GOOGLE_DRIVE -my should return 0 or 1")
        
        if result.returncode == 0:
            print("✅ GOOGLE_DRIVE - My Drive option successful")
        else:
            print("✅ GOOGLE_DRIVE - My Drive option handled (browser may not be available)")
        
        print("✅ GOOGLE_DRIVE - All tests completed")
    
    def test_08_search_paper(self):
        """Test SEARCH_PAPER tool"""
        if not self.should_run_test('SEARCH_PAPER'):
            self.skipTest("SEARCH_PAPER not in tools_to_test")
            
        print("\n" + "="*50)
        print("TESTING SEARCH_PAPER")
        print("="*50)
        
        # Test 1: Help output
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'SEARCH_PAPER.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0, "SEARCH_PAPER --help should succeed")
        self.assertIn('Search', result.stdout, "Help should mention Search")
        # Check for either 'Usage:' or 'usage:' (case insensitive)
        self.assertTrue('Usage:' in result.stdout or 'usage:' in result.stdout, 
                       "Help should show usage information")
        # SEARCH_PAPER uses argparse which doesn't show 'Examples:' section
        self.assertIn('optional arguments:', result.stdout, "Help should show optional arguments")
        
        print("✅ SEARCH_PAPER - Help output successful")
        
        # Test 2: Error handling - Invalid max-results
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'SEARCH_PAPER.py'),
            '--max-results', 'invalid'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertNotEqual(result.returncode, 0, "SEARCH_PAPER with invalid max-results should fail")
        # argparse errors go to stderr, not stdout
        self.assertTrue('error:' in result.stderr or 'Error' in result.stdout, 
                       "Should show error for invalid max-results")
        
        print("✅ SEARCH_PAPER - Error handling for invalid max-results")
        
        # Test 3: Error handling - Missing max-results value
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'SEARCH_PAPER.py'),
            '--max-results'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertNotEqual(result.returncode, 0, "SEARCH_PAPER with missing max-results value should fail")
        # argparse errors go to stderr, not stdout
        self.assertTrue('error:' in result.stderr or 'Error' in result.stdout, 
                       "Should show error for missing max-results value")
        
        print("✅ SEARCH_PAPER - Error handling for missing max-results value")
        
        # Test 4: Error handling - Unknown option
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'SEARCH_PAPER.py'),
            '--unknown-option'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertNotEqual(result.returncode, 0, "SEARCH_PAPER with unknown option should fail")
        # argparse errors go to stderr, not stdout
        self.assertTrue('error:' in result.stderr or 'unrecognized arguments' in result.stderr, 
                       "Should show error for unknown option")
        
        print("✅ SEARCH_PAPER - Error handling for unknown option")
        
        # Test 5: Actual search with a simple query (but allow network failures)
        try:
            result = subprocess.run([
                sys.executable,
                str(self.base_dir / 'SEARCH_PAPER.py'),
                'machine learning',
                '--max-results', '2'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ SEARCH_PAPER - Paper search successful")
                # Check if output contains expected elements
                if 'Title:' in result.stdout or 'Authors:' in result.stdout:
                    print("✅ SEARCH_PAPER - Search results contain expected format")
                else:
                    print("⚠️  SEARCH_PAPER - Search results may be empty (network issue?)")
            else:
                print("⚠️  SEARCH_PAPER - Paper search failed (network issue?)")
                print(f"   Error: {result.stderr}")
                # Don't fail test for network issues
                
        except subprocess.TimeoutExpired:
            print("⚠️  SEARCH_PAPER - Search timeout (network issue?)")
            # Don't fail test for timeouts
        
        # Test 6: Search with sources parameter
        try:
            result = subprocess.run([
                sys.executable,
                str(self.base_dir / 'SEARCH_PAPER.py'),
                'neural networks',
                '--max-results', '1',
                '--sources', 'arxiv'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print("✅ SEARCH_PAPER - Search with sources parameter successful")
            else:
                print("⚠️  SEARCH_PAPER - Search with sources failed (network issue?)")
                
        except subprocess.TimeoutExpired:
            print("⚠️  SEARCH_PAPER - Search with sources timeout (network issue?)")
        
        print("✅ SEARCH_PAPER - All tests completed")
    
    def test_09_export(self):
        """Test EXPORT tool"""
        if not self.should_run_test('EXPORT'):
            self.skipTest("EXPORT not in tools_to_test")
            
        print("\n" + "="*50)
        print("TESTING EXPORT")
        print("="*50)
        
        # Test 1: Help output
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'EXPORT.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0, "EXPORT --help should succeed")
        self.assertIn('Environment', result.stdout, "Help should mention Environment")
        self.assertIn('Usage:', result.stdout, "Help should show usage")
        
        print("✅ EXPORT - Help output successful")
        
        # Test 2: Error handling - No arguments
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'EXPORT.py')
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "EXPORT with no args should fail")
        self.assertIn('Error', result.stdout, "Should show error message")
        
        print("✅ EXPORT - Error handling for no arguments")
        
        # Test 3: Error handling - Missing value
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'EXPORT.py'),
            'TEST_VAR'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "EXPORT with missing value should fail")
        self.assertIn('Error', result.stdout, "Should show error for missing value")
        
        print("✅ EXPORT - Error handling for missing value")
        
        # Test 4: Actual export test
        test_var_name = "BIN_TEST_EXPORT_VAR_12345"
        test_var_value = "test_value_for_bin_unittest"
        
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'EXPORT.py'),
            test_var_name,
            test_var_value
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0, "EXPORT with valid args should succeed")
        self.assertIn('Successfully exported', result.stdout, "Should show success message")
        
        print("✅ EXPORT - Variable export successful")
        
        # Test 5: Verify variable was written to config files
        config_files = [
            Path.home() / ".bash_profile",
            Path.home() / ".bashrc", 
            Path.home() / ".zshrc"
        ]
        
        found_in_files = []
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()
                        if f'export {test_var_name}="{test_var_value}"' in content:
                            found_in_files.append(str(config_file))
                except Exception:
                    pass
        
        self.assertGreater(len(found_in_files), 0, "Variable should be found in at least one config file")
        print(f"✅ EXPORT - Variable found in config files: {', '.join(found_in_files)}")
        
        # Test 6: Clean up - Remove the test variable from config files
        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        lines = f.readlines()
                    
                    # Remove lines containing our test variable
                    new_lines = []
                    for line in lines:
                        if f'export {test_var_name}=' not in line:
                            new_lines.append(line)
                    
                    # Write back if changed
                    if len(new_lines) != len(lines):
                        with open(config_file, 'w') as f:
                            f.writelines(new_lines)
                        print(f"✅ EXPORT - Cleaned up {config_file}")
                except Exception as e:
                    print(f"⚠️  EXPORT - Could not clean up {config_file}: {e}")
        
        print("✅ EXPORT - All tests completed")
    
    def test_10_download(self):
        """Test DOWNLOAD tool"""
        if not self.should_run_test('DOWNLOAD'):
            self.skipTest("DOWNLOAD not in tools_to_test")
            
        print("\n" + "="*50)
        print("TESTING DOWNLOAD")
        print("="*50)
        
        # Test 1: Help output
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'DOWNLOAD.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0, "DOWNLOAD --help should succeed")
        self.assertIn('Download', result.stdout, "Help should mention Download")
        self.assertIn('Usage:', result.stdout, "Help should show usage")
        self.assertIn('Examples:', result.stdout, "Help should show examples")
        
        print("✅ DOWNLOAD - Help output successful")
        
        # Test 2: Error handling - No URL provided
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'DOWNLOAD.py')
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "DOWNLOAD with no args should fail")
        self.assertIn('Error', result.stdout, "Should show error message")
        
        print("✅ DOWNLOAD - Error handling for no URL")
        
        # Test 3: Error handling - Invalid URL
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'DOWNLOAD.py'),
            'invalid-url'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "DOWNLOAD with invalid URL should fail")
        self.assertIn('Error', result.stdout, "Should show error for invalid URL")
        
        print("✅ DOWNLOAD - Error handling for invalid URL")
        
        # Test 4: Actual download test with a small test file
        # Using a reliable test URL that serves a small text file
        test_url = "https://httpbin.org/robots.txt"
        test_download_dir = self.test_dir / "download_test"
        test_download_dir.mkdir(exist_ok=True)
        
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'DOWNLOAD.py'),
            test_url,
            str(test_download_dir)
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Check if file was downloaded
            downloaded_file = test_download_dir / "robots.txt"
            self.assertTrue(downloaded_file.exists(), "Downloaded file should exist")
            self.assertGreater(downloaded_file.stat().st_size, 0, "Downloaded file should not be empty")
            
            print("✅ DOWNLOAD - Actual download successful")
        else:
            # If download fails (network issues), skip this test
            print("⚠️  DOWNLOAD - Actual download skipped (network issues)")
            print(f"   Error: {result.stderr}")
        
        print("✅ DOWNLOAD - All tests completed")
    
    def test_11_run_show_integration(self):
        """Test RUN --show functionality for all tools"""
        print("\n" + "="*50)
        print("TESTING RUN --show INTEGRATION")
        print("="*50)
        
        # Read _bin.json to get all tools
        bin_json_path = self.base_dir / '_bin.json'
        with open(bin_json_path, 'r') as f:
            tools_data = json.load(f)
        
        run_compatible_tools = [
            tool for tool, data in tools_data.items() 
            if data.get('run_compatible', False)
        ]
        
        print(f"Testing RUN --show for {len(run_compatible_tools)} compatible tools...")
        
        for tool in run_compatible_tools:
            with self.subTest(tool=tool):
                print(f"\nTesting: RUN --show {tool}")
                
                result = subprocess.run([
                    sys.executable, 'RUN.py', '--show', tool
                ], capture_output=True, text=True, timeout=30, 
                cwd=self.base_dir)
                
                if result.returncode == 0:
                    print(f"✅ {tool} - PASSED")
                else:
                    print(f"❌ {tool} - FAILED")
                    print(f"   Error: {result.stderr}")
                    
                self.assertEqual(result.returncode, 0, 
                               f"RUN --show {tool} should succeed")
    
    def test_12_FILEDIALOG(self):
        """Test FILEDIALOG tool"""
        if not self.should_run_test('FILEDIALOG'):
            self.skipTest("FILEDIALOG not in tools_to_test")
            
        print("\n" + "="*50)
        print("TESTING FILEDIALOG")
        print("="*50)
        
        # Test 1: Help output
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'FILEDIALOG.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0, "FILEDIALOG --help should succeed")
        self.assertIn('FILEDIALOG', result.stdout, "Help should mention FILEDIALOG")
        self.assertIn('Usage:', result.stdout, "Help should show usage")
        self.assertIn('Examples:', result.stdout, "Help should show examples")
        self.assertIn('File Types:', result.stdout, "Help should show file types")
        
        print("✅ FILEDIALOG - Help output successful")
        
        # Test 2: Error handling - Invalid directory
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'FILEDIALOG.py'),
            '--dir', '/nonexistent/directory'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "FILEDIALOG with invalid directory should fail")
        self.assertIn('Error', result.stdout, "Should show error message")
        self.assertIn('does not exist', result.stdout, "Should mention directory doesn't exist")
        
        print("✅ FILEDIALOG - Error handling for invalid directory")
        
        # Test 3: Error handling - Invalid argument
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'FILEDIALOG.py'),
            '--invalid-arg'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 1, "FILEDIALOG with invalid argument should fail")
        self.assertIn('Error', result.stdout, "Should show error for invalid argument")
        
        print("✅ FILEDIALOG - Error handling for invalid argument")
        
        # Test 4: RUN integration test with help
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'RUN.py'),
            '--show', 'FILEDIALOG', '--help'
        ], capture_output=True, text=True, timeout=30, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, "RUN --show FILEDIALOG --help should succeed")
        
        # Parse JSON output to verify structure
        json_start = result.stdout.find('{')
        json_end = result.stdout.rfind('}') + 1
        if json_start != -1 and json_end > json_start:
            json_output = result.stdout[json_start:json_end]
            try:
                data = json.loads(json_output)
                self.assertTrue(data.get('success', False), "JSON should indicate success")
                self.assertIn('help', data, "JSON should contain help field")
            except json.JSONDecodeError:
                self.fail("Should produce valid JSON output")
        
        print("✅ FILEDIALOG - RUN integration test successful")
        
        # Test 5: Test argument validation without opening GUI
        # Test with missing value for --types
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'FILEDIALOG.py'),
            '--types'
        ], capture_output=True, text=True, timeout=5)
        
        self.assertEqual(result.returncode, 1, "FILEDIALOG with missing --types value should fail")
        self.assertIn('requires a value', result.stdout, "Should show error for missing --types value")
        
        # Test with missing value for --title
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'FILEDIALOG.py'),
            '--title'
        ], capture_output=True, text=True, timeout=5)
        
        self.assertEqual(result.returncode, 1, "FILEDIALOG with missing --title value should fail")
        self.assertIn('requires a value', result.stdout, "Should show error for missing --title value")
        
        print("✅ FILEDIALOG - Argument validation test successful")
        
        print("✅ FILEDIALOG - All tests completed")

    def test_13_run_tool_itself(self):
        """Test RUN tool itself and compare --show vs normal execution"""
        print("\n" + "="*50)
        print("TESTING RUN TOOL ITSELF")
        print("="*50)
        
        # Test 1: RUN RUN should fail (recursive call)
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'RUN.py'),
            'RUN'
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertNotEqual(result.returncode, 0, "RUN RUN should fail")
        print("✅ RUN RUN - Properly fails as expected")
        
        # Test 2: RUN --help should work
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'RUN.py'),
            '--help'
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, "RUN --help should succeed")
        self.assertIn('Usage:', result.stdout, "Should show usage information")
        print("✅ RUN --help - Shows usage information")
        
        # Test 3: Compare RUN --show SEARCH_PAPER --help vs RUN SEARCH_PAPER --help
        result_show = subprocess.run([
            sys.executable,
            str(self.base_dir / 'RUN.py'),
            '--show', 'SEARCH_PAPER', '--help'
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        result_normal = subprocess.run([
            sys.executable,
            str(self.base_dir / 'RUN.py'),
            'SEARCH_PAPER', '--help'
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertEqual(result_show.returncode, 0, "RUN --show SEARCH_PAPER --help should succeed")
        self.assertEqual(result_normal.returncode, 0, "RUN SEARCH_PAPER --help should succeed")
        
        # --show should have JSON output, normal should not
        self.assertIn('{', result_show.stdout, "--show should produce JSON output")
        self.assertNotIn('{', result_normal.stdout, "Normal execution should not produce JSON output")
        
        print("✅ RUN --show vs RUN - Properly differentiated")
        
        # Test 4: Test invalid command
        result = subprocess.run([
            sys.executable,
            str(self.base_dir / 'RUN.py'),
            'NONEXISTENT_TOOL'
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertNotEqual(result.returncode, 0, "RUN with invalid command should fail")
        print("✅ RUN with invalid command - Properly fails")
        
        print("✅ RUN tool tests completed")

def load_bin_json():
    """Load _bin.json file"""
    bin_json_path = Path(__file__).parent.parent / '_bin.json'
    try:
        with open(bin_json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading _bin.json: {e}")
        return None

def save_bin_json(data):
    """Save _bin.json file"""
    bin_json_path = Path(__file__).parent.parent / '_bin.json'
    try:
        with open(bin_json_path, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving _bin.json: {e}")
        return False

def reset_test_status():
    """Reset test status for all tools"""
    data = load_bin_json()
    if not data:
        return False
    
    for tool_name, tool_data in data['tools'].items():
        if tool_data.get('testable', False):
            tool_data['test_passed'] = False
        else:
            tool_data['test_passed'] = True
    
    if save_bin_json(data):
        print("✅ Test status reset successfully")
        return True
    else:
        print("❌ Failed to reset test status")
        return False

def set_tools_test_status(tools, passed=False):
    """Set test status for specified tools"""
    data = load_bin_json()
    if not data:
        return False
    
    updated_tools = []
    for tool_name in tools:
        if tool_name in data['tools']:
            data['tools'][tool_name]['test_passed'] = passed
            updated_tools.append(tool_name)
        else:
            print(f"⚠️  Tool '{tool_name}' not found in _bin.json")
    
    if save_bin_json(data):
        print(f"✅ Updated test status for tools: {', '.join(updated_tools)}")
        return True
    else:
        print("❌ Failed to update test status")
        return False

def get_available_tools():
    """Get list of all available tools from _bin.json"""
    data = load_bin_json()
    if not data:
        return []
    
    return list(data['tools'].keys())

def get_testable_tools():
    """Get list of testable tools from _bin.json"""
    data = load_bin_json()
    if not data:
        return []
    
    return [tool_name for tool_name, tool_data in data['tools'].items() 
            if tool_data.get('testable', False)]

if __name__ == '__main__':
    # Handle custom arguments before unittest processes them
    custom_args = ['--reset-test', '--tools', '--list-tools', '--list-testable']
    has_custom_args = any(arg in sys.argv for arg in custom_args)
    
    if has_custom_args:
        parser = argparse.ArgumentParser(description='Bin Tools Integration Test Suite')
        parser.add_argument('--reset-test', action='store_true', 
                           help='Reset test status for all tools')
        parser.add_argument('--tools', nargs='+', 
                           help='Specify tools to test (sets their test_passed to false)')
        parser.add_argument('--list-tools', action='store_true',
                           help='List all available tools')
        parser.add_argument('--list-testable', action='store_true',
                           help='List all testable tools')
        
        # Parse only known args to avoid conflicts with unittest
        args, remaining = parser.parse_known_args()
        
        # Handle special commands
        if args.reset_test:
            reset_test_status()
            sys.exit(0)
        
        if args.list_tools:
            tools = get_available_tools()
            print("Available tools:")
            for tool in tools:
                print(f"  - {tool}")
            sys.exit(0)
        
        if args.list_testable:
            tools = get_testable_tools()
            print("Testable tools:")
            for tool in tools:
                print(f"  - {tool}")
            sys.exit(0)
        
        if args.tools:
            # Validate tools exist
            available_tools = get_available_tools()
            invalid_tools = [tool for tool in args.tools if tool not in available_tools]
            if invalid_tools:
                print(f"❌ Invalid tools: {', '.join(invalid_tools)}")
                print(f"Available tools: {', '.join(available_tools)}")
                sys.exit(1)
            
            # Set specified tools to test_passed = false
            set_tools_test_status(args.tools, passed=False)
            print(f"Starting tests for tools: {', '.join(args.tools)}")
            
            # Set the tools_to_test class variable
            BinToolsIntegrationTest.tools_to_test = args.tools
            
            # Remove custom args from sys.argv before unittest processes them
            sys.argv = [sys.argv[0]] + remaining
    
    # Run tests with verbose output and capture results
    import io
    from contextlib import redirect_stdout, redirect_stderr
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(BinToolsIntegrationTest)
    
    # 运行测试并捕获结果
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # 如果有指定的工具且测试成功，更新状态
    if hasattr(BinToolsIntegrationTest, 'tools_to_test') and BinToolsIntegrationTest.tools_to_test:
        if result.wasSuccessful():
            # 测试全部通过，更新状态为 true
            set_tools_test_status(BinToolsIntegrationTest.tools_to_test, passed=True)
        else:
            print(f"❌ Some tests failed. Test status remains false for: {', '.join(BinToolsIntegrationTest.tools_to_test)}")
    
    # 退出时返回正确的状态码
    sys.exit(0 if result.wasSuccessful() else 1) 