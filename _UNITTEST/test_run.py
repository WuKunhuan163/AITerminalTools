#!/usr/bin/env python3
"""
Unit tests for RUN tool
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
    import RUN
except ImportError:
    RUN = None

class TestRUN(unittest.TestCase):
    """Test cases for RUN tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
    
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_run_identifier_generation(self):
        """Test unique run identifier generation"""
        id1 = RUN.generate_run_identifier()
        id2 = RUN.generate_run_identifier()
        
        self.assertNotEqual(id1, id2)
        self.assertEqual(len(id1), 16)  # Should be 16 character hex string
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_json_output_format(self):
        """Test JSON output format"""
        result = RUN.create_json_output(
            success=True,
            message="Command executed successfully",
            command="test_command",
            output="test output",
            error="",
            run_identifier="test_run_id"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('command', result)
        self.assertIn('output', result)
        self.assertIn('error', result)
        self.assertIn('run_identifier', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test basic command execution
        args = RUN.parse_arguments(['OVERLEAF', 'test.tex'])
        self.assertEqual(args.command, 'OVERLEAF')
        self.assertEqual(args.args, ['test.tex'])
        
        # Test --show flag
        args = RUN.parse_arguments(['--show', 'OVERLEAF'])
        self.assertTrue(args.show)
        self.assertEqual(args.command, 'OVERLEAF')
        
        # Test --list flag
        args = RUN.parse_arguments(['--list'])
        self.assertTrue(args.list)
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    @patch('json.load')
    @patch('builtins.open')
    def test_load_tools_registry(self, mock_open, mock_json_load):
        """Test loading tools registry from bin.json"""
        mock_json_load.return_value = {
            'OVERLEAF': {'run_compatible': True},
            'EXTRACT_PDF': {'run_compatible': True}
        }
        
        tools = RUN.load_tools_registry()
        
        self.assertIn('OVERLEAF', tools)
        self.assertIn('EXTRACT_PDF', tools)
        mock_open.assert_called_once()
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_command_validation(self):
        """Test command validation against registry"""
        mock_tools = {
            'OVERLEAF': {'run_compatible': True},
            'EXTRACT_PDF': {'run_compatible': True},
            'INVALID_TOOL': {'run_compatible': False}
        }
        
        # Valid commands
        self.assertTrue(RUN.is_valid_command('OVERLEAF', mock_tools))
        self.assertTrue(RUN.is_valid_command('EXTRACT_PDF', mock_tools))
        
        # Invalid commands
        self.assertFalse(RUN.is_valid_command('INVALID_TOOL', mock_tools))
        self.assertFalse(RUN.is_valid_command('NONEXISTENT', mock_tools))
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    @patch('subprocess.run')
    def test_command_execution_success(self, mock_run):
        """Test successful command execution"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"success": true, "message": "Test successful"}',
            stderr=""
        )
        
        result = RUN.execute_command('OVERLEAF', ['test.tex'], 'test_run_id')
        
        self.assertTrue(result['success'])
        mock_run.assert_called_once()
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    @patch('subprocess.run')
    def test_command_execution_failure(self, mock_run):
        """Test failed command execution"""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Command failed"
        )
        
        result = RUN.execute_command('OVERLEAF', ['test.tex'], 'test_run_id')
        
        self.assertFalse(result['success'])
        self.assertIn('failed', result['message'].lower())
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_output_file_creation(self):
        """Test output file creation"""
        run_id = "test_run_123"
        output_file = RUN.get_output_file_path(run_id)
        
        self.assertTrue(output_file.endswith(f"run_{run_id}.json"))
        self.assertIn('RUN_DATA', output_file)
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['RUN.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    RUN.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()

class TestRUNIntegration(unittest.TestCase):
    """Integration tests for RUN tool"""
    
    def test_command_line_execution(self):
        """Test command line execution of RUN"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Execute bin tools', result.stdout)
    
    def test_list_functionality(self):
        """Test --list functionality"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--list'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        # Should list available tools
        self.assertIn('Available tools', result.stdout)

if __name__ == '__main__':
    unittest.main() 