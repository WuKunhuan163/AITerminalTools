from .base_command import BaseCommand

class CatCommand(BaseCommand):
    @property
    def command_name(self):
        return "cat"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行cat命令"""
        # print(f"🔍 CAT_COMMAND DEBUG: Processing cat with args: {args}")
        
        if not args:
            print("Error: cat command needs a file name")
            return 1
        
        filename = args[0]
        
        # 调用shell的cat方法
        result = self.shell.cmd_cat(filename)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                print(result.get("output", ""), end = "")
            return 0
        else:
            print(result.get("error", "Failed to read file"))
            return 1
