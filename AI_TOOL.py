#!/usr/bin/env python3
"""
AI_TOOL_RULE.py - Binary Tools Management System
Manages AI_TOOL.json registry and generates user rules for Cursor AI
"""

import json
import sys
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class BinManager:
    """Binary tools management system"""
    
    def __init__(self):
        self.bin_file = Path(__file__).parent / "AI_TOOL.json"
        self.tools = self.load_tools()
    
    def load_tools(self) -> Dict[str, Any]:
        """Load tools from AI_TOOL.json"""
        try:
            with open(self.bin_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tools', {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_tools(self):
        """Save tools to AI_TOOL.json"""
        data = {
            "tools": self.tools,
            "metadata": {
                "version": "1.0.0",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "total_tools": len(self.tools)
            }
        }
        
        with open(self.bin_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def add_tool(self, name: str, description: str, purpose: str, usage: str, 
                 examples: List[str], run_compatible: bool = True, 
                 tool_use_scenario: str = None) -> bool:
        """Add a new tool to the registry"""
        
        if name in self.tools:
            print(f"Tool '{name}' already exists. Use update to modify it.")
            return False
        
        # Default scenario if not provided
        if tool_use_scenario is None:
            tool_use_scenario = f"When user needs to use {name}"
        
        self.tools[name] = {
            "name": name,
            "description": description,
            "purpose": purpose,
            "usage": usage,
            "examples": examples,
            "files": {
                "binary": name,
                "python": f"{name}.py",
                "markdown": f"{name}.md"
            },
            "run_compatible": run_compatible,
            "testable": True,
            "test_passed": False,
            "ai_usable": True,
            "tool_use_scenario": tool_use_scenario
        }
        
        self.save_tools()
        print(f"✅ Tool '{name}' added successfully")
        return True
    
    def remove_tool(self, name: str) -> bool:
        """Remove a tool from the registry"""
        
        if name not in self.tools:
            print(f"Tool '{name}' not found")
            return False
        
        del self.tools[name]
        self.save_tools()
        print(f"✅ Tool '{name}' removed successfully")
        return True
    
    def update_tool(self, name: str, **kwargs) -> bool:
        """Update an existing tool"""
        
        if name not in self.tools:
            print(f"Tool '{name}' not found")
            return False
        
        # Update only provided fields
        for key, value in kwargs.items():
            if key in self.tools[name]:
                self.tools[name][key] = value
        
        self.save_tools()
        print(f"✅ Tool '{name}' updated successfully")
        return True
    
    def list_tools(self) -> None:
        """List all tools"""
        
        if not self.tools:
            print("No tools registered")
            return
        
        print(f"📋 Registered Tools ({len(self.tools)}):")
        print("=" * 50)
        
        for name, tool in self.tools.items():
            run_status = "✅ RUN Compatible" if tool.get('run_compatible', True) else "❌ Not RUN Compatible"
            print(f"🔧 {name}")
            print(f"   Description: {tool['description']}")
            print(f"   Purpose: {tool['purpose']}")
            print(f"   Usage: {tool['usage']}")
            print(f"   Status: {run_status}")
            print()
    
    def get_tool_info(self, name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool"""
        
        if name not in self.tools:
            print(f"Tool '{name}' not found")
            return None
        
        tool = self.tools[name]
        print(f"🔧 {name}")
        print(f"Description: {tool['description']}")
        print(f"Purpose: {tool['purpose']}")
        print(f"Usage: {tool['usage']}")
        print(f"RUN Compatible: {'Yes' if tool.get('run_compatible', True) else 'No'}")
        if 'tool_use_scenario' in tool:
            print(f"Use Scenario: {tool['tool_use_scenario']}")
        print()
        print("Examples:")
        for example in tool['examples']:
            print(f"  {example}")
        print()
        print("Files:")
        for file_type, filename in tool['files'].items():
            print(f"  {file_type}: {filename}")
        
        return tool
    
    def generate_user_rule(self) -> str:
        """Generate Cursor AI user rule for test_passed tools"""
        
        if not self.tools:
            return "No tools available for user rule generation."
        
        # Filter tools that have test_passed = true AND ai_usable = true
        passed_tools = {name: tool for name, tool in self.tools.items() 
                       if tool.get('test_passed', False) and tool.get('ai_usable', False)}
        
        if not passed_tools:
            return "No AI-usable tools have passed tests yet."
        
        # Separate RUN-compatible and non-compatible tools
        run_compatible = []
        non_compatible = []
        
        for name, tool in passed_tools.items():
            if tool.get('run_compatible', True):
                run_compatible.append(tool)
            else:
                non_compatible.append(tool)
        
        # Generate user rule
        rule_parts = [
            "# Binary Tools Available in ~/.local/bin",
            "",
            "When working with the user, you have access to the following custom binary tools:",
            ""
        ]
        
        # RUN-compatible tools
        if run_compatible:
            rule_parts.extend([
                "## RUN-Compatible Tools (PREFERRED: use `RUN --show` for clean JSON output):",
                ""
            ])
            
            for tool in run_compatible:
                rule_parts.extend([
                    f"### {tool['name']}",
                    f"- **Purpose**: {tool['purpose']}",
                    f"- **Description**: {tool['description']}",
                    f"- **Usage**: `{tool['usage']}`",
                    f"- **Examples**:"
                ])
                
                for example in tool['examples']:
                    rule_parts.append(f"  - `{example}`")
                
                rule_parts.append("")
        
        # Non-compatible tools
        if non_compatible:
            rule_parts.extend([
                "## Other Tools:",
                ""
            ])
            
            for tool in non_compatible:
                rule_parts.extend([
                    f"### {tool['name']}",
                    f"- **Purpose**: {tool['purpose']}",
                    f"- **Description**: {tool['description']}",
                    f"- **Usage**: `{tool['usage']}`",
                    f"- **Examples**:"
                ])
                
                for example in tool['examples']:
                    rule_parts.append(f"  - `{example}`")
                
                rule_parts.append("")
        
        # Usage guidelines
        rule_parts.extend([
            "## Usage Guidelines:",
            "",
            "1. **PREFERRED: Use RUN --show for clean output**: Always use `RUN --show TOOL_NAME [args]` to get structured JSON output and avoid verbose terminal logs",
            "2. **For direct execution**: Use `./TOOL_NAME [args]` only when you need terminal output or interactive features",
            "3. **Interactive modes**: Some tools support interactive mode when called without arguments",
            "4. **File selection**: Tools like OVERLEAF and EXTRACT_PDF support GUI file selection",
            "5. **Help**: All tools support `--help` or `-h` for usage information",
            "6. **Avoid GUI when possible**: Always provide specific parameters when known, rather than relying on GUI file selection or interactive prompts",
            "7. **Use USERINPUT for missing info**: If you need file paths or other parameters, use USERINPUT to ask the user instead of interactive modes",
            "8. **Handle errors gracefully**: When encountering errors (file not found, invalid paths, etc.), use USERINPUT to get corrected information from the user",
            "9. **Clean output preference**: Use `RUN --show` to minimize terminal noise and focus on key results",
            "",
            "## When to Use These Tools:",
            ""
        ])
        
        # Dynamic tool usage descriptions from AI_TOOL.json
        for tool_name, tool_data in passed_tools.items():
            scenario = tool_data.get('tool_use_scenario', f"When user needs to use {tool_name}")
            rule_parts.append(f"- **{tool_name}**: {scenario}")
        
        rule_parts.extend([
            "",
            "Always prefer using these tools over manual implementations when the functionality matches the user's needs."
        ])
        
        return "\n".join(rule_parts)
    
    def check_files_exist(self):
        """检查所有工具的文件是否存在"""
        results = {}
        bin_dir = Path(__file__).parent
        
        for tool_name, tool_data in self.tools.items():
            results[tool_name] = {}
            
            # 检查主脚本文件
            script_file = bin_dir / tool_name
            results[tool_name]['script'] = script_file.exists()
            
            # 检查Python文件
            py_file = bin_dir / f"{tool_name}.py"
            results[tool_name]['python'] = py_file.exists()
            
            # 检查Markdown文档
            md_file = bin_dir / f"{tool_name}.md"
            results[tool_name]['markdown'] = md_file.exists()
        
        return results
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件的SHA256哈希值"""
        if not file_path.exists():
            return ""
        
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            # 分块读取文件以处理大文件
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        return sha256_hash.hexdigest()
    
    def calculate_tool_hashes(self, tool_name: str) -> Dict[str, str]:
        """计算工具所有文件的哈希值"""
        bin_dir = Path(__file__).parent
        hashes = {}
        
        if tool_name not in self.tools:
            return hashes
        
        tool_data = self.tools[tool_name]
        files = tool_data.get('files', {})
        
        # 计算每个文件的哈希值
        for file_type, filename in files.items():
            if file_type == 'project':
                # 项目文件可能在子目录中
                file_path = bin_dir / filename
            else:
                file_path = bin_dir / filename
            
            hashes[file_type] = self.calculate_file_hash(file_path)
        
        return hashes
    
    def update_tool_hashes(self, tool_name: str = None):
        """更新工具的哈希值"""
        if tool_name:
            tools_to_update = [tool_name]
        else:
            tools_to_update = list(self.tools.keys())
        
        updated_count = 0
        for tool in tools_to_update:
            if tool in self.tools:
                new_hashes = self.calculate_tool_hashes(tool)
                
                # 更新哈希值
                if 'file_hashes' not in self.tools[tool]:
                    self.tools[tool]['file_hashes'] = {}
                
                old_hashes = self.tools[tool]['file_hashes']
                self.tools[tool]['file_hashes'] = new_hashes
                
                # 检查是否有变化
                if old_hashes != new_hashes:
                    updated_count += 1
                    print(f"✓ Updated hashes for {tool}")
                    
                    # 显示变化的文件
                    for file_type, new_hash in new_hashes.items():
                        old_hash = old_hashes.get(file_type, "")
                        if old_hash != new_hash:
                            if old_hash:
                                print(f"  - {file_type}: {old_hash[:8]}... -> {new_hash[:8]}...")
                            else:
                                print(f"  - {file_type}: (new) -> {new_hash[:8]}...")
        
        # 保存更新后的配置
        self.save_tools()
        print(f"Updated hashes for {updated_count} tools")
        return updated_count
    
    def detect_changes(self, tool_name: str = None) -> Dict[str, Dict[str, Any]]:
        """检测工具文件的变更"""
        if tool_name:
            tools_to_check = [tool_name]
        else:
            tools_to_check = list(self.tools.keys())
        
        changes = {}
        
        for tool in tools_to_check:
            if tool not in self.tools:
                continue
                
            current_hashes = self.calculate_tool_hashes(tool)
            stored_hashes = self.tools[tool].get('file_hashes', {})
            
            tool_changes = {}
            for file_type, current_hash in current_hashes.items():
                stored_hash = stored_hashes.get(file_type, "")
                if stored_hash != current_hash:
                    tool_changes[file_type] = {
                        'old_hash': stored_hash,
                        'new_hash': current_hash,
                        'status': 'modified' if stored_hash else 'new'
                    }
            
            if tool_changes:
                changes[tool] = tool_changes
        
        return changes
    
    def run_automated_tests(self, tool_name: str = None):
        """运行自动化测试流程"""
        if tool_name:
            tools_to_test = [tool_name]
        else:
            # 只测试有变更的工具
            changes = self.detect_changes()
            tools_to_test = list(changes.keys())
        
        if not tools_to_test:
            print("✅ No tools need testing")
            return True
        
        print(f"🧪 Running automated tests for {len(tools_to_test)} tool(s)...")
        
        test_results = {}
        for tool in tools_to_test:
            print(f"\n🔧 Testing {tool}...")
            
            # 检查工具文件是否存在
            files_exist = self.check_tool_files(tool)
            if not all(files_exist.values()):
                print(f"❌ {tool}: Missing files")
                test_results[tool] = False
                continue
            
            # 运行基本功能测试
            basic_test = self.run_basic_test(tool)
            
            # 检查文档一致性
            doc_check = self.check_documentation_consistency(tool)
            
            test_results[tool] = basic_test and doc_check
            
            if test_results[tool]:
                print(f"✅ {tool}: All tests passed")
                # 更新test_passed状态
                self.tools[tool]['test_passed'] = True
            else:
                print(f"❌ {tool}: Tests failed")
                self.tools[tool]['test_passed'] = False
        
        # 保存测试结果
        self.save_tools()
        
        # 更新哈希值（只有测试通过的工具）
        passed_tools = [tool for tool, passed in test_results.items() if passed]
        if passed_tools:
            print(f"\n🔄 Updating hashes for {len(passed_tools)} passed tool(s)...")
            for tool in passed_tools:
                self.update_tool_hashes(tool)
        
        return all(test_results.values())
    
    def check_tool_files(self, tool_name: str) -> Dict[str, bool]:
        """检查工具文件是否存在"""
        bin_dir = Path(__file__).parent
        files_exist = {}
        
        if tool_name not in self.tools:
            return files_exist
        
        files = self.tools[tool_name].get('files', {})
        for file_type, filename in files.items():
            file_path = bin_dir / filename
            files_exist[file_type] = file_path.exists()
        
        return files_exist
    
    def run_basic_test(self, tool_name: str) -> bool:
        """运行工具的基本功能测试"""
        import subprocess
        
        bin_dir = Path(__file__).parent
        tool_path = bin_dir / tool_name
        
        if not tool_path.exists():
            return False
        
        try:
            # 测试--help选项
            result = subprocess.run(
                [str(tool_path), '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # 如果返回码是0或1（某些工具help返回1），且有输出，认为测试通过
            if result.returncode in [0, 1] and (result.stdout or result.stderr):
                print(f"  ✅ Help test passed")
                return True
            else:
                print(f"  ❌ Help test failed (return code: {result.returncode})")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"  ❌ Help test timed out")
            return False
        except Exception as e:
            print(f"  ❌ Help test error: {e}")
            return False
    
    def check_documentation_consistency(self, tool_name: str) -> bool:
        """检查文档与功能的一致性"""
        bin_dir = Path(__file__).parent
        md_file = bin_dir / f"{tool_name}.md"
        
        if not md_file.exists():
            print(f"  ❌ Documentation file not found")
            return False
        
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                doc_content = f.read()
            
            # 基本检查：文档是否包含基本部分
            required_sections = ['Usage', 'Examples']
            missing_sections = []
            
            for section in required_sections:
                if section.lower() not in doc_content.lower():
                    missing_sections.append(section)
            
            if missing_sections:
                print(f"  ❌ Missing documentation sections: {', '.join(missing_sections)}")
                return False
            
            print(f"  ✅ Documentation consistency check passed")
            return True
            
        except Exception as e:
            print(f"  ❌ Documentation check error: {e}")
            return False
    
    def init_tools(self):
        """初始化所有注册的工具，添加执行权限"""
        import stat
        
        results = {
            'success': [],
            'failed': [],
            'not_found': []
        }
        
        print("🔧 Initializing tool permissions...")
        print("=" * 40)
        
        bin_dir = Path(__file__).parent
        
        for tool_name, tool_data in self.tools.items():
            script_file = bin_dir / tool_name
            py_file = bin_dir / f"{tool_name}.py"
            
            # 处理主脚本文件
            if script_file.exists():
                try:
                    # 添加执行权限
                    current_mode = script_file.stat().st_mode
                    new_mode = current_mode | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    script_file.chmod(new_mode)
                    results['success'].append(f"{tool_name} (script)")
                    print(f"✅ {tool_name}: Script permissions set")
                except Exception as e:
                    results['failed'].append(f"{tool_name} (script): {e}")
                    print(f"❌ {tool_name}: Script permissions set failed - {e}")
            else:
                results['not_found'].append(f"{tool_name} (script)")
                print(f"⚠️  {tool_name}: Script file not found")
            
            # 处理Python文件
            if py_file.exists():
                try:
                    # 添加执行权限
                    current_mode = py_file.stat().st_mode
                    new_mode = current_mode | stat.S_IEXEC | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
                    py_file.chmod(new_mode)
                    results['success'].append(f"{tool_name}.py")
                    print(f"✅ {tool_name}.py: Python file permissions set")
                except Exception as e:
                    results['failed'].append(f"{tool_name}.py: {e}")
                    print(f"❌ {tool_name}.py: Python file permissions set failed - {e}")
        
        print("\n📊 Initialization results:")
        print(f"✅ Success: {len(results['success'])} files")
        print(f"❌ Failed: {len(results['failed'])} files")
        print(f"⚠️  Not found: {len(results['not_found'])} files")
        
        if results['failed']:
            print("\n❌ Failed details:")
            for item in results['failed']:
                print(f"  - {item}")
        
        if results['not_found']:
            print("\n⚠️  Not found files:")
            for item in results['not_found']:
                print(f"  - {item}")
        
        return results

def show_help():
    """显示帮助信息"""
    print("""AI_TOOL.py - Tool management system

Usage: python AI_TOOL.py <command> [options]

Commands:
  list                                 List all tools
  add <name> <desc> <purpose> <usage> <examples> [scenario]
                                       Add new tool
  remove <name>                        Remove tool
  update <name> <field>=<value> ...    Update tool information
  check                                Check if tool files exist
  --init                               Initialize all tool permissions (chmod +x)
  --generate-user-rule                 Generate user rule file
  --update-hashes [tool_name]          Update tool file hashes
  --detect-changes [tool_name]         Detect tool file changes
  --sync-docs [tool_name]              Sync tool documentation with functionality
  --test [tool_name]                   Run automated tests

Examples:
  python AI_TOOL.py list
  python AI_TOOL.py add MYTOOL "Description" "Purpose" "Usage" "Example1,Example2"
  python AI_TOOL.py update MYTOOL test_passed=true
  python AI_TOOL.py check
  python AI_TOOL.py --init
  python AI_TOOL.py --generate-user-rule
  python AI_TOOL.py --update-hashes
  python AI_TOOL.py --update-hashes LEARN
  python AI_TOOL.py --detect-changes
  python AI_TOOL.py --sync-docs OPENROUTER
  python AI_TOOL.py --test
  python AI_TOOL.py --test LEARN
""")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        show_help()
        return 1
    
    command = sys.argv[1]
    manager = BinManager()
    
    if command == 'list':
        manager.list_tools()
        return 0
    
    elif command == '--generate-user-rule':
        rule_content = manager.generate_user_rule()
        # Write to AI_TOOL_RULE.md file
        with open('AI_TOOL_RULE.md', 'w', encoding='utf-8') as f:
            f.write(rule_content)
        print(f"Generated user rule file: AI_TOOL_RULE.md")
        return 0
    
    elif command == '--init':
        manager.init_tools()
        return 0
    
    elif command == '--update-hashes':
        tool_name = sys.argv[2] if len(sys.argv) > 2 else None
        print("🔄 Updating file hashes...")
        manager.update_tool_hashes(tool_name)
        return 0
    
    elif command == '--detect-changes':
        tool_name = sys.argv[2] if len(sys.argv) > 2 else None
        print("🔍 Detecting file changes...")
        changes = manager.detect_changes(tool_name)
        
        if not changes:
            print("✅ No changes detected")
        else:
            print(f"📝 Detected changes in {len(changes)} tool(s):")
            for tool, tool_changes in changes.items():
                print(f"\n🔧 {tool}:")
                for file_type, change_info in tool_changes.items():
                    status = change_info['status']
                    old_hash = change_info['old_hash']
                    new_hash = change_info['new_hash']
                    
                    if status == 'new':
                        print(f"  ✨ {file_type}: (new file) -> {new_hash[:8]}...")
                    else:
                        print(f"  📝 {file_type}: {old_hash[:8]}... -> {new_hash[:8]}...")
        
        return 0
    
    elif command == '--sync-docs':
        tool_name = sys.argv[2] if len(sys.argv) > 2 else None
        print("📚 Syncing documentation with functionality...")
        # TODO: Implement documentation sync
        print("⚠️  Documentation sync not yet implemented")
        return 0
    
    elif command == '--test':
        tool_name = sys.argv[2] if len(sys.argv) > 2 else None
        success = manager.run_automated_tests(tool_name)
        return 0 if success else 1
    
    elif command == 'add':
        if len(sys.argv) < 7:
            print("Error: Insufficient arguments")
            print("Usage: python AI_TOOL.py add <name> <desc> <purpose> <usage> <examples> [scenario]")
            return 1
        
        name = sys.argv[2]
        description = sys.argv[3]
        purpose = sys.argv[4]
        usage = sys.argv[5]
        examples = sys.argv[6].split(',')
        run_compatible = '--no-run' not in sys.argv
        
        # Check for optional tool_use_scenario parameter
        tool_use_scenario = None
        if len(sys.argv) >= 8 and not sys.argv[7].startswith('--'):
            tool_use_scenario = sys.argv[7]
        
        manager.add_tool(name, description, purpose, usage, examples, run_compatible, tool_use_scenario)
        return 0
    
    elif command == 'remove':
        if len(sys.argv) < 3:
            print("Error: Tool name required")
            return 1
        
        tool_name = sys.argv[2]
        manager.remove_tool(tool_name)
        return 0
    
    elif command == 'update':
        if len(sys.argv) < 4:
            print("Error: Tool name and field=value pairs required")
            return 1
        
        tool_name = sys.argv[2]
        updates = {}
        
        for arg in sys.argv[3:]:
            if '=' in arg:
                key, value = arg.split('=', 1)
                updates[key] = value
        
        manager.update_tool(tool_name, **updates)
        return 0
    
    elif command == 'check':
        results = manager.check_files_exist()
        
        print("📁 File Existence Check:")
        print("=" * 40)
        
        for tool_name, files in results.items():
            print(f"🔧 {tool_name}:")
            for file_type, exists in files.items():
                status = "✅" if exists else "❌"
                print(f"  {file_type}: {status}")
            print()
        
        return 0
    
    else:
        print(f"Unknown command: {command}")
        show_help()
        return 1

if __name__ == "__main__":
    sys.exit(main()) 