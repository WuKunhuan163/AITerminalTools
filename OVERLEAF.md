# OVERLEAF 命令

LaTeX文件编译工具，支持GUI文件选择和JSON返回值。

## 功能特点

- **GUI文件选择**: 无参数调用时自动打开文件选择器
- **JSON返回值**: 返回结构化的编译结果信息
- **自动清理**: 编译后自动清理临时文件
- **错误处理**: 详细的错误信息和状态报告
- **程序化调用**: 提供Python包装器支持

## 使用方法

### 1. 基本用法

```bash
# 使用GUI选择文件编译
OVERLEAF

# 编译指定文件
OVERLEAF document.tex
```

### 2. JSON返回值格式

成功编译：
```json
{
  "success": true,
  "message": "Compilation successful",
  "file": "/path/to/document.tex",
  "output": "/path/to/document.pdf"
}
```

编译失败：
```json
{
  "success": false,
  "error": "Compilation failed: error details...",
  "file": "/path/to/document.tex"
}
```

文件未找到：
```json
{
  "success": false,
  "error": "File not found: document.tex",
  "file": "document.tex"
}
```

### 3. 程序化调用

使用Python包装器：

```python
# 导入包装器
import sys
sys.path.append('/Users/wukunhuan/.local/project')
from overleaf_wrapper import OverleafWrapper

# 创建实例
wrapper = OverleafWrapper()

# 使用GUI选择文件
result = wrapper.compile_with_gui()

# 编译指定文件
result = wrapper.compile_file("document.tex")

# 检查结果
if result["success"]:
    print(f"编译成功: {result['output']}")
else:
    print(f"编译失败: {result['error']}")
```

直接调用包装器脚本：

```bash
# 使用GUI选择文件
python3 ~/.local/project/overleaf_wrapper.py

# 编译指定文件
python3 ~/.local/project/overleaf_wrapper.py document.tex
```

## 依赖要求

- **LaTeX**: 需要安装完整的LaTeX发行版（如MacTeX、TeX Live）
- **latexmk**: LaTeX编译工具
- **Python 3**: 用于GUI文件选择器
- **tkinter**: Python GUI库（通常随Python安装）

## 安装依赖

### macOS
```bash
# 安装MacTeX
brew install --cask mactex

# 或者安装BasicTeX（轻量版）
brew install --cask basictex
```

### Linux
```bash
# Ubuntu/Debian
sudo apt-get install texlive-full

# 或者最小安装
sudo apt-get install texlive-latex-base texlive-latex-extra
```

## 编译过程

1. **文件选择**: 无参数时打开GUI文件选择器
2. **文件验证**: 检查文件是否存在
3. **编译执行**: 使用latexmk进行PDF编译
4. **结果检查**: 验证PDF是否成功生成
5. **清理工作**: 删除临时文件和日志
6. **返回结果**: 输出JSON格式的编译结果

## 常见问题

### 1. GUI不显示
- 确保系统支持图形界面
- 检查Python tkinter是否正确安装
- 尝试在终端中直接运行Python GUI测试

### 2. 编译失败
- 检查LaTeX语法错误
- 确认所需的宏包已安装
- 查看详细错误信息中的具体问题

### 3. 权限问题
- 确保脚本有执行权限
- 检查文件目录的读写权限

### 4. 路径问题
- 使用绝对路径或确保在正确目录中
- 检查文件名是否包含特殊字符

## 示例用法

### 编译学术论文
```bash
OVERLEAF paper.tex
```

### 批量编译检查
```python
from overleaf_wrapper import OverleafWrapper

wrapper = OverleafWrapper()
tex_files = ["chapter1.tex", "chapter2.tex", "chapter3.tex"]

for tex_file in tex_files:
    result = wrapper.compile_file(tex_file)
    if result["success"]:
        print(f"✓ {tex_file} 编译成功")
    else:
        print(f"✗ {tex_file} 编译失败: {result['error']}")
```

### 集成到工作流
```bash
# 编译并检查结果
result=$(OVERLEAF document.tex)
if echo "$result" | grep -q '"success": true'; then
    echo "编译成功，可以继续后续步骤"
else
    echo "编译失败，请检查LaTeX文件"
    exit 1
fi
``` 