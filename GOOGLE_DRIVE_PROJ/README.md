# Google Drive Remote Control Project

这个项目为GOOGLE_DRIVE工具提供远程控制Google Drive的API功能。

## 文件结构

```
GOOGLE_DRIVE_PROJ/
├── README.md                 # 项目说明
├── google_drive_api.py       # Google Drive API服务类集成代码
```

## 文件说明

### google_drive_api.py
- **功能**: 提供完整的Google Drive API服务类
- **主要类**: `GoogleDriveService`
- **主要功能**:
  - 测试API连接
  - 列出文件和文件夹
  - 上传文件到Drive
  - 从Drive下载文件
  - 删除Drive文件
  - 分享文件给其他用户
  - 创建文件夹

## 使用方法

### 1. 本地使用

```bash
# 测试API连接
python GOOGLE_DRIVE_PROJ/google_drive_api.py

# 在Python代码中使用
from GOOGLE_DRIVE_PROJ.google_drive_api import GoogleDriveService
drive = GoogleDriveService()
result = drive.list_files()
```

### 3. 通过GOOGLE_DRIVE工具使用

```bash
# 设置API
GOOGLE_DRIVE --console-setup

# 测试连接
GOOGLE_DRIVE --api-test

# 列出文件
GOOGLE_DRIVE --api-list

# 上传文件
GOOGLE_DRIVE --api-upload ./myfile.txt

# 下载文件
GOOGLE_DRIVE --api-download FILE_ID

# 删除文件
GOOGLE_DRIVE --api-delete FILE_ID
```

## 依赖要求

```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

## 环境变量

需要设置以下环境变量：
- `GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY`: 服务账户密钥文件的完整路径

## 注意事项

1. **服务账户权限**: 服务账户只能访问与其共享的文件和文件夹
2. **个人文件访问**: 如需访问个人Drive文件，请在Drive中将文件夹分享给服务账户邮箱
3. **Colab集成**: 在Colab中可以结合Drive挂载和API服务实现完整的远程控制
4. **安全性**: 请妥善保管服务账户密钥文件，不要将其提交到版本控制系统

## 错误排查

### 常见问题

1. **认证失败**
   - 检查服务账户密钥文件路径是否正确
   - 确认密钥文件格式为JSON且内容完整
   - 验证环境变量是否正确设置

2. **权限不足**
   - 确认服务账户在Google Cloud项目中有适当权限
   - 检查要访问的文件/文件夹是否已分享给服务账户

3. **API未启用**
   - 在Google Cloud Console中确认已启用Google Drive API
   - 检查项目配置是否正确 