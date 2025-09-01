#!/usr/bin/env python3
"""
SEARCH_PAPER.py - Enhanced Academic Paper Search Tool
Supports interactive mode and multi-platform search (arXiv, Google Scholar)
Python version with RUN environment detection
"""

import os
import sys
import json
import argparse
import hashlib
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

def is_run_environment(command_identifier=None):
    """Check if running in RUN environment by checking environment variables"""
    if command_identifier:
        return os.environ.get(f'RUN_IDENTIFIER_{command_identifier}') == 'True'
    return False

def write_to_json_output(data, command_identifier=None):
    """将结果写入到指定的 JSON 输出文件中"""
    if not is_run_environment(command_identifier):
        return False
    
    # Get the specific output file for this command identifier
    if command_identifier:
        output_file = os.environ.get(f'RUN_DATA_FILE_{command_identifier}')
    else:
        output_file = os.environ.get('RUN_DATA_FILE')
    
    if not output_file:
        return False
    
    try:
        # 确保输出目录存在
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error writing to JSON output file: {e}")
        return False

def get_interactive_query(command_identifier=None):
    """获取交互式查询输入"""
    if is_run_environment(command_identifier):
        # 在RUN环境中，返回错误
        error_data = {
            "success": False,
            "error": "Interactive mode not supported in RUN environment. Please provide a query.",
            "suggestion": "Usage: SEARCH_PAPER 'your query here' --max-results 10"
        }
        write_to_json_output(error_data, command_identifier)
        return None
    
    print(f"=== Academic Paper Search Tool ===", file=sys.stderr)
    print(f"Enter your search query (or 'quit' to exit):", file=sys.stderr)
    print(file=sys.stderr)
    
    try:
        query = input("Search query: ").strip()
        if query.lower() in ['quit', 'exit', 'q']:
            return None
        if not query:
            print(f"Empty query. Please try again.", file=sys.stderr)
            return get_interactive_query(command_identifier)
        return query
    except (KeyboardInterrupt, EOFError):
        print(f"\nSearch cancelled.", file=sys.stderr)
        return None

