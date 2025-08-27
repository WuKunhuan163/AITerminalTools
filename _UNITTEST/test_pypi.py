#!/usr/bin/env python3
"""
Unit tests for PYPI tool
"""

import unittest
import subprocess
import json
import sys
import os

# Add the parent directory to the path so we can import PYPI
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PYPI import PyPIClient
    PYPI_MODULE_AVAILABLE = True
except ImportError:
    PYPI_MODULE_AVAILABLE = False


class TestPyPITool(unittest.TestCase):
    """Test cases for PYPI command-line tool"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.pypi_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'PYPI.py')
        cls.test_packages = ['requests', 'numpy', 'pandas']
        
    def _run_pypi_command(self, *args):
        """Helper method to run PYPI command and return result"""
        cmd = [sys.executable, self.pypi_path] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result
    
    def test_01_pypi_tool_exists(self):
        """Test that PYPI tool exists and is accessible"""
        print("\n🧪 Test 01: PYPI tool existence and accessibility")
        
        self.assertTrue(os.path.exists(self.pypi_path), "PYPI tool should exist")
        # For .py files, we check readability instead of executability
        self.assertTrue(os.access(self.pypi_path, os.R_OK), "PYPI tool should be readable")
    
    def test_02_test_command(self):
        """Test the test command"""
        print("\n🧪 Test 02: PYPI test command")
        
        result = self._run_pypi_command('test')
        
        self.assertEqual(result.returncode, 0, "Test command should succeed")
        self.assertIn("Testing PyPI API connection", result.stdout)
        self.assertIn("Test completed", result.stdout)
        
        # Should test at least the basic packages
        for pkg in ['requests', 'numpy', 'pandas']:
            self.assertIn(pkg, result.stdout, f"Should test {pkg} package")
    
    def test_03_info_command(self):
        """Test getting package information"""
        print("\n🧪 Test 03: PYPI info command")
        
        result = self._run_pypi_command('info', 'requests')
        
        self.assertEqual(result.returncode, 0, "Info command should succeed")
        self.assertIn("Name: requests", result.stdout)
        self.assertIn("Version:", result.stdout)
        self.assertIn("Summary:", result.stdout)
    
    def test_04_info_command_json(self):
        """Test getting package information in JSON format"""
        print("\n🧪 Test 04: PYPI info command with JSON output")
        
        result = self._run_pypi_command('info', 'requests', '--json')
        
        self.assertEqual(result.returncode, 0, "Info command with JSON should succeed")
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            self.assertIn('info', data)
            self.assertIn('name', data['info'])
            self.assertEqual(data['info']['name'], 'requests')
        except json.JSONDecodeError:
            self.fail("Output should be valid JSON")
    
    def test_05_deps_command(self):
        """Test getting package dependencies"""
        print("\n🧪 Test 05: PYPI deps command")
        
        result = self._run_pypi_command('deps', 'requests')
        
        self.assertEqual(result.returncode, 0, "Deps command should succeed")
        self.assertIn("Dependencies for requests:", result.stdout)
        
        # requests should have some common dependencies (note: PyPI uses underscores)
        expected_deps = ['urllib3', 'certifi', 'charset_normalizer', 'idna']
        for dep in expected_deps:
            self.assertIn(dep, result.stdout, f"Should list {dep} as dependency")
    
    def test_06_deps_command_json(self):
        """Test getting package dependencies in JSON format"""
        print("\n🧪 Test 06: PYPI deps command with JSON output")
        
        result = self._run_pypi_command('deps', 'requests', '--json')
        
        self.assertEqual(result.returncode, 0, "Deps command with JSON should succeed")
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            self.assertIn('package', data)
            self.assertIn('dependencies', data)
            self.assertEqual(data['package'], 'requests')
            self.assertIsInstance(data['dependencies'], list)
            self.assertGreater(len(data['dependencies']), 0, "Should have dependencies")
        except json.JSONDecodeError:
            self.fail("Output should be valid JSON")
    
    def test_07_size_command(self):
        """Test getting package size"""
        print("\n🧪 Test 07: PYPI size command")
        
        result = self._run_pypi_command('size', 'requests')
        
        self.assertEqual(result.returncode, 0, "Size command should succeed")
        self.assertIn("Size of requests:", result.stdout)
        self.assertIn("bytes", result.stdout)
    
    def test_08_size_command_json(self):
        """Test getting package size in JSON format"""
        print("\n🧪 Test 08: PYPI size command with JSON output")
        
        result = self._run_pypi_command('size', 'requests', '--json')
        
        self.assertEqual(result.returncode, 0, "Size command with JSON should succeed")
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            self.assertIn('package', data)
            self.assertIn('size', data)
            self.assertIn('formatted_size', data)
            self.assertEqual(data['package'], 'requests')
            self.assertIsInstance(data['size'], int)
            self.assertGreater(data['size'], 0, "Package should have positive size")
        except json.JSONDecodeError:
            self.fail("Output should be valid JSON")
    
    def test_09_metadata_command(self):
        """Test getting comprehensive package metadata"""
        print("\n🧪 Test 09: PYPI metadata command")
        
        result = self._run_pypi_command('metadata', 'requests')
        
        self.assertEqual(result.returncode, 0, "Metadata command should succeed")
        self.assertIn("Package: requests", result.stdout)
        self.assertIn("Version:", result.stdout)
        self.assertIn("Summary:", result.stdout)
        self.assertIn("Size:", result.stdout)
        self.assertIn("Dependencies", result.stdout)
    
    def test_10_metadata_command_json(self):
        """Test getting metadata in JSON format"""
        print("\n🧪 Test 10: PYPI metadata command with JSON output")
        
        result = self._run_pypi_command('metadata', 'requests', '--json')
        
        self.assertEqual(result.returncode, 0, "Metadata command with JSON should succeed")
        
        # Parse JSON output
        try:
            data = json.loads(result.stdout)
            required_fields = ['name', 'version', 'summary', 'size', 'dependencies']
            for field in required_fields:
                self.assertIn(field, data, f"Metadata should include {field}")
            
            self.assertEqual(data['name'], 'requests')
            self.assertIsInstance(data['dependencies'], list)
            self.assertIsInstance(data['size'], int)
        except json.JSONDecodeError:
            self.fail("Output should be valid JSON")
    
    def test_11_batch_command(self):
        """Test batch processing of multiple packages"""
        print("\n🧪 Test 11: PYPI batch command")
        
        result = self._run_pypi_command('batch', '--packages', 'requests', 'numpy')
        
        self.assertEqual(result.returncode, 0, "Batch command should succeed")
        self.assertIn("Processing 2 packages", result.stdout)
        self.assertIn("requests:", result.stdout)
        self.assertIn("numpy:", result.stdout)
    
    def test_12_batch_command_json(self):
        """Test batch processing with JSON output"""
        print("\n🧪 Test 12: PYPI batch command with JSON output")
        
        result = self._run_pypi_command('batch', '--packages', 'requests', 'numpy', '--json')
        
        self.assertEqual(result.returncode, 0, "Batch command with JSON should succeed")
        
        # Parse JSON output (ignore warning messages)
        try:
            # Find JSON part of output (after any warning messages)
            output_lines = result.stdout.strip().split('\n')
            json_start = -1
            for i, line in enumerate(output_lines):
                if line.strip().startswith('{'):
                    json_start = i
                    break
            
            if json_start >= 0:
                json_content = '\n'.join(output_lines[json_start:])
                data = json.loads(json_content)
                self.assertIn('requests', data)
                self.assertIn('numpy', data)
                
                for pkg in ['requests', 'numpy']:
                    self.assertIn('dependencies', data[pkg])
                    self.assertIn('size', data[pkg])
                    self.assertIn('formatted_size', data[pkg])
            else:
                self.fail("No JSON content found in output")
        except json.JSONDecodeError as e:
            self.fail(f"Output should be valid JSON: {e}\nOutput: {result.stdout}")
    
    def test_13_nonexistent_package(self):
        """Test handling of non-existent packages"""
        print("\n🧪 Test 13: Non-existent package handling")
        
        fake_package = 'this-package-definitely-does-not-exist-12345'
        result = self._run_pypi_command('info', fake_package)
        
        # Should handle gracefully, either with exit code 0 and "not found" message
        # or with non-zero exit code
        if result.returncode == 0:
            self.assertIn("not found", result.stdout.lower())
        else:
            # Non-zero exit code is also acceptable for non-existent packages
            pass
    
    def test_14_timeout_parameter(self):
        """Test custom timeout parameter"""
        print("\n🧪 Test 14: Custom timeout parameter")
        
        result = self._run_pypi_command('info', 'requests', '--timeout', '5')
        
        self.assertEqual(result.returncode, 0, "Command with custom timeout should succeed")
        self.assertIn("Name: requests", result.stdout)
    
    def test_15_workers_parameter(self):
        """Test custom workers parameter for batch operations"""
        print("\n🧪 Test 15: Custom workers parameter")
        
        result = self._run_pypi_command('batch', '--packages', 'requests', 'numpy', '--workers', '2')
        
        self.assertEqual(result.returncode, 0, "Batch command with custom workers should succeed")
        self.assertIn("requests:", result.stdout)
        self.assertIn("numpy:", result.stdout)


@unittest.skipUnless(PYPI_MODULE_AVAILABLE, "PYPI module not available")
class TestPyPIClient(unittest.TestCase):
    """Test cases for PyPIClient class"""
    
    def setUp(self):
        """Set up test client"""
        self.client = PyPIClient()
    
    def test_01_client_initialization(self):
        """Test client initialization"""
        print("\n🧪 Test 01: PyPIClient initialization")
        
        self.assertIsNotNone(self.client)
        self.assertEqual(self.client.timeout, 10)
        self.assertEqual(self.client.max_workers, 40)
    
    def test_02_get_package_info(self):
        """Test getting package information"""
        print("\n🧪 Test 02: Get package info")
        
        info = self.client.get_package_info('requests')
        
        self.assertIsNotNone(info)
        self.assertIn('info', info)
        self.assertEqual(info['info']['name'], 'requests')
    
    def test_03_get_package_dependencies(self):
        """Test getting package dependencies"""
        print("\n🧪 Test 03: Get package dependencies")
        
        deps = self.client.get_package_dependencies('requests')
        
        self.assertIsNotNone(deps)
        self.assertIsInstance(deps, list)
        self.assertGreater(len(deps), 0, "requests should have dependencies")
        
        # Check for common dependencies
        expected_deps = ['urllib3', 'certifi']
        for dep in expected_deps:
            self.assertIn(dep, deps, f"Should include {dep}")
    
    def test_04_get_package_size(self):
        """Test getting package size"""
        print("\n🧪 Test 04: Get package size")
        
        size = self.client.get_package_size('requests')
        
        self.assertIsInstance(size, int)
        self.assertGreater(size, 0, "requests should have positive size")
    
    def test_05_get_package_dependencies_with_size(self):
        """Test getting both dependencies and size"""
        print("\n🧪 Test 05: Get dependencies with size")
        
        deps, size = self.client.get_package_dependencies_with_size('requests')
        
        self.assertIsNotNone(deps)
        self.assertIsInstance(deps, list)
        self.assertGreater(len(deps), 0, "Should have dependencies")
        self.assertIsInstance(size, int)
        self.assertGreater(size, 0, "Should have positive size")
    
    def test_06_get_package_metadata(self):
        """Test getting comprehensive metadata"""
        print("\n🧪 Test 06: Get package metadata")
        
        metadata = self.client.get_package_metadata('requests')
        
        self.assertIsNotNone(metadata)
        required_fields = ['name', 'version', 'summary', 'size', 'dependencies']
        for field in required_fields:
            self.assertIn(field, metadata, f"Metadata should include {field}")
        
        self.assertEqual(metadata['name'], 'requests')
        self.assertIsInstance(metadata['dependencies'], list)
        self.assertIsInstance(metadata['size'], int)
    
    def test_07_batch_get_dependencies_with_sizes(self):
        """Test batch operations"""
        print("\n🧪 Test 07: Batch get dependencies with sizes")
        
        packages = ['requests', 'numpy']
        results = self.client.batch_get_dependencies_with_sizes(packages)
        
        self.assertEqual(len(results), 2)
        for pkg in packages:
            self.assertIn(pkg, results)
            deps, size = results[pkg]
            self.assertIsNotNone(deps)
            self.assertIsInstance(size, int)
    
    def test_08_nonexistent_package(self):
        """Test handling of non-existent packages"""
        print("\n🧪 Test 08: Non-existent package handling in client")
        
        fake_package = 'this-package-definitely-does-not-exist-12345'
        
        # Should return None for non-existent packages
        info = self.client.get_package_info(fake_package)
        self.assertIsNone(info)
        
        deps = self.client.get_package_dependencies(fake_package)
        self.assertIsNone(deps)
        
        size = self.client.get_package_size(fake_package)
        self.assertEqual(size, 0)
        
        deps, size = self.client.get_package_dependencies_with_size(fake_package)
        self.assertIsNone(deps)
        self.assertEqual(size, 0)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
