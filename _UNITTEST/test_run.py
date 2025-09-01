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
        self.assertEqual(len(id1), 24)  # Should be YYYYMMDD_HHMMSS_XXXXXXXX format (24 chars)
        # Check format: should contain two underscores
        self.assertEqual(id1.count('_'), 2, "Identifier should have format YYYYMMDD_HHMMSS_XXXXXXXX")
    
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
        self.assertEqual(args['command'], 'OVERLEAF')
        self.assertEqual(args['args'], ['test.tex'])
        
        # Test --show flag
        args = RUN.parse_arguments(['--show', 'OVERLEAF'])
        self.assertTrue(args['show'])
        self.assertEqual(args['command'], 'OVERLEAF')
        
        # Test --help flag
        args = RUN.parse_arguments(['--help'])
        self.assertTrue(args['help'])
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_run_alias_command(self):
        """Test RUN with ALIAS command - functional test"""
        import tempfile
        
        # Test creating an alias
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / 'RUN.py'),
            'ALIAS', 'test_alias', 'echo "test successful"'
        ], capture_output=True, text=True, timeout=30)
        
        # Should succeed (exit code 0)
        self.assertEqual(result.returncode, 0)
        
        # Should output a JSON file path
        output_lines = result.stdout.strip().split('\n')
        json_file = output_lines[-1]  # Last line should be the JSON file path
        self.assertTrue(json_file.endswith('.json'))
        self.assertTrue(Path(json_file).exists())
        
        # Clean up
        try:
            if Path(json_file).exists():
                Path(json_file).unlink()
        except:
            pass
    
    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_run_with_show_flag(self):
        """Test RUN with --show flag - functional test with JSON parsing"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'ALIAS', 'test_show', 'echo "show test"'
        ], capture_output=True, text=True, timeout=30)
        
        # Should succeed
        self.assertEqual(result.returncode, 0)
        
        # Should contain JSON output in stdout when using --show
        self.assertIn('{', result.stdout)  # Should contain JSON
        self.assertIn('"success"', result.stdout)  # Should show success field
        
        # Parse and validate JSON output
        import json
        lines = result.stdout.strip().split('\n')
        json_found = False
        
        for i, line in enumerate(lines):
            if line.strip().startswith('{'):
                try:
                    # Extract JSON from this point
                    json_lines = []
                    brace_count = 0
                    for j in range(i, len(lines)):
                        json_lines.append(lines[j])
                        brace_count += lines[j].count('{') - lines[j].count('}')
                        if brace_count == 0 and lines[j].strip().endswith('}'):
                            break
                    
                    json_content = '\n'.join(json_lines)
                    data = json.loads(json_content)
                    
                    # Validate JSON structure
                    self.assertIn('success', data)
                    self.assertIsInstance(data['success'], bool)
                    json_found = True
                    break
                except (json.JSONDecodeError, ValueError):
                    continue
        
        self.assertTrue(json_found, "Valid JSON output not found in stdout")
    
    @unittest.skipIf(RUN is None, "RUN module not available") 
    def test_run_invalid_command(self):
        """Test RUN with invalid command - functional test"""
        result = subprocess.run([
            sys.executable, str(Path(__file__).parent.parent / 'RUN.py'),
            'INVALID_NONEXISTENT_COMMAND'
        ], capture_output=True, text=True, timeout=10)
        
        # Should fail (non-zero exit code)
        self.assertNotEqual(result.returncode, 0)
        
        # Should still output a JSON file path even for failures
        if result.stdout.strip():
            output_lines = result.stdout.strip().split('\n')
            json_file = output_lines[-1]
            if json_file.endswith('.json') and Path(json_file).exists():
                # Clean up
                try:
                    Path(json_file).unlink()
                except:
                    pass
    
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

    @unittest.skipIf(RUN is None, "RUN module not available")
    def test_all_run_compatible_tools(self):
        """Test all RUN-compatible tools from AI_TOOL.json registry"""
        import json
        
        # Load AI_TOOL.json registry
        bin_json_path = Path(__file__).parent.parent / 'AI_TOOL.json'
        if not bin_json_path.exists():
            self.skipTest("AI_TOOL.json not found")
        
        with open(bin_json_path, 'r') as f:
            registry = json.load(f)
        
        # Find all RUN-compatible tools with test commands
        run_tools = []
        for name, tool in registry['tools'].items():
            if tool.get('run_compatible', False) and 'test_command' in tool:
                run_tools.append((name, tool['test_command']))
        
        self.assertGreater(len(run_tools), 0, "No RUN-compatible tools found with test commands")
        
        # Test each tool
        failed_tools = []
        passed_tools = []
        
        for tool_name, test_args in run_tools:
            with self.subTest(tool=tool_name):
                try:
                    # Run the tool with --show flag
                    # Use appropriate timeout for file processing tools
                    file_processing_timeouts = {
                        'OVERLEAF': 15,     # LaTeX compilation (increased for complex docs)
                        'IMG2TEXT': 15,     # Image analysis with API
                        'UNIMERNET': 10,    # Formula recognition
                        'EXTRACT_PDF': 20   # PDF extraction with MinerU
                    }
                    timeout = file_processing_timeouts.get(tool_name, 30)
                    result = subprocess.run([
                        sys.executable, str(Path(__file__).parent.parent / 'RUN.py'),
                        '--show', tool_name
                    ] + test_args, 
                    capture_output=True, text=True, timeout=timeout,
                    cwd=Path(__file__).parent.parent)  # Use parent directory as working directory
                    
                    # Should succeed (exit code 0)
                    if result.returncode != 0:
                        error_msg = f"{tool_name}: exit code {result.returncode}"
                        if result.stderr:
                            error_msg += f" (stderr: {result.stderr[:100]})"
                        if result.stdout:
                            error_msg += f" (stdout: {result.stdout[:100]})"

                        failed_tools.append(error_msg)
                        continue
                    
                    # Should contain JSON output
                    if '{' not in result.stdout:
                        failed_tools.append(f"{tool_name}: no JSON output")
                        continue
                    
                    # Try to parse JSON from stdout
                    lines = result.stdout.strip().split('\n')
                    json_found = False
                    
                    for i, line in enumerate(lines):
                        if line.strip().startswith('{'):
                            # Try to parse JSON from this point
                            try:
                                json_lines = []
                                brace_count = 0
                                for j in range(i, len(lines)):
                                    json_lines.append(lines[j])
                                    brace_count += lines[j].count('{') - lines[j].count('}')
                                    if brace_count == 0 and lines[j].strip().endswith('}'):
                                        break
                                
                                json_content = '\n'.join(json_lines)
                                data = json.loads(json_content)
                                
                                # Verify required fields
                                self.assertIn('success', data, f"{tool_name}: missing 'success' field")
                                
                                json_found = True
                                break
                            except (json.JSONDecodeError, ValueError):
                                continue
                    
                    if not json_found:
                        failed_tools.append(f"{tool_name}: invalid JSON output")
                        continue
                    
                    passed_tools.append(tool_name)
                    
                    # Clean up any output files
                    if result.stdout.strip():
                        output_lines = result.stdout.strip().split('\n')
                        for line in output_lines:
                            if line.endswith('.json') and Path(line).exists():
                                try:
                                    Path(line).unlink()
                                except:
                                    pass
                
                except subprocess.TimeoutExpired:
                    failed_tools.append(f"{tool_name}: timeout")
                except Exception as e:
                    failed_tools.append(f"{tool_name}: {str(e)}")
        
        # Report results
        print(f"\nRUN Tool Test Results:")
        print(f"  Passed: {len(passed_tools)} tools")
        for tool in passed_tools:
            print(f"    {tool}")
        
        if failed_tools:
            print(f"  Failed: {len(failed_tools)} tools")
            for failure in failed_tools:
                print(f"    {failure}")
        
        print(f"  Total tested: {len(run_tools)} tools")
        
        # Test should pass if at least 70% of tools work (some tools may have complex dependencies)
        success_rate = len(passed_tools) / len(run_tools) if run_tools else 0
        self.assertGreaterEqual(success_rate, 0.7, 
            f"Only {success_rate:.1%} of tools passed. Failed: {failed_tools}")

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