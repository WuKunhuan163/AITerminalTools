#!/usr/bin/env python3
"""
Google Drive Shell - Unified Help System
Provides consistent help information for both command line and shell modes
"""

import os
import sys

def get_unified_help_data():
    """
    Get structured help data that can be formatted for different contexts
    Returns a dictionary with help sections
    """
    return {
        "tool_info": {
            "name": "GOOGLE_DRIVE",
            "description": "Google Drive access tool with GDS (Google Drive Shell)",
            "usage": "GOOGLE_DRIVE [url] [options]"
        },
        "arguments": {
            "url": "Custom Google Drive URL (default: https://drive.google.com/)"
        },
        "main_options": {
            "-my": "Open My Drive (https://drive.google.com/drive/u/0/my-drive)",
            "--console-setup": "Start Google Drive API setup wizard with GUI assistance",
            "--shell [COMMAND]": "Enter interactive shell mode or execute shell command (alias: GDS)",
            "--upload FILE [PATH]": "Upload a file to Google Drive via local sync (PATH defaults to REMOTE_ROOT)",
            "--create-remote-shell": "Create a new remote shell session",
            "--list-remote-shell": "List all remote shell sessions",
            "--checkout-remote-shell ID": "Switch to a specific remote shell",
            "--terminate-remote-shell ID": "Terminate a remote shell session",
            "--desktop --status": "Check Google Drive Desktop application status",
            "--desktop --shutdown": "Shutdown Google Drive Desktop application",
            "--desktop --launch": "Launch Google Drive Desktop application",
            "--desktop --restart": "Restart Google Drive Desktop application",
            "--desktop --set-local-sync-dir": "Set local sync directory path",
            "--desktop --set-global-sync-dir": "Set global sync directory (Drive folder)",
            "--help, -h": "Show this help message"
        },
        "shell_commands": {
            "navigation": {
                "pwd": "show current directory path",
                "ls [path] [--detailed] [-R]": "list directory contents (recursive with -R)",
                "cd <path>": "change directory (supports ~, .., relative paths)"
            },
            "file_operations": {
                "mkdir [-p] <dir>": "create directory (recursive with -p)",
                "rm <file>": "remove file",
                "rm -rf <dir>": "remove directory recursively", 
                "rm -f <file>": "force remove file (no confirmation)",
                "mv <source> <dest>": "move/rename file or folder",
                "cat <file>": "display file contents",
                "read <file> [start end]": "read file content with line numbers",
                "touch <file>": "create empty file"
            },
            "upload_download": {
                "upload [--target-dir TARGET] <files...>": "upload files to Google Drive (default: current directory)",
                "upload [--remove-local] <files...>": "upload files and optionally remove local copies",
                "upload-folder [--keep-zip] <folder> [target]": "upload folder (zip->upload->unzip->cleanup)",
                "download [--force] <file> [path]": "download file with caching"
            },
            "text_operations": {
                "echo <text>": "display text",
                "echo <text> > <file>": "create file with text",
                "grep <pattern> <file>": "search for pattern in file",
                "grep <file>": "display file content with line numbers (no pattern)",
                "edit [--preview] [--backup] <file> '<spec>'": "edit file with multi-segment replacement"
            },
            "remote_execution": {
                "python <file>": "execute python file remotely",
                "python -c '<code>'": "execute python code remotely"
            },
            "package_management": {
                "pip install <package>": "install Python packages",
                "pip list": "list installed packages",
                "pip show <package>": "show package information",
                "deps <package> [options]": "analyze package dependencies",
                "  --depth=N": "set analysis depth (default: 2)",
                "  --analysis-type=TYPE": "use 'smart' or 'depth' analysis"
            },
            "virtual_environment": {
                "venv --create <env_name...>": "create virtual environment(s) (supports multiple names)",
                "venv --delete <env_name...>": "delete virtual environment(s) (supports multiple names, protects GaussianObject)",
                "venv --activate <env_name>": "activate virtual environment (set PYTHONPATH)",
                "venv --deactivate": "deactivate virtual environment (clear PYTHONPATH)",
                "venv --list": "list all virtual environments"
            },
            "search": {
                "find [path] -name [pattern]": "search for files matching pattern",
                "find [path] -type [f|d] -name [pattern]": "search by type (file/directory) and pattern"
            },
            "code_quality": {
                "linter <file>": "lint code files (Python, JavaScript, TypeScript, etc.)"
            },
            "help_exit": {
                "help": "show available commands",
                "exit": "exit shell mode"
            }
        },
        "advanced_features": [
            "Multi-file operations: upload [[src1, dst1], [src2, dst2], ...]",
            "Command chaining: cmd1 && cmd2 && cmd3",
            "Path resolution: supports ~, .., relative and absolute paths",
            "File caching: automatic download caching with cache management",
            "Remote execution: run Python code on remote Google Drive environment"
        ],
        "examples": {
            "basic": [
                ("GOOGLE_DRIVE", "Open main Google Drive"),
                ("GOOGLE_DRIVE -my", "Open My Drive folder"),
                ("GOOGLE_DRIVE https://drive.google.com/drive/my-drive", "Open specific folder"),
                ("GOOGLE_DRIVE --console-setup", "Start API setup wizard")
            ],
            "shell_mode": [
                ("GOOGLE_DRIVE --shell", "Enter interactive shell mode"),
                ("GOOGLE_DRIVE --shell pwd", "Show current path"),
                ("GOOGLE_DRIVE --shell ls", "List directory contents"),
                ("GOOGLE_DRIVE --shell mkdir test", "Create directory"),
                ("GOOGLE_DRIVE --shell cd hello", "Change directory"),
                ("GOOGLE_DRIVE --shell rm file.txt", "Remove file"),
                ("GOOGLE_DRIVE --shell rm -rf folder", "Remove directory"),
                ("GOOGLE_DRIVE --shell upload file1.txt file2.txt", "Upload multiple files to current directory"),
                ("GOOGLE_DRIVE --shell upload --target-dir docs file.txt", "Upload file to docs directory"),
                ('GOOGLE_DRIVE --shell "ls && cd test && pwd"', "Chain commands"),
                ("GDS pwd", "Using alias (same as above)")
            ],
            "upload": [
                ("GOOGLE_DRIVE --upload file.txt", "Upload file to REMOTE_ROOT"),
                ("GOOGLE_DRIVE --upload file.txt subfolder", "Upload file to REMOTE_ROOT/subfolder")
            ],
            "remote_shells": [
                ("GOOGLE_DRIVE --create-remote-shell", "Create remote shell"),
                ("GOOGLE_DRIVE --list-remote-shell", "List remote shells"),
                ("GOOGLE_DRIVE --checkout-remote-shell abc123", "Switch to shell"),
                ("GOOGLE_DRIVE --terminate-remote-shell abc123", "Terminate shell")
            ],
            "desktop": [
                ("GOOGLE_DRIVE --desktop --status", "Check Desktop app status"),
                ("GOOGLE_DRIVE --desktop --shutdown", "Shutdown Desktop app"),
                ("GOOGLE_DRIVE --desktop --launch", "Launch Desktop app"),
                ("GOOGLE_DRIVE --desktop --restart", "Restart Desktop app"),
                ("GOOGLE_DRIVE --desktop --set-local-sync-dir", "Set local sync directory"),
                ("GOOGLE_DRIVE --desktop --set-global-sync-dir", "Set global sync directory")
            ],
            "advanced": [
                ("GOOGLE_DRIVE --setup-hf", "Setup HuggingFace credentials on remote"),
                ("GOOGLE_DRIVE --test-hf", "Test HuggingFace configuration on remote"),
                ("GOOGLE_DRIVE --help", "Show help")
            ]
        }
    }

