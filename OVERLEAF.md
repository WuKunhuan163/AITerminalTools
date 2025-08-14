# OVERLEAF 命令

LaTeX文件编译工具，支持GUI文件选择、JSON返回值和模板管理功能。

## 功能特点

- **GUI文件选择**: 无参数调用时自动打开文件选择器
- **JSON返回值**: 返回结构化的编译结果信息
- **模板管理**: 支持模板复制和部署功能
- **自动清理**: 编译后自动清理所有临时文件（包括.bbl、.aux等）
- **错误处理**: 详细的错误信息和状态报告
- **程序化调用**: 提供Python包装器支持

## 使用方法

### 1. 基本用法

```bash
# 使用GUI选择文件编译
OVERLEAF

# 编译指定文件
OVERLEAF document.tex
RUN --show OVERLEAF document.tex

# 指定输出目录
OVERLEAF document.tex --output-dir /path/to/output
```

### 2. 模板管理

```bash
# 列出所有可用模板
OVERLEAF --list-templates

# 复制模板到指定目录
OVERLEAF --template ICPRS my_paper

# 使用RUN环境获取JSON输出
RUN --show OVERLEAF --template ICPRS my_paper
```

### 3. JSON返回值格式

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

模板复制成功：
```json
{
  "success": true,
  "message": "Template 'ICPRS' copied successfully",
  "template": "ICPRS",
  "target_dir": "/path/to/my_paper",
  "files_copied": ["main.tex", "references.bib", "figures", "template"]
}
```

模板列表：
```json
{
  "success": true,
  "available_templates": ["ICPRS"],
  "message": "Available templates: ICPRS"
}
```

## 可用模板

### ICPRS
- **描述**: ICPRS会议论文模板
- **格式**: 双栏A4格式
- **包含文件**:
  - `main.tex`: 主文档文件
  - `template/preamble.tex`: 模板配置文件
  - `references.bib`: 参考文献数据库
  - `figures/template_figure_1.png`: 示例图片
  - `main.pdf`: 编译好的示例PDF
- **特点**: 
  - 标准ICPRS会议格式
  - 双栏布局
  - 匿名提交格式
  - 40%宽度图片显示
  - Abstract与正文标题格式统一

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

### LaTeX编译流程
1. **文件选择**: 无参数时打开GUI文件选择器
2. **文件验证**: 检查文件是否存在
3. **编译执行**: 使用latexmk进行PDF编译（包含BibTeX处理）
4. **结果检查**: 验证PDF是否成功生成
5. **清理工作**: 删除所有临时文件（.aux、.bbl、.blg、.fdb_latexmk、.run.xml、.bcf等）
6. **返回结果**: 输出JSON格式的编译结果

### 模板复制流程
1. **模板验证**: 检查指定模板是否存在
2. **目标检查**: 验证目标目录是否为空
3. **文件复制**: 复制模板的所有文件和子目录
4. **权限设置**: 保持文件权限和时间戳
5. **返回结果**: 输出复制成功信息

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
# 编译现有文档
OVERLEAF paper.tex

# 使用模板创建新论文
OVERLEAF --template ICPRS icprs_paper
cd icprs_paper
OVERLEAF main.tex

# 获取JSON格式的详细结果
RUN --show OVERLEAF main.tex
```

### 模板工作流程
```bash
# 1. 查看可用模板
OVERLEAF --list-templates

# 2. 创建新项目
OVERLEAF --template ICPRS my_conference_paper

# 3. 进入项目目录
cd my_conference_paper

# 4. 编辑main.tex文件
# (使用你喜欢的编辑器)

# 5. 编译生成PDF
OVERLEAF main.tex

# 6. 检查生成的PDF
open main.pdf  # macOS
# 或 xdg-open main.pdf  # Linux
```
