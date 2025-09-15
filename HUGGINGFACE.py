#!/usr/bin/env python3
"""
HuggingFace Credentials Management Tool
HuggingFace凭据管理工具

This tool provides functionality to manage HuggingFace credentials, authentication,
and model access for projects that require HuggingFace Hub integration.

Usage:
    HUGGINGFACE --login                    # Interactive login
    HUGGINGFACE --token <token>           # Set token directly
    HUGGINGFACE --status                  # Check authentication status
    HUGGINGFACE --logout                  # Logout and clear credentials
    HUGGINGFACE --whoami                  # Show current user info
    HUGGINGFACE --test                    # Test authentication
    HUGGINGFACE --help                    # Show help
"""

import os
import sys
import json
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Any

def ensure_huggingface_hub():
    """确保huggingface_hub已安装"""
    try:
        import huggingface_hub
        return True
    except ImportError:
        print(f"Installing huggingface_hub...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", 
                "huggingface_hub", "--quiet"
            ])
            import huggingface_hub
            return True
        except Exception as e:
            return False, f"Failed to install huggingface_hub: {e}"

def get_hf_token_path():
    """获取HuggingFace token文件路径"""
    hf_home = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
    return Path(hf_home) / "token"

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_json_output(data: Dict[str, Any]):
    """写入JSON格式输出（用于RUN --show）"""
    if is_run_environment():
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        # 非RUN环境，使用友好的输出格式
        if data.get("success"):
            print(f"{data.get('message', 'Operation successful')}")
            if 'details' in data:
                for key, value in data['details'].items():
                    print(f"   {key}: {value}")
        else:
            print(f"Error: {data.get('error', 'Operation failed')}")

