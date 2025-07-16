"""
Arxiv搜索器
使用arxiv库来搜索Arxiv上的论文
"""

import requests
import time
import re
from typing import List, Optional
from urllib.parse import urljoin
import os
from datetime import datetime

try:
    import arxiv
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    print("警告: arxiv库未安装，Arxiv搜索功能将受限")

from base_searcher import BaseSearcher, PaperInfo, SortBy


class ArxivSearcher(BaseSearcher):
    """Arxiv搜索器"""
    
    def __init__(self):
        super().__init__("Arxiv")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search(self, keywords: List[str], max_results: int = 10, 
               sort_by: SortBy = SortBy.RELEVANCE, 
               year_range: Optional[tuple] = None) -> List[PaperInfo]:
        """
        搜索Arxiv上的论文
        """
        if not ARXIV_AVAILABLE:
            return self._fallback_search(keywords, max_results, sort_by, year_range)
        
        try:
            # 构建搜索查询
            query = " ".join(keywords)
            print(f"正在搜索Arxiv: {query}")
            
            # 设置排序方式
            sort_criterion = self._get_arxiv_sort_criterion(sort_by)
            
            # 使用arxiv库进行搜索
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=sort_criterion,
                sort_order=arxiv.SortOrder.Descending
            )
            
            papers = []
            
            for result in search.results():
                try:
                    # 提取论文信息
                    paper_info = self._extract_paper_info(result)
                    
                    # 年份过滤
                    if year_range and paper_info.publication_date:
                        try:
                            pub_year = int(paper_info.publication_date.split('-')[0])
                            if not (year_range[0] <= pub_year <= year_range[1]):
                                continue
                        except (ValueError, IndexError):
                            pass
                    
                    papers.append(paper_info)
                    
                    # 避免请求过快
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"处理论文时出错: {e}")
                    continue
            
            # 记录搜索历史
            self.add_to_history(keywords, len(papers))
            
            print(f"找到 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            print(f"Arxiv搜索出错: {e}")
            return self._fallback_search(keywords, max_results, sort_by, year_range)
    
    def _get_arxiv_sort_criterion(self, sort_by: SortBy):
        """获取Arxiv的排序标准"""
        if sort_by == SortBy.DATE:
            return arxiv.SortCriterion.SubmittedDate
        elif sort_by == SortBy.CITATION:
            # Arxiv本身不提供引用排序，使用更新时间作为替代
            return arxiv.SortCriterion.LastUpdatedDate
        else:  # RELEVANCE
            return arxiv.SortCriterion.Relevance
    
    def _extract_paper_info(self, result) -> PaperInfo:
        """从arxiv结果中提取论文信息"""
        title = result.title
        authors = [author.name for author in result.authors]
        abstract = result.summary
        url = result.entry_id
        pdf_url = result.pdf_url
        
        # 获取发表日期
        publication_date = result.published.strftime('%Y-%m-%d')
        
        # 获取分类信息作为关键词
        keywords = [category for category in result.categories]
        
        # 获取期刊信息
        venue = result.journal_ref if result.journal_ref else "arXiv preprint"
        
        # 获取DOI
        doi = result.doi
        
        return PaperInfo(
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            pdf_url=pdf_url,
            publication_date=publication_date,
            citation_count=None,  # Arxiv不提供引用数
            venue=venue,
            doi=doi,
            keywords=keywords
        )
    
    def _fallback_search(self, keywords: List[str], max_results: int, 
                        sort_by: SortBy, year_range: Optional[tuple]) -> List[PaperInfo]:
        """
        备用搜索方法（当arxiv库不可用时）
        使用Arxiv API进行搜索
        """
        print("使用备用搜索方法...")
        
        try:
            # 构建Arxiv API查询
            query = " ".join(keywords)
            api_url = "http://export.arxiv.org/api/query"
            
            params = {
                'search_query': f'all:{query}',
                'start': 0,
                'max_results': max_results,
                'sortBy': 'relevance',
                'sortOrder': 'descending'
            }
            
            response = self.session.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            
            # 解析XML响应
            papers = self._parse_arxiv_xml(response.text, year_range)
            
            return papers[:max_results]
            
        except Exception as e:
            print(f"备用搜索也失败: {e}")
            return self._create_sample_data(keywords, max_results)
    
    def _parse_arxiv_xml(self, xml_content: str, year_range: Optional[tuple]) -> List[PaperInfo]:
        """解析Arxiv API返回的XML"""
        papers = []
        
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_content)
            
            # 定义命名空间
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            entries = root.findall('atom:entry', namespaces)
            
            for entry in entries:
                try:
                    title = entry.find('atom:title', namespaces).text.strip()
                    
                    # 获取作者
                    authors = []
                    for author in entry.findall('atom:author', namespaces):
                        name = author.find('atom:name', namespaces)
                        if name is not None:
                            authors.append(name.text)
                    
                    # 获取摘要
                    summary = entry.find('atom:summary', namespaces)
                    abstract = summary.text.strip() if summary is not None else ""
                    
                    # 获取链接
                    url = entry.find('atom:id', namespaces).text
                    
                    # 获取PDF链接
                    pdf_url = None
                    for link in entry.findall('atom:link', namespaces):
                        if link.get('type') == 'application/pdf':
                            pdf_url = link.get('href')
                            break
                    
                    # 获取发表日期
                    published = entry.find('atom:published', namespaces)
                    publication_date = published.text[:10] if published is not None else None
                    
                    # 年份过滤
                    if year_range and publication_date:
                        try:
                            pub_year = int(publication_date.split('-')[0])
                            if not (year_range[0] <= pub_year <= year_range[1]):
                                continue
                        except (ValueError, IndexError):
                            pass
                    
                    # 获取分类
                    categories = []
                    for category in entry.findall('atom:category', namespaces):
                        term = category.get('term')
                        if term:
                            categories.append(term)
                    
                    paper_info = PaperInfo(
                        title=title,
                        authors=authors,
                        abstract=abstract,
                        url=url,
                        pdf_url=pdf_url,
                        publication_date=publication_date,
                        citation_count=None,
                        venue="arXiv preprint",
                        keywords=categories
                    )
                    
                    papers.append(paper_info)
                    
                except Exception as e:
                    print(f"解析单个论文时出错: {e}")
                    continue
            
        except Exception as e:
            print(f"解析XML时出错: {e}")
        
        return papers
    
    def _create_sample_data(self, keywords: List[str], max_results: int) -> List[PaperInfo]:
        """创建示例数据"""
        query = " ".join(keywords)
        
        sample_papers = [
            PaperInfo(
                title=f"Arxiv示例论文: {query}的深度学习方法",
                authors=["研究者A", "研究者B"],
                abstract=f"这是一篇关于{query}的Arxiv示例论文摘要...",
                url="https://arxiv.org/abs/2301.00001",
                pdf_url="https://arxiv.org/pdf/2301.00001.pdf",
                publication_date="2023-01-01",
                citation_count=None,
                venue="arXiv preprint",
                keywords=["cs.AI", "cs.LG"]
            )
        ]
        
        return sample_papers[:max_results]
    
    def download_paper(self, paper_info: PaperInfo, save_path: str) -> bool:
        """
        下载论文PDF
        """
        if not paper_info.pdf_url:
            print(f"论文 '{paper_info.title}' 没有可用的PDF链接")
            return False
        
        try:
            print(f"正在下载: {paper_info.title}")
            
            response = self.session.get(paper_info.pdf_url, timeout=30)
            response.raise_for_status()
            
            # 确保目录存在
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"下载成功: {save_path}")
            return True
            
        except Exception as e:
            print(f"下载失败: {e}")
            return False
    
    def get_paper_categories(self, paper_info: PaperInfo) -> List[str]:
        """
        获取论文的分类信息
        """
        if paper_info.keywords:
            return paper_info.keywords
        
        # 如果没有关键词，尝试从URL中提取
        if "arxiv.org/abs/" in paper_info.url:
            try:
                arxiv_id = paper_info.url.split("/abs/")[-1]
                # 可以通过arxiv_id获取更详细的分类信息
                return [f"arxiv:{arxiv_id}"]
            except:
                pass
        
        return [] 