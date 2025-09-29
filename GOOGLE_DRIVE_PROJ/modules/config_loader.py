#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 统一管理所有常量和配置
提高系统维护性，避免硬编码
"""

import json
import os
from pathlib import Path
from typing import Dict, Any


class ConfigLoader:
    """配置加载器单例类"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            # 获取配置文件路径
            current_dir = Path(__file__).parent.parent.parent
            config_file = current_dir / "GOOGLE_DRIVE_DATA" / "config.json"
            
            if not config_file.exists():
                raise FileNotFoundError(f"Config file not found: {config_file}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)

        except Exception:
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置（当配置文件加载失败时使用）"""
        return {
            "constants": {
                "HOME_URL": "https://drive.google.com/drive/u/0/my-drive",
                "HOME_FOLDER_ID": "root",
                "REMOTE_ROOT_FOLDER_ID": "1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f",
                "REMOTE_ROOT": "/content/drive/MyDrive/REMOTE_ROOT"
            },
            "queue_settings": {
                "timeout_hours": 2,
                "heartbeat_interval": 0.1,
                "heartbeat_check_interval": 0.5,
                "lock_timeout": 10,
                "heartbeat_failure_threshold": 2
            },
            "file_paths": {
                "remote_window_queue_file": "remote_window_queue.json",
                "remote_window_queue_lock": "remote_window_queue.lock",
                "debug_log_dir": "../tmp"
            }
        }
    
    def get(self, key_path: str, default=None):
        """
        获取配置值，支持点号分隔的路径
        
        Args:
            key_path: 配置键路径，如 'constants.HOME_URL' 或 'queue_settings.timeout_hours'
            default: 默认值
            
        Returns:
            配置值
        """
        try:
            keys = key_path.split('.')
            value = self._config
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def get_constants(self) -> Dict[str, str]:
        """获取所有常量"""
        return self.get('constants', {})
    
    def get_queue_settings(self) -> Dict[str, Any]:
        """获取队列设置"""
        return self.get('queue_settings', {})
    
    def get_file_paths(self) -> Dict[str, str]:
        """获取文件路径配置"""
        return self.get('file_paths', {})
    
    # 便捷属性访问
    @property
    def HOME_URL(self) -> str:
        return self.get('constants.HOME_URL', 'https://drive.google.com/drive/u/0/my-drive')
    
    @property
    def HOME_FOLDER_ID(self) -> str:
        return self.get('constants.HOME_FOLDER_ID', 'root')
    
    @property
    def REMOTE_ROOT_FOLDER_ID(self) -> str:
        return self.get('constants.REMOTE_ROOT_FOLDER_ID', '1LSndouoVj8pkoyi-yTYnC4Uv03I77T8f')
    
    @property
    def REMOTE_ROOT(self) -> str:
        return self.get('constants.REMOTE_ROOT', '/content/drive/MyDrive/REMOTE_ROOT')
    
    @property
    def timeout_hours(self) -> float:
        return self.get('queue_settings.timeout_hours', 2)
    
    @property
    def heartbeat_interval(self) -> float:
        return self.get('queue_settings.heartbeat_interval', 0.1)
    
    @property
    def heartbeat_check_interval(self) -> float:
        return self.get('queue_settings.heartbeat_check_interval', 0.5)
    
    @property
    def lock_timeout(self) -> int:
        return self.get('queue_settings.lock_timeout', 10)
    
    @property
    def heartbeat_failure_threshold(self) -> int:
        return self.get('queue_settings.heartbeat_failure_threshold', 2)


# 全局配置实例
_config_loader = None

def get_config() -> ConfigLoader:
    """获取配置加载器单例"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


# 便捷函数
def get_constant(name: str, default=None):
    """获取常量值"""
    return get_config().get(f'constants.{name}', default)


def get_queue_setting(name: str, default=None):
    """获取队列设置值"""
    return get_config().get(f'queue_settings.{name}', default)


def get_file_path(name: str, default=None):
    """获取文件路径配置"""
    return get_config().get(f'file_paths.{name}', default)
