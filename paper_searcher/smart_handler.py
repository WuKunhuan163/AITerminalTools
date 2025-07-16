"""
智能PAPER_SEARCH处理器
自动识别和处理PAPER_SEARCH开头的用户输入
"""

import re
import sys
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from paper_search_handler import PaperSearchHandler
from keyword_extractor import KeywordExtractor


class SmartPaperSearchHandler:
    """智能PAPER_SEARCH处理器"""
    
    def __init__(self):
        self.handler = PaperSearchHandler()
        self.keyword_extractor = KeywordExtractor()
    
    def process_user_input(self, user_input: str) -> Optional[str]:
        """
        处理用户输入，如果是PAPER_SEARCH相关则自动处理
        
        Args:
            user_input: 用户输入的原始文本
            
        Returns:
            处理结果消息，如果不是PAPER_SEARCH相关则返回None
        """
        # 检查是否是PAPER_SEARCH指令
        if self.is_paper_search_request(user_input):
            try:
                # 如果是直接的PAPER_SEARCH指令
                if self.handler.is_paper_search_command(user_input):
                    result = self.handler.handle_paper_search(user_input)
                    return f"PAPER_SEARCH指令执行完成，退出码: {result}"
                
                # 如果是描述性的搜索请求，转换为PAPER_SEARCH指令
                else:
                    paper_search_cmd = self.convert_to_paper_search_command(user_input)
                    print(f"自动生成的PAPER_SEARCH指令: {paper_search_cmd}")
                    
                    result = self.handler.handle_paper_search(paper_search_cmd)
                    return f"论文搜索完成，退出码: {result}"
                    
            except Exception as e:
                return f"处理PAPER_SEARCH请求时出错: {e}"
        
        return None  # 不是PAPER_SEARCH相关的请求
    
    def is_paper_search_request(self, user_input: str) -> bool:
        """
        判断用户输入是否是论文搜索请求
        """
        input_lower = user_input.lower().strip()
        
        # 直接的PAPER_SEARCH指令
        if input_lower.startswith('paper_search'):
            return True
        
        # 包含论文搜索相关的关键词
        search_indicators = [
            '搜索论文', '查找论文', '找论文', '论文搜索',
            'search paper', 'find paper', 'paper search',
            '搜索文献', '查找文献', '文献搜索',
            'search literature', 'find literature', 'literature search',
            '搜索研究', '查找研究', '研究搜索',
            'search research', 'find research', 'research search'
        ]
        
        # 检查是否包含搜索指示词
        has_search_indicator = any(indicator in input_lower for indicator in search_indicators)
        
        # 检查是否包含学术相关词汇
        academic_terms = [
            'paper', 'research', 'study', 'article', 'journal', 'conference',
            'arxiv', 'google scholar', 'publication', 'academic',
            '论文', '研究', '学术', '文献', '期刊', '会议', '发表'
        ]
        
        has_academic_term = any(term in input_lower for term in academic_terms)
        
        # 检查是否包含技术领域词汇
        tech_terms = [
            'machine learning', 'deep learning', 'artificial intelligence',
            'computer vision', 'natural language processing', 'data mining',
            'neural network', 'algorithm', 'optimization', 'statistics',
            '机器学习', '深度学习', '人工智能', '计算机视觉',
            '自然语言处理', '数据挖掘', '神经网络', '算法', '优化'
        ]
        
        has_tech_term = any(term in input_lower for term in tech_terms)
        
        # 如果有搜索指示词，或者同时有学术词汇和技术词汇
        return has_search_indicator or (has_academic_term and has_tech_term)
    
    def convert_to_paper_search_command(self, user_input: str) -> str:
        """
        将用户描述转换为PAPER_SEARCH指令
        """
        # 提取主要描述部分
        description = self.extract_main_description(user_input)
        
        # 提取选项参数
        options = self.extract_options_from_description(user_input)
        
        # 使用关键词提取器增强查询
        enhanced_query = self.handler.extract_and_enhance_query(description)
        
        # 构建PAPER_SEARCH指令
        command_parts = [f"PAPER_SEARCH {enhanced_query}"]
        
        # 添加选项
        for key, value in options.items():
            if key == 'max_results':
                command_parts.append(f"--max-results {value}")
            elif key == 'sort_by':
                command_parts.append(f"--sort-by {value}")
            elif key == 'sources':
                command_parts.append(f"--sources {','.join(value)}")
            elif key == 'year_range':
                command_parts.append(f"--year-range {value[0]} {value[1]}")
            elif key == 'download_pdfs' and value:
                command_parts.append("--download-pdfs")
            elif key == 'output_dir':
                command_parts.append(f"--output-dir {value}")
        
        return " ".join(command_parts)
    
    def extract_main_description(self, user_input: str) -> str:
        """
        从用户输入中提取主要描述部分
        """
        # 移除常见的搜索前缀
        prefixes_to_remove = [
            r'请?帮我?搜索?论文?关于',
            r'请?帮我?查找?论文?关于',
            r'请?帮我?找?论文?关于',
            r'我想?搜索?论文?关于',
            r'我想?查找?论文?关于',
            r'我想?找?论文?关于',
            r'搜索?论文?关于',
            r'查找?论文?关于',
            r'找?论文?关于',
            r'search papers? about',
            r'find papers? about',
            r'look for papers? about',
            r'i want to search papers? about',
            r'i want to find papers? about',
            r'help me search papers? about',
            r'help me find papers? about'
        ]
        
        cleaned_input = user_input.strip()
        
        for prefix in prefixes_to_remove:
            cleaned_input = re.sub(prefix, '', cleaned_input, flags=re.IGNORECASE).strip()
        
        return cleaned_input
    
    def extract_options_from_description(self, user_input: str) -> Dict[str, Any]:
        """
        从用户描述中提取选项参数
        """
        options = {}
        input_lower = user_input.lower()
        
        # 提取数量要求
        quantity_patterns = [
            r'(\d+)\s*篇?论文',
            r'(\d+)\s*个?结果',
            r'(\d+)\s*papers?',
            r'(\d+)\s*results?'
        ]
        
        for pattern in quantity_patterns:
            match = re.search(pattern, input_lower)
            if match:
                options['max_results'] = int(match.group(1))
                break
        
        # 提取排序要求
        if any(word in input_lower for word in ['引用', 'citation', 'cited', '被引']):
            options['sort_by'] = 'citation'
        elif any(word in input_lower for word in ['最新', '新', 'recent', 'latest', 'new']):
            options['sort_by'] = 'date'
        elif any(word in input_lower for word in ['相关', 'relevant', 'relevance']):
            options['sort_by'] = 'relevance'
        
        # 提取来源要求
        sources = []
        if any(word in input_lower for word in ['arxiv', 'arXiv']):
            sources.append('arxiv')
        if any(word in input_lower for word in ['google scholar', 'scholar']):
            sources.append('google_scholar')
        
        if sources:
            options['sources'] = sources
        
        # 提取年份要求
        year_patterns = [
            r'(\d{4})\s*年?以后',
            r'(\d{4})\s*年?之后',
            r'since\s*(\d{4})',
            r'after\s*(\d{4})',
            r'(\d{4})\s*-\s*(\d{4})',
            r'(\d{4})\s*到\s*(\d{4})',
            r'from\s*(\d{4})\s*to\s*(\d{4})'
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, input_lower)
            if match:
                if len(match.groups()) == 1:
                    # 单个年份，表示从该年份到现在
                    start_year = int(match.group(1))
                    options['year_range'] = (start_year, 2024)
                else:
                    # 年份范围
                    start_year = int(match.group(1))
                    end_year = int(match.group(2))
                    options['year_range'] = (start_year, end_year)
                break
        
        # 提取下载要求
        if any(word in input_lower for word in ['下载', 'download', 'pdf']):
            options['download_pdfs'] = True
        
        # 提取输出目录要求
        output_patterns = [
            r'保存到\s*([^\s]+)',
            r'输出到\s*([^\s]+)',
            r'save to\s*([^\s]+)',
            r'output to\s*([^\s]+)'
        ]
        
        for pattern in output_patterns:
            match = re.search(pattern, input_lower)
            if match:
                options['output_dir'] = match.group(1)
                break
        
        return options
    
    def get_search_suggestions(self, user_input: str) -> Dict[str, Any]:
        """
        基于用户输入提供搜索建议
        """
        suggestions = self.handler.suggest_search_improvements(user_input)
        
        # 添加基于输入内容的额外建议
        input_lower = user_input.lower()
        
        # 建议搜索源
        if 'arxiv' in input_lower:
            suggestions['recommended_sources'] = ['arxiv']
        elif 'google scholar' in input_lower:
            suggestions['recommended_sources'] = ['google_scholar']
        elif any(term in input_lower for term in ['综述', 'review', 'survey']):
            suggestions['recommended_sources'] = ['google_scholar']
        elif any(term in input_lower for term in ['预印本', 'preprint', '最新']):
            suggestions['recommended_sources'] = ['arxiv']
        
        # 建议结果数量
        if any(term in input_lower for term in ['详细', 'detailed', '全面', 'comprehensive']):
            suggestions['recommended_max_results'] = 20
        elif any(term in input_lower for term in ['简单', 'simple', '快速', 'quick']):
            suggestions['recommended_max_results'] = 5
        
        return suggestions


def main():
    """主函数 - 用于测试"""
    handler = SmartPaperSearchHandler()
    
    # 测试用例
    test_inputs = [
        "PAPER_SEARCH 深度学习 --max-results 5",
        "请帮我搜索关于机器学习优化的论文",
        "我想找一些关于自然语言处理的最新研究，大概10篇",
        "搜索计算机视觉方面的论文，要引用量高的，从arxiv上找",
        "查找2020年以后的深度学习论文，下载PDF"
    ]
    
    for test_input in test_inputs:
        print(f"\n测试输入: {test_input}")
        result = handler.process_user_input(test_input)
        if result:
            print(f"处理结果: {result}")
        else:
            print("不是PAPER_SEARCH相关的请求")
        print("-" * 50)


if __name__ == '__main__':
    main() 