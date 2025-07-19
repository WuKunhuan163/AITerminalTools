#!/usr/bin/env python3
"""
MinerU Configuration Module for UNIMERNET
Extracted and adapted from MinerU for better model configuration
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

try:
    import torch
    import torch_npu
except ImportError:
    torch_npu = None

class ModelPath:
    """Model path configurations compatible with MinerU"""
    # HuggingFace repositories
    vlm_root_hf = "opendatalab/MinerU2.0-2505-0.9B"
    pipeline_root_hf = "opendatalab/PDF-Extract-Kit-1.0"
    
    # ModelScope repositories
    vlm_root_modelscope = "OpenDataLab/MinerU2.0-2505-0.9B"
    pipeline_root_modelscope = "OpenDataLab/PDF-Extract-Kit-1.0"
    
    # Model relative paths
    doclayout_yolo = "models/Layout/YOLO/doclayout_yolo_docstructbench_imgsz1280_2501.pt"
    yolo_v8_mfd = "models/MFD/YOLO/yolo_v8_ft.pt"
    unimernet_small = "models/MFR/unimernet_hf_small_2503"
    pytorch_paddle = "models/OCR/paddleocr_torch"
    layout_reader = "models/ReadingOrder/layout_reader"
    slanet_plus = "models/TabRec/SlanetPlus/slanet-plus.onnx"

class ConfigReader:
    """Configuration reader for UNIMERNET with MinerU compatibility"""
    
    @staticmethod
    def get_config_file_path() -> Path:
        """Get configuration file path"""
        config_name = os.getenv('MINERU_TOOLS_CONFIG_JSON', 'mineru.json')
        if os.path.isabs(config_name):
            return Path(config_name)
        else:
            return Path.home() / config_name
    
    @staticmethod
    def read_config() -> Optional[Dict[str, Any]]:
        """Read configuration from mineru.json"""
        config_file = ConfigReader.get_config_file_path()
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.warning(f"Failed to read config file {config_file}: {e}")
            return None
    
    @staticmethod
    def get_device() -> str:
        """
        Get optimal device for model execution.
        Priority: Environment variable > CUDA > MPS > NPU > CPU
        """
        device_mode = os.getenv('MINERU_DEVICE_MODE', None)
        if device_mode is not None:
            return device_mode
        
        # Check CUDA availability
        if torch.cuda.is_available():
            return "cuda"
        
        # Check MPS (Apple Silicon) availability
        if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
        
        # Check NPU availability
        if torch_npu is not None:
            try:
                if torch_npu.npu.is_available():
                    return "npu"
            except Exception:
                pass
        
        return "cpu"
    
    @staticmethod
    def get_local_models_dir() -> Optional[Dict[str, str]]:
        """Get local models directory configuration"""
        config = ConfigReader.read_config()
        if config is None:
            return None
        
        models_dir = config.get('models-dir')
        if models_dir is None:
            logger.warning("'models-dir' not found in config, using default paths")
        
        return models_dir
    
    @staticmethod
    def get_formula_enable(default: bool = True) -> bool:
        """Get formula processing enable flag"""
        formula_enable_env = os.getenv('MINERU_FORMULA_ENABLE')
        return default if formula_enable_env is None else formula_enable_env.lower() == 'true'
    
    @staticmethod
    def get_table_enable(default: bool = True) -> bool:
        """Get table processing enable flag"""
        table_enable_env = os.getenv('MINERU_TABLE_ENABLE')
        return default if table_enable_env is None else table_enable_env.lower() == 'true'

class ModelDownloader:
    """Model download utilities compatible with MinerU"""
    
    @staticmethod
    def auto_download_and_get_model_root_path(relative_path: str, repo_mode: str = 'pipeline') -> str:
        """
        Download model and get root path.
        
        Args:
            relative_path: Relative path to model
            repo_mode: Repository mode ('pipeline' or 'vlm')
            
        Returns:
            Local model root path
        """
        model_source = os.getenv('MINERU_MODEL_SOURCE', "huggingface")
        
        # Check for local models first
        if model_source == 'local':
            local_models_config = ConfigReader.get_local_models_dir()
            if local_models_config:
                root_path = local_models_config.get(repo_mode, None)
                if root_path:
                    return root_path
        
        # Repository mapping
        repo_mapping = {
            'pipeline': {
                'huggingface': ModelPath.pipeline_root_hf,
                'modelscope': ModelPath.pipeline_root_modelscope,
                'default': ModelPath.pipeline_root_hf
            },
            'vlm': {
                'huggingface': ModelPath.vlm_root_hf,
                'modelscope': ModelPath.vlm_root_modelscope,
                'default': ModelPath.vlm_root_hf
            }
        }
        
        if repo_mode not in repo_mapping:
            raise ValueError(f"Unsupported repo_mode: {repo_mode}, must be 'pipeline' or 'vlm'")
        
        repo = repo_mapping[repo_mode].get(model_source, repo_mapping[repo_mode]['default'])
        
        # Try to download using huggingface_hub or modelscope
        try:
            if model_source == "huggingface":
                from huggingface_hub import snapshot_download
                cache_dir = snapshot_download(repo, allow_patterns=[relative_path, relative_path+"/*"])
            elif model_source == "modelscope":
                from modelscope import snapshot_download
                cache_dir = snapshot_download(repo, allow_patterns=[relative_path, relative_path+"/*"])
            else:
                raise ValueError(f"Unknown model source: {model_source}")
            
            return cache_dir
        except ImportError as e:
            logger.warning(f"Failed to import download library: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to download model: {relative_path} from {repo}: {e}")
            raise

class UnimerNetConfig:
    """UNIMERNET specific configuration"""
    
    def __init__(self):
        self.device = ConfigReader.get_device()
        self.formula_enable = ConfigReader.get_formula_enable()
        self.table_enable = ConfigReader.get_table_enable()
        self.local_models_dir = ConfigReader.get_local_models_dir()
        
        logger.info(f"UnimerNet Config initialized:")
        logger.info(f"  Device: {self.device}")
        logger.info(f"  Formula enabled: {self.formula_enable}")
        logger.info(f"  Table enabled: {self.table_enable}")
        logger.info(f"  Local models dir: {self.local_models_dir}")
    
    def get_model_path(self, model_name: str = "unimernet_small") -> str:
        """
        Get model path for UnimerNet.
        
        Args:
            model_name: Name of the model to get path for
            
        Returns:
            Path to the model
        """
        # Check if using local models
        if self.local_models_dir:
            pipeline_dir = self.local_models_dir.get('pipeline')
            if pipeline_dir:
                model_path = os.path.join(pipeline_dir, getattr(ModelPath, model_name))
                if os.path.exists(model_path):
                    return model_path
        
        # Use current project's model path as fallback
        current_dir = Path(__file__).parent
        local_model_path = current_dir / "unimernet_models" / "unimernet_base"
        if local_model_path.exists():
            return str(local_model_path)
        
        # Try to download from remote
        try:
            relative_path = getattr(ModelPath, model_name)
            return ModelDownloader.auto_download_and_get_model_root_path(relative_path)
        except Exception as e:
            logger.error(f"Failed to get model path for {model_name}: {e}")
            raise
    
    def get_attention_implementation(self) -> str:
        """Get appropriate attention implementation for the device"""
        if self.device.startswith("mps") or self.device.startswith("npu"):
            return "eager"
        return "sdpa"  # Default for CUDA and CPU
    
    def get_model_dtype(self):
        """Get appropriate model dtype for the device"""
        if self.device.startswith("cpu"):
            return torch.float32
        else:
            return torch.float16
    
    def should_use_float16(self) -> bool:
        """Check if float16 should be used for the current device"""
        return not self.device.startswith("cpu")

# Global configuration instance
config = UnimerNetConfig() 