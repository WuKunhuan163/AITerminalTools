#!/usr/bin/env python3
"""
Google Drive - Hf Credentials Manager Module
从GOOGLE_DRIVE.py重构而来的hf_credentials_manager模块
"""

import os
import sys
import json
import webbrowser
import hashlib
import subprocess
import time
import uuid
import warnings
from pathlib import Path
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')
from dotenv import load_dotenv
load_dotenv()

# 导入Google Drive Shell管理类
try:
    # from google_drive_shell import GoogleDriveShell
    pass
except ImportError as e:
    print(f"Error: Import Google Drive Shell failed: {e}")
    GoogleDriveShell = None

def get_local_hf_token():
    """
    获取本地HuggingFace token
    
    Returns:
        dict: 包含token信息或错误信息
    """
    try:
        # 检查HUGGINGFACE工具是否可用
        import subprocess
        result = subprocess.run(['HUGGINGFACE', '--status'], capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"success": False, "error": "HUGGINGFACE tool not available or not authenticated"}
        
        # 直接读取token文件
        import os
        from pathlib import Path
        
        hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        token_path = Path(hf_home) / "token"
        
        if not token_path.exists():
            return {"success": False, "error": "HuggingFace token file not found"}
        
        try:
            with open(token_path, 'r') as f:
                token = f.read().strip()
            
            if not token:
                return {"success": False, "error": "HuggingFace token file is empty"}
            
            return {
                "success": True,
                "token": token,
                "token_path": str(token_path),
                "token_length": len(token)
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to read token file: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"Failed to get local HF token: {str(e)}"}

def setup_remote_hf_credentials(command_identifier=None):
    """
    设置远端HuggingFace认证配置
    
    Args:
        command_identifier (str): 命令标识符
        
    Returns:
        dict: 操作结果
    """
    try:
        # 1. 获取本地HF token
        token_result = get_local_hf_token()
        if not token_result["success"]:
            return {
                "success": False,
                "error": f"Failed to get local HF token: {token_result['error']}"
            }
        
        token = token_result["token"]
        
        # 2. 生成远端设置命令
        remote_setup_commands = f"""
# HuggingFace Credentials Setup
export HF_TOKEN="{token}"
export HUGGINGFACE_HUB_TOKEN="{token}"

# Create HF cache directory
mkdir -p ~/.cache/huggingface

# Write token to standard location
echo "{token}" > ~/.cache/huggingface/token
chmod 600 ~/.cache/huggingface/token

# Verify setup
if [ -f ~/.cache/huggingface/token ]; then
    echo "HuggingFace token configured successfully"
    echo "Token length: {len(token)}"
    echo "Token prefix: {token[:8]}..."
else
    echo "Error: Failed to configure HuggingFace token"
    exit 1
fi

# Test HuggingFace authentication (if python and pip are available)
if command -v python3 >/dev/null 2>&1; then
    echo "🧪 Testing HuggingFace authentication..."
    python3 -c "
import sys
import subprocess

try:
    # Try to install huggingface_hub if not available
    try:
        import huggingface_hub
    except ImportError:
        print('📦 Installing huggingface_hub...')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'huggingface_hub', '--quiet'])
        import huggingface_hub
    
    # Test authentication
    from huggingface_hub import HfApi
    api = HfApi()
    user_info = api.whoami()
    username = user_info.get('name', 'Unknown')
    email = user_info.get('email', 'Unknown')
    
    print('HuggingFace authentication successful!')
    print(f'   Username: {{username}}')
    print(f'   Email: {{email}}')
    
    # Test model access
    try:
        model_info = api.model_info('bert-base-uncased')
        print('Model access verified (can access public models)')
    except Exception as model_error:
        print(f'Warning: Model access test failed: {{model_error}}')
    
    # Final success indicator
    print('🎉 HuggingFace setup completed successfully!')
    exit(0)
    
except Exception as e:
    print(f'Error: HuggingFace authentication failed: {{e}}')
    print('💡 Please check your token and try again')
    exit(1)
"
    
    # Check the exit code from Python script
    if [ $? -eq 0 ]; then
        clear
        echo "Setup completed"
    else
        echo "Error: Setup failed"
        exit 1
    fi
else
    echo "Warning: Python not available, skipping authentication test"
    echo "🎉 Token configured, but manual verification needed"
fi
"""
        
        # 3. 通过tkinter显示远端命令供用户执行
        if is_run_environment(command_identifier):
            return {
                "success": True,
                "message": "HuggingFace remote setup command generated",
                "remote_command": remote_setup_commands.strip(),
                "token_configured": True,
                "instructions": "Execute the remote_command in your remote terminal to set up HuggingFace credentials"
            }
        else:
            # 非RUN环境，使用subprocess方法显示窗口
            # show_command_window_subprocess现在在remote_commands中，需要通过main_instance访问
            
            title = "🤗 HuggingFace remote setup"
            instruction = "Please execute the following command in your remote environment to set up HuggingFace credentials:"
            
            # 使用subprocess方法显示窗口
            # 创建一个临时的remote_commands实例来调用方法
            from .remote_commands import RemoteCommands
            remote_cmd_instance = RemoteCommands(None, None)
            result = remote_cmd_instance.show_command_window_subprocess(
                title=title,
                command_text=remote_setup_commands.strip(),
                timeout_seconds=300
            )
            
            # 转换结果格式
            if result["action"] == "success":
                return {
                    "success": True,
                    "remote_command": remote_setup_commands.strip(),
                    "token_configured": True,
                    "message": "HuggingFace credentials setup completed"
                }
            elif result["action"] == "copy":
                return {
                    "success": True,
                    "remote_command": remote_setup_commands.strip(),
                    "token_configured": True,
                    "message": "Command copied to clipboard, please manually execute"
                }
            else:
                return {
                    "success": False,
                    "error": f"Operation cancelled or failed: {result.get('error', 'Unknown error')}",
                    "remote_command": remote_setup_commands.strip()
                }
            
    except Exception as e:
        return {"success": False, "error": f"Failed to setup remote HF credentials: {str(e)}"}

