# Google Drive Shell 完整设置指南

## 解决服务账户存储限制的方案

### 问题描述
服务账户默认没有存储配额，无法直接上传文件到Google Drive。错误信息：
```
Service Accounts do not have storage quota
```

### 解决方案
我们提供两种解决方案来突破这个限制：

## 方案一：共享驱动器 (Shared Drives) - 推荐

### 优势
- ✅ 完全解决存储限制问题
- ✅ 服务账户可以在共享驱动器中创建和管理文件
- ✅ 支持所有文件操作（创建、上传、删除）
- ✅ 适合团队协作

### 设置步骤

#### 1. 创建Google Cloud项目（如已完成可跳过）
1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用Google Drive API

#### 2. 创建服务账户（如已完成可跳过）
1. 在Google Cloud Console中，转到 **IAM & Admin > Service Accounts**
2. 点击 **Create Service Account**
3. 填写服务账户详情，点击 **Create and Continue**
4. 点击 **Keys > Add Key > Create New Key**
5. 选择 **JSON** 格式下载密钥文件

#### 3. 设置环境变量
```bash
export GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY="/path/to/your/service-account-key.json"
```

#### 4. 创建共享驱动器
运行我们的共享驱动器设置脚本：

```bash
cd GOOGLE_DRIVE_PROJ
python shared_drive_solution.py
```

这将：
- 自动创建名为 "GOOGLE_DRIVE_SHELL_WORKSPACE" 的共享驱动器
- 保存配置到 `GOOGLE_DRIVE_DATA/shared_drive_config.json`
- 测试文件上传功能

#### 5. 验证设置
```bash
# 测试echo命令创建文件
GDS echo "Hello Shared Drive!" > test.txt

# 应该成功创建文件而不是返回存储配额错误
```

## 方案二：用户委派 (Domain-wide Delegation)

### 优势
- ✅ 可以代表用户操作
- ✅ 访问用户的个人Drive存储
- ✅ 适合企业G Suite环境

### 限制
- ❌ 需要G Suite管理员权限
- ❌ 设置较复杂
- ❌ 仅适用于组织环境

### 设置步骤

#### 1. 启用域范围委派
1. 在Google Cloud Console中，转到 **IAM & Admin > Service Accounts**
2. 选择您的服务账户
3. 点击 **Show Advanced Settings**
4. 在 "Domain-wide delegation" 下，复制 Client ID
5. 点击 **View Google Workspace Admin Console**

#### 2. 在Admin Console中授权
1. 转到 **Security > Access and data control > API controls**
2. 点击 **Manage Domain Wide Delegation**
3. 点击 **Add new**
4. 粘贴服务账户的Client ID
5. 在OAuth Scopes中添加：
   ```
   https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/drive.file
   ```
6. 点击 **Authorize**

#### 3. 使用委派
在代码中指定要模拟的用户：
```python
# 在google_drive_api.py中修改
credentials = service_account.Credentials.from_service_account_file(
    self.key_path, scopes=SCOPES
).with_subject('user@yourdomain.com')  # 指定要模拟的用户
```

## 推荐配置

### 对于个人用户
使用 **方案一（共享驱动器）**：
- 创建个人工作区共享驱动器
- 简单易设置
- 无需管理员权限

### 对于企业用户
可选择：
- **方案一**：独立工作区，不依赖用户权限
- **方案二**：集成到现有用户环境

## 故障排除

### 常见错误

#### 1. "Insufficient Permission"
**解决方案**：确保服务账户有创建共享驱动器的权限
```bash
# 检查权限
python -c "
from GOOGLE_DRIVE_PROJ.shared_drive_solution import SharedDriveSolution
solution = SharedDriveSolution()
result = solution.list_shared_drives()
print(result)
"
```

#### 2. "Drive not found"
**解决方案**：重新运行共享驱动器设置
```bash
cd GOOGLE_DRIVE_PROJ
python shared_drive_solution.py
```

#### 3. "Service account key not found"
**解决方案**：检查环境变量和密钥文件路径
```bash
echo $GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY
ls -la "$GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY"
```

### 验证配置

#### 检查共享驱动器配置
```bash
cat GOOGLE_DRIVE_DATA/shared_drive_config.json
```

#### 测试文件操作
```bash
# 测试创建文件
GDS echo "Test content" > test.txt

# 测试Python执行
GDS python -c "print('Hello from shared drive!')"

# 测试列出文件
GDS ls
```

## 性能优化

### 批量操作
对于大量文件操作，考虑使用批处理请求：
```python
# 在shared_drive_solution.py中实现批量上传
def batch_upload_files(self, file_paths, drive_id):
    # 实现批量上传逻辑
    pass
```

### 缓存机制
实现文件ID和路径的本地缓存以提高性能。

## 安全考虑

### 密钥管理
- ✅ 将服务账户密钥文件存储在安全位置
- ✅ 设置适当的文件权限 (600)
- ✅ 不要将密钥文件提交到版本控制

### 权限控制
- ✅ 只授予必要的最小权限
- ✅ 定期审查和轮换服务账户密钥
- ✅ 监控API使用情况

## 下一步

设置完成后，您可以：

1. **使用所有shell命令**：
   ```bash
   GDS pwd
   GDS ls
   GDS mkdir projects
   GDS echo "Hello World" > hello.txt
   GDS cat hello.txt
   GDS python -c "print('Python works!')"
   ```

2. **集成到自动化流程**：
   ```bash
   RUN --show GDS "python -c 'import os; print(os.getcwd())'"
   ```

3. **扩展功能**：
   - 添加更多shell命令
   - 实现文件同步
   - 创建备份脚本

## 支持

如果遇到问题：
1. 检查[故障排除](#故障排除)部分
2. 验证所有设置步骤
3. 查看错误日志和API响应 