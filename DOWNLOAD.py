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

def generate_run_identifier():
    """生成一个基于时间和随机数的唯一标识符"""
    import time
    import random
    
    timestamp = str(time.time())
    random_num = str(random.randint(100000, 999999))
    combined = f"{timestamp}_{random_num}_{os.getpid()}"
    
    return hashlib.sha256(combined.encode()).hexdigest()[:16]

def get_run_context():
    """获取 RUN 执行上下文信息"""
    run_identifier = os.environ.get('RUN_IDENTIFIER')
    output_file = os.environ.get('RUN_OUTPUT_FILE')
    
    if run_identifier:
        if not output_file:
            output_file = f"RUN_output/run_{run_identifier}.json"
        return {
            'in_run_context': True,
            'identifier': run_identifier,
            'output_file': output_file
        }
    elif output_file:
        try:
            filename = Path(output_file).stem
            if filename.startswith('run_'):
                identifier = filename[4:]
            else:
                identifier = generate_run_identifier()
        except:
            identifier = generate_run_identifier()
        
        return {
            'in_run_context': True,
            'identifier': identifier,
            'output_file': output_file
        }
    else:
        return {
            'in_run_context': False,
            'identifier': None,
            'output_file': None
        }

def write_to_json_output(data, run_context):
    """将结果写入到指定的 JSON 输出文件中"""
    if not run_context['in_run_context'] or not run_context['output_file']:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(run_context['output_file'])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 添加RUN相关信息
        data['run_identifier'] = run_context['identifier']
        
        with open(run_context['output_file'], 'w', encoding='utf-8') as f:
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

def download_file(url: str, destination: str, run_context):
    """下载文件"""
    
    # 验证URL
    if not url.startswith(('http://', 'https://')):
        error_data = {
            "success": False,
            "error": f"Invalid URL: {url}",
            "url": url
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"❌ Error: Invalid URL: {url}")
        return 1
    
    # 处理目标路径
    dest_path = Path(destination).expanduser().resolve()
    
    # 如果目标是目录，则在目录中创建文件
    if dest_path.is_dir() or destination.endswith('/'):
        dest_path = dest_path / get_filename_from_url(url)
    
    # 确保目标目录存在
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not run_context['in_run_context']:
        print(f"🚀 Downloading: {url}")
        print(f"📁 Destination: {dest_path}")
    
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
                    if not run_context['in_run_context'] and total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        print(f"\r📥 Progress: {progress:.1f}% ({downloaded_size}/{total_size} bytes)", end='', flush=True)
        
        if not run_context['in_run_context']:
            print(f"\n✅ Download completed successfully!")
            print(f"📄 File saved to: {dest_path}")
            print(f"📊 Size: {downloaded_size} bytes")
        
        success_data = {
            "success": True,
            "message": "Download completed successfully",
            "url": url,
            "destination": str(dest_path),
            "size": downloaded_size,
            "content_type": response.headers.get('content-type', 'unknown')
        }
        
        if run_context['in_run_context']:
            write_to_json_output(success_data, run_context)
        
        return 0
        
    except requests.exceptions.RequestException as e:
        error_data = {
            "success": False,
            "error": f"Download failed: {str(e)}",
            "url": url,
            "destination": str(dest_path)
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"\n❌ Download failed: {e}")
        return 1
    
    except Exception as e:
        error_data = {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "url": url,
            "destination": str(dest_path)
        }
        
        if run_context['in_run_context']:
            write_to_json_output(error_data, run_context)
        else:
            print(f"\n❌ Unexpected error: {e}")
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
    # 获取执行上下文
    run_context = get_run_context()
    
    # 解析命令行参数
    args = sys.argv[1:]
    
    if len(args) == 0:
        if run_context['in_run_context']:
            error_data = {
                "success": False,
                "error": "No URL provided. Usage: DOWNLOAD <url> [destination]"
            }
            write_to_json_output(error_data, run_context)
        else:
            print("❌ Error: No URL provided")
            print("Usage: DOWNLOAD <url> [destination]")
            print("Use --help for more information")
        return 1
    
    if args[0] in ['--help', '-h']:
        if run_context['in_run_context']:
            help_data = {
                "success": True,
                "message": "Help information",
                "help": "DOWNLOAD - Resource Download Tool"
            }
            write_to_json_output(help_data, run_context)
        else:
            show_help()
        return 0
    
    # 获取URL和目标路径
    url = args[0]
    destination = args[1] if len(args) > 1 else '.'
    
    return download_file(url, destination, run_context)

if __name__ == "__main__":
    sys.exit(main()) 