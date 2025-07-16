"""
关键词提取器
从用户描述中智能提取搜索关键词
"""

import re
from typing import List, Dict, Set
from collections import Counter
import string


class KeywordExtractor:
    """关键词提取器"""
    
    def __init__(self):
        # 常见的停用词
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
            'between', 'among', 'under', 'over', 'again', 'further', 'then', 'once', 'here', 'there',
            'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
            'too', 'very', 'can', 'will', 'just', 'should', 'now', 'is', 'are', 'was', 'were',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'doing', 'would', 'could',
            'should', 'might', 'may', 'must', 'shall', 'this', 'that', 'these', 'those', 'i', 'me',
            'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself',
            'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it',
            'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which',
            'who', 'whom', 'whose', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was',
            'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did',
            'doing', 'get', 'got', 'getting', 'go', 'going', 'went', 'gone', 'come', 'came',
            'coming', 'want', 'wanted', 'wanting', 'like', 'liked', 'liking', 'need', 'needed',
            'needing', 'use', 'used', 'using', 'work', 'worked', 'working', 'make', 'made',
            'making', 'take', 'took', 'taken', 'taking', 'give', 'gave', 'given', 'giving',
            'find', 'found', 'finding', 'look', 'looked', 'looking', 'see', 'saw', 'seen',
            'seeing', 'know', 'knew', 'known', 'knowing', 'think', 'thought', 'thinking',
            'say', 'said', 'saying', 'tell', 'told', 'telling', 'ask', 'asked', 'asking',
            'paper', 'papers', 'research', 'study', 'studies', 'method', 'methods', 'approach',
            'approaches', 'technique', 'techniques', 'algorithm', 'algorithms', 'model', 'models',
            'system', 'systems', 'framework', 'frameworks', 'analysis', 'analyses', 'review',
            'reviews', 'survey', 'surveys', 'article', 'articles', 'journal', 'journals',
            'conference', 'conferences', 'proceedings', 'publication', 'publications'
        }
        
        # 学术领域相关的重要词汇
        self.academic_terms = {
            'machine learning', 'deep learning', 'neural network', 'artificial intelligence',
            'computer vision', 'natural language processing', 'data mining', 'big data',
            'reinforcement learning', 'supervised learning', 'unsupervised learning',
            'classification', 'regression', 'clustering', 'optimization', 'statistics',
            'probability', 'bayesian', 'markov', 'gaussian', 'linear algebra', 'calculus',
            'differential equations', 'graph theory', 'topology', 'geometry', 'algebra',
            'number theory', 'combinatorics', 'discrete mathematics', 'continuous mathematics',
            'physics', 'chemistry', 'biology', 'medicine', 'engineering', 'mathematics',
            'computer science', 'software engineering', 'hardware', 'robotics', 'automation',
            'control systems', 'signal processing', 'image processing', 'pattern recognition',
            'feature extraction', 'dimensionality reduction', 'principal component analysis',
            'support vector machine', 'random forest', 'gradient boosting', 'ensemble methods',
            'cross validation', 'hyperparameter tuning', 'model selection', 'evaluation metrics',
            'precision', 'recall', 'f1 score', 'accuracy', 'auc', 'roc curve', 'confusion matrix'
        }
        
        # 技术术语的同义词映射
        self.synonyms = {
            'ai': 'artificial intelligence',
            'ml': 'machine learning',
            'dl': 'deep learning',
            'nn': 'neural network',
            'nlp': 'natural language processing',
            'cv': 'computer vision',
            'rl': 'reinforcement learning',
            'svm': 'support vector machine',
            'pca': 'principal component analysis',
            'cnn': 'convolutional neural network',
            'rnn': 'recurrent neural network',
            'lstm': 'long short term memory',
            'gru': 'gated recurrent unit',
            'gan': 'generative adversarial network',
            'vae': 'variational autoencoder',
            'bert': 'bidirectional encoder representations from transformers',
            'gpt': 'generative pre-trained transformer',
            'transformer': 'transformer architecture'
        }
    
    def extract_keywords(self, description: str, max_keywords: int = 10) -> List[str]:
        """
        从描述中提取关键词
        
        Args:
            description: 用户描述
            max_keywords: 最大关键词数量
            
        Returns:
            关键词列表
        """
        # 清理和预处理文本
        cleaned_text = self._clean_text(description)
        
        # 提取不同类型的关键词
        phrase_keywords = self._extract_phrases(cleaned_text)
        single_keywords = self._extract_single_words(cleaned_text)
        technical_keywords = self._extract_technical_terms(cleaned_text)
        
        # 合并和排序关键词
        all_keywords = self._merge_and_rank_keywords(
            phrase_keywords, single_keywords, technical_keywords
        )
        
        # 应用同义词映射
        expanded_keywords = self._expand_synonyms(all_keywords)
        
        # 返回前N个关键词
        return expanded_keywords[:max_keywords]
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 转换为小写
        text = text.lower()
        
        # 移除特殊字符，但保留空格和连字符
        text = re.sub(r'[^\w\s\-]', ' ', text)
        
        # 规范化空格
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_phrases(self, text: str) -> List[str]:
        """提取短语关键词"""
        phrases = []
        
        # 寻找学术术语中的短语
        for term in self.academic_terms:
            if term in text:
                phrases.append(term)
        
        # 寻找连字符连接的词
        hyphenated_words = re.findall(r'\b\w+\-\w+\b', text)
        phrases.extend(hyphenated_words)
        
        # 寻找常见的技术短语模式
        tech_patterns = [
            r'\b\w+\s+learning\b',
            r'\b\w+\s+network\b',
            r'\b\w+\s+algorithm\b',
            r'\b\w+\s+model\b',
            r'\b\w+\s+system\b',
            r'\b\w+\s+method\b',
            r'\b\w+\s+analysis\b',
            r'\b\w+\s+processing\b',
            r'\b\w+\s+recognition\b',
            r'\b\w+\s+detection\b',
            r'\b\w+\s+classification\b',
            r'\b\w+\s+optimization\b'
        ]
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, text)
            phrases.extend(matches)
        
        return list(set(phrases))
    
    def _extract_single_words(self, text: str) -> List[str]:
        """提取单词关键词"""
        words = text.split()
        
        # 过滤停用词和短词
        filtered_words = [
            word for word in words
            if len(word) > 2 and word not in self.stop_words
        ]
        
        # 计算词频
        word_freq = Counter(filtered_words)
        
        # 返回按频率排序的词
        return [word for word, freq in word_freq.most_common(20)]
    
    def _extract_technical_terms(self, text: str) -> List[str]:
        """提取技术术语"""
        technical_terms = []
        
        # 寻找缩写词
        abbreviations = re.findall(r'\b[A-Z]{2,}\b', text.upper())
        technical_terms.extend([abbr.lower() for abbr in abbreviations])
        
        # 寻找数学/科学术语
        math_patterns = [
            r'\b\w*matrix\w*\b',
            r'\b\w*vector\w*\b',
            r'\b\w*tensor\w*\b',
            r'\b\w*function\w*\b',
            r'\b\w*equation\w*\b',
            r'\b\w*distribution\w*\b',
            r'\b\w*probability\w*\b',
            r'\b\w*statistic\w*\b',
            r'\b\w*metric\w*\b',
            r'\b\w*feature\w*\b',
            r'\b\w*parameter\w*\b',
            r'\b\w*hyperparameter\w*\b'
        ]
        
        for pattern in math_patterns:
            matches = re.findall(pattern, text)
            technical_terms.extend(matches)
        
        return list(set(technical_terms))
    
    def _merge_and_rank_keywords(self, phrases: List[str], 
                                single_words: List[str], 
                                technical_terms: List[str]) -> List[str]:
        """合并和排序关键词"""
        keyword_scores = {}
        
        # 短语权重最高
        for phrase in phrases:
            keyword_scores[phrase] = keyword_scores.get(phrase, 0) + 3
        
        # 技术术语权重中等
        for term in technical_terms:
            keyword_scores[term] = keyword_scores.get(term, 0) + 2
        
        # 单词权重最低
        for word in single_words:
            keyword_scores[word] = keyword_scores.get(word, 0) + 1
        
        # 按分数排序
        sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
        
        return [keyword for keyword, score in sorted_keywords]
    
    def _expand_synonyms(self, keywords: List[str]) -> List[str]:
        """扩展同义词"""
        expanded = []
        
        for keyword in keywords:
            expanded.append(keyword)
            
            # 检查是否有同义词
            if keyword in self.synonyms:
                expanded.append(self.synonyms[keyword])
            
            # 检查是否是同义词的值
            for abbr, full_term in self.synonyms.items():
                if keyword == full_term and abbr not in expanded:
                    expanded.append(abbr)
        
        # 去重但保持顺序
        seen = set()
        result = []
        for item in expanded:
            if item not in seen:
                seen.add(item)
                result.append(item)
        
        return result
    
    def suggest_related_terms(self, keywords: List[str]) -> List[str]:
        """根据关键词建议相关术语"""
        suggestions = []
        
        for keyword in keywords:
            # 基于关键词找相关的学术术语
            related_terms = [
                term for term in self.academic_terms
                if any(word in term for word in keyword.split())
            ]
            suggestions.extend(related_terms)
        
        return list(set(suggestions))
    
    def extract_with_context(self, description: str) -> Dict[str, List[str]]:
        """
        提取关键词并提供上下文信息
        
        Returns:
            包含不同类型关键词的字典
        """
        cleaned_text = self._clean_text(description)
        
        return {
            'primary_keywords': self.extract_keywords(description, max_keywords=5),
            'phrases': self._extract_phrases(cleaned_text),
            'technical_terms': self._extract_technical_terms(cleaned_text),
            'single_words': self._extract_single_words(cleaned_text)[:10],
            'suggested_terms': self.suggest_related_terms(self.extract_keywords(description, max_keywords=3))
        } 