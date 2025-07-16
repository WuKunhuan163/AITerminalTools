# USERINPUT.py - User Input Script for Cursor AI

## 概述

`USERINPUT.py` 是一个专门为 Cursor AI 工作流程设计的用户输入脚本。它可以作为独立脚本运行，也可以作为接口在 RUN 环境中使用，支持唯一标识符系统来区分不同的执行实例。

## 主要特性

### 1. 双重运行模式
- **独立模式**: 直接执行，显示简单的 GUI 界面并在终端获取输入
- **RUN 接口模式**: 通过 `RUN_IDENTIFIER` 环境变量识别，将输入写入指定的 JSON 文件

### 2. 唯一标识符系统
- 支持通过 `RUN_IDENTIFIER` 环境变量区分不同的 RUN 执行
- 自动生成基于时间戳、随机数和进程ID的唯一标识符
- 向后兼容旧的 `RUN_OUTPUT_FILE` 环境变量

### 3. 项目信息显示
- 自动检测项目名称和目录结构
- 显示当前工作目录、项目根目录信息
- 在 RUN 模式下显示运行标识符

## 使用方法

### 基本用法

```bash
# 独立运行
python3 USERINPUT.py

# 通过 RUN 脚本调用
RUN USERINPUT

# 直接执行（如果有可执行权限）
./USERINPUT.py
```

### 命令行参数

```bash
# 生成新的唯一标识符
python3 USERINPUT.py --generate-id

# 设置标识符并运行
python3 USERINPUT.py --set-identifier <identifier>

# 设置标识符和输出文件
python3 USERINPUT.py --set-identifier <identifier> <output_file>
```

### 环境变量

- `RUN_IDENTIFIER`: 运行标识符（优先级最高）
- `RUN_OUTPUT_FILE`: 输出文件路径（向后兼容）

## 运行模式详解

### 独立模式

当没有设置 `RUN_IDENTIFIER` 或 `RUN_OUTPUT_FILE` 环境变量时：

1. 显示简单的 Tkinter GUI 界面（如果可用）
2. 显示项目信息和提示头部
3. 在终端中获取多行输入（Ctrl+D 结束）
4. 清屏并输出结果，附加任务完成提示

### RUN 接口模式

当设置了 `RUN_IDENTIFIER` 环境变量时：

1. 跳过 GUI 界面显示
2. 直接在终端获取输入
3. 将输入写入指定的 JSON 文件
4. JSON 文件包含运行标识符和其他元数据

## JSON 输出格式

```json
{
  "success": true,
  "type": "user_input",
  "run_identifier": "abc123def456",
  "user_input": "用户输入的内容",
  "message": "User input received successfully"
}
```

## 标识符生成算法

```python
def generate_run_identifier():
    timestamp = str(time.time())
    random_num = str(random.randint(100000, 999999))
    combined = f"{timestamp}_{random_num}_{os.getpid()}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]
```

## 与 RUN 系统的集成

### RUN 脚本调用流程

1. `RUN USERINPUT` 执行时，RUN 脚本自动：
   - 生成唯一的 `RUN_IDENTIFIER`
   - 设置 `RUN_OUTPUT_FILE` 环境变量
   - 调用 `USERINPUT.py`

2. `USERINPUT.py` 检测到 RUN 环境后：
   - 使用提供的标识符
   - 将输入写入指定的 JSON 文件
   - 确保输出目录存在

### 多实例隔离

通过唯一标识符系统，多个 RUN 实例可以同时执行而不会相互干扰：

```bash
# 实例1
RUN USERINPUT  # 生成标识符: a1b2c3d4e5f6g7h8

# 实例2（同时运行）
RUN USERINPUT  # 生成标识符: x9y8z7w6v5u4t3s2
```

## 错误处理

### 常见错误情况

1. **JSON 文件写入失败**: 显示错误信息并输出到 stdout
2. **GUI 界面创建失败**: 自动回退到纯终端模式
3. **用户中断输入**: Ctrl+C 返回 "stop"
4. **空输入**: 自动转换为 "stop"

### 调试信息

在 RUN 模式下，脚本会显示：
- 当前工作目录
- 项目根目录
- 运行标识符
- 输出文件路径

## 向后兼容性

脚本完全向后兼容旧的 `RUN_OUTPUT_FILE` 系统：

1. 如果只设置了 `RUN_OUTPUT_FILE`，会从文件名提取标识符
2. 如果无法提取，会自动生成新的标识符
3. 保持原有的 JSON 输出格式

## 最佳实践

### 在脚本中使用

```python
# 导入函数
from USERINPUT import generate_run_identifier, get_run_context

# 生成标识符
identifier = generate_run_identifier()

# 获取运行上下文
context = get_run_context()
if context['in_run_context']:
    print(f"Running in RUN mode with ID: {context['identifier']}")
```

### 与其他工具集成

```bash
# 在其他脚本中使用
export RUN_IDENTIFIER=$(python3 USERINPUT.py --generate-id)
export RUN_OUTPUT_FILE="output/run_${RUN_IDENTIFIER}.json"

# 调用 USERINPUT
python3 USERINPUT.py
```

## 故障排除

### 常见问题

1. **GUI 界面不显示**: 检查是否安装了 Tkinter
2. **权限错误**: 确保输出目录有写入权限
3. **编码问题**: 所有文件使用 UTF-8 编码

### 调试模式

```bash
# 查看生成的标识符
python3 USERINPUT.py --generate-id

# 测试特定标识符
python3 USERINPUT.py --set-identifier test123
```

## 更新日志

### v2.0 (当前版本)
- 添加唯一标识符系统
- 支持命令行参数
- 改进的运行上下文检测
- 向后兼容性支持

### v1.0 (原始版本)
- 基本的用户输入功能
- 简单的 RUN_OUTPUT_FILE 支持
- GUI 界面显示 