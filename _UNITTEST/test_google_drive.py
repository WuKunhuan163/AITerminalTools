#!/usr/bin/env python3
"""
Unit tests for GOOGLE_DRIVE tool
Simple tests that verify basic functionality without requiring actual Google Drive access
"""

import unittest
import subprocess
import sys
import os
import tempfile
import json
from pathlib import Path

class TestGoogleDrive(unittest.TestCase):
    """Test cases for GOOGLE_DRIVE tool"""
    
    def setUp(self):
        """Set up test environment"""
        self.tool_path = Path(__file__).parent.parent / "GOOGLE_DRIVE.py"
        self.assertTrue(self.tool_path.exists(), "GOOGLE_DRIVE.py not found")
    
    def run_tool(self, args, timeout=10):
        """Helper method to run the GOOGLE_DRIVE tool with given arguments"""
        try:
            result = subprocess.run(
                [sys.executable, str(self.tool_path)] + args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result
        except subprocess.TimeoutExpired:
            self.fail(f"Tool execution timed out with args: {args}")
    
    def test_help_option(self):
        """Test --help option displays help information"""
        result = self.run_tool(["--help"])
        
        # Should return successfully (exit code 0)
        self.assertEqual(result.returncode, 0, "Help command should return exit code 0")
        
        # Should contain key information
        output = result.stdout.lower()
        self.assertIn("google drive", output, "Help should mention Google Drive")
        self.assertIn("usage", output, "Help should show usage information")
        self.assertIn("gds", output, "Help should mention GDS (Google Drive Shell)")
        self.assertIn("shell", output, "Help should mention shell functionality")
    
    def test_help_short_option(self):
        """Test -h option displays help information"""
        result = self.run_tool(["-h"])
        
        # Should return successfully (exit code 0)
        self.assertEqual(result.returncode, 0, "Short help command should return exit code 0")
        
        # Should contain key information
        output = result.stdout.lower()
        self.assertIn("google drive", output, "Help should mention Google Drive")
        self.assertIn("usage", output, "Help should show usage information")
    
    def test_invalid_arguments(self):
        """Test handling of invalid arguments"""
        result = self.run_tool(["--invalid-option"])
        
        # The tool treats unknown arguments as URLs and tries to open them
        # So it may return 0 (success) or 1 (failure) depending on browser availability
        # The important thing is that it doesn't crash
        self.assertIn(result.returncode, [0, 1], "Tool should handle invalid arguments gracefully")
    
    def test_shell_help_command(self):
        """Test shell help command"""
        result = self.run_tool(["--shell", "help"])
        
        # Should return successfully
        self.assertEqual(result.returncode, 0, "Shell help command should return exit code 0")
        
        # Should list available commands
        output = result.stdout.lower()
        expected_commands = ["pwd", "ls", "mkdir", "cd", "rm", "upload", "download"]
        for cmd in expected_commands:
            self.assertIn(cmd, output, f"Help should mention {cmd} command")
    
    def test_my_drive_option(self):
        """Test -my option (should attempt to open My Drive)"""
        # This test just verifies the option is recognized and processed
        # We can't test actual browser opening in unit tests
        result = self.run_tool(["-my"])
        
        # Should return successfully (even if browser opening fails in test environment)
        # The important thing is that the option is recognized
        self.assertIn(result.returncode, [0, 1], "My Drive option should be recognized")
    
    def test_desktop_status_option(self):
        """Test --desktop --status option"""
        result = self.run_tool(["--desktop", "--status"])
        
        # Should return some result (0 or 1 depending on Google Drive Desktop status)
        self.assertIn(result.returncode, [0, 1], "Desktop status command should return 0 or 1")
        
        # Should provide some output about status
        output = result.stdout + result.stderr
        self.assertTrue(len(output.strip()) > 0, "Desktop status should provide some output")
    
    def test_list_remote_shell(self):
        """Test --list-remote-shell option"""
        result = self.run_tool(["--list-remote-shell"])
        
        # Should return successfully
        self.assertEqual(result.returncode, 0, "List remote shell should return exit code 0")
        
        # Should provide information about shells (even if empty)
        output = result.stdout.lower()
        self.assertTrue(
            "shell" in output or "没有" in output or "not found" in output,
            "Should provide information about shell status"
        )
    
    def test_tool_structure(self):
        """Test that the tool has proper structure"""
        # Check that the Python file is executable
        self.assertTrue(os.access(self.tool_path, os.R_OK), "Tool should be readable")
        
        # Check that it has a main function or __main__ block
        with open(self.tool_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertTrue(
                'if __name__ == "__main__"' in content or 'def main(' in content,
                "Tool should have main function or __main__ block"
            )
    
    def test_run_environment_compatibility(self):
        """Test compatibility with RUN environment"""
        # Create a temporary RUN environment simulation
        with tempfile.TemporaryDirectory() as temp_dir:
            # Set up mock RUN environment variables
            env = os.environ.copy()
            test_id = "test_12345"
            output_file = os.path.join(temp_dir, "output.json")
            
            env[f'RUN_IDENTIFIER_{test_id}'] = 'True'
            env[f'RUN_DATA_FILE_{test_id}'] = output_file
            
            # Test help command in RUN environment
            result = subprocess.run(
                [sys.executable, str(self.tool_path), test_id, "--help"],
                capture_output=True,
                text=True,
                env=env,
                timeout=10
            )
            
            # Should return successfully
            self.assertEqual(result.returncode, 0, "RUN environment help should return exit code 0")
            
            # Should create output file
            self.assertTrue(os.path.exists(output_file), "RUN environment should create output file")
            
            # Output file should contain valid JSON
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.assertIsInstance(data, dict, "Output should be valid JSON object")
                    self.assertIn("success", data, "Output should contain success field")
            except json.JSONDecodeError:
                self.fail("Output file should contain valid JSON")

def run_tests():
    """Run all tests and return success status"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGoogleDrive)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2, buffer=True)
    result = runner.run(suite)
    
    # Return True if all tests passed
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 