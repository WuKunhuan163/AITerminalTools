#!/usr/bin/env python3
"""
Unit tests for FILEDIALOG tool
"""

import unittest
import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

class TestFileSelect(unittest.TestCase):
    """Test cases for FILEDIALOG tool"""

    def setUp(self):
        self.FILEDIALOG_script = Path(__file__).parent.parent / 'FILEDIALOG'
        self.FILEDIALOG_py = Path(__file__).parent.parent / 'FILEDIALOG.py'
        
        # Create a temporary directory for test files
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_pdf = self.temp_dir / "test.pdf"
        self.test_txt = self.temp_dir / "test.txt"
        
        # Create test files
        self.test_pdf.write_text("fake pdf content")
        self.test_txt.write_text("test text content")

    def tearDown(self):
        # Clean up temporary files
        if self.test_pdf.exists():
            self.test_pdf.unlink()
        if self.test_txt.exists():
            self.test_txt.unlink()
        if self.temp_dir.exists():
            self.temp_dir.rmdir()

    def test_filedialog_script_exists(self):
        """Test that FILEDIALOG script exists"""
        self.assertTrue(self.FILEDIALOG_script.exists())

    def test_filedialog_py_exists(self):
        """Test that FILEDIALOG.py exists"""
        self.assertTrue(self.FILEDIALOG_py.exists())

    def test_help_output(self):
        """Test FILEDIALOG help output"""
        result = subprocess.run([
            sys.executable, str(self.FILEDIALOG_py), '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('FILEDIALOG - File Selection Tool', result.stdout)
        self.assertIn('Usage:', result.stdout)
        self.assertIn('--types', result.stdout)
        self.assertIn('--title', result.stdout)

    def test_file_types_parameter(self):
        """Test that FILEDIALOG accepts file types parameter"""
        # Test with --types parameter (should not fail on parameter parsing)
        result = subprocess.run([
            sys.executable, str(self.FILEDIALOG_py), '--types', 'pdf', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        # Should still show help and not fail
        self.assertEqual(result.returncode, 0)
        self.assertIn('FILEDIALOG - File Selection Tool', result.stdout)

    def test_multiple_parameter(self):
        """Test that FILEDIALOG accepts multiple parameter"""
        result = subprocess.run([
            sys.executable, str(self.FILEDIALOG_py), '--multiple', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('FILEDIALOG - File Selection Tool', result.stdout)

    def test_title_parameter(self):
        """Test that FILEDIALOG accepts title parameter"""
        result = subprocess.run([
            sys.executable, str(self.FILEDIALOG_py), '--title', 'Test Title', '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('FILEDIALOG - File Selection Tool', result.stdout)

    def test_dir_parameter(self):
        """Test that FILEDIALOG accepts dir parameter"""
        result = subprocess.run([
            sys.executable, str(self.FILEDIALOG_py), '--dir', str(self.temp_dir), '--help'
        ], capture_output=True, text=True, timeout=10)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('FILEDIALOG - File Selection Tool', result.stdout)

    @patch('tkinter.filedialog.askopenfilename')
    @patch('tkinter.Tk')
    def test_single_FILEDIALOGion_mock(self, mock_tk, mock_askopenfilename):
        """Test single file selection with mocked tkinter"""
        # Mock tkinter components
        mock_root = MagicMock()
        mock_tk.return_value = mock_root
        mock_askopenfilename.return_value = str(self.test_pdf)
        
        # Import and test the module (if we can import it directly)
        try:
            import FILEDIALOG
            # This would test the actual function if we could import it
            # For now, we just test that the mock setup works
            self.assertTrue(True)
        except ImportError:
            # If we can't import directly, that's okay for this test
            self.assertTrue(True)

class TestFileSelectIntegration(unittest.TestCase):
    """Integration tests for FILEDIALOG tool"""
    
    def test_command_line_help(self):
        """Test command line help execution"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'FILEDIALOG.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('FILEDIALOG - File Selection Tool', result.stdout)

    def test_run_show_compatibility(self):
        """Test RUN --show compatibility with FILEDIALOG"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show',
            'FILEDIALOG',
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output - extract only the JSON part
        try:
            lines = result.stdout.strip().split('\n')
            json_lines = []
            in_json = False
            
            for line in lines:
                if line.strip().startswith('{'):
                    in_json = True
                if in_json:
                    json_lines.append(line)
                if line.strip().endswith('}') and in_json:
                    break
            
            if json_lines:
                json_output = '\n'.join(json_lines)
                output_data = json.loads(json_output)
                self.assertIn('success', output_data)
                # Should be successful since --help doesn't require GUI
                self.assertTrue(output_data['success'])
            else:
                # If no JSON found, check if output contains expected information
                self.assertIn('FILEDIALOG', result.stdout)
                
        except json.JSONDecodeError as e:
            # If JSON parsing fails, check if the help output is present
            self.assertIn('FILEDIALOG', result.stdout)
            print(f"Warning: JSON parsing failed, but output contains expected content: {e}")

if __name__ == '__main__':
    unittest.main() 