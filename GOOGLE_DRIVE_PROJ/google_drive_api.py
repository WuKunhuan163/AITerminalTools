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
        self.key_path = None
        self.key_data = None
        # 路径解析缓存，减少重复API调用
        self._path_cache = {}
        self._cache_max_size = 100  # 最大缓存条目数
        
        # 优先尝试从环境变量加载密钥信息
        if self._load_from_environment():
            pass  # 已从环境变量加载
        elif service_account_key_path:
            self.key_path = service_account_key_path
            if not os.path.exists(self.key_path):
                raise FileNotFoundError(f"服务账户密钥文件不存在: {self.key_path}")
        else:
            # 回退到文件路径模式
            self.key_path = os.environ.get('GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY')
            if not self.key_path:
                raise ValueError("未找到服务账户密钥文件路径或环境变量")
            if not os.path.exists(self.key_path):
                raise FileNotFoundError(f"服务账户密钥文件不存在: {self.key_path}")
        
        self._authenticate()
    
    def _load_from_environment(self):
        """
        从环境变量加载服务账户密钥信息
        
        Returns:
            bool: 是否成功从环境变量加载
        """
        try:
            # 检查是否有完整的环境变量集合
            required_env_vars = {
                'type': 'GOOGLE_DRIVE_SERVICE_TYPE',
                'project_id': 'GOOGLE_DRIVE_PROJECT_ID',
                'private_key_id': 'GOOGLE_DRIVE_PRIVATE_KEY_ID',
                'private_key': 'GOOGLE_DRIVE_PRIVATE_KEY',
                'client_email': 'GOOGLE_DRIVE_CLIENT_EMAIL',
                'client_id': 'GOOGLE_DRIVE_CLIENT_ID',
                'auth_uri': 'GOOGLE_DRIVE_AUTH_URI',
                'token_uri': 'GOOGLE_DRIVE_TOKEN_URI',
                'auth_provider_x509_cert_url': 'GOOGLE_DRIVE_AUTH_PROVIDER_CERT_URL',
                'client_x509_cert_url': 'GOOGLE_DRIVE_CLIENT_CERT_URL'
            }
            
            # 构建密钥数据字典
            key_data = {}
            missing_vars = []
            
            for json_key, env_var in required_env_vars.items():
                value = os.environ.get(env_var)
                if value is None:
                    missing_vars.append(env_var)
                else:
                    key_data[json_key] = value
            
            # 检查可选字段
            universe_domain = os.environ.get('GOOGLE_DRIVE_UNIVERSE_DOMAIN')
            if universe_domain:
                key_data['universe_domain'] = universe_domain
            
            # 如果有缺失的必需变量，返回False
            if missing_vars:
                return False
            
            # 保存密钥数据
            self.key_data = key_data
            return True
            
        except Exception as e:
            return False
    
    def _authenticate(self):
        """认证并创建服务对象"""
        try:
            # 定义需要的权限范围
            SCOPES = [
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file'
            ]
            
            # 根据加载方式创建凭据
            if self.key_data:
                # 从环境变量中的密钥数据创建凭据
                self.credentials = service_account.Credentials.from_service_account_info(
                    self.key_data, scopes=SCOPES
                )
            elif self.key_path:
                # 从服务账户密钥文件创建凭据
                self.credentials = service_account.Credentials.from_service_account_file(
                    self.key_path, scopes=SCOPES
                )
            else:
                raise ValueError("无法创建凭据：既没有密钥数据也没有密钥文件")
            
            # 创建Drive API服务对象
            self.service = build('drive', 'v3', credentials=self.credentials)
            
        except Exception as e:
            raise Exception(f"Google Drive API认证失败: {e}")
    
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
    
    def _resolve_absolute_path_to_folder_id(self, absolute_path, remote_root_folder_id):
        """
        将绝对路径解析为Google Drive文件夹ID
        
        Args:
            absolute_path (str): 绝对路径
            remote_root_folder_id (str): 远程根目录ID
            
        Returns:
            tuple: (folder_id, resolved_path) 或 (None, None)
        """
        try:
            # 检查缓存
            cache_key = f"{remote_root_folder_id}:{absolute_path}"
            if cache_key in self._path_cache:
                return self._path_cache[cache_key]
            
            # 处理根目录
            if absolute_path == "~":
                result = (remote_root_folder_id, "~")
                self._cache_result(cache_key, result)
                return result
            
            # 处理以~/开头的路径
            if not absolute_path.startswith("~/"):
                result = (None, None)
                self._cache_result(cache_key, result)
                return result
            
            # 移除~/前缀
            relative_path = absolute_path[2:]
            if not relative_path:
                result = (remote_root_folder_id, "~")
                self._cache_result(cache_key, result)
                return result
            
            # 分割路径
            path_parts = [part for part in relative_path.split("/") if part]
            
            current_folder_id = remote_root_folder_id
            current_path = "~"
            
            # 逐级解析路径
            for part in path_parts:
                # 处理特殊路径组件
                if part == "..":
                    # 父目录 - 需要通过API查找父目录
                    parent_id = self._get_parent_folder_id(current_folder_id)
                    if not parent_id:
                        return None, None  # 没有父目录
                    current_folder_id = parent_id
                    # 更新逻辑路径
                    if current_path == "~":
                        return None, None  # 根目录没有父目录
                    else:
                        # 移除路径的最后一部分
                        path_parts_current = current_path.split("/")
                        if len(path_parts_current) > 1:
                            current_path = "/".join(path_parts_current[:-1])
                        else:
                            current_path = "~"
                elif part == ".":
                    # 当前目录，跳过
                    continue
                else:
                    # 普通目录名
                    folder_id = self._find_folder_by_name(current_folder_id, part)
                    if not folder_id:
                        return None, None  # 文件夹不存在
                    current_folder_id = folder_id
                    # 更新逻辑路径
                    if current_path == "~":
                        current_path = f"~/{part}"
                    else:
                        current_path = f"{current_path}/{part}"
            
            # 缓存成功的结果
            result = (current_folder_id, current_path)
            self._cache_result(cache_key, result)
            return result
            
        except Exception as e:
            # 缓存失败的结果
            result = (None, None)
            self._cache_result(cache_key, result)
            return result
    
    def _cache_result(self, cache_key, result):
        """缓存结果，管理缓存大小"""
        if len(self._path_cache) >= self._cache_max_size:
            # 清除最老的一半缓存条目
            keys_to_remove = list(self._path_cache.keys())[:self._cache_max_size // 2]
            for key in keys_to_remove:
                del self._path_cache[key]
        
        self._path_cache[cache_key] = result
    
    def _get_parent_folder_id(self, folder_id):
        """获取文件夹的父目录ID"""
        try:
            file_metadata = self.service.files().get(
                fileId=folder_id,
                fields="parents"
            ).execute()
            
            parents = file_metadata.get('parents', [])
            return parents[0] if parents else None
            
        except Exception:
            return None
    
    def _find_folder_by_name(self, parent_folder_id, folder_name):
        """在父目录中查找指定名称的文件夹"""
        try:
            query = f"'{parent_folder_id}' in parents and name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
            results = self.service.files().list(
                q=query,
                pageSize=1,
                fields="files(id)"
            ).execute()
            
            items = results.get('files', [])
            return items[0]['id'] if items else None
            
        except Exception:
            return None
    
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
                "message": "File downloaded successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"{e}"
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
                "message": "File deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to delete file: {e}"
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
                "message": f"File shared with {email_address}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to share file: {e}"
            }

# 测试函数
def test_drive_service():
    """测试Google Drive服务"""
    try:
        print("🧪 Testing Google Drive API connection...")
        
        # 创建服务实例
        drive_service = GoogleDriveService()
        
        # 测试连接
        result = drive_service.test_connection()
        
        if result['success']:
            print("✅ API connection test successful!")
            print(f"📧 Service account email: {result.get('user_email', 'Unknown')}")
            print(f"👤 User name: {result.get('user_name', 'Unknown')}")
            
            # 测试列出文件
            print("\n📂 Testing file list...")
            files_result = drive_service.list_files(max_results=5)
            
            if files_result['success']:
                print(f"✅ File list retrieval successful! Found {files_result['count']} files")
                for file in files_result['files'][:3]:  # 显示前3个文件
                    print(f"   📄 {file['name']} ({file['mimeType']})")
            else:
                print(f"❌ File list retrieval failed: {files_result['error']}")
            
            return True
        else:
            print(f"❌ API connection test failed: {result['error']}")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    test_drive_service()
