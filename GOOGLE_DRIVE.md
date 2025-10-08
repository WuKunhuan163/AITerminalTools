# GOOGLE_DRIVE - Google Drive 远程控制工具

## 概述

GOOGLE_DRIVE 是一个强大的 Google Drive 远程控制工具，支持通过命令行进行文件管理、上传下载、以及与 Google Colab 的集成。

## 🔧 GDS Shell 管理系统

### GDS vs GOOGLE_DRIVE --shell 的区别

**重要理解**: `GDS` 和 `GOOGLE_DRIVE --shell` 是不同的概念：

- **`GOOGLE_DRIVE --shell`**: 返回并进入默认shell（如果直接运行会进入交互模式）
- **`GDS`**: 对**当前活跃shell**进行操作的命令别名

### Shell 管理功能

`GDS` 代表一个完整的shell管理系统，支持：

- **多Shell环境**: 可以创建多个独立的shell会话
- **Shell切换**: 在不同shell之间自由切换（checkout）
- **Shell生命周期**: 创建、删除、查看所有shell
- **工作目录管理**: 每个shell维护自己的远端等效路径
- **会话隔离**: 不同shell相当于不同的工作环境

### Shell 管理命令

```bash
# Shell 会话管理
GOOGLE_DRIVE --create-remote-shell              # 创建新shell
GOOGLE_DRIVE --list-remote-shell                # 列出所有shell
GOOGLE_DRIVE --checkout-remote-shell <shell_id> # 切换到指定shell
GOOGLE_DRIVE --terminate-remote-shell <shell_id> # 终止指定shell

# 使用GDS操作当前活跃shell
GDS pwd                                         # 显示当前shell的路径
GDS ls                                          # 列出当前shell目录内容
GDS cd <path>                                   # 在当前shell中切换目录
```

### 工作流程示例

```bash
# 创建一个用于项目A的shell
GOOGLE_DRIVE --create-remote-shell
# 输出: 远程shell创建成功，Shell ID: abc123

# 在项目A的shell中工作
GDS cd project_a
GDS upload file1.txt
GDS ls

# 创建另一个用于项目B的shell
GOOGLE_DRIVE --create-remote-shell  
# 输出: 远程shell创建成功，Shell ID: def456

# 切换到项目B的shell
GOOGLE_DRIVE --checkout-remote-shell def456

# 在项目B的shell中工作
GDS cd project_b
GDS upload file2.txt

# 查看所有shell
GOOGLE_DRIVE --list-remote-shell

# 切换回项目A
GOOGLE_DRIVE --checkout-remote-shell abc123
GDS pwd  # 显示项目A的当前路径
```

### 🚀 Background 执行功能

GDS 支持后台执行命令，让你可以同时运行多个任务而不被阻塞：

#### Background 基本语法
```bash
# 启动后台任务
GDS --bg <command>           # 后台执行命令
```

#### Background 管理命令
```bash
# 启动后台任务
GDS --bg "python train.py"
GDS --bg "find . -name '*.py' | wc -l"

# 查看任务状态
GDS --bg --status <task_id>       # 查看特定任务状态

# 查看任务日志
GDS --bg --log <task_id>          # 查看任务输出日志

# 查看任务结果
GDS --bg --result <task_id>       # 查看任务最终结果
```

#### 使用示例
```bash
# 启动一个长时间运行的训练任务
GDS --bg "python train_model.py --epochs 100"
# 输出: Background task started with ID: 1726234567_1234

# 同时启动数据处理任务
GDS --bg "python process_data.py"
# 输出: Background task started with ID: 1726234580_5678

# 查看特定任务状态
GDS --bg --status 1726234567_1234
# 输出:
# Status: completed
# PID: 1726234567_1234 (finished)
# Command: "python train_model.py --epochs 100"
# Start time: 2025-10-06T10:57:45.849037
# End time: 2025-10-06T02:58:44.159887
# Log size: 40 bytes

# 查看训练任务的实时日志
GDS --bg --log 1726234567_1234

# 查看任务最终结果（包含完整输出）
GDS --bg --result 1726234567_1234
# 输出: Training completed successfully with 95% accuracy
```

