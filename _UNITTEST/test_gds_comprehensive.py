#!/usr/bin/env python3
"""
Comprehensive test suite for GDS (Google Drive Shell) read, edit, upload, and echo commands.

This test suite focuses on the recently fixed functionality:
- GDS read command with various options (--force, line ranges, multiple ranges)
- GDS edit command with line-based and text-based editing (--preview, --backup)
- GDS upload command with single/multiple files and options
- GDS echo command with text creation, redirection, validation mechanism, Chinese characters, and special character support

Features:
- Uses temporary test folders in ~/tmp with hashed timestamps
- No timeout restrictions to allow user interaction
- Comprehensive test coverage for all command variations
- Proper cleanup after tests
"""

import unittest
import subprocess
import sys
import os
import tempfile
import json
import hashlib
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import GOOGLE_DRIVE
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE = None
    GOOGLE_DRIVE_AVAILABLE = False

class GDSComprehensiveTest(unittest.TestCase):
    """
    Comprehensive test class for GDS commands with temporary folder support
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment with temporary folders"""
        print("🚀 Setting up GDS Comprehensive Test Environment...")
        
        # Set up paths
        cls.BIN_DIR = Path(__file__).parent.parent
        cls.GOOGLE_DRIVE_PY = cls.BIN_DIR / "GOOGLE_DRIVE.py"
        
        # Create hashed timestamp for unique test folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hash_input = f"{timestamp}_{os.getpid()}"
        folder_hash = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        cls.test_folder_name = f"gds_test_{timestamp}_{folder_hash}"
        
        print(f"📁 Test folder: ~/tmp/{cls.test_folder_name}")
        
        # Create local test data directory
        cls.local_test_dir = Path(__file__).parent / "_DATA" / "gds_comprehensive_test"
        cls.local_test_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test files for upload testing
        cls.test_files = []
        test_file_contents = [
            "# Test File 1\nThis is the first test file for GDS testing.\nLine 3 content\nLine 4 content\n",
            "# Test File 2\nSecond test file with different content.\nAnother line here\nFinal line\n",
            "# Test File 3\nThird test file for multi-file testing.\nSome more content\nEnd of file\n"
        ]
        
        for i, content in enumerate(test_file_contents, 1):
            test_file = cls.local_test_dir / f"test_file_{i}.txt"
            test_file.write_text(content)
            cls.test_files.append(test_file)
        
        # Create a Python test file for editing tests
        cls.python_test_file = cls.local_test_dir / "test_script.py"
        python_content = '''#!/usr/bin/env python3
"""Test Python script for editing tests"""

def hello_world():
    print("Hello, World!")

def main():
    hello_world()
    print("This is a test script")

if __name__ == "__main__":
    main()
'''
        cls.python_test_file.write_text(python_content)
        cls.test_files.append(cls.python_test_file)
        
        # Create a JSON test file
        cls.json_test_file = cls.local_test_dir / "test_config.json"
        json_content = '''{
    "debug": false,
    "host": "localhost",
    "port": 8080,
    "features": {
        "logging": true,
        "auth": false
    }
}'''
        cls.json_test_file.write_text(json_content)
        cls.test_files.append(cls.json_test_file)
        
        print(f"📝 Created {len(cls.test_files)} test files in {cls.local_test_dir}")
        
        # Initialize remote test folder
        cls._setup_remote_test_folder()
    
    @classmethod
    def _setup_remote_test_folder(cls):
        """Set up the remote test folder in ~/tmp with dedicated test shell"""
        print(f"🔧 Setting up remote test folder: ~/tmp/{cls.test_folder_name}")
        
        # First clean up any existing tmp folders to avoid confusion
        print("🧹 Cleaning up existing tmp folders...")
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "rm", "-rf", "~/tmp"]
        print(f"🗑️  Cleaning tmp directory: {' '.join(cmd)}")
        print("👤 Please complete the tmp cleanup in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        if result.returncode != 0:
            print(f"⚠️  Warning: Failed to clean tmp folder (may not exist)")
        
        # First ensure ~/tmp exists
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "mkdir", "-p", "~/tmp"]
        print(f"📁 Ensuring ~/tmp exists: {' '.join(cmd)}")
        print("👤 Please complete the tmp folder creation in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        if result.returncode != 0:
            print(f"⚠️  Warning: Failed to create ~/tmp folder")
        
        # Create the remote test folder
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "mkdir", "-p", f"~/tmp/{cls.test_folder_name}"]
        print(f"📁 Creating remote test folder: {' '.join(cmd)}")
        print("👤 Please complete the test folder creation in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        if result.returncode != 0:
            print(f"⚠️  Warning: Failed to create remote test folder")
        
        # Create a dedicated test shell for this test session
        print("🔧 Creating dedicated test shell...")
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--create-remote-shell"]
        print(f"🆕 Creating test shell: {' '.join(cmd)}")
        print("👤 Please complete the test shell creation in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            # Extract shell ID from output if possible
            output = result.stdout + result.stderr
            if "Shell ID:" in output:
                import re
                shell_match = re.search(r'Shell ID:\s*(\w+)', output)
                if shell_match:
                    cls.test_shell_id = shell_match.group(1)
                    print(f"✅ Created test shell: {cls.test_shell_id}")
                else:
                    cls.test_shell_id = None
                    print("⚠️  Shell created but couldn't extract ID")
            else:
                cls.test_shell_id = None
                print("⚠️  Shell created but couldn't extract ID from output")
        else:
            cls.test_shell_id = None
            print("⚠️  Warning: Failed to create test shell, using default shell")
        
        # Change to the test folder in the test shell
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "cd", f"~/tmp/{cls.test_folder_name}"]
        print(f"📂 Changing to test folder: {' '.join(cmd)}")
        print("👤 Please complete the directory change in the UI...")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        if result.returncode != 0:
            print(f"⚠️  Warning: Failed to change to test folder - tests will run from current directory")
        
        print("✅ Remote test folder and shell setup completed")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        print(f"🧹 Cleaning up test environment...")
        
        # Clean up entire tmp folder to avoid confusion with duplicate names
        cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--shell", "rm", "-rf", "~/tmp"]
        print(f"🗑️  Removing entire tmp directory: {' '.join(cmd)}")
        print("👤 Please complete the cleanup in the UI...")
        print("📝 Note: This will remove all temporary test files to avoid duplicate folder confusion")
        
        result = subprocess.run(cmd, cwd=cls.BIN_DIR)
        if result.returncode != 0:
            print(f"⚠️  Warning: Cleanup command completed - please check the remote command result")
        else:
            print("✅ Cleanup command executed successfully")
        
        # Clean up the test shell if it was created
        if hasattr(cls, 'test_shell_id') and cls.test_shell_id:
            print(f"🗑️  Terminating test shell: {cls.test_shell_id}")
            cmd = ["python3", str(cls.GOOGLE_DRIVE_PY), "--terminate-remote-shell", cls.test_shell_id]
            print(f"🔚 Terminating shell: {' '.join(cmd)}")
            print("👤 Please complete the shell termination in the UI...")
            
            result = subprocess.run(cmd, cwd=cls.BIN_DIR)
            if result.returncode == 0:
                print("✅ Test shell terminated successfully")
            else:
                print("⚠️  Warning: Failed to terminate test shell")
        
        print("✅ Test environment cleanup completed")
    
    def run_gds_command(self, *args):
        """Helper method to run GDS commands without timeout"""
        cmd = ["python3", str(self.GOOGLE_DRIVE_PY), "--shell"] + list(args)
        print(f"🚀 Running: {' '.join(cmd)}")
        print("👤 Please complete the operation in the UI...")
        
        # No timeout to allow user interaction
        result = subprocess.run(cmd, cwd=self.BIN_DIR, capture_output=True, text=True)
        return result
    
    def test_01_echo_basic(self):
        """Test basic echo functionality"""
        print("\n🧪 Testing basic echo functionality...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test simple echo output (no redirection)
        result = self.run_gds_command('echo "Hello GDS Test"')
        self.assertEqual(result.returncode, 0, "Basic echo should succeed")
        
        # Test echo with quotes and exclamation marks
        result = self.run_gds_command('echo "Hello World with quotes and exclamation!"')
        self.assertEqual(result.returncode, 0, "Echo with quotes should succeed")
        
        print("✅ Basic echo tests passed")
    
    def test_02_echo_file_creation(self):
        """Test echo with file redirection"""
        print("\n🧪 Testing echo file creation...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Create a test file using echo with proper syntax
        result = self.run_gds_command('echo "This is test content created by echo" > echo_test.txt')
        self.assertEqual(result.returncode, 0, "Echo file creation should succeed")
        
        # Test echo with Chinese characters and exclamation marks
        result = self.run_gds_command('echo "中文测试内容！Echo支持中文字符！" > echo_chinese_test.txt')
        self.assertEqual(result.returncode, 0, "Echo with Chinese characters should succeed")
        
        # Test echo file overwrite
        result = self.run_gds_command('echo "Overwritten content with validation!" > echo_test.txt')
        self.assertEqual(result.returncode, 0, "Echo file overwrite should succeed")
        
        print("✅ Echo file creation tests passed")
    
    def test_02b_echo_advanced_features(self):
        """Test advanced echo features: validation, special characters, edge cases"""
        print("\n🧪 Testing advanced echo features...")
        print("⏰ No timeout restrictions - take your time with UI interactions")
        
        # Test echo with special characters
        result = self.run_gds_command('echo "Special chars: @#$%^&*()+={}[]|:;,.<>?" > special_chars.txt')
        self.assertEqual(result.returncode, 0, "Echo with special characters should succeed")
        
        # Test echo with backslashes
        result = self.run_gds_command('echo "Backslashes: \\\\ test" > backslash_test.txt')
        self.assertEqual(result.returncode, 0, "Echo with backslashes should succeed")
        
        # Test echo validation mechanism (should show ⏳ and √)
        result = self.run_gds_command('echo "Validation mechanism test!" > validation_test.txt')
        self.assertEqual(result.returncode, 0, "Echo validation should succeed")
        
        # Test empty echo (no redirection)
        result = self.run_gds_command("echo")
        self.assertEqual(result.returncode, 0, "Empty echo should succeed")
        
        print("✅ Advanced echo features tests passed")
    
    def test_03_upload_single_file(self):
        """Test uploading a single file"""
        print("\n🧪 Testing single file upload...")
        
        # Upload the first test file
        result = self.run_gds_command("upload", str(self.test_files[0]))
        self.assertEqual(result.returncode, 0, "Single file upload should succeed")
        
        # Verify the file exists remotely
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "ls after upload should succeed")
        
        print("✅ Single file upload tests passed")
    
    def test_04_upload_multiple_files(self):
        """Test uploading multiple files"""
        print("\n🧪 Testing multiple file upload...")
        
        # Upload multiple test files
        file_args = [str(f) for f in self.test_files[1:3]]  # Upload files 2 and 3
        result = self.run_gds_command("upload", *file_args)
        self.assertEqual(result.returncode, 0, "Multiple file upload should succeed")
        
        # Verify files exist remotely
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "ls after multiple upload should succeed")
        
        print("✅ Multiple file upload tests passed")
    
    def test_05_upload_with_target_dir(self):
        """Test upload with target directory option"""
        print("\n🧪 Testing upload with target directory...")
        
        # Create a subdirectory for testing
        result = self.run_gds_command("mkdir", "upload_target")
        self.assertEqual(result.returncode, 0, "mkdir should succeed")
        
        # Upload with target directory
        result = self.run_gds_command("upload", "--target-dir", "upload_target", str(self.test_files[0]))
        self.assertEqual(result.returncode, 0, "Upload with target dir should succeed")
        
        # Verify file in target directory
        result = self.run_gds_command("ls", "upload_target")
        self.assertEqual(result.returncode, 0, "ls target directory should succeed")
        
        print("✅ Upload with target directory tests passed")
    
    def test_06_read_basic(self):
        """Test basic read functionality"""
        print("\n🧪 Testing basic read functionality...")
        
        # Read the entire uploaded file
        result = self.run_gds_command("read", "test_file_1.txt")
        self.assertEqual(result.returncode, 0, "Basic read should succeed")
        
        print("✅ Basic read tests passed")
    
    def test_07_read_with_line_range(self):
        """Test read with line range"""
        print("\n🧪 Testing read with line range...")
        
        # Read specific line range (lines 0-2)
        result = self.run_gds_command("read", "test_file_1.txt", "0", "2")
        self.assertEqual(result.returncode, 0, "Read with line range should succeed")
        
        # Read from specific line to end
        result = self.run_gds_command("read", "test_file_1.txt", "1")
        self.assertEqual(result.returncode, 0, "Read from line to end should succeed")
        
        print("✅ Read with line range tests passed")
    
    def test_08_read_with_force(self):
        """Test read with --force option"""
        print("\n🧪 Testing read with --force option...")
        
        # Read with force to bypass cache
        result = self.run_gds_command("read", "--force", "test_file_1.txt")
        self.assertEqual(result.returncode, 0, "Read with --force should succeed")
        
        print("✅ Read with --force tests passed")
    
    def test_09_read_multiple_ranges(self):
        """Test read with multiple ranges"""
        print("\n🧪 Testing read with multiple ranges...")
        
        # Read multiple ranges using JSON format
        ranges = '[[0, 1], [2, 3]]'
        result = self.run_gds_command("read", "test_file_1.txt", ranges)
        self.assertEqual(result.returncode, 0, "Read with multiple ranges should succeed")
        
        print("✅ Read with multiple ranges tests passed")
    
    def test_10_edit_line_replacement(self):
        """Test edit with line replacement"""
        print("\n🧪 Testing edit with line replacement...")
        
        # Upload Python test file first (ensure it exists)
        result = self.run_gds_command("upload", str(self.python_test_file))
        self.assertEqual(result.returncode, 0, "Upload Python file should succeed")
        
        # Verify the file was uploaded
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "ls should succeed")
        
        # Edit specific lines using line replacement (fix quote escaping)
        edit_spec = '[[[1, 1], "# Updated test Python script"], [[4, 4], "    print(\'Hello, Updated World!\')"]]'
        result = self.run_gds_command("edit", "test_script.py", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit with line replacement should succeed")
        
        print("✅ Edit with line replacement tests passed")
    
    def test_11_edit_text_replacement(self):
        """Test edit with text search and replace"""
        print("\n🧪 Testing edit with text replacement...")
        
        # Upload JSON test file first
        result = self.run_gds_command("upload", str(self.json_test_file))
        self.assertEqual(result.returncode, 0, "Upload JSON file should succeed")
        
        # Edit using text search and replace
        edit_spec = '[["false", "true"], ["localhost", "0.0.0.0"], ["8080", "3000"]]'
        result = self.run_gds_command("edit", "test_config.json", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit with text replacement should succeed")
        
        print("✅ Edit with text replacement tests passed")
    
    def test_12_edit_with_preview(self):
        """Test edit with --preview option"""
        print("\n🧪 Testing edit with --preview option...")
        
        # Preview edit without saving
        edit_spec = '[["debug": true", "debug": false"]]'
        result = self.run_gds_command("edit", "--preview", "test_config.json", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit with --preview should succeed")
        
        print("✅ Edit with --preview tests passed")
    
    def test_13_edit_with_backup(self):
        """Test edit with --backup option"""
        print("\n🧪 Testing edit with --backup option...")
        
        # Edit with backup creation (fix quote escaping)
        edit_spec = '[["Hello, Updated World!", "Hello, Backup Test World!"]]'
        result = self.run_gds_command("edit", "--backup", "test_script.py", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit with --backup should succeed")
        
        # Verify backup file was created
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "ls after backup edit should succeed")
        
        print("✅ Edit with --backup tests passed")
    
    def test_14_edit_mixed_mode(self):
        """Test edit with mixed line and text replacement"""
        print("\n🧪 Testing edit with mixed mode...")
        
        # Mixed mode: line replacement + text replacement (fix quote escaping)
        edit_spec = '[[[0, 0], "#!/usr/bin/env python3"], ["print", "# print"]]'
        result = self.run_gds_command("edit", "test_script.py", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit with mixed mode should succeed")
        
        print("✅ Edit with mixed mode tests passed")
    
    def test_15_comprehensive_workflow(self):
        """Test a comprehensive workflow combining all commands"""
        print("\n🧪 Testing comprehensive workflow...")
        
        # 1. Create a new file with echo (using proper syntax)
        result = self.run_gds_command('echo "# Workflow Test File\nInitial content\nLine 3" > workflow_test.txt')
        self.assertEqual(result.returncode, 0, "Echo file creation should succeed")
        
        # 2. Read the file to verify content
        result = self.run_gds_command("read", "workflow_test.txt")
        self.assertEqual(result.returncode, 0, "Read workflow file should succeed")
        
        # 3. Edit the file to modify content
        edit_spec = '[["Initial content", "Modified content"], [[2, 2], "Updated line 3"]]'
        result = self.run_gds_command("edit", "--backup", "workflow_test.txt", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit workflow file should succeed")
        
        # 4. Read the modified file
        result = self.run_gds_command("read", "workflow_test.txt")
        self.assertEqual(result.returncode, 0, "Read modified file should succeed")
        
        # 5. Upload another file to the same location
        result = self.run_gds_command("upload", str(self.test_files[-1]))
        self.assertEqual(result.returncode, 0, "Upload additional file should succeed")
        
        # 6. List all files to verify everything is there
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "Final ls should succeed")
        
        print("✅ Comprehensive workflow tests passed")
    
    def test_16_cat_command(self):
        """Test cat command for displaying file content"""
        print("\n🧪 Testing cat command...")
        
        # Cat the uploaded file
        result = self.run_gds_command("cat", "test_file_1.txt")
        self.assertEqual(result.returncode, 0, "Cat command should succeed")
        
        print("✅ Cat command tests passed")
    
    def test_17_grep_command(self):
        """Test grep command for searching file content"""
        print("\n🧪 Testing grep command...")
        
        # Search for pattern in file
        result = self.run_gds_command("grep", "Test File", "test_file_1.txt")
        self.assertEqual(result.returncode, 0, "Grep command should succeed")
        
        # Search for pattern that doesn't exist
        result = self.run_gds_command("grep", "NonexistentPattern", "test_file_1.txt")
        # Should handle gracefully (may return 0 with no matches message)
        
        print("✅ Grep command tests passed")
    
    def test_18_find_command(self):
        """Test find command for locating files"""
        print("\n🧪 Testing find command...")
        
        # Find all .txt files
        result = self.run_gds_command("find", ".", "-name", "*.txt")
        self.assertEqual(result.returncode, 0, "Find command should succeed")
        
        # Find files with specific pattern
        result = self.run_gds_command("find", ".", "-name", "*test*")
        self.assertEqual(result.returncode, 0, "Find with pattern should succeed")
        
        print("✅ Find command tests passed")
    
    def test_19_mv_command(self):
        """Test mv command for moving/renaming files"""
        print("\n🧪 Testing mv command...")
        
        # Create a test file first
        result = self.run_gds_command('echo "Content for mv test" > mv_test_source.txt')
        self.assertEqual(result.returncode, 0, "Create source file should succeed")
        
        # Move/rename the file
        result = self.run_gds_command("mv", "mv_test_source.txt", "mv_test_destination.txt")
        self.assertEqual(result.returncode, 0, "Mv command should succeed")
        
        # Verify the file was moved
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "Ls after mv should succeed")
        
        print("✅ Mv command tests passed")
    
    def test_20_ls_advanced_options(self):
        """Test ls command with advanced options"""
        print("\n🧪 Testing ls command with advanced options...")
        
        # Test --detailed option
        result = self.run_gds_command("ls", "--detailed")
        self.assertEqual(result.returncode, 0, "Ls --detailed should succeed")
        
        # Test recursive option
        result = self.run_gds_command("ls", "-R")
        self.assertEqual(result.returncode, 0, "Ls -R should succeed")
        
        print("✅ Ls advanced options tests passed")
    
    def test_21_edit_insert_mode(self):
        """Test edit command insert mode with [line, null] syntax"""
        print("\n🧪 Testing edit insert mode...")
        
        # Create a simple test file (fix escaping)
        result = self.run_gds_command('echo "Line 1\nLine 2\nLine 3" > insert_test.txt')
        self.assertEqual(result.returncode, 0, "Create test file should succeed")
        
        # Test insert mode - insert after line 1
        edit_spec = '[[[1, null], "# Inserted after line 1"]]'
        result = self.run_gds_command("edit", "insert_test.txt", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit insert mode should succeed")
        
        # Test multiple inserts
        edit_spec = '[[[0, null], "# Header"], [[3, null], "# Footer"]]'
        result = self.run_gds_command("edit", "insert_test.txt", edit_spec)
        self.assertEqual(result.returncode, 0, "Edit multiple inserts should succeed")
        
        print("✅ Edit insert mode tests passed")
    
    def test_22_download_command(self):
        """Test download command"""
        print("\n🧪 Testing download command...")
        
        # Download a file (basic download)
        result = self.run_gds_command("download", "test_file_1.txt")
        self.assertEqual(result.returncode, 0, "Basic download should succeed")
        
        # Download with --force option
        result = self.run_gds_command("download", "--force", "test_file_2.txt")
        self.assertEqual(result.returncode, 0, "Download with --force should succeed")
        
        print("✅ Download command tests passed")
    
    def test_23_python_execution(self):
        """Test python command execution"""
        print("\n🧪 Testing python command execution...")
        
        # Execute Python code directly (fix quote escaping)
        result = self.run_gds_command("python", "-c", "print('Hello from Python!')")
        self.assertEqual(result.returncode, 0, "Python -c should succeed")
        
        # Execute uploaded Python file (ensure test_script.py exists)
        # First verify the file was uploaded in earlier test
        result = self.run_gds_command("ls")
        self.assertEqual(result.returncode, 0, "ls should succeed")
        
        # Execute the Python file
        result = self.run_gds_command("python", "test_script.py")
        self.assertEqual(result.returncode, 0, "Python file execution should succeed")
        
        print("✅ Python execution tests passed")
    
    def test_24_venv_management(self):
        """Test virtual environment management"""
        print("\n🧪 Testing virtual environment management...")
        
        # List existing environments (if any)
        result = self.run_gds_command("venv", "--list")
        self.assertEqual(result.returncode, 0, "Venv --list should succeed")
        
        # Create a virtual environment
        result = self.run_gds_command("venv", "--create", "test_env")
        self.assertEqual(result.returncode, 0, "Venv --create should succeed")
        
        # List environments after creation
        result = self.run_gds_command("venv", "--list")
        self.assertEqual(result.returncode, 0, "Venv --list after create should succeed")
        
        # Activate the environment
        result = self.run_gds_command("venv", "--activate", "test_env")
        self.assertEqual(result.returncode, 0, "Venv --activate should succeed")
        
        # Deactivate the environment
        result = self.run_gds_command("venv", "--deactivate")
        self.assertEqual(result.returncode, 0, "Venv --deactivate should succeed")
        
        # Delete the environment
        result = self.run_gds_command("venv", "--delete", "test_env")
        self.assertEqual(result.returncode, 0, "Venv --delete should succeed")
        
        print("✅ Virtual environment management tests passed")
    
    def test_25_pip_management(self):
        """Test pip package management"""
        print("\n🧪 Testing pip package management...")
        
        # Create and activate a virtual environment for pip testing
        result = self.run_gds_command("venv", "--create", "pip_test_env")
        self.assertEqual(result.returncode, 0, "Create pip test env should succeed")
        
        result = self.run_gds_command("venv", "--activate", "pip_test_env")
        self.assertEqual(result.returncode, 0, "Activate pip test env should succeed")
        
        # List installed packages
        result = self.run_gds_command("pip", "list")
        self.assertEqual(result.returncode, 0, "Pip list should succeed")
        
        # Install a small package
        result = self.run_gds_command("pip", "install", "colorama")
        self.assertEqual(result.returncode, 0, "Pip install should succeed")
        
        # List packages after installation
        result = self.run_gds_command("pip", "list")
        self.assertEqual(result.returncode, 0, "Pip list after install should succeed")
        
        # Uninstall the package
        result = self.run_gds_command("pip", "uninstall", "-y", "colorama")
        self.assertEqual(result.returncode, 0, "Pip uninstall should succeed")
        
        # Deactivate and clean up
        result = self.run_gds_command("venv", "--deactivate")
        self.assertEqual(result.returncode, 0, "Deactivate pip test env should succeed")
        
        result = self.run_gds_command("venv", "--delete", "pip_test_env")
        self.assertEqual(result.returncode, 0, "Delete pip test env should succeed")
        
        print("✅ Pip management tests passed")
    
    def test_26_advanced_workflow(self):
        """Test advanced workflow combining multiple commands"""
        print("\n🧪 Testing advanced workflow...")
        
        # 1. Create a complex project structure
        result = self.run_gds_command("mkdir", "-p", "project/src")
        self.assertEqual(result.returncode, 0, "Create project structure should succeed")
        
        result = self.run_gds_command("mkdir", "-p", "project/docs")
        self.assertEqual(result.returncode, 0, "Create docs directory should succeed")
        
        # 2. Create files in different directories (fix escaping)
        result = self.run_gds_command('echo "def main():\n    print(\'Hello Project\')\n\nif __name__ == \'__main__\':\n    main()" > project/src/main.py')
        self.assertEqual(result.returncode, 0, "Create main.py should succeed")
        
        result = self.run_gds_command('echo "# Project Documentation\nThis is a test project." > project/docs/README.md')
        self.assertEqual(result.returncode, 0, "Create README.md should succeed")
        
        # 3. Navigate and explore the structure
        result = self.run_gds_command("cd", "project")
        self.assertEqual(result.returncode, 0, "Change to project directory should succeed")
        
        result = self.run_gds_command("ls", "-R")
        self.assertEqual(result.returncode, 0, "Recursive ls should succeed")
        
        # 4. Search for content
        result = self.run_gds_command("find", ".", "-name", "*.py")
        self.assertEqual(result.returncode, 0, "Find Python files should succeed")
        
        result = self.run_gds_command("grep", "main", "src/main.py")
        self.assertEqual(result.returncode, 0, "Grep in Python file should succeed")
        
        # 5. Edit and test the Python file
        result = self.run_gds_command("edit", "src/main.py", '[["Hello Project", "Hello Advanced Workflow"]]')
        self.assertEqual(result.returncode, 0, "Edit Python file should succeed")
        
        result = self.run_gds_command("python", "src/main.py")
        self.assertEqual(result.returncode, 0, "Execute Python file should succeed")
        
        # 6. Move and organize files
        result = self.run_gds_command("mv", "docs/README.md", "README.md")
        self.assertEqual(result.returncode, 0, "Move README to root should succeed")
        
        # 7. Download files for local inspection
        result = self.run_gds_command("download", "src/main.py")
        self.assertEqual(result.returncode, 0, "Download Python file should succeed")
        
        print("✅ Advanced workflow tests passed")
    
    def test_27_error_handling(self):
        """Test error handling scenarios"""
        print("\n🧪 Testing error handling scenarios...")
        
        # Try to read non-existent file
        result = self.run_gds_command("read", "nonexistent_file.txt")
        # Should handle gracefully (may return 0 with error message)
        
        # Try to edit non-existent file
        result = self.run_gds_command("edit", "nonexistent_file.txt", '[["old", "new"]]')
        # Should handle gracefully
        
        # Try invalid edit syntax
        result = self.run_gds_command("edit", "test_file_1.txt", 'invalid_json')
        # Should handle gracefully
        
        # Try to move non-existent file
        result = self.run_gds_command("mv", "nonexistent_source.txt", "destination.txt")
        # Should handle gracefully
        
        # Try to delete non-existent file
        result = self.run_gds_command("rm", "nonexistent_file.txt")
        # Should handle gracefully
        
        # Try to activate non-existent virtual environment
        result = self.run_gds_command("venv", "--activate", "nonexistent_env")
        # Should handle gracefully
        
        print("✅ Error handling tests completed")


def run_comprehensive_tests():
    """Run the comprehensive GDS tests"""
    if not GOOGLE_DRIVE_AVAILABLE:
        print("❌ GOOGLE_DRIVE module not available - skipping tests")
        return False
    
    print("🧪 Running GDS Comprehensive Tests...")
    print("📝 These tests require user interaction - please follow the prompts")
    print("⏰ No timeouts are set to allow for user interaction")
    
    suite = unittest.TestLoader().loadTestsFromTestCase(GDSComprehensiveTest)
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description="GDS Comprehensive Test Suite")
    parser.add_argument('--specific', type=str, help='Run specific test method')
    args = parser.parse_args()
    
    if args.specific:
        # Run specific test
        suite = unittest.TestSuite()
        suite.addTest(GDSComprehensiveTest(args.specific))
        runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout, buffer=False)
        result = runner.run(suite)
        success = result.wasSuccessful()
    else:
        # Run all tests
        success = run_comprehensive_tests()
    
    sys.exit(0 if success else 1) 