
from .venv_operations import VenvOperations
from .pip_operations import PipOperations
from .dependency_analysis import DependencyAnalysis
from .python_execution import PythonExecution
from .file_core import FileCore
from .text_operations import TextOperations

class FileOperations:
    """
    Main file operations coordinator - delegates to specialized modules
    """
    
    def __init__(self, drive_service, main_instance=None):
        """Initialize all specialized modules"""
        self.drive_service = drive_service
        self.main_instance = main_instance
    
        # Initialize specialized modules
        self.venv_operations = VenvOperations(drive_service, main_instance)
        self.pip_operations = PipOperations(drive_service, main_instance)
        self.dependency_analysis = DependencyAnalysis(drive_service, main_instance)
        self.python_execution = PythonExecution(drive_service, main_instance)
        self.file_core = FileCore(drive_service, main_instance)
        self.text_operations = TextOperations(drive_service, main_instance)

    def get_venv_base_path(self, *args, **kwargs):
        """Delegate to venv_operations"""
        return self.venv_operations.get_venv_base_path(*args, **kwargs)
    
    def get_venv_state_file_path(self, *args, **kwargs):
        """Delegate to venv_operations"""
        return self.venv_operations.get_venv_state_file_path(*args, **kwargs)
    
    def read_venv_states(self, *args, **kwargs):
        """Delegate to venv_operations"""
        return self.venv_operations.read_venv_states(*args, **kwargs)
    
    def list_venv_environments(self, *args, **kwargs):
        """Delegate to venv_operations"""
        return self.venv_operations.list_venv_environments(*args, **kwargs)
    
    def cmd_venv(self, *args, **kwargs):
        """Delegate to venv_operations"""
        return self.venv_operations.cmd_venv(*args, **kwargs)
    
    def cmd_pip(self, *args, **kwargs):
        """Delegate to pip_operations"""
        return self.pip_operations.cmd_pip(*args, **kwargs)
    
    def cmd_deps(self, *args, **kwargs):
        """Delegate to dependency_analysis"""
        return self.dependency_analysis.cmd_deps(*args, **kwargs)
    
    def cmd_python(self, *args, **kwargs):
        """Delegate to python_execution"""
        return self.python_execution.cmd_python(*args, **kwargs)
    
    def cmd_upload_folder(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_upload_folder(*args, **kwargs)
    
    def cmd_upload(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_upload(*args, **kwargs)
    
    def cmd_download(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_download(*args, **kwargs)
    
    def cmd_pwd(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_pwd(*args, **kwargs)
    
    def cmd_ls(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_ls(*args, **kwargs)
    
    def cmd_cd(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_cd(*args, **kwargs)
    
    def cmd_mkdir(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_mkdir(*args, **kwargs)
    
    def cmd_touch(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_touch(*args, **kwargs)
    
    def cmd_rm(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_rm(*args, **kwargs)
    
    def cmd_cp(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_cp(*args, **kwargs)
    
    def cmd_mv(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.cmd_mv(*args, **kwargs)
    
    def wait_for_file_sync(self, *args, **kwargs):
        """Delegate to file_operations"""
        return self.file_core.wait_for_file_sync(*args, **kwargs)
    
    def cmd_edit(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_edit(*args, **kwargs)
    
    def _create_text_file(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations._create_text_file(*args, **kwargs)
    
    def cmd_nano(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_nano(*args, **kwargs)
    
    def cmd_vim(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_vim(*args, **kwargs)
    
    def cmd_cat(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_cat(*args, **kwargs)
    
    def cmd_head(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_head(*args, **kwargs)
    
    def cmd_tail(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_tail(*args, **kwargs)
    
    def cmd_grep(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_grep(*args, **kwargs)
    
    def cmd_find(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_find(*args, **kwargs)
    
    def cmd_wc(self, *args, **kwargs):
        """Delegate to text_operations"""
        return self.text_operations.cmd_wc(*args, **kwargs)
    
    def cmd_read(self, filename, *args, **kwargs):
        """Read file content - delegate to text_operations cat command for now"""
        # For now, use cat command as a simple implementation of read
        return self.text_operations.cmd_cat(filename)
    
    def cmd_linter(self, filename, *args, **kwargs):
        """Lint file - delegate to linter functionality"""
        try:
            # Get file content first
            cat_result = self.text_operations.cmd_cat(filename)
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"Could not read file {filename}: {cat_result.get('error', 'Unknown error')}"
                }
            
            content = cat_result.get("output", "")
            
            # Import and use the linter
            from .linter import GDSLinter
            linter = GDSLinter()
            
            # Run linter on content
            result = linter.lint_content(content, filename)
            
            # Format output for display
            output_lines = []
            output_lines.append(f"Language: {result.get('language', 'unknown')}")
            output_lines.append(f"Status: {'✅ PASS' if result.get('success', False) else '❌ FAIL'}")
            output_lines.append(f"Message: {result.get('message', '')}")
            
            if result.get('errors'):
                output_lines.append("\n🚫 Errors:")
                for error in result['errors']:
                    output_lines.append(f"  • {error}")
            
            if result.get('warnings'):
                output_lines.append("\n⚠️  Warnings:")
                for warning in result['warnings']:
                    output_lines.append(f"  • {warning}")
            
            if result.get('info'):
                output_lines.append("\nℹ️  Info:")
                for info in result['info']:
                    output_lines.append(f"  • {info}")
            
            return {
                "success": True,
                "output": "\n".join(output_lines),
                "has_errors": bool(result.get('errors')),
                "linter_result": result
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Linter execution failed: {str(e)}"
            }
    
    def check_network_connection(self):
        """Check network connection"""
        try:
            import urllib.request
            urllib.request.urlopen('http://www.google.com', timeout=1)
            return True
        except:
            return False
    
    def ensure_google_drive_desktop_running(self):
        """Ensure Google Drive Desktop is running"""
        try:
            import subprocess
            import platform
            import time
            
            # Check if running
            result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                  capture_output=True, text=True)
            if result.returncode == 0 and bool(result.stdout.strip()):
                return True
            
            # Try to start
            print("🚀 Starting Google Drive Desktop...")
            if platform.system() == "Darwin":
                subprocess.run(['open', '-a', 'Google Drive'], check=False)
            elif platform.system() == "Linux":
                subprocess.run(['google-drive'], check=False)
            elif platform.system() == "Windows":
                subprocess.run(['start', 'GoogleDrive'], shell=True, check=False)
            
            # Wait for startup
            for i in range(10):
                time.sleep(1)
                result = subprocess.run(['pgrep', '-f', 'Google Drive'], 
                                      capture_output=True, text=True)
                if result.returncode == 0 and bool(result.stdout.strip()):
                    print("✅ Google Drive Desktop started successfully")
                    return True
            
            print("⚠️ Could not confirm Google Drive Desktop startup")
            return False
            
        except Exception as e:
            print(f"❌ Error managing Google Drive Desktop: {e}")
            return False