#### Background 功能特点
- **非阻塞执行**: 后台任务不会阻塞当前终端，立即返回任务ID
- **状态追踪**: 使用 `--status` 查看任务运行状态和PID
- **日志管理**: 使用 `--log` 查看任务的实时输出日志
- **结果保存**: 使用 `--result` 查看任务完成后的完整输出
- **多任务支持**: 同时运行多个独立的后台任务
- **引号处理**: 完美支持复杂命令中的转义引号和特殊字符
- **管道支持**: 支持管道操作，已修复 broken pipe 错误
- **错误处理**: 完善的错误检测和报告机制

## 🤖 AI Agent 使用指南

### 文件编辑最佳实践

**重要提示**: 对于AI agents，推荐使用 `GDS edit` 功能进行文件编辑，而不是创建本地文件后上传替换的方式。

#### 推荐工作流程

```bash
# 1. 获取文件上下文
GDS grep "function_name" target_file.py    # 搜索相关内容
GDS read target_file.py 10 20             # 读取特定行范围

# 2. 基于上下文进行精确编辑
GDS edit target_file.py '[[[15, 18], "def improved_function():\n    return \"better implementation\""]]'

# 3. 验证编辑结果
GDS read target_file.py 10 25             # 检查修改后的内容
```

#### 避免的做法

```bash
# Error: 不推荐：创建本地文件 + 强制上传替换
echo "new content" > local_file.py
GDS upload --force local_file.py

# 推荐：直接编辑远程文件
GDS edit remote_file.py '[["old_content", "new_content"]]'
```

#### 编辑功能优势

1. **高效性**: 直接修改远程文件，无需下载-修改-上传循环
2. **精确性**: 支持多段同步替换，避免行号变化导致的错误
3. **安全性**: 支持预览模式和备份功能
4. **一致性**: 与Cursor IDE的编辑体验保持一致

#### 复杂编辑示例

```bash
# 混合模式编辑：行号替换 + 文本搜索替换
GDS edit complex_file.py '[
  [[1, 1], "#!/usr/bin/env python3"],
  ["import os", "import os\nimport sys"],
  ["DEBUG = True", "DEBUG = False"],
  [[50, 55], "# Refactored function\ndef new_implementation():\n    pass"]
]'

# 预览模式：查看修改结果而不保存
GDS edit --preview important_file.py '[["old_logic", "new_logic"]]'

# 备份模式：重要文件修改前创建备份
GDS edit --backup production_config.py '[["old_setting", "new_setting"]]'
```

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
- 📤 文件上传 (`upload`)
- 📥 文件下载 (`download`)
- 🔄 文件移动 (`mv`)
- ✏️ 文件编辑 (`edit`) - **支持多段同步替换**
- 🔍 路径解析支持

### 3. 高级功能
- 🐍 Python 代码执行
- 🔍 文件内容查看和搜索 (`cat`, `grep`, `read`, `find`)
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
| `--upload [--remove-local] FILE [PATH]` | 通过本地同步上传文件到Google Drive |
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

## EDIT 功能详解

### 概述
EDIT 功能提供用户友好的文件编辑能力，采用直观的命令行选项替代复杂的JSON格式。整个编辑流程包括：下载、编辑、重新上传，并与现有的缓存系统完全集成。

### ✨ 核心特性
- **用户友好语法**: 使用直观的命令行选项，无需复杂的JSON格式
- **多行内容支持**: 原生支持 `\n` 转义字符，轻松处理多行内容
- **多种编辑模式**: 支持内容替换、文本替换、行号编辑
- **预览功能**: 支持预览模式，查看修改结果而不实际保存
- **备份机制**: 可选择性创建备份文件
- **缓存集成**: 与现有下载/上传缓存系统完全集成
- **智能编码**: 自动处理 UTF-8 和 GBK 编码

