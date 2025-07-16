#!/usr/bin/env python3
"""
直接测试UnimerNet模型的tokenizer加载问题
"""
import sys
import os
import traceback
from pathlib import Path

# 添加MinerU路径
sys.path.insert(0, str(Path(__file__).parent.parent / "pdf_extractor_MinerU"))

def test_tokenizer_loading_direct():
    """直接测试tokenizer加载"""
    print("=== 直接测试UnimerNet Tokenizer加载 ===")
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from transformers import AutoTokenizer
        
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

def test_unimernet_model_direct():
    """直接测试UnimerNet模型加载"""
    print("\n=== 直接测试UnimerNet模型加载 ===")
    
    # 使用本地模型路径
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        from mineru.model.mfr.unimernet.unimernet_hf.modeling_unimernet import UnimernetModel
        
        print(f"尝试加载UnimerNet模型...")
        
        # 首先测试配置加载
        from transformers import VisionEncoderDecoderConfig
        config = VisionEncoderDecoderConfig.from_pretrained(model_path)
        config._name_or_path = model_path
        print(f"✅ 配置加载成功!")
        
        # 使用from_checkpoint方法加载模型
        model = UnimernetModel.from_checkpoint(model_path, "pytorch_model.pth")
        print(f"✅ UnimerNet模型加载成功!")
        print(f"模型类型: {type(model)}")
        
        # 测试tokenizer
        print(f"Tokenizer类型: {type(model.tokenizer)}")
        print(f"Transform类型: {type(model.transform)}")
        
        return True
        
    except Exception as e:
        print(f"❌ UnimerNet模型加载失败: {e}")
        print(f"错误类型: {type(e)}")
        traceback.print_exc()
        return False

def test_tokenizer_config():
    """测试tokenizer配置文件"""
    print("\n=== 检查Tokenizer配置 ===")
    
    model_path = str(Path(__file__).parent.parent / "math_formula_test" / "models" / "unimernet_base")
    
    try:
        import json
        
        # 读取tokenizer配置
        tokenizer_config_path = os.path.join(model_path, "tokenizer_config.json")
        if os.path.exists(tokenizer_config_path):
            with open(tokenizer_config_path, 'r') as f:
                config = json.load(f)
            print(f"Tokenizer配置:")
            for key, value in config.items():
                print(f"  {key}: {value}")
                
        # 读取模型配置
        model_config_path = os.path.join(model_path, "config.json")
        if os.path.exists(model_config_path):
            with open(model_config_path, 'r') as f:
                config = json.load(f)
            print(f"\n模型配置关键信息:")
            for key in ['model_type', 'architectures', 'decoder', 'encoder']:
                if key in config:
                    print(f"  {key}: {config[key]}")
                    
        return True
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("UnimerNet 直接测试工具")
    print("=" * 50)
    
    # 检查tokenizer配置
    test_tokenizer_config()
    
    # 测试tokenizer加载
    test_tokenizer_loading_direct()
    
    # 测试完整模型加载
    test_unimernet_model_direct() 