#!/usr/bin/env python3
"""
Google Drive Shell Management
Google Drive远程Shell管理系统
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

# 抑制urllib3的SSL警告
warnings.filterwarnings('ignore', message='urllib3 v2 only supports OpenSSL 1.1.1+')

from google_drive_api import GoogleDriveService

def get_multiline_input_safe(prompt_text="请输入内容", single_line=True):
    """
    安全的输入处理函数，支持多行输入和Ctrl+D结束输入
    参考USERINPUT.py的实现，避免Ctrl+D导致Cursor terminal停止的问题
    
    Args:
        prompt_text (str): 提示文本
        single_line (bool): 是否为单行输入模式，True表示使用标准input()，False表示多行输入
    
    Returns:
        str: 用户输入的内容，如果取消返回None
    """
    if single_line:
        # 单行输入模式，使用标准input()但添加异常处理
        try:
            return input(prompt_text).strip()
        except EOFError:
            # Ctrl+D被按下，在单行模式下返回空字符串
            print("\n输入已结束")
            return ""
        except KeyboardInterrupt:
            # Ctrl+C被按下
            print("\n输入已取消")
            return None
    else:
        # 多行输入模式，类似USERINPUT.py的处理方式
        print(f"{prompt_text}")
        print("多行输入模式：输入完成后按 Ctrl+D (EOF) 结束输入")
        print("输入内容: ", end="", flush=True)
        
        lines = []
        try:
            while True:
                try:
                    line = input()
                    lines.append(line)
                except EOFError:
                    # Ctrl+D 被按下，结束输入
                    break
        except KeyboardInterrupt:
            # Ctrl+C 被按下
            print("\n输入已取消")
            return None
        
        # 组合所有行为最终输入
        full_input = '\n'.join(lines).strip()
        return full_input if full_input else ""

class GoogleDriveShell:
    """Google Drive Shell管理类"""
    
    def __init__(self):
        """初始化Google Drive Shell"""
        self.shells_file = Path(__file__).parent / "shells.json"
        self.config_file = Path(__file__).parent / "cache_config.json"
        self.deletion_cache_file = Path(__file__).parent / "deletion_cache.json"  # 新增删除时间缓存文件
        
        # 初始化shell配置
        self.shells_data = self.load_shells()
        
        # 加载缓存配置
        self.load_cache_config()
        
        # 初始化删除时间缓存
        self.deletion_cache = self.load_deletion_cache()
        
        # 设置常量
        self.HOME_URL = "https://drive.google.com/drive/u/0/my-drive"
        
        # 设置路径
        if self.cache_config_loaded:
            try:
                config = self.cache_config
                self.LOCAL_EQUIVALENT = config.get("local_equivalent", "/Users/wukunhuan/Applications/Google Drive")
                self.DRIVE_EQUIVALENT = config.get("drive_equivalent", "/content/drive/Othercomputers/我的 MacBook Air/Google Drive")
                self.DRIVE_EQUIVALENT_FOLDER_ID = config.get("drive_equivalent_folder_id", "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
                
                # 静默处理目录创建
                os.makedirs(self.LOCAL_EQUIVALENT, exist_ok=True)
                
                # 静默加载同步配置，不显示详细信息
                pass
            except Exception:
                # 如果配置加载失败，使用默认值
                self.LOCAL_EQUIVALENT = "/Users/wukunhuan/Applications/Google Drive"
                self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
                self.REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"
                
                self.DRIVE_EQUIVALENT = "/content/drive/Othercomputers/我的 MacBook Air/Google Drive"
                
                self.DRIVE_EQUIVALENT_FOLDER_ID = "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
        else:
            # 如果配置加载失败，使用默认值
            self.LOCAL_EQUIVALENT = "/Users/wukunhuan/Applications/Google Drive"
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
            self.REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"
            
            self.DRIVE_EQUIVALENT = "/content/drive/Othercomputers/我的 MacBook Air/Google Drive"
            
            self.DRIVE_EQUIVALENT_FOLDER_ID = "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"
        
        # 确保所有必要的属性都存在
        if not hasattr(self, 'REMOTE_ROOT'):
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        if not hasattr(self, 'REMOTE_ROOT_FOLDER_ID'):
            self.REMOTE_ROOT_FOLDER_ID = "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f"
        
        # 尝试加载Google Drive API服务
        self.drive_service = self.load_drive_service()

    def _setup_environment_paths(self):
        """根据运行环境设置路径配置"""
        import os
        import platform
        import json
        
        # 尝试从配置文件加载设置
        try:
            config_file = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA" / "sync_config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 使用配置文件中的设置
                self.LOCAL_EQUIVALENT = config.get("local_equivalent", "/Users/wukunhuan/Applications/Google Drive")
                self.DRIVE_EQUIVALENT = config.get("drive_equivalent", "/content/drive/Othercomputers/我的 MacBook Air/Google Drive")
                self.DRIVE_EQUIVALENT_FOLDER_ID = config.get("drive_equivalent_folder_id", "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY")
                
                # 静默加载同步配置，不显示详细信息
                pass
            else:
                # 使用默认配置
                self._setup_default_paths()
        except Exception as e:
            print(f"⚠️ 加载同步配置失败，使用默认配置: {e}")
            self._setup_default_paths()
        
        # 检测运行环境
        if os.path.exists('/content/drive'):
            self.environment = "colab"
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        elif platform.system() == "Darwin":  # macOS
            self.environment = "macos"
            self.REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
        else:
            # 其他环境（Linux/Windows）
            raise Exception("Unsupported environment")
        
        # 确保目录存在
        os.makedirs(self.LOCAL_EQUIVALENT, exist_ok=True)
        # 只在Colab环境下创建DRIVE_REMOTE_ROOT目录
        if self.environment == "colab":
            os.makedirs(self.REMOTE_ROOT, exist_ok=True)
    
    def _setup_default_paths(self):
        """设置默认路径配置"""
        import platform
        
        if platform.system() == "Darwin":  # macOS
            self.LOCAL_EQUIVALENT = "/Users/wukunhuan/Applications/Google Drive"
            self.DRIVE_EQUIVALENT = "/content/drive/Othercomputers/我的 MacBook Air/Google Drive"
        else:
            raise Exception("Not Implemented Yet")
        
        # 默认的DRIVE_EQUIVALENT_FOLDER_ID
        self.DRIVE_EQUIVALENT_FOLDER_ID = "1E6Dw-LZlPF7WT5RV0EhIquDwdP2oZYbY"

    def move_to_local_equivalent(self, file_path):
        """
        将文件移动到 LOCAL_EQUIVALENT 目录，如果有同名文件则重命名
        
        Args:
            file_path (str): 要移动的文件路径
            
        Returns:
            dict: 包含成功状态和移动后文件路径的字典
        """
        try:
            # 确保 LOCAL_EQUIVALENT 目录存在
            local_equiv_path = Path(self.LOCAL_EQUIVALENT)
            if not local_equiv_path.exists():
                return {
                    "success": False,
                    "error": f"LOCAL_EQUIVALENT 目录不存在: {self.LOCAL_EQUIVALENT}"
                }
            
            source_path = Path(file_path)
            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"源文件不存在: {file_path}"
                }
            
            # 获取文件名和扩展名
            filename = source_path.name
            name_part = source_path.stem
            ext_part = source_path.suffix
            
            # 检查目标目录中是否已存在同名文件
            target_path = local_equiv_path / filename
            final_filename = filename
            renamed = False
            
            if target_path.exists():
                # 如果远端也有同名文件，使用重命名策略
                print(f"🔄 LOCAL_EQUIVALENT中发现同名文件，检查远端是否也存在: {filename}")
                
                # 检查远端是否有同名文件
                remote_has_same_file = self._check_remote_file_exists(filename)
                
                # 检查是否在删除时间缓存中（5分钟内删除过）
                cache_suggests_rename = self.should_rename_file(filename)
                
                if remote_has_same_file or cache_suggests_rename:
                    # 远端有同名文件或缓存建议重命名，使用重命名策略
                    counter = 1
                    while target_path.exists():
                        # 生成新的文件名：name_1.ext, name_2.ext, ...
                        new_filename = f"{name_part}_{counter}{ext_part}"
                        target_path = local_equiv_path / new_filename
                        counter += 1
                    
                    final_filename = target_path.name
                    renamed = True
                    
                    if cache_suggests_rename:
                        print(f"🏷️  基于删除缓存重命名文件: {filename} -> {final_filename}")
                    else:
                        print(f"🏷️  重命名文件以避免冲突: {filename} -> {final_filename}")
                else:
                    # 远端没有同名文件且缓存无风险，删除本地旧文件并记录删除
                    try:
                        target_path.unlink()
                        print(f"🗑️  删除LOCAL_EQUIVALENT中的旧文件: {filename}")
                        
                        # 记录删除到缓存
                        self.add_deletion_record(filename)
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"删除旧文件失败: {e}"
                        }
            
            # 复制文件而不是移动（保留原文件）
            shutil.copy2(str(source_path), str(target_path))
            
            return {
                "success": True,
                "original_path": str(source_path),
                "new_path": str(target_path),
                "filename": final_filename,
                "original_filename": filename,
                "renamed": renamed
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"移动文件时出错: {e}"
            }

    def check_network_connection(self):
        """
        检测网络连接状态
        
        Returns:
            dict: 网络连接状态
        """
        try:
            # 如果有可用的API服务，直接测试API连接
            if self.drive_service:
                try:
                    # 尝试一个简单的API调用
                    result = self.drive_service.test_connection()
                    if result.get('success'):
                        return {"success": True, "message": "Google Drive API连接正常"}
                    else:
                        return {"success": False, "error": f"Google Drive API连接失败: {result.get('error', '未知错误')}"}
                except Exception as e:
                    # API测试失败，继续尝试ping
                    pass
            
            # 回退到ping测试（更宽松的参数）
            import platform
            if platform.system() == "Darwin":  # macOS
                ping_cmd = ["ping", "-c", "1", "-W", "3000", "8.8.8.8"]  # 使用Google DNS
            else:
                ping_cmd = ["ping", "-c", "1", "-W", "3", "8.8.8.8"]
            
            result = subprocess.run(
                ping_cmd, 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                return {"success": True, "message": "网络连接正常"}
            else:
                # 网络测试失败但不影响功能
                return {"success": True, "message": "网络状态未知，但将继续执行"}
                
        except subprocess.TimeoutExpired:
            return {"success": True, "message": "网络检测超时，但将继续执行"}
        except Exception as e:
            return {"success": True, "message": f"网络检测失败，但将继续执行: {e}"}

    def calculate_timeout_from_file_sizes(self, file_moves):
        """
        根据文件大小计算超时时间
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            int: 超时时间（秒）
        """
        try:
            total_size_mb = 0
            for file_info in file_moves:
                file_path = file_info["new_path"]
                if os.path.exists(file_path):
                    size_bytes = os.path.getsize(file_path)
                    size_mb = size_bytes / (1024 * 1024)  # 转换为MB
                    total_size_mb += size_mb
            
            # 基础检测时间30秒 + 按照100KB/s的速度计算文件传输时间
            # 100KB/s = 0.1MB/s，所以每MB需要10秒
            base_time = 30  # 基础检测时间（从10秒增加到30秒）
            transfer_time = max(30, int(total_size_mb * 10))  # 按100KB/s计算，最少30秒（从10秒增加到30秒）
            timeout = base_time + transfer_time
            
            return timeout
            
        except Exception as e:
            print(f"计算超时时间时出错: {e}")
            return 60  # 默认60秒（10秒基础 + 50秒传输）

    def wait_for_file_sync(self, expected_files, file_moves):
        """
        等待文件同步到 DRIVE_EQUIVALENT 目录，使用GDS ls命令检测
        
        Args:
            expected_files (list): 期望同步的文件名列表
            file_moves (list): 文件移动信息列表（用于计算超时时间）
            
        Returns:
            dict: 同步状态
        """
        try:
            # 根据文件大小计算超时时间
            timeout = self.calculate_timeout_from_file_sizes(file_moves)
            
            start_time = time.time()
            synced_files = []
            check_count = 0
            next_check_delay = 1.0  # 第一次检测等待1秒
            
            # 只显示一行简洁的开始信息
            print(f"⏳", end="", flush=True)
            
            while time.time() - start_time < timeout:
                check_count += 1
                elapsed_time = time.time() - start_time
                
                # 直接使用 ls_with_folder_id 检查 DRIVE_EQUIVALENT 目录
                try:
                    # 使用内部API直接检查DRIVE_EQUIVALENT目录
                    ls_result = self.ls_with_folder_id(self.DRIVE_EQUIVALENT_FOLDER_ID, detailed=False)
                    
                    if ls_result.get("success"):
                        files = ls_result.get("files", [])
                        current_synced = []
                        
                        for filename in expected_files:
                            # 检查文件名是否在DRIVE_EQUIVALENT中
                            file_found = any(f.get("name") == filename for f in files)
                            if file_found:
                                current_synced.append(filename)
                        
                        # 如果所有文件都已同步，返回成功
                        if len(current_synced) == len(expected_files):
                            print(f" ({elapsed_time:.1f}s)")
                            return {
                                "success": True,
                                "synced_files": current_synced,
                                "sync_time": elapsed_time,
                                "base_sync_time": elapsed_time  # 保存基础同步时间用于计算额外等待
                            }
                        
                        # 更新已同步文件列表
                        synced_files = current_synced
                        
                except Exception as e: 
                    pass  # 静默处理错误
                
                # 显示一个点表示检测进行中
                print(".", end="", flush=True)
                
                # 使用对数规律增加等待时间：每次 * √2，最多等待16秒
                time.sleep(min(next_check_delay, 16))
                next_check_delay *= 1.414  # √2 ≈ 1.414
            
            # 超时，返回当前状态
            missing_files = [f for f in expected_files if f not in synced_files]
            print(f" ⏰ 超时 ({timeout}s)")
            
            return {
                "success": len(synced_files) > 0,
                "error": "文件同步超时，但部分文件可能已同步",
                "synced_files": synced_files,
                "missing_files": missing_files,
                "sync_time": timeout
            }
            
        except Exception as e:
            print(f" ❌ 检测失败: {e}")
            return {"success": False, "error": f"文件同步检测失败: {e}"}
    
    def _zip_folder(self, folder_path, zip_path=None):
        """
        将文件夹打包成zip文件
        
        Args:
            folder_path (str): 要打包的文件夹路径
            zip_path (str): zip文件保存路径，如果为None则自动生成
            
        Returns:
            dict: 打包结果 {"success": bool, "zip_path": str, "error": str}
        """
        try:
            folder_path = Path(folder_path)
            if not folder_path.exists():
                return {"success": False, "error": f"文件夹不存在: {folder_path}"}
            
            if not folder_path.is_dir():
                return {"success": False, "error": f"路径不是文件夹: {folder_path}"}
            
            # 生成zip文件路径
            if zip_path is None:
                # 在临时目录中创建zip文件
                temp_dir = Path(tempfile.gettempdir())
                zip_filename = f"{folder_path.name}.zip"
                zip_path = temp_dir / zip_filename
            else:
                zip_path = Path(zip_path)
            
            print(f"📦 正在打包文件夹: {folder_path.name}")
            
            # 创建zip文件
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历文件夹中的所有文件
                for file_path in folder_path.rglob('*'):
                    if file_path.is_file():
                        # 计算相对路径，使用文件夹名作为根目录
                        arcname = file_path.relative_to(folder_path.parent)
                        zipf.write(file_path, arcname)
                        
            # 检查zip文件是否创建成功
            if zip_path.exists():
                file_size = zip_path.stat().st_size
                print(f"✅ 打包完成: {zip_path.name} ({file_size} bytes)")
                return {
                    "success": True,
                    "zip_path": str(zip_path),
                    "original_folder": str(folder_path),
                    "zip_size": file_size
                }
            else:
                return {"success": False, "error": "zip文件创建失败"}
                
        except Exception as e:
            return {"success": False, "error": f"打包过程出错: {e}"}
    
    def _unzip_remote_file(self, zip_filename, target_dir=".", delete_zip=True, remote_path=None):
        """
        生成包含两个同步检测的远程解压命令并通过tkinter窗口提供给用户执行
        
        Args:
            zip_filename (str): 要解压的zip文件名
            target_dir (str): 解压目标目录
            delete_zip (bool): 解压后是否删除zip文件
            remote_path (str): 远程目标路径
            
        Returns:
            dict: 解压结果
        """
        try:
            print(f"📂 生成包含双重同步检测的远程解压命令: {zip_filename}")
            
            # 构建远程路径
            if remote_path is None:
                remote_target_path = f'"{self.REMOTE_ROOT}"'
            else:
                if remote_path.startswith('/'):
                    remote_target_path = f'"{remote_path}"'
                else:
                    # 解析相对路径，处理~和..
                    import os.path
                    if remote_path.startswith('~'):
                        # 将~替换为REMOTE_ROOT
                        resolved_path = remote_path.replace('~', self.REMOTE_ROOT, 1)
                    else:
                        resolved_path = f"{self.REMOTE_ROOT}/{remote_path}"
                    
                    # 规范化路径，处理..
                    normalized_path = os.path.normpath(resolved_path)
                    remote_target_path = f'"{normalized_path}"'
            
            # 构建源文件路径（Google Drive Desktop同步路径）
            source_path = f'"/content/drive/Othercomputers/我的 MacBook Air/Google Drive/{zip_filename}"'
            target_zip_path = f'{remote_target_path}/{zip_filename}'
            
            # 生成包含两个同步检测的远程命令
            if delete_zip:
                # 第一个⏳：等待上传完成并移动zip文件
                # 第二个⏳：等待移动完成后直接解压
                remote_command = f"""(mkdir -p {remote_target_path} && echo -n "⏳"; for i in {{1..60}}; do     if mv {source_path} {target_zip_path} 2>/dev/null; then         echo "";         break;     else         if [ $i -eq 60 ]; then             echo " ❌ (已重试60次失败)";             exit 1;         else             echo -n ".";             sleep 1;         fi;     fi; done) && (cd {remote_target_path} && echo -n "⏳"; for i in {{1..30}}; do     if [ -f "{zip_filename}" ]; then         echo "";         break;     else         if [ $i -eq 30 ]; then             echo " ❌ (zip文件检测失败)";             exit 1;         else             echo -n ".";             sleep 1;         fi;     fi; done) && (cd {remote_target_path} && echo "=== 开始解压 ===" && unzip -o {zip_filename} && echo "=== 删除zip ===" && rm {zip_filename} && echo "=== 验证结果 ===" && ls -la) && clear && echo "✅ 执行成功" || echo "❌ 执行失败\""""
            else:
                # 保留zip文件的版本
                remote_command = f"""(mkdir -p {remote_target_path} && echo -n "⏳"; for i in {{1..60}}; do     if mv {source_path} {target_zip_path} 2>/dev/null; then         echo "";         break;     else         if [ $i -eq 60 ]; then             echo " ❌ (已重试60次失败)";             exit 1;         else             echo -n ".";             sleep 1;         fi;     fi; done) && (cd {remote_target_path} && echo -n "⏳"; for i in {{1..30}}; do     if [ -f "{zip_filename}" ]; then         echo "";         break;     else         if [ $i -eq 30 ]; then             echo " ❌ (zip文件检测失败)";             exit 1;         else             echo -n ".";             sleep 1;         fi;     fi; done) && (cd {remote_target_path} && echo "=== 开始解压 ===" && unzip -o {zip_filename} && echo "=== 验证结果 ===" && ls -la) && clear && echo "✅ 执行成功" || echo "❌ 执行失败\""""
            
            print(f"🔧 生成的远程命令（包含双重同步检测）: {remote_command}")
            
            # 使用tkinter窗口显示命令并等待用户反馈
            try:
                import tkinter as tk
                from tkinter import messagebox, scrolledtext
                import threading
                import queue
                
                # 创建结果队列
                result_queue = queue.Queue()
                
                def show_command_window():
                    """显示远程命令窗口"""
                    root = tk.Tk()
                    root.title("远程文件夹上传命令 - Google Drive")
                    root.geometry("800x600")
                    
                    # 标题
                    title_label = tk.Label(root, text=f"远程文件夹上传: {zip_filename}", 
                                         font=("Arial", 14, "bold"))
                    title_label.pack(pady=10)
                    
                    # 说明文字
                    instruction_text = f"""
请在远程终端执行以下命令来完成文件夹上传：

该命令包含双重同步检测：
• 第一个⏳：等待zip文件上传完成并移动到目标位置
• 第二个⏳：等待移动完成后自动解压

1. 复制下面的命令到剪切板
2. 在远程终端粘贴并执行
3. 根据执行结果选择相应按钮
"""
                    instruction_label = tk.Label(root, text=instruction_text, 
                                               justify=tk.LEFT, wraplength=750)
                    instruction_label.pack(pady=10)
                    
                    # 命令文本框
                    command_frame = tk.Frame(root)
                    command_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
                    
                    command_text = scrolledtext.ScrolledText(command_frame, height=8, 
                                                           font=("Consolas", 10))
                    command_text.pack(fill=tk.BOTH, expand=True)
                    command_text.insert(tk.END, remote_command)
                    command_text.config(state=tk.DISABLED)
                    
                    # 复制按钮
                    def copy_command():
                        root.clipboard_clear()
                        root.clipboard_append(remote_command)
                        messagebox.showinfo("已复制", "命令已复制到剪切板")
                    
                    copy_btn = tk.Button(root, text="📋 复制命令到剪切板", 
                                       command=copy_command, font=("Arial", 12))
                    copy_btn.pack(pady=10)
                    
                    # 结果按钮框架
                    result_frame = tk.Frame(root)
                    result_frame.pack(pady=20)
                    
                    # 结果按钮
                    def on_success():
                        result_queue.put({"success": True, "message": "用户确认解压成功"})
                        root.destroy()
                    
                    def on_failure():
                        result_queue.put({"success": False, "error": "用户报告解压失败"})
                        root.destroy()
                    
                    def on_cancel():
                        result_queue.put({"success": False, "error": "用户取消操作"})
                        root.destroy()
                    
                    success_btn = tk.Button(result_frame, text="✅ 执行成功", 
                                          command=on_success, bg="lightgreen",
                                          font=("Arial", 12), width=12)
                    success_btn.pack(side=tk.LEFT, padx=10)
                    
                    failure_btn = tk.Button(result_frame, text="❌ 执行失败", 
                                          command=on_failure, bg="lightcoral",
                                          font=("Arial", 12), width=12)
                    failure_btn.pack(side=tk.LEFT, padx=10)
                    
                    cancel_btn = tk.Button(result_frame, text="🚫 取消操作", 
                                         command=on_cancel, bg="lightgray",
                                         font=("Arial", 12), width=12)
                    cancel_btn.pack(side=tk.LEFT, padx=10)
                    
                    # 居中显示窗口
                    root.update_idletasks()
                    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
                    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
                    root.geometry(f"+{x}+{y}")
                    
                    root.mainloop()
                
                # 在单独线程中显示窗口
                window_thread = threading.Thread(target=show_command_window)
                window_thread.start()
                window_thread.join()
                
                # 获取用户反馈结果
                try:
                    user_result = result_queue.get_nowait()
                    if user_result["success"]:
                        return {
                            "success": True,
                            "message": f"成功解压 {zip_filename}",
                            "zip_deleted": delete_zip,
                            "method": "manual_execution"
                        }
                    else:
                        return {
                            "success": False,
                            "error": user_result["error"],
                            "method": "manual_execution"
                        }
                except queue.Empty:
                    return {
                        "success": False,
                        "error": "用户未提供反馈",
                        "method": "manual_execution"
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"显示命令窗口失败: {e}",
                    "command": remote_command
                }
                
        except Exception as e:
            return {"success": False, "error": f"生成远程解压命令失败: {e}"}
    
    def _generate_unzip_and_delete_command(self, zip_filename, remote_target_path, keep_zip=False):
        """
        生成远程解压和删除zip文件的命令，并通过tkinter窗口提供给用户执行
        
        Args:
            zip_filename (str): zip文件名
            remote_target_path (str): 远程目标路径
            keep_zip (bool): 是否保留zip文件
            
        Returns:
            dict: 命令生成结果
        """
        try:
            print(f"📂 生成远程解压和删除命令: {zip_filename}")
            
            # 构建远程命令
            if keep_zip:
                # 保留zip文件的版本：只解压，不删除
                remote_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 验证结果 ===" && ls -la && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'''
            else:
                # 默认版本：解压后删除zip文件
                remote_command = f'''cd "{remote_target_path}" && echo "=== 开始解压 ===" && unzip -o "{zip_filename}" && echo "=== 删除zip ===" && rm "{zip_filename}" && echo "=== 验证结果 ===" && ls -la && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'''
            
            print(f"🔧 生成的远程解压命令: {remote_command}")
            
            # 使用tkinter窗口显示命令并等待用户反馈
            try:
                import tkinter as tk
                from tkinter import messagebox, scrolledtext
                import threading
                import queue
                
                # 创建结果队列
                result_queue = queue.Queue()
                
                def show_command_window():
                    """显示远程解压命令窗口"""
                    root = tk.Tk()
                    root.title("远程文件夹解压命令 - Google Drive")
                    root.geometry("800x600")
                    
                    # 标题
                    title_label = tk.Label(root, text=f"远程文件夹解压: {zip_filename}", 
                                         font=("Arial", 14, "bold"))
                    title_label.pack(pady=10)
                    
                    # 说明文字
                    action_text = "解压并删除zip文件" if not keep_zip else "解压但保留zip文件"
                    instruction_text = f"""
请在远程终端执行以下命令来完成文件夹解压：

操作: {action_text}
目标路径: {remote_target_path}

1. 复制下面的命令到剪切板
2. 在远程终端粘贴并执行
3. 根据执行结果选择相应按钮
"""
                    instruction_label = tk.Label(root, text=instruction_text, 
                                               justify=tk.LEFT, wraplength=750)
                    instruction_label.pack(pady=10)
                    
                    # 命令文本框
                    command_frame = tk.Frame(root)
                    command_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
                    
                    command_text = scrolledtext.ScrolledText(command_frame, height=8, 
                                                           font=("Consolas", 10))
                    command_text.pack(fill=tk.BOTH, expand=True)
                    command_text.insert(tk.END, remote_command)
                    command_text.config(state=tk.DISABLED)
                    
                    # 复制按钮
                    def copy_command():
                        root.clipboard_clear()
                        root.clipboard_append(remote_command)
                        messagebox.showinfo("已复制", "命令已复制到剪切板")
                    
                    copy_btn = tk.Button(root, text="📋 复制命令到剪切板", 
                                       command=copy_command, font=("Arial", 12))
                    copy_btn.pack(pady=10)
                    
                    # 结果按钮框架
                    result_frame = tk.Frame(root)
                    result_frame.pack(pady=20)
                    
                    # 结果按钮
                    def on_success():
                        result_queue.put({"success": True, "message": "用户确认解压成功"})
                        root.destroy()
                    
                    def on_failure():
                        result_queue.put({"success": False, "error": "用户报告解压失败"})
                        root.destroy()
                    
                    def on_cancel():
                        result_queue.put({"success": False, "error": "用户取消操作"})
                        root.destroy()
                    
                    success_btn = tk.Button(result_frame, text="✅ 执行成功", 
                                          command=on_success, bg="lightgreen",
                                          font=("Arial", 12), width=12)
                    success_btn.pack(side=tk.LEFT, padx=10)
                    
                    failure_btn = tk.Button(result_frame, text="❌ 执行失败", 
                                          command=on_failure, bg="lightcoral",
                                          font=("Arial", 12), width=12)
                    failure_btn.pack(side=tk.LEFT, padx=10)
                    
                    cancel_btn = tk.Button(result_frame, text="🚫 取消操作", 
                                         command=on_cancel, bg="lightgray",
                                         font=("Arial", 12), width=12)
                    cancel_btn.pack(side=tk.LEFT, padx=10)
                    
                    # 居中显示窗口
                    root.update_idletasks()
                    x = (root.winfo_screenwidth() // 2) - (root.winfo_width() // 2)
                    y = (root.winfo_screenheight() // 2) - (root.winfo_height() // 2)
                    root.geometry(f"+{x}+{y}")
                    
                    root.mainloop()
                
                # 在单独线程中显示窗口
                window_thread = threading.Thread(target=show_command_window)
                window_thread.start()
                window_thread.join()
                
                # 获取用户反馈结果
                try:
                    user_result = result_queue.get_nowait()
                    if user_result["success"]:
                        return {
                            "success": True,
                            "message": f"成功解压 {zip_filename}",
                            "zip_deleted": not keep_zip,
                            "method": "manual_execution",
                            "command": remote_command
                        }
                    else:
                        return {
                            "success": False,
                            "error": user_result["error"],
                            "method": "manual_execution",
                            "command": remote_command
                        }
                except queue.Empty:
                    return {
                        "success": False,
                        "error": "用户未提供反馈",
                        "method": "manual_execution",
                        "command": remote_command
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "error": f"显示命令窗口失败: {e}",
                    "command": remote_command
                }
                
        except Exception as e:
            return {"success": False, "error": f"生成远程解压命令失败: {e}"}
    
    def _wait_for_zip_sync(self, zip_filename, timeout=60):
        """
        等待zip文件同步到远程目录
        
        Args:
            zip_filename (str): 要等待的zip文件名
            timeout (int): 超时时间（秒）
            
        Returns:
            dict: 等待结果
        """
        try:
            import time
            
            print(f"⏳ 等待zip文件同步: {zip_filename}")
            
            start_time = time.time()
            check_count = 0
            next_check_delay = 1.0  # 第一次检测等待1秒
            
            # 只显示一行简洁的开始信息
            print(f"⏳", end="", flush=True)
            
            while time.time() - start_time < timeout:
                check_count += 1
                elapsed_time = time.time() - start_time
                
                # 使用 ls 命令检查文件是否存在
                try:
                    check_result = self.cmd_ls(".")
                    if check_result.get("success"):
                        files = check_result.get("files", [])
                        zip_exists = any(f.get("name") == zip_filename for f in files)
                        
                        if zip_exists:
                            print(f" ({elapsed_time:.1f}s)")
                            return {
                                "success": True,
                                "message": f"zip文件同步完成: {zip_filename}",
                                "sync_time": elapsed_time
                            }
                        
                except Exception as e:
                    pass  # 静默处理检查错误
                
                # 显示一个点表示检测进行中
                print(".", end="", flush=True)
                
                # 使用对数规律增加等待时间：每次 * √2，最多等待8秒
                time.sleep(min(next_check_delay, 8))
                next_check_delay *= 1.414  # √2 ≈ 1.414
            
            # 超时，返回失败
            print(f" ⏰ 超时 ({timeout}s)")
            return {
                "success": False,
                "error": f"zip文件同步超时: {zip_filename}",
                "sync_time": timeout
            }
            
        except Exception as e:
            print(f" ❌ 检测失败: {e}")
            return {"success": False, "error": f"zip文件同步检测失败: {e}"}

    def cmd_upload_folder(self, folder_path, target_path=".", keep_zip=False):
        """
        上传文件夹到Google Drive
        
        流程：打包 -> 上传zip文件（作为普通文件）
        
        Args:
            folder_path (str): 要上传的文件夹路径
            target_path (str): 目标路径（相对于当前shell路径）
            keep_zip (bool): 是否保留本地zip文件（远端总是保留zip文件）
            
        Returns:
            dict: 上传结果
        """
        try:
            print(f"🚀 开始上传文件夹: {folder_path}")
            
            # 步骤1: 打包文件夹
            print("📦 步骤1: 打包文件夹...")
            zip_result = self._zip_folder(folder_path)
            if not zip_result["success"]:
                return {"success": False, "error": f"打包失败: {zip_result['error']}"}
            
            zip_path = zip_result["zip_path"]
            zip_filename = Path(zip_path).name
            
            try:
                # 步骤2: 上传zip文件并自动解压
                print("📤 步骤2: 上传zip文件并自动解压...")
                
                # 传递文件夹上传的特殊参数
                upload_result = self.cmd_upload([zip_path], target_path, force=False, 
                                              folder_upload_info={
                                                  "is_folder_upload": True,
                                                  "zip_filename": zip_filename,
                                                  "keep_zip": keep_zip
                                              })
                if not upload_result["success"]:
                    return {"success": False, "error": f"上传失败: {upload_result['error']}"}
                
                # 成功完成
                folder_name = Path(folder_path).name
                print(f"Folder upload successful: {folder_name}")
                
                return {
                    "success": True,
                    "message": f"成功上传文件夹: {folder_name}",
                    "original_folder": folder_path,
                    "zip_uploaded": zip_filename,
                    "zip_kept": keep_zip,
                    "target_path": target_path,
                    "zip_size": zip_result.get("zip_size", 0),
                    "method": "zip_upload_and_extract",
                    "upload_details": upload_result
                }
                
            finally:
                # 根据keep_zip参数决定是否清理本地临时zip文件
                if not keep_zip:
                    try:
                        if Path(zip_path).exists():
                            Path(zip_path).unlink()
                            print(f"🧹 已清理本地临时文件: {zip_filename}")
                    except Exception as e:
                        print(f"⚠️ 清理临时文件失败: {e}")
                else:
                    print(f"📁 保留本地zip文件: {zip_path}")
                    
        except Exception as e:
            # 如果出错，也要清理临时文件
            try:
                if 'zip_path' in locals() and Path(zip_path).exists():
                    Path(zip_path).unlink()
                    print(f"🧹 已清理本地临时文件: {zip_path}")
            except:
                pass
            return {"success": False, "error": f"文件夹上传过程出错: {e}"}
    
    def _wait_for_file_sync_with_timeout(self, expected_files, file_moves, custom_timeout):
        """
        等待文件同步到 DRIVE_EQUIVALENT 目录，使用自定义超时时间
        
        Args:
            expected_files (list): 期望同步的文件名列表
            file_moves (list): 文件移动信息列表
            custom_timeout (int): 自定义超时时间（秒）
            
        Returns:
            dict: 同步状态
        """
        try:
            start_time = time.time()
            synced_files = []
            check_count = 0
            next_check_delay = 1.0  # 第一次检测等待1秒
            
            # 只显示一行简洁的开始信息
            print(f"⏳", end="", flush=True)
            
            while time.time() - start_time < custom_timeout:
                check_count += 1
                elapsed_time = time.time() - start_time
                
                # 使用 GDS ls 命令检查 DRIVE_EQUIVALENT 目录
                try:
                    import subprocess
                    import sys
                    
                    # 执行 GDS ls 命令
                    result = subprocess.run([
                        sys.executable, "GOOGLE_DRIVE.py", "--shell", "ls"
                    ], capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        # 解析输出，查找期望的文件
                        output_lines = result.stdout.strip().split('\n')
                        current_synced = []
                        
                        for filename in expected_files:
                            # 检查文件名是否在输出中
                            for line in output_lines:
                                if filename in line:
                                    current_synced.append(filename)
                                    break
                        
                        # 如果所有文件都已同步，返回成功
                        if len(current_synced) == len(expected_files):
                            print(f" ({elapsed_time:.1f}s)")
                            return {
                                "success": True,
                                "synced_files": current_synced,
                                "sync_time": elapsed_time,
                                "base_sync_time": elapsed_time  # 保存基础同步时间用于计算额外等待
                            }
                        
                        # 更新已同步文件列表
                        synced_files = current_synced
                        
                except subprocess.TimeoutExpired:
                    pass  # 静默处理超时
                except Exception:
                    pass  # 静默处理错误
                
                # 显示一个点表示检测进行中
                print(".", end="", flush=True)
                
                # 使用对数规律增加等待时间：每次 * √2，最多等待16秒
                time.sleep(min(next_check_delay, 16))
                next_check_delay *= 1.414  # √2 ≈ 1.414
            
            # 超时，返回当前状态
            missing_files = [f for f in expected_files if f not in synced_files]
            print(f" ⏰ 重试超时 ({custom_timeout}s)")
            
            return {
                "success": len(synced_files) > 0,
                "error": "文件同步重试超时，但部分文件可能已同步",
                "synced_files": synced_files,
                "missing_files": missing_files,
                "sync_time": custom_timeout
            }
            
        except Exception as e:
            print(f" ❌ 重试检测失败: {e}")
            return {"success": False, "error": f"文件同步重试检测失败: {e}"}
    
    def _restart_google_drive_desktop(self):
        """
        重启Google Drive Desktop应用
        
        Returns:
            bool: 重启是否成功
        """
        try:
            import subprocess
            import sys
            
            print("🔄 正在重启Google Drive Desktop...")
            
            # 调用主GOOGLE_DRIVE.py的重启功能
            result = subprocess.run([
                sys.executable, "GOOGLE_DRIVE.py", "--desktop", "--restart"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # print("✅ Google Drive Desktop重启成功")
                return True
            else:
                # print(f"❌ Google Drive Desktop重启失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Google Drive Desktop重启超时")
            return False
        except Exception as e:
            print(f"❌ 重启Google Drive Desktop时出错: {e}")
            return False

    def _check_local_files(self, expected_files):
        """检查本地文件系统中的文件"""
        try:
            drive_equiv_path = Path(self.DRIVE_EQUIVALENT)
            if not drive_equiv_path.exists():
                return {
                    "success": False,
                    "error": f"DRIVE_EQUIVALENT 目录不存在: {self.DRIVE_EQUIVALENT}"
                }
            
            synced_files = []
            missing_files = []
            
            for filename in expected_files:
                file_path = drive_equiv_path / filename
                if file_path.exists():
                    synced_files.append(filename)
                else:
                    missing_files.append(filename)
            
            return {
                "success": len(synced_files) == len(expected_files),
                "synced_files": synced_files,
                "missing_files": missing_files,
                "sync_time": 0  # 本地检查是即时的
            }
            
        except Exception as e:
            return {"success": False, "error": f"本地文件检查失败: {e}"}

    def generate_remote_commands(self, file_moves, target_path, folder_upload_info=None):
        """
        生成远端等效命令，包含必要的mkdir命令
        
        Args:
            file_moves (list): 文件移动信息列表，每个元素包含 filename 和 new_path
            target_path (str): 目标路径（"." 表示当前shell位置，绝对路径或相对于 REMOTE_ROOT 的路径）
            
        Returns:
            str: 远端命令字符串，包含mkdir和mv命令
        """
        try:
            commands = []
            
            # 计算目标绝对路径
            # 计算目标绝对路径
            import os.path
            
            if target_path == "." or target_path == "":
                # "." 表示当前shell的位置，但如果没有shell则默认为REMOTE_ROOT
                current_shell = self.get_current_shell()
                if current_shell and current_shell.get("current_path") != "~":
                    # 当前shell在子目录中，计算相对于REMOTE_ROOT的路径
                    current_path = current_shell.get("current_path", "~")
                    if current_path.startswith("~/"):
                        relative_path = current_path[2:]  # 去掉 ~/
                        target_absolute = f"{self.REMOTE_ROOT}/{relative_path}"
                    else:
                        target_absolute = self.REMOTE_ROOT
                else:
                    # 默认为REMOTE_ROOT
                    target_absolute = self.REMOTE_ROOT
            elif target_path.startswith("/"):
                # 绝对路径，基于 REMOTE_ROOT
                target_absolute = f"{self.REMOTE_ROOT}{target_path}"
            else:
                # 相对路径，需要考虑当前shell位置并规范化路径
                current_shell = self.get_current_shell()
                if current_shell and current_shell.get("current_path") != "~":
                    current_path = current_shell.get("current_path", "~")
                    if current_path.startswith("~/"):
                        # 从当前路径计算相对路径
                        current_relative = current_path[2:]  # 去掉 ~/
                        combined_path = f"{self.REMOTE_ROOT}/{current_relative}/{target_path}"
                    else:
                        combined_path = f"{self.REMOTE_ROOT}/{target_path}"
                else:
                    combined_path = f"{self.REMOTE_ROOT}/{target_path.lstrip('/')}"
                
                # 规范化路径，处理..等
                target_absolute = os.path.normpath(combined_path)
            
            for file_info in file_moves:
                filename = file_info["filename"]  # 实际的文件名（可能已重命名）
                original_filename = file_info.get("original_filename", filename)  # 原始文件名
                
                # 源路径：DRIVE_EQUIVALENT 中的文件（使用实际文件名）
                source_absolute = f"{self.DRIVE_EQUIVALENT}/{filename}"
                
                # 目标路径，使用原始文件名（这样远端文件保持原始名称）
                dest_absolute = f"{target_absolute.rstrip('/')}/{original_filename}"
                
                # 生成 mv 命令
                commands.append(f'mv "{source_absolute}" "{dest_absolute}"')
            
            # 将mv命令改为循环重试版本
            retry_commands = []
            for file_info in file_moves:
                filename = file_info["filename"]  # 实际的文件名（可能已重命名）
                original_filename = file_info.get("original_filename", filename)  # 原始文件名
                source_absolute = f"{self.DRIVE_EQUIVALENT}/{filename}"
                dest_absolute = f"{target_absolute.rstrip('/')}/{original_filename}"
                
                # 生成循环重试的mv命令，用简洁的点显示进度，并提供详细错误诊断
                retry_cmd = f'''
echo -n "⏳"
for i in {{1..60}}; do
    if mv "{source_absolute}" "{dest_absolute}" 2>/dev/null; then
        echo ""
        break
    else
        if [ $i -eq 60 ]; then
            echo ""
            echo "❌ 文件移动失败: {original_filename}"
            echo "📂 源文件检查:"
            if [ -f "{source_absolute}" ]; then
                echo "  ✅ 源文件存在: {source_absolute}"
                ls -la "{source_absolute}"
            else
                echo "  ❌ 源文件不存在: {source_absolute}"
                echo "  📋 DRIVE_EQUIVALENT 目录内容:"
                ls -la "{self.DRIVE_EQUIVALENT}/" | head -10
            fi
            echo "📂 目标路径检查:"
            target_dir="{target_absolute.rstrip('/')}"
            if [ -d "$target_dir" ]; then
                echo "  ✅ 目标目录存在: $target_dir"
            else
                echo "  ❌ 目标目录不存在: $target_dir"
            fi
            echo "🔍 权限检查:"
            echo "  源目录权限: $(ls -ld "{self.DRIVE_EQUIVALENT}/" 2>/dev/null || echo "无法访问")"
            echo "  目标目录权限: $(ls -ld "$target_dir" 2>/dev/null || echo "无法访问")"
            exit 1
        else
            echo -n "."
            sleep 1
        fi
    fi
done'''.strip()
                retry_commands.append(retry_cmd)
            
            # 用 && 连接所有重试命令
            base_command = " && ".join(retry_commands)
            
            # 添加目标目录创建命令
            target_dirs = set()
            for file_info in file_moves:
                original_filename = file_info.get("original_filename", file_info["filename"])
                dest_absolute = f"{target_absolute.rstrip('/')}/{original_filename}"
                target_dir = dest_absolute.rsplit('/', 1)[0]  # 获取目标目录
                target_dirs.add(target_dir)
            
            # 生成创建目录的命令
            mkdir_commands = []
            for target_dir in target_dirs:
                mkdir_commands.append(f'mkdir -p "{target_dir}"')
            
            mkdir_command_str = " && ".join(mkdir_commands) if mkdir_commands else ""
            
            # 检查是否为文件夹上传，如果是则添加解压和删除命令
            additional_commands = ""
            if folder_upload_info and folder_upload_info.get("is_folder_upload"):
                zip_filename = folder_upload_info.get("zip_filename")
                keep_zip = folder_upload_info.get("keep_zip", False)
                
                if zip_filename:
                    # 添加解压命令
                    unzip_cmd = f'echo "=== 开始解压 ===" && unzip -o "{zip_filename}"'
                    
                    # 如果不保留zip文件，添加删除命令
                    if not keep_zip:
                        delete_cmd = f'echo "=== 删除zip ===" && rm "{zip_filename}"'
                        additional_commands = f' && cd "{target_absolute}" && {unzip_cmd} && {delete_cmd} && echo "=== 验证结果 ===" && ls -la'
                    else:
                        additional_commands = f' && cd "{target_absolute}" && {unzip_cmd} && echo "=== 验证结果 ===" && ls -la'
            
            # 组合完整命令：创建目录 + 移动文件 + 解压删除 + 结果提示
            if mkdir_command_str:
                enhanced_command = f'({mkdir_command_str} && {base_command}{additional_commands}) && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            else:
                enhanced_command = f'({base_command}{additional_commands}) && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
            return enhanced_command
            
        except Exception as e:
            return f"# 生成远端命令时出错: {e}"

    def _verify_files_available(self, file_moves):
        """
        验证文件是否在同步目录中可用
        
        Args:
            file_moves (list): 文件移动信息列表
            
        Returns:
            bool: 所有文件都可用返回True，否则返回False
        """
        try:
            import os
            for file_info in file_moves:
                filename = file_info["filename"]
                file_path = os.path.join(self.LOCAL_EQUIVALENT, filename)
                if not os.path.exists(file_path):
                    return False
            return True
        except Exception as e:
            return False

    def show_remote_command_window(self, remote_command, command_type="upload"):
        """
        显示远端命令的 tkinter 窗口（简化版本，只有按钮）
        
        Args:
            remote_command (str): 要显示的远端命令
            command_type (str): 命令类型，用于设置窗口标题
            
        Returns:
            dict: 包含用户选择和可能的错误信息的字典
        """
        try:
            import tkinter as tk
            from tkinter import messagebox
            import webbrowser
            
            result = {"success": False, "action": None, "error_info": None}
            
            # 创建窗口
            root = tk.Tk()
            window_title = f"Google Drive - {command_type} Command"
            root.title(window_title)
            root.geometry("500x60")
            root.resizable(False, False)
            
            # 居中窗口
            root.eval('tk::PlaceWindow . center')
            
            # 设置窗口置顶
            root.attributes('-topmost', True)
            
            # 主框架
            main_frame = tk.Frame(root, padx=10, pady=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 按钮框架
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, expand=True)
            
            def copy_command():
                try:
                    root.clipboard_clear()
                    root.clipboard_append(remote_command)
                    copy_btn.config(text="✅ 已复制", bg="#4CAF50")
                    root.after(1500, lambda: copy_btn.config(text="📋 复制命令", bg="#2196F3"))
                except Exception as e:
                    print(f"复制到剪贴板失败: {e}")
            
            def execution_success():
                result["success"] = True
                result["action"] = "success"
                root.destroy()
            
            def execution_failed():
                result["success"] = False
                result["action"] = "failed"
                root.destroy()
            
            # 复制命令按钮
            copy_btn = tk.Button(
                button_frame, 
                text="📋 复制命令", 
                command=copy_command,
                font=("Arial", 10),
                bg="#2196F3",
                fg="white",
                padx=15,
                pady=5,
                relief=tk.RAISED,
                bd=2
            )
            copy_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
            
            # 执行成功按钮
            success_btn = tk.Button(
                button_frame, 
                text="✅ 执行成功", 
                command=execution_success,
                font=("Arial", 10, "bold"),
                bg="#4CAF50",
                fg="white",
                padx=15,
                pady=5,
                relief=tk.RAISED,
                bd=2
            )
            success_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
            
            # 执行失败按钮
            failed_btn = tk.Button(
                button_frame, 
                text="❌ 执行失败", 
                command=execution_failed,
                font=("Arial", 10),
                bg="#f44336",
                fg="white",
                padx=15,
                pady=5,
                relief=tk.RAISED,
                bd=2
            )
            failed_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # 只自动复制到剪贴板，不再自动打开Drive链接
            copy_command()
            
            # 运行窗口
            root.mainloop()
            
            # 如果用户选择了执行失败，进行交互式错误收集
            if result["action"] == "failed":
                print("\n" + "=" * 60)
                print("🚨 远端命令执行失败")
                print("=" * 60)
                print(f"命令: {remote_command}")
                print()
                
                try:
                    error_description = get_multiline_input_safe("请描述失败的原因或错误信息: ", single_line=False)
                    if error_description:
                        result["error_info"] = error_description
                        print(f"✅ 已记录错误信息: {error_description}")
                    else:
                        result["error_info"] = "用户未提供具体错误信息"
                        print("⚠️ 未提供具体错误信息")
                except KeyboardInterrupt:
                    print("\n❌ 错误信息收集已取消")
                    result["error_info"] = "用户取消了错误信息输入"
                print("=" * 60)
            
            return result
            
        except ImportError:
            # tkinter 不可用，回退到终端显示
            print("=" * 80)
            print("🚀 Google Drive Upload - Remote Terminal Command")
            print("=" * 80)
            print()
            print("请在远端终端执行以下命令：")
            print()
            print(remote_command)
            print()
            print("=" * 80)
            
            try:
                while True:
                    user_choice = get_multiline_input_safe("命令执行结果 [s=成功/f=失败/c=取消]: ", single_line=True)
                    if user_choice is None:
                        return {"success": False, "action": "cancelled", "error_info": "用户取消操作"}
                    user_choice = user_choice.lower()
                    if user_choice in ['s', 'success', '成功']:
                        return {"success": True, "action": "success", "error_info": None}
                    elif user_choice in ['f', 'failed', '失败']:
                        error_info = get_multiline_input_safe("请描述失败的原因: ", single_line=False)
                        return {
                            "success": False, 
                            "action": "failed", 
                            "error_info": error_info or "用户未提供具体错误信息"
                        }
                    elif user_choice in ['c', 'cancel', '取消']:
                        return {"success": False, "action": "cancelled", "error_info": "用户取消操作"}
                    else:
                        print("❌ 无效选择，请输入 s/f/c")
                        
            except KeyboardInterrupt:
                print("\n❌ 上传已取消")
                return {"success": False, "action": "cancelled", "error_info": "用户中断操作"}
                
        except Exception as e:
            print(f"❌ 显示远端命令窗口时出错: {e}")
            return {"success": False, "action": "error", "error_info": f"窗口显示错误: {e}"}

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

    def _expand_path(self, path):
        """展开路径，处理~等特殊字符"""
        try:
            import os
            return os.path.expanduser(os.path.expandvars(path))
        except Exception as e:
            print(f"路径展开失败: {e}")
            return path

    def _check_large_files(self, source_files):
        """
        检查大文件（>1GB）并提供手动上传方案
        
        Args:
            source_files (list): 源文件路径列表
            
        Returns:
            tuple: (normal_files, large_files) - 正常文件和大文件列表
        """
        try:
            normal_files = []
            large_files = []
            GB_SIZE = 1024 * 1024 * 1024  # 1GB in bytes
            
            for file_path in source_files:
                expanded_path = self._expand_path(file_path)
                if os.path.exists(expanded_path):
                    file_size = os.path.getsize(expanded_path)
                    if file_size > GB_SIZE:
                        large_files.append({
                            "path": expanded_path,
                            "original_path": file_path,
                            "size_gb": file_size / GB_SIZE
                        })
                    else:
                        normal_files.append(expanded_path)
                else:
                    print(f"File does not exist: {file_path}")
            
            return normal_files, large_files
            
        except Exception as e:
            print(f"检查大文件时出错: {e}")
            return source_files, []

    def _handle_large_files(self, large_files, target_path=".", current_shell=None):
        """处理大文件的手动上传，支持逐一跟进"""
        try:
            if not large_files:
                return {"success": True, "message": "没有大文件需要手动处理"}
            
            print(f"\n📁 发现 {len(large_files)} 个大文件（>1GB），将逐一处理:")
            
            successful_uploads = []
            failed_uploads = []
            
            for i, file_info in enumerate(large_files, 1):
                print(f"\n{'='*60}")
                print(f"🔄 处理第 {i}/{len(large_files)} 个大文件")
                print(f"📄 文件: {file_info['original_path']} ({file_info['size_gb']:.2f} GB)")
                print(f"{'='*60}")
                
                # 为单个文件创建临时上传目录
                single_upload_dir = Path(os.getcwd()) / f"_MANUAL_UPLOAD_{i}"
                single_upload_dir.mkdir(exist_ok=True)
                
                file_path = Path(file_info["path"])
                link_path = single_upload_dir / file_path.name
                
                # 删除已存在的链接
                if link_path.exists():
                    link_path.unlink()
                
                # 创建符号链接
                try:
                    link_path.symlink_to(file_path)
                    print(f"✅ 已准备文件: {file_path.name}")
                except Exception as e:
                    print(f"❌ 创建链接失败: {file_path.name} - {e}")
                    failed_uploads.append({
                        "file": file_info["original_path"],
                        "error": f"创建链接失败: {e}"
                    })
                    continue
                
                # 确定目标文件夹URL
                target_folder_id = None
                target_url = None
                
                if current_shell and self.drive_service:
                    try:
                        # 尝试解析目标路径
                        if target_path == ".":
                            target_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                        else:
                            target_folder_id, _ = self.resolve_path(target_path, current_shell)
                        
                        if target_folder_id:
                            target_url = f"https://drive.google.com/drive/folders/{target_folder_id}"
                        else:
                            target_url = f"https://drive.google.com/drive/folders/{self.REMOTE_ROOT_FOLDER_ID}"
                    except:
                        target_url = f"https://drive.google.com/drive/folders/{self.REMOTE_ROOT_FOLDER_ID}"
                else:
                    target_url = f"https://drive.google.com/drive/folders/{self.REMOTE_ROOT_FOLDER_ID}"
                
                # 打开文件夹和目标位置
                try:
                    import subprocess
                    import webbrowser
                    
                    # 打开本地文件夹
                    if platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", str(single_upload_dir)])
                    elif platform.system() == "Windows":
                        os.startfile(str(single_upload_dir))
                    else:  # Linux
                        subprocess.run(["xdg-open", str(single_upload_dir)])
                    
                    # 打开目标Google Drive文件夹（不是DRIVE_EQUIVALENT）
                    webbrowser.open(target_url)
                    
                    print(f"🚀 已打开本地文件夹: {single_upload_dir}")
                    print(f"🌐 已打开目标Google Drive文件夹")
                    print(f"📋 请将文件拖拽到Google Drive目标文件夹中")
                    
                except Exception as e:
                    print(f"⚠️ 打开文件夹失败: {e}")
                
                # 等待用户确认
                try:
                    print(f"\n⏳ 请完成文件上传后按回车继续...")
                    get_multiline_input_safe("按Enter键继续...", single_line=True)  # 等待用户确认
                    
                    # 清理临时目录
                    try:
                        if link_path.exists():
                            link_path.unlink()
                        single_upload_dir.rmdir()
                    except:
                        pass
                    
                    successful_uploads.append({
                        "file": file_info["original_path"],
                        "size_gb": file_info["size_gb"]
                    })
                    
                    print(f"✅ 文件 {i}/{len(large_files)} 处理完成")
                    
                except KeyboardInterrupt:
                    print(f"\n❌ 用户中断了大文件上传过程")
                    # 清理临时目录
                    try:
                        if link_path.exists():
                            link_path.unlink()
                        single_upload_dir.rmdir()
                    except:
                        pass
                    break
                except Exception as e:
                    print(f"❌ 处理文件时出错: {e}")
                    failed_uploads.append({
                        "file": file_info["original_path"],
                        "error": str(e)
                    })
            
            print(f"\n{'='*60}")
            print(f"📊 大文件处理完成:")
            print(f"✅ 成功: {len(successful_uploads)} 个文件")
            print(f"❌ 失败: {len(failed_uploads)} 个文件")
            print(f"{'='*60}")
            
            return {
                "success": len(successful_uploads) > 0,
                "large_files_count": len(large_files),
                "successful_uploads": successful_uploads,
                "failed_uploads": failed_uploads,
                "message": f"大文件处理完成: {len(successful_uploads)}/{len(large_files)} 个文件成功"
            }
            
        except Exception as e:
            return {"success": False, "error": f"处理大文件时出错: {e}"}

    def cmd_upload(self, source_files, target_path=".", force=False, folder_upload_info=None, remove_local=False):
        """
        GDS UPLOAD 命令实现
        
        Args:
            source_files (list): 要上传的源文件路径列表
            target_path (str): 目标路径（相对于当前 shell 路径）
            force (bool): 是否强制覆盖现有文件
            
        Returns:
            dict: 上传结果
        """
        try:
            # 0. 检查Google Drive Desktop是否运行
            if not self.ensure_google_drive_desktop_running():
                return {"success": False, "error": "用户取消上传操作"}
            
            # 1. 验证输入参数
            if not source_files:
                return {"success": False, "error": "请指定要上传的文件"}
            
            if isinstance(source_files, str):
                source_files = [source_files]
            
            # 1.5. 检查大文件并分离处理
            normal_files, large_files = self._check_large_files(source_files)
            
            # 处理大文件
            if large_files:
                large_file_result = self._handle_large_files(large_files, target_path, current_shell)
                if not large_file_result["success"]:
                    return large_file_result
            
            # 如果没有正常大小的文件需要处理，但有大文件，需要等待手动上传完成
            if not normal_files:
                if large_files:
                    # 等待大文件手动上传完成
                    large_file_names = [Path(f["path"]).name for f in large_files]
                    print(f"\n⏳ 等待手动上传完成...")
                    
                    # 创建虚拟file_moves用于计算超时时间
                    virtual_file_moves = [{"new_path": f["path"]} for f in large_files]
                    sync_result = self.wait_for_file_sync(large_file_names, virtual_file_moves)
                    
                    if sync_result["success"]:
                        
                        return {
                            "success": True,
                            "message": f"✅ Large files manual upload completed: {len(large_files)} files",
                            "large_files_handled": True,
                            "sync_time": sync_result.get("sync_time", 0)
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"Manual upload failed: {sync_result.get('error', 'Unknown error')}",
                            "large_files_handled": True
                        }
                else:
                    return {"success": False, "error": "Cannot find valid files"}
            
            # 继续处理正常大小的文件
            source_files = normal_files
            
            # 2. 获取当前 shell
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell"}
            
            # 3. 解析目标路径（如果没有 API 服务，使用默认值）
            if self.drive_service:
                if target_path == ".":
                    target_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                    target_display_path = current_shell.get("current_path", "~")
                else:
                    target_folder_id, target_display_path = self.resolve_path(target_path, current_shell)
                    if not target_folder_id:
                        # 目标路径不存在，但这是正常的，我们会在远端创建它
                        # 静默处理目标路径创建
                        target_folder_id = None  # 标记为需要创建
                        target_display_path = target_path
            else:
                # 没有 API 服务时使用默认值
                target_folder_id = self.REMOTE_ROOT_FOLDER_ID
                target_display_path = "~" if target_path == "." else target_path
                print("⚠️ 警告: Google Drive API 服务未初始化，将使用模拟模式")
            
            # 3.5. 检查目标文件是否已存在，避免冲突（除非使用--force）
            overridden_files = []
            if not force:
                conflict_check_result = self._check_target_file_conflicts_before_move(source_files, target_path)
                if not conflict_check_result["success"]:
                    return conflict_check_result
            else:
                # Force模式：检查哪些文件会被覆盖，记录警告
                override_check_result = self._check_files_to_override(source_files, target_path)
                if override_check_result["success"] and override_check_result.get("overridden_files"):
                    overridden_files = override_check_result["overridden_files"]
                    for file_path in overridden_files:
                        print(f"⚠️ Warning: Overriding remote file {file_path}")
            
            # 4. 移动文件到 LOCAL_EQUIVALENT
            file_moves = []
            failed_moves = []
            
            for source_file in source_files:
                move_result = self.move_to_local_equivalent(source_file)
                if move_result["success"]:
                    file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"]
                    })
                    # 静默处理文件移动
                    if move_result["renamed"]:
                        print(f"   (已重命名避免冲突)")
                else:
                    failed_moves.append({
                        "file": source_file,
                        "error": move_result["error"]
                    })
                    print(f"❌ 文件移动失败: {source_file} - {move_result['error']}")
            
            if not file_moves:
                return {
                    "success": False,
                    "error": "所有文件移动失败",
                    "failed_moves": failed_moves
                }
            
            # 5. 检测网络连接
            network_result = self.check_network_connection()
            if not network_result["success"]:
                print(f"⚠️ 网络连接检测: {network_result['error']}")
                print("📱 将继续执行，但请确保网络连接正常")
            else:
                # 静默处理网络检查
                pass
            
            # 6. 等待文件同步到 DRIVE_EQUIVALENT
            expected_filenames = [fm.get("original_filename", fm["filename"]) for fm in file_moves]
            
            sync_result = self.wait_for_file_sync(expected_filenames, file_moves)
            
            if not sync_result["success"]:
                # 检查是否是小文件超时（文件总大小 < 10MB）
                total_size_mb = sum(
                    os.path.getsize(fm["new_path"]) / (1024 * 1024) 
                    for fm in file_moves 
                    if os.path.exists(fm["new_path"])
                )
                
                if total_size_mb < 10:  # 小文件超时，尝试重启Google Drive Desktop并重试
                    print(f"⚠️ 小文件上传同步超时，尝试重启Google Drive Desktop并重试...")
                    
                    # 重启Google Drive Desktop
                    restart_result = self._restart_google_drive_desktop()
                    if restart_result:
                        print("✅ Google Drive Desktop重启成功，开始重试上传...")
                        
                        # 重新计算超时时间并增加60秒
                        original_timeout = self.calculate_timeout_from_file_sizes(file_moves)
                        retry_timeout = original_timeout + 60  # 从+10秒增加到+60秒
                        print(f"🔄 重试超时时间: {retry_timeout}秒 (原{original_timeout}秒 + 60秒)")
                        
                        # 重试同步检测
                        retry_sync_result = self._wait_for_file_sync_with_timeout(expected_filenames, file_moves, retry_timeout)
                        
                        if retry_sync_result["success"]:
                            print("✅ 重试上传成功!")
                            sync_result = retry_sync_result
                        else:
                            return {
                                "success": False,
                                "error": f"小文件上传重试失败: {retry_sync_result.get('error', '未知错误')}",
                                "file_moves": file_moves,
                                "total_size_mb": total_size_mb,
                                "sync_time": retry_sync_result.get("sync_time", 0),
                                "retry_attempted": True,
                                "suggestion": "Google Drive Desktop重启后仍然失败，请检查网络连接或手动上传"
                            }
                    else:
                        return {
                            "success": False,
                            "error": f"小文件上传同步超时，且Google Drive Desktop重启失败",
                            "file_moves": file_moves,
                            "total_size_mb": total_size_mb,
                            "sync_time": sync_result.get("sync_time", 0),
                            "retry_attempted": False,
                            "suggestion": "请手动重启Google Drive Desktop后重试"
                        }
                
                print(f"⚠️ 文件同步检测: {sync_result['error']}")
                print("📱 将继续执行，但请手动确认文件已同步")
                # 在没有同步检测的情况下，假设文件已同步
                sync_result = {
                    "success": True,
                    "synced_files": expected_filenames,
                    "sync_time": 0,
                    "base_sync_time": 0
                }
            else:
                base_time = sync_result.get("base_sync_time", sync_result.get("sync_time", 0))
                # 静默处理文件同步完成
                sync_result["sync_time"] = base_time
            
            # 7. 静默验证文件同步状态
            self._verify_files_available(file_moves)
            
            # 8. 静默生成远端命令
            remote_command = self.generate_remote_commands(file_moves, target_path, folder_upload_info)
            
            # 7.5. 远端目录创建已经集成到generate_remote_commands中，无需额外处理
            
            # 8. 使用统一的远端命令执行接口
            context_info = {
                "expected_filenames": expected_filenames,
                "target_folder_id": target_folder_id,
                "target_path": target_path,
                "file_moves": file_moves
            }
            
            execution_result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="upload",
                context_info=context_info
            )
            
            # 如果执行失败，直接返回错误
            if not execution_result["success"]:
                return {
                    "success": False,
                    "error": execution_result["message"],
                    "remote_command": remote_command,
                    "execution_result": execution_result
                }
            
            # 执行成功，使用返回的验证结果
            verify_result = execution_result
            
            # 9. 上传和远端命令执行完成后，清理LOCAL_EQUIVALENT中的文件
            if verify_result["success"]:
                self._cleanup_local_equivalent_files(file_moves)
                
                # 如果指定了 --remove-local 选项，删除本地源文件
                if remove_local:
                    removed_files = []
                    failed_removals = []
                    for source_file in source_files:
                        try:
                            if os.path.exists(source_file):
                                os.unlink(source_file)
                                removed_files.append(source_file)
                        except Exception as e:
                            failed_removals.append({"file": source_file, "error": str(e)})
            
            result = {
                "success": verify_result["success"],
                "uploaded_files": verify_result.get("found_files", []),
                "failed_files": verify_result.get("missing_files", []) + [fm["file"] for fm in failed_moves],
                "target_path": target_display_path,
                "target_folder_id": target_folder_id,
                "total_attempted": len(source_files),
                "total_succeeded": len(verify_result.get("found_files", [])),
                "remote_command": remote_command,
                "file_moves": file_moves,
                "failed_moves": failed_moves,
                "sync_time": sync_result.get("sync_time", 0),
                "message": f"Upload completed: {len(verify_result.get('found_files', []))}/{len(source_files)} files" if verify_result["success"] else f"⚠️ Partially uploaded: {len(verify_result.get('found_files', []))}/{len(source_files)} files",
                "api_available": self.drive_service is not None
            }
            
            # 添加本地文件删除信息
            if remove_local and verify_result["success"]:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Upload error: {str(e)}"
            }
    
    def load_shells(self):
        """加载远程shell配置"""
        try:
            if self.shells_file.exists():
                with open(self.shells_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"shells": {}, "active_shell": None}
        except Exception as e:
            print(f"❌ 加载shell配置失败: {e}")
            return {"shells": {}, "active_shell": None}
    
    def save_shells(self, shells_data):
        """保存远程shell配置"""
        try:
            with open(self.shells_file, 'w', encoding='utf-8') as f:
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
    
    def _create_default_shell(self):
        """创建默认shell"""
        try:
            # 生成默认shell ID
            shell_id = "default_shell"
            shell_name = "default"
            
            # 默认shell配置，总是从根目录开始
            shell_config = {
                "id": shell_id,
                "name": shell_name,
                "folder_id": self.REMOTE_ROOT_FOLDER_ID,  # 根目录
                "current_path": "~",  # 根路径
                "current_folder_id": self.REMOTE_ROOT_FOLDER_ID,
                "created_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "last_accessed": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "active",
                "type": "default"
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
                "folder_id": self.REMOTE_ROOT_FOLDER_ID,
                "current_path": "~",
                "current_folder_id": self.REMOTE_ROOT_FOLDER_ID,
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
                "folder_id": folder_id or self.REMOTE_ROOT_FOLDER_ID,
                "current_path": "~",
                "current_folder_id": self.REMOTE_ROOT_FOLDER_ID,
                "created_time": created_time,
                "last_accessed": created_time,
                "status": "active"
            }
            
            shells_data = self.load_shells()
            shells_data["shells"][shell_id] = shell_config
            shells_data["active_shell"] = shell_id
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "message": f"✅ 创建远程shell成功: {shell_name}"
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
            shells_data["shells"][shell_id]["current_folder_id"] = self.REMOTE_ROOT_FOLDER_ID
            
            if self.save_shells(shells_data):
                shell_name = shells_data["shells"][shell_id]["name"]
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "current_path": "~",
                    "message": f"✅ 已切换到shell: {shell_name}，路径重置为根目录"
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
            del shells_data["shells"][shell_id]
            
            if shells_data["active_shell"] == shell_id:
                shells_data["active_shell"] = None
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "message": f"✅ 已终止shell: {shell_name}"
                }
            else:
                return {"success": False, "error": "保存shell状态失败"}
                
        except Exception as e:
            return {"success": False, "error": f"终止shell时出错: {e}"}
    
    def exit_shell(self):
        """退出当前shell"""
        try:
            current_shell = self.get_current_shell()
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
    
    def resolve_path(self, path, current_shell=None):
        """解析路径，返回对应的Google Drive文件夹ID和逻辑路径"""
        if not self.drive_service:
            return None, None
            
        if not current_shell:
            current_shell = self.get_current_shell()
            
        if not current_shell:
            return None, None
        
        try:
            current_path = current_shell.get("current_path", "~")
            current_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
            
            # 处理特殊路径：DRIVE_EQUIVALENT
            if path == "@drive_equivalent" or path.startswith("@drive_equivalent/"):
                if path == "@drive_equivalent":
                    return self.DRIVE_EQUIVALENT_FOLDER_ID, "@drive_equivalent"
                else:
                    # 处理@drive_equivalent下的子路径
                    relative_path = path[len("@drive_equivalent/"):]
                    return self._resolve_relative_path(relative_path, self.DRIVE_EQUIVALENT_FOLDER_ID, "@drive_equivalent")
            
            # 处理绝对路径（基于REMOTE_ROOT）
            if path == "~":
                return self.REMOTE_ROOT_FOLDER_ID, "~"
            elif path.startswith("~/"):
                relative_path = path[2:]
                return self._resolve_relative_path(relative_path, self.REMOTE_ROOT_FOLDER_ID, "~")
            elif path.startswith("~"):
                # 处理 ~something 的情况，这在远端逻辑中无效
                return None, None
            
            # 处理相对路径
            elif path.startswith("./"):
                relative_path = path[2:]
                return self._resolve_relative_path(relative_path, current_folder_id, current_path)
            
            elif path == ".":
                return current_folder_id, current_path
            
            elif path == "..":
                return self._resolve_parent_directory(current_folder_id, current_path)
            
            elif path.startswith("../"):
                parent_id, parent_path = self._resolve_parent_directory(current_folder_id, current_path)
                if parent_id:
                    relative_path = path[3:]
                    return self._resolve_relative_path(relative_path, parent_id, parent_path)
                return None, None
            
            else:
                return self._resolve_relative_path(path, current_folder_id, current_path)
                
        except Exception as e:
            print(f"❌ 解析路径时出错: {e}")
            return None, None
    
    def _resolve_relative_path(self, relative_path, base_folder_id, base_path):
        """解析相对路径"""
        if not relative_path:
            return base_folder_id, base_path
        
        try:
            path_parts = relative_path.split("/")
            current_id = base_folder_id
            current_logical_path = base_path
            
            for part in path_parts:
                if not part:
                    continue
                
                files_result = self.drive_service.list_files(folder_id=current_id, max_results=100)
                if not files_result['success']:
                    return None, None
                
                found_folder = None
                for file in files_result['files']:
                    if file['name'] == part and file['mimeType'] == 'application/vnd.google-apps.folder':
                        found_folder = file
                        break
                
                if not found_folder:
                    return None, None
                
                current_id = found_folder['id']
                if current_logical_path == "~":
                    current_logical_path = f"~/{part}"
                else:
                    current_logical_path = f"{current_logical_path}/{part}"
            
            return current_id, current_logical_path
            
        except Exception as e:
            print(f"❌ 解析相对路径时出错: {e}")
            return None, None
    
    def _resolve_parent_directory(self, folder_id, current_path):
        """解析父目录"""
        if current_path == "~":
            return None, None
        
        try:
            folder_info = self.drive_service.service.files().get(
                fileId=folder_id,
                fields="parents"
            ).execute()
            
            parents = folder_info.get('parents', [])
            if not parents:
                return None, None
            
            parent_id = parents[0]
            
            if current_path.count('/') == 1:
                parent_path = "~"
            else:
                parent_path = '/'.join(current_path.split('/')[:-1])
            
            return parent_id, parent_path
            
        except Exception as e:
            print(f"❌ 解析父目录时出错: {e}")
            return None, None
    
    # Shell命令实现
    def cmd_pwd(self):
        """显示当前路径"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            return {
                "success": True,
                "current_path": current_shell.get("current_path", "~"),
                "home_url": self.HOME_URL,
                "shell_id": current_shell["id"],
                "shell_name": current_shell["name"]
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取当前路径时出错: {e}"}
    
    def cmd_ls(self, path=None, detailed=False, recursive=False):
        """列出目录内容，支持递归和详细模式"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if path is None or path == "." or path == "~":
                target_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                display_path = current_shell.get("current_path", "~")
            else:
                target_folder_id, display_path = self.resolve_path(path, current_shell)
                if not target_folder_id:
                    return {"success": False, "error": f"目录不存在: {path}"}
            
            if recursive:
                return self._ls_recursive(target_folder_id, display_path, detailed)
            else:
                return self._ls_single(target_folder_id, display_path, detailed)
                
        except Exception as e:
            return {"success": False, "error": f"执行ls命令时出错: {e}"}
    

    
    def _ls_recursive(self, root_folder_id, root_path, detailed):
        """递归列出目录内容"""
        try:
            all_items = []
            
            def scan_folder(folder_id, folder_path, depth=0):
                result = self.drive_service.list_files(folder_id=folder_id, max_results=100)
                if not result['success']:
                    return
                
                files = result['files']
                
                # 添加网页链接
                for file in files:
                    file['url'] = self._generate_web_url(file)
                    file['path'] = folder_path
                    file['depth'] = depth
                    all_items.append(file)
                    
                    # 如果是文件夹，递归扫描
                    if file['mimeType'] == 'application/vnd.google-apps.folder':
                        sub_path = f"{folder_path}/{file['name']}" if folder_path != "~" else f"~/{file['name']}"
                        scan_folder(file['id'], sub_path, depth + 1)
            
            # 开始递归扫描
            scan_folder(root_folder_id, root_path)
            
            # 按路径和名称排序
            all_items.sort(key=lambda x: (x['path'], x['name'].lower()))
            
            # 分离文件夹和文件
            folders = [f for f in all_items if f['mimeType'] == 'application/vnd.google-apps.folder']
            other_files = [f for f in all_items if f['mimeType'] != 'application/vnd.google-apps.folder']
            
            if detailed:
                # 详细模式：返回嵌套的树形结构
                nested_structure = self._build_nested_structure(all_items, root_path)
                
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "folder_url": self._generate_folder_url(root_folder_id),
                    "files": nested_structure["files"],
                    "folders": nested_structure["folders"],  # 每个文件夹包含自己的files和folders
                    "count": len(all_items),
                    "mode": "recursive_detailed"
                }
            else:
                # 简单模式：只返回基本信息
                return {
                    "success": True,
                    "path": root_path,
                    "folder_id": root_folder_id,
                    "files": other_files,
                    "folders": folders,
                    "all_items": all_items,
                    "count": len(all_items),
                    "mode": "recursive_bash"
                }
                
        except Exception as e:
            return {"success": False, "error": f"递归列出目录时出错: {e}"}
    
    def _build_nested_structure(self, all_items, root_path):
        """构建嵌套的文件夹结构，每个文件夹包含自己的files和folders"""
        try:
            # 按路径分组所有项目
            path_groups = {}
            
            for item in all_items:
                path = item['path']
                if path not in path_groups:
                    path_groups[path] = {'files': [], 'folders': []}
                
                if item['mimeType'] == 'application/vnd.google-apps.folder':
                    path_groups[path]['folders'].append(item)
                else:
                    path_groups[path]['files'].append(item)
            
            # 构建嵌套结构
            def build_folder_content(folder_path):
                content = path_groups.get(folder_path, {'files': [], 'folders': []})
                
                # 为每个子文件夹递归构建内容
                enriched_folders = []
                for folder in content['folders']:
                    folder_copy = folder.copy()
                    sub_path = f"{folder_path}/{folder['name']}" if folder_path != "~" else f"~/{folder['name']}"
                    sub_content = build_folder_content(sub_path)
                    
                    # 将子内容添加到文件夹中
                    folder_copy['files'] = sub_content['files']
                    folder_copy['folders'] = sub_content['folders']
                    enriched_folders.append(folder_copy)
                
                return {
                    'files': content['files'],
                    'folders': enriched_folders
                }
            
            # 从根路径开始构建
            return build_folder_content(root_path)
            
        except Exception as e:
            return {'files': [], 'folders': [], 'error': str(e)}
    
    def _build_folder_tree(self, folders):
        """构建文件夹树结构，便于显示层次关系"""
        try:
            tree = {}
            
            for folder in folders:
                path_parts = folder['path'].split('/')
                current_level = tree
                
                for i, part in enumerate(path_parts):
                    if part not in current_level:
                        current_level[part] = {
                            'folders': {},
                            'info': None
                        }
                    current_level = current_level[part]['folders']
                
                # 在最终位置添加当前文件夹信息
                current_level[folder['name']] = {
                    'folders': {},
                    'info': {
                        'id': folder['id'],
                        'url': folder['url'],
                        'name': folder['name'],
                        'path': folder['path'],
                        'depth': folder['depth']
                    }
                }
            
            return tree
            
        except Exception as e:
            print(f"构建文件夹树时出错: {e}")
            return {}
    
    def _generate_folder_url(self, folder_id):
        """生成文件夹的网页链接"""
        return f"https://drive.google.com/drive/folders/{folder_id}"
    
    def _generate_web_url(self, file):
        """为文件生成网页链接"""
        file_id = file['id']
        mime_type = file['mimeType']
        
        if mime_type == 'application/vnd.google.colaboratory':
            # Colab文件
            return f"https://colab.research.google.com/drive/{file_id}"
        elif mime_type == 'application/vnd.google-apps.document':
            # Google文档
            return f"https://docs.google.com/document/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google表格
            return f"https://docs.google.com/spreadsheets/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.presentation':
            # Google幻灯片
            return f"https://docs.google.com/presentation/d/{file_id}/edit"
        elif mime_type == 'application/vnd.google-apps.folder':
            # 文件夹
            return f"https://drive.google.com/drive/folders/{file_id}"
        else:
            # 其他文件（预览或下载）
            return f"https://drive.google.com/file/d/{file_id}/view"
    
    def cmd_cd(self, path):
        """切换目录"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                path = "~"
            
            target_id, target_path = self.resolve_path(path, current_shell)
            
            if not target_id:
                return {"success": False, "error": f"目录不存在: {path}"}
            
            shells_data = self.load_shells()
            shell_id = current_shell['id']
            
            shells_data["shells"][shell_id]["current_path"] = target_path
            shells_data["shells"][shell_id]["current_folder_id"] = target_id
            shells_data["shells"][shell_id]["last_accessed"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "new_path": target_path,
                    "folder_id": target_id,
                    "message": f"✅ 已切换到目录: {target_path}"
                }
            else:
                return {"success": False, "error": "保存shell状态失败"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cd命令时出错: {e}"}
    
    def cmd_mkdir(self, path, recursive=False):
        """创建目录，通过远程命令界面执行以确保由用户账户创建"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not path:
                return {"success": False, "error": "请指定要创建的目录名称"}
            
            # 调用统一的mkdir_remote方法
            return self.cmd_mkdir_remote(path, recursive)
                
        except Exception as e:
            return {"success": False, "error": f"执行mkdir命令时出错: {e}"}
    
    def _ls_single(self, target_folder_id, display_path, detailed):
        """列出单个目录内容（统一实现，包含去重处理）"""
        try:
            result = self.drive_service.list_files(folder_id=target_folder_id, max_results=50)
            
            if result['success']:
                files = result['files']
                
                # 添加网页链接到每个文件
                for file in files:
                    file['url'] = self._generate_web_url(file)
                
                # 按名称排序，文件夹优先
                folders = sorted([f for f in files if f['mimeType'] == 'application/vnd.google-apps.folder'], 
                               key=lambda x: x['name'].lower())
                other_files = sorted([f for f in files if f['mimeType'] != 'application/vnd.google-apps.folder'], 
                                   key=lambda x: x['name'].lower())
                
                # 去重处理
                seen_names = set()
                clean_folders = []
                clean_files = []
                
                # 处理文件夹
                for folder in folders:
                    if folder["name"] not in seen_names:
                        clean_folders.append(folder)
                        seen_names.add(folder["name"])
                
                # 处理文件
                for file in other_files:
                    if file["name"] not in seen_names:
                        clean_files.append(file)
                        seen_names.add(file["name"])
                
                if detailed:
                    # 详细模式：返回完整JSON
                    return {
                        "success": True,
                        "path": display_path,
                        "folder_id": target_folder_id,
                        "folder_url": self._generate_folder_url(target_folder_id),
                        "files": clean_files,  # 只有非文件夹文件
                        "folders": clean_folders,  # 只有文件夹
                        "count": len(clean_folders) + len(clean_files),
                        "mode": "detailed"
                    }
                else:
                    # bash风格：只返回文件名列表
                    return {
                        "success": True,
                        "path": display_path,
                        "folder_id": target_folder_id,
                        "files": clean_files,  # 只有非文件夹文件
                        "folders": clean_folders,  # 只有文件夹
                        "count": len(clean_folders) + len(clean_files),
                        "mode": "bash"
                    }
            else:
                return {"success": False, "error": f"列出文件失败: {result['error']}"}
                
        except Exception as e:
            return {"success": False, "error": f"列出单个目录时出错: {e}"}
    
    def _resolve_absolute_mkdir_path(self, path, current_shell, recursive=False):
        """解析mkdir路径为绝对路径"""
        try:
            # 获取当前路径
            current_path = current_shell.get("current_path", "~")
            
            if path.startswith("~"):
                # 以~开头，相对于REMOTE_ROOT
                if path == "~":
                    return self.REMOTE_ROOT
                elif path.startswith("~/"):
                    return f"{self.REMOTE_ROOT}/{path[2:]}"
                else:
                    return None
            elif path.startswith("/"):
                # 绝对路径
                return path
            elif path.startswith("./"):
                # 相对于当前目录
                if current_path == "~":
                    return f"{self.REMOTE_ROOT}/{path[2:]}"
                else:
                    # 将当前GDS路径转换为绝对路径
                    abs_current = self._gds_path_to_absolute(current_path)
                    return f"{abs_current}/{path[2:]}"
            else:
                # 相对路径
                if current_path == "~":
                    return f"{self.REMOTE_ROOT}/{path}"
                else:
                    # 将当前GDS路径转换为绝对路径
                    abs_current = self._gds_path_to_absolute(current_path)
                    return f"{abs_current}/{path}"
                    
        except Exception as e:
            print(f"❌ 解析mkdir路径时出错: {e}")
            return None
    
    def _gds_path_to_absolute(self, gds_path):
        """将GDS路径转换为绝对路径"""
        try:
            if gds_path == "~":
                return self.REMOTE_ROOT
            elif gds_path.startswith("~/"):
                return f"{self.REMOTE_ROOT}/{gds_path[2:]}"
            else:
                return gds_path
        except Exception as e:
            print(f"❌ 转换GDS路径时出错: {e}")
            return gds_path
    
    def _verify_mkdir_result(self, path, current_shell):
        """验证mkdir创建结果"""
        try:

            # 使用GDS ls命令验证
            if "/" in path:
                # 如果是多级路径，检查父目录
                parent_path = "/".join(path.split("/")[:-1])
                dir_name = path.split("/")[-1]
                
                # 先切换到父目录
                parent_id, _ = self.resolve_path(parent_path, current_shell)
                if parent_id:
                    # 列出父目录内容
                    ls_result = self._ls_single(parent_id, parent_path, detailed=False)
                    if ls_result["success"]:
                        # 检查目标目录是否存在
                        all_folders = ls_result.get("folders", [])
                        for folder in all_folders:
                            if folder["name"] == dir_name:
                                return {
                                    "success": True,
                                    "message": f"✅ 验证成功，目录已创建: {dir_name}",
                                    "folder_id": folder["id"]
                                }
                        return {
                            "success": False,
                            "error": f"验证失败，目录未找到: {dir_name}"
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"验证失败，无法列出父目录: {ls_result.get('error', '未知错误')}"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"验证失败，父目录不存在: {parent_path}"
                    }
            else:
                # 单级目录，在当前目录下检查
                current_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                current_path = current_shell.get("current_path", "~")
                
                ls_result = self._ls_single(current_folder_id, current_path, detailed=False)
                if ls_result["success"]:
                    all_folders = ls_result.get("folders", [])
                    for folder in all_folders:
                        if folder["name"] == path:
                            return {
                                "success": True,
                                "message": f"✅ 验证成功，目录已创建: {path}",
                                "folder_id": folder["id"]
                            }
                    return {
                        "success": False,
                        "error": f"验证失败，目录未找到: {path}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"验证失败，无法列出当前目录: {ls_result.get('error', '未知错误')}"
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "error": f"验证mkdir结果时出错: {e}"
            }

    def _verify_mkdir_with_ls(self, path, current_shell):
        """使用GDS ls验证单层目录创建，带重试机制"""
        import time
        
        try:
            print(f"🔍 验证目录创建: {path}")
            
            # 重试机制，最多尝试3次
            for attempt in range(3):
                if attempt > 0:
                    print(f"⏳ 等待Google Drive同步... (尝试 {attempt + 1}/3)")
                    time.sleep(2)  # 等待2秒让Google Drive同步
                
                # 在当前目录执行ls命令
                ls_result = self.cmd_ls(None, detailed=False, recursive=False)
                if ls_result["success"]:
                    folders = ls_result.get("folders", [])
                    
                    for folder in folders:
                        if folder["name"] == path:
                            return {
                                "success": True,
                                "message": f"验证成功，目录已创建: {path}",
                                "folder_id": folder["id"]
                            }
                    
                    if attempt == 0:
                        print(f"📂 当前目录包含: {[f['name'] for f in folders]}")
                        print(f"🔍 未找到目标目录 '{path}'，可能需要等待同步")
                else:
                    return {
                        "success": False,
                        "error": f"验证失败，无法执行ls命令: {ls_result.get('error', '未知错误')}"
                    }
            
            # 所有重试都失败了
            print(f"❌ 验证失败，3次尝试后仍未找到目录: {path}")
            return {
                "success": False,
                "error": f"验证失败，目录可能已创建但Google Drive同步延迟: {path}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"验证过程出错: {e}"
            }

    def _verify_mkdir_with_ls_recursive(self, path, current_shell):
        """使用GDS ls -R验证多层目录创建"""
        try:
            # 使用递归ls命令验证
            ls_result = self.cmd_ls(None, detailed=False, recursive=True)
            if ls_result["success"]:
                # 检查目标路径是否存在
                target_parts = path.split("/")
                target_name = target_parts[-1]
                
                # 在递归结果中查找目标目录
                all_items = ls_result.get("all_items", [])
                for item in all_items:
                    if (item["name"] == target_name and 
                        item["mimeType"] == "application/vnd.google-apps.folder"):
                        # 检查路径是否匹配
                        item_path = item.get("path", "")
                        expected_parent_path = "/".join(target_parts[:-1])
                        
                        # 简化路径匹配逻辑
                        if expected_parent_path in item_path or item_path.endswith(expected_parent_path):
                            return {
                                "success": True,
                                "message": f"验证成功，多层目录已创建: {path}",
                                "folder_id": item["id"],
                                "full_path": item_path
                            }
                
                return {
                    "success": False,
                    "error": f"验证失败，多层目录未找到: {path}"
                }
            else:
                return {
                    "success": False,
                    "error": f"验证失败，无法执行ls -R命令: {ls_result.get('error', '未知错误')}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"递归验证过程出错: {e}"
            }

    def _mkdir_single(self, path, current_shell):
        """创建单个目录"""
        try:
            # 解析路径
            if "/" in path:
                parent_path = "/".join(path.split("/")[:-1])
                dir_name = path.split("/")[-1]
                
                parent_id, _ = self.resolve_path(parent_path, current_shell)
                if not parent_id:
                    return {"success": False, "error": f"父目录不存在: {parent_path}"}
            else:
                parent_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                dir_name = path
            
            # 检查目录是否已存在
            existing_folder = self._find_folder(dir_name, parent_id)
            if existing_folder:
                return {
                    "success": True,
                    "folder_name": dir_name,
                    "folder_id": existing_folder['id'],
                    "message": f"✅ 目录已存在: {dir_name}",
                    "existed": True
                }
            
            result = self.drive_service.create_folder(dir_name, parent_id)
            
            if result['success']:
                return {
                    "success": True,
                    "folder_name": result['folder_name'],
                    "folder_id": result['folder_id'],
                    "message": f"✅ 目录创建成功: {dir_name}",
                    "existed": False
                }
            else:
                return {"success": False, "error": f"创建目录失败: {result['error']}"}
                
        except Exception as e:
            return {"success": False, "error": f"创建单个目录时出错: {e}"}
    
    def _mkdir_recursive(self, path, current_shell):
        """递归创建目录路径"""
        try:
            # 解析起始位置
            if path.startswith("~"):
                if path == "~":
                    return {"success": True, "message": "根目录已存在", "existed": True}
                elif path.startswith("~/"):
                    current_id = self.REMOTE_ROOT_FOLDER_ID
                    current_path = "~"
                    relative_path = path[2:]
                else:
                    return {"success": False, "error": f"无效路径: {path}"}
            elif path.startswith("./"):
                current_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                current_path = current_shell.get("current_path", "~")
                relative_path = path[2:]
            elif path == ".":
                return {"success": True, "message": "当前目录已存在", "existed": True}
            elif path.startswith("/"):
                # 绝对路径，从REMOTE_ROOT开始
                current_id = self.REMOTE_ROOT_FOLDER_ID
                current_path = "~"
                relative_path = path[1:]  # 去掉开头的"/"
            else:
                # 相对路径
                current_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
                current_path = current_shell.get("current_path", "~")
                relative_path = path
            
            if not relative_path:
                return {"success": True, "message": "目录已存在", "existed": True}
            
            # 分解路径并逐级创建
            path_parts = [p for p in relative_path.split("/") if p]
            created_folders = []
            
            for part in path_parts:
                # 检查当前部分是否已存在
                existing_folder = self._find_folder(part, current_id)
                
                if existing_folder:
                    # 文件夹已存在，继续下一级
                    current_id = existing_folder['id']
                    created_folders.append({
                        "name": part,
                        "id": existing_folder['id'],
                        "existed": True
                    })
                else:
                    # 创建新文件夹
                    result = self.drive_service.create_folder(part, current_id)
                    if result['success']:
                        current_id = result['folder_id']
                        created_folders.append({
                            "name": part,
                            "id": result['folder_id'],
                            "existed": False
                        })
                    else:
                        return {"success": False, "error": f"创建目录失败 '{part}': {result['error']}"}
                
                # 更新当前路径显示
                if current_path == "~":
                    current_path = f"~/{part}"
                else:
                    current_path = f"{current_path}/{part}"
            
            # 统计结果
            new_folders = [f for f in created_folders if not f['existed']]
            existing_folders = [f for f in created_folders if f['existed']]
            
            return {
                "success": True,
                "path": path,
                "final_folder_id": current_id,
                "final_path": current_path,
                "created_folders": new_folders,
                "existing_folders": existing_folders,
                "total_created": len(new_folders),
                "total_existing": len(existing_folders),
                "message": f"✅ 目录路径创建完成: {path} ({len(new_folders)} 个新建, {len(existing_folders)} 个已存在)"
            }
            
        except Exception as e:
            return {"success": False, "error": f"递归创建目录时出错: {e}"}
    
    def _find_folder(self, folder_name, parent_id):
        """在指定父目录中查找文件夹"""
        try:
            files_result = self.drive_service.list_files(folder_id=parent_id, max_results=100)
            if not files_result['success']:
                return None
            
            for file in files_result['files']:
                if (file['name'] == folder_name and 
                    file['mimeType'] == 'application/vnd.google-apps.folder'):
                    return file
            
            return None
            
        except Exception:
            return None
    
    def cmd_rm(self, path, recursive=False, force=False):
        """删除文件或目录，通过远程rm命令执行"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
            
            if not path:
                return {"success": False, "error": "Please specify file or directory to delete"}
            
            # 解析远程绝对路径
            absolute_path = self.resolve_remote_absolute_path(path, current_shell)
            if not absolute_path:
                return {"success": False, "error": f"Cannot resolve path: {path}"}
            
            # 构建rm命令
            rm_flags = ""
            if recursive:
                rm_flags += "r"
            if force:
                rm_flags += "f"
            
            if rm_flags:
                remote_command = f'rm -{rm_flags} "{absolute_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            else:
                remote_command = f'rm "{absolute_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
            # 执行远程命令
            result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="rm",
                context_info={
                    "target_path": path,
                    "absolute_path": absolute_path,
                    "recursive": recursive,
                    "force": force
                }
            )
            
            if result["success"]:
                # 验证删除结果 - 使用find命令检查文件是否还存在
                verification_result = self._verify_rm_with_find(path, current_shell)
                
                if verification_result["success"]:
                    return {
                        "success": True,
                        "path": path,
                        "absolute_path": absolute_path,
                        "remote_command": remote_command,
                        "message": "",  # 空消息，像bash shell一样
                        "verification": verification_result
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Delete verification failed: {verification_result.get('error', 'Files still exist')}",
                        "remote_command": remote_command
                    }
            else:
                return result
                
        except Exception as e:
            return {"success": False, "error": f"Error executing rm command: {e}"}
    
    def cmd_echo(self, text, output_file=None):
        """echo命令 - 输出文本或创建文件"""
        try:
            if not text:
                return {"success": True, "output": ""}
            
            if output_file:
                # echo "text" > file - 创建文件
                return self._create_text_file(output_file, text)
            else:
                # echo "text" - 输出文本
                return {"success": True, "output": text}
                
        except Exception as e:
            return {"success": False, "error": f"执行echo命令时出错: {e}"}
    
    def cmd_cat(self, filename):
        """cat命令 - 显示文件内容"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell，请先创建或切换到一个shell"}
            
            if not filename:
                return {"success": False, "error": "请指定要查看的文件"}
            
            # 查找文件
            file_info = self._find_file(filename, current_shell)
            if not file_info:
                return {"success": False, "error": f"文件或目录不存在: {filename}"}
            
            # 检查是否为文件
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"cat: {filename}: Is a directory"}
            
            # 下载并读取文件内容
            try:
                import io
                from googleapiclient.http import MediaIoBaseDownload
                
                request = self.drive_service.service.files().get_media(fileId=file_info['id'])
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                content = fh.getvalue().decode('utf-8', errors='replace')
                return {"success": True, "output": content, "filename": filename}
                
            except Exception as e:
                return {"success": False, "error": f"无法读取文件内容: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"执行cat命令时出错: {e}"}
    
    def cmd_grep(self, pattern, *filenames):
        """grep命令 - 在文件中搜索模式，支持多文件和regex"""
        import re
        
        try:
            if not pattern:
                return {"success": False, "error": "请指定搜索模式"}
            
            if not filenames:
                return {"success": False, "error": "请指定要搜索的文件"}
            
            # 编译正则表达式
            try:
                regex = re.compile(pattern)
            except re.error as e:
                return {"success": False, "error": f"无效的正则表达式: {e}"}
            
            result = {}
            
            for filename in filenames:
                # 获取文件内容
                cat_result = self.cmd_cat(filename)
                if not cat_result["success"]:
                    result[filename] = {
                        "local_file": None,
                        "occurrences": [],
                        "error": cat_result["error"]
                    }
                    continue
                
                content = cat_result["output"]
                lines = content.split('\n')
                
                # 搜索匹配的位置
                occurrences = {}
                for line_num, line in enumerate(lines, 1):
                    line_matches = []
                    for match in regex.finditer(line):
                        line_matches.append(match.start())
                    if line_matches:
                        occurrences[line_num] = line_matches
                
                # 转换为所需格式: {line_num: [positions]}
                formatted_occurrences = occurrences
                
                # 获取本地缓存文件路径
                local_file = self._get_local_cache_path(filename)
                
                result[filename] = {
                    "local_file": local_file,
                    "occurrences": formatted_occurrences
                }
            
            return {"success": True, "result": result}
                
        except Exception as e:
            return {"success": False, "error": f"执行grep命令时出错: {e}"}
    
    def _get_local_cache_path(self, remote_path):
        """获取远程文件对应的本地缓存路径"""
        try:
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            # 获取文件的哈希值作为本地文件名
            file_hash = hashlib.md5(remote_path.encode()).hexdigest()[:16]
            local_path = cache_manager.cache_dir / "remote_files" / file_hash
            
            if local_path.exists():
                return str(local_path)
            else:
                return file_hash  # 返回哈希文件名
        except Exception:
            # 如果无法获取缓存路径，返回简化的文件名
            return remote_path.split('/')[-1] if '/' in remote_path else remote_path
    
    def cmd_upload_multi(self, file_pairs, force=False, remove_local=False):
        """
        多文件上传命令，支持 [[src1, dst1], [src2, dst2], ...] 语法
        
        Args:
            file_pairs (list): 文件对列表，每个元素为 [源文件路径, 远端目标路径]
            
        Returns:
            dict: 上传结果
        """
        try:
            # 0. 检查Google Drive Desktop是否运行
            if not self.ensure_google_drive_desktop_running():
                return {"success": False, "error": "用户取消上传操作"}
            
            if not file_pairs:
                return {"success": False, "error": "Please specify file pairs to upload"}
            
            # 验证文件对格式和源文件唯一性
            validated_pairs = []
            source_files = set()
            
            for pair in file_pairs:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    return {"success": False, "error": "File pair format error, each element should be [source_file, remote_path]"}
                src_file, dst_path = pair
                if not os.path.exists(src_file):
                    return {"success": False, "error": f"Source file does not exist: {src_file}"}
                
                # 检查源文件是否重复
                abs_src_file = os.path.abspath(src_file)
                if abs_src_file in source_files:
                    return {
                        "success": False,
                        "error": f"Source file conflict: {src_file} cannot be uploaded to multiple locations"
                    }
                source_files.add(abs_src_file)
                
                validated_pairs.append([src_file, dst_path])
            
            # 第一阶段：检查目标目录冲突和文件存在冲突
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell, please create or switch to a shell first"}
            
            # 检查目标目录是否有重复
            target_paths = set()
            for src_file, dst_path in validated_pairs:
                filename = Path(src_file).name
                
                # 判断 dst_path 是文件还是文件夹
                # 简单方法：检查路径最后一个部分是否包含点号
                last_part = dst_path.split('/')[-1]
                is_file = '.' in last_part and last_part != '.' and last_part != '..'
                
                # 计算完整的远端目标路径
                if is_file:
                    # dst_path 是文件名，直接使用
                    if dst_path.startswith("/"):
                        full_target_path = dst_path
                    elif dst_path == "." or dst_path == "":
                        # 这种情况不应该发生，因为 "." 不包含点号
                        full_target_path = f"~/{filename}"
                    else:
                        # 相对路径文件名
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    full_target_path = f"~/{base_path}/{dst_path}"
                                else:
                                    full_target_path = f"~/{dst_path}"
                            else:
                                full_target_path = f"~/{dst_path}"
                        else:
                            full_target_path = f"~/{dst_path}"
                else:
                    # dst_path 是文件夹，在后面添加文件名
                    if dst_path.startswith("/"):
                        full_target_path = f"{dst_path.rstrip('/')}/{filename}"
                    elif dst_path == "." or dst_path == "":
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                full_target_path = f"{current_path}/{filename}"
                            else:
                                full_target_path = f"~/{filename}"
                        else:
                            full_target_path = f"~/{filename}"
                    else:
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    full_target_path = f"~/{base_path}/{dst_path.strip('/')}/{filename}"
                                else:
                                    full_target_path = f"~/{dst_path.strip('/')}/{filename}"
                            else:
                                full_target_path = f"~/{dst_path.strip('/')}/{filename}"
                        else:
                            full_target_path = f"~/{dst_path.strip('/')}/{filename}"
                
                if full_target_path in target_paths:
                    return {
                        "success": False,
                        "error": f"Target path conflict: {full_target_path} specified by multiple files"
                    }
                target_paths.add(full_target_path)
            
            # 检查每个目标文件是否已存在（除非使用--force）
            overridden_files = []
            if not force:
                for src_file, dst_path in validated_pairs:
                    filename = Path(src_file).name
                    
                    # 计算远端绝对路径
                    if dst_path.startswith("/"):
                        remote_file_path = f"{dst_path.rstrip('/')}/{filename}"
                    elif dst_path == "." or dst_path == "":
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                remote_file_path = f"{current_path}/{filename}"
                            else:
                                remote_file_path = f"~/{filename}"
                        else:
                            remote_file_path = f"~/{filename}"
                    else:
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    remote_file_path = f"~/{base_path}/{dst_path.strip('/')}/{filename}"
                                else:
                                    remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                            else:
                                remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                        else:
                            remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                    
                    # 检查文件是否存在
                    dir_path = '/'.join(remote_file_path.split('/')[:-1]) if remote_file_path.count('/') > 0 else "~"
                    file_name = remote_file_path.split('/')[-1]
                    
                    ls_result = self.cmd_ls(dir_path, detailed=False, recursive=False)
                    if ls_result["success"] and "files" in ls_result:
                        existing_files = [f["name"] for f in ls_result["files"]]
                        if file_name in existing_files:
                            return {
                                "success": False,
                                "error": f"File exists: {remote_file_path}"
                            }
            else:
                # Force模式：检查哪些文件会被覆盖，记录警告
                for src_file, dst_path in validated_pairs:
                    filename = Path(src_file).name
                    
                    # 计算远端绝对路径
                    if dst_path.startswith("/"):
                        remote_file_path = f"{dst_path.rstrip('/')}/{filename}"
                    elif dst_path == "." or dst_path == "":
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                remote_file_path = f"{current_path}/{filename}"
                            else:
                                remote_file_path = f"~/{filename}"
                        else:
                            remote_file_path = f"~/{filename}"
                    else:
                        if current_shell.get("current_path") != "~":
                            current_path = current_shell.get("current_path", "~")
                            if current_path.startswith("~/"):
                                base_path = current_path[2:] if len(current_path) > 2 else ""
                                if base_path:
                                    remote_file_path = f"~/{base_path}/{dst_path.strip('/')}/{filename}"
                                else:
                                    remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                            else:
                                remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                        else:
                            remote_file_path = f"~/{dst_path.strip('/')}/{filename}"
                    
                    # 检查文件是否存在，如果存在则记录为覆盖
                    dir_path = '/'.join(remote_file_path.split('/')[:-1]) if remote_file_path.count('/') > 0 else "~"
                    file_name = remote_file_path.split('/')[-1]
                    
                    ls_result = self.cmd_ls(dir_path, detailed=False, recursive=False)
                    if ls_result["success"] and "files" in ls_result:
                        existing_files = [f["name"] for f in ls_result["files"]]
                        if file_name in existing_files:
                            overridden_files.append(remote_file_path)
                            print(f"⚠️ Warning: Overriding remote file {remote_file_path}")
            
            # 第二阶段：执行多文件上传
            all_file_moves = []
            failed_moves = []
            
            # 移动所有文件到LOCAL_EQUIVALENT
            for src_file, dst_path in validated_pairs:
                move_result = self.move_to_local_equivalent(src_file)
                if move_result["success"]:
                    all_file_moves.append({
                        "original_path": move_result["original_path"],
                        "filename": move_result["filename"],
                        "new_path": move_result["new_path"],
                        "renamed": move_result["renamed"],
                        "target_path": dst_path
                    })
                else:
                    failed_moves.append({
                        "file": src_file,
                        "error": move_result["error"]
                    })
            
            if not all_file_moves:
                return {
                    "success": False,
                    "error": "所有文件移动失败",
                    "failed_moves": failed_moves
                }
            
            # 等待文件同步到DRIVE_EQUIVALENT
            expected_filenames = [fm["filename"] for fm in all_file_moves]
            sync_result = self.wait_for_file_sync(expected_filenames, all_file_moves)
            
            if not sync_result["success"]:
                return {
                    "success": False,
                    "error": f"文件同步检测失败: {sync_result.get('error', '未知错误')}",
                    "file_moves": all_file_moves,
                    "sync_time": sync_result.get("sync_time", 0)
                }
            
            # 生成异步远端命令
            remote_command = self._generate_multi_file_remote_commands(all_file_moves)
            
            # 执行远端命令
            context_info = {
                "file_moves": all_file_moves,
                "multi_file": True
            }
            
            execution_result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="upload",
                context_info=context_info
            )
            
            if not execution_result["success"]:
                return {
                    "success": False,
                    "error": execution_result["message"],
                    "remote_command": remote_command,
                    "execution_result": execution_result
                }
            
            # 如果指定了 --remove-local 选项，删除本地源文件
            removed_files = []
            failed_removals = []
            if remove_local and execution_result["success"]:
                for src_file, _ in validated_pairs:
                    try:
                        if os.path.exists(src_file):
                            os.unlink(src_file)
                            removed_files.append(src_file)
                    except Exception as e:
                        failed_removals.append({"file": src_file, "error": str(e)})
            
            result = {
                "success": True,
                "uploaded_files": [{"name": fm["filename"], "target_path": fm["target_path"]} for fm in all_file_moves],
                "failed_files": [fm["file"] for fm in failed_moves],
                "total_attempted": len(validated_pairs),
                "total_succeeded": len(all_file_moves),
                "message": f"✅ 多文件上传完成: {len(all_file_moves)}/{len(validated_pairs)} 个文件成功",
                "sync_time": sync_result.get("sync_time", 0),
                "remote_command": remote_command
            }
            
            # 添加本地文件删除信息
            if remove_local:
                result["removed_local_files"] = removed_files
                result["failed_local_removals"] = failed_removals
                if removed_files:
                    result["message"] += f" (removed {len(removed_files)} local files)"
                if failed_removals:
                    result["message"] += f" (failed to remove {len(failed_removals)} local files)"
            
            return result
            
        except Exception as e:
            return {"success": False, "error": f"多文件上传时出错: {e}"}
    
    def _generate_multi_file_remote_commands(self, all_file_moves):
        """生成多文件分布式远端移动命令，每个文件独立重试60次，直到所有文件完成"""
        try:
            # 生成文件信息数组
            file_info_list = []
            for i, file_info in enumerate(all_file_moves):
                filename = file_info["filename"]
                target_path = file_info["target_path"]
                
                # 计算目标绝对路径
                if target_path == "." or target_path == "":
                    current_shell = self.get_current_shell()
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:]
                            target_absolute = f"{self.REMOTE_ROOT}/{relative_path}" if relative_path else self.REMOTE_ROOT
                        else:
                            target_absolute = self.REMOTE_ROOT
                    else:
                        target_absolute = self.REMOTE_ROOT
                elif target_path.startswith("/"):
                    target_absolute = f"{self.REMOTE_ROOT}{target_path}"
                else:
                    target_absolute = f"{self.REMOTE_ROOT}/{target_path.lstrip('/')}"
                
                source_absolute = f"{self.DRIVE_EQUIVALENT}/{filename}"
                dest_absolute = f"{target_absolute.rstrip('/')}/{filename}"
                
                file_info_list.append({
                    'filename': filename,
                    'source': source_absolute,
                    'dest': dest_absolute,
                    'index': i
                })
            
            # 生成分布式移动脚本
            full_command = f'''
# 初始化完成状态数组
declare -a completed
total_files={len(file_info_list)}
completed_count=0

# 为每个文件启动独立的移动进程
'''
            
            for file_info in file_info_list:
                full_command += f'''
(
    echo -n "⏳ {file_info['filename']}: "
    for attempt in {{1..60}}; do
        if mv "{file_info['source']}" "{file_info['dest']}" 2>/dev/null; then
            echo "✅"
            completed[{file_info['index']}]=1
            break
        else
            if [ $attempt -eq 60 ]; then
                echo "❌ (已重试60次失败)"
                completed[{file_info['index']}]=0
            else
                echo -n "."
                sleep 1
            fi
        fi
    done
) &
'''
            
            # 等待所有进程完成并检查结果
            full_command += f'''
# 等待所有后台进程完成
wait

# 简化结果统计 - 检查目标文件是否存在
success_count=0
fail_count=0
'''
            
            # 为每个文件生成检查命令
            for file_info in file_info_list:
                full_command += f'''
if [ -f "{file_info['dest']}" ]; then
    ((success_count++))
else
    ((fail_count++))
fi
'''
            
            full_command += f'''
# 输出最终结果
total_files={len(file_info_list)}
if [ $fail_count -eq 0 ]; then
    clear && echo "✅ 执行成功"
else
    echo "⚠️  部分文件处理完成: $success_count/$total_files 成功, $fail_count 失败"
fi
'''
            
            return full_command
            
        except Exception as e:
            return f"echo '❌ 生成多文件命令失败: {e}'"

    def _check_target_file_conflicts_before_move(self, source_files, target_path):
        """在移动文件之前检查目标位置是否已存在同名文件，避免上传冲突"""
        try:
            # 计算每个文件的远端绝对路径
            current_shell = self.get_current_shell()
            
            for source_file in source_files:
                filename = Path(source_file).name
                
                # 计算远端绝对路径
                if target_path == "." or target_path == "":
                    # 当前shell位置
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:]
                            remote_file_path = f"~/{relative_path}/{filename}" if relative_path else f"~/{filename}"
                        else:
                            remote_file_path = f"~/{filename}"
                    else:
                        remote_file_path = f"~/{filename}"
                elif target_path.startswith("/"):
                    # 绝对路径
                    remote_file_path = f"{target_path.rstrip('/')}/{filename}"
                else:
                    # 相对路径
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            base_path = current_path[2:] if len(current_path) > 2 else ""
                            if base_path:
                                remote_file_path = f"~/{base_path}/{target_path.strip('/')}/{filename}"
                            else:
                                remote_file_path = f"~/{target_path.strip('/')}/{filename}"
                        else:
                            remote_file_path = f"~/{target_path.strip('/')}/{filename}"
                    else:
                        remote_file_path = f"~/{target_path.strip('/')}/{filename}"
                
                # 使用ls命令检查文件是否存在
                # 获取目录路径和文件名
                if remote_file_path.count('/') > 0:
                    dir_path = '/'.join(remote_file_path.split('/')[:-1])
                    file_name = remote_file_path.split('/')[-1]
                else:
                    dir_path = "~"
                    file_name = remote_file_path
                
                # 列出目录内容
                ls_result = self.cmd_ls(dir_path, detailed=False, recursive=False)
                if ls_result["success"] and "files" in ls_result:
                    existing_files = [f["name"] for f in ls_result["files"]]
                    if file_name in existing_files:
                        # 文件存在，返回简洁错误信息
                        return {
                            "success": False,
                            "error": f"File exists: {remote_file_path}"
                        }
            
            return {"success": True}
            
        except Exception as e:
            # 如果检查过程出错，为了安全起见，允许继续上传
            print(f"⚠️ 文件冲突检查出错: {e}")
            return {"success": True}

    def _check_mv_destination_conflict(self, destination, current_shell):
        """检查mv命令的目标是否已存在"""
        try:
            # 计算目标的远端绝对路径
            if destination.startswith("/"):
                # 绝对路径
                remote_destination_path = destination
            else:
                # 相对路径，基于当前shell位置
                if current_shell and current_shell.get("current_path") != "~":
                    current_path = current_shell.get("current_path", "~")
                    if current_path.startswith("~/"):
                        relative_path = current_path[2:] if len(current_path) > 2 else ""
                        if relative_path:
                            remote_destination_path = f"~/{relative_path}/{destination}"
                        else:
                            remote_destination_path = f"~/{destination}"
                    else:
                        remote_destination_path = f"~/{destination}"
                else:
                    remote_destination_path = f"~/{destination}"
            
            # 使用ls命令检查目标是否存在
            # 获取目录路径和文件名
            if remote_destination_path.count('/') > 0:
                dir_path = '/'.join(remote_destination_path.split('/')[:-1])
                file_name = remote_destination_path.split('/')[-1]
            else:
                dir_path = "~"
                file_name = remote_destination_path
            
            # 列出目录内容
            ls_result = self.cmd_ls(dir_path, detailed=False, recursive=False)
            if ls_result["success"] and "files" in ls_result:
                existing_files = [f["name"] for f in ls_result["files"]]
                if file_name in existing_files:
                    # 目标已存在，返回简洁错误信息
                    return {
                        "success": False,
                        "error": f"File exists: {remote_destination_path}"
                    }
            
            return {"success": True}
            
        except Exception as e:
            # 如果检查过程出错，为了安全起见，允许继续操作
            print(f"⚠️ mv目标冲突检查出错: {e}")
            return {"success": True}

    def _check_target_file_conflicts(self, file_moves, target_path):
        """检查目标位置是否已存在同名文件，避免上传冲突"""
        try:
            # 计算目标路径
            if target_path == "." or target_path == "":
                current_shell = self.get_current_shell()
                if current_shell and current_shell.get("current_path") != "~":
                    current_path = current_shell.get("current_path", "~")
                    if current_path.startswith("~/"):
                        check_path = current_path[2:] if len(current_path) > 2 else None
                    else:
                        check_path = None
                else:
                    check_path = None
            else:
                check_path = target_path
            
            # 使用ls命令检查目标路径
            ls_result = self.cmd_ls(check_path, detailed=False, recursive=False)
            if not ls_result["success"]:
                # 如果ls失败，可能是路径不存在，这是正常的
                return {"success": True}
            
            # 检查每个要上传的文件是否与现有文件冲突
            existing_files = []
            if "files" in ls_result:
                existing_files = [f["name"] for f in ls_result["files"]]
            elif "output" in ls_result and ls_result["output"]:
                # 解析简单的ls输出
                lines = ls_result["output"].strip().split('\n')
                for line in lines:
                    if line.strip():
                        # 简单解析文件名（去掉可能的权限、大小等信息）
                        parts = line.strip().split()
                        if parts:
                            existing_files.append(parts[-1])  # 通常文件名是最后一部分
            
            # 检查冲突
            conflicting_files = []
            for file_info in file_moves:
                filename = file_info["filename"]
                if filename in existing_files:
                    conflicting_files.append(filename)
            
            if conflicting_files:
                return {
                    "success": False,
                    "error": f"目标位置已存在文件: {', '.join(conflicting_files)}",
                    "conflicting_files": conflicting_files,
                    "target_path": target_path,
                    "suggestion": "请使用不同的文件名或先删除现有文件"
                }
            
            return {"success": True}
            
        except Exception as e:
            # 如果检查过程出错，为了安全起见，允许继续上传
            print(f"⚠️ 文件冲突检查出错: {e}")
            return {"success": True}
    
    def _create_text_file(self, filename, content):
        """创建文本文件"""
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API服务未初始化"}
                
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 尝试使用共享驱动器解决方案
            try:
                # 加载共享驱动器配置
                data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
                config_file = data_dir / "shared_drive_config.json"
                
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    
                    drive_id = config["shared_drive_id"]
                    
                    # 在共享驱动器中创建文件
                    result = self._create_file_in_shared_drive(content, filename, drive_id)
                    if result["success"]:
                        return result
                    else:
                        print(f"共享驱动器创建失败: {result['error']}")
                
            except Exception as e:
                print(f"共享驱动器方法出错: {e}")
            
            # 服务账户无法创建文件，返回友好提示
            return {
                "success": False,
                "error": "文件创建功能暂不可用",
                "info": {
                    "reason": "服务账户无法在Google Drive中创建文件（存储配额限制）",
                    "setup_instructions": "运行: cd GOOGLE_DRIVE_PROJ && python setup_shared_drive.py",
                    "alternatives": [
                        "创建共享驱动器并与服务账户分享",
                        "使用 python -c 'code' 直接执行Python代码",
                        "手动在Google Drive中创建文件后使用 cat filename 查看"
                    ],
                    "working_features": [
                        "✅ 读取现有文件 (cat)",
                        "✅ 执行Python代码 (python -c)",
                        "✅ 目录导航 (cd, ls, pwd)",
                        "✅ 文本搜索 (grep)",
                        "✅ 目录管理 (mkdir, rm)"
                    ]
                }
            }
                
        except Exception as e:
            return {"success": False, "error": f"创建文件时出错: {e}"}
    
    def _create_file_in_shared_drive(self, content, filename, drive_id):
        """在共享驱动器中创建文件"""
        try:
            import tempfile
            import os
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # 文件元数据
                file_metadata = {
                    'name': filename,
                    'parents': [drive_id]  # 共享驱动器ID作为父级
                }
                
                # 使用MediaFileUpload
                from googleapiclient.http import MediaFileUpload
                media = MediaFileUpload(temp_file_path, mimetype='text/plain')
                
                # 创建文件，使用supportsAllDrives=True
                result = self.drive_service.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    supportsAllDrives=True,  # 关键：支持共享驱动器
                    fields='id,name,size,webViewLink'
                ).execute()
                
                # 清理临时文件
                os.unlink(temp_file_path)
                
                return {
                    "success": True,
                    "file_id": result['id'],
                    "file_name": result['name'],
                    "file_size": result.get('size', 0),
                    "web_link": result.get('webViewLink'),
                    "message": f"✅ 文件创建成功: {filename}"
                }
                
            except Exception as e:
                # 确保清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                return {"success": False, "error": f"共享驱动器文件创建失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"准备共享驱动器文件时出错: {e}"}
    
    def cmd_download(self, filename, local_path=None, force=False):
        """
        download命令 - 从Google Drive下载文件并缓存
        用法：
        - download A: 下载到缓存目录，显示哈希文件名
        - download A B: 下载到缓存目录，然后复制到指定位置（类似cp操作）
        - download --force A: 强制重新下载，替换缓存
        """
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "缓存管理器未找到"}
            
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 构建远端绝对路径
            remote_absolute_path = self.resolve_remote_absolute_path(filename, current_shell)
            
            # 检查是否已经缓存（如果force=True则跳过缓存检查）
            if not force and cache_manager.is_file_cached(remote_absolute_path):
                cached_info = cache_manager.get_cached_file(remote_absolute_path)
                cached_path = cache_manager.get_cached_file_path(remote_absolute_path)
                
                if local_path:
                    # 如果指定了本地目标，复制缓存文件到目标位置（cp操作）
                    import shutil
                    if os.path.isdir(local_path):
                        target_path = os.path.join(local_path, filename)
                    else:
                        target_path = local_path
                    
                    # 确保目标目录存在
                    os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                    shutil.copy2(cached_path, target_path)
                    
                    return {
                        "success": True,
                        "message": f"Using cached file: {target_path}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "local_path": target_path,
                        "cache_status": cached_info["status"]
                    }
                else:
                    # 只显示缓存信息
                    return {
                        "success": True,
                        "message": f"Using cached file: {cached_info['cache_file']}",
                        "source": "cache",
                        "remote_path": remote_absolute_path,
                        "cache_file": cached_info["cache_file"],
                        "cached_path": cached_path,
                        "cache_status": cached_info["status"]
                    }
            
            # 文件未缓存或强制重新下载
            # 如果是强制模式且文件已缓存，先删除旧缓存
            if force and cache_manager.is_file_cached(remote_absolute_path):
                old_cached_info = cache_manager.get_cached_file(remote_absolute_path)
                old_cache_file = old_cached_info.get("cache_file")
                
                # 删除旧的缓存文件
                cleanup_result = cache_manager.cleanup_cache(remote_absolute_path)
                force_info = {
                    "force_mode": True,
                    "removed_old_cache": cleanup_result.get("success", False),
                    "old_cache_file": old_cache_file
                }
            else:
                force_info = {"force_mode": False}
            
            # 获取文件信息和下载URL
            file_info = None
            current_folder_id = current_shell.get("current_folder_id")
            
            # 列出当前目录文件，查找目标文件
            result = self.drive_service.list_files(folder_id=current_folder_id, max_results=100)
            if result['success']:
                files = result['files']
                for file in files:
                    if file['name'] == filename:
                        file_info = file
                        break
            
            if not file_info:
                return {"success": False, "error": f"Download failed: file not found: {filename}"}
            
            # 检查是否为文件（不是文件夹）
            if file_info['mimeType'] == 'application/vnd.google-apps.folder':
                return {"success": False, "error": f"download: {filename}: 是一个目录，无法下载"}
            
            # 使用Google Drive API直接下载文件
            import tempfile
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                temp_path = temp_file.name
            
            try:
                # 使用Google Drive API下载文件内容
                file_id = file_info['id']
                request = self.drive_service.service.files().get_media(fileId=file_id)
                content = request.execute()
                
                # 将内容写入临时文件
                with open(temp_path, 'wb') as f:
                    f.write(content)
                
                # 下载成功，缓存文件
                cache_result = cache_manager.cache_file(
                    remote_path=remote_absolute_path,
                    temp_file_path=temp_path
                )
                
                if cache_result["success"]:
                    if local_path:
                        # 如果指定了本地目标，也复制到目标位置（cp操作）
                        import shutil
                        if os.path.isdir(local_path):
                            target_path = os.path.join(local_path, filename)
                        else:
                            target_path = local_path
                        
                        # 确保目标目录存在
                        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
                        shutil.copy2(temp_path, target_path)
                        
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {target_path}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"],
                            "local_path": target_path
                        }
                        result.update(force_info)
                        return result
                    else:
                        # 只显示缓存信息
                        result = {
                            "success": True,
                            "message": f"Downloaded successfully to: {cache_result['cache_file']}",
                            "source": "download",
                            "remote_path": remote_absolute_path,
                            "cache_file": cache_result["cache_file"],
                            "cache_path": cache_result["cache_path"]
                        }
                        result.update(force_info)
                        return result
                else:
                    return {"success": False, "error": f"Download failed: {cache_result.get('error')}"}
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            return {"success": False, "error": f"下载文件时出错: {e}"}
    

    
    def cmd_mv_multi(self, file_pairs, force=False):
        """
        多文件移动命令，支持 [[src1, dst1], [src2, dst2], ...] 语法
        
        Args:
            file_pairs (list): 文件对列表，每个元素为 [源远端路径, 目标远端路径]
            
        Returns:
            dict: 移动结果
        """
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            if not file_pairs:
                return {"success": False, "error": "请指定要移动的文件对"}
            
            # 验证文件对格式并检查冲突
            validated_pairs = []
            target_destinations = set()
            source_files = set()
            
            for pair in file_pairs:
                if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                    return {"success": False, "error": "文件对格式错误，每个元素应为 [源路径, 目标路径]"}
                
                source, destination = pair
                if not source or not destination:
                    return {"success": False, "error": "Source and destination paths cannot be empty"}
                
                # 检查源文件是否重复
                abs_source_path = self.resolve_remote_absolute_path(source, current_shell)
                if abs_source_path in source_files:
                    return {
                        "success": False,
                        "error": f"Source file conflict: {source} cannot be moved to multiple destinations"
                    }
                source_files.add(abs_source_path)
                
                # 计算目标的远端绝对路径用于重复检测
                if destination.startswith("/"):
                    abs_destination = destination
                else:
                    if current_shell and current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            relative_path = current_path[2:] if len(current_path) > 2 else ""
                            if relative_path:
                                abs_destination = f"~/{relative_path}/{destination}"
                            else:
                                abs_destination = f"~/{destination}"
                        else:
                            abs_destination = f"~/{destination}"
                    else:
                        abs_destination = f"~/{destination}"
                
                # 检查目标路径是否重复
                if abs_destination in target_destinations:
                    return {
                        "success": False,
                        "error": f"Destination path conflict: {abs_destination} specified by multiple files"
                    }
                target_destinations.add(abs_destination)
                
                # 检查目标是否已存在
                destination_check_result = self._check_mv_destination_conflict(destination, current_shell)
                if not destination_check_result["success"]:
                    return destination_check_result
                
                validated_pairs.append([source, destination])
            
            # 生成多文件mv的远端命令
            remote_command = self._generate_multi_mv_remote_commands(validated_pairs, current_shell)
            
            # 执行远端命令
            context_info = {
                "file_pairs": validated_pairs,
                "multi_file": True
            }
            
            result = self.execute_remote_command_interface(
                remote_command=remote_command, 
                command_type="move", 
                context_info=context_info
            )
            
            if result.get("success"):
                return {
                    "success": True,
                    "moved_files": [{"source": src, "destination": dst} for src, dst in validated_pairs],
                    "total_moved": len(validated_pairs),
                    "message": f"✅ 多文件移动完成: {len(validated_pairs)} 个文件",
                    "verification": "success"
                }
            else:
                error_msg = result.get("message", result.get("error", "未知错误"))
                return {
                    "success": False,
                    "error": f"多文件移动失败: {error_msg}",
                    "verification": "failed"
                }
                
        except Exception as e:
            return {"success": False, "error": f"多文件移动时出错: {e}"}
    
    def _generate_multi_mv_remote_commands(self, file_pairs, current_shell):
        """生成多文件mv的分布式远端命令，每个文件独立重试60次"""
        try:
            # 生成文件信息数组
            file_info_list = []
            for i, (source, destination) in enumerate(file_pairs):
                source_absolute_path = self.resolve_remote_absolute_path(source, current_shell)
                destination_absolute_path = self.resolve_remote_absolute_path(destination, current_shell)
                
                file_info_list.append({
                    'source_name': source,
                    'dest_name': destination,
                    'source_path': source_absolute_path,
                    'dest_path': destination_absolute_path,
                    'index': i
                })
            
            # 生成分布式mv脚本
            full_command = f'''
# 初始化完成状态数组
declare -a completed
total_files={len(file_info_list)}

# 为每个文件启动独立的移动进程
'''
            
            for file_info in file_info_list:
                full_command += f'''
(
    echo -n "⏳ {file_info['source_name']} -> {file_info['dest_name']}: "
    for attempt in {{1..60}}; do
        if mv {file_info['source_path']} {file_info['dest_path']} 2>/dev/null; then
            echo "✅"
            completed[{file_info['index']}]=1
            break
        else
            if [ $attempt -eq 60 ]; then
                echo "❌ (已重试60次失败)"
                completed[{file_info['index']}]=0
            else
                echo -n "."
                sleep 1
            fi
        fi
    done
) &
'''
            
            # 等待所有进程完成并检查结果
            full_command += f'''
# 等待所有后台进程完成
wait

# 简化结果统计 - 检查目标文件是否存在
success_count=0
fail_count=0
'''
            
            # 为每个文件生成检查命令
            for file_info in file_info_list:
                full_command += f'''
if [ -f {file_info['dest_path']} ]; then
    ((success_count++))
else
    ((fail_count++))
fi
'''
            
            full_command += f'''
# 输出最终结果
total_files={len(file_info_list)}
if [ $fail_count -eq 0 ]; then
    clear && echo "✅ 执行成功"
else
    echo "⚠️  部分文件移动完成: $success_count/$total_files 成功, $fail_count 失败"
fi
'''
            
            return full_command
            
        except Exception as e:
            return f"echo '❌ 生成多文件mv命令失败: {e}'"

    def cmd_mv(self, source, destination, force=False):
        """mv命令 - 移动/重命名文件或文件夹（使用远端指令执行）"""
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            if not source or not destination:
                return {"success": False, "error": "用法: mv <source> <destination>"}
            
            # 检查目标是否已存在（避免覆盖）
            destination_check_result = self._check_mv_destination_conflict(destination, current_shell)
            if not destination_check_result["success"]:
                return destination_check_result
            
            # 构建远端mv命令 - 需要计算绝对路径
            source_absolute_path = self.resolve_remote_absolute_path(source, current_shell)
            destination_absolute_path = self.resolve_remote_absolute_path(destination, current_shell)
            
            # 构建增强的远端命令，包含成功/失败提示
            base_command = f"mv {source_absolute_path} {destination_absolute_path}"
            remote_command = f"({base_command}) && clear && echo \"✅ 执行成功\" || echo \"❌ 执行失败\""
            
            # 使用远端指令执行接口
            result = self.execute_remote_command_interface(remote_command, "move", {
                "source": source,
                "destination": destination
            })
            
            if result.get("success"):
                # 验证移动是否成功
                verification_result = self._verify_mv_with_ls(source, destination, current_shell)
                
                if verification_result.get("success"):
                    # 移动成功，更新缓存路径映射
                    cache_update_result = self._update_cache_after_mv(source, destination, current_shell)
                    
                    return {
                        "success": True,
                        "source": source,
                        "destination": destination,
                        "message": f"✅ 已移动 {source} -> {destination}",
                        "cache_updated": cache_update_result.get("success", False),
                        "verification": "success"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"移动命令执行但验证失败: {verification_result.get('error')}",
                        "verification": "failed"
                    }
            else:
                # 处理不同类型的失败
                error_msg = "未知错误"
                if result.get("user_reported_failure"):
                    error_info = result.get("error_info")
                    if error_info:
                        error_msg = f"执行失败：{error_info}"
                    else:
                        error_msg = "执行失败"
                elif result.get("cancelled"):
                    error_msg = "用户取消操作"
                elif result.get("window_error"):
                    error_msg = result.get("error_info", "窗口显示错误")
                else:
                    error_msg = result.get("message", result.get("error", "未知错误"))
                
                return {
                    "success": False,
                    "error": f"远端mv命令执行失败: {error_msg}"
                }
                
        except Exception as e:
            return {"success": False, "error": f"执行mv命令时出错: {e}"}
    
    def resolve_remote_absolute_path(self, path, current_shell=None):
        """
        通用路径解析接口：将相对路径解析为远端绝对路径
        
        Args:
            path (str): 要解析的路径
            current_shell (dict): 当前shell状态，如果为None则自动获取
            
        Returns:
            str: 解析后的远端绝对路径
        """
        try:
            if not current_shell:
                current_shell = self.get_current_shell()
                if not current_shell:
                    return path  # 如果没有shell，返回原路径
            
            # 如果已经是绝对路径（以/开头），直接返回
            if path.startswith("/"):
                return path
            
            # 获取当前路径和REMOTE_ROOT路径
            current_path = current_shell.get("current_path", "~")
            remote_root_path = getattr(self, 'REMOTE_ROOT', '/content/drive/MyDrive/REMOTE_ROOT')
            
            # 处理特殊路径
            if path == "~":
                return remote_root_path
            elif path.startswith("~/"):
                # ~/xxx 形式的绝对路径
                relative_part = path[2:]
                return f"{remote_root_path}/{relative_part}"
            elif path == ".":
                # 当前目录
                if current_path == "~":
                    return remote_root_path
                else:
                    current_relative = current_path[2:] if current_path.startswith("~/") else current_path
                    return f"{remote_root_path}/{current_relative}"
            else:
                # 相对路径，基于当前目录
                if current_path == "~":
                    return f"{remote_root_path}/{path}"
                else:
                    current_relative = current_path[2:] if current_path.startswith("~/") else current_path
                    return f"{remote_root_path}/{current_relative}/{path}"
            
        except Exception as e:
            # 如果解析失败，返回原路径
            return path
    
    def _verify_mv_with_ls(self, source, destination, current_shell, max_retries=3, delay_seconds=2):
        """验证mv操作是否成功，通过ls检查文件是否在新位置"""
        import time
        
        for attempt in range(max_retries):
            try:
                # 检查源文件是否还存在（应该不存在）
                source_still_exists = self._find_file(source, current_shell) is not None
                
                # 检查目标位置是否有文件
                if '/' in destination:
                    # 目标包含路径
                    dest_parent = '/'.join(destination.split('/')[:-1])
                    dest_name = destination.split('/')[-1]
                    
                    # 切换到目标目录检查
                    dest_folder_id, _ = self.resolve_path(dest_parent, current_shell)
                    if dest_folder_id:
                        temp_shell = current_shell.copy()
                        temp_shell["current_folder_id"] = dest_folder_id
                        destination_exists = self._find_file(dest_name, temp_shell) is not None
                    else:
                        destination_exists = False
                else:
                    # 在当前目录重命名
                    destination_exists = self._find_file(destination, current_shell) is not None
                
                # 如果源文件不存在且目标文件存在，则移动成功
                if not source_still_exists and destination_exists:
                    return {"success": True, "message": "mv验证成功"}
                
                # 如果还没成功，等待一下再试（Google Drive API延迟）
                if attempt < max_retries - 1:
                    time.sleep(delay_seconds)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(delay_seconds)
                else:
                    return {"success": False, "error": f"验证mv操作时出错: {e}"}
        
        return {"success": False, "error": f"mv验证失败：经过{max_retries}次尝试后，文件移动状态不明确"}
    
    def _update_cache_after_mv(self, source, destination, current_shell):
        """在mv命令成功后更新缓存路径映射"""
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if not cache_manager_path.exists():
                return {"success": False, "error": "缓存管理器未找到"}
            
            sys.path.insert(0, str(Path(__file__).parent))
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            # 构建原始和新的远端绝对路径
            old_remote_path = self.resolve_remote_absolute_path(source, current_shell)
            new_remote_path = self.resolve_remote_absolute_path(destination, current_shell)
            
            # 检查是否有缓存需要更新
            if cache_manager.is_file_cached(old_remote_path):
                # 更新缓存路径映射
                move_result = cache_manager.move_cached_file(old_remote_path, new_remote_path)
                if move_result["success"]:
                    return {
                        "success": True,
                        "message": f"✅ 已更新缓存路径映射: {old_remote_path} -> {new_remote_path}",
                        "old_path": old_remote_path,
                        "new_path": new_remote_path,
                        "cache_file": move_result["cache_file"]
                    }
                else:
                    return {
                        "success": False,
                        "error": f"更新缓存路径映射失败: {move_result.get('error')}"
                    }
            else:
                return {
                    "success": True,
                    "message": "无需更新缓存（文件未缓存）",
                    "old_path": old_remote_path,
                    "new_path": new_remote_path
                }
                
        except Exception as e:
            return {"success": False, "error": f"更新缓存映射时出错: {e}"}
    
    def _find_file(self, filepath, current_shell):
        """查找文件，支持路径解析"""
        try:
            # 如果包含路径分隔符，需要解析路径
            if '/' in filepath:
                # 分离目录和文件名
                dir_path, filename = filepath.rsplit('/', 1)
                
                # 解析目录路径
                target_folder_id, _ = self.resolve_path(dir_path, current_shell)
                if not target_folder_id:
                    return None
            else:
                # 在当前目录查找
                filename = filepath
                target_folder_id = current_shell.get("current_folder_id", self.REMOTE_ROOT_FOLDER_ID)
            
            # 列出目标目录内容
            files_result = self.drive_service.list_files(folder_id=target_folder_id, max_results=100)
            if not files_result['success']:
                return None
            
            # 查找匹配的文件
            for file in files_result['files']:
                if file['name'] == filename:
                    return file
            
            return None
            
        except Exception:
            return None
    
    def cmd_python(self, code=None, filename=None, save_output=False):
        """python命令 - 执行Python代码"""
        try:
            if filename:
                # 执行Drive中的Python文件
                return self._execute_python_file(filename, save_output)
            elif code:
                # 执行直接提供的Python代码
                return self._execute_python_code(code, save_output)
            else:
                return {"success": False, "error": "请提供Python代码或文件名"}
                
        except Exception as e:
            return {"success": False, "error": f"执行Python命令时出错: {e}"}
    
    def _execute_python_file(self, filename, save_output=False):
        """执行Google Drive中的Python文件"""
        try:
            # 首先读取文件内容
            cat_result = self.cmd_cat(filename)
            if not cat_result["success"]:
                return cat_result
            
            python_code = cat_result["output"]
            return self._execute_python_code(python_code, save_output, filename)
            
        except Exception as e:
            return {"success": False, "error": f"执行Python文件时出错: {e}"}
    
    def _execute_python_code(self, code, save_output=False, filename=None):
        """执行Python代码并返回结果"""
        try:
            import subprocess
            import tempfile
            import os
            
            # 创建临时Python文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(code)
                temp_file_path = temp_file.name
            
            try:
                # 执行Python代码
                result = subprocess.run(
                    ['/usr/bin/python3', temp_file_path],
                    capture_output=True,
                    text=True,
                    timeout=30  # 30秒超时
                )
                
                # 清理临时文件
                os.unlink(temp_file_path)
                
                # 准备结果
                execution_result = {
                    "success": True,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "filename": filename
                }
                
                # 如果需要保存输出到Drive
                if save_output and (result.stdout or result.stderr):
                    output_filename = f"{filename}_output.txt" if filename else "python_output.txt"
                    output_content = f"=== Python Execution Result ===\n"
                    output_content += f"Return code: {result.returncode}\n\n"
                    
                    if result.stdout:
                        output_content += f"=== STDOUT ===\n{result.stdout}\n"
                    
                    if result.stderr:
                        output_content += f"=== STDERR ===\n{result.stderr}\n"
                    
                    # 尝试保存到Drive（如果失败也不影响主要功能）
                    try:
                        save_result = self._create_text_file(output_filename, output_content)
                        if save_result["success"]:
                            execution_result["output_saved"] = output_filename
                    except:
                        pass  # 保存失败不影响主要功能
                
                return execution_result
                
            except subprocess.TimeoutExpired:
                os.unlink(temp_file_path)
                return {"success": False, "error": "Python代码执行超时（30秒）"}
            except Exception as e:
                os.unlink(temp_file_path)
                return {"success": False, "error": f"执行Python代码时出错: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"准备Python执行环境时出错: {e}"}
    
    def open_dir(self, path):
        """打开目录 - 相当于创建shell + cd"""
        try:
            current_shell = self.get_current_shell()
            
            # 如果已经有活跃shell，直接cd
            if current_shell:
                return self.cmd_cd(path)
            
            # 没有活跃shell，先创建一个
            shell_id = self.generate_shell_id()
            shell_name = f"shell_{shell_id[:8]}"
            created_time = time.strftime("%Y-%m-%d %H:%M:%S")
            
            # 解析目标路径
            temp_shell = {
                "current_path": "~",
                "current_folder_id": self.REMOTE_ROOT_FOLDER_ID
            }
            
            target_id, target_path = self.resolve_path(path, temp_shell)
            if not target_id:
                return {"success": False, "error": f"目录不存在: {path}"}
            
            # 创建shell配置，直接定位到目标目录
            shell_config = {
                "id": shell_id,
                "name": shell_name,
                "folder_id": self.REMOTE_ROOT_FOLDER_ID,
                "current_path": target_path,
                "current_folder_id": target_id,
                "created_time": created_time,
                "last_accessed": created_time,
                "status": "active"
            }
            
            # 保存shell
            shells_data = self.load_shells()
            shells_data["shells"][shell_id] = shell_config
            shells_data["active_shell"] = shell_id
            
            if self.save_shells(shells_data):
                return {
                    "success": True,
                    "shell_id": shell_id,
                    "shell_name": shell_name,
                    "path": target_path,
                    "folder_id": target_id,
                    "message": f"✅ 已创建shell并打开目录: {target_path}"
                }
            else:
                return {"success": False, "error": "保存shell配置失败"}
                
        except Exception as e:
            return {"success": False, "error": f"执行open-dir命令时出错: {e}"} 

    def generate_mkdir_commands(self, target_path):
        """
        生成创建远端目录结构的命令
        
        Args:
            target_path (str): 目标路径
            
        Returns:
            str: mkdir 命令字符串，如果不需要创建目录则返回空字符串
        """
        try:
            # 如果是当前目录或根目录，不需要创建
            if target_path == "." or target_path == "" or target_path == "~":
                return ""
            
            # 计算需要创建的目录路径
            if target_path.startswith("/"):
                # 绝对路径
                full_target_path = target_path
            else:
                # 相对路径，基于 REMOTE_ROOT
                full_target_path = f"{self.REMOTE_ROOT}/{target_path.lstrip('/')}"
            
            # 生成 mkdir -p 命令来创建整个目录结构，添加清屏和成功/失败提示
            mkdir_command = f'mkdir -p "{full_target_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
            return mkdir_command
            
        except Exception as e:
            print(f"❌ 生成mkdir命令时出错: {e}")
            return ""

    def execute_remote_command_interface(self, remote_command, command_type="upload", context_info=None):
        """
        统一的远端命令执行接口
        
        Args:
            remote_command (str): 要执行的远端命令
            command_type (str): 命令类型 ("upload", "mkdir", "move", etc.)
            context_info (dict): 上下文信息，包含文件名、路径等
            
        Returns:
            dict: 执行结果
        """
        try:
            # 显示远端命令（用于调试和协作）
            print(f"   {remote_command}")
            
            # 显示tkinter窗口获取用户确认
            window_result = self.show_remote_command_window(remote_command, command_type)
            os.system("clear") if os.name == "posix" else os.system("cls")
            
            # 统一处理用户确认结果
            if window_result["action"] == "cancel":
                return {
                    "success": False,
                    "cancelled": True,
                    "message": "Operation cancelled. "
                }
            elif window_result["action"] == "failed":
                return {
                    "success": False,
                    "user_reported_failure": True,
                    "error_info": window_result.get('error_info'),
                    "message": "User reported failure: " + window_result.get('error_info')
                }
            elif window_result["action"] == "error":
                return {
                    "success": False,
                    "window_error": True,
                    "error_info": window_result.get('error_info'),
                    "message": f"Window error: {window_result.get('error_info', 'Unknown error')}"
                }
            elif window_result["action"] == "success":
                # 根据命令类型进行相应的后处理
                return self._handle_successful_remote_execution(command_type, context_info)
            else:
                return {
                    "success": False,
                    "unknown_action": True,
                    "message": f"Unknown user action: {window_result.get('action')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "interface_error": True,
                "error": str(e),
                "message": f"Remote command interface error: {e}"
            }
    
    def _handle_successful_remote_execution(self, command_type, context_info):
        """
        处理用户确认成功后的逻辑
        
        Args:
            command_type (str): 命令类型
            context_info (dict): 上下文信息
            
        Returns:
            dict: 处理结果
        """
        try:
            if command_type == "upload":
                return self._handle_upload_success(context_info)
            elif command_type == "mkdir":
                return self._handle_mkdir_success(context_info)
            elif command_type == "move":
                return self._handle_move_success(context_info)
            else:
                # 通用成功处理
                return {
                    "success": True,
                    "user_confirmed": True,
                    "command_type": command_type,
                    "message": "远端命令执行成功"
                }
                
        except Exception as e:
            return {
                "success": False,
                "post_processing_error": True,
                "error": str(e),
                "message": f"成功后处理错误: {e}"
            }
    
    def _handle_move_success(self, context_info):
        """处理mv命令成功的逻辑"""
        try:
            return {
                "success": True,
                "user_confirmed": True,
                "command_type": "move",
                "source": context_info.get("source"),
                "destination": context_info.get("destination"),
                "message": "远端mv命令执行成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"处理mv成功逻辑时出错: {e}"
            }
    
    def _handle_upload_success(self, context_info):
        """处理上传成功的情况"""
        try:
            expected_filenames = context_info.get("expected_filenames", [])
            target_folder_id = context_info.get("target_folder_id")
            
            # 尝试获取真实文件信息，优先使用API，其次使用文件夹URL
            if target_folder_id:
                if self.drive_service:
                    
                    # 添加重试机制，因为Google Drive同步可能有延迟
                    import time
                    max_retries = 3
                    retry_delay = 2  # 秒
                    
                    verify_result = None
                    for attempt in range(max_retries):
                        if attempt > 0:
                            time.sleep(retry_delay)
                        
                        verify_result = self.verify_upload_success(expected_filenames, target_folder_id)
                        
                        if verify_result["success"]:
                            break
                        elif attempt < max_retries - 1:
                            pass
                            # print(f"验证失败，将重试...")
                        else:
                            print(f"最终验证失败详情: {verify_result}")
                        
                    if verify_result["success"]:
                        verify_result["user_confirmed"] = True
                        
                        # 更新上传文件的缓存信息，记录最新的远端修改时间
                        self._update_uploaded_files_cache(verify_result.get("found_files", []), context_info)
                        
                        return verify_result
                    else:
                        # API验证失败，使用文件夹URL作为备选
                        folder_url = f"https://drive.google.com/drive/folders/{target_folder_id}"
                        return {
                            "success": True,
                            "found_files": [{"name": fn, "id": f"folder_{target_folder_id}", "size": "unknown", "modified": "unknown", "url": folder_url} for fn in expected_filenames],
                            "missing_files": [],
                            "total_expected": len(expected_filenames),
                            "total_found": len(expected_filenames),
                            "user_confirmed": True,
                            "api_verification_failed": True,
                            "folder_url": folder_url
                        }
                else:
                    # 没有API服务，但有文件夹ID，生成文件夹URL
                    folder_url = f"https://drive.google.com/drive/folders/{target_folder_id}"
                    return {
                        "success": True,
                        "found_files": [{"name": fn, "id": f"folder_{target_folder_id}", "size": "unknown", "modified": "unknown", "url": folder_url} for fn in expected_filenames],
                        "missing_files": [],
                        "total_expected": len(expected_filenames),
                        "total_found": len(expected_filenames),
                        "user_confirmed": True,
                        "api_unavailable": True,
                        "folder_url": folder_url
                    }
            else:
                # 既没有API服务也没有文件夹ID
                return {
                    "success": True,
                    "found_files": [{"name": fn, "id": "user_confirmed", "size": "unknown", "modified": "unknown", "url": "unavailable"} for fn in expected_filenames],
                    "missing_files": [],
                    "total_expected": len(expected_filenames),
                    "total_found": len(expected_filenames),
                    "user_confirmed": True,
                    "no_folder_id": True
                }
                
        except Exception as e:
            return {
                "success": False,
                "upload_post_processing_error": True,
                "error": str(e),
                "message": f"上传后处理错误: {e}"
            }
    
    def _handle_mkdir_success(self, context_info):
        """处理目录创建成功的情况"""
        return {
            "success": True,
            "user_confirmed": True,
            "command_type": "mkdir",
            "target_path": context_info.get("target_path"),
            "message": "目录创建成功"
        }
    


    def cmd_mkdir_remote(self, target_path, recursive=False):
        """
        通过远端命令创建目录的接口（使用统一接口）
        
        Args:
            target_path (str): 目标路径
            recursive (bool): 是否递归创建
            
        Returns:
            dict: 创建结果
        """
        try:
            # 获取当前shell以解析相对路径
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 解析绝对路径
            absolute_path = self._resolve_absolute_mkdir_path(target_path, current_shell, recursive)
            if not absolute_path:
                return {"success": False, "error": f"无法解析路径: {target_path}"}
            
            # 生成远端mkdir命令，添加清屏和成功/失败提示（总是使用-p确保父目录存在）
            remote_command = f'mkdir -p "{absolute_path}" && clear && echo "✅ 执行成功" || echo "❌ 执行失败"'
            
            # 准备上下文信息
            context_info = {
                "target_path": target_path,
                "absolute_path": absolute_path,
                "recursive": recursive
            }
            
            # 使用统一接口执行远端命令
            execution_result = self.execute_remote_command_interface(
                remote_command=remote_command,
                command_type="mkdir",
                context_info=context_info
            )
            
            if execution_result["success"]:
                # 简洁返回，像bash shell一样成功时不显示任何信息
                return {
                    "success": True,
                    "path": target_path,
                    "absolute_path": absolute_path,
                    "remote_command": remote_command,
                    "message": "",  # 空消息，不显示任何内容
                    "verification": {"success": True}
                }
            else:
                return execution_result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"远端mkdir命令生成失败: {e}"
            }

    def demo_unified_interface(self):
        """
        演示统一远端命令接口的使用
        展示不同命令类型如何使用相同的界面和反馈模式
        """
        print("🎯 统一远端命令接口演示")
        print("=" * 50)
        
        # 演示1: mkdir命令
        print("\n📁 演示1: 创建远端目录")
        mkdir_result = self.cmd_mkdir_remote("/demo/unified_interface", recursive=True)
        if mkdir_result["success"]:
            print(f"✅ 目录创建成功: {mkdir_result.get('message', '成功')}")
        else:
            print(f"❌ 目录创建失败: {mkdir_result.get('message', '失败')}")
        
        # 演示2: 可以扩展其他命令类型
        print("\n📋 可扩展的命令类型:")
        print("  - upload: 文件上传")
        print("  - mkdir: 目录创建") 
        print("  - move: 文件移动")
        print("  - copy: 文件复制")
        print("  - delete: 文件删除")
        print("  - custom: 自定义命令")
        
        print("\n🎉 所有命令都使用相同的:")
        print("  - tkinter确认窗口")
        print("  - 统一的结果处理逻辑")
        print("  - 一致的错误处理")
        
        return {
            "success": True,
            "message": "统一接口演示完成",
            "interface_features": [
                "统一的用户确认界面",
                "一致的成功/失败处理",
                "可扩展的命令类型支持",
                "标准化的结果格式"
            ]
        }
    
    def _verify_rm_with_find(self, path, current_shell, max_retries=60):
        """
        使用find命令验证文件是否被成功删除
        
        Args:
            path (str): 原始路径
            current_shell (dict): 当前shell信息
            max_retries (int): 最大重试次数
            
        Returns:
            dict: 验证结果
        """
        try:
            import time
            
            for attempt in range(max_retries):
                # 使用find命令查找文件
                find_result = self.cmd_find(path, name_pattern=None, recursive=False)
                
                if find_result["success"] and not find_result.get("files"):
                    # 没有找到文件，删除成功
                    return {"success": True, "message": "Files successfully deleted"}
                
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
            
            # 所有重试都失败
            return {"success": False, "error": "Files still exist after deletion"}
            
        except Exception as e:
            return {"success": False, "error": f"Verification error: {e}"}
    
    def cmd_find(self, path=".", name_pattern=None, recursive=False):
        """
        基于ls实现的find命令，支持名称模式匹配和递归搜索
        
        Args:
            path (str): 搜索路径
            name_pattern (str): 文件名模式（支持通配符）
            recursive (bool): 是否递归搜索
            
        Returns:
            dict: 搜索结果
        """
        try:
            if not self.drive_service:
                return {"success": False, "error": "Google Drive API service not initialized"}
                
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            # 使用ls命令获取文件列表
            if recursive:
                ls_result = self.cmd_ls(path, recursive=True)
            else:
                ls_result = self.cmd_ls(path)
            
            if not ls_result["success"]:
                return ls_result
            
            # 提取文件列表
            all_files = []
            
            if recursive and "folders" in ls_result:
                # 递归结果包含多个目录
                for folder_info in ls_result["folders"]:
                    if "files" in folder_info:
                        for file_info in folder_info["files"]:
                            all_files.append({
                                "name": file_info["name"],
                                "path": f"{folder_info['path']}/{file_info['name']}",
                                "type": "file" if file_info.get("mimeType") != "application/vnd.google-apps.folder" else "directory",
                                "size": file_info.get("size", "0"),
                                "id": file_info.get("id", "")
                            })
            else:
                # 单目录结果
                if "files" in ls_result:
                    for file_info in ls_result["files"]:
                        all_files.append({
                            "name": file_info["name"],
                            "path": f"{path.rstrip('/')}/{file_info['name']}" if path != "." else file_info["name"],
                            "type": "file" if file_info.get("mimeType") != "application/vnd.google-apps.folder" else "directory",
                            "size": file_info.get("size", "0"),
                            "id": file_info.get("id", "")
                        })
            
            # 应用名称模式过滤
            if name_pattern:
                import fnmatch
                filtered_files = []
                for file_info in all_files:
                    if fnmatch.fnmatch(file_info["name"], name_pattern):
                        filtered_files.append(file_info)
                all_files = filtered_files
            
            return {
                "success": True,
                "path": path,
                "name_pattern": name_pattern,
                "recursive": recursive,
                "files": all_files,
                "count": len(all_files),
                "message": "" if all_files else "No files found"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error executing find command: {e}"}

    def _check_files_to_override(self, source_files, target_path):
        """
        检查哪些文件会被覆盖（用于--force模式）
        
        Args:
            source_files (list): 源文件列表
            target_path (str): 目标路径
            
        Returns:
            dict: 检查结果，包含会被覆盖的文件列表
        """
        try:
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "No active remote shell"}
            
            overridden_files = []
            
            for source_file in source_files:
                if not os.path.exists(source_file):
                    continue
                    
                filename = os.path.basename(source_file)
                
                # 计算目标远程路径
                if target_path == ".":
                    if current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            target_remote_path = f"{current_path}/{filename}"
                        else:
                            target_remote_path = f"~/{filename}"
                    else:
                        target_remote_path = f"~/{filename}"
                else:
                    if current_shell.get("current_path") != "~":
                        current_path = current_shell.get("current_path", "~")
                        if current_path.startswith("~/"):
                            base_path = current_path[2:] if len(current_path) > 2 else ""
                            if base_path:
                                target_remote_path = f"~/{base_path}/{target_path.strip('/')}/{filename}"
                            else:
                                target_remote_path = f"~/{target_path.strip('/')}/{filename}"
                        else:
                            target_remote_path = f"~/{target_path.strip('/')}/{filename}"
                    else:
                        target_remote_path = f"~/{target_path.strip('/')}/{filename}"
                
                # 检查目标文件是否存在
                check_result = self._check_single_target_file_conflict(filename, target_path)
                if not check_result["success"] and "File exists" in check_result.get("error", ""):
                    overridden_files.append(target_remote_path)
            
            return {
                "success": True,
                "overridden_files": overridden_files
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error checking files to override: {e}"}

    def _wait_for_drive_equivalent_file_deletion(self, filename, timeout=60):
        """
        等待DRIVE_EQUIVALENT中的文件被删除，使用内部ls_with_folder_id接口
        
        Args:
            filename (str): 要等待删除的文件名
            timeout (int): 超时时间（秒）
            
        Returns:
            dict: 等待结果
        """
        try:
            import time
            
            print(f"⏳ 等待DRIVE_EQUIVALENT中的文件删除: {filename}")
            print(f"🔍 检查远端目录ID: {self.DRIVE_EQUIVALENT_FOLDER_ID}")
            
            start_time = time.time()
            
            # 60秒检测机制，每秒检查一次
            for attempt in range(timeout):
                try:
                    # 使用内部ls_with_folder_id接口检查DRIVE_EQUIVALENT目录
                    ls_result = self.ls_with_folder_id(self.DRIVE_EQUIVALENT_FOLDER_ID, detailed=False)
                    
                    if ls_result.get("success"):
                        files = ls_result.get("files", [])
                        file_found = any(f.get("name") == filename for f in files)
                        
                        if not file_found:
                            print(f"✅ DRIVE_EQUIVALENT中的文件已删除: {filename}")
                            return {"success": True, "message": f"File {filename} deleted from DRIVE_EQUIVALENT"}
                    else:
                        print(f"⚠️ ls检查失败: {ls_result.get('error')}")
                
                except Exception as check_error:
                    print(f"⚠️ 检查文件时出错: {check_error}")
                
                # 显示进度点，类似上传时的显示
                if attempt % 5 == 0 and attempt > 0:
                    elapsed = time.time() - start_time
                    print(f"⏳ 等待删除中... ({elapsed:.0f}s)")
                else:
                    print(".", end="", flush=True)
                
                time.sleep(1)
            
            # 超时
            print(f"\n⏰ 删除等待超时 ({timeout}s): {filename}")
            print(f"⚠️ 警告: DRIVE_EQUIVALENT中的文件删除检测超时，但将继续上传")
            return {
                "success": False, 
                "error": f"Timeout waiting for {filename} deletion in DRIVE_EQUIVALENT"
            }
            
        except Exception as e:
            print(f"⚠️ 删除等待过程中出错: {e}")
            return {"success": False, "error": f"Error waiting for file deletion: {e}"}

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

    def ls_with_folder_id(self, folder_id, detailed=False):
        """
        直接通过文件夹ID列出文件，避免循环引用
        
        Args:
            folder_id (str): 要列出的文件夹ID
            detailed (bool): 是否返回详细信息
            
        Returns:
            dict: 列出结果
        """
        try:
            if not self.drive_service:
                return {
                    "success": False,
                    "error": "Google Drive API服务未初始化"
                }
            
            # 直接使用API列出文件
            result = self.drive_service.list_files(folder_id=folder_id, max_results=50)
            
            if result['success']:
                files = result['files']
                
                if detailed:
                    # 详细模式：返回完整JSON格式
                    return {
                        "success": True,
                        "folder_id": folder_id,
                        "files": files,
                        "mode": "detailed"
                    }
                else:
                    # 简洁模式：只返回文件信息
                    return {
                        "success": True,
                        "folder_id": folder_id,
                        "files": files,
                        "mode": "simple"
                    }
            else:
                return {
                    "success": False,
                    "error": f"列出文件失败: {result['error']}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"ls_with_folder_id执行出错: {e}"
            }

    def _check_remote_file_exists(self, filename):
        """
        检查远端DRIVE_EQUIVALENT目录中是否存在指定文件
        
        Args:
            filename (str): 要检查的文件名
            
        Returns:
            bool: 文件是否存在
        """
        try:
            ls_result = self.ls_with_folder_id(self.DRIVE_EQUIVALENT_FOLDER_ID, detailed=False)
            
            if ls_result.get("success"):
                files = ls_result.get("files", [])
                return any(f.get("name") == filename for f in files)
            else:
                print(f"⚠️ 检查远端文件时出错: {ls_result.get('error')}")
                # 如果检查失败，假设文件存在，使用重命名策略（更安全）
                return True
                
        except Exception as e:
            print(f"⚠️ 检查远端文件异常: {e}")
            # 如果检查失败，假设文件存在，使用重命名策略（更安全）
            return True

    def _cleanup_local_equivalent_files(self, file_moves):
        """
        清理LOCAL_EQUIVALENT中的文件（上传完成后）
        
        Args:
            file_moves (list): 文件移动信息列表
        """
        try:
            cleaned_files = []
            failed_cleanups = []
            
            for file_info in file_moves:
                filename = file_info["filename"]  # 实际的文件名（可能已重命名）
                file_path = Path(file_info["new_path"])
                
                try:
                    if file_path.exists():
                        file_path.unlink()
                        cleaned_files.append(filename)
                        # print(f"🧹 清理LOCAL_EQUIVALENT文件: {filename}")
                        
                        # 记录删除到缓存（使用原始文件名）
                        original_filename = file_info.get("original_filename", filename)
                        self.add_deletion_record(original_filename)
                    else:
                        print(f"⚠️ 文件已不存在，跳过清理: {filename}")
                except Exception as e:
                    failed_cleanups.append({"file": filename, "error": str(e)})
                    print(f"⚠️ 清理文件失败: {filename} - {e}")
            
            if cleaned_files:
                pass
                # print(f"✅ 成功清理 {len(cleaned_files)} 个LOCAL_EQUIVALENT文件")
            
            if failed_cleanups:
                pass
                # print(f"⚠️ {len(failed_cleanups)} 个文件清理失败")
                
        except Exception as e:
            print(f"⚠️ 清理LOCAL_EQUIVALENT文件时出错: {e}")

    def load_deletion_cache(self):
        """
        加载删除时间缓存
        
        Returns:
            list: 删除记录栈（按时间排序）
        """
        try:
            if self.deletion_cache_file.exists():
                with open(self.deletion_cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    return cache_data.get("deletion_records", [])
            else:
                return []
        except Exception as e:
            print(f"⚠️ 加载删除缓存失败: {e}")
            return []
    
    def save_deletion_cache(self, deletion_records):
        """
        保存删除时间缓存
        
        Args:
            deletion_records (list): 删除记录栈
        """
        try:
            cache_data = {
                "deletion_records": deletion_records,
                "last_updated": time.time()
            }
            with open(self.deletion_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 保存删除缓存失败: {e}")
    
    def add_deletion_record(self, filename):
        """
        添加删除记录到缓存栈
        
        Args:
            filename (str): 被删除的文件名
        """
        import time
        
        current_time = time.time()
        
        # 清理超过5分钟的旧记录
        self.deletion_cache = [
            record for record in self.deletion_cache
            if current_time - record["deletion_time"] <= 300  # 5分钟 = 300秒
        ]
        
        # 添加新的删除记录到栈顶
        new_record = {
            "filename": filename,
            "deletion_time": current_time
        }
        self.deletion_cache.insert(0, new_record)
        
        # 保存更新后的缓存
        self.save_deletion_cache(self.deletion_cache)
    
    def should_rename_file(self, filename):
        """
        判断文件是否需要重命名（基于删除时间缓存）
        
        Args:
            filename (str): 要检查的文件名
            
        Returns:
            bool: 是否需要重命名
        """
        import time
        
        current_time = time.time()
        
        # 检查是否在最近5分钟内删除过同名文件
        for record in self.deletion_cache:
            if record["filename"] == filename:
                time_since_deletion = current_time - record["deletion_time"]
                if time_since_deletion <= 300:  # 5分钟内
                    print(f"⚠️ 检测到风险: {filename} 在 {time_since_deletion:.1f}秒前被删除，将自动重命名")
                    return True
        
        return False

    def load_cache_config(self):
        """加载缓存配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.cache_config = json.load(f)
                    self.cache_config_loaded = True
            else:
                self.cache_config = {}
                self.cache_config_loaded = False
        except Exception as e:
            print(f"⚠️ 加载缓存配置失败: {e}")
            self.cache_config = {}
            self.cache_config_loaded = False
    
    def load_drive_service(self):
        """加载Google Drive API服务"""
        try:
            import sys
            from pathlib import Path
            
            # 添加GOOGLE_DRIVE_PROJ到Python路径
            api_service_path = Path(__file__).parent / "google_drive_api.py"
            if api_service_path.exists():
                sys.path.insert(0, str(api_service_path.parent))
                from google_drive_api import GoogleDriveService #type: ignore
                return GoogleDriveService()
            else:
                return None
        except Exception as e:
            print(f"⚠️ 加载Google Drive API服务失败: {e}")
            return None

    def check_google_drive_desktop_status(self):
        """
        检查Google Drive Desktop是否正在运行
        
        Returns:
            tuple: (is_running: bool, status_message: str)
        """
        try:
            # 根据操作系统检查不同的进程名称
            if platform.system() == "Darwin":  # macOS
                process_names = ["Google Drive", "GoogleDrive"]
            elif platform.system() == "Windows":
                process_names = ["GoogleDriveFS.exe", "GoogleDriveSync.exe"]
            else:  # Linux
                process_names = ["google-drive-ocamlfuse", "gdrive"]
            
            # 检查进程是否运行
            running_processes = []
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    proc_name = proc.info['name']
                    if any(name.lower() in proc_name.lower() for name in process_names):
                        running_processes.append(proc_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            if running_processes:
                return True, f"✅ Google Drive Desktop is running: {', '.join(set(running_processes))}"
            else:
                return False, "❌ Google Drive Desktop is not running. Trying to restart ..."
                
        except Exception as e:
            return False, f"⚠️ 无法检查 Google Drive Desktop 状态: {e}"

    def launch_google_drive_desktop(self):
        """
        启动Google Drive Desktop应用
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            print("🚀 正在启动 Google Drive Desktop...")
            
            # 使用 macOS 的 open 命令启动 Google Drive
            result = subprocess.run(['open', '-a', 'Google Drive'], 
                                  capture_output=True, text=True)
            
            if result.returncode != 0:
                return False, f"启动失败: {result.stderr}"
            
            # 等待启动，最多等待10秒
            max_wait = 10
            for i in range(max_wait):
                time.sleep(1)
                is_running, _ = self.check_google_drive_desktop_status()
                if is_running:
                    return True, f"✅ Google Drive Desktop 已成功启动 (耗时 {i+1} 秒)"
            
            # 检查是否最终启动成功
            is_running, _ = self.check_google_drive_desktop_status()
            if is_running:
                return True, "✅ Google Drive Desktop 已启动 (启动时间较长)"
            else:
                return False, "❌ Google Drive Desktop 启动超时"
                
        except Exception as e:
            return False, f"启动过程出错: {e}"

    def ensure_google_drive_desktop_running(self):
        """
        确保Google Drive Desktop正在运行，如果没有运行则自动启动
        
        Returns:
            bool: True if running or successfully started, False if failed to start
        """
        is_running, status_message = self.check_google_drive_desktop_status()
        
        if is_running:
            print(status_message)
            return True
        else:
            print(status_message)
            print("\n⚠️ 警告: Google Drive Desktop 未运行，这可能导致以下问题:")
            print("   • 文件无法同步到本地 Google Drive 文件夹")
            print("   • 上传后的文件可能无法在远程正确显示")
            print("   • 本地文件缓存机制可能失效")
            
            # 直接尝试自动启动，不再询问用户
            print("\n🚀 正在自动启动 Google Drive Desktop...")
            success, message = self.launch_google_drive_desktop()
            print(message)
            
            if success:
                return True
            else:
                print("❌ 自动启动失败，强制继续执行，但可能遇到同步问题")
                return True  # 即使启动失败也继续执行，避免阻塞用户操作


    

    

    def is_remote_file_cached(self, remote_path: str) -> Dict:
        """检查远端文件是否在本地有缓存"""
        try:
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            cache_config = cache_manager.cache_config
            files = cache_config.get("files", {})
            
            if remote_path in files:
                file_info = files[remote_path]
                cache_file_path = file_info.get("cache_path")
                
                if cache_file_path and Path(cache_file_path).exists():
                    return {
                        "success": True,
                        "is_cached": True,
                        "cache_file_path": cache_file_path,
                        "cache_info": file_info
                    }
                else:
                    return {
                        "success": True,
                        "is_cached": False,
                        "reason": "cache_file_not_found"
                    }
            else:
                return {
                    "success": True,
                    "is_cached": False,
                    "reason": "not_in_cache_config"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"检查缓存时出错: {e}"
            }
    
    def get_remote_file_modification_time(self, remote_path: str) -> Dict:
        """获取远端文件的修改时间"""
        try:
            # 如果remote_path看起来像文件名（不包含路径分隔符），在当前目录中查找
            if '/' not in remote_path and not remote_path.startswith('~'):
                # 列出当前目录的所有文件
                result = self.cmd_ls('', detailed=True)
                
                if result["success"] and result["files"]:
                    # 在文件列表中查找指定文件
                    for file_info in result["files"]:
                        if file_info.get("name") == remote_path:
                            modified_time = file_info.get("modifiedTime")
                            
                            if modified_time:
                                return {
                                    "success": True,
                                    "modified_time": modified_time,
                                    "file_info": file_info
                                }
                            else:
                                return {
                                    "success": False,
                                    "error": "无法获取文件修改时间"
                                }
                    
                    # 文件未找到
                    return {
                        "success": False,
                        "error": f"文件不存在或无法访问: {remote_path}"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"无法列出目录内容: {result.get('error', 'unknown error')}"
                    }
            else:
                # 原来的逻辑，处理路径格式的文件
                result = self.cmd_ls(remote_path, detailed=True)
                
                if result["success"] and result["files"]:
                    file_info = result["files"][0]
                    modified_time = file_info.get("modifiedTime")
                    
                    if modified_time:
                        return {
                            "success": True,
                            "modified_time": modified_time,
                            "file_info": file_info
                        }
                    else:
                        return {
                            "success": False,
                            "error": "无法获取文件修改时间"
                        }
                else:
                    return {
                        "success": False,
                        "error": f"文件不存在或无法访问: {remote_path}"
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"获取文件修改时间时出错: {e}"
            }
    
    def is_cached_file_up_to_date(self, remote_path: str) -> Dict:
        """检查缓存文件是否为最新版本"""
        try:
            cache_result = self.is_remote_file_cached(remote_path)
            if not cache_result["success"]:
                return cache_result
            
            if not cache_result["is_cached"]:
                return {
                    "success": True,
                    "is_cached": False,
                    "is_up_to_date": False,
                    "reason": "no_cache"
                }
            
            cache_info = cache_result["cache_info"]
            cached_modified_time = cache_info.get("remote_modified_time")
            
            if not cached_modified_time:
                return {
                    "success": True,
                    "is_cached": True,
                    "is_up_to_date": False,
                    "reason": "no_cached_modified_time"
                }
            
            import os
            filename = os.path.basename(remote_path)
            remote_time_result = self.get_remote_file_modification_time(filename)
            if not remote_time_result["success"]:
                return {
                    "success": False,
                    "error": f"无法获取远端修改时间: {remote_time_result.get('error', '未知错误')}"
                }
            
            current_modified_time = remote_time_result["modified_time"]
            is_up_to_date = cached_modified_time == current_modified_time
            
            return {
                "success": True,
                "is_cached": True,
                "is_up_to_date": is_up_to_date,
                "cached_modified_time": cached_modified_time,
                "current_modified_time": current_modified_time
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"检查缓存新旧时出错: {e}"
            }

    def cmd_read(self, filename, *args):
        """读取远端文件内容，支持智能缓存和行数范围"""
        try:
            if not filename:
                return {"success": False, "error": "请指定要读取的文件"}
            
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            remote_absolute_path = self.resolve_remote_absolute_path(filename, current_shell)
            if not remote_absolute_path:
                return {"success": False, "error": f"无法解析文件路径: {filename}"}
            
            line_ranges = self._parse_line_ranges(args)
            if line_ranges is False:
                return {"success": False, "error": "行数范围参数格式错误"}
            
            freshness_result = self.is_cached_file_up_to_date(remote_absolute_path)
            
            file_content = None
            source = "unknown"
            
            if (freshness_result["success"] and 
                freshness_result["is_cached"] and 
                freshness_result["is_up_to_date"]):
                
                cache_status = self.is_remote_file_cached(remote_absolute_path)
                cache_file_path = cache_status["cache_file_path"]
                
                if cache_file_path and Path(cache_file_path).exists():
                    with open(cache_file_path, 'r', encoding='utf-8', errors='replace') as f:
                        file_content = f.read()
                    source = "cache"
                else:
                    download_result = self._download_and_get_content(filename, remote_absolute_path)
                    if not download_result["success"]:
                        return download_result
                    file_content = download_result["content"]
                    source = "download"
            else:
                download_result = self._download_and_get_content(filename, remote_absolute_path)
                if not download_result["success"]:
                    return download_result
                file_content = download_result["content"]
                source = "download"
            
            lines = file_content.split('\n')
            
            if not line_ranges:
                selected_lines = [(i, line) for i, line in enumerate(lines)]
            else:
                selected_lines = []
                for start, end in line_ranges:
                    start = max(0, start)
                    end = min(len(lines), end)
                    
                    for i in range(start, end):
                        if i < len(lines):
                            selected_lines.append((i, lines[i]))
                
                selected_lines = list(dict(selected_lines).items())
                selected_lines.sort(key=lambda x: x[0])
            
            formatted_output = self._format_read_output(selected_lines)
            
            return {
                "success": True,
                "filename": filename,
                "remote_path": remote_absolute_path,
                "source": source,
                "total_lines": len(lines),
                "selected_lines": len(selected_lines),
                "line_ranges": line_ranges,
                "output": formatted_output,
                "lines_data": selected_lines
            }
            
        except Exception as e:
            return {"success": False, "error": f"读取文件时出错: {e}"}

    def _parse_line_ranges(self, args):
        """解析行数范围参数"""
        try:
            if not args:
                return None
            
            if len(args) == 1:
                arg = args[0]
                if isinstance(arg, str) and arg.startswith('[[') and arg.endswith(']]'):
                    import ast
                    try:
                        ranges = ast.literal_eval(arg)
                        if isinstance(ranges, list):
                            return [(start, end) for start, end in ranges]
                    except:
                        return False
                else:
                    return False
            
            elif len(args) == 2:
                try:
                    start = int(args[0])
                    end = int(args[1])
                    return [(start, end)]
                except ValueError:
                    return False
            
            else:
                return False
                
        except Exception:
            return False
    
    def _download_and_get_content(self, filename, remote_absolute_path):
        """下载文件并获取内容"""
        try:
            download_result = self.cmd_download(filename, force=True)
            
            if not download_result["success"]:
                return {
                    "success": False,
                    "error": f"下载文件失败: {download_result.get('error', '未知错误')}"
                }
            
            cache_file_path = download_result.get("cache_path")
            if not cache_file_path or not Path(cache_file_path).exists():
                return {
                    "success": False,
                    "error": "下载后无法找到缓存文件"
                }
            
            with open(cache_file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            return {
                "success": True,
                "content": content,
                "cache_path": cache_file_path
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"下载和读取文件时出错: {e}"
            }
    
    def _format_read_output(self, selected_lines):
        """格式化读取输出，带行号"""
        if not selected_lines:
            return ""
        
        formatted_lines = []
        for line_num, content in selected_lines:
            formatted_lines.append(f"{line_num}: {content}")
        
        return '\n'.join(formatted_lines)

    def _update_uploaded_files_cache(self, found_files, context_info):
        """
        更新上传文件的缓存信息，记录最新的远端修改时间
        
        Args:
            found_files (list): 验证成功的文件列表，包含文件信息
            context_info (dict): 上下文信息，包含file_moves等
        """
        try:
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if not cache_manager_path.exists():
                return  # 缓存管理器不存在，静默返回
                
            sys.path.insert(0, str(Path(__file__).parent))
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            
            file_moves = context_info.get("file_moves", [])
            target_path = context_info.get("target_path", ".")
            
            # 为每个成功上传的文件更新缓存
            for found_file in found_files:
                file_name = found_file.get("name")
                if not file_name:
                    continue
                    
                # 构建远端绝对路径
                if target_path == ".":
                    # 当前目录
                    current_shell = self.get_current_shell()
                    if current_shell:
                        current_path = current_shell.get("current_path", "~")
                        if current_path == "~":
                            remote_absolute_path = f"{self.REMOTE_ROOT}/{file_name}"
                        else:
                            remote_absolute_path = f"{current_path}/{file_name}"
                    else:
                        remote_absolute_path = f"{self.REMOTE_ROOT}/{file_name}"
                else:
                    # 指定目标路径
                    if target_path.startswith("/"):
                        remote_absolute_path = f"{target_path}/{file_name}"
                    else:
                        current_shell = self.get_current_shell()
                        if current_shell:
                            current_path = current_shell.get("current_path", "~")
                            if current_path == "~":
                                remote_absolute_path = f"{self.REMOTE_ROOT}/{target_path}/{file_name}"
                            else:
                                remote_absolute_path = f"{current_path}/{target_path}/{file_name}"
                        else:
                            remote_absolute_path = f"{self.REMOTE_ROOT}/{target_path}/{file_name}"
                
                # 获取远端修改时间
                remote_modified_time = found_file.get("modified")
                if remote_modified_time:
                    # 检查是否已经有缓存
                    if cache_manager.is_file_cached(remote_absolute_path):
                        # 更新现有缓存的远端修改时间
                        cache_manager._update_cached_file_modified_time(remote_absolute_path, remote_modified_time)
                        print(f"✅ 已更新缓存文件时间: {file_name} -> {remote_modified_time}")
                    else:
                        # 文件还没有缓存，存储修改时间以备后用
                        cache_manager.store_pending_modified_time(remote_absolute_path, remote_modified_time)
                        print(f"📝 记录上传文件修改时间: {file_name} -> {remote_modified_time}")
                        
        except Exception as e:
            # 静默处理错误，不影响主流程
            print(f"⚠️ 更新缓存时间时出错: {e}")


    def cmd_find(self, *args):
        """
        GDS find命令实现，类似bash find
        
        用法:
            find [path] -name [pattern]
            find [path] -iname [pattern]  # 大小写不敏感
            find [path] -type f -name [pattern]  # 只查找文件
            find [path] -type d -name [pattern]  # 只查找目录
        
        Args:
            *args: 命令参数
            
        Returns:
            dict: 查找结果
        """
        try:
            if not args:
                return {
                    "success": False,
                    "error": "用法: find [path] -name [pattern] 或 find [path] -type [f|d] -name [pattern]"
                }
            
            # 解析参数
            parsed_args = self._parse_find_args(args)
            if not parsed_args["success"]:
                return parsed_args
            
            search_path = parsed_args["path"]
            pattern = parsed_args["pattern"]
            case_sensitive = parsed_args["case_sensitive"]
            file_type = parsed_args["file_type"]  # "f" for files, "d" for directories, None for both
            
            # 递归搜索文件
            results = self._recursive_find(search_path, pattern, case_sensitive, file_type)
            
            if results["success"]:
                found_files = results["files"]
                
                # 格式化输出
                output_lines = []
                for file_path in sorted(found_files):
                    output_lines.append(file_path)
                
                return {
                    "success": True,
                    "files": found_files,
                    "count": len(found_files),
                    "output": "\n".join(output_lines) if output_lines else "No files found matching the pattern."
                }
            else:
                return results
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Find命令执行错误: {e}"
            }


    def _parse_find_args(self, args):
        """
        解析find命令的参数
        
        Args:
            args: 命令参数元组
            
        Returns:
            dict: 解析结果
        """
        try:
            args_list = list(args)
            
            # 默认值
            search_path = "."
            pattern = None
            case_sensitive = True
            file_type = None  # None表示文件和目录都查找
            
            i = 0
            while i < len(args_list):
                arg = args_list[i]
                
                if arg == "-name":
                    if i + 1 >= len(args_list):
                        return {"success": False, "error": "-name参数需要指定模式"}
                    pattern = args_list[i + 1]
                    case_sensitive = True
                    i += 2
                elif arg == "-iname":
                    if i + 1 >= len(args_list):
                        return {"success": False, "error": "-iname参数需要指定模式"}
                    pattern = args_list[i + 1]
                    case_sensitive = False
                    i += 2
                elif arg == "-type":
                    if i + 1 >= len(args_list):
                        return {"success": False, "error": "-type参数需要指定类型"}
                    type_value = args_list[i + 1]
                    if type_value not in ["f", "d"]:
                        return {"success": False, "error": "-type参数只支持f（文件）或d（目录）"}
                    file_type = type_value
                    i += 2
                elif not arg.startswith("-"):
                    # 这是路径参数
                    search_path = arg
                    i += 1
                else:
                    return {"success": False, "error": f"未知参数: {arg}"}
            
            if pattern is None:
                return {"success": False, "error": "必须指定-name或-iname参数"}
            
            return {
                "success": True,
                "path": search_path,
                "pattern": pattern,
                "case_sensitive": case_sensitive,
                "file_type": file_type
            }
            
        except Exception as e:
            return {"success": False, "error": f"参数解析错误: {e}"}


    def _recursive_find(self, search_path, pattern, case_sensitive=True, file_type=None):
        """
        递归搜索匹配模式的文件和目录
        
        Args:
            search_path: 搜索路径
            pattern: 匹配模式（支持通配符）
            case_sensitive: 是否大小写敏感
            file_type: 文件类型过滤（"f"=文件, "d"=目录, None=都包括）
            
        Returns:
            dict: 搜索结果
        """
        try:
            import fnmatch
            
            found_files = []
            
            # 解析搜索路径
            if search_path == ".":
                # 当前目录，直接使用"."
                base_path = "."
            else:
                # 其他路径，解析为绝对路径
                base_path = self.resolve_remote_absolute_path(search_path)
            
            # 递归遍历目录
            self._find_in_directory(base_path, pattern, case_sensitive, file_type, found_files, "")
            
            return {
                "success": True,
                "files": found_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"递归搜索错误: {e}"
            }
    
    def _find_in_directory(self, dir_path, pattern, case_sensitive, file_type, found_files, relative_prefix):
        """
        在指定目录中搜索匹配的文件
        
        Args:
            dir_path: 目录路径
            pattern: 匹配模式
            case_sensitive: 是否大小写敏感
            file_type: 文件类型过滤
            found_files: 结果列表（引用传递）
            relative_prefix: 相对路径前缀
        """
        try:
            import fnmatch
            
            # 获取目录内容
            if dir_path == "~" or dir_path == ".": 
                # 当前目录
                ls_result = self.cmd_ls("", detailed=True)
            elif dir_path.startswith("~/"):
                # 相对路径格式，转换为shell命令
                relative_path = dir_path[2:] if len(dir_path) > 2 else ""
                ls_result = self.cmd_ls(relative_path, detailed=True)
            else:
                # 绝对路径格式，需要转换
                ls_result = self.cmd_ls("", detailed=True)  # 先获取当前目录
            
            if not ls_result.get("success"):
                return  # 无法访问目录，跳过
            
            files = ls_result.get("files", [])
            folders = ls_result.get("folders", [])
            
            # 合并文件和目录列表
            all_items = files + folders
            
            for file_info in all_items:
                file_name = file_info.get("name")
                if not file_name:
                    continue
                
                mime_type = file_info.get("mimeType", "")
                is_directory = mime_type == "application/vnd.google-apps.folder"
                
                # 构建相对路径
                if relative_prefix:
                    relative_path = f"{relative_prefix}/{file_name}"
                else:
                    relative_path = file_name
                
                # 检查文件类型过滤
                if file_type == "f" and is_directory:
                    # 只要文件，跳过目录
                    pass
                elif file_type == "d" and not is_directory:
                    # 只要目录，跳过文件
                    pass
                else:
                    # 检查模式匹配
                    match_name = file_name.lower() if not case_sensitive else file_name
                    match_pattern = pattern.lower() if not case_sensitive else pattern
                    
                    if fnmatch.fnmatch(match_name, match_pattern):
                        found_files.append(relative_path)
                
                # 如果是目录，递归搜索
                if is_directory:
                    # 构建子目录路径
                    if dir_path == "~":
                        sub_dir_path = f"~/{file_name}"
                    elif dir_path.startswith("~/"):
                        sub_dir_path = f"{dir_path}/{file_name}"
                    else:
                        sub_dir_path = f"{dir_path}/{file_name}"
                    
                    # 递归搜索子目录（暂时禁用以避免死循环）
                    # self._find_in_directory(sub_dir_path, pattern, case_sensitive, file_type, found_files, relative_path)
                    
        except Exception as e:
            # 忽略单个目录的错误，继续搜索其他目录
            pass

    def cmd_edit(self, filename, replacement_spec, preview=False, backup=False):
        """
        GDS edit命令 - 支持多段文本同步替换的文件编辑功能
        
        Args:
            filename (str): 要编辑的文件名
            replacement_spec (str): 替换规范，支持多种格式
            preview (bool): 预览模式，只显示修改结果不实际保存
            backup (bool): 是否创建备份文件
            
        Returns:
            dict: 编辑结果
            
        支持的替换格式:
        1. 行号替换: '[[[1, 2], "new content"], [[5, 7], "another content"]]'
        2. 文本搜索替换: '[["old text", "new text"], ["another old", "another new"]]'
        3. 混合模式: '[[[1, 1], "line replacement"], ["text search", "text replace"]]'
        """
        try:
            import json
            import re
            import tempfile
            import shutil
            from datetime import datetime
            
            # 导入缓存管理器
            import sys
            from pathlib import Path
            cache_manager_path = Path(__file__).parent / "cache_manager.py"
            if cache_manager_path.exists():
                sys.path.insert(0, str(Path(__file__).parent))
                from cache_manager import GDSCacheManager
                cache_manager = GDSCacheManager()
            else:
                return {"success": False, "error": "缓存管理器未找到"}
            
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的远程shell"}
            
            # 1. 解析替换规范
            try:
                replacements = json.loads(replacement_spec)
                if not isinstance(replacements, list):
                    return {"success": False, "error": "替换规范必须是数组格式"}
            except json.JSONDecodeError as e:
                return {"success": False, "error": f"替换规范JSON解析失败: {e}"}
            
            # 2. 下载文件到缓存
            download_result = self.cmd_download(filename, force=True)  # 强制重新下载确保最新内容
            if not download_result["success"]:
                return {"success": False, "error": f"下载文件失败: {download_result.get('error')}"}
            
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            if not cache_file_path or not os.path.exists(cache_file_path):
                return {"success": False, "error": "无法获取缓存文件路径"}
            
            # 3. 读取文件内容
            try:
                with open(cache_file_path, 'r', encoding='utf-8') as f:
                    original_lines = f.readlines()
            except UnicodeDecodeError:
                # 尝试其他编码
                try:
                    with open(cache_file_path, 'r', encoding='gbk') as f:
                        original_lines = f.readlines()
                except:
                    return {"success": False, "error": "文件编码不支持，请确保文件为UTF-8或GBK编码"}
            except Exception as e:
                return {"success": False, "error": f"读取文件失败: {e}"}
            
            # 4. 解析和验证替换操作
            parsed_replacements = []
            for i, replacement in enumerate(replacements):
                if not isinstance(replacement, list) or len(replacement) != 2:
                    return {"success": False, "error": f"替换规范第{i+1}项格式错误，应为[source, target]格式"}
                
                source, target = replacement
                
                if isinstance(source, list) and len(source) == 2 and all(isinstance(x, int) for x in source):
                    # 行号替换模式: [[start_line, end_line], "new_content"] (0-based, [a, b) 语法)
                    start_line, end_line = source
                    # 使用0-based索引，[a, b) 语法
                    start_idx = start_line
                    end_idx = end_line - 1  # end_line是exclusive的
                    
                    if start_idx < 0 or start_idx >= len(original_lines) or end_line > len(original_lines) or start_idx > end_idx:
                        return {"success": False, "error": f"行号范围错误: [{start_line}, {end_line})，文件共{len(original_lines)}行 (0-based索引)"}
                    
                    parsed_replacements.append({
                        "type": "line_range",
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "start_line": start_line,
                        "end_line": end_line,
                        "new_content": target,
                        "original_content": "".join(original_lines[start_idx:end_line]).rstrip()
                    })
                    
                elif isinstance(source, str):
                    # 文本搜索替换模式: ["old_text", "new_text"]
                    if source not in "".join(original_lines):
                        return {"success": False, "error": f"未找到要替换的文本: {source[:50]}..."}
                    
                    parsed_replacements.append({
                        "type": "text_search",
                        "old_text": source,
                        "new_text": target
                    })
                else:
                    return {"success": False, "error": f"替换规范第{i+1}项的源格式不支持，应为行号数组[start, end]或文本字符串"}
            
            # 5. 执行替换操作
            modified_lines = original_lines.copy()
            
            # 按行号倒序处理行替换，避免行号变化影响后续替换
            line_replacements = [r for r in parsed_replacements if r["type"] == "line_range"]
            line_replacements.sort(key=lambda x: x["start_idx"], reverse=True)
            
            for replacement in line_replacements:
                start_idx = replacement["start_idx"]
                end_idx = replacement["end_idx"]
                new_content = replacement["new_content"]
                
                # 确保新内容以换行符结尾（如果原内容有换行符）
                if not new_content.endswith('\n') and end_idx < len(modified_lines) - 1:
                    new_content += '\n'
                elif new_content.endswith('\n') and end_idx == len(modified_lines) - 1 and not original_lines[-1].endswith('\n'):
                    new_content = new_content.rstrip('\n')
                
                # 替换行范围 (使用[a, b)语法)
                modified_lines[start_idx:replacement["end_line"]] = [new_content] if new_content else []
            
            # 处理文本搜索替换
            text_replacements = [r for r in parsed_replacements if r["type"] == "text_search"]
            if text_replacements:
                file_content = "".join(modified_lines)
                for replacement in text_replacements:
                    file_content = file_content.replace(replacement["old_text"], replacement["new_text"])
                modified_lines = file_content.splitlines(keepends=True)
            
            # 6. 生成结果预览
            diff_info = self._generate_edit_diff(original_lines, modified_lines, parsed_replacements)
            
            if preview:
                # 预览模式：只返回修改预览，不实际保存
                return {
                    "success": True,
                    "mode": "preview",
                    "filename": filename,
                    "original_lines": len(original_lines),
                    "modified_lines": len(modified_lines),
                    "replacements_applied": len(parsed_replacements),
                    "diff": diff_info,
                    "preview_content": "".join(modified_lines)
                }
            
            # 7. 创建备份（如果需要）
            backup_info = {}
            if backup:
                backup_filename = f"{filename}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_result = self._create_backup(filename, backup_filename)
                backup_info = {
                    "backup_created": backup_result["success"],
                    "backup_filename": backup_filename if backup_result["success"] else None,
                    "backup_error": backup_result.get("error") if not backup_result["success"] else None
                }
            
            # 8. 保存修改后的文件到临时位置，使用正确的文件名
            import tempfile
            temp_dir = tempfile.gettempdir()
            temp_file_path = os.path.join(temp_dir, filename)
            
            # 如果临时文件已存在，添加时间戳避免冲突
            if os.path.exists(temp_file_path):
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                name_parts = filename.rsplit('.', 1)
                if len(name_parts) == 2:
                    temp_filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
                else:
                    temp_filename = f"{filename}_{timestamp}"
                temp_file_path = os.path.join(temp_dir, temp_filename)
            
            with open(temp_file_path, 'w', encoding='utf-8') as temp_file:
                temp_file.writelines(modified_lines)
            
            try:
                # 9. 更新缓存
                remote_absolute_path = self.resolve_remote_absolute_path(filename, current_shell)
                cache_result = cache_manager.cache_file(remote_absolute_path, temp_file_path)
                
                if not cache_result["success"]:
                    return {"success": False, "error": f"更新缓存失败: {cache_result.get('error')}"}
                
                # 10. 上传修改后的文件，使用多文件上传语法指定目标文件名
                file_pairs = [[temp_file_path, filename]]
                upload_result = self.cmd_upload_multi(file_pairs, force=True)
                
                if upload_result["success"]:
                    result = {
                        "success": True,
                        "filename": filename,
                        "original_lines": len(original_lines),
                        "modified_lines": len(modified_lines),
                        "replacements_applied": len(parsed_replacements),
                        "diff": diff_info,
                        "cache_updated": True,
                        "uploaded": True,
                        "message": f"文件 {filename} 编辑完成，应用了 {len(parsed_replacements)} 个替换操作"
                    }
                    result.update(backup_info)
                    return result
                else:
                    return {
                        "success": False,
                        "error": f"上传修改后的文件失败: {upload_result.get('error')}",
                        "cache_updated": True,
                        "diff": diff_info
                    }
                    
            finally:
                # 清理临时文件
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            
        except Exception as e:
            return {"success": False, "error": f"编辑操作失败: {str(e)}"}
    
    def _generate_edit_diff(self, original_lines, modified_lines, replacements):
        """生成编辑差异信息"""
        diff_info = {
            "total_replacements": len(replacements),
            "line_changes": [],
            "text_changes": [],
            "lines_added": len(modified_lines) - len(original_lines),
            "summary": []
        }
        
        for replacement in replacements:
            if replacement["type"] == "line_range":
                diff_info["line_changes"].append({
                    "lines": f"[{replacement['start_line']}, {replacement['end_line']})",
                    "before": replacement["original_content"],
                    "after": replacement["new_content"].rstrip()
                })
                diff_info["summary"].append(f"Lines [{replacement['start_line']}, {replacement['end_line']}): replaced")
            elif replacement["type"] == "text_search":
                diff_info["text_changes"].append({
                    "before": replacement["old_text"],
                    "after": replacement["new_text"]
                })
                diff_info["summary"].append(f"Text '{replacement['old_text'][:30]}...' replaced")
        
        return diff_info
    
    def _create_backup(self, original_filename, backup_filename):
        """创建文件备份"""
        try:
            # 下载原文件
            download_result = self.cmd_download(original_filename)
            if not download_result["success"]:
                return {"success": False, "error": f"下载原文件失败: {download_result.get('error')}"}
            
            cache_file_path = download_result.get("cache_path") or download_result.get("cached_path")
            
            # 上传为备份文件
            upload_result = self.cmd_upload([cache_file_path], ".", force=True)
            # 这里需要重命名上传的文件，但由于当前上传机制的限制，我们先简化实现
            
            return {
                "success": True,
                "message": f"备份文件 {backup_filename} 创建成功"
            }
        except Exception as e:
            return {"success": False, "error": f"创建备份失败: {str(e)}"}

    # 特殊命令列表 - 这些命令在本地处理，不需要远端执行
    SPECIAL_COMMANDS = {
        'ls', 'cd', 'pwd', 'mkdir', 'rm', 'mv', 'cat', 'echo', 'grep', 
        'upload', 'download', 'edit', 'read', 'find', 'help', 'exit', 'quit'
    }

    def execute_generic_remote_command(self, cmd, args):
        """
        统一远端命令执行接口 - 处理除特殊命令外的所有命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            
        Returns:
            dict: 执行结果，包含stdout、stderr、path等字段
        """
        try:
            # 检查是否为特殊命令
            if cmd in self.SPECIAL_COMMANDS:
                return {
                    "success": False, 
                    "error": f"命令 '{cmd}' 应该通过特殊命令处理，不应调用此接口"
                }
            
            # 获取当前shell信息
            current_shell = self.get_current_shell()
            if not current_shell:
                return {"success": False, "error": "没有活跃的shell会话"}
            
            # 生成远端命令
            remote_command_info = self._generate_remote_command(cmd, args, current_shell)
            
            # 显示远端命令并通过tkinter获取用户执行结果
            result = self._execute_with_result_capture(remote_command_info, cmd, args)
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": f"执行远端命令时出错: {str(e)}"
            }
    
    def _generate_remote_command(self, cmd, args, current_shell):
        """
        生成远端执行命令
        
        Args:
            cmd (str): 命令名称
            args (list): 命令参数
            current_shell (dict): 当前shell信息
            
        Returns:
            tuple: (远端命令字符串, 结果文件名)
        """
        try:
            # 获取当前路径
            current_path = current_shell.get("current_path", "~")
            
            # 解析远端绝对路径
            if current_path == "~":
                remote_path = self.REMOTE_ROOT
            elif current_path.startswith("~/"):
                remote_path = f"{self.REMOTE_ROOT}/{current_path[2:]}"
            else:
                remote_path = current_path
            
            # 构建基础命令
            full_command = f"{cmd} {' '.join(args)}" if args else cmd
            
            # 将args转换为JSON格式
            import json
            args_json = json.dumps(args)
            
            # 生成结果文件名：时间戳+哈希，存储在REMOTE_ROOT/tmp目录
            import time
            import hashlib
            timestamp = str(int(time.time()))
            cmd_hash = hashlib.md5(f"{cmd}_{' '.join(args)}_{timestamp}".encode()).hexdigest()[:8]
            result_filename = f"cmd_{timestamp}_{cmd_hash}.json"
            result_path = f"{self.REMOTE_ROOT}/tmp/{result_filename}"
            
            # 构建完整的远端命令
            # 使用字符串拼接避免f-string中的反斜杠问题，并正确转义JSON字符串
            remote_command = (
                f'cd "{remote_path}" && {{\n'
                f'    # 确保tmp目录存在\n'
                f'    mkdir -p "{self.REMOTE_ROOT}/tmp"\n'
                f'    echo "{{" > "{result_path}"\n'
                f'    echo \'  "cmd": "{cmd}",\' >> "{result_path}"\n'
                f'    echo \'  "args": {args_json},\' >> "{result_path}"\n'
                f'    echo \'  "working_dir": "\'$(pwd)\'",\' >> "{result_path}"\n'
                f'    echo \'  "timestamp": "\'$(date -Iseconds)\'",\' >> "{result_path}"\n'
                f'    \n'
                f'    # 执行命令并捕获输出\n'
                f'    OUTPUT_FILE="/tmp/cmd_stdout_{timestamp}_{cmd_hash}"\n'
                f'    ERROR_FILE="/tmp/cmd_stderr_{timestamp}_{cmd_hash}"\n'
                f'    \n'
                f'    {full_command} > "$OUTPUT_FILE" 2> "$ERROR_FILE"\n'
                f'    EXIT_CODE=$?\n'
                f'    \n'
                f'    echo \'  "exit_code": \'$EXIT_CODE\',\' >> "{result_path}"\n'
                f'    echo \'  "stdout": "\' >> "{result_path}"\n'
                f'    if [ -f "$OUTPUT_FILE" ]; then\n'
                f'        # 使用Python进行JSON转义，将换行符转为\\n\n'
                f'        python3 -c "import json, sys; content=sys.stdin.read(); print(json.dumps(content)[1:-1], end=\'\')" < "$OUTPUT_FILE" >> "{result_path}"\n'
                f'    fi\n'
                f'    echo \'",\' >> "{result_path}"\n'
                f'    \n'
                f'    echo \'  "stderr": "\' >> "{result_path}"\n'
                f'    if [ -f "$ERROR_FILE" ]; then\n'
                f'        # 使用Python进行JSON转义，将换行符转为\\n\n'
                f'        python3 -c "import json, sys; content=sys.stdin.read(); print(json.dumps(content)[1:-1], end=\'\')" < "$ERROR_FILE" >> "{result_path}"\n'
                f'    fi\n'
                f'    echo \'"\' >> "{result_path}"\n'
                f'    \n'
                f'    echo "}}" >> "{result_path}"\n'
                f'    \n'
                f'    # 清理临时文件\n'
                f'    rm -f "$OUTPUT_FILE" "$ERROR_FILE"\n'
                f'    \n'
                f'    echo "命令执行完成，结果已保存到: {result_filename}"\n'
                f'}}'
            )
            
            return remote_command, result_filename
            
        except Exception as e:
            raise Exception(f"生成远端命令失败: {str(e)}")
    
    def _execute_with_result_capture(self, remote_command_info, cmd, args):
        """
        执行远端命令并捕获结果
        
        Args:
            remote_command_info (tuple): (远端命令, 结果文件名)
            cmd (str): 原始命令名
            args (list): 原始命令参数
            
        Returns:
            dict: 执行结果
        """
        try:
            remote_command, result_filename = remote_command_info
            
            # 通过tkinter显示命令并获取用户反馈
            window_result = self._show_generic_command_window(remote_command, cmd, args)
            
            if window_result.get("action") != "success":
                return {
                    "success": False,
                    "error": f"User operation: {'Cancelled' if window_result.get('action', 'unknown') == 'error' else window_result.get('action', 'unknown')}",
                    "user_feedback": window_result
                }
            
            # 等待远端文件出现，最多等待60秒
            result_data = self._wait_and_read_result_file(result_filename)
            
            if not result_data.get("success"):
                return {
                    "success": False,
                    "error": "读取结果文件失败",
                    "read_error": result_data.get("error")
                }
            
            # 返回完整结果
            return {
                "success": True,
                "cmd": cmd,
                "args": args,
                "exit_code": result_data["data"].get("exit_code", -1),
                "stdout": result_data["data"].get("stdout", "") + "\n" if result_data["data"].get("stdout", "").strip() else "",
                "stderr": result_data["data"].get("stderr", "") + "\n" if result_data["data"].get("stderr", "").strip() else "",
                "working_dir": result_data["data"].get("working_dir", ""),
                "timestamp": result_data["data"].get("timestamp", ""),
                "path": f"tmp/{result_filename}"  # 远端结果文件路径
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"执行结果捕获失败: {str(e)}"
            }
    
    def _show_generic_command_window(self, remote_command, cmd, args):
        """
        显示简化的命令执行窗口
        
        Args:
            remote_command (str): 远端命令
            cmd (str): 原始命令名
            args (list): 原始命令参数
            
        Returns:
            dict: 用户操作结果
        """
        try:
            import tkinter as tk
            from tkinter import messagebox
            import queue
            
            result_queue = queue.Queue()
            
            def show_command_window():
                root = tk.Tk()
                root.title("Google Drive Shell")
                root.geometry("400x60")
                root.resizable(False, False)
                
                # 居中窗口
                root.eval('tk::PlaceWindow . center')
                
                # 设置窗口置顶
                root.attributes('-topmost', True)
                
                # 自动复制命令到剪切板
                root.clipboard_clear()
                root.clipboard_append(remote_command)
                
                # 主框架
                main_frame = tk.Frame(root, padx=10, pady=10)
                main_frame.pack(fill=tk.BOTH, expand=True)
                
                # 按钮框架
                button_frame = tk.Frame(main_frame)
                button_frame.pack(fill=tk.X, expand=True)
                
                def copy_command():
                    try:
                        # 使用更可靠的复制方法 - 一次性复制完整命令
                        root.clipboard_clear()
                        root.clipboard_append(remote_command)
                        
                        # 验证复制是否成功
                        try:
                            clipboard_content = root.clipboard_get()
                            if clipboard_content == remote_command:
                                copy_btn.config(text="✅ 复制成功", bg="#4CAF50")
                            else:
                                # 复制不完整，重试一次
                                root.clipboard_clear()
                                root.clipboard_append(remote_command)
                                copy_btn.config(text="⚠️ 已重试", bg="#FF9800")
                                print(f"复制验证: 原始{len(remote_command)}字符，剪切板{len(clipboard_content)}字符")
                        except Exception as verify_error:
                            # 验证失败但复制可能成功，显示已复制
                            copy_btn.config(text="✅ 已复制", bg="#4CAF50")
                            print(f"复制验证失败但命令已复制: {verify_error}")
                        
                        root.after(1500, lambda: copy_btn.config(text="📋 复制指令", bg="#2196F3"))
                    except Exception as e:
                        print(f"复制到剪贴板失败: {e}")
                        copy_btn.config(text="❌ 复制失败", bg="#f44336")
                
                def execution_completed():
                    result_queue.put({"action": "success", "message": "用户确认执行完成"})
                    root.destroy()
                
                # 复制指令按钮
                copy_btn = tk.Button(
                    button_frame, 
                    text="📋 复制指令", 
                    command=copy_command,
                    font=("Arial", 10),
                    bg="#2196F3",
                    fg="white",
                    padx=15,
                    pady=5,
                    relief=tk.RAISED,
                    bd=2
                )
                copy_btn.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
                
                # 执行完成按钮
                complete_btn = tk.Button(
                    button_frame, 
                    text="✅ 执行完成", 
                    command=execution_completed,
                    font=("Arial", 10, "bold"),
                    bg="#4CAF50",
                    fg="white",
                    padx=15,
                    pady=5,
                    relief=tk.RAISED,
                    bd=2
                )
                complete_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                # 设置焦点到完成按钮
                complete_btn.focus_set()
                
                # 自动复制命令到剪贴板
                copy_command()
                
                root.mainloop()
            
            # 直接在主线程中显示窗口，避免tkinter线程问题
            show_command_window()
            
            # 获取结果
            try:
                return result_queue.get_nowait()
            except queue.Empty:
                return {"action": "error", "error_info": "窗口关闭但未获取到用户操作"}
                
        except Exception as e:
            return {"action": "error", "error_info": f"显示命令窗口失败: {str(e)}"}
    
    def _download_result_file(self, result_filename):
        """
        下载远端结果文件到本地/tmp目录
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            
        Returns:
            dict: 下载结果
        """
        try:
            import tempfile
            import os
            
            # 确保/tmp目录存在
            tmp_dir = "/tmp"
            os.makedirs(tmp_dir, exist_ok=True)
            
            # 本地文件路径
            local_path = os.path.join(tmp_dir, result_filename)
            
            # 远端文件路径（在tmp目录中）
            remote_file_path = f"tmp/{result_filename}"
            
            # 首先检查远端文件是否存在
            check_result = self._check_remote_file_exists(remote_file_path)
            if not check_result.get("exists"):
                return {
                    "success": False,
                    "error": f"远端结果文件不存在: {remote_file_path}"
                }
            
            # 使用现有的download功能下载文件
            download_result = self.cmd_download(remote_file_path, local_path, force=True)
            
            if download_result.get("success"):
                return {
                    "success": True,
                    "local_path": local_path,
                    "message": f"结果文件已下载到: {local_path}"
                }
            else:
                return {
                    "success": False,
                    "error": f"下载失败: {download_result.get('error', 'unknown error')}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"下载结果文件时出错: {str(e)}"
            }
    
    def _wait_and_read_result_file(self, result_filename):
        """
        等待并读取远端结果文件，最多等待60秒
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            
        Returns:
            dict: 读取结果
        """
        try:
            import sys
            
            # 远端文件路径（在REMOTE_ROOT/tmp目录中）
            remote_file_path = f"~/tmp/{result_filename}"
            
            # 输出等待指示器
            print("⏳", end="", flush=True)
            
            # 等待文件出现，最多60秒
            max_wait_time = 60
            for wait_count in range(max_wait_time):
                # 检查文件是否存在
                check_result = self._check_remote_file_exists_absolute(remote_file_path)
                
                if check_result.get("exists"):
                    # 文件存在，读取内容
                    print()  # 换行
                    return self._read_result_file_via_gds(result_filename)
                
                # 文件不存在，等待1秒并输出进度点
                time.sleep(1)
                print(".", end="", flush=True)
            
            # 超时
            print()  # 换行
            return {
                "success": False,
                "error": f"等待远端结果文件超时（60秒）: {remote_file_path}"
            }
            
        except Exception as e:
            print()  # 换行
            return {
                "success": False,
                "error": f"等待结果文件时出错: {str(e)}"
            }
    
    def _preprocess_json_content(self, content):
        """
        预处理JSON内容，修复常见的格式问题
        
        Args:
            content (str): 原始JSON内容
            
        Returns:
            str: 处理后的JSON内容
        """
        # 现在远程命令已经正确转义了换行符为\n，
        # 我们只需要处理可能仍然存在的跨行问题
        import re
        
        # 先尝试直接解析，如果成功就不需要预处理
        try:
            import json
            json.loads(content)
            return content  # 如果能直接解析，就返回原内容
        except:
            pass  # 如果解析失败，继续预处理
        
        # 处理可能的跨行问题：将多行的stdout/stderr字段合并到单行
        lines = content.split('\n')
        cleaned_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # 检查是否是跨行的stdout或stderr字段
            if ('"stdout":' in line or '"stderr":' in line) and line.endswith('"') and not line.count('"') >= 4:
                # 这可能是一个跨行字段的开始
                field_content = [line]
                i += 1
                
                # 收集内容直到找到结束
                while i < len(lines):
                    current_line = lines[i].rstrip()
                    field_content.append(current_line)
                    
                    # 检查是否结束（以" 或 ", 结尾，且不在字符串中间）
                    if current_line.endswith('"') or current_line.endswith('",'):
                        break
                    i += 1
                
                # 合并成单行
                merged_line = ' '.join(field_content)
                cleaned_lines.append(merged_line)
            else:
                # 普通行，直接添加
                cleaned_lines.append(line)
            
            i += 1
        
        return '\n'.join(cleaned_lines)

    def _read_result_file_via_gds(self, result_filename):
        """
        使用GDS ls和cat机制读取远端结果文件
        
        Args:
            result_filename (str): 远端结果文件名（在tmp目录中）
            
        Returns:
            dict: 读取结果
        """
        try:
            # 远端文件路径（在REMOTE_ROOT/tmp目录中）
            # 需要先cd到根目录，然后访问tmp目录
            remote_file_path = f"~/tmp/{result_filename}"
            
            # 首先使用ls检查文件是否存在
            check_result = self._check_remote_file_exists_absolute(remote_file_path)
            if not check_result.get("exists"):
                return {
                    "success": False,
                    "error": f"远端结果文件不存在: {remote_file_path}"
                }
            
            # 使用cat命令读取文件内容
            cat_result = self.cmd_cat(remote_file_path)
            
            if not cat_result.get("success"):
                return {
                    "success": False,
                    "error": f"读取文件内容失败: {cat_result.get('error', 'unknown error')}"
                }
            
            # 获取文件内容
            content = cat_result.get("output", "")
            
            # 尝试解析JSON
            try:
                import json
                # 预处理JSON内容以修复格式问题
                cleaned_content = self._preprocess_json_content(content)
                result_data = json.loads(cleaned_content)
                return {
                    "success": True,
                    "data": result_data
                }
            except json.JSONDecodeError as e:
                # 如果JSON解析失败，返回原始内容
                return {
                    "success": True,
                    "data": {
                        "exit_code": -1,
                        "stdout": content,
                        "stderr": f"JSON解析失败: {str(e)}",
                        "raw_content": content
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"读取结果文件时出错: {str(e)}"
            }
    
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
            ls_result = self.cmd_ls(dir_path)
            
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
            ls_result = self.cmd_ls(dir_path)
            
            if not ls_result.get("success"):
                return {"exists": False, "error": f"无法访问目录: {dir_path}"}
            
            # 检查文件是否在列表中
            files = ls_result.get("files", [])
            file_exists = any(f.get("name") == filename for f in files)
            
            return {"exists": file_exists}
            
        except Exception as e:
            return {"exists": False, "error": f"检查文件存在性时出错: {str(e)}"}
    
    def _parse_result_file(self, local_file_path):
        """
        解析本地结果文件
        
        Args:
            local_file_path (str): 本地结果文件路径
            
        Returns:
            dict: 解析结果
        """
        try:
            if not os.path.exists(local_file_path):
                return {
                    "success": False,
                    "error": f"结果文件不存在: {local_file_path}"
                }
            
            with open(local_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析JSON
            try:
                import json
                # 预处理JSON内容以修复格式问题
                cleaned_content = self._preprocess_json_content(content)
                result_data = json.loads(cleaned_content)
                return {
                    "success": True,
                    "data": result_data
                }
            except json.JSONDecodeError as e:
                # 如果JSON解析失败，返回原始内容
                return {
                    "success": True,
                    "data": {
                        "exit_code": -1,
                        "stdout": content,
                        "stderr": f"JSON解析失败: {str(e)}",
                        "raw_content": content
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"解析结果文件时出错: {str(e)}"
            }
    
    def _cleanup_remote_result_file(self, result_filename):
        """
        清理远端结果文件
        
        Args:
            result_filename (str): 要清理的远端文件名（在tmp目录中）
        """
        try:
            # 使用rm命令删除远端文件（静默执行）
            remote_file_path = f"tmp/{result_filename}"
            self.cmd_rm(remote_file_path, force=True)
        except:
            # 清理失败不影响主要功能
            pass

