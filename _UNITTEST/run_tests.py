#!/usr/bin/env python3
"""
Test runner with timeout management
带超时管理的测试运行器
"""

import unittest
import sys
import os
import time
import signal
from pathlib import Path
from typing import List, Dict, Any
from io import StringIO

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from _UNITTEST.base_test import BaseTest, APITest, LongRunningTest, QuickTest


class TestResult:
    """测试结果"""
    def __init__(self, test_name: str, success: bool, duration: float, error: str = None):
        self.test_name = test_name
        self.success = success
        self.duration = duration
        self.error = error


class TimeoutTestRunner:
    """带超时管理的测试运行器"""
    
    def __init__(self, verbosity: int = 1):
        self.verbosity = verbosity
        self.results: List[TestResult] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.timeout_tests = 0
    
    def run_test_suite(self, test_suite: unittest.TestSuite) -> bool:
        """运行测试套件"""
        print(f"🧪 开始运行测试套件...")
        print(f"📊 总计 {test_suite.countTestCases()} 个测试")
        print("=" * 60)
        
        start_time = time.time()
        
        # 递归遍历测试套件
        self._run_tests_recursive(test_suite)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        self._print_summary(total_duration)
        
        return self.failed_tests == 0 and self.timeout_tests == 0
    
    def _run_tests_recursive(self, test_suite):
        """递归运行测试"""
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                # 如果是测试套件，递归处理
                self._run_tests_recursive(test)
            else:
                # 如果是单个测试，运行它
                self._run_single_test(test)
    
    def _run_single_test(self, test: unittest.TestCase):
        """运行单个测试"""
        test_name = f"{test.__class__.__name__}.{test._testMethodName}"
        
        # 确定测试超时时间
        timeout = getattr(test.__class__, 'TEST_TIMEOUT', 10)
        
        if self.verbosity >= 1:
            print(f"🔍 运行: {test_name} (超时: {timeout}s)")
        
        start_time = time.time()
        
        try:
            # 设置超时信号 (仅在Unix系统上)
            if hasattr(signal, 'SIGALRM'):
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Test timed out after {timeout} seconds")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(timeout)
            
            # 运行测试
            test_result = unittest.TestResult()
            test(test_result)
            
            # 取消超时
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if test_result.wasSuccessful():
                self._record_success(test_name, duration)
            else:
                errors = test_result.errors + test_result.failures
                error_msg = errors[0][1] if errors else "Unknown error"
                self._record_failure(test_name, duration, error_msg)
        
        except TimeoutError as e:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            end_time = time.time()
            duration = end_time - start_time
            self._record_timeout(test_name, duration, str(e))
        
        except Exception as e:
            if hasattr(signal, 'SIGALRM'):
                signal.alarm(0)
            end_time = time.time()
            duration = end_time - start_time
            self._record_failure(test_name, duration, str(e))
    
    def _record_success(self, test_name: str, duration: float):
        """记录成功的测试"""
        self.results.append(TestResult(test_name, True, duration))
        self.total_tests += 1
        self.passed_tests += 1
        
        if self.verbosity >= 1:
            print(f"✅ {test_name} ({duration:.2f}s)")
    
    def _record_failure(self, test_name: str, duration: float, error: str):
        """记录失败的测试"""
        self.results.append(TestResult(test_name, False, duration, error))
        self.total_tests += 1
        self.failed_tests += 1
        
        if self.verbosity >= 1:
            print(f"❌ {test_name} ({duration:.2f}s)")
            if self.verbosity >= 2:
                print(f"   错误: {error}")
    
    def _record_timeout(self, test_name: str, duration: float, error: str):
        """记录超时的测试"""
        self.results.append(TestResult(test_name, False, duration, error))
        self.total_tests += 1
        self.timeout_tests += 1
        
        if self.verbosity >= 1:
            print(f"⏰ {test_name} ({duration:.2f}s) - TIMEOUT")
    
    def _print_summary(self, total_duration: float):
        """打印测试总结"""
        print("\n" + "=" * 60)
        print(f"📊 测试总结")
        print(f"总计: {self.total_tests} 个测试")
        print(f"✅ 成功: {self.passed_tests}")
        print(f"❌ 失败: {self.failed_tests}")
        print(f"⏰ 超时: {self.timeout_tests}")
        print(f"⏱️  总时间: {total_duration:.2f}s")
        
        if self.failed_tests > 0 or self.timeout_tests > 0:
            print("\n❌ 失败的测试:")
            for result in self.results:
                if not result.success:
                    print(f"  - {result.test_name} ({result.duration:.2f}s)")
                    if result.error and self.verbosity >= 2:
                        print(f"    {result.error}")
        
        print("\n" + "=" * 60)


def discover_tests(test_dir: str = None) -> unittest.TestSuite:
    """发现测试"""
    if test_dir is None:
        test_dir = str(Path(__file__).parent)
    
    loader = unittest.TestLoader()
    suite = loader.discover(test_dir, pattern='test_*.py')
    return suite


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="测试运行器")
    parser.add_argument('-v', '--verbose', action='count', default=1, help="详细输出")
    parser.add_argument('-q', '--quiet', action='store_true', help="静默模式")
    parser.add_argument('-p', '--pattern', default='test_*.py', help="测试文件模式")
    parser.add_argument('-t', '--test', help="运行特定测试")
    parser.add_argument('--fast', action='store_true', help="只运行快速测试")
    parser.add_argument('--api', action='store_true', help="只运行API测试")
    
    args = parser.parse_args()
    
    if args.quiet:
        verbosity = 0
    else:
        verbosity = args.verbose
    
    runner = TimeoutTestRunner(verbosity)
    
    if args.test:
        # 运行特定测试
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromName(args.test)
    else:
        # 发现所有测试
        suite = discover_tests()
        
        # 过滤测试类型
        if args.fast or args.api:
            filtered_suite = unittest.TestSuite()
            for test_group in suite:
                if hasattr(test_group, '__iter__'):
                    for test in test_group:
                        test_class = test.__class__
                        if args.fast and issubclass(test_class, QuickTest):
                            filtered_suite.addTest(test)
                        elif args.api and issubclass(test_class, APITest):
                            filtered_suite.addTest(test)
            suite = filtered_suite
    
    success = runner.run_test_suite(suite)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main()) 