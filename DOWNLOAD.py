#!/usr/bin/env python3
"""
DOWNLOAD.py - Resource Download Tool
Downloads resources from URLs to specified destination folders
Python version with RUN environment detection
"""

import os
import sys
import json
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote
from typing import Optional

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def get_filename_from_url(url: str) -> str:
    """从URL中提取文件名"""
    parsed = urlparse(url)
    filename = unquote(parsed.path.split('/')[-1])
    
    # 如果没有文件名或者文件名为空，使用默认名称
    if not filename or filename == '/':
        filename = 'downloaded_file'
    
    return filename

def download_file(url: str, destination: str, command_identifier=None):
    """下载文件"""
    
    # 验证URL
    if not url.startswith(('http://', 'https://')):
        error_data = {
            "success": False,
            "error": f"Invalid URL: {url}",
            "url": url
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: Invalid URL: {url}")
        return 1
    
    # 处理目标路径
    dest_path = Path(destination).expanduser().resolve()
    
    # 如果目标是目录，则在目录中创建文件
    if dest_path.is_dir() or destination.endswith('/'):
        dest_path = dest_path / get_filename_from_url(url)
    
    # 确保目标目录存在
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not is_run_environment(command_identifier):
        print(f"Downloading: {url}")
        print(f"Destination: {dest_path}")
    
    try:
        # 创建会话
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # 发送请求
        response = session.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        # 获取文件大小
        total_size = int(response.headers.get('content-length', 0))
        
        # 下载文件
        downloaded_size = 0
        with open(dest_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    
                    # 显示进度（仅在直接调用时）
                    if not is_run_environment(command_identifier) and total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"Progress: {progress:.1f}% ({downloaded_size}/{total_size} bytes)", end='', flush=True)
        
        if not is_run_environment(command_identifier):
            print(f"Download completed successfully!")
            print(f"File saved to: {dest_path}")
            print(f"Size: {downloaded_size} bytes")
        
        success_data = {
            "success": True,
            "message": "Download completed successfully",
            "url": url,
            "destination": str(dest_path),
            "size": downloaded_size,
            "content_type": response.headers.get('content-type', 'unknown')
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(success_data, command_identifier)
        
        return 0
        
    except requests.exceptions.RequestException as e:
        error_data = {
            "success": False,
            "error": f"Download failed: {str(e)}",
            "url": url,
            "destination": str(dest_path)
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"\nError: Download failed: {e}")
        return 1
    
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "url": url,
            "destination": str(dest_path)
        }
        
        if is_run_environment(command_identifier):
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"\nError: Unexpected error: {e}")
        return 1

def show_help():
    """显示帮助信息"""
    help_text = """DOWNLOAD - Resource Download Tool

Usage: DOWNLOAD <url> [destination]

Arguments:
  url                  URL of the resource to download
  destination         Destination file path or directory (default: current directory)

Options:
  --help, -h          Show this help message

Examples:
  DOWNLOAD https://example.com/file.pdf                    # Download to current directory
  DOWNLOAD https://example.com/file.pdf ~/Desktop/        # Download to Desktop
  DOWNLOAD https://example.com/file.pdf ~/Desktop/my.pdf  # Download with custom name
  DOWNLOAD --help                                          # Show help

This tool will:
1. Download the resource from the specified URL
2. Save it to the specified destination (or current directory if not specified)
3. Show download progress and file information
4. Handle various file types and content types"""
    
    print(help_text)

def main():
    """主函数"""
    # 获取执行上下文和command_identifier
    args = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args and is_run_environment(args[0]):
        command_identifier = args[0]
        args = args[1:]  # 移除command_identifier，保留实际参数
    
    if len(args) == 0:
        if is_run_environment(command_identifier):
            error_data = {
                "success": False,
                "error": "No URL provided. Usage: DOWNLOAD <url> [destination]"
            }
            write_to_json_output(error_data, command_identifier)
        else:
            print(f"Error: No URL provided")
            print(f"Usage: DOWNLOAD <url> [destination]")
            print(f"Use --help for more information")
        return 1
    
    if args[0] in ['--help', '-h']:
        if is_run_environment(command_identifier):
            help_data = {
                "success": True,
                "message": "Help information",
                "help": "DOWNLOAD - Resource Download Tool"
            }
            write_to_json_output(help_data, command_identifier)
        else:
            show_help()
        return 0
    
    # 获取URL和目标路径
    url = args[0]
    destination = args[1] if len(args) > 1 else '.'
    
    return download_file(url, destination, command_identifier)

if __name__ == "__main__":
    sys.exit(main()) 