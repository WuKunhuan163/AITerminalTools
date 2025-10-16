"""
Grep command handler for GDS.
"""

from typing import List
from .base_command import BaseCommand


class GrepCommand(BaseCommand):
    """Handler for grep commands."""
    
    @property
    def command_name(self) -> str:
        return "grep"
    
    def validate_args(self, args: List[str]) -> bool:
        """Validate grep command arguments."""
        if len(args) < 1:
            self.print_error("grep command needs at least a file name")
            return False
        return True
    
    def execute(self, args: List[str], **kwargs) -> int:
        """Execute grep command."""
        self.print_debug(f"✅ MATCHED GREP BRANCH! Processing grep with args: {args}")
        
        # 处理参数解析
        if len(args) == 1:
            # 只有一个参数，视为文件名，模式为空（等效于read）
            pattern = ""
            filenames = args
        elif '.' in args[-1] and not args[-1].startswith('.'):
            # 最后一个参数很可能是文件名，前面的是模式
            filenames = [args[-1]]
            pattern_parts = args[:-1]
            pattern = ' '.join(pattern_parts)
        else:
            # 传统处理：第一个参数是模式，其余是文件名
            pattern = args[0]
            filenames = args[1:]
        
        # 移除pattern的外层引号（如果存在）
        original_pattern = pattern
        if pattern.startswith('"') and pattern.endswith('"'):
            pattern = pattern[1:-1]
        elif pattern.startswith("'") and pattern.endswith("'"):
            pattern = pattern[1:-1]
        
        # 检查是否为无模式的grep（等效于read）
        if not pattern or pattern.strip() == "":
            # 无模式grep，等效于read命令
            for filename in filenames:
                cat_result = self.shell.cmd_cat(filename)
                if cat_result.get("success"):
                    content = cat_result["output"]
                    # 修复换行显示问题，并添加行号
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        print(f"{i:3}: {line}")
                else:
                    self.print_error(f"无法读取文件: {filename}")
            return 0
        
        # 有模式的grep，只显示匹配行
        result = self.shell.cmd_grep(pattern, *filenames)
        if result.get("success", False):
            result_data = result.get("result", {})
            has_matches = False
            has_file_errors = False
            
            for filename, file_result in result_data.items():
                if "error" in file_result:
                    self.print_error(f"{filename}: {file_result['error']}")
                    has_file_errors = True
                else:
                    occurrences = file_result.get("occurrences", {})
                    if occurrences:
                        has_matches = True
                        # 获取文件内容用于显示匹配行
                        cat_result = self.shell.cmd_cat(filename)
                        if cat_result.get("success"):
                            lines = cat_result["output"].split('\n')
                            for line_num in sorted(occurrences.keys()):
                                if 1 <= line_num <= len(lines):
                                    print(f"{line_num:3}: {lines[line_num-1]}")
                        else:
                            self.print_error(f"无法读取文件内容: {filename}")
            
            # 按照bash grep的标准行为返回退出码
            if has_file_errors:
                return 2  # 文件错误（如文件不存在）
            elif not has_matches:
                return 1  # 没有匹配项
            else:
                return 0  # 有匹配项
        else:
            self.print_error(result.get("error", "Grep命令执行失败"))
            return 1
