#!/usr/bin/env python3
"""
测试 MinerU 是否能正确使用本地模型
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

def test_model_path_resolution():
    """测试模型路径解析"""
    print("=== 测试模型路径解析 ===")
    
    try:
        from mineru.utils.models_download_utils import auto_download_and_get_model_root_path
        from mineru.utils.enum_class import ModelPath
        
        print(f"MINERU_MODEL_SOURCE: {os.environ.get('MINERU_MODEL_SOURCE')}")
        print(f"UnimerNet 模型路径: {ModelPath.unimernet_small}")
        
        # 测试路径解析
        model_root = auto_download_and_get_model_root_path(ModelPath.unimernet_small, repo_mode='pipeline')
        print(f"解析的模型根路径: {model_root}")
        
        # 构建完整路径
        full_model_path = os.path.join(model_root, ModelPath.unimernet_small)
        print(f"完整模型路径: {full_model_path}")
        
        # 检查路径是否存在
        if os.path.exists(full_model_path):
            print("✅ 模型路径存在")
            
            # 列出文件
            files = os.listdir(full_model_path)
            print(f"模型文件: {files}")
            
            # 检查必要文件
            required_files = ['config.json', 'pytorch_model.pth', 'tokenizer.json', 'tokenizer_config.json']
            missing_files = [f for f in required_files if f not in files]
            
            if not missing_files:
                print("✅ 所有必要文件都存在")
                return True
            else:
                print(f"❌ 缺少文件: {missing_files}")
                return False
        else:
            print(f"❌ 模型路径不存在: {full_model_path}")
            return False
            
    except Exception as e:
        print(f"❌ 路径解析失败: {e}")
        traceback.print_exc()
        return False

def test_model_loading():
    """测试模型加载"""
    print("\n=== 测试模型加载 ===")
    
    try:
        from mineru.backend.pipeline.model_init import mfr_model_init
        from mineru.utils.models_download_utils import auto_download_and_get_model_root_path
        from mineru.utils.enum_class import ModelPath
        
        # 获取模型路径
        model_root = auto_download_and_get_model_root_path(ModelPath.unimernet_small, repo_mode='pipeline')
        weight_dir = os.path.join(model_root, ModelPath.unimernet_small)
        
        print(f"尝试加载模型从: {weight_dir}")
        
        # 初始化模型
        model = mfr_model_init(weight_dir, device='cpu')
        print(f"✅ 模型加载成功: {type(model)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        traceback.print_exc()
        return False

def test_config_file():
    """测试配置文件"""
    print("\n=== 测试配置文件 ===")
    
    try:
        from mineru.utils.config_reader import read_config, get_local_models_dir
        
        config = read_config()
        if config:
            print("✅ 配置文件读取成功")
            print(f"配置内容: {config}")
            
            models_dir = get_local_models_dir()
            print(f"本地模型目录配置: {models_dir}")
            
            return True
        else:
            print("❌ 配置文件读取失败")
            return False
            
    except Exception as e:
        print(f"❌ 配置文件测试失败: {e}")
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("MinerU 本地模型测试")
    print("=" * 50)
    
    # 测试配置文件
    config_ok = test_config_file()
    
    # 测试路径解析
    path_ok = test_model_path_resolution()
    
    # 测试模型加载
    model_ok = test_model_loading()
    
    print("\n" + "=" * 50)
    print("测试结果总结:")
    print(f"配置文件: {'✅' if config_ok else '❌'}")
    print(f"路径解析: {'✅' if path_ok else '❌'}")
    print(f"模型加载: {'✅' if model_ok else '❌'}")
    
    if config_ok and path_ok and model_ok:
        print("\n🎉 所有测试通过！MinerU 可以正确使用本地模型。")
        return True
    else:
        print("\n❌ 部分测试失败，需要修复配置。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 