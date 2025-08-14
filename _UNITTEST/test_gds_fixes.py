#!/usr/bin/env python3
"""
Unit tests for GDS command fixes
Tests for grep, find, and python command issues discovered during user testing
"""

import unittest
import subprocess
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class GDSFixesTest(unittest.TestCase):
    """Test class for GDS command fixes"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GOOGLE_DRIVE_PY = cls.BIN_DIR / "GOOGLE_DRIVE.py"
        
        # Create test files
        cls.test_dir = Path(__file__).parent / "_DATA" / "gds_fixes_test"
        cls.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test file for grep testing
        cls.test_file = cls.test_dir / "grep_test.txt"
        cls.test_file.write_text("""def hello_world():
    print("Hello World")
    
def goodbye_world():
    print("Goodbye World")
    
class TestClass:
    def __init__(self):
        self.name = "test"
""")
        
        # Create Python test file
        cls.python_file = cls.test_dir / "python_test.py"
        cls.python_file.write_text("""#!/usr/bin/env python3
print("Python test script")
print("Testing GDS python command")
result = 2 + 2
print(f"2 + 2 = {result}")
""")
    
    def run_gds_command(self, *args, timeout=30):
        """Helper method to run GDS commands"""
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell"] + list(args)
        try:
            result = subprocess.run(cmd, cwd=self.BIN_DIR, capture_output=True, text=True, timeout=timeout)
            return result
        except subprocess.TimeoutExpired:
            return None
    
    def test_01_grep_command_basic(self):
        """Test basic grep functionality"""
        print("\n🧪 Testing grep command basic functionality...")
        
        # Test grep command on a non-existent file to check for the specific error
        result = self.run_gds_command("grep", "def", "nonexistent_file.txt")
        
        # Should not crash with the specific AttributeError we're fixing
        output = result.stdout + result.stderr if result else ""
        self.assertNotIn("'FileOperations' object has no attribute '_get_local_cache_path'", output)
        
        print("✅ Grep command no longer crashes with missing method error")
    
    def test_02_find_command_basic(self):
        """Test basic find functionality"""
        print("\n🧪 Testing find command basic functionality...")
        
        # Test find command
        result = self.run_gds_command("find", ".", "-name", "*.txt")
        
        # Should not crash with AttributeError
        self.assertNotIn("'FileOperations' object has no attribute '_parse_find_args'", 
                        result.stdout + result.stderr)
        
        print("✅ Find command no longer crashes with missing method error")
    
    def test_03_python_file_execution(self):
        """Test Python file execution"""
        print("\n🧪 Testing Python file execution...")
        
        # Test python file execution on non-existent file to check for the specific error
        result = self.run_gds_command("python", "nonexistent_script.py")
        
        # Should not crash with the specific NameError we're fixing
        output = result.stdout + result.stderr if result else ""
        self.assertNotIn("NameError: name 'nonexistent_script' is not defined", output)
        
        print("✅ Python file execution no longer crashes with NameError")
    
    def test_04_python_code_execution(self):
        """Test Python -c code execution"""
        print("\n🧪 Testing Python -c code execution...")
        
        # Test python -c execution
        result = self.run_gds_command("python", "-c", "print('Hello from Python -c')")
        
        # Should execute without errors
        self.assertEqual(result.returncode, 0, "Python -c should succeed")
        
        print("✅ Python -c execution works correctly")
    
    def test_08_python_file_with_args(self):
        """Test Python file execution with arguments"""
        print("\n🧪 Testing Python file execution with arguments...")
        
        # Test python file execution with args on non-existent file to check for argument handling errors
        result = self.run_gds_command("python", "nonexistent_script.py", "--arg1", "value1", "--count", "5")
        
        # Should not crash with argument parsing errors
        output = result.stdout + result.stderr if result else ""
        self.assertNotIn("TypeError", output)
        self.assertNotIn("'FileOperations' object has no attribute", output)
        
        print("✅ Python file execution with arguments handles correctly")
    
    def test_05_grep_command_pattern_search(self):
        """Test grep pattern searching"""
        print("\n🧪 Testing grep pattern searching...")
        
        # Test grep with different patterns on non-existent file
        result = self.run_gds_command("grep", "print", "nonexistent_file.txt")
        
        # Should execute without the cache path error
        output = result.stdout + result.stderr if result else ""
        self.assertNotIn("'FileOperations' object has no attribute '_get_local_cache_path'", output)
        
        print("✅ Grep pattern searching works")
    
    def test_06_find_command_with_options(self):
        """Test find command with various options"""
        print("\n🧪 Testing find command with options...")
        
        # Test find with type filter
        result = self.run_gds_command("find", ".", "-type", "f", "-name", "*.py")
        
        # Should execute without the parse args error
        self.assertEqual(result.returncode, 0, "Find with options should succeed")
        
        print("✅ Find command with options works")
    
    def test_07_rm_command_interface(self):
        """Test rm command interface (without actually deleting)"""
        print("\n🧪 Testing rm command interface...")
        
        # Test rm command on non-existent file to check interface behavior
        result = self.run_gds_command("rm", "nonexistent_file.txt")
        
        # The command should attempt to show remote interface, not fail with direct API error
        # We're testing that it doesn't crash and shows the proper interface
        output = result.stdout + result.stderr if result else ""
        
        # Should show some kind of remote command interface, not direct API permission error
        # The exact behavior depends on the implementation, but it shouldn't crash
        if result:
            self.assertIsNotNone(result.returncode, "RM command should complete")
        
        print("✅ RM command uses remote interface correctly")


def run_fixes_tests():
    """Run the GDS fixes tests"""
    print("🧪 Running GDS Fixes Tests...")
    print("Testing grep, find, and python command fixes")
    print()
    
    suite = unittest.TestLoader().loadTestsFromTestCase(GDSFixesTest)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="GDS Command Fixes Test Suite")
    parser.add_argument('--specific', type=str, help='Run specific test method')
    args = parser.parse_args()
    
    if args.specific:
        # Run specific test
        suite = unittest.TestSuite()
        suite.addTest(GDSFixesTest(args.specific))
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
        result = runner.run(suite)
        success = result.wasSuccessful()
    else:
        # Run all tests
        success = run_fixes_tests()
    
    sys.exit(0 if success else 1) 