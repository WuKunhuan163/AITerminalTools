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
from ..google_drive_api import GoogleDriveService

class Validation:
    """Google Drive Shell Validation"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def verify_upload_success(self, expected_files, target_folder_id):
        """
        验证文件是否成功上传到目标文件夹
        
        Args:
            expected_files (list): 期望上传的文件名列表
            target_folder_id (str): 目标文件夹ID
            
        Returns:
            dict: 验证结果
        """
        try:
            if not self.drive_service:
                return {
                    "success": False,
                    "error": "Google Drive API 服务未初始化"
                }
            
            # 列出目标文件夹内容
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not result['success']:
                return {
                    "success": False,
                    "error": f"无法访问目标文件夹: {result['error']}"
                }
            
            # 检查每个期望的文件是否存在
            found_files = []
            missing_files = []
            existing_files = [f['name'] for f in result['files']]
            
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
            
            return {
                "success": len(missing_files) == 0,
                "found_files": found_files,
                "missing_files": missing_files,
                "total_expected": len(expected_files),
                "total_found": len(found_files)
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
