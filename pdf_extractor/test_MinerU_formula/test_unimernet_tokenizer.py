#!/usr/bin/env python3
"""
测试UnimerNet模型的tokenizer加载问题
"""
import sys
import os
import traceback
from pathlib import Path

# 添加MinerU路径
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

def test_tokenizer_loading():
    """测试tokenizer加载"""
    print("=== 测试UnimerNet Tokenizer加载 ===")
    
    try:
        from transformers import AutoTokenizer
        from mineru.utils.enum_class import ModelPath
        from mineru.utils.models_download_utils import auto_download_and_get_model_root_path
        
        # 获取模型路径
        model_root_path = auto_download_and_get_model_root_path(ModelPath.unimernet_small)
        model_path = os.path.join(model_root_path, ModelPath.unimernet_small)
        
        print(f"模型路径: {model_path}")
        
        # 检查模型文件是否存在
        if not os.path.exists(model_path):
            print(f"❌ 模型路径不存在: {model_path}")
            return False
            
        # 列出模型目录内容
        print(f"模型目录内容:")
        for item in os.listdir(model_path):
            print(f"  - {item}")
            
        # 尝试加载tokenizer
        print("\n尝试加载tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        print(f"✅ Tokenizer加载成功!")
        print(f"Tokenizer类型: {type(tokenizer)}")
        print(f"Vocab大小: {len(tokenizer)}")
        print(f"特殊token: bos={tokenizer.bos_token}, eos={tokenizer.eos_token}, pad={tokenizer.pad_token}")
        
        return True
        
    except Exception as e:
        print(f"❌ Tokenizer加载失败: {e}")
        print(f"错误类型: {type(e)}")
        traceback.print_exc()
        return False

def test_unimernet_model_loading():
    """测试完整的UnimerNet模型加载"""
    print("\n=== 测试完整UnimerNet模型加载 ===")
    
    try:
        from mineru.model.mfr.unimernet.Unimernet import UnimernetModel
        from mineru.utils.enum_class import ModelPath
        from mineru.utils.models_download_utils import auto_download_and_get_model_root_path
        
        # 获取模型路径
        model_root_path = auto_download_and_get_model_root_path(ModelPath.unimernet_small)
        model_path = os.path.join(model_root_path, ModelPath.unimernet_small)
        
        print(f"尝试加载UnimerNet模型...")
        model = UnimernetModel(model_path, "cpu")
        print(f"✅ UnimerNet模型加载成功!")
        print(f"模型设备: {model.device}")
        
        return True
        
    except Exception as e:
        print(f"❌ UnimerNet模型加载失败: {e}")
        print(f"错误类型: {type(e)}")
        traceback.print_exc()
        return False

def check_model_files():
    """检查模型文件结构"""
    print("\n=== 检查模型文件结构 ===")
    
    try:
        from mineru.utils.enum_class import ModelPath
        from mineru.utils.models_download_utils import auto_download_and_get_model_root_path
        
        model_root_path = auto_download_and_get_model_root_path(ModelPath.unimernet_small)
        model_path = os.path.join(model_root_path, ModelPath.unimernet_small)
        
        print(f"模型根目录: {model_root_path}")
        print(f"模型完整路径: {model_path}")
        
        if not os.path.exists(model_path):
            print(f"❌ 模型路径不存在")
            return False
            
        # 递归显示目录结构
        def show_tree(path, prefix="", max_depth=3, current_depth=0):
            if current_depth > max_depth:
                return
                
            items = sorted(os.listdir(path))
            for i, item in enumerate(items):
                item_path = os.path.join(path, item)
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                print(f"{prefix}{current_prefix}{item}")
                
                if os.path.isdir(item_path) and current_depth < max_depth:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    show_tree(item_path, next_prefix, max_depth, current_depth + 1)
        
        show_tree(model_path)
        
        # 检查关键文件
        key_files = ['config.json', 'tokenizer.json', 'tokenizer_config.json', 'pytorch_model.pth']
        print(f"\n关键文件检查:")
        for file in key_files:
            file_path = os.path.join(model_path, file)
            exists = os.path.exists(file_path)
            print(f"  {file}: {'✅' if exists else '❌'}")
            
        return True
        
    except Exception as e:
        print(f"❌ 文件检查失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("UnimerNet Tokenizer 问题诊断工具")
    print("=" * 50)
    
    # 检查模型文件
    check_model_files()
    
    # 测试tokenizer加载
    test_tokenizer_loading()
    
    # 测试完整模型加载
    test_unimernet_model_loading() 