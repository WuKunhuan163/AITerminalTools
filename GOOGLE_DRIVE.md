# GOOGLE_DRIVE - Google Drive 远程控制工具

## 概述

GOOGLE_DRIVE 是一个强大的 Google Drive 远程控制工具，支持通过命令行进行文件管理、上传下载、以及与 Google Colab 的集成。

## ✅ 最新修复 (2024)

### Google Drive Desktop 自动启动
- **问题修复**: Upload功能现在会自动启动Google Drive Desktop，无需用户手动选择
- **改进**: 简化了启动流程，提高用户体验
- **状态检测**: 自动检测Google Drive Desktop运行状态

### Upload检测优化
- **调试增强**: 当upload检测超时时，自动显示`GDS ls ~`输出进行调试
- **问题诊断**: 帮助快速定位文件同步问题
- **超时处理**: 改进了60秒超时机制的错误处理

## 主要功能

### 1. 基础功能
- 🌐 在浏览器中打开 Google Drive
- 🔧 Google Drive API 设置向导
- 📂 远程文件夹管理
- 🚀 交互式 Shell 模式
- 🔄 自动启动 Google Drive Desktop

### 2. 文件操作
- 📁 目录导航 (`pwd`, `ls`, `cd`, `mkdir`)
- 🗑️ 文件删除 (`rm`, `rm -rf`)
- 📤 文件上传 (`upload`) - **已优化检测机制**
- 📥 文件下载 (`download`)
- 🔄 文件移动 (`mv`)
- 🔍 路径解析支持

### 3. 高级功能
- 🐍 Python 代码执行
- 🔍 文件内容查看和搜索 (`cat`, `grep`)
- 📝 文本文件创建 (`echo`)
- 🔗 与 Google Colab 集成
- 🛠️ 调试和诊断工具

## 安装和配置

### 前置要求
```bash
pip install google-api-python-client google-auth google-auth-oauthlib google-auth-httplib2
```

### API 设置
运行设置向导：
```bash
GOOGLE_DRIVE --console-setup
```

设置向导将指导您完成：
1. 创建 Google Cloud 项目
2. 启用 Google Drive API
3. 创建服务账户
4. 下载并配置密钥文件

## 使用方法

### 基本语法
```bash
GOOGLE_DRIVE [url] [options]
GDS [command]  # Shell 模式别名
```

### 命令行选项

| 选项 | 描述 |
|------|------|
| `-my` | 打开 My Drive |
| `--console-setup` | 启动 API 设置向导 |
| `--shell [COMMAND]` | 进入交互式 Shell 或执行指定命令 (别名: GDS) |
| `--upload FILE [PATH]` | 通过本地同步上传文件到Google Drive |
| `--create-remote-shell` | 创建新的远程 Shell 会话 |
| `--list-remote-shell` | 列出所有远程 Shell 会话 |
| `--checkout-remote-shell ID` | 切换到指定 Shell |
| `--terminate-remote-shell ID` | 终止指定 Shell |
| `--desktop --status` | 检查 Google Drive Desktop 应用状态 |
| `--desktop --shutdown` | 关闭 Google Drive Desktop 应用 |
| `--desktop --launch` | 启动 Google Drive Desktop 应用 |
| `--desktop --restart` | 重启 Google Drive Desktop 应用 |
| `--desktop --set-local-sync-dir` | 设置本地同步目录路径 |
| `--desktop --set-global-sync-dir` | 设置全局同步目录 (Drive文件夹) |
| `--help, -h` | 显示帮助信息 |

## UPLOAD 功能详解

### 概述
UPLOAD 功能通过 Google Drive Desktop 实现文件上传，支持本地文件同步到远程 Google Drive。

### ✅ 最新改进
- **自动启动**: 自动检测并启动Google Drive Desktop，无需手动干预
- **调试增强**: 检测失败时自动显示`GDS ls ~`输出，便于问题诊断
- **超时优化**: 改进60秒超时机制，提供更详细的错误信息
- **路径解析**: 支持基本路径解析功能

### 工作原理
1. **环境检查**: 自动检测并启动Google Drive Desktop
2. **文件移动**: 将本地文件移动到 `LOCAL_EQUIVALENT` 目录
3. **同步等待**: 等待 Google Drive Desktop 同步文件到云端（带调试输出）
4. **远端命令**: 生成并显示远端终端命令
5. **结果验证**: 验证文件是否成功上传到目标位置

### 配置参数
```python
LOCAL_EQUIVALENT = "/Users/wukunhuan/Applications/Google Drive"
DRIVE_EQUIVALENT = "/content/drive/Othercomputers/我的 MacBook Air/Google Drive"
REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
```

### 使用方式

#### 1. Shell 模式上传
```bash
# 上传到当前目录
GOOGLE_DRIVE --shell upload file.txt

# 上传多个文件
GOOGLE_DRIVE --shell upload file1.txt file2.txt

# 上传到指定目录
GOOGLE_DRIVE --shell upload file.txt subfolder
```

#### 2. 直接命令上传
```bash
# 上传到 REMOTE_ROOT
GOOGLE_DRIVE --upload file.txt

# 上传到指定子目录
GOOGLE_DRIVE --upload file.txt documents

# 上传到绝对路径
GOOGLE_DRIVE --upload file.txt /content/drive/MyDrive/Projects
```

