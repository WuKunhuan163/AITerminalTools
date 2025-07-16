"""
基础搜索器抽象类
定义了所有论文搜索器必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os
from datetime import datetime


class SortBy(Enum):
    """排序方式枚举"""
    RELEVANCE = "relevance"  # 相关性
    CITATION = "citation"    # 引用量
    DATE = "date"           # 时间
    

@dataclass
class PaperInfo:
    """论文信息数据类"""
    title: str
    authors: List[str]
    abstract: str
    url: str
    pdf_url: Optional[str] = None
    publication_date: Optional[str] = None
    citation_count: Optional[int] = None
    venue: Optional[str] = None  # 会议/期刊名称
    doi: Optional[str] = None
    keywords: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'url': self.url,
            'pdf_url': self.pdf_url,
            'publication_date': self.publication_date,
            'citation_count': self.citation_count,
            'venue': self.venue,
            'doi': self.doi,
            'keywords': self.keywords or []
        }


class BaseSearcher(ABC):
    """基础搜索器抽象类"""
    
    def __init__(self, name: str):
        self.name = name
        self.search_history = []
    
    @abstractmethod
    def search(self, keywords: List[str], max_results: int = 10, 
               sort_by: SortBy = SortBy.RELEVANCE, 
               year_range: Optional[tuple] = None) -> List[PaperInfo]:
        """
        搜索论文
        
        Args:
            keywords: 搜索关键词列表
            max_results: 最大结果数量
            sort_by: 排序方式
            year_range: 年份范围 (start_year, end_year)
            
        Returns:
            论文信息列表
        """
        pass
    
    @abstractmethod
    def download_paper(self, paper_info: PaperInfo, save_path: str) -> bool:
        """
        下载论文PDF
        
        Args:
            paper_info: 论文信息
            save_path: 保存路径
            
        Returns:
            是否下载成功
        """
        pass
    
    def save_results(self, papers: List[PaperInfo], output_dir: str) -> None:
        """
        保存搜索结果
        
        Args:
            papers: 论文列表
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存论文信息到JSON文件
        papers_data = {
            'search_time': datetime.now().isoformat(),
            'searcher': self.name,
            'total_papers': len(papers),
            'papers': [paper.to_dict() for paper in papers]
        }
        
        json_path = os.path.join(output_dir, 'papers.json')
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(papers_data, f, ensure_ascii=False, indent=2)
        
        # 创建papers子目录用于存放PDF
        papers_dir = os.path.join(output_dir, 'papers')
        os.makedirs(papers_dir, exist_ok=True)
        
        print(f"结果已保存到: {output_dir}")
        print(f"论文信息: {json_path}")
        print(f"PDF文件夹: {papers_dir}")
    
    def get_search_history(self) -> List[Dict[str, Any]]:
        """获取搜索历史"""
        return self.search_history
    
    def add_to_history(self, keywords: List[str], result_count: int):
        """添加搜索记录到历史"""
        self.search_history.append({
            'timestamp': datetime.now().isoformat(),
            'keywords': keywords,
            'result_count': result_count,
            'searcher': self.name
        }) 