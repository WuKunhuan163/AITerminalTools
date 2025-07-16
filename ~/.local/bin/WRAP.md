# WRAP 通用命令包装器

WRAP 是一个通用命令包装器，可以将任何支持的命令包装为返回JSON结果的形式，使得命令可以像函数一样有返回值。

## 功能特点

- **通用包装**: 支持包装 OVERLEAF、PAPER_SEARCH、LEARN、ALIAS 等命令
- **JSON返回值**: 所有命令都返回结构化的JSON结果
- **程序化调用**: 可以通过 subprocess.run() 等方式调用
- **错误处理**: 完整的错误信息和状态报告
- **唯一文件名**: 使用SHA256哈希避免文件名冲突
- **执行时间**: 记录命令执行时间
- **输出保存**: 结果保存到 `~/.local/bin/wrap_output/` 目录

## 使用方法

### 1. 基本语法

```bash
WRAP <command> [args...]
```

### 2. 支持的命令

- `OVERLEAF [file.tex]` - LaTeX编译
- `PAPER_SEARCH <query>` - 论文搜索
- `LEARN <topic>` - 学习材料生成
- `ALIAS <name> <command>` - 别名创建

### 3. 返回值

WRAP 命令输出一个JSON文件的路径，该文件包含命令的执行结果。

## JSON输出格式

### 成功执行 (OVERLEAF)
```json
{
  "success": true,
  "message": "Compilation successful",
  "file": "test.tex",
  "output": "./test.pdf",
  "wrapped": true,
  "command": "OVERLEAF",
  "args": "test.tex",
  "output_file": "/Users/wukunhuan/.local/bin/wrap_output/wrap_xxx.json",
  "duration": 1
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
  "output_file": "/Users/wukunhuan/.local/bin/wrap_output/wrap_xxx.json"
}
```

### 执行失败
```json
{
  "success": false,
  "error": "Command execution failed",
  "command": "OVERLEAF",
  "args": "nonexistent.tex",
  "stdout": "",
  "stderr": "File not found: nonexistent.tex",
  "exit_code": 1,
  "duration": 0,
  "output_file": "/Users/wukunhuan/.local/bin/wrap_output/wrap_xxx.json"
}
```

## 程序化调用

### 1. 使用 subprocess.run()

```python
import subprocess
import json
import os

# 执行命令
wrap_path = os.path.expanduser('~/.local/bin/WRAP')
result = subprocess.run([wrap_path, 'OVERLEAF', 'document.tex'], 
                       capture_output=True, text=True)

# 获取JSON文件路径
output_file = result.stdout.strip()

# 读取和解析JSON结果
with open(output_file, 'r') as f:
    data = json.load(f)

# 检查结果
if data['success']:
    print(f"编译成功: {data['output']}")
else:
    print(f"编译失败: {data['error']}")
```

### 2. 使用 WrapClient 类

```python
import sys
sys.path.append('/Users/wukunhuan/.local/project')
from wrap_client import WrapClient

# 创建客户端
client = WrapClient()

# 执行命令
result = client.overleaf('document.tex')
result = client.paper_search('machine learning')
result = client.learn('python basics')
result = client.alias('ll', 'ls -la')

# 或者使用通用方法
result = client.execute('OVERLEAF', 'document.tex')
```

### 3. 直接使用 WrapClient 脚本

```bash
# 命令行使用
python3 ~/.local/project/wrap_client.py OVERLEAF document.tex

# 获取JSON输出
python3 ~/.local/project/wrap_client.py OVERLEAF document.tex | jq '.success'
```

## 使用示例

### 编译 LaTeX 文件

```bash
# 基本用法
output_file=$(WRAP OVERLEAF document.tex)
echo "结果保存在: $output_file"

# 检查结果
if jq -r '.success' "$output_file" | grep -q true; then
    echo "编译成功"
    pdf_file=$(jq -r '.output' "$output_file")
    echo "PDF文件: $pdf_file"
else
    echo "编译失败"
    error=$(jq -r '.error' "$output_file")
    echo "错误: $error"
fi
```

### 搜索论文

```bash
output_file=$(WRAP PAPER_SEARCH "neural networks")
success=$(jq -r '.success' "$output_file")
if [[ "$success" == "true" ]]; then
    echo "搜索成功"
    jq -r '.stdout' "$output_file"
else
    echo "搜索失败"
    jq -r '.error' "$output_file"
fi
```

### 批量处理

