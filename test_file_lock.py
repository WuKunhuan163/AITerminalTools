#!/usr/bin/env python3

import sys
import os
import time
import fcntl
import threading
from pathlib import Path

def test_file_lock(process_id, iterations=3):
    """测试文件锁在多进程间的工作情况"""
    lock_file_path = Path("tmp/test_file.lock")
    lock_file_path.parent.mkdir(exist_ok=True)
    
    for i in range(iterations):
        print(f"Process {process_id}: Attempt {i+1}/{iterations}")
        
        # 尝试获取文件锁
        try:
            with open(lock_file_path, 'w') as lock_file:
                print(f"Process {process_id}: Trying to acquire lock...")
                start_time = time.time()
                
                # 尝试获取排他锁（非阻塞）
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquire_time = time.time() - start_time
                
                print(f"Process {process_id}: ✅ ACQUIRED LOCK in {acquire_time:.3f}s at {time.strftime('%H:%M:%S.%f')[:-3]}")
                
                # 记录到测试文件
                with open("tmp/lock_test_results.txt", "a") as f:
                    timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                    f.write(f"[{timestamp}] Process {process_id}: LOCK ACQUIRED (attempt {i+1})\n")
                
                # 持有锁一段时间
                time.sleep(1)
                
                print(f"Process {process_id}: ✅ RELEASING LOCK")
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                
                # 记录释放
                with open("tmp/lock_test_results.txt", "a") as f:
                    timestamp = time.strftime('%H:%M:%S.%f')[:-3]
                    f.write(f"[{timestamp}] Process {process_id}: LOCK RELEASED (attempt {i+1})\n")
                
        except (IOError, OSError) as e:
            print(f"Process {process_id}: ❌ FAILED to acquire lock: {e}")
            # 等待后重试
            time.sleep(0.5)
        
        # 进程间等待
        time.sleep(0.1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 test_file_lock.py <process_id>")
        sys.exit(1)
    
    process_id = sys.argv[1]
    print(f"Starting file lock test for process {process_id}")
    test_file_lock(process_id)
    print(f"Process {process_id} finished")

