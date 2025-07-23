#!/usr/bin/env python3
"""
Google Drive Folder Sharing Solution
基于用户分享文件夹的解决方案，解决服务账户存储限制
"""

import json
from pathlib import Path
from google_drive_api import GoogleDriveService

class FolderSharingSolution:
    """文件夹分享解决方案类"""
    
    def __init__(self):
        self.drive_service = GoogleDriveService()
    
    def get_service_account_email(self):
        """获取服务账户邮箱地址"""
        try:
            # 从服务账户密钥文件中获取邮箱
            import os
            import json
            
            key_path = os.environ.get('GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY')
            if not key_path or not os.path.exists(key_path):
                return {"success": False, "error": "服务账户密钥文件未找到"}
            
            with open(key_path, 'r') as f:
                key_data = json.load(f)
            
            email = key_data.get('client_email')
            if not email:
                return {"success": False, "error": "无法从密钥文件获取邮箱地址"}
            
            return {
                "success": True,
                "email": email,
                "project_id": key_data.get('project_id', 'unknown')
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取服务账户邮箱失败: {e}"}
    
    def check_folder_access(self, folder_id):
        """检查是否可以访问指定文件夹"""
        try:
            # 尝试获取文件夹信息
            result = self.drive_service.service.files().get(
                fileId=folder_id,
                fields='id,name,mimeType,capabilities'
            ).execute()
            
            # 检查是否为文件夹
            if result.get('mimeType') != 'application/vnd.google-apps.folder':
                return {"success": False, "error": "指定ID不是文件夹"}
            
            capabilities = result.get('capabilities', {})
            
            return {
                "success": True,
                "folder_name": result['name'],
                "folder_id": result['id'],
                "can_create": capabilities.get('canAddChildren', False),
                "can_edit": capabilities.get('canEdit', False),
                "can_list": capabilities.get('canListChildren', False)
            }
            
        except Exception as e:
            return {"success": False, "error": f"无法访问文件夹: {e}"}
    
    def test_file_creation(self, folder_id):
        """测试在文件夹中创建文件"""
        try:
            # 创建测试文件
            import tempfile
            import os
            
            test_content = "Google Drive Shell 测试文件\n创建时间: " + __import__('time').strftime("%Y-%m-%d %H:%M:%S")
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as temp_file:
                temp_file.write(test_content)
                temp_file_path = temp_file.name
            
            try:
                # 文件元数据
                file_metadata = {
                    'name': 'gds_test_file.txt',
                    'parents': [folder_id]
                }
                
                # 使用MediaFileUpload
                from googleapiclient.http import MediaFileUpload
                media = MediaFileUpload(temp_file_path, mimetype='text/plain')
                
                # 创建文件
                result = self.drive_service.service.files().create(
                    body=file_metadata,
                    media_body=media,
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
                    "message": f"✅ 测试文件创建成功: {result['name']}"
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
    
    def setup_shared_folder(self, folder_url=None, folder_id=None):
        """设置共享文件夹"""
        try:
            # 从URL提取文件夹ID
            if folder_url and not folder_id:
                import re
                match = re.search(r'/folders/([a-zA-Z0-9-_]+)', folder_url)
                if match:
                    folder_id = match.group(1)
                else:
                    return {"success": False, "error": "无法从URL提取文件夹ID"}
            
            if not folder_id:
                return {"success": False, "error": "请提供文件夹ID或URL"}
            
            # 检查文件夹访问权限
            access_result = self.check_folder_access(folder_id)
            if not access_result["success"]:
                return access_result
            
            # 检查必要权限
            if not access_result["can_create"]:
                return {
                    "success": False,
                    "error": "服务账户没有在此文件夹创建文件的权限",
                    "suggestion": "请确保文件夹已与服务账户共享，并给予编辑权限"
                }
            
            # 测试文件创建
            test_result = self.test_file_creation(folder_id)
            if not test_result["success"]:
                return {
                    "success": False,
                    "error": f"文件创建测试失败: {test_result['error']}",
                    "folder_info": access_result
                }
            
            # 保存配置
            config_result = self.save_folder_config(folder_id, access_result["folder_name"])
            
            return {
                "success": True,
                "folder_id": folder_id,
                "folder_name": access_result["folder_name"],
                "test_file": test_result,
                "config_saved": config_result["success"],
                "message": f"✅ 共享文件夹设置成功: {access_result['folder_name']}"
            }
            
        except Exception as e:
            return {"success": False, "error": f"设置共享文件夹失败: {e}"}
    
    def save_folder_config(self, folder_id, folder_name):
        """保存共享文件夹配置"""
        try:
            data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
            data_dir.mkdir(exist_ok=True)
            
            config_file = data_dir / "shared_folder_config.json"
            
            config = {
                "shared_folder_id": folder_id,
                "shared_folder_name": folder_name,
                "created_time": __import__('time').strftime("%Y-%m-%d %H:%M:%S"),
                "type": "user_shared_folder"
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return {"success": True, "config_file": str(config_file)}
            
        except Exception as e:
            return {"success": False, "error": f"保存配置失败: {e}"}
    
    def load_folder_config(self):
        """加载共享文件夹配置"""
        try:
            data_dir = Path(__file__).parent.parent / "GOOGLE_DRIVE_DATA"
            config_file = data_dir / "shared_folder_config.json"
            
            if not config_file.exists():
                return {"success": False, "error": "配置文件不存在"}
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return {"success": True, "config": config}
            
        except Exception as e:
            return {"success": False, "error": f"加载配置失败: {e}"}
    
    def create_text_file_in_shared_folder(self, content, filename, folder_id=None):
        """在共享文件夹中创建文本文件"""
        try:
            if not folder_id:
                # 从配置加载文件夹ID
                config_result = self.load_folder_config()
                if not config_result["success"]:
                    return {"success": False, "error": "未找到共享文件夹配置"}
                folder_id = config_result["config"]["shared_folder_id"]
            
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
                    'parents': [folder_id]
                }
                
                # 使用MediaFileUpload
                from googleapiclient.http import MediaFileUpload
                media = MediaFileUpload(temp_file_path, mimetype='text/plain')
                
                # 创建文件
                result = self.drive_service.service.files().create(
                    body=file_metadata,
                    media_body=media,
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
                return {"success": False, "error": f"文件创建失败: {e}"}
                
        except Exception as e:
            return {"success": False, "error": f"创建文本文件时出错: {e}"}
    
    def show_setup_instructions(self):
        """显示设置说明"""
        email_result = self.get_service_account_email()
        
        if email_result["success"]:
            service_email = email_result["email"]
            
            print("🔧 Google Drive Shell 文件夹共享设置")
            print("=" * 50)
            print()
            print("📋 设置步骤：")
            print()
            print("1. 在Google Drive中创建一个新文件夹")
            print("   - 访问 https://drive.google.com")
            print("   - 创建文件夹，例如 'Google Drive Shell Workspace'")
            print()
            print("2. 与服务账户分享文件夹")
            print("   - 右键点击文件夹 → 共享")
            print(f"   - 添加邮箱地址: {service_email}")
            print("   - 权限设置为: 编辑者 (Editor)")
            print("   - 点击发送")
            print()
            print("3. 获取文件夹链接")
            print("   - 右键点击文件夹 → 获取链接")
            print("   - 复制链接，格式类似：")
            print("     https://drive.google.com/drive/folders/1ABC...XYZ")
            print()
            print("4. 运行设置命令")
            print("   python folder_sharing_solution.py --setup <文件夹链接>")
            print()
            print(f"📧 服务账户邮箱: {service_email}")
            print(f"🆔 项目ID: {email_result.get('project_id', 'unknown')}")
            
        else:
            print(f"❌ 获取服务账户信息失败: {email_result['error']}")

def main():
    """主函数"""
    import sys
    
    solution = FolderSharingSolution()
    
    if len(sys.argv) < 2:
        solution.show_setup_instructions()
        return
    
    if sys.argv[1] == '--setup' and len(sys.argv) > 2:
        folder_url = sys.argv[2]
        print(f"🚀 设置共享文件夹: {folder_url}")
        
        result = solution.setup_shared_folder(folder_url=folder_url)
        print(f"设置结果: {result}")
        
        if result["success"]:
            print()
            print("✅ 设置完成！现在可以使用以下命令：")
            print("  GDS echo 'Hello World' > test.txt")
            print("  GDS ls")
            print("  GDS cat test.txt")
    
    elif sys.argv[1] == '--test':
        print("🧪 测试共享文件夹配置...")
        
        config_result = solution.load_folder_config()
        if config_result["success"]:
            folder_id = config_result["config"]["shared_folder_id"]
            test_result = solution.test_file_creation(folder_id)
            print(f"测试结果: {test_result}")
        else:
            print(f"❌ 配置加载失败: {config_result['error']}")
    
    else:
        solution.show_setup_instructions()

if __name__ == "__main__":
    main() 