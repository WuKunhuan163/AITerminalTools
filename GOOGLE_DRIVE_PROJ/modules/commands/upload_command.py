from .base_command import BaseCommand

class UploadCommand(BaseCommand):
    @property
    def command_name(self):
        return "upload"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行upload命令"""
        # print(f"🔍 UPLOAD_COMMAND DEBUG: Processing upload with args: {args}")
        
        if not args:
            print("Error: upload command needs a file name")
            return 1
        
        # 解析参数
        source_path = None
        target_path = None
        overwrite = False
        
        i = 0
        while i < len(args):
            if args[i] == '--overwrite' or args[i] == '--force':
                overwrite = True
            elif source_path is None:
                source_path = args[i]
            elif target_path is None:
                target_path = args[i]
            i += 1
        
        if source_path is None:
            print("Error: upload command needs a source file")
            return 1
        
        # 如果没有指定目标路径，使用源文件名
        if target_path is None:
            import os
            target_path = os.path.basename(source_path)
        
        # 调用shell的upload方法
        result = self.shell.cmd_upload([source_path], target_path=target_path, force=overwrite)
        
        if result.get("success", False):
            if not result.get("direct_feedback", False):
                print(result.get("message", "File uploaded successfully"))
            return 0
        else:
            print(result.get("error", "Failed to upload file"))
            return 1