class MultiPlatformPaperSearcher:
    """多平台论文搜索器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        self.output_dir = Path(__file__).parent / "SEARCH_PAPER_DATA"
        self.results_dir = self.output_dir / "results"
        self.papers_dir = self.output_dir / "papers"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.papers_dir.mkdir(parents=True, exist_ok=True)
    
    def search_papers(self, query: str, max_results: int = 10, sources: List[str] = None) -> Dict[str, Any]:
        """
        搜索论文
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            sources: 搜索源列表，默认为所有源
        
        Returns:
            搜索结果字典
        """
        if sources is None:
            sources = ['arxiv', 'google_scholar']
        
        all_papers = []
        source_results = {}
        
        # 搜索各个平台
        for source in sources:
            try:
                if source == 'arxiv':
                    papers = self._search_arxiv(query, max_results)
                elif source == 'google_scholar':
                    # 对于Google Scholar使用双重阈值机制
                    threshold = min(max_results, 10)  # 默认阈值10，但不超过max_results
                    max_eval = 100  # 默认最大评估100篇论文
                    papers = self._search_google_scholar(query, max_results, threshold, max_eval)
                else:
                    continue
                
                source_results[source] = len(papers)
                all_papers.extend(papers)
                
                # 添加延迟以避免被封
                time.sleep(1)
                
            except Exception as e:
                source_results[source] = f"Error: {str(e)}"
                print(f"Error searching {source}: {e}", file=sys.stderr)
                continue
        
        # 去重和排序
        unique_papers = self._remove_duplicates(all_papers)
        final_papers = unique_papers[:max_results]
        
        # 创建结果
        result = {
            "success": True,
            "query": query,
            "max_results": max_results,
            "total_papers_found": len(final_papers),
            "source_results": source_results,
            "papers": final_papers,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存结果
        self._save_results(result)
        
        return result
    
    def search_papers_with_thresholds(self, query: str, max_results: int = 10, sources: List[str] = None, 
                                    threshold: int = 10, max_eval: int = 100) -> Dict[str, Any]:
        """
        搜索论文（支持Google Scholar双重阈值机制）
        
        Args:
            query: 搜索查询
            max_results: 最大结果数
            sources: 搜索源列表，默认为所有源
            threshold: Google Scholar有效PDF论文数量阈值（默认10）
            max_eval: Google Scholar最大评估论文数量（默认100）
        
        Returns:
            搜索结果字典
        """
        if sources is None:
            sources = ['arxiv', 'google_scholar']
        
        all_papers = []
        source_results = {}
        
        # 搜索各个平台
        for source in sources:
            try:
                if source == 'arxiv':
                    papers = self._search_arxiv(query, max_results)
                elif source == 'google_scholar':
                    # 对于Google Scholar使用双重阈值机制
                    papers = self._search_google_scholar(query, max_results, threshold, max_eval)
                else:
                    continue
                
                source_results[source] = len(papers)
                all_papers.extend(papers)
                
                # 添加延迟以避免被封
                time.sleep(1)
                
            except Exception as e:
                source_results[source] = f"Error: {str(e)}"
                print(f"Error searching {source}: {e}", file=sys.stderr)
                continue
        
        # 去重和排序
        unique_papers = self._remove_duplicates(all_papers)
        final_papers = unique_papers[:max_results]
        
        # 创建结果
        result = {
            "success": True,
            "query": query,
            "max_results": max_results,
            "threshold": threshold,
            "max_eval": max_eval,
            "total_papers_found": len(final_papers),
            "source_results": source_results,
            "papers": final_papers,
            "timestamp": datetime.now().isoformat()
        }
        
        # 保存结果
        self._save_results(result)
        
        return result
    
    def _search_arxiv(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """搜索arXiv，改进搜索策略以提高相关性"""
        papers = []
        
        try:
            # 改进的搜索策略：
            # 1. 主要在标题和摘要中搜索，而不是所有字段
            # 2. 按相关性排序，而不是提交日期
            # 3. 增加机器学习相关分类的权重
            
            # 构建更精确的搜索查询
            # 优先搜索标题和摘要，同时考虑相关分类
            search_parts = []
            
            # 在标题和摘要中搜索
            search_parts.append(f"ti:{query}")  # 标题
            search_parts.append(f"abs:{query}")  # 摘要
            
            # 根据查询内容添加相关分类
            if any(keyword in query.lower() for keyword in ['machine learning', 'optimization', 'neural', 'deep learning', 'gradient']):
                search_parts.append("cat:cs.LG")  # 机器学习
                search_parts.append("cat:cs.AI")  # 人工智能
                search_parts.append("cat:stat.ML")  # 统计机器学习
            
            if any(keyword in query.lower() for keyword in ['optimization', 'gradient', 'descent', 'sgd', 'adam']):
                search_parts.append("cat:math.OC")  # 优化与控制
            
            # 使用OR连接不同的搜索条件
            search_query = " OR ".join(search_parts)
            
            # 使用arXiv API，按相关性排序
            api_url = f"http://export.arxiv.org/api/query?search_query={search_query}&start=0&max_results={max_results * 2}&sortBy=relevance&sortOrder=descending"
            
            print(f"arXiv search query: {search_query}", file=sys.stderr)
            
            response = self.session.get(api_url, timeout=30)
            response.raise_for_status()
            
            # 解析XML响应
            from xml.etree import ElementTree as ET
            root = ET.fromstring(response.content)
            
            # 定义命名空间
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }
            
            for entry in root.findall('atom:entry', namespaces):
                try:
                    paper = self._parse_arxiv_entry(entry, namespaces)
                    if paper and self._is_relevant_arxiv_paper(paper, query):
                        papers.append(paper)
                        if len(papers) >= max_results:
                            break
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"arXiv search error: {e}", file=sys.stderr)
        
        return papers
    
    def _is_relevant_arxiv_paper(self, paper: Dict[str, Any], query: str) -> bool:
        """检查arXiv论文是否与查询相关"""
        try:
            title = paper.get('title', '').lower()
            abstract = paper.get('abstract', '').lower()
            query_lower = query.lower()
            
            # 提取查询中的关键词
            query_keywords = set(query_lower.split())
            
            # 检查标题和摘要中是否包含查询关键词
            title_words = set(title.split())
            abstract_words = set(abstract.split())
            
            # 计算关键词匹配度
            title_matches = len(query_keywords.intersection(title_words))
            abstract_matches = len(query_keywords.intersection(abstract_words))
            
            # 至少在标题或摘要中有关键词匹配
            if title_matches > 0 or abstract_matches > 0:
                return True
            
            # 对于优化算法相关查询，检查特定术语
            if any(keyword in query_lower for keyword in ['optimization', 'gradient', 'sgd', 'adam']):
                optimization_terms = ['optimization', 'gradient', 'descent', 'sgd', 'adam', 'optimizer', 'learning rate', 'convergence']
                if any(term in title or term in abstract for term in optimization_terms):
                    return True
            
            # 对于机器学习查询，检查ML相关术语
            if any(keyword in query_lower for keyword in ['machine learning', 'neural', 'deep learning']):
                ml_terms = ['machine learning', 'neural', 'deep learning', 'classification', 'regression', 'training', 'model']
                if any(term in title or term in abstract for term in ml_terms):
                    return True
            
            return False
            
        except Exception:
            return True  # 如果检查出错，保守地认为相关
    
    def _search_google_scholar(self, query: str, max_results: int, threshold: int = 10, max_eval: int = 100) -> List[Dict[str, Any]]:
        """搜索Google Scholar，使用双重阈值机制
        
        Args:
            query: 搜索查询
            max_results: 期望的最大结果数（用于兼容性）
            threshold: 有效PDF论文数量阈值，达到此数量自动停止（默认10）
            max_eval: 最大评估论文数量，不管是否有PDF都会停止（默认100）
        """
        papers = []
        evaluated_count = 0
        
        try:
            # 使用更大的搜索范围，因为需要评估更多论文
            search_num = min(max_eval, 100)  # 最多搜索100个结果
            
            # 使用Google Scholar搜索URL，添加filetype:pdf参数提高PDF结果比例
            search_url = f"https://scholar.google.com/scholar?q={query}+filetype:pdf&hl=en&num={search_num}"
            
            print(f"Searching Google Scholar with dual-threshold: threshold={threshold}, max_eval={max_eval}", file=sys.stderr)
            print(f"Search URL: {search_url}", file=sys.stderr)
            
            response = self.session.get(search_url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找论文条目
            paper_entries = soup.find_all('div', class_='gs_r gs_or gs_scl')
            
            print(f"Found {len(paper_entries)} paper entries from Google Scholar", file=sys.stderr)
            
            for entry in paper_entries:
                try:
                    evaluated_count += 1
                    print(f"Evaluating paper {evaluated_count}/{max_eval}...", file=sys.stderr)
                    
                    paper = self._parse_google_scholar_entry(entry)
                    if paper:
                        papers.append(paper)
                        print(f"Valid PDF paper found: {len(papers)}/{threshold}", file=sys.stderr)
                        
                        # 阈值1：如果已经找到足够的有效PDF论文，停止处理
                        if len(papers) >= threshold:
                            print(f"Reached threshold of {threshold} valid PDF papers, stopping search", file=sys.stderr)
                            break
                    else:
                        print(f"Paper {evaluated_count} skipped (no valid PDF)", file=sys.stderr)
                    
                    # 阈值2：如果已经评估了足够多的论文，停止处理
                    if evaluated_count >= max_eval:
                        print(f"Reached max evaluation limit of {max_eval} papers, stopping search", file=sys.stderr)
                        break
                        
                except Exception as e:
                    evaluated_count += 1
                    print(f"Error parsing entry {evaluated_count}: {e}", file=sys.stderr)
                    
                    # 即使出错也要检查max_eval阈值
                    if evaluated_count >= max_eval:
                        print(f"Reached max evaluation limit of {max_eval} papers, stopping search", file=sys.stderr)
                        break
                    continue
            
            print(f"Google Scholar search completed: {len(papers)} valid papers found after evaluating {evaluated_count} papers", file=sys.stderr)
                    
        except Exception as e:
            print(f"Google Scholar search error: {e}", file=sys.stderr)
        
        return papers
    

    
    def _parse_arxiv_entry(self, entry, namespaces) -> Optional[Dict[str, Any]]:
        """解析arXiv条目"""
        try:
            title = entry.find('atom:title', namespaces).text.strip()
            
            # 提取作者
            authors = []
            for author in entry.findall('atom:author', namespaces):
                name = author.find('atom:name', namespaces)
                if name is not None:
                    authors.append(name.text.strip())
            
            # 提取摘要
            summary = entry.find('atom:summary', namespaces)
            abstract = summary.text.strip() if summary is not None else ""
            
            # 提取URL
            id_elem = entry.find('atom:id', namespaces)
            url = id_elem.text.strip() if id_elem is not None else ""
            
            # 生成PDF URL
            pdf_url = url.replace('/abs/', '/pdf/') + '.pdf' if url else ""
            
            # 提取发布日期
            published = entry.find('atom:published', namespaces)
            pub_date = published.text.strip()[:10] if published is not None else ""
            
            return {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": url,
                "pdf_url": pdf_url,
                "publication_date": pub_date,
                "venue": "arXiv preprint",
                "citation_count": None,
                "source": "arxiv"
            }
            
        except Exception as e:
            print(f"Error parsing arXiv entry: {e}", file=sys.stderr)
            return None
    
    def _parse_google_scholar_entry(self, entry) -> Optional[Dict[str, Any]]:
        """解析Google Scholar条目，只返回有PDF下载链接的论文"""
        try:
            # 提取标题和URL
            title_elem = entry.find('h3', class_='gs_rt')
            if not title_elem:
                return None
            
            title_link = title_elem.find('a')
            if title_link:
                title = title_link.get_text().strip()
                url = title_link.get('href', '')
            else:
                title = title_elem.get_text().strip()
                url = ""
            
            # 提取PDF链接 - 查找右侧的PDF链接
            pdf_url = ""
            
            # 方法1: 查找 gs_or_ggsm 类中的PDF链接
            pdf_links = entry.find_all('a', href=True)
            for link in pdf_links:
                href = link.get('href', '')
                link_text = link.get_text().strip().lower()
                
                # 检查是否是PDF链接
                if (href.endswith('.pdf') or 
                    'pdf' in link_text or 
                    'filetype:pdf' in href or
                    '.pdf' in href):
                    
                    # 确保是完整的URL
                    if href.startswith('http'):
                        pdf_url = href
                        break
                    elif href.startswith('/'):
                        pdf_url = 'https://scholar.google.com' + href
                        break
            
            # 方法2: 如果没找到PDF链接，查找可能的直接链接
            if not pdf_url:
                # 查找可能包含PDF的链接
                for link in pdf_links:
                    href = link.get('href', '')
                    if href and href.startswith('http') and href != url:
                        # 简单检查URL是否可能包含PDF
                        if any(domain in href.lower() for domain in ['arxiv.org', 'researchgate.net', 'academia.edu', 'ieee.org', 'acm.org', 'springer.com', 'sciencedirect.com']):
                            # 对于arXiv链接，转换为PDF格式
                            if 'arxiv.org/abs/' in href:
                                pdf_url = href.replace('/abs/', '/pdf/') + '.pdf'
                                break
                            else:
                                pdf_url = href
                                break
            
            # 如果没有找到PDF链接，跳过这篇论文
            if not pdf_url:
                print(f"Skipping paper without PDF: {title[:50]}...", file=sys.stderr)
                return None
            
            # 验证PDF链接是否可访问（简单检查，避免过多请求）
            if not self._validate_pdf_url(pdf_url):
                print(f"Skipping paper with invalid PDF URL: {title[:50]}...", file=sys.stderr)
                return None
            
            # 提取作者和期刊信息
            authors_elem = entry.find('div', class_='gs_a')
            authors = []
            venue = ""
            pub_date = ""
            
            if authors_elem:
                text = authors_elem.get_text()
                if text:  # 确保 text 不为 None
                    parts = text.split(' - ')
                    if len(parts) >= 2:
                        authors_text = parts[0]
                        venue_text = parts[1]
                        
                        # 提取作者
                        if authors_text:
                            authors = [a.strip() for a in authors_text.split(',')]
                        
                        # 提取期刊和日期
                        if venue_text:  # 确保 venue_text 不为 None
                            venue_match = re.search(r'^([^,]+)', venue_text)
                            if venue_match:
                                venue = venue_match.group(1).strip()
                            
                            date_match = re.search(r'(\d{4})', venue_text)
                            if date_match:
                                pub_date = date_match.group(1)
            
            # 提取摘要
            abstract_elem = entry.find('div', class_='gs_rs')
            abstract = abstract_elem.get_text().strip() if abstract_elem else ""
            
            # 提取引用数
            citation_elem = entry.find('div', class_='gs_fl')
            citation_count = None
            if citation_elem:
                citation_link = citation_elem.find('a', string=re.compile(r'Cited by'))
                if citation_link:
                    citation_text = citation_link.get_text()
                    if citation_text:  # 确保 citation_text 不为 None
                        citation_match = re.search(r'(\d+)', citation_text)
                        if citation_match:
                            citation_count = int(citation_match.group(1))
            
            print(f"Found paper with PDF: {title[:50]}... -> {pdf_url}", file=sys.stderr)
            
            return {
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "url": url,
                "pdf_url": pdf_url,
                "publication_date": pub_date,
                "venue": venue,
                "citation_count": citation_count,
                "source": "google_scholar"
            }
            
        except Exception as e:
            print(f"Error parsing Google Scholar entry: {e}", file=sys.stderr)
            return None
    
    def _validate_pdf_url(self, pdf_url: str) -> bool:
        """验证PDF URL是否可访问（简单检查）"""
        try:
            # 基本URL格式检查
            if not pdf_url or not pdf_url.startswith('http'):
                return False
            
            # 对于已知的可靠域名，跳过验证以避免过多请求
            reliable_domains = [
                'arxiv.org', 'ieee.org', 'acm.org', 'springer.com', 
                'sciencedirect.com', 'nature.com', 'science.org'
            ]
            
            if any(domain in pdf_url.lower() for domain in reliable_domains):
                return True
            
            # 对于其他域名，进行简单的HEAD请求检查
            try:
                response = self.session.head(pdf_url, timeout=5, allow_redirects=True)
                content_type = response.headers.get('content-type', '').lower()
                
                # 检查是否是PDF内容或可能的PDF
                if ('pdf' in content_type or 
                    response.status_code == 200 or 
                    response.status_code == 302):  # 302表示重定向，可能有效
                    return True
                    
            except:
                # 如果请求失败，对于某些域名仍然认为可能有效
                maybe_valid_domains = ['researchgate.net', 'academia.edu', 'semanticscholar.org']
                if any(domain in pdf_url.lower() for domain in maybe_valid_domains):
                    return True
                return False
            
            return False
            
        except Exception:
            return False
    
    def _remove_duplicates(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """去重"""
        unique_papers = []
        seen_titles = set()
        
        for paper in papers:
            title = paper.get('title', '').lower().strip()
            title_hash = hashlib.md5(title.encode()).hexdigest()
            
            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                unique_papers.append(paper)
        
        return unique_papers
    
    def _save_results(self, result: Dict[str, Any]):
        """保存搜索结果到JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"search_results_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {result_file}", file=sys.stderr)

        # 保存每篇论文到单独的文件
        for paper in result.get("papers", []):
            paper_title = paper.get("title", "untitled").replace("/", "-")
            paper_file = self.papers_dir / f"{paper_title}.json"
            with open(paper_file, 'w', encoding='utf-8') as f:
                json.dump(paper, f, ensure_ascii=False, indent=2)
            print(f"Paper saved to {paper_file}", file=sys.stderr)

