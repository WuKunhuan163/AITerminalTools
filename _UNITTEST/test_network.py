#!/usr/bin/env python3
"""
Unit tests for NETWORK tool
"""
import unittest
import subprocess
import os
import sys
import json
import time


class TestNetworkTool(unittest.TestCase):
    """Test cases for NETWORK tool"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Find the NETWORK tool path
        cls.network_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'NETWORK')
        
        # Verify NETWORK tool exists
        if not os.path.exists(cls.network_path):
            raise FileNotFoundError(f"NETWORK tool not found at {cls.network_path}")

    def run_network_command(self, args, timeout=30):
        """Helper method to run NETWORK commands"""
        cmd = [self.network_path] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result
        except subprocess.TimeoutExpired:
            self.fail(f"Command {' '.join(cmd)} timed out after {timeout} seconds")
        except Exception as e:
            self.fail(f"Failed to run command {' '.join(cmd)}: {e}")

    def test_01_network_tool_exists(self):
        """Test that NETWORK tool exists and is accessible"""
        print("🧪 Test 01: NETWORK tool existence and accessibility")
        self.assertTrue(os.path.exists(self.network_path), "NETWORK tool should exist")
        self.assertTrue(os.access(self.network_path, os.R_OK), "NETWORK tool should be readable")

    def test_02_test_command(self):
        """Test the test command"""
        print("🧪 Test 02: NETWORK test command")
        result = self.run_network_command(['--test'])
        self.assertEqual(result.returncode, 0, f"Test command failed: {result.stderr}")
        self.assertIn("Network Test Results", result.stdout)

    def test_03_test_command_output_format(self):
        """Test that test command produces expected output format"""
        print("🧪 Test 03: NETWORK test command output format")
        result = self.run_network_command(['--test'], timeout=60)
        self.assertEqual(result.returncode, 0, f"Test command failed: {result.stderr}")
        
        # Should contain expected output elements
        self.assertIn("Testing network connection", result.stdout)
        self.assertIn("Network Test Results", result.stdout)
        self.assertIn("Latency:", result.stdout)
        self.assertIn("Download Speed:", result.stdout)
        self.assertIn("Upload Speed:", result.stdout)
        self.assertIn("ms", result.stdout)
        self.assertIn("Mbps", result.stdout)

    def test_04_network_data_file_creation(self):
        """Test that network test creates data file"""
        print("🧪 Test 04: Network data file creation")
        
        # Run test
        result = self.run_network_command(['--test'], timeout=60)
        self.assertEqual(result.returncode, 0, f"Test command failed: {result.stderr}")
        
        # Check if data file was created
        network_data_dir = os.path.join(os.path.dirname(self.network_path), "NETWORK_DATA")
        network_data_file = os.path.join(network_data_dir, "network_test_data.json")
        
        self.assertTrue(os.path.exists(network_data_file), "Network data file should be created")
        
        # Verify data file contains valid JSON
        try:
            with open(network_data_file, 'r') as f:
                data = json.load(f)
                
            # Should contain expected fields
            self.assertIn("timestamp", data)
            self.assertIn("status", data)
            
            if data["status"] == "success":
                self.assertIn("latency_ms", data)
                self.assertIn("download_speed_mbps", data)
                self.assertIn("upload_speed_mbps", data)
                
        except json.JSONDecodeError as e:
            self.fail(f"Network data file should contain valid JSON: {e}")

    def test_05_invalid_command(self):
        """Test handling of invalid commands"""
        print("🧪 Test 05: Invalid command handling")
        result = self.run_network_command(['invalid_command_xyz'])
        self.assertNotEqual(result.returncode, 0, "Invalid command should fail")
        # Should contain error message
        self.assertTrue(
            "Unknown option" in result.stdout or len(result.stderr) > 0,
            f"Invalid command should produce error message: stdout='{result.stdout}', stderr='{result.stderr}'"
        )

    def test_06_no_arguments(self):
        """Test behavior when no arguments are provided"""
        print("🧪 Test 06: No arguments handling")
        result = self.run_network_command([])
        self.assertNotEqual(result.returncode, 0, "Command without arguments should show usage and fail")
        # Should contain usage information
        self.assertTrue(
            any(keyword in result.stdout.lower() for keyword in ['usage', 'options', '--test']),
            f"Output should contain usage information: {result.stdout}"
        )

    def test_07_network_tester_class_interface(self):
        """Test NetworkTester class can be imported and used"""
        print("🧪 Test 07: NetworkTester class interface")
        
        # Test that we can import and use the NetworkTester class
        import sys
        sys.path.insert(0, os.path.dirname(self.network_path))
        
        try:
            from NETWORK import NetworkTester, network_test_interface, get_network_data_interface
            
            # Test the interface functions exist
            self.assertTrue(callable(network_test_interface), "network_test_interface should be callable")
            self.assertTrue(callable(get_network_data_interface), "get_network_data_interface should be callable")
            
            # Test NetworkTester class can be instantiated
            tester = NetworkTester()
            self.assertIsNotNone(tester, "NetworkTester should be instantiable")
            
        except ImportError as e:
            self.fail(f"Should be able to import NetworkTester: {e}")
        finally:
            sys.path.pop(0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
