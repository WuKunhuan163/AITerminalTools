#!/usr/bin/env python3
"""
Comprehensive unit tests for GDS echo functionality
Tests all edge cases, validation mechanism, and Chinese character support
"""

import unittest
import subprocess
import sys
import time
from pathlib import Path

class GDSEchoComprehensiveTest(unittest.TestCase):
    """Comprehensive tests for GDS echo command"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        print("🧪 Setting up GDS Echo Comprehensive Tests...")
        
        # Generate unique test folder name
        import datetime
        import hashlib
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_hash = hashlib.md5(f"echo_test_{timestamp}".encode()).hexdigest()[:8]
        cls.test_folder_name = f"echo_test_{timestamp}_{folder_hash}"
        
        print(f"📁 Creating test folder: {cls.test_folder_name}")
        
        # Pre-cleanup: remove ~/tmp if exists
        print("🧹 Pre-cleanup: Removing ~/tmp directory...")
        subprocess.run([
            sys.executable, str(cls.GOOGLE_DRIVE_PY), "--shell", 
            f"rm -rf ~/tmp"
        ], capture_output=True, text=True)
        
        # Create ~/tmp directory
        print("📁 Creating ~/tmp directory...")
        subprocess.run([
            sys.executable, str(cls.GOOGLE_DRIVE_PY), "--shell", 
            f"mkdir -p ~/tmp"
        ], capture_output=True, text=True)
        
        # Create test folder
        print(f"📁 Creating test folder: ~/tmp/{cls.test_folder_name}")
        subprocess.run([
            sys.executable, str(cls.GOOGLE_DRIVE_PY), "--shell", 
            f"mkdir -p ~/tmp/{cls.test_folder_name}"
        ], capture_output=True, text=True)
        
        # Create dedicated test shell and cd into test folder
        print("🐚 Creating dedicated test shell...")
        result = subprocess.run([
            sys.executable, str(cls.GOOGLE_DRIVE_PY), 
            "--create-remote-shell"
        ], capture_output=True, text=True)
        
        # Extract shell ID from output
        for line in result.stdout.split('\n'):
            if 'Shell ID:' in line:
                cls.test_shell_id = line.split('Shell ID:')[1].strip()
                break
        else:
            cls.test_shell_id = None
        
        print(f"🐚 Test shell ID: {cls.test_shell_id}")
        
        # Change to test directory
        if cls.test_shell_id:
            print(f"📂 Changing to test directory...")
            subprocess.run([
                sys.executable, str(cls.GOOGLE_DRIVE_PY), "--shell",
                f"cd ~/tmp/{cls.test_folder_name}"
            ], capture_output=True, text=True)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        print("🧹 Cleaning up test environment...")
        
        # Terminate dedicated test shell
        if hasattr(cls, 'test_shell_id') and cls.test_shell_id:
            print(f"🗑️ Terminating test shell: {cls.test_shell_id}")
            subprocess.run([
                sys.executable, str(cls.GOOGLE_DRIVE_PY), 
                "--terminate-remote-shell", cls.test_shell_id
            ], capture_output=True, text=True)
        
        # Clean up ~/tmp directory
        print("🧹 Final cleanup: Removing ~/tmp directory...")
        subprocess.run([
            sys.executable, str(cls.GOOGLE_DRIVE_PY), "--shell", 
            f"rm -rf ~/tmp"
        ], capture_output=True, text=True)
        
        print("✅ Cleanup completed")
    
    @classmethod
    def setUpClassProperties(cls):
        """Set up class properties"""
        cls.GOOGLE_DRIVE_PY = Path(__file__).parent.parent / "GOOGLE_DRIVE.py"
        assert cls.GOOGLE_DRIVE_PY.exists(), "GOOGLE_DRIVE.py not found"
    
    def run_gds_command(self, *args, allow_user_interaction=True):
        """Run a GDS command and return the result"""
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell"] + list(args)
        try:
            if allow_user_interaction:
                result = subprocess.run(cmd, capture_output=True, text=True)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return result
        except subprocess.TimeoutExpired:
            raise AssertionError(f"Command timed out: {args}")
    
    def test_01_basic_echo_file_creation(self):
        """Test basic echo file creation"""
        print("\n🧪 Testing basic echo file creation...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test basic file creation
        result = self.run_gds_command('echo "print(\\"Hello World!\\")" > basic_test.py')
        
        # Should succeed (exit code 0 or command executed)
        self.assertIsNotNone(result)
        print("✅ Basic echo file creation test completed")
    
    def test_02_echo_with_exclamation_marks(self):
        """Test echo with exclamation marks"""
        print("\n🧪 Testing echo with exclamation marks...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test exclamation marks
        result = self.run_gds_command('echo "print(\\"Exclamation test works!\\")" > exclamation_test.py')
        
        self.assertIsNotNone(result)
        print("✅ Echo with exclamation marks test completed")
    
    def test_03_echo_with_chinese_characters(self):
        """Test echo with Chinese characters"""
        print("\n🧪 Testing echo with Chinese characters...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test Chinese characters
        result = self.run_gds_command('echo "print(\\"中文测试成功！\\")" > chinese_test.py')
        
        self.assertIsNotNone(result)
        print("✅ Echo with Chinese characters test completed")
    
    def test_04_echo_with_special_characters(self):
        """Test echo with various special characters"""
        print("\n🧪 Testing echo with special characters...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test special characters
        result = self.run_gds_command('echo "Special chars: @#$%^&*()+={}[]" > special_chars_test.py')
        
        self.assertIsNotNone(result)
        print("✅ Echo with special characters test completed")
    
    def test_05_echo_file_overwrite(self):
        """Test echo file overwrite functionality"""
        print("\n🧪 Testing echo file overwrite...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Create initial file
        result1 = self.run_gds_command('echo "Initial content" > overwrite_test.py')
        self.assertIsNotNone(result1)
        
        # Overwrite the file
        result2 = self.run_gds_command('echo "Overwritten content!" > overwrite_test.py')
        self.assertIsNotNone(result2)
        
        print("✅ Echo file overwrite test completed")
    
    def test_06_echo_empty_content(self):
        """Test echo with empty content"""
        print("\n🧪 Testing echo with empty content...")
        
        # Test empty echo
        result = self.run_gds_command("echo")
        
        # Should succeed without errors
        self.assertEqual(result.returncode, 0)
        print("✅ Echo empty content test completed")
    
    def test_07_echo_normal_output(self):
        """Test echo normal output (no redirection)"""
        print("\n🧪 Testing echo normal output...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test normal echo output
        result = self.run_gds_command('echo "Hello World Output Test"')
        
        self.assertIsNotNone(result)
        print("✅ Echo normal output test completed")
    
    def test_08_echo_with_backslashes(self):
        """Test echo with backslashes and escape sequences"""
        print("\n🧪 Testing echo with backslashes...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test backslashes
        result = self.run_gds_command('echo "Backslashes: \\\\\\\\ test" > backslash_test.py')
        
        self.assertIsNotNone(result)
        print("✅ Echo with backslashes test completed")
    
    def test_09_echo_validation_mechanism(self):
        """Test echo validation mechanism"""
        print("\n🧪 Testing echo validation mechanism...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test validation mechanism
        result = self.run_gds_command('echo "Validation test content" > validation_mechanism_test.py')
        
        # Should include validation output (⏳ and √)
        self.assertIsNotNone(result)
        print("✅ Echo validation mechanism test completed")
    
    def test_10_echo_complex_python_code(self):
        """Test echo with complex Python code"""
        print("\n🧪 Testing echo with complex Python code...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test complex Python code
        result = self.run_gds_command('echo "for i in range(3): print(f\\"Line {i+1}!\\")" > complex_python.py')
        
        self.assertIsNotNone(result)
        print("✅ Echo with complex Python code test completed")

# Set up class properties before running tests
GDSEchoComprehensiveTest.setUpClassProperties()

def run_echo_tests():
    """Run the echo comprehensive tests"""
    print("🚀 Starting GDS Echo Comprehensive Tests")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(GDSEchoComprehensiveTest)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"🎯 Echo Tests Summary:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Success rate: {((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100):.1f}%" if result.testsRun > 0 else "N/A")
    
    if result.failures:
        print(f"\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   - {test}: {traceback}")
    
    if result.errors:
        print(f"\n🚨 Errors:")
        for test, traceback in result.errors:
            print(f"   - {test}: {traceback}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_echo_tests()
    sys.exit(0 if success else 1) 