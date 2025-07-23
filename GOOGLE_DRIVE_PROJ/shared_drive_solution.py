#!/usr/bin/env python3
"""
Google Drive Shared Drive Solution
解决服务账户存储配额限制的方案
"""

import json
from pathlib import Path
from google_drive_api import GoogleDriveService

class SharedDriveSolution:
    """Shared Drive解决方案类"""
    
    def __init__(self):
        self.drive_service = GoogleDriveService()
    
    def create_shared_drive(self, name="GOOGLE_DRIVE_SHELL_WORKSPACE"):
        """创建共享驱动器"""
        try:
            import uuid
            request_id = str(uuid.uuid4())
            
            # 创建共享驱动器
            drive_metadata = {
                'name': name
            }
            
            # 使用drives.create方法
            result = self.drive_service.service.drives().create(
                body=drive_metadata,
                requestId=request_id,
                fields='id,name'
            ).execute()
            
            return {
                "success": True,
                "drive_id": result['id'],
                "drive_name": result['name'],
                "message": f"✅ 共享驱动器创建成功: {name}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"创建共享驱动器失败: {e}"}
    
    def list_shared_drives(self):
        """列出可访问的共享驱动器"""
        try:
            result = self.drive_service.service.drives().list(
                fields='drives(id,name,capabilities)'
            ).execute()
            
            drives = result.get('drives', [])
            
            return {
                "success": True,
                "drives": drives,
                "count": len(drives)
            }
            
        except Exception as e:
            return {"success": False, "error": f"列出共享驱动器失败: {e}"}
    
    def upload_to_shared_drive(self, file_path, drive_id, filename=None):
        """上传文件到共享驱动器"""
        try:
            if not filename:
                filename = Path(file_path).name
            
            # 文件元数据
            file_metadata = {
                'name': filename,
                'parents': [drive_id]  # 指定共享驱动器ID作为父级
            }
            
            # 使用MediaFileUpload
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(file_path, resumable=True)
            
            # 创建文件
            result = self.drive_service.service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,  # 支持共享驱动器
                fields='id,name,size'
            ).execute()
            
            return {
                "success": True,
                "file_id": result['id'],
                "file_name": result['name'],
                "file_size": result.get('size', 0),
                "message": f"✅ 文件上传到共享驱动器成功: {filename}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"上传到共享驱动器失败: {e}"}
    
    def create_text_file_in_shared_drive(self, content, filename, drive_id):
        """在共享驱动器中创建文本文件"""
        try:
            import tempfile
            import os
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # 上传到共享驱动器
                result = self.upload_to_shared_drive(temp_file_path, drive_id, filename)
                
                # 清理临时文件
                os.unlink(temp_file_path)
                
                return result
                
            except Exception as e:
                # 确保清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                return {"success": False, "error": f"创建文本文件失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"准备文本文件失败: {e}"}
    
    def setup_workspace_drive(self):
        """设置工作区共享驱动器"""
        try:
            # 首先检查是否已有工作区驱动器
            drives_result = self.list_shared_drives()
            if not drives_result["success"]:
                return drives_result
            
            workspace_drive = None
            for drive in drives_result["drives"]:
                if drive["name"] == "GOOGLE_DRIVE_SHELL_WORKSPACE":
                    workspace_drive = drive
                    break
            
            if workspace_drive:
                return {
                    "success": True,
                    "drive_id": workspace_drive["id"],
                    "drive_name": workspace_drive["name"],
                    "message": "✅ 工作区共享驱动器已存在",
                    "action": "existing"
                }
            else:
                # 创建新的工作区驱动器
                create_result = self.create_shared_drive("GOOGLE_DRIVE_SHELL_WORKSPACE")
                if create_result["success"]:
                    create_result["action"] = "created"
                return create_result
                
        except Exception as e:
            return {"success": False, "error": f"设置工作区驱动器失败: {e}"}
    
    def save_drive_config(self, drive_id, drive_name):
        """保存共享驱动器配置"""
        try:
            data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
            data_dir.mkdir(exist_ok=True)
            
            config_file = data_dir / "shared_drive_config.json"
            
            config = {
                "workspace_drive_id": drive_id,
                "workspace_drive_name": drive_name,
                "created_time": __import__('time').strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return {"success": True, "config_file": str(config_file)}
            
        except Exception as e:
            return {"success": False, "error": f"保存配置失败: {e}"}
    
    def load_drive_config(self):
        """加载共享驱动器配置"""
        try:
            data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
            config_file = data_dir / "shared_drive_config.json"
            
            if not config_file.exists():
                return {"success": False, "error": "配置文件不存在"}
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return {"success": True, "config": config}
            
        except Exception as e:
            return {"success": False, "error": f"加载配置失败: {e}"}

def main():
    """测试共享驱动器功能"""
    solution = SharedDriveSolution()
    
    print("🚀 设置Google Drive Shell工作区...")
    
    # 设置工作区
    setup_result = solution.setup_workspace_drive()
    print(f"设置结果: {setup_result}")
    
    if setup_result["success"]:
        # 保存配置
        save_result = solution.save_drive_config(
            setup_result["drive_id"],
            setup_result["drive_name"]
        )
        print(f"配置保存: {save_result}")
        
        # 测试文本文件创建
        test_result = solution.create_text_file_in_shared_drive(
            "Hello from Google Drive Shell!\nThis is a test file.",
            "test_file.txt",
            setup_result["drive_id"]
        )
        print(f"测试文件创建: {test_result}")

if __name__ == "__main__":
    main() 