### 语法格式

#### 基本语法
```bash
GDS edit [选项] <文件名>
```

#### 选项参数
- `--content, -c <内容>`: 直接设置文件内容
- `--replace, -r <旧文本> <新文本>`: 文本替换（可多次使用）
- `--line, -l <行号> <内容>`: 替换指定行
- `--insert, -i <行号> <内容>`: 在指定行后插入
- `--preview`: 预览模式，只显示修改结果不实际保存
- `--backup`: 创建备份文件（格式：filename.backup.YYYYMMDD_HHMMSS）

#### 替换规范格式

##### 1. 行号替换模式 (0-based, [a, b) 语法)
```json
[[[起始行号, 结束行号], "新内容"], [[起始行号, 结束行号], "新内容"]]
```

示例：
```bash
# 将第0行替换为新函数定义，第3行替换为函数调用 (0-based索引)
GDS edit main.py '[[[0, 1], "def greet():"], [[3, 4], "greet()"]]'
```

##### 2. 文本搜索替换模式
```json
[["旧文本", "新文本"], ["旧文本", "新文本"]]
```

示例：
```bash
# 替换配置项
GDS edit config.py '[["DEBUG = False", "DEBUG = True"], ["localhost", "0.0.0.0"]]'
```

##### 3. 混合模式
```json
[[[行号范围], "新内容"], ["搜索文本", "替换文本"]]
```

示例：
```bash
# 第1行添加shebang，搜索替换函数名
GDS edit app.py '[[[1, 1], "#!/usr/bin/env python3"], ["old_func", "new_func"]]'
```

### 工作原理

1. **参数解析**: 解析命令选项和替换规范
2. **文件下载**: 强制重新下载文件确保获取最新内容
3. **内容读取**: 智能处理文件编码（UTF-8/GBK）
4. **替换验证**: 验证行号范围和搜索文本是否存在
5. **同步替换**: 按倒序处理行替换，避免行号变化影响
6. **结果生成**: 生成详细的修改差异信息
7. **缓存更新**: 更新本地缓存文件
8. **文件上传**: 上传修改后的文件到远程

### 使用示例

#### 基础示例
```bash
# 修改Python函数
GDS edit hello.py '[[[1, 2], "def say_hello(name):"], [[3, 3], "    print(f\"Hello, {name}!\")"]]'

# 配置文件修改
GDS edit settings.json '[["\"debug\": false", "\"debug\": true"], ["\"port\": 8080", "\"port\": 3000"]]'
```

#### 预览模式
```bash
# 先预览修改结果
GDS edit --preview main.py '[[[5, 10], "# New implementation\ndef new_function():\n    pass"]]'
```

#### 备份模式
```bash
# 重要文件修改前创建备份
GDS edit --backup production.py '[["old_api_key", "new_api_key"]]'
```

#### 复杂编辑
```bash
# 多类型替换组合
GDS edit complex.py '[
  [[1, 1], "#!/usr/bin/env python3"],
  ["import os", "import os\nimport sys"],
  ["DEBUG = True", "DEBUG = False"],
  [[20, 25], "# Refactored function\ndef improved_function():\n    return \"better implementation\""]
]'
```

## 🐍 虚拟环境管理功能

### 概述
GDS Shell 提供了完整的虚拟环境管理功能，支持在远程 Google Colab 环境中创建、管理和使用 Python 虚拟环境。这个功能特别适用于需要隔离不同项目依赖的场景。

### ✨ 核心特性
- **多环境支持**: 可以创建和管理多个独立的虚拟环境
- **Shell 隔离**: 每个 Shell 会话可以独立激活不同的虚拟环境
- **自动 pip 集成**: pip 命令自动识别当前激活的虚拟环境
- **状态持久化**: 虚拟环境状态在 Shell 会话间保持
- **Google Drive 集成**: 虚拟环境存储在 Google Drive 中，支持跨设备访问

