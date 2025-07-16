# SEARCH_PAPER 命令接口说明

## 概述
SEARCH_PAPER 是一个真正的网页爬虫学术论文搜索工具，通过网页抓取（crawl）从多个学术网站获取论文信息，并验证所有链接的有效性。

## 🔧 核心特性

1. **真正的网页爬虫**：通过网页抓取获取论文信息
2. **链接验证**：验证所有论文链接的有效性
3. **JSON输出**：返回结构化的JSON数据
4. **减少日志输出**：终端输出极简，只在必要时显示错误
5. **无示例论文**：完全通过真实网页搜索获取论文

## 🌐 搜索源

SEARCH_PAPER支持多个真实的搜索源：

1. **arXiv**：通过网页爬虫搜索arXiv.org
2. **Google Scholar**：爬取Google Scholar搜索结果
3. **Semantic Scholar**：使用Semantic Scholar API

## 基本语法
```bash
SEARCH_PAPER <查询内容> [选项...]
```

## 使用示例

### 基本搜索
```bash
SEARCH_PAPER "machine learning"
SEARCH_PAPER "3DGS"
```

### 带参数搜索
```bash
# 指定结果数量
SEARCH_PAPER "neural networks" --max-results 20

# 搜索3DGS相关论文
SEARCH_PAPER "3DGS" --max-results 3
```

## 命令行选项

### 搜索控制
- `--max-results <数量>`: 最大结果数量 (默认: 10)

## 🎯 实际测试结果

**命令**：`RUN SEARCH_PAPER "3DGS" --max-results 3`

**结果**：成功找到真实的3DGS相关论文：

#### 论文1：Feature 3DGS: Supercharging 3D Gaussian Splatting to Enable Distilled Feature Fields
- **作者**：S Zhou, H Chang, S Jiang, Z Fan等
- **来源**：CVPR 2024
- **链接**：http://openaccess.thecvf.com/content/CVPR2024/html/Zhou_Feature_3DGS_Supercharging_3D_Gaussian_Splatting_to_Enable_Distilled_Feature_CVPR_2024_paper.html
- **PDF**：http://openaccess.thecvf.com/content/CVPR2024/papers/Zhou_Feature_3DGS_Supercharging_3D_Gaussian_Splatting_to_Enable_Distilled_Feature_CVPR_2024_paper.pdf
- **状态**：✅ 链接已验证有效

#### 论文2：3DGS-Enhancer: Enhancing Unbounded 3D Gaussian Splatting with View-Consistent 2D Diffusion Priors
- **作者**：X Liu, C Zhou, S Huang
- **来源**：NeurIPS 2024
- **链接**：https://proceedings.neurips.cc/paper_files/paper/2024/hash/f0b42291ddab77dcb2ef8a3488301b62-Abstract-Conference.html
- **PDF**：https://proceedings.neurips.cc/paper_files/paper/2024/file/f0b42291ddab77dcb2ef8a3488301b62-Paper-Conference.pdf
- **状态**：✅ 链接已验证有效

## 📊 JSON输出格式

```json
{
  "success": true,
  "query": "3DGS",
  "total_papers_found": 2,
  "papers": [
    {
      "title": "Feature 3dgs: Supercharging 3d gaussian splatting to enable distilled feature fields",
      "authors": ["S Zhou", "H Chang", "S Jiang", "Z Fan…"],
      "abstract": "… In this work, we present Feature 3DGS: the first feature field distillation technique based on the 3D Gaussian Splatting framework...",
      "url": "http://openaccess.thecvf.com/content/CVPR2024/html/Zhou_Feature_3DGS_Supercharging_3D_Gaussian_Splatting_to_Enable_Distilled_Feature_CVPR_2024_paper.html",
      "pdf_url": "http://openaccess.thecvf.com/content/CVPR2024/papers/Zhou_Feature_3DGS_Supercharging_3D_Gaussian_Splatting_to_Enable_Distilled_Feature_CVPR_2024_paper.pdf",
      "publication_date": "",
      "venue": "openaccess.thecvf.com",
      "citation_count": null,
      "source": "google_scholar"
    }
  ],
  "timestamp": "2025-07-16T15:07:48.137974"
}
```

## 🔧 技术实现

1. **真实网页爬虫**：
   - 使用requests和BeautifulSoup进行网页抓取
   - 模拟真实浏览器请求头
   - 处理不同网站的HTML结构

2. **链接验证**：
   - 验证论文主页链接的可访问性
   - 自动查找和验证PDF链接
   - 过滤无效链接

3. **去重处理**：
   - 基于标题相似性去除重复论文
   - 使用MD5哈希进行快速比较

4. **错误处理**：
   - 静默处理单个搜索源的失败
   - 继续尝试其他搜索源
   - 优雅降级，确保总是有结果

## 🚀 使用方法

### 基本使用
```bash
# 直接使用
python3 SEARCH_PAPER "3DGS" --max-results 3

# 通过RUN命令（推荐）
RUN SEARCH_PAPER "3DGS" --max-results 3

# 带终端显示
RUN --show SEARCH_PAPER "3DGS" --max-results 3
```

### Python集成
```python
import subprocess
import json

# 执行搜索
result = subprocess.run("RUN SEARCH_PAPER '3DGS' --max-results 3", 
                       shell=True, capture_output=True, text=True)

# 解析结果
output_file = result.stdout.strip()
with open(output_file, 'r') as f:
    data = json.load(f)

# 访问论文信息
papers = data['papers']
for paper in papers:
    print(f"标题: {paper['title']}")
    print(f"链接: {paper['url']}")
    print(f"PDF: {paper['pdf_url']}")
```

## 错误处理

### 常见错误
1. **网络连接错误**: 检查网络连接
2. **搜索结果为空**: 尝试调整关键词
3. **链接无效**: 系统自动过滤无效链接

### 调试模式
使用RUN命令的`--show`参数获取详细信息：
```bash
RUN --show SEARCH_PAPER "machine learning"
```

## 依赖要求
- Python 3.7+
- requests
- beautifulsoup4
- lxml

## 项目位置
- 主程序: `~/.local/bin/SEARCH_PAPER`
- 默认输出: `~/.local/project/SEARCH_PAPERer/data/papers.json`

## 更多信息
SEARCH_PAPER现在是一个真正的网页爬虫，能够从多个学术网站获取实际存在的论文信息，并验证所有链接的有效性！ 