def format_output(result: Dict[str, Any], command_identifier=None):
    """格式化输出"""
    if is_run_environment(command_identifier):
        # 在RUN环境中，直接输出JSON到stdout
        # write_to_json_output(result, run_context)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 直接调用时，输出格式化的结果
        print(f"\n=== Search Results for: '{result['query']}' ===")
        print(f"Found {result['total_papers_found']} papers")
        
        if 'source_results' in result:
            print(f"\nSource Results:")
            for source, count in result['source_results'].items():
                print(f"  {source}: {count}")
        
        print(f"\nPapers:")
        for i, paper in enumerate(result['papers'], 1):
            print(f"\n{i}. {paper['title']}")
            if paper['authors']:
                authors_str = ', '.join(paper['authors'][:3])
                if len(paper['authors']) > 3:
                    authors_str += f" et al."
                print(f"   Authors: {authors_str}")
            if paper['venue']:
                print(f"   Venue: {paper['venue']}")
            if paper['publication_date']:
                print(f"   Date: {paper['publication_date']}")
            if paper['citation_count']:
                print(f"   Citations: {paper['citation_count']}")
            if paper['url']:
                print(f"   URL: {paper['url']}")
            if paper['pdf_url']:
                print(f"   PDF: {paper['pdf_url']}")
            if paper['abstract']:
                abstract = paper['abstract'][:200] + "..." if len(paper['abstract']) > 200 else paper['abstract']
                print(f"   Abstract: {abstract}")

