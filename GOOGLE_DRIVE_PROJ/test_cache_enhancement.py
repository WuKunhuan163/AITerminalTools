#!/usr/bin/env python3
"""
测试 Google Drive Shell 缓存增强功能
测试新增的接口函数和改进的缓存机制
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from google_drive_shell import GoogleDriveShell
from cache_manager import GDSCacheManager

def test_cache_interface():
    """测试缓存接口函数"""
    print("=" * 60)
    print("测试缓存接口函数")
    print("=" * 60)
    
    # 初始化 Google Drive Shell
    gds = GoogleDriveShell()
    
    # 测试文件路径（假设这些文件存在于远端）
    test_files = [
        "test.txt",
        "~/documents/sample.pdf",
        "nonexistent.file"
    ]
    
    for remote_path in test_files:
        print(f"\n🔍 测试文件: {remote_path}")
        
        # 测试缓存状态检查
        cache_status = gds.is_remote_file_cached(remote_path)
        print(f"  缓存状态: {cache_status}")
        
        # 测试获取远端修改时间
        if cache_status.get("success"):
            mod_time_result = gds.get_remote_file_modification_time(remote_path)
            print(f"  远端修改时间: {mod_time_result}")
            
            # 测试缓存新鲜度检查
            freshness_result = gds.is_cached_file_up_to_date(remote_path)
            print(f"  缓存新鲜度: {freshness_result}")

def test_cache_manager_enhancement():
    """测试缓存管理器的增强功能"""
    print("\n" + "=" * 60)
    print("测试缓存管理器增强功能")
    print("=" * 60)
    
    # 初始化缓存管理器
    cache_manager = GDSCacheManager()
    
    # 创建测试文件
    test_file_path = Path(__file__).parent / "test_temp_file.txt"
    test_content = "这是一个测试文件内容\n用于测试缓存功能"
    
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    try:
        # 测试缓存文件（包含远端修改时间）
        remote_path = "~/test/cached_file.txt"
        remote_modified_time = "2025-01-23T12:00:00.000Z"
        
        print(f"\n📁 缓存文件: {remote_path}")
        cache_result = cache_manager.cache_file(
            remote_path=remote_path,
            temp_file_path=str(test_file_path),
            remote_modified_time=remote_modified_time
        )
        print(f"  缓存结果: {cache_result}")
        
        # 测试获取缓存信息
        print(f"\n🔍 检查缓存信息:")
        cached_info = cache_manager.get_cached_file(remote_path)
        print(f"  缓存信息: {json.dumps(cached_info, indent=2, ensure_ascii=False)}")
        
        # 测试缓存状态检查
        is_cached = cache_manager.is_file_cached(remote_path)
        print(f"  是否已缓存: {is_cached}")
        
        # 测试获取缓存文件路径
        cached_path = cache_manager.get_cached_file_path(remote_path)
        print(f"  缓存文件路径: {cached_path}")
        
        # 测试缓存统计
        stats = cache_manager.get_cache_stats()
        print(f"\n📊 缓存统计: {json.dumps(stats, indent=2, ensure_ascii=False)}")
        
    finally:
        # 清理测试文件
        if test_file_path.exists():
            test_file_path.unlink()
        
        # 清理缓存
        cache_manager.cleanup_cache(remote_path)

def test_cache_config_format():
    """测试缓存配置文件格式"""
    print("\n" + "=" * 60)
    print("测试缓存配置文件格式")
    print("=" * 60)
    
    cache_config_file = Path(__file__).parent / "cache_config.json"
    
    if cache_config_file.exists():
        with open(cache_config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"📄 缓存配置文件内容:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        
        # 检查是否包含新的字段
        files = config.get("files", {})
        if files:
            print(f"\n🔍 检查缓存文件字段:")
            for remote_path, file_info in files.items():
                print(f"  文件: {remote_path}")
                print(f"    upload_time: {file_info.get('upload_time', 'N/A')}")
                print(f"    remote_modified_time: {file_info.get('remote_modified_time', 'N/A')}")
                print(f"    content_hash: {file_info.get('content_hash', 'N/A')}")
                print(f"    status: {file_info.get('status', 'N/A')}")
        else:
            print("  暂无缓存文件")
    else:
        print("⚠️  缓存配置文件不存在")

def main():
    """主测试函数"""
    print("🚀 开始测试 Google Drive Shell 缓存增强功能")
    
    try:
        # 测试缓存管理器增强功能
        test_cache_manager_enhancement()
        
        # 测试缓存配置文件格式
        test_cache_config_format()
        
        # 测试缓存接口函数（需要 Google Drive API）
        print("\n⚠️  缓存接口函数测试需要 Google Drive API 连接")
        print("   如果 API 可用，可以取消注释下面的测试:")
        print("   # test_cache_interface()")
        
        print(f"\n✅ 测试完成!")
        
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 