### 工作原理

#### 存储结构
```
REMOTE_ROOT/
├── .env/              # 虚拟环境根目录
│   ├── .tmp/          # 状态文件目录（隐藏）
│   │   └── current_venv_<shell_id>.txt  # 当前激活环境记录
│   ├── myproject/     # 虚拟环境目录
│   │   ├── env_info.txt        # 环境信息
│   │   └── <packages>/         # 安装的包
│   └── dataanalysis/  # 另一个虚拟环境
│       └── ...
```

#### 环境变量管理
- **激活时**: `PYTHONPATH=/env/python:<env_path>`
- **未激活时**: `PYTHONPATH=/env/python`
- **状态跟踪**: 通过隐藏的状态文件跟踪每个 Shell 的激活状态

### 命令参考

#### 虚拟环境管理
```bash
# 创建虚拟环境
GDS venv --create <env_name>

# 列出所有虚拟环境
GDS venv --list

# 激活虚拟环境
GDS venv --activate <env_name>

# 取消激活虚拟环境
GDS venv --deactivate

# 删除虚拟环境
GDS venv --delete <env_name>
```

#### 包管理
```bash
# 在激活的虚拟环境中安装包
GDS pip install <package_name>

# 在激活的虚拟环境中列出包
GDS pip list

# 在激活的虚拟环境中卸载包
GDS pip uninstall <package_name>

# 在系统环境中安装包（未激活虚拟环境时）
GDS pip install <package_name>
```

### 使用示例

#### 基础工作流程
```bash
# 1. 创建新的虚拟环境
GDS venv --create myproject
# 输出: Virtual environment 'myproject' created successfully

# 2. 查看所有环境
GDS venv --list
# 输出: 
# Virtual environments (1 total):
#   myproject

# 3. 激活环境
GDS venv --activate myproject
# 输出: Virtual environment 'myproject' activated successfully

# 4. 在虚拟环境中安装包
GDS pip install numpy pandas matplotlib
# 输出: pip install numpy pandas matplotlib executed successfully in environment 'myproject'

# 5. 查看当前环境状态
GDS venv --list
# 输出:
# Virtual environments (1 total):
# * myproject    # 星号表示当前激活的环境

# 6. 取消激活
GDS venv --deactivate
# 输出: Virtual environment deactivated

# 7. 删除环境（可选）
GDS venv --delete myproject
# 输出: Virtual environment 'myproject' deleted successfully
```

#### 智能依赖树分析 ⭐ **新功能**
```bash
GDS pip --show-deps tensorflow --depth=2
```
```
Analysis completed: 288 API calls, 493 packages analyzed in 29.40s

tensorflow (592.1MB→7487.7GB)
├─ numpy (20.3MB)
├─ protobuf (430.3KB)
├─ setuptools (1.3MB→14.8GB)
│   ├─ pytest (1.4MB→36.9GB)
│   ├─ wheel (0.1MB→36.9GB)
│   ├─ packaging (161.8KB)
│   └─ pip (1.8MB)
├─ grpcio (12.2MB→14.8MB)
│   └─ grpcio-tools (5.6MB→14.8MB)
└─ keras (1.3MB→569.2GB)
    ├─ numpy (20.3MB)
    ├─ h5py (4.7MB→25.0MB)
    └─ ml-dtypes (5.0MB→37.4GB)

Level 1: setuptools (1.3MB), grpcio (12.2MB), keras (1.3MB), protobuf (430.3KB), numpy (20.3MB)
Level 2: pytest (1.4MB), wheel (0.1MB), grpcio-tools (5.6MB), h5py (4.7MB), ml-dtypes (5.0MB)
```

