# Paper Searcher API

一个强大的学术论文搜索工具，支持Google Scholar和Arxiv的智能搜索。

## 功能特性

- 🔍 **智能关键词提取**: 从用户描述中自动提取和优化搜索关键词
- 📚 **多源搜索**: 支持Google Scholar和Arxiv两个主要学术数据库
- 🤖 **AI增强**: 利用AI技术优化搜索查询和结果排序
- 📊 **多种排序**: 支持按相关性、引用量、时间排序
- 💾 **结果管理**: 自动保存搜索结果和论文PDF
- 🔧 **灵活配置**: 丰富的命令行选项和配置文件支持

## 安装

1. 安装依赖包：
```bash
pip install -r requirements.txt
```

2. 确保PAPER_SEARCH脚本可执行：
```bash
chmod +x PAPER_SEARCH
```

## 使用方法

### 1. 直接使用PAPER_SEARCH指令

```bash
# 基本搜索
./PAPER_SEARCH "machine learning optimization"

# 指定结果数量
./PAPER_SEARCH "deep learning" --max-results 10

# 按引用量排序
./PAPER_SEARCH "neural networks" --sort-by citation

# 指定搜索源
./PAPER_SEARCH "computer vision" --sources arxiv

# 年份过滤
./PAPER_SEARCH "NLP" --year-range 2020 2023

# 下载PDF
./PAPER_SEARCH "reinforcement learning" --download-pdfs

# 指定输出目录
./PAPER_SEARCH "optimization" --output-dir ./my_papers
```

### 2. 交互模式

```bash
# 进入交互模式
./PAPER_SEARCH

# 或者
./PAPER_SEARCH --interactive
```

### 3. 智能处理器（在代码中使用）

```python
from paper_searcher.smart_handler import SmartPaperSearchHandler

handler = SmartPaperSearchHandler()

# 自动识别和处理论文搜索请求
result = handler.process_user_input("请帮我搜索关于深度学习的论文")
```

## 命令行选项

### 基本选项
- `--max-results, -n`: 最大结果数量 (默认: 10)
- `--sources, -s`: 搜索源 (google_scholar, arxiv, all)
- `--sort-by`: 排序方式 (relevance, citation, date)
- `--year-range`: 年份范围 (例如: --year-range 2020 2023)

### 输出选项
- `--output-dir, -o`: 输出目录 (默认: paper_searcher/data)
- `--download-pdfs`: 下载PDF文件
- `--save-format`: 保存格式 (json, csv, txt)

### 关键词选项
- `--keywords`: 手动指定关键词
- `--show-keywords`: 显示提取的关键词
- `--max-keywords`: 最大关键词数量

### 其他选项
- `--interactive, -i`: 交互模式
- `--verbose, -v`: 详细输出
- `--config`: 配置文件路径

## 智能识别功能

系统能够自动识别以下类型的输入：

1. **直接PAPER_SEARCH指令**:
   - `PAPER_SEARCH machine learning --max-results 5`

2. **自然语言描述**:
   - "请帮我搜索关于深度学习的论文"
   - "我想找一些计算机视觉的最新研究"
   - "搜索自然语言处理的论文，引用量高的"

3. **智能参数提取**:
   - 自动识别数量要求: "要10篇论文"
   - 自动识别排序偏好: "最新的"、"引用量高的"
   - 自动识别年份范围: "2020年以后"
   - 自动识别下载需求: "下载PDF"

## 输出格式

### JSON格式 (默认)
```json
{
  "query": "machine learning",
  "keywords": ["machine learning", "ml", "optimization"],
  "total_papers": 10,
  "papers": [
    {
      "title": "论文标题",
      "authors": ["作者1", "作者2"],
      "abstract": "摘要内容...",
      "url": "论文链接",
      "pdf_url": "PDF链接",
      "publication_date": "2023-01-01",
      "citation_count": 100,
      "venue": "会议/期刊名称"
    }
  ]
}
```

### 目录结构
```
paper_searcher/data/
├── papers.json          # 论文信息
├── papers.csv           # CSV格式 (可选)
├── papers.txt           # 文本格式 (可选)
└── papers/              # PDF文件目录
    ├── 001_paper_title.pdf
    ├── 002_another_paper.pdf
    └── ...
```

## 系统架构

### 核心组件

1. **BaseSearcher**: 抽象基类，定义搜索器接口
2. **GoogleScholarSearcher**: Google Scholar搜索实现
3. **ArxivSearcher**: Arxiv搜索实现
4. **KeywordExtractor**: 智能关键词提取器
5. **PaperSearchHandler**: PAPER_SEARCH指令处理器
6. **SmartPaperSearchHandler**: 智能处理器

### 数据结构

- **PaperInfo**: 论文信息数据类
- **SortBy**: 排序方式枚举
- **搜索历史**: 自动记录搜索历史

## 扩展性

系统采用工厂模式设计，可以轻松添加新的搜索源：

```python
class NewSearcher(BaseSearcher):
    def __init__(self):
        super().__init__("New Source")
    
    def search(self, keywords, max_results, sort_by, year_range):
        # 实现搜索逻辑
        pass
    
    def download_paper(self, paper_info, save_path):
        # 实现下载逻辑
        pass
```

## 故障排除

### 常见问题

1. **ImportError**: 确保所有依赖包已安装
2. **网络错误**: 检查网络连接和代理设置
3. **权限错误**: 确保有写入输出目录的权限
4. **搜索结果为空**: 尝试调整关键词或搜索源

### 调试模式

使用 `--verbose` 选项获取详细的调试信息：

```bash
./PAPER_SEARCH "machine learning" --verbose
```

## 贡献

欢迎提交Issue和Pull Request来改进这个项目！

## 许可证

MIT License 