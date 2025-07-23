#!/usr/bin/env python3
"""
设置共享驱动器配置
用于配置Google Drive Shell使用用户创建的共享驱动器
"""

import json
import sys
import re
from pathlib import Path
from google_drive_api import GoogleDriveService

class SharedDriveSetup:
    def __init__(self):
        self.drive_service = GoogleDriveService()
    
    def extract_drive_id_from_url(self, url):
        """从共享驱动器URL提取ID"""
        # 匹配共享驱动器URL模式
        patterns = [
            r'/drive/folders/([a-zA-Z0-9-_]+)',  # 标准文件夹URL
            r'[?&]id=([a-zA-Z0-9-_]+)',          # 带ID参数的URL
            r'/drive/u/\d+/folders/([a-zA-Z0-9-_]+)'  # 带用户ID的URL
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # 如果URL看起来就是一个ID
        if re.match(r'^[a-zA-Z0-9-_]+$', url.strip()):
            return url.strip()
        
        return None
    
    def test_shared_drive_access(self, drive_id):
        """测试共享驱动器访问权限"""
        try:
            # 检查是否可以访问驱动器
            result = self.drive_service.service.drives().get(
                driveId=drive_id,
                fields='id,name,capabilities'
            ).execute()
            
            capabilities = result.get('capabilities', {})
            
            return {
                "success": True,
                "drive_name": result['name'],
                "drive_id": result['id'],
                "can_manage": capabilities.get('canManageMembers', False),
                "can_add_children": capabilities.get('canAddChildren', False),
                "can_edit": capabilities.get('canEdit', False)
            }
            
        except Exception as e:
            return {"success": False, "error": f"无法访问共享驱动器: {e}"}
    
    def test_file_creation_in_drive(self, drive_id):
        """在共享驱动器中测试文件创建"""
        try:
            import tempfile
            import os
            
            test_content = f"Google Drive Shell 测试文件\n创建时间: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}\n驱动器ID: {drive_id}"
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(test_content)
                temp_file_path = temp_file.name
            
            try:
                # 文件元数据 - 直接上传到共享驱动器根目录
                file_metadata = {
                    'name': 'gds_shared_drive_test.txt',
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
                    "message": f"✅ 共享驱动器文件创建成功: {result['name']}"
                }
                
            except Exception as e:
                # 确保清理临时文件
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                return {"success": False, "error": f"文件创建失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"测试文件创建时出错: {e}"}
    
    def save_shared_drive_config(self, drive_id, drive_name):
        """保存共享驱动器配置"""
        try:
            data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
            data_dir.mkdir(exist_ok=True)
            
            config_file = data_dir / "shared_drive_config.json"
            
            config = {
                "shared_drive_id": drive_id,
                "shared_drive_name": drive_name,
                "type": "user_created_shared_drive",
                "created_time": __import__('time').strftime("%Y-%m-%d %H:%M:%S"),
                "supports_file_creation": True
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return {"success": True, "config_file": str(config_file)}
            
        except Exception as e:
            return {"success": False, "error": f"保存配置失败: {e}"}
    
    def setup_shared_drive(self, drive_url_or_id):
        """设置共享驱动器"""
        try:
            # 提取驱动器ID
            drive_id = self.extract_drive_id_from_url(drive_url_or_id)
            if not drive_id:
                return {"success": False, "error": "无法从URL提取共享驱动器ID"}
            
            print(f"🔍 检查共享驱动器访问权限...")
            
            # 测试驱动器访问
            access_result = self.test_shared_drive_access(drive_id)
            if not access_result["success"]:
                return access_result
            
            print(f"✅ 可以访问共享驱动器: {access_result['drive_name']}")
            
            if not access_result["can_add_children"]:
                return {
                    "success": False,
                    "error": "服务账户在此共享驱动器中没有创建文件的权限",
                    "suggestion": "请确保服务账户具有'内容管理员'或'管理员'权限"
                }
            
            print(f"🧪 测试文件创建...")
            
            # 测试文件创建
            test_result = self.test_file_creation_in_drive(drive_id)
            if not test_result["success"]:
                return {
                    "success": False,
                    "error": f"文件创建测试失败: {test_result['error']}",
                    "drive_info": access_result
                }
            
            print(f"✅ 文件创建测试成功!")
            
            # 保存配置
            config_result = self.save_shared_drive_config(drive_id, access_result["drive_name"])
            
            return {
                "success": True,
                "drive_id": drive_id,
                "drive_name": access_result["drive_name"],
                "test_file": test_result,
                "config_saved": config_result["success"],
                "message": f"🎉 共享驱动器设置成功: {access_result['drive_name']}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"设置共享驱动器失败: {e}"}
    
    def show_instructions(self):
        """显示设置说明"""
        print("🔧 Google Drive Shell 共享驱动器设置")
        print("=" * 50)
        print()
        print("📋 设置步骤：")
        print()
        print("1. 创建共享驱动器")
        print("   - 访问 https://drive.google.com")
        print("   - 点击左侧 '共享驱动器'")
        print("   - 点击 '新建' 创建驱动器")
        print("   - 命名为: 'Google Drive Shell Workspace'")
        print()
        print("2. 添加服务账户为成员")
        print("   - 在共享驱动器中点击 '管理成员'")
        print("   - 添加邮箱: drive-remote-controller@console-control-466711.iam.gserviceaccount.com")
        print("   - 权限设为: 内容管理员 或 管理员")
        print()
        print("3. 获取驱动器链接")
        print("   - 进入共享驱动器")
        print("   - 复制浏览器地址栏URL")
        print()
        print("4. 运行配置命令")
        print("   python setup_shared_drive.py <驱动器URL或ID>")
        print()

def main():
    """主函数"""
    setup = SharedDriveSetup()
    
    if len(sys.argv) < 2:
        setup.show_instructions()
        return
    
    drive_url_or_id = sys.argv[1]
    
    print(f"🚀 设置共享驱动器...")
    result = setup.setup_shared_drive(drive_url_or_id)
    
    print()
    if result["success"]:
        print("🎉 设置完成!")
        print(f"驱动器名称: {result['drive_name']}")
        print(f"驱动器ID: {result['drive_id']}")
        print()
        print("现在可以使用文件创建功能了:")
        print("  GDS echo 'Hello Shared Drive!' > test.txt")
        print("  GDS cat test.txt")
        print("  GDS ls")
    else:
        print(f"❌ 设置失败: {result['error']}")
        if "suggestion" in result:
            print(f"💡 建议: {result['suggestion']}")

if __name__ == "__main__":
    main() 