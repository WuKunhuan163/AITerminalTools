# PAPER_SEARCH 命令接口说明

## 概述
PAPER_SEARCH 是一个智能学术论文搜索工具，支持从Google Scholar和Arxiv搜索论文。

## 基本语法
```bash
PAPER_SEARCH <查询内容> [选项...]
```

## 使用示例

### 基本搜索
```bash
PAPER_SEARCH "machine learning"
PAPER_SEARCH "深度学习在计算机视觉中的应用"
```

### 带参数搜索
```bash
# 指定结果数量
PAPER_SEARCH "neural networks" --max-results 20

# 按引用量排序
PAPER_SEARCH "optimization" --sort-by citation

# 指定搜索源
PAPER_SEARCH "NLP" --sources arxiv

# 年份过滤
PAPER_SEARCH "computer vision" --year-range 2020 2023

# 下载PDF
PAPER_SEARCH "reinforcement learning" --download-pdfs

# 指定输出目录
PAPER_SEARCH "transformer" --output-dir ./my_papers
```

## 命令行选项

### 搜索控制
- `--max-results, -n <数量>`: 最大结果数量 (默认: 10)
- `--sources, -s <源>`: 搜索源选择
  - `google_scholar`: 仅Google Scholar
  - `arxiv`: 仅Arxiv
  - `all`: 所有源 (默认)
- `--sort-by <方式>`: 排序方式
  - `relevance`: 按相关性 (默认)
  - `citation`: 按引用量
  - `date`: 按时间
- `--year-range <起始年> <结束年>`: 年份范围过滤

### 输出控制
- `--output-dir, -o <目录>`: 输出目录 (默认: ~/.local/project/paper_searcher/data)
- `--download-pdfs`: 下载PDF文件
- `--save-format <格式>`: 保存格式
  - `json`: JSON格式 (默认)
  - `csv`: CSV格式
  - `txt`: 文本格式

### 关键词控制
- `--keywords <关键词...>`: 手动指定关键词
- `--show-keywords`: 显示提取的关键词
- `--max-keywords <数量>`: 最大关键词数量 (默认: 10)

### 其他选项
- `--interactive, -i`: 交互模式
- `--verbose, -v`: 详细输出
- `--config <文件>`: 配置文件路径
- `--help, -h`: 显示帮助信息

## 交互模式
```bash
# 进入交互模式
PAPER_SEARCH --interactive
# 或者
PAPER_SEARCH
```

交互模式下，系统会引导您输入搜索参数。

## 智能识别
系统支持自然语言输入，会自动识别以下模式：

### 数量识别
- "要10篇论文" → `--max-results 10`
- "大概5篇" → `--max-results 5`

### 排序识别
- "最新的" → `--sort-by date`
- "引用量高的" → `--sort-by citation`

### 年份识别
- "2020年以后" → `--year-range 2020 2024`
- "2018-2022年" → `--year-range 2018 2022`

### 下载识别
- "下载PDF" → `--download-pdfs`

## 输出格式

### 默认输出目录结构
```
~/.local/project/paper_searcher/data/
├── papers.json          # 论文详细信息
├── papers.csv           # CSV格式 (可选)
├── papers.txt           # 文本格式 (可选)
└── papers/              # PDF文件目录
    ├── 001_paper_title.pdf
    ├── 002_another_paper.pdf
    └── ...
```

### JSON格式示例
```json
{
  "query": "machine learning",
  "keywords": ["machine learning", "ml", "optimization"],
  "total_papers": 10,
  "search_params": {
    "sources": ["all"],
    "max_results": 10,
    "sort_by": "relevance"
  },
  "papers": [
    {
      "title": "论文标题",
      "authors": ["作者1", "作者2"],
      "abstract": "摘要内容...",
      "url": "https://arxiv.org/abs/xxxx.xxxxx",
      "pdf_url": "https://arxiv.org/pdf/xxxx.xxxxx.pdf",
      "publication_date": "2023-01-01",
      "citation_count": 100,
      "venue": "Conference/Journal Name"
    }
  ]
}
```

## 错误处理

### 常见错误
1. **网络连接错误**: 检查网络连接
2. **权限错误**: 确保有写入输出目录的权限
3. **搜索结果为空**: 尝试调整关键词或搜索源
4. **PDF下载失败**: 某些论文可能没有开放的PDF链接

### 调试模式
使用 `--verbose` 获取详细信息：
```bash
PAPER_SEARCH "machine learning" --verbose
```

## 依赖要求
- Python 3.7+
- requests
- arxiv
- 其他依赖见 requirements.txt

## 项目位置
- 主程序: `~/.local/bin/PAPER_SEARCH`
- 项目代码: `~/.local/project/paper_searcher/`
- 默认输出: `~/.local/project/paper_searcher/data/`

## 更多信息
详细文档请参考: `~/.local/project/paper_searcher/README.md` 