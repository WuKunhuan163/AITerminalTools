"""
Venv command handler for GDS.
"""

from typing import List
from .base_command import BaseCommand


class VenvCommand(BaseCommand):
    """Handler for venv commands."""
    
    @property
    def command_name(self) -> str:
        return "venv"
    
    def execute(self, args: List[str], **kwargs) -> int:
        """Execute venv command."""
        # self.print_debug(f"✅ MATCHED VENV BRANCH! Inside venv command handler, calling cmd_venv with args: {args}")
        
        # 使用委托方法处理venv命令
        result = self.shell.cmd_venv(*args)
        # self.print_debug(f"cmd_venv returned: {result}")
        
        if result.get("success", False):
            # venv命令成功后，同步更新本地shell状态
            self.shell._sync_venv_state_to_local_shell(args)
            return 0
        else:
            error_message = result.get("error", "Virtual environment operation failed")
            self.print_error(error_message)
            return 1