```python
import os
import json
import subprocess

def wrap_command(command, *args):
    """执行WRAP命令并返回JSON结果"""
    wrap_path = os.path.expanduser('~/.local/bin/WRAP')
    result = subprocess.run([wrap_path, command] + list(args), 
                           capture_output=True, text=True)
    
    output_file = result.stdout.strip()
    with open(output_file, 'r') as f:
        return json.load(f)

# 批量编译LaTeX文件
tex_files = ['chapter1.tex', 'chapter2.tex', 'chapter3.tex']
results = []

for tex_file in tex_files:
    result = wrap_command('OVERLEAF', tex_file)
    results.append(result)
    
    if result['success']:
        print(f"✓ {tex_file} 编译成功")
    else:
        print(f"✗ {tex_file} 编译失败: {result['error']}")

# 统计结果
success_count = sum(1 for r in results if r['success'])
print(f"成功编译: {success_count}/{len(tex_files)}")
```

## 输出目录管理

### 清理旧文件

```bash
# 清理超过7天的输出文件
find ~/.local/bin/wrap_output -name "wrap_*.json" -mtime +7 -delete

# 清理所有输出文件
rm -f ~/.local/bin/wrap_output/wrap_*.json
```

### 查看最近的输出

```bash
# 查看最近的10个输出文件
ls -lt ~/.local/bin/wrap_output/wrap_*.json | head -10

# 查看最近一个成功的编译结果
find ~/.local/bin/wrap_output -name "wrap_*.json" -exec jq -r 'select(.success == true and .command == "OVERLEAF") | .output_file' {} \; | head -1
```

## 集成到工作流

### 在脚本中使用

```bash
#!/bin/bash
# 自动化LaTeX编译脚本

TEX_FILE="$1"
if [[ -z "$TEX_FILE" ]]; then
    echo "用法: $0 <tex_file>"
    exit 1
fi

# 编译文件
output_file=$(WRAP OVERLEAF "$TEX_FILE")
result=$(jq -r '.success' "$output_file")

if [[ "$result" == "true" ]]; then
    pdf_file=$(jq -r '.output' "$output_file")
    echo "编译成功: $pdf_file"
    
    # 可以继续后续操作，如打开PDF
    open "$pdf_file"
else
    echo "编译失败:"
    jq -r '.error' "$output_file"
    exit 1
fi
```

### 在Python项目中使用

```python
from wrap_client import WrapClient
import logging

class DocumentProcessor:
    def __init__(self):
        self.wrap_client = WrapClient()
        
    def compile_latex(self, tex_file):
        """编译LaTeX文件"""
        result = self.wrap_client.overleaf(tex_file)
        
        if result['success']:
            logging.info(f"LaTeX编译成功: {result['output']}")
            return result['output']
        else:
            logging.error(f"LaTeX编译失败: {result['error']}")
            raise Exception(f"编译失败: {result['error']}")
    
    def search_papers(self, query):
        """搜索相关论文"""
        result = self.wrap_client.paper_search(query)
        
        if result['success']:
            logging.info(f"论文搜索成功")
            return result['stdout']
        else:
            logging.error(f"论文搜索失败: {result['error']}")
            return None
```

## 故障排除

### 常见问题

1. **输出文件不存在**
   - 检查 `~/.local/bin/wrap_output/` 目录权限
   - 确保磁盘空间充足

2. **JSON解析错误**
   - 检查输出文件是否完整
   - 验证JSON格式是否正确

3. **命令执行失败**
   - 检查原始命令是否正常工作
   - 查看stderr输出了解具体错误

### 调试技巧

```bash
# 启用详细输出
export DEBUG=1
WRAP OVERLEAF document.tex

# 手动检查输出文件
output_file=$(WRAP OVERLEAF document.tex)
cat "$output_file" | jq '.'

# 验证JSON格式
output_file=$(WRAP OVERLEAF document.tex)
jq empty "$output_file" && echo "JSON格式正确" || echo "JSON格式错误"
```

## 扩展支持

要添加新命令的支持，需要：

1. 在 `WRAP` 脚本的 `supported_commands` 数组中添加命令名
2. 在 `case` 语句中添加相应的处理逻辑
3. 在 `WrapClient` 类中添加对应的方法

## 项目结构

```
~/.local/bin/
├── WRAP                    # 主包装器脚本
├── WRAP.md                 # 文档文件
├── OVERLEAF               # 被包装的命令
├── PAPER_SEARCH           # 被包装的命令
├── LEARN                  # 被包装的命令
├── ALIAS                  # 被包装的命令
└── wrap_output/           # 输出文件目录
    └── wrap_*.json        # JSON结果文件

~/.local/project/
├── wrap_client.py         # Python客户端
└── overleaf_wrapper.py    # 原始包装器(已弃用)
```

WRAP 系统提供了一个统一的接口，使得所有命令都可以像函数一样返回结构化的结果，便于程序化调用和自动化处理。 