def format_help_for_command_line():
    """Format help for command line usage (GOOGLE_DRIVE --help)"""
    data = get_unified_help_data()
    
    help_text = f"""{data['tool_info']['name']} - {data['tool_info']['description']}

Usage: {data['tool_info']['usage']}

Arguments:
"""
    
    # Add arguments
    for arg, desc in data['arguments'].items():
        help_text += f"  {arg:<20} {desc}\n"
    
    help_text += "\nOptions:\n"
    
    # Add main options
    for option, desc in data['main_options'].items():
        help_text += f"  {option:<30} {desc}\n"
    
    help_text += "\nGDS (Google Drive Shell) Commands:\n"
    help_text += "  When using --shell or in interactive mode, the following commands are available:\n\n"
    
    # Add shell commands by category
    for category, commands in data['shell_commands'].items():
        category_title = category.replace('_', ' ').title().replace('_', ' ')
        if category == "navigation":
            help_text += "  Navigation:\n"
        elif category == "file_operations":
            help_text += "  File Operations:\n"
        elif category == "upload_download":
            help_text += "  Upload/Download:\n"
        elif category == "text_operations":
            help_text += "  Text Operations:\n"
        elif category == "remote_execution":
            help_text += "  Remote Execution:\n"
        elif category == "package_management":
            help_text += "  Package Management:\n"
        elif category == "virtual_environment":
            help_text += "  Virtual Environment:\n"
        elif category == "search":
            help_text += "  Search:\n"
        elif category == "code_quality":
            help_text += "  Code Quality:\n"
        elif category == "help_exit":
            help_text += "  Help:\n"
        
        for cmd, desc in commands.items():
            help_text += f"    {cmd:<30} - {desc}\n"
        help_text += "\n"
    
    help_text += "Advanced Features:\n"
    for feature in data['advanced_features']:
        help_text += f"  - {feature}\n"
    
    help_text += "\nExamples:\n"
    
    # Add examples by category
    for category, examples in data['examples'].items():
        for cmd, desc in examples:
            help_text += f"  {cmd:<50} # {desc}\n"
    
    return help_text

def format_help_for_shell_mode():
    """Format help for shell mode usage (GDS help)"""
    data = get_unified_help_data()
    
    help_text = ""
    
    # Add shell commands in a more compact format for shell mode
    for category, commands in data['shell_commands'].items():
        for cmd, desc in commands.items():
            if cmd.startswith('  '):  # Skip sub-options like --depth
                continue
            help_text += f"{cmd:<35} - {desc}\n"
    
    return help_text.rstrip()

def show_unified_help(context="command_line", command_identifier=None):
    """
    Show unified help based on context
    
    Args:
        context: "command_line" for --help, "shell" for shell help
        command_identifier: For RUN environment support
    """
    try:
        # Import functions for RUN environment support
        from .remote_commands import is_run_environment, write_to_json_output
    except ImportError:
        def is_run_environment(cmd_id=None):
            return False
        def write_to_json_output(data, cmd_id=None):
            return False
    
    if context == "shell":
        help_text = format_help_for_shell_mode()
    else:
        help_text = format_help_for_command_line()
    
    if is_run_environment(command_identifier):
        write_to_json_output({"success": True, "help": help_text}, command_identifier)
    else:
        print(help_text)
    
    return 0

# Standalone functions for backward compatibility
def show_help():
    """显示命令行帮助信息 (for --help)"""
    return show_unified_help(context="command_line")

def shell_help(command_identifier=None):
    """显示shell模式帮助信息 (for GDS help)"""
    return show_unified_help(context="shell", command_identifier=command_identifier)
