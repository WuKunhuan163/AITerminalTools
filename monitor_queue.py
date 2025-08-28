#!/usr/bin/env python3
"""
监控远程窗口队列状态的脚本
"""

import json
import time
from pathlib import Path

def monitor_queue():
    queue_file = Path(__file__).parent / "GOOGLE_DRIVE_PROJ" / "remote_window_queue.json"
    print("🔍 开始监控远程窗口队列状态...")
    print("=" * 60)
    
    start_time = time.time()
    last_count = 0
    
    while True:
        try:
            if queue_file.exists():
                with open(queue_file, 'r', encoding='utf-8') as f:
                    queue_data = json.load(f)
                
                current_count = queue_data.get("completed_windows_count", 0)
                current_window = queue_data.get("current_window")
                waiting_count = len(queue_data.get("waiting_queue", []))
                
                elapsed_time = int(time.time() - start_time)
                
                # 清屏并显示状态
                print(f"\r⏱️  监控时间: {elapsed_time}s | 完成窗口: {current_count} | 当前窗口: {'有' if current_window else '无'} | 等待队列: {waiting_count}", end="", flush=True)
                
                # 检查是否有新的完成窗口
                if current_count > last_count:
                    print(f"\n✅ 新完成窗口: {current_count - last_count} 个")
                    last_count = current_count
                
                # 如果120秒内完成了至少4个窗口，认为正常
                if elapsed_time >= 120:
                    if current_count >= 4:
                        print(f"\n🎉 测试正常！120秒内完成了 {current_count} 个窗口")
                        break
                    else:
                        print(f"\n⚠️  可能卡住！120秒内只完成了 {current_count} 个窗口")
                        print("\n当前队列详细状态:")
                        print(json.dumps(queue_data, indent=2, ensure_ascii=False))
                        break
                
                time.sleep(1)
            else:
                print(f"\r⏱️  监控时间: {int(time.time() - start_time)}s | 队列文件不存在", end="", flush=True)
                time.sleep(1)
                
        except KeyboardInterrupt:
            print(f"\n⛔ 监控被用户中断")
            break
        except Exception as e:
            print(f"\n❌ 监控出错: {e}")
            time.sleep(1)

if __name__ == "__main__":
    monitor_queue()
