#!/usr/bin/env python3
"""
测试 GDS upload 和 GDS read 的完整流程
演示上传文件后立即读取的实际场景
"""

import os
import sys
import json
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from google_drive_shell import GoogleDriveShell

def create_test_file():
    """创建测试文件用于上传"""
    test_content = """这是一个测试文件
用于演示 GDS upload 和 read 的完整流程

文件内容包括：
- 第一部分：基本信息
- 第二部分：功能测试
- 第三部分：结果验证

测试时间：2025-01-24
测试目的：验证上传后立即读取的功能

这是第10行内容
这是第11行内容
这是第12行内容

结束标记：测试完成"""
    
    test_file_path = Path(__file__).parent / "upload_test_file.txt"
    with open(test_file_path, 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    return test_file_path, test_content

def test_upload_read_flow():
    """测试完整的上传和读取流程"""
    print("🚀 测试 GDS upload 和 read 完整流程")
    print("=" * 80)
    
    # 创建测试文件
    test_file_path, test_content = create_test_file()
    
    try:
        # 初始化 Google Drive Shell
        gds = GoogleDriveShell()
        
        print(f"📄 测试文件: {test_file_path}")
        print(f"📁 文件大小: {test_file_path.stat().st_size} bytes")
        print()
        
        # 步骤 1: 上传文件
        print("📤 步骤 1: 上传文件到 Google Drive")
        print("-" * 50)
        
        # 模拟上传过程（由于没有实际的 Google Drive Desktop，我们展示预期行为）
        print("调用: gds.cmd_upload([str(test_file_path)], target_path='.')")
        print()
        print("预期行为:")
        print("1. 检查 Google Drive Desktop 是否运行")
        print("2. 将文件移动到 LOCAL_EQUIVALENT 目录")
        print("3. 等待文件同步到 DRIVE_EQUIVALENT")
        print("4. 生成远端命令并等待用户执行")
        print("5. 在远端执行 mv 命令将文件移动到 REMOTE_ROOT")
        print()
        
        # 由于没有实际的 Google Drive 环境，我们模拟上传成功的状态
        print("⚠️  模拟状态: 假设文件已成功上传到远端")
        
        # 模拟上传成功后的缓存状态
        from cache_manager import GDSCacheManager
        cache_manager = GDSCacheManager()
        
        # 创建缓存条目（模拟下载过程中的缓存）
        remote_path = f"~/{test_file_path.name}"
        cache_result = cache_manager.cache_file(
            remote_path=remote_path,
            temp_file_path=str(test_file_path),
            remote_modified_time="2025-01-24T15:40:00.000Z"  # 模拟远端修改时间
        )
        
        if cache_result["success"]:
            print(f"✅ 模拟缓存创建成功: {cache_result['cache_file']}")
        else:
            print(f"❌ 模拟缓存创建失败: {cache_result.get('error')}")
            return
        
        print()
        
        # 步骤 2: 立即读取上传的文件
        print("📖 步骤 2: 读取刚上传的文件")
        print("-" * 50)
        
        print(f"调用: gds.cmd_read('{test_file_path.name}')")
        print()
        
        # 实际调用 cmd_read
        try:
            # 由于 cmd_read 需要 Google Drive API 来获取远端修改时间，
            # 我们直接测试缓存读取部分
            
            # 检查缓存状态
            cache_status = gds.is_remote_file_cached(remote_path)
            print("缓存状态检查:")
            print(f"  是否已缓存: {cache_status['is_cached'] if cache_status['success'] else 'Error'}")
            
            if cache_status["success"] and cache_status["is_cached"]:
                cached_info = cache_status["cached_info"]
                print(f"  缓存文件: {cached_info['cache_file']}")
                print(f"  远端修改时间: {cached_info.get('remote_modified_time', 'N/A')}")
                
                # 直接从缓存读取文件内容
                cache_file_path = cache_status["cache_file_path"]
                if cache_file_path and Path(cache_file_path).exists():
                    with open(cache_file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    
                    print(f"  ✅ 成功从缓存读取文件，内容长度: {len(file_content)} 字符")
                    print()
                    
                    # 演示不同的读取方式
                    print("📋 演示不同的读取方式:")
                    
                    # 1. 读取全部内容
                    lines = file_content.split('\n')
                    all_lines = [(i, line) for i, line in enumerate(lines)]
                    formatted_all = gds._format_read_output(all_lines)
                    
                    print("1. 读取全部内容 (前10行):")
                    all_output_lines = formatted_all.split('\n')
                    for line in all_output_lines[:10]:
                        print(f"   {line}")
                    if len(all_output_lines) > 10:
                        print(f"   ... (还有 {len(all_output_lines) - 10} 行)")
                    print()
                    
                    # 2. 读取前5行
                    selected_lines = [(i, lines[i]) for i in range(min(5, len(lines)))]
                    formatted_range = gds._format_read_output(selected_lines)
                    
                    print("2. 读取前5行 (0-4):")
                    for line in formatted_range.split('\n'):
                        print(f"   {line}")
                    print()
                    
                    # 3. 读取多个范围
                    multi_ranges = [(0, 3), (6, 9), (12, 15)]
                    multi_selected = []
                    for start, end in multi_ranges:
                        for i in range(start, min(end, len(lines))):
                            if i < len(lines):
                                multi_selected.append((i, lines[i]))
                    
                    multi_selected = list(dict(multi_selected).items())
                    multi_selected.sort(key=lambda x: x[0])
                    formatted_multi = gds._format_read_output(multi_selected)
                    
                    print("3. 读取多个范围 [[0,3], [6,9], [12,15]]:")
                    for line in formatted_multi.split('\n'):
                        print(f"   {line}")
                    print()
                
            else:
                print("  ❌ 文件未在缓存中找到")
            
        except Exception as e:
            print(f"❌ 读取过程出错: {e}")
        
        # 步骤 3: 分析结果
        print("🔍 步骤 3: 流程分析")
        print("-" * 50)
        
        print("实际场景下的行为:")
        print("1. 上传文件后，文件会被缓存在本地")
        print("2. 立即调用 read 时，会检查缓存新鲜度")
        print("3. 由于刚上传，缓存是最新的，直接使用缓存")
        print("4. 无需重新下载，提供快速读取体验")
        print()
        
        print("优势:")
        print("✅ 无网络延迟: 直接从本地缓存读取")
        print("✅ 数据一致性: 缓存包含远端修改时间信息")
        print("✅ 高效体验: 上传后立即可读取")
        print("✅ 智能判断: 自动检查缓存是否为最新")
        
        print()
        print("✅ 测试完成!")
        
    finally:
        # 清理测试文件
        if test_file_path.exists():
            test_file_path.unlink()
        
        # 清理缓存
        try:
            from cache_manager import GDSCacheManager
            cache_manager = GDSCacheManager()
            cache_manager.cleanup_cache(remote_path)
            print(f"\n🧹 已清理测试文件和缓存")
        except:
            pass

if __name__ == "__main__":
    test_upload_read_flow() 