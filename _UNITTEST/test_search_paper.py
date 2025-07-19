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
    from SEARCH_PAPER import MultiPlatformPaperSearcher, get_run_context, write_to_json_output, main as search_paper_main
except ImportError as e:
    MultiPlatformPaperSearcher = None
    get_run_context = None
    write_to_json_output = None
    search_paper_main = None
    print(f"Failed to import SEARCH_PAPER components: {e}")

@unittest.skipIf(MultiPlatformPaperSearcher is None, "SEARCH_PAPER module not available")
class TestSearchPaper(unittest.TestCase):
    """Test cases for SEARCH_PAPER tool"""

    def setUp(self):
        self.searcher = MultiPlatformPaperSearcher()
        # Create a temporary directory for test outputs
        self.test_dir = Path("_UNITTEST/temp_test_data")
        self.searcher.output_dir = self.test_dir
        self.searcher.papers_dir = self.test_dir / "papers"
        self.test_dir.mkdir(exist_ok=True)
        (self.test_dir / "papers").mkdir(exist_ok=True)

    def tearDown(self):
        # Clean up the temporary directory
        for f in self.test_dir.glob("**/*"):
            if f.is_file():
                f.unlink()
        if (self.test_dir / "papers").exists():
            (self.test_dir / "papers").rmdir()
        if self.test_dir.exists():
            self.test_dir.rmdir()


    def test_run_environment_detection(self):
        """Test RUN environment detection"""
        with patch.dict(os.environ, clear=True):
            run_context = get_run_context()
            self.assertFalse(run_context['in_run_context'])
        
        with patch.dict(os.environ, {
            'RUN_IDENTIFIER': 'test_run',
            'RUN_DATA_FILE': str(self.test_dir / 'test_output.json')
        }):
            run_context = get_run_context()
            self.assertTrue(run_context['in_run_context'])

    @patch('SEARCH_PAPER.requests.Session.get')
    def test_arxiv_search(self, mock_get):
        """Test arXiv search functionality"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'''<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <entry>
                <title>Test Paper Title</title>
                <summary>Test abstract</summary>
                <id>http://arxiv.org/abs/2024.0001</id>
                <author><name>Test Author</name></author>
            </entry>
        </feed>'''
        mock_get.return_value = mock_response
        
        results = self.searcher._search_arxiv("machine learning", max_results=5)
        
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn('title', results[0])
        self.assertIn('url', results[0])
        mock_get.assert_called_once()

    @patch('SEARCH_PAPER.requests.Session.get')
    def test_search_failure(self, mock_get):
        """Test search failure handling"""
        mock_get.side_effect = Exception("Network error")
        
        results = self.searcher._search_arxiv("test query", max_results=5)
        
        self.assertEqual(results, [])

    def test_help_output(self):
        """Test help output"""
        with patch('sys.argv', ['SEARCH_PAPER.py', '--help']):
            with patch('sys.stdout') as mock_stdout:
                try:
                    search_paper_main()
                except SystemExit:
                    pass
                
                output = "".join(call.args[0] for call in mock_stdout.write.call_args_list)
                self.assertIn("usage: search_paper", output.lower())

@unittest.skipIf(MultiPlatformPaperSearcher is None, "SEARCH_PAPER module not available")
class TestSearchPaperIntegration(unittest.TestCase):
    """Integration tests for SEARCH_PAPER tool"""
    
    def test_command_line_execution_help(self):
        """Test command line execution of SEARCH_PAPER --help"""
        result = subprocess.run([
            sys.executable, 
            str(Path(__file__).parent.parent / 'SEARCH_PAPER.py'),
            '--help'
        ], capture_output=True, text=True, timeout=30)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('usage: search_paper', result.stdout.lower())

if __name__ == '__main__':
    unittest.main() 