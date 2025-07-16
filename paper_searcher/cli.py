#!/usr/bin/env python3
"""
Paper Searcher CLI
论文搜索命令行工具
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from base_searcher import SortBy
from google_scholar_searcher import GoogleScholarSearcher
from arxiv_searcher import ArxivSearcher
from keyword_extractor import KeywordExtractor


class PaperSearchCLI:
    """论文搜索CLI类"""
    
    def __init__(self):
        self.keyword_extractor = KeywordExtractor()
        self.searchers = {
            'google_scholar': GoogleScholarSearcher(),
            'arxiv': ArxivSearcher()
        }
    
    def create_parser(self) -> argparse.ArgumentParser:
        """创建命令行参数解析器"""
        parser = argparse.ArgumentParser(
            description='论文搜索工具 - 搜索Google Scholar和Arxiv上的学术论文',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例用法:
  python cli.py "深度学习在计算机视觉中的应用" --max-results 20 --sort-by citation
  python cli.py "machine learning optimization" --sources arxiv --year-range 2020 2023
  python cli.py "natural language processing" --output-dir ./results --download-pdfs
  python cli.py --interactive
            """
        )
        
        # 主要参数
        parser.add_argument(
            'query',
            nargs='?',
            help='搜索查询描述（如果不提供，将进入交互模式）'
        )
        
        # 搜索选项
        parser.add_argument(
            '--sources', '-s',
            nargs='+',
            choices=['google_scholar', 'arxiv', 'all'],
            default=['all'],
            help='搜索源 (默认: all)'
        )
        
        parser.add_argument(
            '--max-results', '-n',
            type=int,
            default=10,
            help='每个源的最大结果数量 (默认: 10)'
        )
        
        parser.add_argument(
            '--sort-by',
            choices=['relevance', 'citation', 'date'],
            default='relevance',
            help='排序方式 (默认: relevance)'
        )
        
        parser.add_argument(
            '--year-range',
            nargs=2,
            type=int,
            metavar=('START_YEAR', 'END_YEAR'),
            help='年份范围过滤 (例如: --year-range 2020 2023)'
        )
        
        # 输出选项
        parser.add_argument(
            '--output-dir', '-o',
            type=str,
            default='paper_searcher/data',
            help='输出目录 (默认: paper_searcher/data)'
        )
        
        parser.add_argument(
            '--download-pdfs',
            action='store_true',
            help='下载论文PDF文件'
        )
        
        parser.add_argument(
            '--save-format',
            choices=['json', 'csv', 'txt'],
            default='json',
            help='保存格式 (默认: json)'
        )
        
        # 关键词选项
        parser.add_argument(
            '--keywords',
            nargs='+',
            help='手动指定关键词（覆盖自动提取）'
        )
        
        parser.add_argument(
            '--show-keywords',
            action='store_true',
            help='显示提取的关键词'
        )
        
        parser.add_argument(
            '--max-keywords',
            type=int,
            default=10,
            help='最大关键词数量 (默认: 10)'
        )
        
        # 其他选项
        parser.add_argument(
            '--interactive', '-i',
            action='store_true',
            help='进入交互模式'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='详细输出'
        )
        
        parser.add_argument(
            '--config',
            type=str,
            help='配置文件路径'
        )
        
        return parser
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """运行CLI"""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        try:
            # 加载配置
            config = self.load_config(parsed_args.config) if parsed_args.config else {}
            
            # 合并配置和命令行参数
            final_args = self.merge_config_and_args(config, parsed_args)
            
            # 交互模式
            if final_args.interactive or not final_args.query:
                return self.interactive_mode()
            
            # 执行搜索
            return self.execute_search(final_args)
            
        except KeyboardInterrupt:
            print("\n搜索被用户中断")
            return 1
        except Exception as e:
            print(f"错误: {e}")
            if parsed_args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def interactive_mode(self) -> int:
        """交互模式"""
        print("=== 论文搜索工具 - 交互模式 ===")
        print("输入 'help' 查看帮助，输入 'quit' 退出")
        
        while True:
            try:
                query = input("\n请输入搜索描述: ").strip()
                
                if query.lower() in ['quit', 'exit', 'q']:
                    print("再见！")
                    break
                
                if query.lower() == 'help':
                    self.show_help()
                    continue
                
                if not query:
                    continue
                
                # 获取搜索参数
                search_params = self.get_interactive_params()
                
                # 创建参数对象
                class Args:
                    def __init__(self, **kwargs):
                        for k, v in kwargs.items():
                            setattr(self, k, v)
                
                args = Args(
                    query=query,
                    sources=search_params.get('sources', ['all']),
                    max_results=search_params.get('max_results', 10),
                    sort_by=search_params.get('sort_by', 'relevance'),
                    year_range=search_params.get('year_range'),
                    output_dir=search_params.get('output_dir', 'paper_searcher/data'),
                    download_pdfs=search_params.get('download_pdfs', False),
                    save_format=search_params.get('save_format', 'json'),
                    keywords=None,
                    show_keywords=True,
                    max_keywords=10,
                    verbose=True
                )
                
                # 执行搜索
                self.execute_search(args)
                
            except KeyboardInterrupt:
                print("\n\n再见！")
                break
            except Exception as e:
                print(f"错误: {e}")
        
        return 0
    
    def get_interactive_params(self) -> Dict[str, Any]:
        """获取交互式参数"""
        params = {}
        
        # 搜索源
        sources_input = input("搜索源 (google_scholar/arxiv/all) [all]: ").strip()
        if sources_input:
            if sources_input == 'all':
                params['sources'] = ['all']
            else:
                params['sources'] = [s.strip() for s in sources_input.split(',')]
        
        # 结果数量
        max_results_input = input("最大结果数量 [10]: ").strip()
        if max_results_input:
            try:
                params['max_results'] = int(max_results_input)
            except ValueError:
                print("无效的数量，使用默认值 10")
        
        # 排序方式
        sort_by_input = input("排序方式 (relevance/citation/date) [relevance]: ").strip()
        if sort_by_input and sort_by_input in ['relevance', 'citation', 'date']:
            params['sort_by'] = sort_by_input
        
        # 年份范围
        year_range_input = input("年份范围 (例如: 2020 2023) [无]: ").strip()
        if year_range_input:
            try:
                years = year_range_input.split()
                if len(years) == 2:
                    params['year_range'] = (int(years[0]), int(years[1]))
            except ValueError:
                print("无效的年份范围")
        
        # 输出目录
        output_dir_input = input("输出目录 [paper_searcher/data]: ").strip()
        if output_dir_input:
            params['output_dir'] = output_dir_input
        
        # 下载PDF
        download_pdfs_input = input("下载PDF文件? (y/n) [n]: ").strip().lower()
        params['download_pdfs'] = download_pdfs_input in ['y', 'yes']
        
        return params
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
可用命令:
- help: 显示此帮助信息
- quit/exit/q: 退出程序

