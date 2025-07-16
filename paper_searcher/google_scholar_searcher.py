"""
Google Scholar搜索器
使用scholarly库来搜索Google Scholar上的论文
"""

import requests
import time
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import os

try:
    from scholarly import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    print("警告: scholarly库未安装，Google Scholar搜索功能将受限")

from base_searcher import BaseSearcher, PaperInfo, SortBy


class GoogleScholarSearcher(BaseSearcher):
    """Google Scholar搜索器"""
    
    def __init__(self):
        super().__init__("Google Scholar")
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def search(self, keywords: List[str], max_results: int = 10, 
               sort_by: SortBy = SortBy.RELEVANCE, 
               year_range: Optional[tuple] = None) -> List[PaperInfo]:
        """
        搜索Google Scholar上的论文
        """
        if not SCHOLARLY_AVAILABLE:
            return self._fallback_search(keywords, max_results, sort_by, year_range)
        
        try:
            # 构建搜索查询
            query = " ".join(keywords)
            print(f"正在搜索Google Scholar: {query}")
            
            # 使用scholarly进行搜索
            search_query = scholarly.search_pubs(query)
            
            papers = []
            count = 0
            
            for pub in search_query:
                if count >= max_results:
                    break
                
                try:
                    # 获取详细信息
                    pub_filled = scholarly.fill(pub)
                    
                    # 提取论文信息
                    paper_info = self._extract_paper_info(pub_filled)
                    
                    # 年份过滤
                    if year_range and paper_info.publication_date:
                        try:
                            pub_year = int(paper_info.publication_date.split('-')[0])
                            if not (year_range[0] <= pub_year <= year_range[1]):
                                continue
                        except (ValueError, IndexError):
                            pass
                    
                    papers.append(paper_info)
                    count += 1
                    
                    # 避免请求过快
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"处理论文时出错: {e}")
                    continue
            
            # 根据排序方式排序
            papers = self._sort_papers(papers, sort_by)
            
            # 记录搜索历史
            self.add_to_history(keywords, len(papers))
            
            print(f"找到 {len(papers)} 篇论文")
            return papers
            
        except Exception as e:
            print(f"Google Scholar搜索出错: {e}")
            return self._fallback_search(keywords, max_results, sort_by, year_range)
    
    def _extract_paper_info(self, pub) -> PaperInfo:
        """从scholarly结果中提取论文信息"""
        title = pub.get('title', '未知标题')
        authors = [author.get('name', '') for author in pub.get('author', [])]
        abstract = pub.get('abstract', '')
        url = pub.get('pub_url', '')
        
        # 尝试获取PDF链接
        pdf_url = None
        if 'eprint_url' in pub:
            pdf_url = pub['eprint_url']
        
        # 获取发表日期
        publication_date = None
        if 'pub_year' in pub:
            publication_date = str(pub['pub_year'])
        
        # 获取引用数
        citation_count = pub.get('num_citations', 0)
        
        # 获取会议/期刊信息
        venue = pub.get('venue', '')
        
        return PaperInfo(
            title=title,
            authors=authors,
            abstract=abstract,
            url=url,
            pdf_url=pdf_url,
            publication_date=publication_date,
            citation_count=citation_count,
            venue=venue
        )
    
    def _fallback_search(self, keywords: List[str], max_results: int, 
                        sort_by: SortBy, year_range: Optional[tuple]) -> List[PaperInfo]:
        """
        备用搜索方法（当scholarly不可用时）
        这是一个简化版本，实际项目中可以实现更复杂的爬虫逻辑
        """
        print("使用备用搜索方法...")
        
        # 这里可以实现基于requests的爬虫逻辑
        # 由于Google Scholar有反爬虫机制，这里只返回示例数据
        query = " ".join(keywords)
        
        # 示例数据
        sample_papers = [
            PaperInfo(
                title=f"示例论文: {query}相关研究",
                authors=["作者1", "作者2"],
                abstract=f"这是一篇关于{query}的示例论文摘要...",
                url="https://example.com/paper1",
                pdf_url="https://example.com/paper1.pdf",
                publication_date="2023",
                citation_count=10,
                venue="示例会议"
            )
        ]
        
        return sample_papers[:max_results]
    
    def _sort_papers(self, papers: List[PaperInfo], sort_by: SortBy) -> List[PaperInfo]:
        """根据指定方式排序论文"""
        if sort_by == SortBy.CITATION:
            return sorted(papers, key=lambda p: p.citation_count or 0, reverse=True)
        elif sort_by == SortBy.DATE:
            return sorted(papers, key=lambda p: p.publication_date or "0000", reverse=True)
        else:  # RELEVANCE
            return papers  # scholarly默认按相关性排序
    
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
    
    def get_paper_metrics(self, paper_info: PaperInfo) -> dict:
        """
        获取论文的详细指标信息
        """
        if not SCHOLARLY_AVAILABLE:
            return {}
        
        try:
            # 通过标题搜索获取详细信息
            search_query = scholarly.search_pubs(paper_info.title)
            pub = next(search_query)
            pub_filled = scholarly.fill(pub)
            
            return {
                'citation_count': pub_filled.get('num_citations', 0),
                'h_index': pub_filled.get('hindex', 0),
                'i10_index': pub_filled.get('i10index', 0),
                'cited_by': pub_filled.get('citedby_url', ''),
                'related_articles': pub_filled.get('related_articles', [])
            }
            
        except Exception as e:
            print(f"获取论文指标失败: {e}")
            return {} 