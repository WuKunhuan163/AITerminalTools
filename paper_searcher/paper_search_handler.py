"""
PAPER_SEARCH指令处理器
自动识别和处理PAPER_SEARCH开头的用户输入
"""

import re
import sys
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import PaperSearchCLI
from keyword_extractor import KeywordExtractor


class PaperSearchHandler:
    """PAPER_SEARCH指令处理器"""
    
    def __init__(self):
        self.cli = PaperSearchCLI()
        self.keyword_extractor = KeywordExtractor()
    
    def is_paper_search_command(self, user_input: str) -> bool:
        """检查是否是PAPER_SEARCH指令"""
        return user_input.strip().upper().startswith('PAPER_SEARCH')
    
    def parse_paper_search_command(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """
        解析PAPER_SEARCH指令
        
        Returns:
            (query, options) - 查询内容和选项参数
        """
        # 移除PAPER_SEARCH前缀
        content = re.sub(r'^PAPER_SEARCH\s*', '', user_input.strip(), flags=re.IGNORECASE)
        
        # 解析选项和查询
        options = {}
        query = content
        
        # 解析常见的选项格式
        option_patterns = [
            (r'--max-results?\s+(\d+)', 'max_results', lambda x: int(x)),
            (r'--max\s+(\d+)', 'max_results', lambda x: int(x)),
            (r'-n\s+(\d+)', 'max_results', lambda x: int(x)),
            (r'--sort-by\s+(relevance|citation|date)', 'sort_by', lambda x: str(x)),
            (r'--sort\s+(relevance|citation|date)', 'sort_by', lambda x: str(x)),
            (r'--sources?\s+([\w,\s]+)', 'sources', lambda x: [s.strip() for s in x.split(',')]),
            (r'--source\s+([\w,\s]+)', 'sources', lambda x: [s.strip() for s in x.split(',')]),
            (r'-s\s+([\w,\s]+)', 'sources', lambda x: [s.strip() for s in x.split(',')]),
            (r'--year-range\s+(\d{4})\s+(\d{4})', 'year_range', lambda x, y: (int(x), int(y))),
            (r'--years?\s+(\d{4})-(\d{4})', 'year_range', lambda x, y: (int(x), int(y))),
            (r'--output-dir\s+([^\s]+)', 'output_dir', lambda x: str(x)),
            (r'--output\s+([^\s]+)', 'output_dir', lambda x: str(x)),
            (r'-o\s+([^\s]+)', 'output_dir', lambda x: str(x)),
            (r'--download-pdfs?', 'download_pdfs', lambda: True),
            (r'--download', 'download_pdfs', lambda: True),
            (r'--pdf', 'download_pdfs', lambda: True),
            (r'--save-format\s+(json|csv|txt)', 'save_format', lambda x: str(x)),
            (r'--format\s+(json|csv|txt)', 'save_format', lambda x: str(x)),
            (r'--verbose', 'verbose', lambda: True),
            (r'-v', 'verbose', lambda: True),
        ]
        
        for pattern, key, converter in option_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                if key == 'year_range':
                    options[key] = converter(match.group(1), match.group(2))
                elif len(match.groups()) == 0:  # 无参数标志
                    options[key] = converter()
                else:
                    options[key] = converter(match.group(1))
                
                # 从查询中移除匹配的选项
                query = re.sub(pattern, '', query, flags=re.IGNORECASE).strip()
        
        return query, options
    
    def handle_paper_search(self, user_input: str) -> int:
        """
        处理PAPER_SEARCH指令
        
        Returns:
            退出码 (0表示成功)
        """
        try:
            # 解析指令
            query, options = self.parse_paper_search_command(user_input)
            
            if not query:
                print("错误: 没有提供搜索查询")
                return 1
            
            # 显示解析结果
            print(f"搜索查询: {query}")
            if options:
                print(f"选项: {options}")
            
            # 构建CLI参数
            cli_args = self.build_cli_args(query, options)
            
            # 执行搜索
            return self.cli.run(cli_args)
            
        except Exception as e:
            print(f"处理PAPER_SEARCH指令时出错: {e}")
            return 1
    
    def build_cli_args(self, query: str, options: Dict[str, Any]) -> List[str]:
        """构建CLI参数列表"""
        args = [query]
        
        # 添加选项参数
        for key, value in options.items():
            if key == 'max_results':
                args.extend(['--max-results', str(value)])
            elif key == 'sort_by':
                args.extend(['--sort-by', value])
            elif key == 'sources':
                args.extend(['--sources'] + value)
            elif key == 'year_range':
                args.extend(['--year-range', str(value[0]), str(value[1])])
            elif key == 'output_dir':
                args.extend(['--output-dir', value])
            elif key == 'download_pdfs' and value:
                args.append('--download-pdfs')
            elif key == 'save_format':
                args.extend(['--save-format', value])
            elif key == 'verbose' and value:
                args.append('--verbose')
        
        return args
    
    def extract_and_enhance_query(self, raw_query: str) -> str:
        """
        提取并增强查询内容
        使用AI的力量来改进搜索查询
        """
        # 基本清理
        cleaned_query = raw_query.strip()
        
        # 提取关键词并重新组织
        keywords = self.keyword_extractor.extract_keywords(cleaned_query)
        
        # 获取扩展信息
        keyword_info = self.keyword_extractor.extract_with_context(cleaned_query)
        
        # 构建增强的查询
        enhanced_parts = []
        
        # 添加主要关键词
        if keyword_info['primary_keywords']:
            enhanced_parts.extend(keyword_info['primary_keywords'][:3])
        
        # 添加重要的短语
        if keyword_info['phrases']:
            enhanced_parts.extend(keyword_info['phrases'][:2])
        
        # 添加技术术语
        if keyword_info['technical_terms']:
            enhanced_parts.extend(keyword_info['technical_terms'][:2])
        
        # 去重并组合
        unique_parts = []
        seen = set()
        for part in enhanced_parts:
            if part.lower() not in seen:
                seen.add(part.lower())
                unique_parts.append(part)
        
        enhanced_query = ' '.join(unique_parts[:5])  # 限制长度
        
        return enhanced_query if enhanced_query else cleaned_query
    
    def suggest_search_improvements(self, query: str) -> Dict[str, Any]:
        """
        基于查询内容建议搜索改进
        """
        keyword_info = self.keyword_extractor.extract_with_context(query)
        
        suggestions = {
            'alternative_keywords': keyword_info.get('suggested_terms', []),
            'recommended_sources': [],
            'recommended_sort': 'relevance',
            'recommended_filters': {}
        }
        
        # 基于关键词推荐搜索源
        query_lower = query.lower()
        
        if any(term in query_lower for term in ['deep learning', 'neural network', 'ai', 'machine learning']):
            suggestions['recommended_sources'] = ['arxiv', 'google_scholar']
        elif any(term in query_lower for term in ['algorithm', 'optimization', 'mathematics']):
            suggestions['recommended_sources'] = ['arxiv']
        elif any(term in query_lower for term in ['survey', 'review', 'analysis']):
            suggestions['recommended_sources'] = ['google_scholar']
        else:
            suggestions['recommended_sources'] = ['all']
        
        # 推荐排序方式
        if any(term in query_lower for term in ['recent', 'latest', 'new', '2023', '2024']):
            suggestions['recommended_sort'] = 'date'
        elif any(term in query_lower for term in ['important', 'influential', 'cited']):
            suggestions['recommended_sort'] = 'citation'
        
        # 推荐过滤器
        current_year = 2024
        if any(term in query_lower for term in ['recent', 'latest', 'new']):
            suggestions['recommended_filters']['year_range'] = (current_year - 3, current_year)
        elif any(term in query_lower for term in ['classic', 'foundational', 'seminal']):
            suggestions['recommended_filters']['year_range'] = (2000, current_year - 5)
        
        return suggestions
    
    def interactive_paper_search(self) -> int:
        """
        交互式PAPER_SEARCH处理
        当用户只输入PAPER_SEARCH时启动
        """
        print("=== PAPER_SEARCH 交互模式 ===")
        print("请描述您要搜索的论文内容:")
        
        try:
            query = input("搜索描述: ").strip()
            
            if not query:
                print("未提供搜索查询")
                return 1
            
            # 提取和增强查询
            enhanced_query = self.extract_and_enhance_query(query)
            
            print(f"\n原始查询: {query}")
            print(f"增强查询: {enhanced_query}")
            
            # 获取建议
            suggestions = self.suggest_search_improvements(query)
            
            print(f"\n推荐搜索源: {', '.join(suggestions['recommended_sources'])}")
            print(f"推荐排序: {suggestions['recommended_sort']}")
            
            if suggestions['alternative_keywords']:
                print(f"相关关键词: {', '.join(suggestions['alternative_keywords'][:5])}")
            
            # 询问用户是否使用建议
            use_suggestions = input("\n是否使用推荐设置? (y/n) [y]: ").strip().lower()
            
            if use_suggestions in ['', 'y', 'yes']:
                # 使用建议构建选项
                options = {
                    'sources': suggestions['recommended_sources'],
                    'sort_by': suggestions['recommended_sort']
                }
                
                if 'year_range' in suggestions['recommended_filters']:
                    options['year_range'] = suggestions['recommended_filters']['year_range']
                
                # 询问其他参数
                max_results = input("最大结果数量 [10]: ").strip()
                if max_results:
                    try:
                        options['max_results'] = int(max_results)
                    except ValueError:
                        pass
                
                download_pdfs = input("下载PDF文件? (y/n) [n]: ").strip().lower()
                if download_pdfs in ['y', 'yes']:
                    options['download_pdfs'] = True
                
                output_dir = input("输出目录 [paper_searcher/data]: ").strip()
                if output_dir:
                    options['output_dir'] = output_dir
                
            else:
                # 手动设置参数
                options = {}
                
                sources = input("搜索源 (google_scholar/arxiv/all) [all]: ").strip()
                if sources:
                    options['sources'] = [s.strip() for s in sources.split(',')]
                
                sort_by = input("排序方式 (relevance/citation/date) [relevance]: ").strip()
                if sort_by:
                    options['sort_by'] = sort_by
                
                max_results = input("最大结果数量 [10]: ").strip()
                if max_results:
                    try:
                        options['max_results'] = int(max_results)
                    except ValueError:
                        pass
            
            # 构建CLI参数并执行
            cli_args = self.build_cli_args(enhanced_query, options)
            return self.cli.run(cli_args)
            
        except KeyboardInterrupt:
            print("\n搜索被用户中断")
            return 1
        except Exception as e:
            print(f"交互式搜索出错: {e}")
            return 1


def main():
    """主函数 - 用于测试"""
    handler = PaperSearchHandler()
    
    # 测试示例
    test_commands = [
        "PAPER_SEARCH 深度学习在计算机视觉中的应用 --max-results 5 --sort-by citation",
        "PAPER_SEARCH machine learning optimization --sources arxiv --download-pdfs",
        "PAPER_SEARCH natural language processing transformer --year-range 2020 2023"
    ]
    
    for cmd in test_commands:
        print(f"\n测试命令: {cmd}")
        handler.handle_paper_search(cmd)
        print("-" * 50)


if __name__ == '__main__':
    main() 