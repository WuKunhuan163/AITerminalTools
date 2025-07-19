#!/usr/bin/env python3
"""
Unit tests for OVERLEAF tool
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
    import OVERLEAF
except ImportError:
    # If import fails, skip tests
    OVERLEAF = None

class TestOverleaf(unittest.TestCase):
    """Test cases for OVERLEAF tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Create a simple test LaTeX file
        self.test_tex_content = r"""
\documentclass{article}
\begin{document}
\title{Test Document}
\author{Test Author}
\date{\today}
\maketitle

This is a test document.

\section{Introduction}
This is the introduction section.

\end{document}
"""
        self.test_tex_file = self.test_dir / "test.tex"
        with open(self.test_tex_file, 'w') as f:
            f.write(self.test_tex_content)
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(OVERLEAF.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_DATA_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(OVERLEAF.is_run_environment())
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = OVERLEAF.create_json_output(
            success=True,
            message="Compilation successful",
            output_file="test.pdf",
            log_content="Test log content"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('output_file', result)
        self.assertIn('log_content', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    @patch('subprocess.run')
    def test_latex_compilation_success(self, mock_run):
        """Test successful LaTeX compilation"""
        # Mock successful pdflatex run
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="This is pdfTeX, Version 3.141592653-2.6-1.40.22",
            stderr=""
        )
        
        result = OVERLEAF.compile_latex(str(self.test_tex_file))
        
        self.assertTrue(result['success'])
        self.assertIn('test.pdf', result['output_file'])
        mock_run.assert_called()
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    @patch('subprocess.run')
    def test_latex_compilation_failure(self, mock_run):
        """Test failed LaTeX compilation"""
        # Mock failed pdflatex run
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="! LaTeX Error: File `nonexistent.sty' not found."
        )
        
        result = OVERLEAF.compile_latex(str(self.test_tex_file))
        
        self.assertFalse(result['success'])
        self.assertIn('compilation failed', result['message'].lower())
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    def test_file_path_resolution(self):
        """Test proper file path resolution"""
        # Test relative path
        relative_path = "test.tex"
        resolved = OVERLEAF.resolve_tex_path(relative_path)
        self.assertTrue(Path(resolved).is_absolute())
        
        # Test absolute path
        absolute_path = str(self.test_tex_file)
        resolved = OVERLEAF.resolve_tex_path(absolute_path)
        self.assertEqual(resolved, absolute_path)
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['OVERLEAF.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    OVERLEAF.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()
    
    @unittest.skipIf(OVERLEAF is None, "OVERLEAF module not available")
    @patch('tkinter.filedialog.askopenfilename')
    def test_gui_FILEDIALOGion(self, mock_filedialog):
        """Test GUI file selection when no arguments provided"""
        mock_filedialog.return_value = str(self.test_tex_file)
        
        with patch('sys.argv', ['OVERLEAF.py']):
            with patch.object(OVERLEAF, 'compile_latex') as mock_compile:
                mock_compile.return_value = {
                    'success': True,
                    'message': 'Test compilation',
                    'output_file': 'test.pdf',
                    'log_content': 'Test log'
                }
                
                try:
                    OVERLEAF.main()
                except SystemExit:
                    pass
                
                mock_filedialog.assert_called_once()
                mock_compile.assert_called_once()

class TestOverleafIntegration(unittest.TestCase):
    """Integration tests for OVERLEAF tool"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        
        # Create test LaTeX file
        self.test_tex_content = r"""
\documentclass{article}
\begin{document}
Test document for integration testing.
\end{document}
"""
        self.test_tex_file = self.test_dir / "integration_test.tex"
        with open(self.test_tex_file, 'w') as f:
            f.write(self.test_tex_content)
    
    def tearDown(self):
        """Clean up integration test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_command_line_execution(self):
        """Test command line execution of OVERLEAF"""
        # Test with file argument
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'OVERLEAF.py'),
            str(self.test_tex_file)
        ], capture_output=True, text=True, timeout=30)
        
        # Should not crash (even if LaTeX is not installed)
        self.assertIn(result.returncode, [0, 1])  # 0 for success, 1 for LaTeX not found
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'OVERLEAF'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show OVERLEAF did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 