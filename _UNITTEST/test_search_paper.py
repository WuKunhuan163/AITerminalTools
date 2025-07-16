#!/usr/bin/env python3
"""
Unit tests for SEARCH_PAPER tool
"""

import unittest
import os
import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path to import the module
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import SEARCH_PAPER
except ImportError:
    SEARCH_PAPER = None

class TestSearchPaper(unittest.TestCase):
    """Test cases for SEARCH_PAPER tool"""
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        # Test without RUN environment
        self.assertFalse(SEARCH_PAPER.is_run_environment())
        
        # Test with RUN environment
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_OUTPUT_FILE': '/tmp/test_output.json'
        }):
            self.assertTrue(SEARCH_PAPER.is_run_environment())
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    def test_json_output_format(self):
        """Test JSON output format for RUN environment"""
        result = SEARCH_PAPER.create_json_output(
            success=True,
            message="Search completed successfully",
            results=[{"title": "Test Paper", "url": "https://example.com"}],
            query="test query"
        )
        
        self.assertIsInstance(result, dict)
        self.assertIn('success', result)
        self.assertIn('message', result)
        self.assertIn('results', result)
        self.assertIn('query', result)
        self.assertIn('timestamp', result)
        self.assertTrue(result['success'])
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    def test_argument_parsing(self):
        """Test command line argument parsing"""
        # Test with query
        args = SEARCH_PAPER.parse_arguments(['machine learning'])
        self.assertEqual(args.query, 'machine learning')
        self.assertEqual(args.max_results, 10)  # default
        self.assertEqual(args.sources, ['arxiv', 'scholar', 'semantic'])  # default
        
        # Test with max results
        args = SEARCH_PAPER.parse_arguments(['--max-results', '20', 'deep learning'])
        self.assertEqual(args.max_results, 20)
        
        # Test with specific sources
        args = SEARCH_PAPER.parse_arguments(['--sources', 'arxiv', 'scholar', 'AI research'])
        self.assertEqual(args.sources, ['arxiv', 'scholar'])
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    def test_source_validation(self):
        """Test source validation"""
        valid_sources = ['arxiv', 'scholar', 'semantic']
        
        for source in valid_sources:
            self.assertTrue(SEARCH_PAPER.is_valid_source(source))
        
        # Test invalid source
        self.assertFalse(SEARCH_PAPER.is_valid_source('invalid_source'))
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    @patch('requests.get')
    def test_arxiv_search(self, mock_get):
        """Test arXiv search functionality"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper Title</title>
                <summary>Test abstract</summary>
                <id>http://arxiv.org/abs/2024.0001</id>
                <author><name>Test Author</name></author>
            </entry>
        </feed>'''
        mock_get.return_value = mock_response
        
        results = SEARCH_PAPER.search_arxiv("machine learning", max_results=5)
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('title', results[0])
        self.assertIn('url', results[0])
        mock_get.assert_called_once()
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    @patch('requests.get')
    def test_search_failure(self, mock_get):
        """Test search failure handling"""
        mock_get.side_effect = Exception("Network error")
        
        results = SEARCH_PAPER.search_arxiv("test query", max_results=5)
        
        self.assertEqual(results, [])
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['SEARCH_PAPER.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    SEARCH_PAPER.main()
                except SystemExit:
                    pass  # argparse calls sys.exit after showing help
                
                # Check that help was printed
                mock_stdout.write.assert_called()
    
    @unittest.skipIf(SEARCH_PAPER is None, "SEARCH_PAPER module not available")
    @patch('builtins.input')
    def test_interactive_mode(self, mock_input):
        """Test interactive mode when no query provided"""
        mock_input.return_value = "test query"
        
        with patch('sys.argv', ['SEARCH_PAPER.py']):
            with patch.object(SEARCH_PAPER, 'search_all_sources') as mock_search:
                mock_search.return_value = [
                    {"title": "Test Paper", "url": "https://example.com"}
                ]
                
                try:
                    SEARCH_PAPER.main()
                except SystemExit:
                    pass
                
                mock_input.assert_called_once()
                mock_search.assert_called_once()

class TestSearchPaperIntegration(unittest.TestCase):
    """Integration tests for SEARCH_PAPER tool"""
    
    def test_command_line_execution(self):
        """Test command line execution of SEARCH_PAPER"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'SEARCH_PAPER.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Search academic papers', result.stdout)
    
    def test_run_show_compatibility(self):
        """Test RUN --show compatibility"""
        result = subprocess.run([
            sys.executable,
            str(Path(__file__).parent.parent / 'RUN.py'),
            '--show', 'SEARCH_PAPER'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        try:
            output_data = json.loads(result.stdout)
            self.assertIn('success', output_data)
            self.assertIn('message', output_data)
        except json.JSONDecodeError:
            self.fail("RUN --show SEARCH_PAPER did not return valid JSON")

if __name__ == '__main__':
    unittest.main() 