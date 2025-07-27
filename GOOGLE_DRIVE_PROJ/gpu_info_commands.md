#!/usr/bin/env python3
"""
GPU和系统资源信息获取命令
用于Google Drive远程环境的资源监控
"""

# 1. 基础CUDA和PyTorch信息
cuda_basic_info = """
import torch
import sys
print("="*50)
print("CUDA 基础信息")
print("="*50)
print(f"Python版本: {sys.version}")
print(f"PyTorch版本: {torch.__version__}")  
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA版本: {torch.version.cuda}")
    print(f"GPU数量: {torch.cuda.device_count()}")
    for i in range(torch.cuda.device_count()):
        print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"  显存总量: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
        print(f"  多处理器数量: {torch.cuda.get_device_properties(i).multi_processor_count}")
        print(f"  计算能力: {torch.cuda.get_device_properties(i).major}.{torch.cuda.get_device_properties(i).minor}")
"""

# 2. 详细的GPU内存和使用情况
gpu_memory_info = """
import torch
import gc
print("="*50) 
print("GPU 内存使用情况")
print("="*50)
if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"\\nGPU {i} ({torch.cuda.get_device_name(i)}):")
        # 清理缓存以获得准确的内存信息
        torch.cuda.empty_cache()
        gc.collect()
        
        memory_allocated = torch.cuda.memory_allocated(i)
        memory_reserved = torch.cuda.memory_reserved(i)
        max_memory_allocated = torch.cuda.max_memory_allocated(i)
        max_memory_reserved = torch.cuda.max_memory_reserved(i)
        total_memory = torch.cuda.get_device_properties(i).total_memory
        
        print(f"  当前已分配内存: {memory_allocated / 1024**3:.2f} GB")
        print(f"  当前预留内存: {memory_reserved / 1024**3:.2f} GB") 
        print(f"  峰值分配内存: {max_memory_allocated / 1024**3:.2f} GB")
        print(f"  峰值预留内存: {max_memory_reserved / 1024**3:.2f} GB")
        print(f"  总内存: {total_memory / 1024**3:.2f} GB")
        print(f"  可用内存: {(total_memory - memory_reserved) / 1024**3:.2f} GB")
        print(f"  内存使用率: {(memory_reserved / total_memory) * 100:.1f}%")
        
        # 获取GPU利用率 (需要nvidia-ml-py)
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # 转换为瓦特
            print(f"  GPU利用率: {util.gpu}%")
            print(f"  显存利用率: {util.memory}%") 
            print(f"  温度: {temp}°C")
            print(f"  功耗: {power:.1f}W")
        except ImportError:
            print("  (pynvml未安装，无法获取GPU利用率信息)")
        except Exception as e:
            print(f"  (获取GPU利用率失败: {e})")
else:
    print("CUDA不可用")
"""

# 3. 系统资源信息
system_info = """
import psutil
import platform
import os
import shutil
print("="*50)
print("系统资源信息") 
print("="*50)
print(f"操作系统: {platform.system()} {platform.release()}")
print(f"架构: {platform.machine()}")
print(f"处理器: {platform.processor()}")
print(f"CPU核心数: {psutil.cpu_count(logical=False)} 物理核心, {psutil.cpu_count(logical=True)} 逻辑核心")

# CPU使用率
cpu_percent = psutil.cpu_percent(interval=1)
print(f"CPU使用率: {cpu_percent}%")

# 内存信息
memory = psutil.virtual_memory()
print(f"\\n内存信息:")
print(f"  总内存: {memory.total / 1024**3:.2f} GB")
print(f"  可用内存: {memory.available / 1024**3:.2f} GB")
print(f"  已使用内存: {memory.used / 1024**3:.2f} GB")
print(f"  内存使用率: {memory.percent}%")

# 磁盘信息
disk = psutil.disk_usage('/')
print(f"\\n磁盘信息 (根目录):")
print(f"  总空间: {disk.total / 1024**3:.2f} GB")
print(f"  可用空间: {disk.free / 1024**3:.2f} GB") 
print(f"  已使用空间: {disk.used / 1024**3:.2f} GB")
print(f"  磁盘使用率: {(disk.used / disk.total) * 100:.1f}%")

# 当前工作目录和用户信息
print(f"\\n环境信息:")
print(f"  当前用户: {os.getenv('USER', 'unknown')}")
print(f"  当前目录: {os.getcwd()}")
print(f"  HOME目录: {os.path.expanduser('~')}")

# 检查重要工具是否可用
print(f"\\n工具可用性:")
tools = ['nvidia-smi', 'nvcc', 'git', 'wget', 'curl']
for tool in tools:
    if shutil.which(tool):
        print(f"  ✅ {tool}: 可用")
    else:
        print(f"  ❌ {tool}: 不可用")
"""

# 4. nvidia-smi信息 (如果可用)
nvidia_smi_info = """
import subprocess
import sys
print("="*50)
print("NVIDIA-SMI 信息")
print("="*50)
try:
    result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print("nvidia-smi 执行失败:")
        print(result.stderr)
except FileNotFoundError:
    print("nvidia-smi 命令未找到")
except subprocess.TimeoutExpired:
    print("nvidia-smi 执行超时")
except Exception as e:
    print(f"执行nvidia-smi时出错: {e}")
"""

# 5. 完整的综合信息命令
comprehensive_info = f"""
{cuda_basic_info}

{gpu_memory_info}

{system_info}

{nvidia_smi_info}
"""

if __name__ == "__main__":
    print("GPU和系统信息获取命令已准备好")
    print("可以使用以下代码块分别获取不同类型的信息：")
    print("\n1. CUDA基础信息:")
    print("python -c \"" + cuda_basic_info.replace('"', '\\"').replace('\n', '\\n') + "\"")
    print("\n2. GPU内存信息:")  
    print("python -c \"" + gpu_memory_info.replace('"', '\\"').replace('\n', '\\n') + "\"")
    print("\n3. 系统资源信息:")
    print("python -c \"" + system_info.replace('"', '\\"').replace('\n', '\\n') + "\"")
    print("\n4. NVIDIA-SMI信息:")
    print("python -c \"" + nvidia_smi_info.replace('"', '\\"').replace('\n', '\\n') + "\"") 