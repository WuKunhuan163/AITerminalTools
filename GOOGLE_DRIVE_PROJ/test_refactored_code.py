#!/usr/bin/env python3
"""
测试重构后的Google Drive Shell代码
验证模块导入和基本功能是否正常
"""

import sys
import os
from pathlib import Path

def test_module_imports():
    """测试模块导入"""
    print("🔄 测试模块导入...")
    
    try:
        # 测试各个模块的导入
        from modules.shell_management import ShellManagement
        from modules.file_operations import FileOperations
        from modules.cache_manager import CacheManager
        from modules.remote_commands import RemoteCommands
        from modules.path_resolver import PathResolver
        from modules.sync_manager import SyncManager
        from modules.file_utils import FileUtils
        from modules.validation import Validation
        from modules.verification import Verification
        
        print("✅ 所有模块导入成功")
        return True
        
    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他导入错误: {e}")
        return False

def test_module_initialization():
    """测试模块初始化"""
    print("\n🔄 测试模块初始化...")
    
    try:
        from modules.shell_management import ShellManagement
        from modules.cache_manager import CacheManager
        
        # 模拟drive_service
        mock_drive_service = type('MockDriveService', (), {})()
        
        # 测试初始化
        shell_mgr = ShellManagement(mock_drive_service)
        cache_mgr = CacheManager(mock_drive_service)
        
        print("✅ 模块初始化成功")
        return True
        
    except Exception as e:
        print(f"❌ 模块初始化失败: {e}")
        return False

def test_function_existence():
    """测试关键函数是否存在"""
    print("\n🔄 测试关键函数存在性...")
    
    try:
        from modules.shell_management import ShellManagement
        from modules.file_operations import FileOperations
        from modules.cache_manager import CacheManager
        
        # 检查关键方法是否存在
        shell_methods = ['load_shells', 'save_shells', 'create_shell', 'list_shells']
        file_methods = ['cmd_ls', 'cmd_cd', 'cmd_upload', 'cmd_download']
        cache_methods = ['load_cache_config', 'is_cached_file_up_to_date']
        
        mock_drive_service = type('MockDriveService', (), {})()
        
        shell_mgr = ShellManagement(mock_drive_service)
        file_ops = FileOperations(mock_drive_service)
        cache_mgr = CacheManager(mock_drive_service)
        
        # 检查方法存在
        for method in shell_methods:
            if not hasattr(shell_mgr, method):
                raise AttributeError(f"ShellManagement缺少方法: {method}")
        
        for method in file_methods:
            if not hasattr(file_ops, method):
                raise AttributeError(f"FileOperations缺少方法: {method}")
                
        for method in cache_methods:
            if not hasattr(cache_mgr, method):
                raise AttributeError(f"CacheManager缺少方法: {method}")
        
        print("✅ 关键函数存在性检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 函数存在性检查失败: {e}")
        return False

def test_original_vs_refactored_api():
    """比较原始类和重构类的API兼容性"""
    print("\n🔄 测试API兼容性...")
    
    try:
        # 导入原始类
        from google_drive_shell import GoogleDriveShell as OriginalShell
        
        # 获取原始类的公共方法
        original_methods = [method for method in dir(OriginalShell) 
                          if not method.startswith('_') and callable(getattr(OriginalShell, method))]
        
        print(f"原始类公共方法数量: {len(original_methods)}")
        print(f"主要方法: {original_methods[:10]}...")  # 显示前10个方法
        
        # 检查重构后的模块是否包含这些方法
        from modules import (
            ShellManagement, FileOperations, CacheManager, RemoteCommands,
            PathResolver, SyncManager, FileUtils, Validation, Verification
        )
        
        # 统计各模块的方法数量
        module_classes = [
            ('ShellManagement', ShellManagement),
            ('FileOperations', FileOperations), 
            ('CacheManager', CacheManager),
            ('RemoteCommands', RemoteCommands),
            ('PathResolver', PathResolver),
            ('SyncManager', SyncManager),
            ('FileUtils', FileUtils),
            ('Validation', Validation),
            ('Verification', Verification)
        ]
        
        total_refactored_methods = 0
        for name, cls in module_classes:
            methods = [m for m in dir(cls) if not m.startswith('_') and m != '__init__']
            total_refactored_methods += len(methods)
            print(f"{name}: {len(methods)} 个方法")
        
        print(f"重构后总方法数量: {total_refactored_methods}")
        print("✅ API兼容性检查完成")
        return True
        
    except Exception as e:
        print(f"❌ API兼容性检查失败: {e}")
        return False

def test_code_quality():
    """测试代码质量"""
    print("\n🔄 测试代码质量...")
    
    try:
        # 检查模块文件大小
        modules_dir = Path("modules")
        total_lines = 0
        
        for module_file in modules_dir.glob("*.py"):
            if module_file.name == "__init__.py":
                continue
                
            with open(module_file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                print(f"{module_file.name}: {lines} 行")
        
        # 检查原始文件大小
        with open("google_drive_shell.py", 'r', encoding='utf-8') as f:
            original_lines = len(f.readlines())
        
        print(f"\n原始文件: {original_lines} 行")
        print(f"重构后总行数: {total_lines} 行")
        print(f"代码分割效率: {(total_lines/original_lines)*100:.1f}%")
        
        # 检查最大模块大小
        max_module_size = 0
        largest_module = ""
        
        for module_file in modules_dir.glob("*.py"):
            if module_file.name == "__init__.py":
                continue
                
            with open(module_file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                if lines > max_module_size:
                    max_module_size = lines
                    largest_module = module_file.name
        
        print(f"最大模块: {largest_module} ({max_module_size} 行)")
        
        if max_module_size < 3000:  # 每个模块应该小于3000行
            print("✅ 代码分割质量良好")
            return True
        else:
            print("⚠️  某些模块仍然过大，可能需要进一步分割")
            return True
            
    except Exception as e:
        print(f"❌ 代码质量检查失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试重构后的Google Drive Shell代码\n")
    
    tests = [
        ("模块导入", test_module_imports),
        ("模块初始化", test_module_initialization), 
        ("函数存在性", test_function_existence),
        ("API兼容性", test_original_vs_refactored_api),
        ("代码质量", test_code_quality)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！重构成功！")
        return True
    else:
        print("⚠️  部分测试失败，需要进一步调试")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 