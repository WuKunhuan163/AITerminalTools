#!/usr/bin/env python3
"""
简单的 UnimerNet 模型测试，避免复杂的依赖
"""
import os
import sys
import traceback
from pathlib import Path

# 设置环境变量使用本地模型
os.environ['MINERU_MODEL_SOURCE'] = 'local'

# 添加 MinerU 路径
project_root = Path(__file__).parent.parent.parent
mineru_path = project_root / "pdf_extractor/pdf_extractor_MinerU"
sys.path.insert(0, str(mineru_path))

def test_direct_unimernet_loading():
    """直接测试 UnimerNet 模型加载"""
    print("=== 直接测试 UnimerNet 模型加载 ===")
    
    try:
        from mineru.model.mfr.unimernet.Unimernet import UnimernetModel
        
        # 使用我们设置的本地模型路径
        model_path = "/Users/wukunhuan/.local/bin/pdf_extractor/models/MFR/unimernet_hf_small_2503"
        
        print(f"尝试加载模型从: {model_path}")
        
        # 检查路径是否存在
        if not os.path.exists(model_path):
            print(f"❌ 模型路径不存在: {model_path}")
            return False
        
        # 列出文件
        files = os.listdir(model_path)
        print(f"模型文件: {files}")
        
        # 初始化模型
        model = UnimernetModel(model_path, _device_="cpu")
        print(f"✅ UnimerNet 模型加载成功: {type(model)}")
        
        return True
        
    except Exception as e:
        print(f"❌ UnimerNet 模型加载失败: {e}")
        traceback.print_exc()
        return False

def test_config_and_path():
    """测试配置和路径解析（简化版）"""
    print("\n=== 测试配置和路径解析 ===")
    
    try:
        from mineru.utils.config_reader import read_config, get_local_models_dir
        
        config = read_config()
        if config:
            print("✅ 配置文件读取成功")
            
            models_dir = get_local_models_dir()
            print(f"本地模型目录配置: {models_dir}")
            
            if models_dir and 'pipeline' in models_dir:
                pipeline_dir = models_dir['pipeline']
                print(f"Pipeline 模型目录: {pipeline_dir}")
                
                # 检查 UnimerNet 路径
                unimernet_path = os.path.join(pipeline_dir, "models/MFR/unimernet_hf_small_2503")
                print(f"UnimerNet 完整路径: {unimernet_path}")
                
                if os.path.exists(unimernet_path):
                    print("✅ UnimerNet 模型路径存在")
                    return True
                else:
                    print("❌ UnimerNet 模型路径不存在")
                    return False
            else:
                print("❌ Pipeline 模型目录配置错误")
                return False
        else:
            print("❌ 配置文件读取失败")
            return False
            
    except Exception as e:
        print(f"❌ 配置测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("简单 UnimerNet 模型测试")
    print("=" * 50)
    
    # 测试配置
    config_ok = test_config_and_path()
    
    # 测试直接模型加载
    model_ok = test_direct_unimernet_loading()
    
    print("\n" + "=" * 50)
    print("测试结果总结:")
    print(f"配置和路径: {'✅' if config_ok else '❌'}")
    print(f"模型加载: {'✅' if model_ok else '❌'}")
    
    if config_ok and model_ok:
        print("\n🎉 UnimerNet 模型配置成功！")
        return True
    else:
        print("\n❌ 需要修复配置。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 