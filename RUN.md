# RUN 通用命令包装器

RUN 是一个通用命令包装器，可以将任何命令包装为返回JSON结果的形式，使得命令可以像函数一样有返回值。

## 功能特点

- **通用包装**: 支持包装任何存在的命令
- **JSON返回值**: 所有命令都返回结构化的JSON结果
- **程序化调用**: 可以通过 subprocess.run() 等方式调用
- **错误处理**: 完整的错误信息和状态报告
- **唯一文件名**: 使用SHA256哈希避免文件名冲突
- **执行时间**: 记录命令执行时间
- **输出保存**: 结果保存到 `~/.local/bin/RUN_DATA/` 目录
- **终端显示**: 支持 `--show` 标志在终端显示结果

## 使用方法

### 1. 基本语法

```bash
RUN [--show] <command> [args...]
```

### 2. 选项

- `--show`: 在终端显示输出（同时清除屏幕）

### 3. 返回值

RUN 命令输出一个JSON文件的路径，该文件包含命令的执行结果。

## 使用示例

### 基本用法
```bash
# 基本执行
RUN SEARCH_PAPER "3DGS" --max-results 3
# 输出：/Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json

# 带终端显示
RUN --show SEARCH_PAPER "3DGS" --max-results 3
# 先清除屏幕，然后显示格式化的JSON结果
```

### 支持的命令示例
```bash
RUN OVERLEAF document.tex
RUN SEARCH_PAPER "machine learning" --max-results 5
RUN LEARN "python basics"
RUN ALIAS ll "ls -la"
RUN USERINPUT
```

## JSON输出格式

### 成功执行 (JSON输出命令)
```json
{
  "success": true,
  "query": "3DGS",
  "total_papers_found": 2,
  "papers": [...],
  "timestamp": "2025-07-16T15:07:48.137974",
  "wrapped": true,
  "command": "SEARCH_PAPER",
  "args": "3DGS --max-results 3",
  "output_file": "/Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json",
  "duration": 3
}
```

### 成功执行 (其他命令)
```json
{
  "success": true,
  "message": "Command executed successfully",
  "command": "ALIAS",
  "args": "ll ls -la",
  "stdout": "别名 'll' 已成功创建",
  "stderr": "",
  "exit_code": 0,
  "duration": 0,
  "output_file": "/Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json"
}
```

### 执行失败
```json
{
  "success": false,
  "error": "Command execution failed",
  "command": "NONEXISTENT",
  "args": "test",
  "stdout": "",
  "stderr": "command not found",
  "exit_code": 1,
  "duration": 0,
  "output_file": "/Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json"
}
```

## --show 功能

### 核心特性

1. **终端输出显示**：使用`--show`标志时，命令结果会在终端中显示
2. **清除屏幕**：使用`--show`时会先清除终端屏幕
3. **保留JSON文件**：即使显示在终端，仍然保留JSON文件的功能
4. **格式化输出**：终端显示的JSON经过格式化，便于阅读

### 终端显示格式

```
=== RUN Command Output ===
Command: SEARCH_PAPER 3DGS --max-results 2
Output File: /Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json
==========================

{
    "success": true,
    "query": "3DGS",
    "total_papers_found": 1,
    "papers": [
        {
            "title": "Feature 3dgs: Supercharging 3d gaussian splatting to enable distilled feature fields",
            "authors": ["S Zhou", "H Chang", "S Jiang", "Z Fan…", "2024"],
            "abstract": "… In this work, we present Feature 3DGS...",
            "url": "http://openaccess.thecvf.com/content/CVPR2024/html/Zhou_Feature_3DGS_...",
            "pdf_url": "http://openaccess.thecvf.com/content/CVPR2024/papers/Zhou_Feature_3DGS_...",
            "publication_date": "",
            "venue": "openaccess.thecvf.com",
            "citation_count": null,
            "source": "google_scholar"
        }
    ],
    "timestamp": "2025-07-16T15:15:34.466752",
    "wrapped": true,
    "command": "SEARCH_PAPER",
    "args": "3DGS --max-results 2",
    "output_file": "/Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json",
    "duration": 3
}
/Users/wukunhuan/.local/bin/RUN_DATA/run_xxx.json
```

## 程序化调用

### 1. 使用 subprocess.run()

```python
import subprocess
import json
import os

# 执行命令
result = subprocess.run("RUN SEARCH_PAPER '3DGS' --max-results 3", 
                       shell=True, capture_output=True, text=True)

# 获取JSON文件路径
output_file = result.stdout.strip()

# 读取和解析JSON结果
with open(output_file, 'r') as f:
    data = json.load(f)

# 检查结果
if data['success']:
    print(f"Search successful: Found {data['total_papers_found']} papers")
    for paper in data['papers']:
        print(f"- {paper['title']}")
else:
    print(f"Search failed: {data['error']}")
```

### 2. 使用 --show 进行调试

```python
import subprocess

# 带终端显示的执行（用于调试）
result = subprocess.run("RUN --show SEARCH_PAPER '3DGS' --max-results 3", 
                       shell=True, capture_output=True, text=True)

# 获取JSON文件路径（仍然可用）
output_file = result.stdout.strip().split('\n')[-1]
```

## 使用场景

1. **调试和开发**：使用 `--show` 快速查看命令执行结果
2. **交互式使用**：在终端中直接查看格式化的输出
3. **程序化调用**：在脚本中使用RUN命令获取结构化结果
4. **演示和教学**：清晰展示命令的执行结果

## 技术实现

### 简化的架构

1. **无命令列表维护**：不再维护支持的命令列表
2. **直接命令执行**：直接执行指定的命令
3. **智能JSON检测**：自动检测命令输出是否为JSON格式
4. **统一包装**：非JSON输出自动包装为JSON格式

### 参数处理

1. **--show标志解析**：检测并处理`--show`参数
2. **命令重构**：根据是否有`--show`重构命令参数
3. **双重输出**：支持终端显示和文件输出

## 错误处理

### 常见错误
1. **命令不存在**: 检查命令文件是否存在
2. **执行失败**: 捕获命令执行错误
3. **JSON解析失败**: 自动包装非JSON输出

### 调试模式
使用 `--show` 获取详细信息：
```bash
RUN --show SEARCH_PAPER "machine learning"
```

## 项目位置
- 主程序: `~/.local/bin/RUN`
- 输出目录: `~/.local/bin/RUN_DATA/`

## 更多信息
RUN命令现在是一个真正的通用命令包装器，能够包装任何命令并提供统一的JSON接口，同时支持人性化的终端显示功能！ 