#!/usr/bin/env python3
"""
Base test class with timeout management
为所有单元测试提供统一的超时管理
"""

import unittest
import signal
import sys
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any


class TimeoutError(Exception):
    """测试超时异常"""
    pass


class BaseTest(unittest.TestCase):
    """
    基础测试类，提供统一的超时管理
    
    Features:
    - 默认10秒测试超时
    - 可通过 TEST_TIMEOUT 类属性自定义超时时间
    - 自动处理subprocess调用的超时
    - 统一的错误处理和日志
    """
    
    # 默认测试超时时间（秒）
    TEST_TIMEOUT = 10
    
    def setUp(self):
        """设置测试环境"""
        super().setUp()
        # 设置测试超时
        if hasattr(signal, 'SIGALRM'):  # Unix/Linux系统
            signal.signal(signal.SIGALRM, self._timeout_handler)
            signal.alarm(self.TEST_TIMEOUT)
    
    def tearDown(self):
        """清理测试环境"""
        # 取消超时设置
        if hasattr(signal, 'SIGALRM'):
            signal.alarm(0)
        super().tearDown()
    
    def _timeout_handler(self, signum, frame):
        """超时处理器"""
        raise TimeoutError(f"Test timed out after {self.TEST_TIMEOUT} seconds")
    
    def run_subprocess(self, cmd: List[str], input_data: str = None, 
                      timeout: Optional[int] = None, **kwargs) -> subprocess.CompletedProcess:
        """
        运行子进程，带超时控制
        
        Args:
            cmd: 命令列表
            input_data: 输入数据
            timeout: 超时时间，默认使用TEST_TIMEOUT
            **kwargs: 其他subprocess.run参数
        
        Returns:
            subprocess.CompletedProcess对象
        """
        if timeout is None:
            timeout = self.TEST_TIMEOUT
        
        # 设置默认参数
        kwargs.setdefault('capture_output', True)
        kwargs.setdefault('text', True)
        kwargs.setdefault('timeout', timeout)
        
        if input_data:
            kwargs['input'] = input_data
        
        try:
            return subprocess.run(cmd, **kwargs)
        except subprocess.TimeoutExpired as e:
            self.fail(f"Subprocess timed out after {timeout} seconds: {' '.join(cmd)}")
        except Exception as e:
            self.fail(f"Subprocess failed: {e}")
    
    def assertCommandSuccess(self, cmd: List[str], input_data: str = None, 
                           timeout: Optional[int] = None, **kwargs):
        """
        断言命令成功执行
        
        Args:
            cmd: 命令列表
            input_data: 输入数据
            timeout: 超时时间
            **kwargs: 其他subprocess.run参数
        """
        result = self.run_subprocess(cmd, input_data, timeout, **kwargs)
        self.assertEqual(result.returncode, 0, 
                        f"Command failed: {' '.join(cmd)}\nStderr: {result.stderr}")
        return result
    
    def assertCommandFail(self, cmd: List[str], input_data: str = None, 
                         timeout: Optional[int] = None, **kwargs):
        """
        断言命令执行失败
        
        Args:
            cmd: 命令列表
            input_data: 输入数据
            timeout: 超时时间
            **kwargs: 其他subprocess.run参数
        """
        result = self.run_subprocess(cmd, input_data, timeout, **kwargs)
        self.assertNotEqual(result.returncode, 0, 
                           f"Command should have failed: {' '.join(cmd)}")
        return result
    
    def get_bin_path(self, tool_name: str) -> Path:
        """获取bin目录中工具的路径"""
        bin_dir = Path(__file__).parent.parent
        return bin_dir / tool_name
    
    def get_python_path(self, script_name: str) -> Path:
        """获取Python脚本的路径"""
        bin_dir = Path(__file__).parent.parent
        return bin_dir / script_name
    
    @classmethod
    def setUpClass(cls):
        """类级别的设置，可以被子类覆盖来设置不同的超时时间"""
        super().setUpClass()
        # 子类可以通过设置TEST_TIMEOUT来自定义超时时间
        if not hasattr(cls, 'TEST_TIMEOUT'):
            cls.TEST_TIMEOUT = 10


class LongRunningTest(BaseTest):
    """
    长时间运行的测试基类
    默认超时时间为60秒
    """
    TEST_TIMEOUT = 60


class QuickTest(BaseTest):
    """
    快速测试基类
    默认超时时间为5秒
    """
    TEST_TIMEOUT = 5


class APITest(BaseTest):
    """
    API测试基类
    默认超时时间为180秒（3分钟），适合网络请求
    """
    TEST_TIMEOUT = 180 