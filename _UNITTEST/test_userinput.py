#!/usr/bin/env python3
"""
Unit tests for USERINPUT tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import USERINPUT
except ImportError:
    USERINPUT = None

class TestUSERINPUT(unittest.TestCase):
    """Test cases for USERINPUT tool"""
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(USERINPUT.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_DATA_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(USERINPUT.is_run_environment())
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = USERINPUT.create_json_output(
            success=True,
            message="User input collected successfully",
            user_input="test input from user",
            prompt="Enter your feedback:"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('user_input', result)
        self.assertIn('prompt', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test with custom prompt
        args = USERINPUT.parse_arguments(['--prompt', 'Custom prompt:'])
        self.assertEqual(args.prompt, 'Custom prompt:')
        
        # Test with timeout
        args = USERINPUT.parse_arguments(['--timeout', '30'])
        self.assertEqual(args.timeout, 30)
        
        # Test default arguments
        args = USERINPUT.parse_arguments([])
        self.assertEqual(args.prompt, 'Please provide your input:')  # default
        self.assertEqual(args.timeout, 60)  # default
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    @patch('builtins.input')
    def test_user_input_collection(self, mock_input):
        """Test user input collection"""
        mock_input.return_value = "test user input"
        
        result = USERINPUT.collect_user_input("Enter your feedback:")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['user_input'], "test user input")
        self.assertEqual(result['prompt'], "Enter your feedback:")
        mock_input.assert_called_once_with("Enter your feedback: ")
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    @patch('builtins.input')
    def test_empty_input_handling(self, mock_input):
        """Test handling of empty user input"""
        mock_input.return_value = ""
        
        result = USERINPUT.collect_user_input("Enter your feedback:")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['user_input'], "")
        self.assertIn('empty', result['message'].lower())
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    @patch('builtins.input')
    def test_input_timeout_simulation(self, mock_input):
        """Test input timeout simulation (mocked)"""
        mock_input.side_effect = KeyboardInterrupt()
        
        result = USERINPUT.collect_user_input("Enter your feedback:")
        
        self.assertFalse(result['success'])
        self.assertIn('interrupted', result['message'].lower())
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['USERINPUT.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    USERINPUT.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    @patch('builtins.input')
    def test_multiline_input_handling(self, mock_input):
        """Test handling of multiline input"""
        mock_input.return_value = "Line 1\nLine 2\nLine 3"
        
        result = USERINPUT.collect_user_input("Enter multiline input:")
        
        self.assertTrue(result['success'])
        self.assertIn('\n', result['user_input'])
        self.assertEqual(result['user_input'].count('\n'), 2)
    
    @unittest.skipIf(USERINPUT is None, "USERINPUT module not available")
    @patch('builtins.input')
    def test_special_characters_input(self, mock_input):
        """Test handling of special characters in input"""
        special_input = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        mock_input.return_value = special_input
        
        result = USERINPUT.collect_user_input("Enter special characters:")
        
        self.assertTrue(result['success'])
        self.assertEqual(result['user_input'], special_input)

class TestUSERINPUTIntegration(unittest.TestCase):
    """Integration tests for USERINPUT tool"""
    
    def test_command_line_execution(self):
        """Test command line execution of USERINPUT"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'USERINPUT.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Collect user input', result.stdout)
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'USERINPUT'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show USERINPUT did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 