**功能特性**:
- **多层依赖分析**: 支持 `--depth=1,2,3...` 参数控制分析深度
- **逻辑大小计算**: 显示包的物理大小和包含所有依赖的逻辑大小
- **智能API限制**: 自动限制分析1000个包，避免无限递归
- **并发分析**: 每秒40个API调用，快速获取依赖信息
- **层级汇总**: 按层级显示所有唯一依赖包，便于批量安装规划
- **已安装标记**: 显示 `[√]` 标记已安装的包
- **性能统计**: 显示API调用次数、分析包数和总时间

## Python版本管理详解 ⭐ **新功能**

### 概述

GDS现在支持类似pyenv的Python版本管理功能，允许在远端环境中安装和切换不同版本的Python。这个功能对于需要在不同Python版本下测试代码的开发者特别有用。

### 目录结构

Python版本管理使用以下目录结构：
```
REMOTE_ROOT/
└── .env/
    └── python/
        ├── 3.8.10/         # Python 3.8.10 安装目录
        ├── 3.9.18/         # Python 3.9.18 安装目录
        ├── 3.10.12/        # Python 3.10.12 安装目录
        ├── 3.11.7/         # Python 3.11.7 安装目录
        └── python_states.json  # Python版本状态文件
```

### 基本使用

#### 查看可用版本
```bash
# 查看所有可下载的Python版本
GDS pyenv --list-available
```
输出示例：
```
Available Python versions for download:
  3.8.10
  3.8.18
  3.9.18
  3.10.12
  3.11.7
  3.12.1
```

#### 安装Python版本
```bash
# 安装Python 3.10.12
GDS pyenv --install 3.10.12
```

**注意**: Python版本安装需要在远端进行源码编译，可能需要较长时间（10-30分钟）。

#### 查看已安装版本
```bash
# 查看所有已安装的Python版本
GDS pyenv --list
```
输出示例：
```
Installed Python versions:
  3.9.18
* 3.10.12    # 星号表示当前激活版本
  3.11.7
```

#### 切换Python版本
```bash
# 设置全局默认Python版本
GDS pyenv --global 3.10.12

# 设置当前shell的Python版本（优先级更高）
GDS pyenv --local 3.11.7
```

#### 查看当前版本
```bash
# 查看当前使用的Python版本
GDS pyenv --version
```

## UPLOAD 功能详解

### 概述
UPLOAD 功能通过 Google Drive Desktop 实现文件上传，支持本地文件同步到远程 Google Drive。

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
edit [--preview] [--backup] <file> '<spec>' # 多段文本同sync替换编辑
upload [--target-dir TARGET] <files...>  # 上传文件到Google Drive (默认：当前目录)
```

### 文件内容
```bash
cat <file>                  # 显示文件内容
echo <text>                 # 显示文本
echo <text> > <file>        # 创建文件并写入文本
echo -e <text> > <file>     # 创建文件并处理转义字符（\n, \t等）
grep <pattern> <file>       # 在文件中搜索模式
read <file> [start end]     # 读取文件内容（带行号）
read [--force] <file>       # 强制重新下载并读取文件内容
find [path] -name [pattern] # 查找匹配模式的文件和目录
```

**ECHO 命令详细语法**:
```bash
# 基本用法
echo "Hello World"                    # 显示文本
echo "Hello World" > file.txt         # 创建文件并写入文本

# 处理转义字符
echo -e "Line1\nLine2\nLine3"        # 显示多行文本（处理\n）
echo -e "Tab\tSeparated\tText"       # 处理制表符（\t）

# JSON文件创建（推荐语法）
echo '{"name": "test", "value": 123}' > config.json    # 单引号包围，无需转义
echo '{"debug": true, "items": [1,2,3]}' > settings.json

# Python脚本创建
echo -e 'import json\nprint(f"Hello Python")' > script.py

# 复杂内容创建
echo -e 'Line 1\nLine 2 with "quotes"\nLine 3' > multiline.txt
```

**READ 命令详细语法**:
```bash
# 基本用法
read filename               # 显示整个文件（带行号）
read filename 5             # 从第5行开始显示到文件末尾
read filename 2 8           # 显示第2行到第8行（包含第8行）[a, b]包含语法
read --force filename       # 强制重新下载，忽略缓存

