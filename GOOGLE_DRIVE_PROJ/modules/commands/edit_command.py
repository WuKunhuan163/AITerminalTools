from .base_command import BaseCommand
import re

class EditCommand(BaseCommand):
    @property
    def command_name(self):
        return "edit"
    
    def execute(self, cmd, args, command_identifier=None):
        """执行edit命令"""
        # print(f"🔍 EDIT_COMMAND DEBUG: Processing edit with args: {args}")
        
        if len(args) < 2:
            print("Error: edit command needs a file name and edit specification")
            return 1
        
        # 解析选项参数
        preview = False
        backup = False
        remaining_args = []
        
        for arg in args:
            if arg == '--preview':
                preview = True
            elif arg == '--backup':
                backup = True
            else:
                remaining_args.append(arg)
        
        if len(remaining_args) < 2:
            print("Error: edit command needs a file name and edit specification")
            return 1
        
        filename = remaining_args[0]
        # 对于edit命令，JSON参数不能用空格连接，需要从原始命令中提取
        # 使用正则表达式从原始shell_cmd中提取JSON部分
        shell_cmd_clean = f"{cmd} {' '.join(args)}"
        
        # 构建选项字符串用于匹配
        options_pattern = ""
        if preview:
            options_pattern += r"(?:--preview\s+)?"
        if backup:
            options_pattern += r"(?:--backup\s+)?"
        
        # 匹配命令：edit [options] filename JSON_spec
        pattern = rf'^edit\s+{options_pattern}(\S+)\s+(.+)$'
        match = re.search(pattern, shell_cmd_clean)
        if match:
            edit_spec = match.group(2)  # 直接提取JSON部分，不做空格连接
        else:
            # 回退方案：如果只有一个JSON参数，直接使用
            if len(remaining_args) == 2:
                edit_spec = remaining_args[1]
            else:
                # 多个参数时，可能是引号被分割了，尝试重新组合
                edit_spec = ' '.join(remaining_args[1:])
        
        try:
            result = self.shell.cmd_edit(filename, edit_spec, preview=preview, backup=backup)
        except KeyboardInterrupt:
            result = {"success": False, "error": "Operation interrupted by user"}
        
        if result.get("success", False):
            # 显示diff比较（预览模式和正常模式都显示）
            diff_output = result.get("diff_output", "")
            
            if diff_output and diff_output != "No changes detected":
                print(f"\nEdit comparison: {filename}")
                print(f"=" * 50)
                
                # 过滤diff输出，移除文件头和行号信息
                diff_lines = diff_output.splitlines()
                filtered_lines = []
                for line in diff_lines:
                    # 跳过文件头行（--- 和 +++）
                    if line.startswith('---') or line.startswith('+++'):
                        continue
                    # 跳过行号信息行（@@）
                    if line.startswith('@@'):
                        continue
                    filtered_lines.append(line)
                
                # 显示过滤后的diff内容
                if filtered_lines:
                    print('\n'.join(filtered_lines))
                print(f"=" * 50)
            elif diff_output == "No changes detected":
                print(f"No changes detected")
            
            # 对于正常模式，显示成功信息
            if result.get("mode") != "preview":
                print(result.get("message", "\nFile edited successfully"))
            
            # 显示linter结果（如果有）
            if result.get("has_linter_issues"):
                print(f"=" * 50)
                linter_output = result.get("linter_output", "")
                total_issues = linter_output.count("ERROR:") + linter_output.count("WARNING:")
                print(f"{total_issues} linter warnings or errors found:")
                print(linter_output)
                print(f"=" * 50)
            elif result.get("linter_error"):
                print(f"=" * 50)
                print(f"Linter check failed: {result.get('linter_error')}")
                print(f"=" * 50)
            elif result.get("has_linter_issues") == False:
                # Only show "no issues" message if linter actually ran
                pass  # No need to show anything for clean files
            
            return 0
        else:
            print(result.get("error", "Failed to edit file"))
            return 1