def show_help():
    """显示帮助信息"""
    help_text = """SEARCH_PAPER - Enhanced Academic Paper Search Tool

Usage: SEARCH_PAPER [query] [options]

Arguments:
  query                Search query (if not provided, interactive mode will start)

Options:
  --max-results N      Maximum number of results (default: 10)
  --sources LIST       Comma-separated list of sources: arxiv,google_scholar
  --help, -h           Show this help message

Examples:
  SEARCH_PAPER                                    # Interactive mode
  SEARCH_PAPER "machine learning"                 # Search all sources
  SEARCH_PAPER "deep learning" --max-results 20  # Limit results
  SEARCH_PAPER "NLP" --sources arxiv,google_scholar  # Specific sources
  SEARCH_PAPER --help                             # Show help"""
    
    print(help_text)

def main():
    """主函数"""
    # 获取command_identifier
    args_list = sys.argv[1:]
    command_identifier = None
    
    # 检查是否被RUN调用（第一个参数是command_identifier）
    if args_list and is_run_environment(args_list[0]):
        command_identifier = args_list[0]
        sys.argv = [sys.argv[0]] + args_list[1:]  # 移除command_identifier，保留实际参数
    
    parser = argparse.ArgumentParser(
        prog='SEARCH_PAPER',
        description="SEARCH_PAPER - Enhanced Academic Paper Search Tool"
    )
    parser.add_argument("query", nargs='?', default=None, help="Search query (if not provided, interactive mode will start)")
    parser.add_argument("--max-results", type=int, default=10, help="Maximum number of results")
    parser.add_argument("--sources", type=str, help="Comma-separated list of sources: arxiv,google_scholar")
    parser.add_argument("--threshold", type=int, default=10, help="Threshold for valid PDF papers (Google Scholar only)")
    parser.add_argument("--max-eval", type=int, default=100, help="Maximum number of papers to evaluate (Google Scholar only)")
    
    args = parser.parse_args()
    
    query = args.query
    sources = args.sources.split(',') if args.sources else None
    
    if query is None:
        try:
            # 仅在非RUN环境下提示输入
            if not os.environ.get('RUN_IDENTIFIER'):
                 print(f"Search query: ", file=sys.stderr, end="")
            query = input().strip()
            if not query:
                print(f"Empty query, exiting.", file=sys.stderr)
                # 在RUN环境下，返回一个表示错误的JSON
                if os.environ.get('RUN_IDENTIFIER'):
                    print(json.dumps({"success": False, "error": "Empty query"}, ensure_ascii=False, indent=2))
                    return 0
                return 1
        except (KeyboardInterrupt, EOFError):
            print(f"\nSearch cancelled.", file=sys.stderr)
            if os.environ.get('RUN_IDENTIFIER'):
                print(json.dumps({"success": False, "error": "Search cancelled"}, ensure_ascii=False, indent=2))
                return 0
            return 1
            
    searcher = MultiPlatformPaperSearcher()
    
    # 传递新的阈值参数
    if 'google_scholar' in (sources or ['arxiv', 'google_scholar']):
        # 如果包含Google Scholar，需要修改搜索方法以支持新参数
        result = searcher.search_papers_with_thresholds(query, args.max_results, sources, args.threshold, args.max_eval)
    else:
        result = searcher.search_papers(query, args.max_results, sources)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 