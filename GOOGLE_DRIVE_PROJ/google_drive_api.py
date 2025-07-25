#!/usr/bin/env python3
"""
Google Drive API Service
远程控制Google Drive的API服务类
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import io

class GoogleDriveService:
    """Google Drive API服务类"""
    
    def __init__(self, service_account_key_path=None):
        """
        初始化Google Drive服务
        
        Args:
            service_account_key_path (str): 服务账户密钥文件路径
        """
        self.service = None
        self.credentials = None
        
        # 获取密钥文件路径
        if service_account_key_path:
            self.key_path = service_account_key_path
        else:
            self.key_path = os.environ.get('GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY')
        
        # 尝试认证
        self._authenticate()
    
    def _authenticate(self):
        """认证并创建服务对象"""
        try:
            # 定义需要的权限范围
            SCOPES = [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
            
            # 尝试从文件认证
            if self.key_path and os.path.exists(self.key_path):
                # 从服务账户密钥文件创建凭据
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.key_path, scopes=SCOPES
                )
            else:
                # 尝试从环境变量构建服务账户信息
                service_account_info = self._build_service_account_info_from_env()
                if service_account_info:
                    self.credentials = service_account.Credentials.from_service_account_info(
                        service_account_info, scopes=SCOPES
                    )
                else:
                    raise ValueError("无法找到有效的服务账户认证信息")
            
            # 创建Drive API服务对象
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            raise Exception(f"Google Drive API认证失败: {e}")
    
    def _build_service_account_info_from_env(self):
        """从环境变量构建服务账户信息"""
        try:
            # 检查必需的环境变量
            required_vars = [
                'GOOGLE_DRIVE_SERVICE_TYPE',
                'GOOGLE_DRIVE_PROJECT_ID',
                'GOOGLE_DRIVE_PRIVATE_KEY_ID',
                'GOOGLE_DRIVE_PRIVATE_KEY',
                'GOOGLE_DRIVE_CLIENT_EMAIL',
                'GOOGLE_DRIVE_CLIENT_ID',
                'GOOGLE_DRIVE_AUTH_URI',
                'GOOGLE_DRIVE_TOKEN_URI',
                'GOOGLE_DRIVE_AUTH_PROVIDER_CERT_URL',
                'GOOGLE_DRIVE_CLIENT_CERT_URL'
            ]
            
            # 检查所有必需变量是否存在
            env_values = {}
            for var in required_vars:
                value = os.environ.get(var)
                if not value:
                    return None
                env_values[var] = value
            
            # 构建服务账户信息字典
            service_account_info = {
                "type": env_values['GOOGLE_DRIVE_SERVICE_TYPE'],
                "project_id": env_values['GOOGLE_DRIVE_PROJECT_ID'],
                "private_key_id": env_values['GOOGLE_DRIVE_PRIVATE_KEY_ID'],
                "private_key": env_values['GOOGLE_DRIVE_PRIVATE_KEY'].replace('\\n', '\n'),
                "client_email": env_values['GOOGLE_DRIVE_CLIENT_EMAIL'],
                "client_id": env_values['GOOGLE_DRIVE_CLIENT_ID'],
                "auth_uri": env_values['GOOGLE_DRIVE_AUTH_URI'],
                "token_uri": env_values['GOOGLE_DRIVE_TOKEN_URI'],
                "auth_provider_x509_cert_url": env_values['GOOGLE_DRIVE_AUTH_PROVIDER_CERT_URL'],
                "client_x509_cert_url": env_values['GOOGLE_DRIVE_CLIENT_CERT_URL']
            }
            
            return service_account_info
            
        except Exception as e:
            print(f"从环境变量构建服务账户信息失败: {e}")
            return None
    
    def test_connection(self):
        """测试API连接"""
        try:
            # 获取用户信息
            about = self.service.about().get(fields="user").execute()
            user_info = about.get('user', {})
            
            return {
                "success": True,
                "message": "Google Drive API连接成功",
                "user_email": user_info.get('emailAddress', 'Unknown'),
                "user_name": user_info.get('displayName', 'Unknown')
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"连接测试失败: {e}"
            }
    
    def list_files(self, folder_id=None, max_results=10):
        """
        列出文件
        
        Args:
            folder_id (str): 文件夹ID，None表示根目录
            max_results (int): 最大结果数
            
        Returns:
            dict: 文件列表
        """
        try:
            query = ""
            if folder_id:
                query = f"'{folder_id}' in parents"
            
            results = self.service.files().list(
                q=query,
                pageSize=max_results,
                fields="nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime)"
            ).execute()
            
            items = results.get('files', [])
            
            return {
                "success": True,
                "files": items,
                "count": len(items)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"列出文件失败: {e}"
            }
    
    def create_folder(self, name, parent_id=None):
        """
        创建文件夹
        
        Args:
            name (str): 文件夹名称
            parent_id (str): 父文件夹ID，None表示根目录
            
        Returns:
            dict: 创建结果
        """
        try:
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name'
            ).execute()
            
            return {
                "success": True,
                "folder_id": folder.get('id'),
                "folder_name": folder.get('name')
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"创建文件夹失败: {e}"
            }
    
    def upload_file(self, local_file_path, drive_folder_id=None, drive_filename=None):
        """
        上传文件到Google Drive
        
        Args:
            local_file_path (str): 本地文件路径
            drive_folder_id (str): Drive文件夹ID，None表示根目录
            drive_filename (str): Drive中的文件名，None使用本地文件名
            
        Returns:
            dict: 上传结果
        """
        try:
            if not os.path.exists(local_file_path):
                return {
                    "success": False,
                    "error": f"本地文件不存在: {local_file_path}"
                }
            
            # 确定文件名
            if not drive_filename:
                drive_filename = os.path.basename(local_file_path)
            
            # 文件元数据
            file_metadata = {'name': drive_filename}
            if drive_folder_id:
                file_metadata['parents'] = [drive_folder_id]
            
            # 上传文件
            media = MediaFileUpload(local_file_path)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, size'
            ).execute()
            
            return {
                "success": True,
                "file_id": file.get('id'),
                "file_name": file.get('name'),
                "file_size": file.get('size')
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"上传文件失败: {e}"
            }
    
    def download_file(self, file_id, local_save_path):
        """
        从Google Drive下载文件
        
        Args:
            file_id (str): Drive文件ID
            local_save_path (str): 本地保存路径
            
        Returns:
            dict: 下载结果
        """
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
            
            # 保存文件
            with open(local_save_path, 'wb') as f:
                f.write(fh.getvalue())
            
            return {
                "success": True,
                "local_path": local_save_path,
                "message": "文件下载成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"下载文件失败: {e}"
            }
    
    def delete_file(self, file_id):
        """
        删除文件
        
        Args:
            file_id (str): 文件ID
            
        Returns:
            dict: 删除结果
        """
        try:
            self.service.files().delete(fileId=file_id).execute()
            return {
                "success": True,
                "message": "文件删除成功"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"删除文件失败: {e}"
            }
    
    def share_file(self, file_id, email_address, role='reader'):
        """
        分享文件给指定邮箱
        
        Args:
            file_id (str): 文件ID
            email_address (str): 邮箱地址
            role (str): 权限角色 (reader, writer, owner)
            
        Returns:
            dict: 分享结果
        """
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email_address
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission,
                sendNotificationEmail=True
            ).execute()
            
            return {
                "success": True,
                "message": f"文件已分享给 {email_address}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"分享文件失败: {e}"
            }

# 测试函数
def test_drive_service():
    """测试Google Drive服务"""
    try:
        print("🧪 正在测试Google Drive API连接...")
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 测试连接
        result = drive_service.test_connection()
        
        if result['success']:
            print("✅ API连接测试成功！")
            print(f"📧 服务账户邮箱: {result.get('user_email', 'Unknown')}")
            print(f"👤 用户名: {result.get('user_name', 'Unknown')}")
            
            # 测试列出文件
            print("\n📂 正在测试文件列表功能...")
            files_result = drive_service.list_files(max_results=5)
            
            if files_result['success']:
                print(f"✅ 文件列表获取成功！找到 {files_result['count']} 个文件")
                for file in files_result['files'][:3]:  # 显示前3个文件
                    print(f"   📄 {file['name']} ({file['mimeType']})")
            else:
                print(f"❌ 文件列表获取失败: {files_result['error']}")
            
            return True
        else:
            print(f"❌ API连接测试失败: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

if __name__ == "__main__":
    test_drive_service()
