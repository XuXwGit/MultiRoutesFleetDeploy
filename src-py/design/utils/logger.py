"""
统一的日志管理模块
提供全局日志配置、日志捕获和前端显示功能
"""

import logging
import logging.handlers
import os
import sys
import streamlit as st
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 获取项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 创建日志目录
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
DEFAULT_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
SIMPLE_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
FILE_FORMAT = '%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s'

class LogManager:
    """日志管理器类：统一管理所有日志配置和处理"""
    
    _instance = None  # 单例模式
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(LogManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化日志管理器"""
        if self._initialized:
            return
            
        self.root_logger = logging.getLogger()
        self.loggers: Dict[str, logging.Logger] = {}
        
        # 设置根日志级别
        self.root_logger.setLevel(logging.DEBUG)
        
        # 创建控制台处理器
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))
        self.console_handler.setLevel(logging.INFO)
        
        # 创建文件处理器
        self.file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "app.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        self.file_handler.setFormatter(logging.Formatter(FILE_FORMAT))
        self.file_handler.setLevel(logging.DEBUG)
        
        # 移除已存在的处理器，避免重复
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)
            
        # 添加处理器到根日志记录器
        self.root_logger.addHandler(self.console_handler)
        self.root_logger.addHandler(self.file_handler)
        
        # 设置标记为已初始化
        self._initialized = True
        
        # 标记是否已添加Streamlit处理器
        self.streamlit_handler_added = False
        
        # 记录初始化日志
        self.root_logger.info("="*50)
        self.root_logger.info("日志系统初始化完成")
        self.root_logger.info("="*50)
    
    def setup_streamlit_handler(self):
        """设置Streamlit会话状态日志处理器"""
        if self.streamlit_handler_added:
            return
            
        # 确保session_state中有日志消息列表
        if 'log_messages' not in st.session_state:
            st.session_state.log_messages = []
            
        # 创建Streamlit处理器类
        class StreamlitHandler(logging.Handler):
            def emit(self, record):
                # 只有启用日志或严重日志才记录
                if not st.session_state.get('log_enabled', False) and record.levelno < logging.WARNING:
                    return
                    
                # 格式化日志
                log_entry = self.format(record)
                
                # 限制日志数量
                if len(st.session_state.log_messages) > 1000:
                    st.session_state.log_messages = st.session_state.log_messages[-900:]
                    
                # 添加到会话状态
                st.session_state.log_messages.append(log_entry)
                
        # 创建并配置Streamlit处理器
        streamlit_handler = StreamlitHandler()
        streamlit_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))
        streamlit_handler.setLevel(logging.DEBUG)
        
        # 添加到根日志记录器
        self.root_logger.addHandler(streamlit_handler)
        self.streamlit_handler_added = True
        
        # 记录Streamlit日志处理器添加完成
        self.root_logger.info("Streamlit日志处理器已配置")
    
    def get_logger(self, name: str) -> logging.Logger:
        """获取指定名称的日志记录器
        
        Args:
            name: 日志记录器名称
            
        Returns:
            对应名称的日志记录器
        """
        if name in self.loggers:
            return self.loggers[name]
            
        logger = logging.getLogger(name)
        self.loggers[name] = logger
        return logger
    
    def set_log_level(self, level: int):
        """设置日志级别
        
        Args:
            level: 日志级别 (logging.DEBUG, logging.INFO 等)
        """
        self.root_logger.setLevel(level)
        self.root_logger.info(f"日志级别已设置为: {logging.getLevelName(level)}")
    
    def enable_module_logging(self, module_name: str, level: int = logging.DEBUG):
        """为特定模块启用详细日志
        
        Args:
            module_name: 模块名称
            level: 日志级别
        """
        logging.getLogger(module_name).setLevel(level)

# 创建全局日志管理器实例
log_manager = LogManager()

def get_logger(name: str) -> logging.Logger:
    """获取指定名称的日志记录器的简便函数
    
    Args:
        name: 日志记录器名称
        
    Returns:
        配置好的日志记录器
    """
    return log_manager.get_logger(name)

def setup_streamlit_logging():
    """设置Streamlit日志处理"""
    log_manager.setup_streamlit_handler()

def set_log_level(level_name: str):
    """根据级别名称设置日志级别
    
    Args:
        level_name: 级别名称，如 'DEBUG', 'INFO' 等
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    if level_name in level_map:
        log_manager.set_log_level(level_map[level_name]) 