# 多范围读取（JSON格式）
read filename "[[0, 2], [5, 7]]"  # 显示第0-2行和第5-7行

# 注意事项
# - 行号从0开始（0-based索引）
# - [start, end] 使用包含语法，end行会被显示
# - --force 选项会跳过缓存，从远端重新下载最新版本
```

**EDIT 命令详细语法**:
```bash
# 直接内容模式 - 设置文件内容
edit file.txt --content "Hello World"                    # 简单内容
edit file.txt -c "Line 1\nLine 2\nLine 3"               # 多行内容

# 文本替换模式 - 替换文本内容  
edit file.py --replace "old_text" "new_text"            # 单个替换
edit file.py -r "hello" "hi" -r "world" "earth"         # 多个替换
edit file.py -r "import os" "import os\nimport sys"     # 多行替换

# 行号编辑模式 - 按行号操作
edit file.py --line 5 "new line content"                # 替换第5行
edit file.py -l 3 "# This is line 3"                    # 替换第3行
edit file.py --insert 2 "# Inserted after line 2"      # 在第2行后插入
edit file.py -i 1 "import sys"                          # 在第1行后插入

# 预览和备份
edit --preview file.py -r "old" "new"                   # 预览修改结果
edit --backup file.py -c "new content"                  # 创建备份后编辑

# 组合使用
edit file.py -r "TODO" "DONE" -l 1 "# Updated file" --backup
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

### 虚拟环境管理
```bash
venv --create <env_name>    # 创建虚拟环境
venv --delete <env_name>    # 删除虚拟环境
venv --activate <env_name>  # 激活虚拟环境（设置PYTHONPATH）
venv --deactivate          # 取消激活虚拟环境（清除PYTHONPATH）
venv --list                # 列出所有虚拟环境
pip <command> [options]     # pip包管理器（自动识别激活的虚拟环境）
pip --show-deps <package> [--depth=N]  # 智能依赖树分析（新功能）
```

### Python版本管理 ⭐ **新功能**
```bash
pyenv --install <version>       # 安装指定Python版本（如 3.9.18, 3.10.12）
pyenv --uninstall <version>     # 卸载指定Python版本
pyenv --list                    # 列出所有已安装的Python版本
pyenv --list-available          # 列出所有可下载的Python版本
pyenv --global [version]        # 设置/查看全局默认Python版本
pyenv --local [version]         # 设置/查看当前shell的Python版本
pyenv --version                 # 显示当前使用的Python版本
pyenv --versions                # 显示所有已安装版本及当前版本标记
```

### 代码质量检查 ⭐ **新功能**
```bash
linter [--language LANG] <file>  # 多语言语法和代码风格检查
```

**支持的语言**:
- **Python**: flake8, pylint, pycodestyle
- **JavaScript/TypeScript**: eslint, jshint
- **Java**: javac, checkstyle
- **C/C++**: gcc, cppcheck, clang-tidy
- **Go**: gofmt
- **JSON**: jsonlint, python内置JSON验证
- **YAML**: yamllint
- **Shell**: shellcheck

**功能特性**:
- **自动语言检测**: 根据文件扩展名自动识别语言
- **多linter支持**: 自动检测并使用可用的linter工具
- **详细报告**: 提供错误、警告和信息级别的反馈
- **语法验证**: 检查基本语法错误
- **代码风格**: 检查代码风格和最佳实践
- **集成编辑**: 在edit命令中自动运行linter检查

### 远程命令执行 ⭐ **新功能**
```bash
GOOGLE_DRIVE --shell "command"  # 执行远程命令
```