### 路径解析规则

| 目标路径 | 解析结果 |
|----------|----------|
| `.` 或空 | 当前 Shell 位置（默认为 REMOTE_ROOT） |
| `subfolder` | `REMOTE_ROOT/subfolder` |
| `/absolute/path` | 绝对路径 |

### 生成的远端命令示例

#### 上传到 REMOTE_ROOT
```bash
mv "/content/drive/Othercomputers/我的 MacBook Air/Google Drive/file.txt" "/content/drive/MyDrive/REMOTE_ROOT/file.txt"
```

#### 上传到子目录
```bash
mv "/content/drive/Othercomputers/我的 MacBook Air/Google Drive/file.txt" "/content/drive/MyDrive/REMOTE_ROOT/documents/file.txt"
```

#### 多文件上传
```bash
mv "/content/drive/Othercomputers/我的 MacBook Air/Google Drive/file1.txt" "/content/drive/MyDrive/REMOTE_ROOT/file1.txt" && mv "/content/drive/Othercomputers/我的 MacBook Air/Google Drive/file2.txt" "/content/drive/MyDrive/REMOTE_ROOT/file2.txt"
```

## Shell 命令参考

### 导航命令
```bash
pwd                         # 显示当前目录
ls [path] [--detailed] [-R] # 列出目录内容 (递归使用 -R)
cd <path>                   # 切换目录
```

### 文件操作
```bash
mkdir [-p] <dir>            # 创建目录 (递归使用 -p)
rm <file>                   # 删除文件
rm -rf <dir>                # 递归删除目录
mv <source> <dest>          # 移动/重命名文件或文件夹
upload <files...> [target]  # 上传文件到Google Drive
```

### 文件内容
```bash
cat <file>                  # 显示文件内容
echo <text>                 # 显示文本
echo <text> > <file>        # 创建文件并写入文本
grep <pattern> <file>       # 在文件中搜索模式
```

### 下载功能
```bash
download [--force] <file> [path] # 下载文件到本地 (带缓存)
```

### Python 执行
```bash
python <file>               # 执行Python文件
python -c '<code>'          # 执行Python代码
```

## 使用示例

### 基础操作
```bash
# 进入交互式 Shell
GOOGLE_DRIVE --shell

# 查看当前位置
GDS pwd

# 列出文件
GDS ls

# 创建目录
GDS mkdir projects

# 切换目录
GDS cd projects
```

### 文件上传
```bash
# 上传单个文件到当前目录
GDS upload ~/Documents/report.pdf

# 上传多个文件到指定目录
GDS upload file1.txt file2.txt documents

# 直接命令上传
GOOGLE_DRIVE --upload ~/Documents/presentation.pptx presentations
```

### 文件下载
```bash
# 下载文件
GDS download report.pdf

# 批量下载
GDS download-all *.txt
```

### Python 代码执行
```bash
# 执行 Python 文件
GDS python analysis.py

# 执行 Python 代码
GDS python -c "print('Hello from Google Drive!')"
```

## 错误处理

### 常见问题

1. **API 服务未初始化**
   - 运行 `GOOGLE_DRIVE --console-setup` 设置 API

2. **网络连接失败**
   - 检查网络连接
   - 确认 Google Drive 可访问

3. **文件同步超时**
   - 检查 Google Drive Desktop 是否运行
   - 确认同步目录配置正确

4. **文件移动失败**
   - 检查源文件是否存在
   - 确认 LOCAL_EQUIVALENT 目录存在

### 调试模式
当 API 服务未初始化时，工具会进入模拟模式，仍可测试文件移动和命令生成功能。

## 高级配置

### 自定义路径
可以在代码中修改以下路径配置：
```python
LOCAL_EQUIVALENT = "/Users/username/Applications/Google Drive"
DRIVE_EQUIVALENT = "/content/drive/Othercomputers/MacBook/Google Drive"
REMOTE_ROOT = "/content/drive/MyDrive/REMOTE_ROOT"
```

### Shell 会话管理
```bash
# 创建新会话
GOOGLE_DRIVE --create-remote-shell

# 列出会话
GOOGLE_DRIVE --list-remote-shell

# 切换会话
GOOGLE_DRIVE --checkout-remote-shell <shell_id>

# 终止会话
GOOGLE_DRIVE --terminate-remote-shell <shell_id>
```

## 集成示例

### 与 Google Colab 配合使用
1. 在本地使用 UPLOAD 功能上传文件
2. 在 Colab 中执行生成的远端命令
3. 使用 Colab 处理上传的文件
4. 通过 download 功能获取处理结果

### 批处理脚本
```bash
#!/bin/bash
# 批量上传项目文件
GOOGLE_DRIVE --upload src/main.py code/
GOOGLE_DRIVE --upload data/dataset.csv data/
GOOGLE_DRIVE --upload docs/readme.md docs/
```

## 版本信息

- 当前版本：2.0
- 最后更新：2025-07-23
- 主要功能：UPLOAD 文件同步上传

## 许可证

本工具遵循 MIT 许可证。

---

**注意**: 使用本工具前请确保已正确配置 Google Drive API 和 Google Drive Desktop。 