def login_interactive():
    """交互式登录HuggingFace"""
    try:
        ensure_result = ensure_huggingface_hub()
        if ensure_result is not True:
            return {"success": False, "error": ensure_result[1]}
        
        from huggingface_hub import login
        
        print(f"🤗 HuggingFace Interactive Login")
        print(f"Please visit https://huggingface.co/settings/tokens to get your token")
        print(f"You can create a new token or use an existing one.")
        print()
        
        token = input("Enter your HuggingFace token: ").strip()
        
        if not token:
            return {"success": False, "error": "No token provided"}
        
        try:
            login(token=token, add_to_git_credential=True)
            return {
                "success": True,
                "message": "Successfully logged in to HuggingFace",
                "details": {
                    "token_saved": "Yes",
                    "git_credential": "Added"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Login failed: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"Interactive login failed: {str(e)}"}

def set_token(token: str):
    """设置HuggingFace token"""
    try:
        ensure_result = ensure_huggingface_hub()
        if ensure_result is not True:
            return {"success": False, "error": ensure_result[1]}
        
        from huggingface_hub import login
        
        if not token:
            return {"success": False, "error": "Token cannot be empty"}
        
        try:
            login(token=token, add_to_git_credential=True)
            return {
                "success": True,
                "message": "Token set successfully",
                "details": {
                    "token_length": len(token),
                    "token_prefix": token[:8] + "..." if len(token) > 8 else token,
                    "git_credential": "Added"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to set token: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"Token setting failed: {str(e)}"}

def check_status():
    """检查HuggingFace认证状态"""
    try:
        ensure_result = ensure_huggingface_hub()
        if ensure_result is not True:
            return {"success": False, "error": ensure_result[1]}
        
        from huggingface_hub import HfApi
        
        api = HfApi()
        
        try:
            # 尝试获取用户信息来验证token
            user_info = api.whoami()
            
            token_path = get_hf_token_path()
            token_exists = token_path.exists()
            
            return {
                "success": True,
                "message": "HuggingFace authentication active",
                "details": {
                    "authenticated": "Yes",
                    "username": user_info.get("name", "Unknown"),
                    "email": user_info.get("email", "Unknown"),
                    "token_file": str(token_path),
                    "token_exists": token_exists
                }
            }
        except Exception as e:
            token_path = get_hf_token_path()
            return {
                "success": False,
                "error": "Not authenticated",
                "details": {
                    "authenticated": "No",
                    "token_file": str(token_path),
                    "token_exists": token_path.exists(),
                    "error_details": str(e)
                }
            }
            
    except Exception as e:
        return {"success": False, "error": f"Status check failed: {str(e)}"}

def logout():
    """登出HuggingFace"""
    try:
        ensure_result = ensure_huggingface_hub()
        if ensure_result is not True:
            return {"success": False, "error": ensure_result[1]}
        
        from huggingface_hub import logout
        
        try:
            logout()
            return {
                "success": True,
                "message": "Successfully logged out from HuggingFace",
                "details": {
                    "token_removed": "Yes",
                    "git_credential": "Removed"
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Logout failed: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"Logout operation failed: {str(e)}"}

def whoami():
    """显示当前用户信息"""
    try:
        ensure_result = ensure_huggingface_hub()
        if ensure_result is not True:
            return {"success": False, "error": ensure_result[1]}
        
        from huggingface_hub import HfApi
        
        api = HfApi()
        
        try:
            user_info = api.whoami()
            return {
                "success": True,
                "message": "Current HuggingFace user information",
                "details": {
                    "username": user_info.get("name", "Unknown"),
                    "fullname": user_info.get("fullname", "Unknown"),
                    "email": user_info.get("email", "Unknown"),
                    "avatar_url": user_info.get("avatarUrl", "Unknown"),
                    "plan": user_info.get("plan", "Unknown")
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Not authenticated or unable to get user info: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"User info retrieval failed: {str(e)}"}

def test_authentication():
    """测试HuggingFace认证"""
    try:
        ensure_result = ensure_huggingface_hub()
        if ensure_result is not True:
            return {"success": False, "error": ensure_result[1]}
        
        from huggingface_hub import HfApi
        
        api = HfApi()
        
        try:
            # 测试1: 获取用户信息
            user_info = api.whoami()
            username = user_info.get("name", "Unknown")
            
            # 测试2: 尝试列出一个公共模型的信息
            model_info = api.model_info("bert-base-uncased")
            
            return {
                "success": True,
                "message": "HuggingFace authentication test passed",
                "details": {
                    "user_test": "Passed",
                    "username": username,
                    "api_test": "Passed",
                    "model_access": "Can access public models",
                    "test_model": "bert-base-uncased"
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": "Authentication test failed",
                "details": {
                    "user_test": "❌ Failed",
                    "api_test": "❌ Failed",
                    "error_details": str(e)
                }
            }
            
    except Exception as e:
        return {"success": False, "error": f"Test execution failed: {str(e)}"}

def show_help():
    """显示帮助信息"""
    help_text = """
🤗 HuggingFace Credentials Management Tool

Usage:
    HUGGINGFACE --login                    # Interactive login
    HUGGINGFACE --token <token>           # Set token directly  
    HUGGINGFACE --status                  # Check authentication status
    HUGGINGFACE --logout                  # Logout and clear credentials
    HUGGINGFACE --whoami                  # Show current user info
    HUGGINGFACE --test                    # Test authentication
    HUGGINGFACE --help                    # Show this help

Examples:
    # Interactive login
    HUGGINGFACE --login
    
    # Set token directly
    HUGGINGFACE --token hf_xxxxxxxxxxxxxxxxxxxxxxxxx
    
    # Check if authenticated
    HUGGINGFACE --status
    
    # Test authentication
    HUGGINGFACE --test
    
    # Use with RUN for JSON output
    RUN --show HUGGINGFACE --status

Notes:
    - Get your token from: https://huggingface.co/settings/tokens
    - Tokens are stored in ~/.cache/huggingface/token
    - This tool is compatible with RUN --show for JSON output
    """
    
    if is_run_environment():
        return {
            "success": True,
            "message": "HuggingFace tool help",
            "help": help_text.strip()
        }
    else:
        print(help_text)
        return {"success": True}

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="HuggingFace Credentials Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # 处理RUN --show的情况
    if len(sys.argv) >= 2 and sys.argv[1] == "--show":
        sys.argv = [sys.argv[0]] + sys.argv[2:]  # 移除--show参数
    
    # 处理RUN传递的identifier参数（通常是第一个参数且包含时间戳）
    if len(sys.argv) >= 2 and '_' in sys.argv[1] and sys.argv[1].replace('_', '').replace('-', '').isalnum():
        # 这看起来像是RUN生成的identifier，移除它
        sys.argv = [sys.argv[0]] + sys.argv[2:]
    
    parser.add_argument("--login", action="store_true", help="Interactive login")
    parser.add_argument("--token", type=str, help="Set token directly")
    parser.add_argument("--status", action="store_true", help="Check authentication status")
    parser.add_argument("--logout", action="store_true", help="Logout and clear credentials")
    parser.add_argument("--whoami", action="store_true", help="Show current user info")
    parser.add_argument("--test", action="store_true", help="Test authentication")
    
    if len(sys.argv) == 1:
        # 没有参数，显示状态
        result = check_status()
        write_json_output(result)
        return 0 if result["success"] else 1
    
    try:
        args = parser.parse_args()
        
        if args.login:
            result = login_interactive()
            write_json_output(result)
            return 0 if result["success"] else 1
        elif args.token:
            result = set_token(args.token)
            write_json_output(result)
            return 0 if result["success"] else 1
        elif args.status:
            result = check_status()
            write_json_output(result)
            return 0 if result["success"] else 1
        elif args.logout:
            result = logout()
            write_json_output(result)
            return 0 if result["success"] else 1
        elif args.whoami:
            result = whoami()
            write_json_output(result)
            return 0 if result["success"] else 1
        elif args.test:
            result = test_authentication()
            write_json_output(result)
            return 0 if result["success"] else 1
        else:
            # 默认显示状态
            result = check_status()
            write_json_output(result)
            return 0 if result["success"] else 1
            
    except Exception as e:
        result = {"success": False, "error": f"Unexpected error: {str(e)}"}
        write_json_output(result)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 