搜索参数:
- 搜索源: google_scholar, arxiv, all
- 排序方式: relevance (相关性), citation (引用量), date (时间)
- 年份范围: 例如 "2020 2023"
- 结果数量: 每个源返回的最大结果数
- 输出目录: 结果保存的目录
- 下载PDF: 是否下载论文PDF文件

示例搜索:
- "深度学习在计算机视觉中的应用"
- "machine learning optimization algorithms"
- "natural language processing transformer"
        """
        print(help_text)
    
    def execute_search(self, args) -> int:
        """执行搜索"""
        # 提取关键词
        if args.keywords:
            keywords = args.keywords
        else:
            keywords = self.keyword_extractor.extract_keywords(
                args.query, max_keywords=args.max_keywords
            )
        
        if args.show_keywords:
            print(f"提取的关键词: {', '.join(keywords)}")
        
        # 确定搜索源
        sources_to_search = []
        if 'all' in args.sources:
            sources_to_search = list(self.searchers.keys())
        else:
            sources_to_search = [s for s in args.sources if s in self.searchers]
        
        if not sources_to_search:
            print("错误: 没有可用的搜索源")
            return 1
        
        # 转换排序方式
        sort_by = SortBy(args.sort_by)
        
        # 转换年份范围
        year_range = tuple(args.year_range) if args.year_range else None
        
        # 执行搜索
        all_papers = []
        for source in sources_to_search:
            print(f"\n正在搜索 {source}...")
            
            searcher = self.searchers[source]
            papers = searcher.search(
                keywords=keywords,
                max_results=args.max_results,
                sort_by=sort_by,
                year_range=year_range
            )
            
            all_papers.extend(papers)
            print(f"从 {source} 找到 {len(papers)} 篇论文")
        
        if not all_papers:
            print("没有找到任何论文")
            return 0
        
        # 保存结果
        self.save_results(all_papers, args)
        
        # 下载PDF
        if args.download_pdfs:
            self.download_pdfs(all_papers, args)
        
        # 显示摘要
        self.show_summary(all_papers, args)
        
        return 0
    
    def save_results(self, papers, args):
        """保存搜索结果"""
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存JSON格式
        if args.save_format in ['json', 'all']:
            json_path = output_dir / 'papers.json'
            papers_data = {
                'query': args.query,
                'keywords': self.keyword_extractor.extract_keywords(args.query),
                'total_papers': len(papers),
                'search_params': {
                    'sources': args.sources,
                    'max_results': args.max_results,
                    'sort_by': args.sort_by,
                    'year_range': args.year_range
                },
                'papers': [paper.to_dict() for paper in papers]
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(papers_data, f, ensure_ascii=False, indent=2)
            
            print(f"结果已保存到: {json_path}")
        
        # 保存CSV格式
        if args.save_format in ['csv', 'all']:
            self.save_csv(papers, output_dir / 'papers.csv')
        
        # 保存TXT格式
        if args.save_format in ['txt', 'all']:
            self.save_txt(papers, output_dir / 'papers.txt')
    
    def save_csv(self, papers, csv_path):
        """保存为CSV格式"""
        import csv
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Title', 'Authors', 'Abstract', 'URL', 'PDF_URL', 
                           'Publication_Date', 'Citation_Count', 'Venue'])
            
            for paper in papers:
                writer.writerow([
                    paper.title,
                    '; '.join(paper.authors),
                    paper.abstract,
                    paper.url,
                    paper.pdf_url or '',
                    paper.publication_date or '',
                    paper.citation_count or '',
                    paper.venue or ''
                ])
        
        print(f"CSV结果已保存到: {csv_path}")
    
    def save_txt(self, papers, txt_path):
        """保存为TXT格式"""
        with open(txt_path, 'w', encoding='utf-8') as f:
            for i, paper in enumerate(papers, 1):
                f.write(f"{i}. {paper.title}\n")
                f.write(f"   作者: {'; '.join(paper.authors)}\n")
                f.write(f"   摘要: {paper.abstract[:200]}...\n")
                f.write(f"   链接: {paper.url}\n")
                if paper.pdf_url:
                    f.write(f"   PDF: {paper.pdf_url}\n")
                if paper.publication_date:
                    f.write(f"   发表日期: {paper.publication_date}\n")
                if paper.citation_count:
                    f.write(f"   引用数: {paper.citation_count}\n")
                if paper.venue:
                    f.write(f"   会议/期刊: {paper.venue}\n")
                f.write("\n" + "="*80 + "\n\n")
        
        print(f"TXT结果已保存到: {txt_path}")
    
    def download_pdfs(self, papers, args):
        """下载PDF文件"""
        output_dir = Path(args.output_dir)
        papers_dir = output_dir / 'papers'
        papers_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = 0
        for i, paper in enumerate(papers, 1):
            if paper.pdf_url:
                # 生成安全的文件名
                safe_title = "".join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_title = safe_title[:100]  # 限制长度
                filename = f"{i:03d}_{safe_title}.pdf"
                
                pdf_path = papers_dir / filename
                
                # 根据URL来源选择合适的下载器
                if 'arxiv.org' in paper.pdf_url:
                    searcher = self.searchers['arxiv']
                else:
                    searcher = self.searchers['google_scholar']
                
                if searcher.download_paper(paper, str(pdf_path)):
                    downloaded += 1
        
        print(f"成功下载 {downloaded}/{len([p for p in papers if p.pdf_url])} 个PDF文件")
    
    def show_summary(self, papers, args):
        """显示搜索摘要"""
        print(f"\n=== 搜索摘要 ===")
        print(f"查询: {args.query}")
        print(f"总共找到: {len(papers)} 篇论文")
        
        # 按来源统计
        source_counts = {}
        for paper in papers:
            # 根据URL判断来源
            if 'arxiv.org' in paper.url:
                source = 'Arxiv'
            elif 'scholar.google' in paper.url:
                source = 'Google Scholar'
            else:
                source = '其他'
            
            source_counts[source] = source_counts.get(source, 0) + 1
        
        for source, count in source_counts.items():
            print(f"  {source}: {count} 篇")
        
        # 显示前几篇论文的标题
        print(f"\n前5篇论文:")
        for i, paper in enumerate(papers[:5], 1):
            print(f"  {i}. {paper.title}")
            if paper.citation_count:
                print(f"     引用数: {paper.citation_count}")
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            return {}
    
    def merge_config_and_args(self, config: Dict[str, Any], args) -> argparse.Namespace:
        """合并配置和命令行参数"""
        # 命令行参数优先级更高
        for key, value in config.items():
            if hasattr(args, key) and getattr(args, key) is None:
                setattr(args, key, value)
        
        return args


def main():
    """主函数"""
    cli = PaperSearchCLI()
    return cli.run()


if __name__ == '__main__':
    sys.exit(main()) 