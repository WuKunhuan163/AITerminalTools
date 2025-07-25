#!/usr/bin/env python3
"""
演示 Google Drive Shell 缓存增强功能
展示完整的缓存流程：检查缓存、获取远端时间、判断新鲜度
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from google_drive_shell import GoogleDriveShell
from cache_manager import GDSCacheManager

def demo_cache_workflow():
    """演示完整的缓存工作流程"""
    print("🚀 Google Drive Shell 缓存增强功能演示")
    print("=" * 80)
    
    # 初始化组件
    gds = GoogleDriveShell()
    cache_manager = GDSCacheManager()
    
    # 模拟文件路径
    test_remote_path = "~/demo/test_document.txt"
    
    print(f"📄 演示文件: {test_remote_path}")
    print("-" * 80)
    
    # 步骤 1: 检查文件是否已缓存
    print("🔍 步骤 1: 检查文件缓存状态")
    cache_status = gds.is_remote_file_cached(test_remote_path)
    
    if cache_status["success"]:
        if cache_status["is_cached"]:
            print(f"✅ 文件已缓存")
            print(f"   缓存文件: {cache_status['cached_info']['cache_file']}")
            print(f"   缓存时间: {cache_status['cached_info'].get('upload_time', 'N/A')}")
            print(f"   远端修改时间: {cache_status['cached_info'].get('remote_modified_time', 'N/A')}")
        else:
            print(f"❌ 文件未缓存")
    else:
        print(f"❌ 检查缓存状态失败: {cache_status.get('error', 'Unknown error')}")
    
    print()
    
    # 步骤 2: 模拟获取远端文件修改时间
    print("🌐 步骤 2: 获取远端文件修改时间")
    print("   (模拟 - 实际需要 Google Drive API 连接)")
    
    # 模拟远端文件信息
    simulated_remote_time = "2025-01-23T15:30:00.000Z"
    print(f"   模拟远端修改时间: {simulated_remote_time}")
    print()
    
    # 步骤 3: 创建测试缓存文件
    print("📁 步骤 3: 创建测试缓存文件")
    
    # 创建临时测试文件
    test_file_path = Path(__file__).parent / "demo_temp_file.txt"
    test_content = f"""这是一个演示文件
创建时间: {datetime.now().isoformat()}
用于演示 Google Drive Shell 缓存增强功能

包含的新功能:
1. 远端文件修改时间跟踪
2. 缓存新鲜度检查
3. 智能缓存更新机制
"""
    
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    try:
        # 缓存文件（包含远端修改时间）
        cache_result = cache_manager.cache_file(
            remote_path=test_remote_path,
            temp_file_path=str(test_file_path),
            remote_modified_time=simulated_remote_time
        )
        
        if cache_result["success"]:
            print(f"✅ 文件缓存成功")
            print(f"   缓存文件: {cache_result['cache_file']}")
            print(f"   缓存路径: {cache_result['cache_path']}")
            print(f"   远端修改时间: {cache_result['remote_modified_time']}")
        else:
            print(f"❌ 文件缓存失败: {cache_result.get('error', 'Unknown error')}")
            return
        
        print()
        
        # 步骤 4: 再次检查缓存状态
        print("🔄 步骤 4: 再次检查缓存状态")
        updated_cache_status = gds.is_remote_file_cached(test_remote_path)
        
        if updated_cache_status["success"] and updated_cache_status["is_cached"]:
            cached_info = updated_cache_status["cached_info"]
            print(f"✅ 文件现已缓存")
            print(f"   缓存文件: {cached_info['cache_file']}")
            print(f"   本地缓存时间: {cached_info.get('upload_time', 'N/A')}")
            print(f"   远端修改时间: {cached_info.get('remote_modified_time', 'N/A')}")
            print(f"   内容哈希: {cached_info.get('content_hash', 'N/A')}")
            print(f"   状态: {cached_info.get('status', 'N/A')}")
        
        print()
        
        # 步骤 5: 演示缓存新鲜度检查
        print("🕐 步骤 5: 演示缓存新鲜度检查")
        
        # 情况 1: 文件未变更（相同的修改时间）
        print("   情况 1: 远端文件未变更")
        freshness_result = gds.is_cached_file_up_to_date(test_remote_path)
        
        if freshness_result["success"]:
            print(f"   缓存是否最新: {freshness_result['is_up_to_date']}")
            print(f"   判断原因: {freshness_result.get('reason', 'N/A')}")
            
            if 'remote_modification_time' in freshness_result:
                print(f"   远端修改时间: {freshness_result['remote_modification_time']}")
            if 'cached_remote_time' in freshness_result:
                print(f"   缓存的远端时间: {freshness_result['cached_remote_time']}")
        
        print()
        
        # 情况 2: 模拟文件更新
        print("   情况 2: 模拟远端文件已更新")
        newer_remote_time = "2025-01-23T16:00:00.000Z"
        print(f"   新的远端修改时间: {newer_remote_time}")
        
        # 手动更新缓存信息中的远端时间以模拟比较
        print("   (实际使用中会通过 GDS ls 命令获取最新的远端修改时间)")
        
        print()
        
        # 步骤 6: 显示缓存配置文件
        print("📋 步骤 6: 查看缓存配置文件")
        cache_config_file = Path(__file__).parent / "cache_config.json"
        
        if cache_config_file.exists():
            with open(cache_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print("   当前缓存配置:")
            print(json.dumps(config, indent=4, ensure_ascii=False))
        
        print()
        
        # 步骤 7: 缓存统计
        print("📊 步骤 7: 缓存统计信息")
        stats = cache_manager.get_cache_stats()
        
        if stats["success"]:
            print(f"   总缓存文件数: {stats['total_files']}")
            print(f"   总缓存大小: {stats['total_size_mb']} MB")
            print(f"   缓存目录: {stats['cache_root']}")
        
        print()
        print("✅ 演示完成!")
        print("\n💡 主要改进:")
        print("   1. cache_config.json 现在包含 remote_modified_time 字段")
        print("   2. 新增了 3 个接口函数用于缓存状态检查和新鲜度判断")
        print("   3. 下载文件时会自动保存远端修改时间")
        print("   4. 支持基于远端修改时间的智能缓存更新")
        
    finally:
        # 清理测试文件
        if test_file_path.exists():
            test_file_path.unlink()
        
        # 清理演示缓存
        cache_manager.cleanup_cache(test_remote_path)
        print(f"\n🧹 已清理演示文件和缓存")

if __name__ == "__main__":
    demo_cache_workflow() 