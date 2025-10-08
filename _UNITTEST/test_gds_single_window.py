#!/usr/bin/env python3
"""
GDS单窗口控制测试 - 确保任何时候只有一个窗口存在
容忍性测试：假设用户交互时间无限长
"""

import unittest
import subprocess
import time
import psutil
import threading
import sys
import os
from pathlib import Path

class TestGDSSingleWindow(unittest.TestCase):
    """测试GDS单窗口控制机制"""
    
    def setUp(self):
        """测试前准备"""
        self.window_count = 0
        self.max_concurrent = 0
        self.window_history = []
        self.monitoring = False
        self.test_failed = False
        self.failure_reason = ""
        self.first_window_time = None
        
        # 清理调试日志
        debug_files = [
            'GOOGLE_DRIVE_DATA/force_debug.log',
            'GOOGLE_DRIVE_DATA/window_queue_debug.log'
        ]
        
        for f in debug_files:
            if os.path.exists(f):
                os.remove(f)
                print(f"已清理: {f}")
        
        print("测试环境清理完成")
        
    def detect_gds_windows(self):
        """检测当前GDS窗口数量"""
        gds_processes = []
        
        for proc in psutil.process_iter(['pid', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info['cmdline']
                if not cmdline:
                    continue
                    
                cmdline_str = ' '.join(cmdline)
                
                # 检测GDS窗口的特征 - 检测WindowManager创建的tkinter窗口
                if ('python' in cmdline_str.lower() and 
                    ('-c' in cmdline_str or 'tkinter' in cmdline_str.lower()) and
                    ('Google Drive Shell' in cmdline_str or 'root.title' in cmdline_str or 'TKINTER_WINDOW' in cmdline_str)):
                    
                    create_time = proc.info['create_time']
                    gds_processes.append({
                        'pid': proc.info['pid'],
                        'create_time': create_time,
                        'cmdline': cmdline_str[:100] + '...' if len(cmdline_str) > 100 else cmdline_str
                    })
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
                
        return gds_processes
    
    def monitor_windows(self):
        """监控窗口变化 - 自动检测失败条件"""
        print("🔍 开始自动监控...")
        start_time = time.time()
        
        while self.monitoring and not self.test_failed:
            try:
                current_windows = self.detect_gds_windows()
                current_count = len(current_windows)
                current_time = time.time()
                
                # 检查15秒内是否有窗口出现，如果没有则结束测试
                if current_time - start_time > 15:
                    if self.first_window_time is None:
                        self.test_failed = True
                        self.failure_reason = "15秒内没有窗口出现（可能死锁）"
                        print(f"Error: 自动失败: {self.failure_reason}")
                    else:
                        # 有窗口出现，15秒后根据窗口个数结束测试
                        print(f"⏰ 15秒测试时间到，根据窗口个数结束测试")
                        print(f"📊 当前窗口个数: {current_count}")
                        self.monitoring = False  # 结束监控
                    break
                
                if current_count != self.window_count:
                    timestamp = time.strftime('%H:%M:%S')
                    print(f"🪟 [{timestamp}] 窗口数量变化: {self.window_count} -> {current_count}")
                    
                    # 记录第一个窗口出现时间
                    if current_count > 0 and self.first_window_time is None:
                        self.first_window_time = current_time
                        print(f"第一个窗口在 {current_time - start_time:.1f}s 时出现")
                    
                    if current_count > self.window_count:
                        for window in current_windows:
                            print(f"   新窗口: PID={window['pid']}, 创建时间={time.strftime('%H:%M:%S', time.localtime(window['create_time']))}")
                    
                    self.window_count = current_count
                    self.window_history.append({
                        'timestamp': current_time,
                        'count': current_count,
                        'windows': current_windows.copy()
                    })
                    
                    # 更新最大并发数
                    if current_count > self.max_concurrent:
                        self.max_concurrent = current_count
                        
                    # 立即检测多窗口失败条件
                    if current_count > 1:
                        self.test_failed = True
                        self.failure_reason = f"检测到 {current_count} 个窗口同时存在（多窗口并发问题）"
                        print(f"Error: 自动失败: {self.failure_reason}")
                        
                        for i, window in enumerate(current_windows):
                            print(f"     窗口{i+1}: PID={window['pid']}, 创建时间={time.strftime('%H:%M:%S.%f', time.localtime(window['create_time']))[:-3]}")
                        break
                
                time.sleep(0.3)  # 更频繁的检测
                
            except Exception as e:
                print(f"Error: 监控出错: {e}")
                self.test_failed = True
                self.failure_reason = f"监控异常: {e}"
                break
    
    def run_test_process(self):
        """运行test_google_drive.py"""
        try:
            print("🧪 启动 test_google_drive.py...")
            
            # 启动测试进程
            self.test_process = subprocess.Popen(
                ['python', '_UNITTEST/test_google_drive.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd='/Users/wukunhuan/.local/bin'
            )
            
            print(f"📋 测试进程已启动 (PID: {self.test_process.pid})")
            
            # 等待测试完成或失败检测
            start_time = time.time()
            while self.monitoring and not self.test_failed:
                if self.test_process.poll() is not None:
                    # 进程已结束
                    stdout, stderr = self.test_process.communicate()
                    
                    print("测试进程完成")
                    print(f"   退出码: {self.test_process.returncode}")
                    
                    if stdout:
                        output = stdout.decode()
                        print(f"   输出: {output[:200]}{'...' if len(output) > 200 else ''}")
                    
                    if stderr:
                        error = stderr.decode()
                        print(f"   错误: {error[:200]}{'...' if len(error) > 200 else ''}")
                    
                    break
                
                # 检查是否超过最大测试时间（2分钟）
                if time.time() - start_time > 120:
                    print("⏰ 测试超时 (2分钟)")
                    self.test_process.kill()
                    break
                
                time.sleep(1)
                
            return True
                
        except Exception as e:
            print(f"Error: 启动测试失败: {e}")
            self.test_failed = True
            self.failure_reason = f"测试启动异常: {e}"
            return False
    
    def analyze_debug_logs(self):
        """分析调试日志"""
        print("\\n📊 分析调试日志...")
        
        debug_file = 'GOOGLE_DRIVE_DATA/force_debug.log'
        if os.path.exists(debug_file):
            with open(debug_file, 'r') as f:
                content = f.read()
            
            execute_shell_calls = content.count('execute_shell_command CALLED')
            execute_generic_calls = content.count('execute_command_interface CALLED')
            queue_inits = content.count('queue_manager initialized')
            slot_acquired_direct = content.count('Slot acquired directly')
            slot_acquired_after_waiting = content.count('Slot acquired after waiting')
            slot_acquired_false = content.count('Slot acquired result: False')
            queue_waiting = content.count('waiting in queue')
            slot_busy = content.count('SLOT_BUSY')
            
            print(f"📋 调试统计:")
            print(f"   execute_shell_command调用: {execute_shell_calls}")
            print(f"   execute_generic_command调用: {execute_generic_calls}")
            print(f"   队列管理器初始化: {queue_inits}")
            print(f"   直接获得槽位: {slot_acquired_direct}")
            print(f"   等待后获得槽位: {slot_acquired_after_waiting}")
            print(f"   槽位请求被拒绝: {slot_acquired_false}")
            print(f"   进入等待队列: {queue_waiting}")
            print(f"   槽位忙碌: {slot_busy}")
            
            # 分析队列工作状态
            if slot_acquired_after_waiting > 0 or queue_waiting > 0 or slot_busy > 0:
                print("   队列控制正常工作 - 有命令被阻塞或等待")
                return True
            else:
                print("   Warning: 队列控制可能失效 - 所有命令都直接获得槽位")
                return False
        else:
            print("   Error: 调试日志文件不存在")
            return False
    
    def test_single_window_control(self):
        """测试单窗口控制机制"""
        print("\\n🎯 GDS单窗口控制测试")
        print("=" * 60)
        print("📋 测试条件:")
        print("   成功: 15秒内出现1个窗口，整个过程只有1个窗口")
        print("   Error: 失败: 15秒内无窗口 OR 出现第二个窗口")
        print("   🤖 容忍性测试: 假设用户交互时间无限长")
        print("")
        
        # 启动监控线程
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_windows, daemon=True)
        monitor_thread.start()
        
        # 启动测试进程线程
        test_thread = threading.Thread(target=self.run_test_process, daemon=True)
        test_thread.start()
        
        # 等待测试完成或失败
        try:
            while self.monitoring and not self.test_failed:
                time.sleep(0.5)
                
                # 检查线程是否都完成
                if not test_thread.is_alive() and not monitor_thread.is_alive():
                    break
            
        except KeyboardInterrupt:
            print("\\n🚫 用户中断测试")
            self.test_failed = True
            self.failure_reason = "用户中断"
        finally:
            self.monitoring = False
            if hasattr(self, 'test_process') and self.test_process.poll() is None:
                self.test_process.kill()
        
        print("\\n🛑 监控已停止")
        
        # 分析结果
        print("\\n📊 测试结果分析:")
        print("=" * 40)
        
        print(f"🪟 窗口统计:")
        print(f"   最大并发窗口数: {self.max_concurrent}")
        print(f"   窗口变化记录: {len(self.window_history)} 次")
        
        if self.first_window_time:
            print(f"   第一个窗口出现时间: 测试开始后 {self.first_window_time - time.time() + 15:.1f}s")
        
        # 分析调试日志
        queue_working = self.analyze_debug_logs()
        
        # 最终判断
        if self.test_failed:
            print(f"\\nError: 测试失败: {self.failure_reason}")
            self.fail(f"单窗口控制测试失败: {self.failure_reason}")
        elif self.max_concurrent == 0:
            print(f"\\nError: 测试失败: 没有窗口出现")
            self.fail("没有窗口出现，可能存在死锁")
        elif self.max_concurrent == 1:
            print(f"\\n测试通过: 窗口控制正常")
            print("   只有1个窗口出现")
            print("   没有多窗口并发")
            
            if queue_working:
                print("\\n队列系统评估: 正常工作")
                print("   - 有命令被正确阻塞或等待")
                print("   - 队列控制生效")
            else:
                print("\\nWarning: 队列系统评估: 可能未充分测试")
                print("   - 建议检查是否有足够的并发命令测试")
            
            # 测试通过
            self.assertTrue(True, "单窗口控制测试通过")
        else:
            print(f"\\nError: 测试失败: 最大并发窗口数 {self.max_concurrent} > 1")
            self.fail(f"检测到多个窗口并发: {self.max_concurrent} 个窗口")

if __name__ == '__main__':
    # 确保输出不被吞掉
    unittest.main(verbosity=2, buffer=False)
