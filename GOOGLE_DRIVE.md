# GOOGLE_DRIVE - Google Drive 远程控制工具

## 概述

GOOGLE_DRIVE 是一个强大的 Google Drive 远程控制工具，支持通过命令行进行文件管理、上传下载、以及与 Google Colab 的集成。

## ✅ 最新修复 (2024)

### Google Drive Desktop 自动启动
- **问题修复**: Upload功能现在会自动启动Google Drive Desktop，无需用户手动选择
- **改进**: 简化了启动流程，提高用户体验
- **状态检测**: 自动检测Google Drive Desktop运行状态

### EDIT 功能全新发布 ✅ 已修复
- **多段同步替换**: 支持行号替换和文本搜索替换的混合编辑
- **0-based 索引**: 行号使用 [a, b) 语法，与 Python 和 read 命令对齐  
- **预览模式**: `--preview` 选项查看修改结果而不保存
- **备份功能**: `--backup` 选项创建修改前的备份文件
- **JSON解析修复**: 解决了shlex分割JSON字符串导致的解析失败问题
- **路径重复修复**: 修复了多文件上传中文件名重复添加的路径错误

### Upload 功能优化
- **文件名保持**: 修复了上传时文件名被错误重命名的问题
- **本地文件保护**: 改用 `cp` 替代 `mv`，保护本地文件不被意外删除
- **--remove-local 选项**: 新增选项，成功上传后可选择性删除本地文件
- **智能路径判断**: 通过文件扩展名自动区分文件和文件夹路径

### Upload检测优化
- **调试增强**: 当upload检测超时时，自动显示详细的错误诊断信息
- **问题诊断**: 包括源文件检查、目标路径检查、权限检查等
- **超时处理**: 改进了60秒超时机制的错误处理

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
# 输出: ✅ 远程shell创建成功，Shell ID: abc123

# 在项目A的shell中工作
GDS cd project_a
GDS upload file1.txt
GDS ls

# 创建另一个用于项目B的shell
GOOGLE_DRIVE --create-remote-shell  
# 输出: ✅ 远程shell创建成功，Shell ID: def456

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
# ❌ 不推荐：创建本地文件 + 强制上传替换
echo "new content" > local_file.py
GDS upload --force local_file.py

# ✅ 推荐：直接编辑远程文件
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
- 📤 文件上传 (`upload`) - **已优化检测机制**
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
EDIT 功能提供强大的文件编辑能力，支持多段文本同步替换，类似 Cursor 的 file_edit 工具。整个编辑流程包括：下载、编辑、重新上传，并与现有的缓存系统完全集成。

### ✨ 核心特性
- **多段同步替换**: 支持同时替换多个文本段，避免行号变化导致的替换错误
- **多种替换模式**: 支持行号替换、文本搜索替换、混合模式
- **预览功能**: 支持预览模式，查看修改结果而不实际保存
- **备份机制**: 可选择性创建备份文件
- **缓存集成**: 与现有下载/上传缓存系统完全集成
- **智能编码**: 自动处理 UTF-8 和 GBK 编码

### 语法格式

#### 基本语法
```bash
GDS edit [选项] <文件名> '<替换规范>'
```

#### 选项参数
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

### 输出格式

#### 预览模式输出
```
📝 预览模式 - 文件: main.py
原始行数: 10, 修改后行数: 8
应用替换: 2 个

🔄 修改摘要:
  • Lines 1-2: replaced
  • Text 'main()...' replaced

📄 修改后内容预览:
==================================================
def greet():
    print('Hello! ')
greet()
==================================================
```

#### 正常编辑输出
```
文件 main.py 编辑完成，应用了 2 个替换操作

🔄 修改摘要:
  • Lines 1-2: replaced
  • Text 'main()...' replaced

💾 备份文件已创建: main.py.backup.20250123_143022
```

### 错误处理

常见错误和解决方案：

1. **行号范围错误**
   ```
   行号范围错误: [1, 15]，文件共10行
   ```
   - 检查文件实际行数，调整行号范围

2. **文本未找到**
   ```
   未找到要替换的文本: old_function...
   ```
   - 确认搜索文本在文件中存在，注意大小写和空格

3. **JSON格式错误**
   ```
   替换规范JSON解析失败: Expecting ',' delimiter
   ```
   - 检查JSON格式，确保引号、括号匹配

4. **编码问题**
   ```
   文件编码不支持，请确保文件为UTF-8或GBK编码
   ```
   - 转换文件编码为UTF-8或GBK

### 最佳实践

1. **使用预览模式**: 复杂修改前先使用 `--preview` 查看结果
2. **创建备份**: 重要文件修改时使用 `--backup` 选项
3. **分步编辑**: 复杂修改可分解为多个简单的编辑操作
4. **验证结果**: 编辑后使用 `cat` 或 `read` 命令验证修改结果
5. **JSON转义**: 替换内容包含特殊字符时注意JSON转义

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
edit [--preview] [--backup] <file> '<spec>' # 多段文本同sync替换编辑
upload [--force] <files...> [target]  # 上传文件到Google Drive (--force强制覆盖)
```

### 文件内容
```bash
cat <file>                  # 显示文件内容
echo <text>                 # 显示文本
echo <text> > <file>        # 创建文件并写入文本
grep <pattern> <file>       # 在文件中搜索模式
read <file> [start end]     # 读取文件内容（带行号）
find [path] -name [pattern] # 查找匹配模式的文件和目录```

### 下载功能
```bash
download [--force] <file> [path] # 下载文件到本地 (带缓存)
```

### Python 执行
```bash
python <file>               # 执行Python文件
python -c '<code>'          # 执行Python代码
```

### 远程命令执行 ⭐ **新功能**
```bash
GOOGLE_DRIVE --shell "command"  # 执行远程命令
```

**功能特性**:
- ✅ **完整输出保留**: 支持多行输出、特殊字符、stdout/stderr分离
- ✅ **错误处理**: 完整显示语法错误、运行时错误和traceback信息  
- ✅ **复杂脚本支持**: 可执行Python脚本、shell脚本等复杂程序
- ✅ **JSON格式化**: 内部使用`\n`转义保持输出格式的同时确保数据完整性
- ✅ **简化流程**: 无需额外清理步骤，减少用户交互
- ✅ **超时处理**: 60秒等待超时后提供用户手动输入fallback机制
- ✅ **长期运行支持**: 适用于http-server等需要持续运行的服务

**使用示例**:
```bash
# 基本命令
GOOGLE_DRIVE --shell "whoami"
GOOGLE_DRIVE --shell "pwd && ls -la"

# 执行Python脚本
GOOGLE_DRIVE --shell "python3 my_script.py"

# 复杂命令组合
GOOGLE_DRIVE --shell "cd /path && python3 -c 'print(\"Hello World\")'"

# 长期运行服务（会触发超时fallback）
GOOGLE_DRIVE --shell "python3 -m http.server 8000"
```

**输出效果**:
- 保留原始多行格式
- 正确处理特殊字符（引号、反斜杠等）
- 分别显示stdout和stderr内容
- 完整的错误信息和调试支持

**超时处理机制**:
当命令执行超过60秒未生成结果文件时（如http-server等长期运行服务），系统会：
1. 显示超时提示和可能的原因
2. 提供用户手动输入选项
3. 支持多行输入，按Ctrl+D结束
4. 支持Ctrl+C中断和重新输入
5. 可选择跳过输入（直接按Enter）

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
``````

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