def test_remote_hf_setup(command_identifier=None):
    """
    测试远端HuggingFace配置
    
    Args:
        command_identifier (str): 命令标识符
        
    Returns:
        dict: 测试结果
    """
    try:
        # 生成远端测试命令
        test_command = """
# Test HuggingFace Configuration
echo "🧪 Testing HuggingFace Configuration..."

# Check environment variables
echo "Environment Variables:"
echo "  HF_TOKEN: ${HF_TOKEN:0:8}..."
echo "  HUGGINGFACE_HUB_TOKEN: ${HUGGINGFACE_HUB_TOKEN:0:8}..."

# Check token file
if [ -f ~/.cache/huggingface/token ]; then
    token_content=$(cat ~/.cache/huggingface/token)
    echo "  Token file: Exists (${#token_content} chars)"
else
    echo "  Token file: Error: Missing"
fi

# Test Python integration
if command -v python3 >/dev/null 2>&1; then
    echo "Python HuggingFace Test:"
    python3 -c "
try:
    import huggingface_hub
    from huggingface_hub import HfApi
    
    api = HfApi()
    user_info = api.whoami()
    print(f'  Authentication: Success')
    print(f'  Username: {user_info.get(\"name\", \"Unknown\")}')
    print(f'  Email: {user_info.get(\"email\", \"Unknown\")}')
    
    # Test model access
    model_info = api.model_info('bert-base-uncased')
    print(f'  Model Access: Can access public models')
    
except ImportError:
    print('  HuggingFace Hub: Error: Not installed')
    print('  Run: pip install huggingface_hub')
except Exception as e:
    print(f'  Authentication: Error: Failed - {e}')
"
else
    echo "Python: Error: Not available"
fi

echo "🏁 HuggingFace configuration test completed"
"""
        
        if is_run_environment(command_identifier):
            return {
                "success": True,
                "message": "HuggingFace test command generated",
                "test_command": test_command.strip(),
                "instructions": "Execute the test_command in your remote terminal to verify HuggingFace setup"
            }
        else:
            # 使用GDS执行测试命令
            result = handle_shell_command(f'bash -c "{test_command}"', command_identifier)
            return result
            
    except Exception as e:
        return {"success": False, "error": f"Failed to test remote HF setup: {str(e)}"}
