#!/usr/bin/env python3
"""
PYPI - Python Package Index API Tool

A comprehensive tool for interacting with PyPI API to get package information,
dependencies, sizes, and metadata.

Features:
- Package dependency analysis
- Package size information
- Parallel API calls for performance
- Rate limiting and error handling
- Comprehensive package metadata
"""

import sys
import json
import argparse
import requests
import re
import time
import os
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional, Union
from datetime import datetime, timedelta


class APIRateLimiter:
    """
    API速率限制器
    确保每秒最多40次API调用，支持多线程并发控制
    """
    
    def __init__(self, max_calls_per_second: int = 40, data_folder: str = "PYPI_DATA"):
        self.max_calls_per_second = max_calls_per_second
        self.data_folder = data_folder
        self.call_history = deque()  # 存储最近的API调用时间戳
        self.lock = threading.Lock()  # 线程锁
        self.request_queue = deque()  # 请求队列
        self.stats = {
            "total_calls": 0,
            "queued_calls": 0,
            "delayed_calls": 0,
            "average_delay": 0.0
        }
        
        # 确保数据文件夹存在
        self._ensure_data_folder()
        
        # 加载历史统计数据
        self._load_stats()
    
    def _ensure_data_folder(self):
        """确保数据文件夹存在"""
        if not os.path.exists(self.data_folder):
            os.makedirs(self.data_folder)
    
    def _load_stats(self):
        """加载历史统计数据"""
        stats_file = os.path.join(self.data_folder, "api_rate_stats.json")
        try:
            if os.path.exists(stats_file):
                with open(stats_file, 'r') as f:
                    saved_stats = json.load(f)
                    self.stats.update(saved_stats)
        except Exception:
            pass  # 忽略加载错误，使用默认值
    
    def _save_stats(self):
        """保存统计数据"""
        stats_file = os.path.join(self.data_folder, "api_rate_stats.json")
        try:
            # 添加时间戳
            self.stats["last_updated"] = datetime.now().isoformat()
            with open(stats_file, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception:
            pass  # 忽略保存错误
    
    def _cleanup_old_calls(self):
        """清理1秒前的旧调用记录"""
        current_time = time.time()
        cutoff_time = current_time - 1.0
        
        while self.call_history and self.call_history[0] < cutoff_time:
            self.call_history.popleft()
    
    def _calculate_delay(self) -> float:
        """计算需要等待的时间"""
        self._cleanup_old_calls()
        
        if len(self.call_history) < self.max_calls_per_second:
            return 0.0  # 不需要等待
        
        # 如果已达到限制，计算需要等待到最旧的调用过期
        oldest_call = self.call_history[0]
        wait_time = oldest_call + 1.0 - time.time()
        return max(0.0, wait_time)
    
    def acquire(self) -> float:
        """
        获取API调用许可
        
        Returns:
            实际等待的时间（秒）
        """
        with self.lock:
            delay = self._calculate_delay()
            
            if delay > 0:
                self.stats["delayed_calls"] += 1
                self.stats["queued_calls"] += 1
                
                # 更新平均延迟
                total_delay = self.stats["average_delay"] * (self.stats["delayed_calls"] - 1) + delay
                self.stats["average_delay"] = total_delay / self.stats["delayed_calls"]
        
        # 在锁外等待，避免阻塞其他线程
        if delay > 0:
            time.sleep(delay)
        
        # 记录这次调用
        with self.lock:
            current_time = time.time()
            self.call_history.append(current_time)
            self.stats["total_calls"] += 1
            if delay > 0:
                self.stats["queued_calls"] -= 1
        
        return delay
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self.lock:
            stats_copy = self.stats.copy()
            stats_copy["current_queue_size"] = len(self.request_queue)
            stats_copy["calls_in_last_second"] = len(self.call_history)
            return stats_copy
    
    def save_and_reset_stats(self):
        """保存并重置统计数据"""
        with self.lock:
            self._save_stats()
            self.stats = {
                "total_calls": 0,
                "queued_calls": 0,
                "delayed_calls": 0,
                "average_delay": 0.0
            }


# 全局API限流器实例
_global_rate_limiter = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> APIRateLimiter:
    """获取全局API限流器实例（单例模式）"""
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        with _limiter_lock:
            if _global_rate_limiter is None:
                # 确定数据文件夹路径
                script_dir = os.path.dirname(os.path.abspath(__file__))
                data_folder = os.path.join(script_dir, "PYPI_DATA")
                _global_rate_limiter = APIRateLimiter(data_folder=data_folder)
    
    return _global_rate_limiter


class PyPIClient:
    """PyPI API client with comprehensive package information retrieval"""
    
    def __init__(self, timeout: int = 10, max_workers: int = 40):
        self.timeout = timeout
        self.max_workers = max_workers
        self.session = requests.Session()
        self.rate_limiter = get_rate_limiter()
        
    def get_package_info(self, package_name: str) -> Optional[Dict]:
        """
        Get comprehensive package information from PyPI
        
        Args:
            package_name: Package name to query
            
        Returns:
            Dict containing package info or None if not found
        """
        try:
            # 使用API限流器
            delay = self.rate_limiter.acquire()
            
            api_url = f"https://pypi.org/pypi/{package_name}/json"
            response = self.session.get(api_url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            print(f"Error fetching package info for {package_name}: {e}")
            return None
    
    def get_package_dependencies(self, package_name: str) -> Optional[List[str]]:
        """
        Get direct dependencies of a package
        
        Args:
            package_name: Package name to query
            
        Returns:
            List of dependency names or None if not found
        """
        data = self.get_package_info(package_name)
        if not data:
            return None
            
        dependencies = []
        info = data.get("info", {})
        requires_dist = info.get("requires_dist", [])
        
        if requires_dist:
            for req in requires_dist:
                # Extract package name, ignoring version constraints
                match = re.match(r"([a-zA-Z0-9._-]+)", req)
                if match:
                    dep_name = match.group(1)
                    dependencies.append(dep_name)
        
        return dependencies
    
    def get_package_size(self, package_name: str) -> int:
        """
        Get package size in bytes
        
        Args:
            package_name: Package name to query
            
        Returns:
            Package size in bytes, 0 if not found
        """
        data = self.get_package_info(package_name)
        if not data:
            return 0
            
        info = data.get("info", {})
        releases = data.get("releases", {})
        version = info.get("version", "")
        
        if version and version in releases:
            files = releases[version]
            if files:
                # Return the size of the largest file
                return max((f.get("size", 0) for f in files), default=0)
        
        return 0
    
    def get_package_dependencies_with_size(self, package_name: str) -> Tuple[Optional[List[str]], int]:
        """
        Get both dependencies and size in a single API call
        
        Args:
            package_name: Package name to query
            
        Returns:
            Tuple of (dependencies list, package size in bytes)
        """
        data = self.get_package_info(package_name)
        if not data:
            return None, 0
        
        # Extract dependencies
        dependencies = []
        info = data.get("info", {})
        requires_dist = info.get("requires_dist", [])
        
        if requires_dist:
            for req in requires_dist:
                match = re.match(r"([a-zA-Z0-9._-]+)", req)
                if match:
                    dep_name = match.group(1)
                    dependencies.append(dep_name)
        
        # Extract size
        releases = data.get("releases", {})
        version = info.get("version", "")
        package_size = 0
        
        if version and version in releases:
            files = releases[version]
            if files:
                package_size = max((f.get("size", 0) for f in files), default=0)
        
        return dependencies, package_size
    
    def get_package_metadata(self, package_name: str) -> Optional[Dict]:
        """
        Get comprehensive package metadata
        
        Args:
            package_name: Package name to query
            
        Returns:
            Dict containing metadata or None if not found
        """
        data = self.get_package_info(package_name)
        if not data:
            return None
        
        info = data.get("info", {})
        releases = data.get("releases", {})
        version = info.get("version", "")
        
        # Calculate package size
        package_size = 0
        if version and version in releases:
            files = releases[version]
            if files:
                package_size = max((f.get("size", 0) for f in files), default=0)
        
        # Extract dependencies
        dependencies = []
        requires_dist = info.get("requires_dist", [])
        if requires_dist:
            for req in requires_dist:
                match = re.match(r"([a-zA-Z0-9._-]+)", req)
                if match:
                    dep_name = match.group(1)
                    dependencies.append(dep_name)
        
        return {
            "name": info.get("name", package_name),
            "version": version,
            "summary": info.get("summary", ""),
            "description": info.get("description", ""),
            "author": info.get("author", ""),
            "author_email": info.get("author_email", ""),
            "license": info.get("license", ""),
            "home_page": info.get("home_page", ""),
            "project_url": info.get("project_url", ""),
            "download_url": info.get("download_url", ""),
            "size": package_size,
            "dependencies": dependencies,
            "requires_python": info.get("requires_python", ""),
            "classifiers": info.get("classifiers", []),
            "keywords": info.get("keywords", ""),
            "platform": info.get("platform", ""),
        }
    
    def batch_get_dependencies_with_sizes(self, package_names: List[str]) -> Dict[str, Tuple[Optional[List[str]], int]]:
        """
        Get dependencies and sizes for multiple packages in parallel
        
        Args:
            package_names: List of package names to query
            
        Returns:
            Dict mapping package names to (dependencies, size) tuples
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(package_names))) as executor:
            # Submit all tasks
            future_to_package = {
                executor.submit(self.get_package_dependencies_with_size, pkg): pkg 
                for pkg in package_names
            }
            
            # Collect results
            for future in future_to_package:
                package_name = future_to_package[future]
                try:
                    dependencies, size = future.result()
                    results[package_name] = (dependencies, size)
                except Exception as e:
                    print(f"Error processing {package_name}: {e}")
                    results[package_name] = (None, 0)
        
        return results
    
    def search_packages(self, query: str, limit: int = 20) -> List[Dict]:
        """
        Search for packages on PyPI
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of package information dictionaries
        """
        try:
            # PyPI doesn't have a direct search API anymore, but we can use the warehouse API
            # This is a simplified implementation
            search_url = f"https://pypi.org/search/?q={query}"
            print(f"Note: Direct search API not available. Visit {search_url} for search results.")
            return []
        except Exception as e:
            print(f"Error searching packages: {e}")
            return []


def format_size(size_bytes: int) -> str:
    """Format size in human-readable format"""
    if size_bytes == 0:
        return "0B"
    elif size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f}KB"
    else:
        return f"{size_bytes/(1024*1024):.1f}MB"


def main():
    parser = argparse.ArgumentParser(description="PyPI API Tool")
    parser.add_argument("command", choices=["info", "deps", "size", "metadata", "batch", "test", "stats"], 
                       help="Command to execute")
    parser.add_argument("package", nargs="?", help="Package name")
    parser.add_argument("--packages", nargs="+", help="Multiple package names for batch operations")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout in seconds")
    parser.add_argument("--workers", type=int, default=40, help="Maximum number of parallel workers")
    
    args = parser.parse_args()
    
    client = PyPIClient(timeout=args.timeout, max_workers=args.workers)
    
    if args.command == "stats":
        # 显示API限流统计信息
        rate_limiter = get_rate_limiter()
        stats = rate_limiter.get_stats()
        
        if args.json:
            print(json.dumps(stats, indent=2))
        else:
            print(f"API Rate Limiting Statistics:")
            print(f"  Total API calls: {stats['total_calls']}")
            print(f"  Delayed calls: {stats['delayed_calls']}")
            print(f"  Currently queued: {stats['queued_calls']}")
            print(f"  Calls in last second: {stats['calls_in_last_second']}")
            print(f"  Average delay: {stats['average_delay']:.3f}s")
            
            if 'last_updated' in stats:
                print(f"  Last updated: {stats['last_updated']}")
        
        return
    
    if args.command == "test":
        # Test connection and basic functionality
        print(f"Testing PyPI API connection...")
        test_packages = ["requests", "numpy", "pandas"]
        
        for pkg in test_packages:
            print(f"\nTesting {pkg}:")
            deps, size = client.get_package_dependencies_with_size(pkg)
            if deps is not None:
                print(f"Found {len(deps)} dependencies, size: {format_size(size)}")
            else:
                print(f"Error: Package not found")
        
        print(f"\nTest completed.")
        return
    
    if not args.package and not args.packages:
        print(f"Error: Package name required for this command")
        return
    
    if args.command == "info":
        info = client.get_package_info(args.package)
        if info:
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                pkg_info = info.get("info", {})
                print(f"Name: {pkg_info.get('name', args.package)}")
                print(f"Version: {pkg_info.get('version', 'N/A')}")
                print(f"Summary: {pkg_info.get('summary', 'N/A')}")
                print(f"Author: {pkg_info.get('author', 'N/A')}")
                print(f"License: {pkg_info.get('license', 'N/A')}")
        else:
            print(f"Package '{args.package}' not found")
    
    elif args.command == "deps":
        deps = client.get_package_dependencies(args.package)
        if deps is not None:
            if args.json:
                print(json.dumps({"package": args.package, "dependencies": deps}))
            else:
                print(f"Dependencies for {args.package}:")
                for dep in deps:
                    print(f"  - {dep}")
        else:
            print(f"Package '{args.package}' not found")
    
    elif args.command == "size":
        size = client.get_package_size(args.package)
        if args.json:
            print(json.dumps({"package": args.package, "size": size, "formatted_size": format_size(size)}))
        else:
            print(f"Size of {args.package}: {format_size(size)} ({size} bytes)")
    
    elif args.command == "metadata":
        metadata = client.get_package_metadata(args.package)
        if metadata:
            if args.json:
                print(json.dumps(metadata, indent=2))
            else:
                print(f"Package: {metadata['name']}")
                print(f"Version: {metadata['version']}")
                print(f"Summary: {metadata['summary']}")
                print(f"Size: {format_size(metadata['size'])}")
                print(f"Dependencies ({len(metadata['dependencies'])}):")
                for dep in metadata['dependencies']:
                    print(f"  - {dep}")
        else:
            print(f"Package '{args.package}' not found")
    
    elif args.command == "batch":
        if not args.packages:
            print(f"Error: --packages required for batch command")
            return
        
        print(f"Processing {len(args.packages)} packages...")
        results = client.batch_get_dependencies_with_sizes(args.packages)
        
        if args.json:
            formatted_results = {}
            for pkg, (deps, size) in results.items():
                formatted_results[pkg] = {
                    "dependencies": deps,
                    "size": size,
                    "formatted_size": format_size(size)
                }
            print(json.dumps(formatted_results, indent=2))
        else:
            for pkg, (deps, size) in results.items():
                if deps is not None:
                    print(f"{pkg}: {len(deps)} deps, {format_size(size)}")
                else:
                    print(f"{pkg}: Not found")


if __name__ == "__main__":
    main()
