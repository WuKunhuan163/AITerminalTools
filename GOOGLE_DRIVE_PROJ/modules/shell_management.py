#!/usr/bin/env python3
"""
Google Drive Shell - Shell Management Module
从google_drive_shell.py重构而来的shell_management模块
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

class ShellManagement:
    """Google Drive Shell Shell Management"""

    def __init__(self, drive_service, main_instance=None):
        """初始化管理器"""
        self.drive_service = drive_service
        self.main_instance = main_instance  # 引用主实例以访问其他属性

    def load_shells(self):
        """加载远程shell配置"""
        try:
            if self.main_instance.shells_file.exists():
                with open(self.main_instance.shells_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        # 文件为空，返回默认配置
                        return {"shells": {}, "active_shell": None}
                    return json.loads(content)
            else:
                return {"shells": {}, "active_shell": None}
        except json.JSONDecodeError as e:
            print(f"⚠️ Shell配置文件损坏，重新创建: {e}")
            # 备份损坏的文件并创建新的
            backup_file = self.main_instance.shells_file.with_suffix('.bak')
            if self.main_instance.shells_file.exists():
                self.main_instance.shells_file.rename(backup_file)
            # 返回默认配置，下次保存时会创建新文件
            return {"shells": {}, "active_shell": None}
        except Exception as e:
            print(f"❌ 加载shell配置失败: {e}")
            return {"shells": {}, "active_shell": None}

    def save_shells(self, shells_data):
        """保存远程shell配置"""
        try:
            with open(self.main_instance.shells_file, 'w', encoding='utf-8') as f:
                json.dump(shells_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ 保存shell配置失败: {e}")
            return False

    def generate_shell_id(self):
        """生成shell ID"""
        timestamp = str(int(time.time() * 1000))
        random_str = os.urandom(8).hex()
        hash_input = f"{timestamp}_{random_str}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    def get_current_shell(self):
        """获取当前活跃的shell，如果没有则创建默认shell"""
        shells_data = self.load_shells()
        active_shell_id = shells_data.get("active_shell")
        
        if active_shell_id and active_shell_id in shells_data["shells"]:
            shell = shells_data["shells"][active_shell_id]
            # 更新最后访问时间
            shell["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            self.save_shells(shells_data)
            return shell
        
        # 如果没有活跃shell，创建默认shell
        return self._create_default_shell()

    def get_current_folder_id(self, current_shell=None):
        """
        获取当前shell的文件夹ID，如果没有则返回REMOTE_ROOT_FOLDER_ID
        
        Args:
            current_shell (dict, optional): 当前shell信息，如果为None则自动获取
            
        Returns:
            str: 当前文件夹ID
        """
        if current_shell is None:
            current_shell = self.main_instance.get_current_shell()
        
        if current_shell:
            return current_shell.get("current_folder_id", self.main_instance.REMOTE_ROOT_FOLDER_ID)
        else:
            return self.main_instance.REMOTE_ROOT_FOLDER_ID

    def _create_default_shell(self):
        """创建默认shell"""
        try:
            # 生成默认shell ID
            shell_id = "default_shell"
            shell_name = "default"
            
            # 改进的shell配置，简化结构并添加虚拟环境支持
            shell_config = {
                "id": shell_id,
                "name": shell_name,
                "current_path": "~",  # 当前逻辑路径
                "current_folder_id": self.main_instance.REMOTE_ROOT_FOLDER_ID,  # Google Drive文件夹ID
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S"),
                "venv_state": {
                    "active_env": None,  # 当前激活的虚拟环境名称
                    "pythonpath": "/env/python"  # 当前PYTHONPATH
                }
            }
            
            # 加载现有shells数据
            shells_data = self.load_shells()
            
            # 添加默认shell
            shells_data["shells"][shell_id] = shell_config
            shells_data["active_shell"] = shell_id
            
            # 保存配置
            self.save_shells(shells_data)
            
            return shell_config
            
        except Exception as e:
            print(f"创建默认shell时出错: {e}")
            # 返回最基本的shell配置
            return {
                "id": "emergency_shell",
                "name": "emergency",
                "folder_id": self.main_instance.REMOTE_ROOT_FOLDER_ID,
                "current_path": "~",
                "current_folder_id": self.main_instance.REMOTE_ROOT_FOLDER_ID,
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "active",
                "type": "emergency"
            }

    def create_shell(self, name=None, folder_id=None):
        """创建新的远程shell"""
        try:
            shell_id = self.generate_shell_id()
            shell_name = name or f"shell_{shell_id[:8]}"
            created_time = time.strftime("%Y-%m-%d %H:%M:%S")
            
            shell_config = {
                "id": shell_id,
                "name": shell_name,
                "folder_id": folder_id or self.main_instance.REMOTE_ROOT_FOLDER_ID,
                "current_path": "~",
                "current_folder_id": self.main_instance.REMOTE_ROOT_FOLDER_ID,
                "created_time": created_time,
                "last_accessed": created_time,
                "status": "active"
            }
            
            shells_data = self.load_shells()
            shells_data["shells"][shell_id] = shell_config
            shells_data["active_shell"] = shell_id
            
            if self.save_shells(shells_data):
                # 生成远程命令来初始化shell环境变量
                # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
                current_venv_file = f"{self.main_instance.REMOTE_ENV}/current_venv_{shell_id}.txt"
                commands = [
                    f"mkdir -p {tmp_dir}",
                    f"rm -f {current_venv_file}",  # 清除虚拟环境状态
                    "export PYTHONPATH=/env/python",  # 重置为默认PYTHONPATH
                    f"echo 'Shell {shell_name} created with default environment'"
                ]
                
                command = " && ".join(commands) + ''
                
                # 执行远程命令来初始化环境
                result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
                
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "message": f"✅ 创建远程shell成功: {shell_name}",
                    "remote_command": command,
                    "remote_result": result
                }
            else:
                return {"success": False, "error": "保存shell配置失败"}
                
        except Exception as e:
            return {"success": False, "error": f"创建shell时出错: {e}"}

    def list_shells(self):
        """列出所有shell"""
        try:
            shells_data = self.load_shells()
            active_id = shells_data.get("active_shell")
            
            shells_list = []
            for shell_id, shell_info in shells_data["shells"].items():
                shell_info["is_active"] = (shell_id == active_id)
                shells_list.append(shell_info)
            
            return {
                "success": True,
                "shells": shells_list,
                "active_shell": active_id,
                "total": len(shells_list)
            }
            
        except Exception as e:
            return {"success": False, "error": f"列出shell时出错: {e}"}

    def checkout_shell(self, shell_id):
        """切换到指定shell"""
        try:
            shells_data = self.load_shells()
            
            if shell_id not in shells_data["shells"]:
                return {"success": False, "error": f"Shell不存在: {shell_id}"}
            
            shells_data["active_shell"] = shell_id
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 切换shell时重置到根目录
            shells_data["shells"][shell_id]["current_path"] = "~"
            shells_data["shells"][shell_id]["current_folder_id"] = self.main_instance.REMOTE_ROOT_FOLDER_ID
            
            if self.save_shells(shells_data):
                shell_name = shells_data["shells"][shell_id]["name"]
                
                # 生成远程命令来恢复shell的虚拟环境状态
                # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
                current_venv_file = f"{self.main_instance.REMOTE_ENV}/current_venv_{shell_id}.txt"
                
                # 检查该shell是否有激活的虚拟环境
                try:
                    current_env_result = self.main_instance.cmd_cat(current_venv_file)
                    if current_env_result.get("success") and current_env_result.get("output"):
                        # 有激活的虚拟环境，恢复PYTHONPATH
                        env_name = current_env_result["output"].strip()
                        env_path = f"{self.main_instance.REMOTE_ENV}/{env_name}"
                        pythonpath = f"/env/python:{env_path}"
                        env_message = f"Restored virtual environment: {env_name}"
                    else:
                        # 没有激活的虚拟环境，使用默认PYTHONPATH
                        pythonpath = "/env/python"
                        env_message = "Using default environment"
                except Exception:
                    # 出错时使用默认环境
                    pythonpath = "/env/python"
                    env_message = "Using default environment (fallback)"
                
                commands = [
                    f"export PYTHONPATH={pythonpath}",
                    f"echo 'Switched to shell: {shell_name}'",
                    f"echo '{env_message}'"
                ]
                
                command = " && ".join(commands) + ''
                
                # 执行远程命令来设置环境
                result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
                
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "current_path": "~",
                    "message": f"✅ 已切换到shell: {shell_name}，路径重置为根目录",
                    "remote_command": command,
                    "remote_result": result
                }
            else:
                return {"success": False, "error": "保存shell状态失败"}
                
        except Exception as e:
            return {"success": False, "error": f"切换shell时出错: {e}"}

    def terminate_shell(self, shell_id):
        """终止指定shell"""
        try:
            shells_data = self.load_shells()
            
            if shell_id not in shells_data["shells"]:
                return {"success": False, "error": f"Shell不存在: {shell_id}"}
            
            shell_name = shells_data["shells"][shell_id]["name"]
            
            # 生成远程命令来清理shell相关的环境变量文件
            # Direct storage in REMOTE_ENV, no .tmp subdirectory needed
            current_venv_file = f"{self.main_instance.REMOTE_ENV}/current_venv_{shell_id}.txt"
            commands = [
                f"rm -f {current_venv_file}",  # 删除该shell的虚拟环境状态文件
                "export PYTHONPATH=/env/python",  # 重置为默认PYTHONPATH
                f"echo 'Shell {shell_name} terminated and environment cleaned'"
            ]
            
            command = " && ".join(commands) + ''
            
            # 执行远程命令来清理环境
            result = self.main_instance.execute_generic_remote_command("bash", ["-c", command])
            
            del shells_data["shells"][shell_id]
            
            if shells_data["active_shell"] == shell_id:
                shells_data["active_shell"] = None
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "message": f"✅ 已终止shell: {shell_name}",
                    "remote_command": command,
                    "remote_result": result
                }
            else:
                return {"success": False, "error": "保存shell状态失败"}
                
        except Exception as e:
            return {"success": False, "error": f"终止shell时出错: {e}"}

    def exit_shell(self):
        """退出当前shell"""
        try:
            current_shell = self.main_instance.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            shells_data = self.load_shells()
            shells_data["active_shell"] = None
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "shell_name": current_shell["name"],
                    "message": f"✅ 已退出远程shell: {current_shell['name']}"
                }
            else:
                return {"success": False, "error": "保存shell状态失败"}
                
        except Exception as e:
            return {"success": False, "error": f"退出shell时出错: {e}"}
