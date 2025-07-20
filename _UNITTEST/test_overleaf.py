#!/usr/bin/env python3
"""
Functional tests for OVERLEAF tool
Tests actual LaTeX compilation functionality
"""

import unittest
import os
import sys
import json
import tempfile
import subprocess
import shutil
from pathlib import Path

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestOverleafFunctional(unittest.TestCase):
    """Functional test cases for OVERLEAF tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        self.base_dir = Path(__file__).parent.parent
        
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_simple_tex_file(self, filename="test.tex"):
        """Create a simple LaTeX file for testing"""
        tex_content = r"""
\documentclass{article}
\begin{document}
\title{Test Document}
\author{Test Author}
\date{\today}
\maketitle

This is a test document for OVERLEAF functional testing.

\section{Introduction}
This is the introduction section.

\section{Conclusion}
This is the conclusion section.

\end{document}
"""
        tex_file = self.test_dir / filename
        with open(tex_file, 'w') as f:
            f.write(tex_content)
        return tex_file
    
    def test_basic_latex_compilation(self):
        """Test basic LaTeX compilation functionality"""
        tex_file = self.create_simple_tex_file()
        
        # Test direct compilation
        result = subprocess.run([
            sys.executable, str(self.base_dir / 'OVERLEAF.py'),
            str(tex_file)
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, f"LaTeX compilation failed: {result.stderr}")
        
        # Check if PDF was generated
        pdf_file = tex_file.with_suffix('.pdf')
        self.assertTrue(pdf_file.exists(), "PDF file was not generated")
        
        # Verify PDF is not empty
        self.assertGreater(pdf_file.stat().st_size, 1000, "PDF file seems too small")
    
    def test_run_environment_compilation(self):
        """Test LaTeX compilation in RUN environment"""
        tex_file = self.create_simple_tex_file()
        
        # Test RUN --show compilation
        result = subprocess.run([
            sys.executable, str(self.base_dir / 'RUN.py'),
            '--show', 'OVERLEAF', str(tex_file)
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, f"RUN OVERLEAF failed: {result.stderr}")
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertTrue(output_data.get('success', False), "Compilation should succeed")
            self.assertIn('output', output_data, "Output should contain PDF path")
            
            # Verify PDF path is provided (file may be in temp directory and cleaned up)
            pdf_path = Path(output_data['output'])
            self.assertTrue(str(pdf_path).endswith('.pdf'), "Output should be a PDF file")
            self.assertIn('overleaf_', str(pdf_path), "Should use OVERLEAF temp directory")
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON output: {result.stdout}")
    
    def test_output_dir_functionality(self):
        """Test --output-dir functionality"""
        tex_file = self.create_simple_tex_file()
        output_dir = self.test_dir / "output"
        
        # Test with --output-dir
        result = subprocess.run([
            sys.executable, str(self.base_dir / 'RUN.py'),
            '--show', 'OVERLEAF', str(tex_file), '--output-dir', str(output_dir)
        ], capture_output=True, text=True, timeout=10, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, f"OVERLEAF with --output-dir failed: {result.stderr}")
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertTrue(output_data.get('success', False), "Compilation should succeed")
            
            # Verify PDF is in the specified output directory
            pdf_path = Path(output_data['output'])
            self.assertEqual(pdf_path.parent, output_dir, "PDF should be in specified output directory")
            self.assertTrue(pdf_path.exists(), f"PDF file not found at {pdf_path}")
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON output: {result.stdout}")
    
    def test_help_functionality(self):
        """Test --help functionality"""
        result = subprocess.run([
            sys.executable, str(self.base_dir / 'RUN.py'),
            '--show', 'OVERLEAF', '--help'
        ], capture_output=True, text=True, timeout=5, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, "OVERLEAF --help should succeed")
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertTrue(output_data.get('success', False), "--help should succeed")
            self.assertIn('output', output_data, "Should contain help output")
            help_text = output_data['output']
            self.assertIn('usage:', help_text.lower(), "Should show usage information")
            self.assertIn('--output-dir', help_text, "Should show --output-dir option")
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON output: {result.stdout}")
    
    def test_nonexistent_file_error(self):
        """Test error handling for nonexistent file"""
        nonexistent_file = self.test_dir / "nonexistent.tex"
        
        result = subprocess.run([
            sys.executable, str(self.base_dir / 'RUN.py'),
            '--show', 'OVERLEAF', str(nonexistent_file)
        ], capture_output=True, text=True, timeout=5, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 1, "Should fail for nonexistent file")
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertFalse(output_data.get('success', True), "Should report failure")
            self.assertIn('error', output_data, "Should contain error message")
            self.assertIn('File not found', output_data['error'], "Should indicate file not found")
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON output: {result.stdout}")

class TestOverleafIntegration(unittest.TestCase):
    """Integration tests for OVERLEAF with test data"""
    
    def setUp(self):
        """Set up test environment"""
        self.base_dir = Path(__file__).parent.parent
        self.test_data_dir = self.base_dir / "_UNITTEST" / "_DATA"
    
    def test_with_test_data(self):
        """Test OVERLEAF with existing test data"""
        test_tex = self.test_data_dir / "test_report.tex"
        
        if not test_tex.exists():
            self.skipTest(f"Test file {test_tex} not found")
        
        # Test compilation with test data
        result = subprocess.run([
            sys.executable, str(self.base_dir / 'RUN.py'),
            '--show', 'OVERLEAF', str(test_tex)
        ], capture_output=True, text=True, timeout=15, cwd=self.base_dir)
        
        self.assertEqual(result.returncode, 0, f"Test data compilation failed: {result.stderr}")
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertTrue(output_data.get('success', False), "Test data compilation should succeed")
            
            # Verify PDF path is provided (file may be in temp directory and cleaned up)
            pdf_path = Path(output_data['output'])
            self.assertTrue(str(pdf_path).endswith('.pdf'), "Output should be a PDF file")
            self.assertIn('test_report', str(pdf_path), "Should reference the test file")
        except json.JSONDecodeError:
            self.fail(f"Invalid JSON output: {result.stdout}")

if __name__ == '__main__':
    unittest.main() 