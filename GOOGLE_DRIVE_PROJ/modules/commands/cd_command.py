from .base_command import BaseCommand

class CdCommand(BaseCommand):
    @property
    def command_name(self):
        return "cd"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行cd命令"""
        # print(f"🔍 CD_COMMAND DEBUG: Processing cd with args: {args}")
        
        if not args:
            print("Error: cd command needs a directory path")
            return 1
        
        path = args[0]
        
        # 调用shell的cd方法
        result = self.shell.cmd_cd(path)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                if (result.get("output", "")): 
                    print(result.get("output", ""))
            return 0
        else:
            print(result.get("error", "Failed to change directory"))
            return 1