**功能特性**:
- **完整输出保留**: 支持多行输出、特殊字符、stdout/stderr分离
- **错误处理**: 完整显示语法错误、运行时错误和traceback信息  
- **复杂脚本支持**: 可执行Python脚本、shell脚本等复杂程序
- **JSON格式化**: 内部使用`\n`转义保持输出格式的同时确保数据完整性
- **简化流程**: 无需额外清理步骤，减少用户交互
- **超时处理**: 60秒等待超时后提供用户手动输入fallback机制
- **长期运行支持**: 适用于http-server等需要持续运行的服务

## 使用示例

### Upload 文件上传

**新语法**:
```bash
# 上传单个文件到当前目录
GDS upload file.txt

# 上传多个文件到当前目录  
GDS upload file1.txt file2.txt file3.txt

# 上传文件到指定目录
GDS upload --target-dir docs file.txt

# 上传多个文件到指定目录
GDS upload --target-dir backup file1.txt file2.txt file3.txt

# 上传到嵌套目录（自动创建）
GDS upload --target-dir projects/myproject file.txt
```

**功能特性**:
- **即时进度反馈**: "⏳ Waiting for upload" 立即显示，快速点显示
- **自动目录创建**: 目标目录不存在时自动创建
- **智能验证**: 使用ls-based validation确保准确的成功计数
- **清晰语法**: 所有参数都是文件，除非使用 `--target-dir`
- **双阶段进度**: "⏳ Waiting for upload" → "⏳ Validating the result"

### 基础操作
```bash
# 进入交互式 Shell
GOOGLE_DRIVE --shell

# 查看当前位置
GDS pwd

# 列出文件
GDS ls

# 创建目录
GDS mkdir test_folder

# 切换目录
GDS cd test_folder

# 返回上级目录
GDS cd ..
```

### 文件管理
```bash
# 上传文件到当前目录
GDS upload file.txt

# 上传文件到指定目录
GDS upload file.txt subfolder/

# 强制覆盖上传（替换已存在的文件）
GDS upload --force updated_file.txt

# 移动文件
GDS mv old_name.txt new_name.txt

# 删除文件
GDS rm unwanted_file.txt

# 递归删除目录
GDS rm -rf old_folder
```

### 文件内容操作
```bash
# 查看文件内容
GDS cat document.txt

# 搜索文件内容
GDS grep "pattern" document.txt

# 读取文件指定行
GDS read document.txt 1 10

# 查找文件
GDS find . -name "*.py"

# 下载文件到本地
GDS download remote_file.txt ~/Downloads/

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

### 文件搜索
```bash
# 查找所有 .txt 文件
GDS find . -name "*.txt"

# 大小写不敏感查找
GDS find . -iname "*.PDF"

# 查找包含特定字符的文件
GDS find . -name "*report*"

# 只查找文件（不包括目录）
GDS find . -type f -name "*.py"

# 只查找目录
GDS find . -type d -name "*test*"

# 读取文件内容（带行号）
GDS read document.txt

# 读取指定行数范围
GDS read document.txt 0 10

# 读取多个不连续范围
GDS read document.txt "[[0, 5], [10, 15]]"
```

### 文件编辑
```bash
# 基本编辑 - 行号替换 (0-based索引)
GDS edit main.py '[[[0, 1], "def greet():"], [[3, 4], "greet()"]]'

# 文本搜索替换
GDS edit config.py '[["DEBUG = False", "DEBUG = True"], ["localhost", "0.0.0.0"]]'

# 混合模式编辑
GDS edit app.py '[[[1, 1], "#!/usr/bin/env python3"], ["print(\"old\")", "print(\"new\")"]]'

# 预览模式 - 只显示修改结果不保存
GDS edit --preview main.py '[[[1, 2], "def greet():"]]'

# 创建备份后编辑
GDS edit --backup important.py '[["old_function", "new_function"]]'

# 复杂编辑示例
GDS edit server.py '[
  [[1, 3], "# Updated server configuration"],
  ["port = 8000", "port = 3000"],
  ["debug = True", "debug = False"],
  [[50, 52], "# New error handling code\ntry:\n    process_request()"]
]'
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