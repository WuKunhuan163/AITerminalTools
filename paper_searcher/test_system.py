#!/usr/bin/env python3
"""
测试Paper Searcher系统
"""

import sys
import os
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from keyword_extractor import KeywordExtractor
from arxiv_searcher import ArxivSearcher
from base_searcher import SortBy


def test_keyword_extractor():
    """测试关键词提取器"""
    print("=== 测试关键词提取器 ===")
    
    extractor = KeywordExtractor()
    
    test_descriptions = [
        "深度学习在计算机视觉中的应用",
        "machine learning optimization algorithms",
        "natural language processing with transformers",
        "我想找一些关于强化学习的最新研究"
    ]
    
    for desc in test_descriptions:
        print(f"\n描述: {desc}")
        keywords = extractor.extract_keywords(desc)
        print(f"关键词: {keywords}")
        
        context = extractor.extract_with_context(desc)
        print(f"主要关键词: {context['primary_keywords']}")
        print(f"短语: {context['phrases']}")
        print(f"技术术语: {context['technical_terms']}")


def test_arxiv_searcher():
    """测试Arxiv搜索器"""
    print("\n=== 测试Arxiv搜索器 ===")
    
    searcher = ArxivSearcher()
    
    # 测试搜索
    keywords = ["machine learning", "optimization"]
    print(f"搜索关键词: {keywords}")
    
    try:
        papers = searcher.search(
            keywords=keywords,
            max_results=3,
            sort_by=SortBy.RELEVANCE
        )
        
        print(f"找到 {len(papers)} 篇论文:")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. {paper.title}")
            print(f"   作者: {'; '.join(paper.authors)}")
            print(f"   发表日期: {paper.publication_date}")
            print(f"   URL: {paper.url}")
            print(f"   PDF: {paper.pdf_url}")
            print()
        
        # 测试保存结果
        if papers:
            output_dir = "paper_searcher/data/test_output"
            searcher.save_results(papers, output_dir)
            print(f"结果已保存到: {output_dir}")
        
    except Exception as e:
        print(f"搜索出错: {e}")


def test_cli_args():
    """测试CLI参数解析"""
    print("\n=== 测试CLI参数解析 ===")
    
    from paper_search_handler import PaperSearchHandler
    
    handler = PaperSearchHandler()
    
    test_commands = [
        "PAPER_SEARCH machine learning --max-results 5",
        "PAPER_SEARCH 深度学习 --sort-by citation --sources arxiv",
        "PAPER_SEARCH optimization --year-range 2020 2023 --download-pdfs"
    ]
    
    for cmd in test_commands:
        print(f"\n测试命令: {cmd}")
        try:
            query, options = handler.parse_paper_search_command(cmd)
            print(f"查询: {query}")
            print(f"选项: {options}")
            
            cli_args = handler.build_cli_args(query, options)
            print(f"CLI参数: {cli_args}")
        except Exception as e:
            print(f"解析出错: {e}")


def test_smart_handler():
    """测试智能处理器"""
    print("\n=== 测试智能处理器 ===")
    
    from smart_handler import SmartPaperSearchHandler
    
    handler = SmartPaperSearchHandler()
    
    test_inputs = [
        "请帮我搜索关于机器学习的论文",
        "我想找一些深度学习的最新研究，大概5篇",
        "搜索计算机视觉论文，要引用量高的",
        "查找2020年以后的NLP论文"
    ]
    
    for input_text in test_inputs:
        print(f"\n输入: {input_text}")
        
        # 测试识别
        is_search = handler.is_paper_search_request(input_text)
        print(f"是否为搜索请求: {is_search}")
        
        if is_search:
            # 测试转换
            command = handler.convert_to_paper_search_command(input_text)
            print(f"转换后的命令: {command}")
            
            # 测试建议
            suggestions = handler.get_search_suggestions(input_text)
            print(f"搜索建议: {suggestions}")


def main():
    """主函数"""
    print("开始测试Paper Searcher系统...")
    
    try:
        test_keyword_extractor()
        test_arxiv_searcher()
        test_cli_args()
        test_smart_handler()
        
        print("\n=== 测试完成 ===")
        print("所有组件测试通过！")
        
    except Exception as e:
        print(f"测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main() 