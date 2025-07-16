# LEARN 命令接口说明

## 概述
LEARN 是一个智能学习系统，能够自动生成教程、问题和示例代码，特别支持学术论文的分章节学习。

## 基本语法
```bash
LEARN [选项] <学习内容>
```

## 使用模式

### 1. 交互模式
```bash
# 进入交互模式，系统会引导您输入参数
LEARN
```

### 2. 直接模式

#### 一般主题学习
```bash
# 基础学习
LEARN "Python基础"

# 指定学习模式和风格
LEARN "机器学习" --mode Advanced --style Witty

# 实用模式学习
LEARN "深度学习" --mode Practical --style Rigorous
```

#### 论文学习（特色功能）
```bash
# 基础论文学习
LEARN "/path/to/paper.pdf"

# 带图像分析的论文学习
LEARN "/path/to/paper.pdf" --read-images

# 指定页面范围
LEARN "/path/to/paper.pdf" --pages 1-10

# 自定义章节分割
LEARN "/path/to/paper.pdf" --chapters "Introduction,Method,Results,Conclusion"
```

## 命令行选项

### 学习模式
- `--mode <模式>`: 学习模式
  - `Beginner`: 初学者模式（默认）
  - `Advanced`: 高级模式
  - `Practical`: 实用模式

### 解释风格
- `--style <风格>`: 解释风格
  - `Rigorous`: 严谨风格（默认）
  - `Witty`: 幽默风格

### 论文学习选项
- `--read-images`: 启用图像分析
- `--pages <范围>`: 指定页面范围 (例如: 1-10, 5-15)
- `--chapters <列表>`: 自定义章节分割 (逗号分隔)
- `--max-pages <数量>`: 每次处理的最大页数 (默认: 5)

### 输出选项
- `--output-dir <目录>`: 输出目录
- `--format <格式>`: 输出格式 (markdown, html, pdf)
- `--save-questions`: 保存生成的问题
- `--save-examples`: 保存示例代码

### 其他选项
- `--help, -h`: 显示帮助信息
- `--verbose, -v`: 详细输出
- `--config <文件>`: 配置文件路径

## 功能特性

### 一般主题学习
- 📚 **结构化教程**: 自动生成有序的学习内容
- ❓ **自评问题**: 创建带折叠答案的问题
- 💡 **示例代码**: 生成相关的代码示例
- 🎯 **多种模式**: 支持不同难度和风格

### 论文学习（特色功能）
- 📄 **分块处理**: 自动将论文分成可管理的块
- 📖 **章节分割**: 智能识别论文结构
  - 背景/介绍
  - 方法论
  - 评估/结果
  - 未来工作
- 🖼️ **图像分析**: 可选的图像内容分析
- 📋 **章节教程**: 为每个章节生成专门的教程
- 🔍 **深度问题**: 基于论文内容生成综合性问题

## 使用示例

### 基础学习
```bash
# 学习Python基础
LEARN "Python基础"

# 学习机器学习（高级模式，幽默风格）
LEARN "机器学习" --mode Advanced --style Witty

# 学习深度学习（实用模式）
LEARN "深度学习" --mode Practical
```

### 论文学习
```bash
# 学习一篇论文
LEARN "~/Documents/paper.pdf"

# 带图像分析的论文学习
LEARN "~/Documents/paper.pdf" --read-images

# 学习论文的特定页面
LEARN "~/Documents/paper.pdf" --pages 1-5

# 自定义章节分割
LEARN "~/Documents/paper.pdf" --chapters "Abstract,Introduction,Methodology,Results,Discussion,Conclusion"
```

### 高级用法
```bash
# 保存学习材料到指定目录
LEARN "机器学习" --output-dir ./learning_materials --save-questions --save-examples

# 使用配置文件
LEARN "深度学习" --config my_learn_config.json

# 详细输出模式
LEARN "自然语言处理" --verbose
```

## 输出格式

### 教程结构
```
学习主题: [主题名称]
====================

1. 概述
   - 基本概念
   - 关键要点

2. 详细内容
   - 核心知识点
   - 实际应用

3. 示例代码
   ```python
   # 相关代码示例
   ```

4. 自评问题
   Q: 问题内容
   <details>
   <summary>答案</summary>
   详细答案
   </details>
```

### 论文学习输出
```
论文学习: [论文标题]
==================

章节 1: 介绍
- 背景信息
- 研究问题
- 贡献总结

章节 2: 方法
- 核心方法
- 算法描述
- 实现细节

[继续其他章节...]

综合问题:
1. 论文的主要贡献是什么？
2. 使用的方法有什么优缺点？
3. 结果如何验证方法的有效性？
```

## 配置文件

创建 `learn_config.json`:
```json
{
  "default_mode": "Advanced",
  "default_style": "Rigorous",
  "output_dir": "./learning_output",
  "save_questions": true,
  "save_examples": true,
  "paper_settings": {
    "max_pages": 5,
    "read_images": false,
    "default_chapters": [
      "Introduction",
      "Method",
      "Results",
      "Conclusion"
    ]
  }
}
```

## 集成功能

### 与PDF提取器集成
LEARN系统与现有的PDF提取器集成，支持：
- 📄 PDF文本提取
- 🖼️ 图像内容分析
- 📊 表格和图表理解

### 智能识别
系统能够智能识别：
- 📚 学术论文 vs 一般主题
- 🔍 论文结构和章节
- 💡 关键概念和术语
- ❓ 适合的问题类型

## 故障排除

### 常见问题
1. **文件路径错误**: 确保PDF文件路径正确
2. **权限问题**: 确保有读取PDF文件的权限
3. **依赖缺失**: 运行 `pip install -r requirements.txt`
4. **内存不足**: 对大型PDF使用 `--max-pages` 限制

### 调试模式
```bash
LEARN "主题" --verbose
```

## 系统要求
- Python 3.7+
- PyMuPDF>=1.23.0
- 其他依赖见 requirements.txt

## 项目位置
- 主程序: `~/.local/bin/LEARN`
- 项目代码: `~/.local/project/learn_project/`
- 详细文档: `~/.local/project/learn_project/README.md`

## 更多信息
详细的技术文档和开发指南请参考项目目录中的README.md文件。 