#!/usr/bin/env python3
"""
Google Drive Shell - Validation Module
从google_drive_shell.py重构而来的validation模块
"""

import os
import sys
import json
import time
import hashlib
import warnings
import subprocess
import shutil
import zipfile
import tempfile
from pathlib import Path
import platform
import psutil
from typing import Dict
try:
    from ..google_drive_api import GoogleDriveService
except ImportError:
    from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService

class Validation:
    """Google Drive Shell Validation"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def verify_upload_success_by_ls(self, expected_files, target_path, current_shell):
        """
        使用GDS ls机制验证文件是否成功上传
        
        Args:
            expected_files (list): 期望上传的文件名列表
            target_path (str): 目标路径（相对于当前shell）
            current_shell (dict): 当前shell信息
            
        Returns:
            dict: 验证结果
        """
        import time
        from .remote_commands import debug_print
        
        try:
            debug_print(f"🔧 DEBUG: Starting ls-based validation for {len(expected_files)} files")
            debug_print(f"🔧 DEBUG: target_path='{target_path}', current_path='{current_shell.get('current_path', '~')}'")
            
            # 构造目标目录的完整逻辑路径
            current_path = current_shell.get("current_path", "~")
            if target_path == "." or target_path == "":
                # 当前目录
                search_path = current_path
            elif target_path.startswith("~/"):
                # 绝对路径
                search_path = target_path
            elif target_path.startswith("/"):
                # 系统绝对路径（简化处理）
                search_path = target_path
            else:
                # 检查target_path是否是文件名（包含扩展名或不包含路径分隔符）
                if "/" not in target_path and ("." in target_path or target_path in expected_files):
                    # 这是一个文件名，应该在当前目录中查找
                    search_path = current_path
                    debug_print(f"🔧 DEBUG: target_path '{target_path}' identified as filename, searching in current directory: {search_path}")
                else:
                    # 相对路径，拼接到当前路径
                    if current_path == "~":
                        search_path = f"~/{target_path}"
                    else:
                        search_path = f"{current_path}/{target_path}"
            
            debug_print(f"🔧 DEBUG: constructed search_path='{search_path}'")
            
            # 使用ls命令检查目录内容
            ls_result = self.main_instance.file_operations.cmd_ls(path=search_path)
            debug_print(f"🔧 DEBUG: ls_result success={ls_result.get('success')}")
            
            if not ls_result.get("success"):
                debug_print(f"🔧 DEBUG: ls failed: {ls_result.get('error')}")
                return {
                    "success": False,
                    "error": f"无法访问目标目录 {search_path}: {ls_result.get('error')}",
                    "found_files": [],
                    "missing_files": expected_files,
                    "total_found": 0,
                    "total_expected": len(expected_files)
                }
            
            # 获取目录中的文件列表
            files_in_dir = ls_result.get("files", [])
            file_names_in_dir = [f.get("name") for f in files_in_dir if f.get("name")]
            debug_print(f"🔧 DEBUG: found files in directory: {file_names_in_dir}")
            
            # 检查每个期望的文件是否存在
            found_files = []
            missing_files = []
            
            for expected_file in expected_files:
                if expected_file in file_names_in_dir:
                    found_files.append(expected_file)
                    debug_print(f"🔧 DEBUG: ✅ Found file: {expected_file}")
                else:
                    missing_files.append(expected_file)
                    debug_print(f"🔧 DEBUG: ❌ Missing file: {expected_file}")
            
            success = len(found_files) == len(expected_files)
            debug_print(f"🔧 DEBUG: Validation result: {len(found_files)}/{len(expected_files)} files found")
            
            return {
                "success": success,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_found": len(found_files),
                "total_expected": len(expected_files),
                "search_path": search_path
            }
            
        except Exception as e:
            debug_print(f"🔧 DEBUG: Exception in ls-based validation: {e}")
            return {
                "success": False,
                "error": f"验证过程中出错: {e}",
                "found_files": [],
                "missing_files": expected_files,
                "total_found": 0,
                "total_expected": len(expected_files)
            }

    def verify_upload_success(self, expected_files, target_folder_id):
        """
        验证文件是否成功上传到目标文件夹
        
        Args:
            expected_files (list): 期望上传的文件名列表
            target_folder_id (str): 目标文件夹ID
            
        Returns:
            dict: 验证结果
        """
        import time
        from .remote_commands import debug_print
        
        try:
            debug_print(f"🔧 DEBUG: verify_upload_success called with expected_files={expected_files}, target_folder_id='{target_folder_id}'")
            
            if not self.drive_service:
                return {
                    "success": False,
                    "error": "Google Drive API 服务未初始化"
                }
            
            # 重试机制：最多60秒，每秒重试一次
            max_attempts = 60
            attempt = 0
            
            print("⏳ Validating the result ...", end="", flush=True)
            
            while attempt < max_attempts:
                attempt += 1
                
                # 列出目标文件夹内容
                result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
                if not result['success']:
                    debug_print(f"🔧 DEBUG: list_files failed for folder_id='{target_folder_id}', error: {result.get('error')}")
                    if attempt == max_attempts:
                        print(f"\n❌ 验证失败: 无法访问目标文件夹")
                        return {
                            "success": False,
                            "error": f"无法访问目标文件夹: {result['error']}"
                        }
                    print(".", end="", flush=True)
                    time.sleep(1)
                    continue
                
                # 检查每个期望的文件是否存在
                found_files = []
                missing_files = []
                existing_files = [f['name'] for f in result['files']]
                debug_print(f"🔧 DEBUG: found {len(existing_files)} files in target folder: {existing_files}")
                
                for filename in expected_files:
                    if filename in existing_files:
                        # 找到对应的文件信息
                        file_info = next(f for f in result['files'] if f['name'] == filename)
                        file_id = file_info['id']
                        found_files.append({
                            "name": filename,
                            "id": file_id,
                            "size": file_info.get('size', 'Unknown'),
                            "modified": file_info.get('modifiedTime', 'Unknown'),
                            "url": f"https://drive.google.com/file/d/{file_id}/view"
                        })
                    else:
                        missing_files.append(filename)
                
                if len(missing_files) == 0:
                    return {
                        "success": True,
                        "found_files": found_files,
                        "missing_files": missing_files,
                        "total_expected": len(expected_files),
                        "total_found": len(found_files),
                        "attempts": attempt
                    }
                
                # 如果还有文件没找到且未超时，等待1秒后重试
                if attempt < max_attempts:
                    print(".", end="", flush=True)
                    time.sleep(1)
            
            # 超时后返回最后一次的结果
            print(f"\n⚠️ 验证超时: {len(missing_files)} 个文件未找到")
            return {
                "success": len(missing_files) == 0,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_expected": len(expected_files),
                "total_found": len(found_files),
                "attempts": max_attempts,
                "timeout": True
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"验证上传结果时出错: {e}"
            }

    def _create_error_result(self, error_message):
        """
        创建标准的错误返回结果
        
        Args:
            error_message (str): 错误消息
            
        Returns:
            dict: 标准错误结果字典
        """
        return {"success": False, "error": error_message}

    def _create_success_result(self, message=None, **kwargs):
        """
        创建标准的成功返回结果
        
        Args:
            message (str, optional): 成功消息
            **kwargs: 其他要包含的键值对
            
        Returns:
            dict: 标准成功结果字典
        """
        result = {"success": True}
        if message:
            result["message"] = message
        result.update(kwargs)
        return result

    def _handle_exception(self, e, operation_name, default_message=None):
        """
        通用异常处理方法
        
        Args:
            e (Exception): 异常对象
            operation_name (str): 操作名称
            default_message (str, optional): 默认错误消息
            
        Returns:
            dict: 错误结果字典
        """
        if default_message:
            error_msg = f"{default_message}: {str(e)}"
        else:
            error_msg = f"{operation_name}时出错: {str(e)}"
        return self._create_error_result(error_msg)

    def _format_tkinter_result_message(self, result, default_success_msg="操作成功", default_error_msg="操作失败"):
        """
        统一处理tkinter窗口结果的消息格式化
        
        Args:
            result (dict): tkinter窗口返回的结果
            default_success_msg (str): 默认成功消息
            default_error_msg (str): 默认错误消息
            
        Returns:
            str: 格式化后的消息
        """
        if result.get("success"):
            return result.get("message", default_success_msg)
        else:
            # 处理不同类型的失败
            if result.get("user_reported_failure"):
                error_info = result.get("error_info")
                if error_info and error_info.strip():
                    return f"执行失败：{error_info}"
                else:
                    return "执行失败"
            elif result.get("cancelled"):
                return "用户取消操作"
            elif result.get("window_error"):
                error_info = result.get("error_info")
                if error_info and error_info.strip():
                    return f"窗口显示错误：{error_info}"
                else:
                    return "窗口显示错误"
            else:
                return result.get("message", result.get("error", default_error_msg))

    def _check_remote_file_exists_absolute(self, file_path):
        """
        检查远端文件是否存在（绝对路径）
        
        Args:
            file_path (str): 绝对路径的文件路径（如~/tmp/filename.json）
            
        Returns:
            dict: 检查结果
        """
        try:
            # 解析路径
            if "/" in file_path:
                dir_path, filename = file_path.rsplit("/", 1)
            else:
                dir_path = "~"
                filename = file_path
            
            # 列出目录内容
            ls_result = self.main_instance.cmd_ls(dir_path)
            
            if not ls_result.get("success"):
                return {"exists": False, "error": f"无法访问目录: {dir_path}"}
            
            # 检查文件是否在列表中
            files = ls_result.get("files", [])
            file_exists = any(f.get("name") == filename for f in files)
            
            return {"exists": file_exists}
            
        except Exception as e:
            return {"exists": False, "error": f"检查文件存在性时出错: {str(e)}"}

    def _check_remote_file_exists(self, file_path):
        """
        检查远端文件是否存在
        
        Args:
            file_path (str): 相对于当前目录的文件路径
            
        Returns:
            dict: 检查结果
        """
        try:
            # 使用ls命令检查文件是否存在
            # 解析路径
            if "/" in file_path:
                dir_path, filename = file_path.rsplit("/", 1)
            else:
                dir_path = "."
                filename = file_path
            
            # 列出目录内容
            ls_result = self.main_instance.cmd_ls(dir_path)
            
            if not ls_result.get("success"):
                return {"exists": False, "error": f"无法访问目录: {dir_path}"}
            
            # 检查文件是否在列表中
            files = ls_result.get("files", [])
            file_exists = any(f.get("name") == filename for f in files)
            
            return {"exists": file_exists}
            
        except Exception as e:
            return {"exists": False, "error": f"检查文件存在性时出错: {str(e)}"}
