#!/usr/bin/env python3
"""
bin.py - Binary Tools Management System
Manages _bin.json registry and generates user rules for Cursor AI
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

class BinManager:
    """Binary tools management system"""
    
    def __init__(self):
        self.bin_file = Path(__file__).parent / "_bin.json"
        self.tools = self.load_tools()
    
    def load_tools(self) -> Dict[str, Any]:
        """Load tools from _bin.json"""
        try:
            with open(self.bin_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('tools', {})
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def save_tools(self):
        """Save tools to _bin.json"""
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
                "## RUN-Compatible Tools (can be used with `RUN --show` for JSON output):",
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
            "1. **For RUN-compatible tools**: Use `RUN --show TOOL_NAME [args]` to get JSON output",
            "2. **For direct execution**: Use `./TOOL_NAME [args]` for terminal output",
            "3. **Interactive modes**: Some tools support interactive mode when called without arguments",
            "4. **File selection**: Tools like OVERLEAF and EXTRACT_PDF support GUI file selection",
            "5. **Help**: All tools support `--help` or `-h` for usage information",
            "6. **Avoid GUI when possible**: Always provide specific parameters when known, rather than relying on GUI file selection or interactive prompts",
            "7. **Use USERINPUT for missing info**: If you need file paths or other parameters, use USERINPUT to ask the user instead of interactive modes",
            "8. **Handle errors gracefully**: When encountering errors (file not found, invalid paths, etc.), use USERINPUT to get corrected information from the user",
            "",
            "## When to Use These Tools:",
            ""
        ])
        
        # Dynamic tool usage descriptions from _bin.json
        for tool_name, tool_data in passed_tools.items():
            scenario = tool_data.get('tool_use_scenario', f"When user needs to use {tool_name}")
            rule_parts.append(f"- **{tool_name}**: {scenario}")
        
        rule_parts.extend([
            "",
            "Always prefer using these tools over manual implementations when the functionality matches the user's needs."
        ])
        
        return "\n".join(rule_parts)
    
    def check_files_exist(self) -> Dict[str, Dict[str, bool]]:
        """Check if tool files exist"""
        
        results = {}
        bin_dir = Path(__file__).parent
        
        for name, tool in self.tools.items():
            results[name] = {}
            for file_type, filename in tool['files'].items():
                file_path = bin_dir / filename
                results[name][file_type] = file_path.exists()
        
        return results

def show_help():
    """Show help information"""
    help_text = """bin.py - Binary Tools Management System

Usage: _bin.py [command] [options]

Commands:
  list                     List all registered tools
  info <tool_name>         Show detailed information about a tool
  add <name> <desc> <purpose> <usage> <examples> [scenario] [--no-run]
                          Add a new tool to the registry
  remove <name>           Remove a tool from the registry
  update <name> <field=value>...
                          Update tool information
  check                   Check if tool files exist
  --generate-user-rule    Generate Cursor AI user rule
  --help, -h              Show this help message

Examples:
  _bin.py list
  _bin.py info OVERLEAF
  _bin.py add MYTOOL "My tool description" "Tool purpose" "MYTOOL [args]" "MYTOOL --help" "When user needs custom functionality"
  _bin.py remove MYTOOL
  _bin.py update MYTOOL description="New description"
  _bin.py check
  _bin.py --generate-user-rule
"""
    print(help_text)

def main():
    """Main function"""
    
    manager = BinManager()
    
    if len(sys.argv) == 1:
        show_help()
        return 0
    
    command = sys.argv[1]
    
    if command in ['--help', '-h']:
        show_help()
        return 0
    
    elif command == '--generate-user-rule':
        rule_content = manager.generate_user_rule()
        
        # Save to _bin_rule.md
        rule_file = Path(__file__).parent / '_bin_rule.md'
        try:
            with open(rule_file, 'w', encoding='utf-8') as f:
                f.write(rule_content)
            print(f"✅ User rule generated and saved to {rule_file}")
            print(f"📝 Generated rule for {len([name for name, tool in manager.tools.items() if tool.get('test_passed', False)])} tools")
        except Exception as e:
            print(f"❌ Error saving user rule: {e}")
            print(rule_content)
        
        return 0
    
    elif command == 'list':
        manager.list_tools()
        return 0
    
    elif command == 'info':
        if len(sys.argv) < 3:
            print("Error: Tool name required")
            return 1
        
        tool_name = sys.argv[2]
        manager.get_tool_info(tool_name)
        return 0
    
    elif command == 'add':
        if len(sys.argv) < 7:
            print("Error: Required arguments: name, description, purpose, usage, examples")
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