from pathlib import Path
import sys
import streamlit as st
import time
from typing import Dict, Any, Callable
import threading
import json
import logging

# 配置日志
logging.basicConfig(
    filename='optimizer_execution.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('optimizer_executor')

class OptimizerExecutor:
    """优化执行器，负责后台运行优化任务"""
    
    def __init__(self):
        self.thread = None
        self.stop_event = threading.Event()
        self.current_progress = 0
        self.result = None
    
    def is_running(self) -> bool:
        """检查优化器是否正在运行"""
        return self.thread is not None and self.thread.is_alive()
    
    def start_optimization(self, optimizer_func: Callable, config: Dict[str, Any]):
        """
        启动优化任务
        
        Args:
            optimizer_func: 优化函数
            config: 优化配置
        """
        if self.is_running():
            return False
            
        self.stop_event.clear()
        self.current_progress = 0
        self.result = None
        
        # 创建并启动线程
        self.thread = threading.Thread(
            target=self._run_optimization,
            args=(optimizer_func, config)
        )
        self.thread.daemon = True
        self.thread.start()
        return True
    
    def _run_optimization(self, optimizer_func: Callable, config: Dict[str, Any]):
        """运行优化任务的内部方法"""
        try:
            # 添加调试信息
            logger.info("==== OptimizerExecutor开始执行优化 ====")
            logger.info(f"优化器函数: {optimizer_func.__name__ if hasattr(optimizer_func, '__name__') else optimizer_func}")
            logger.info(f"配置内容: 算法={config.get('algorithm', '未指定')}, 最大迭代={config.get('max_iterations', '未指定')}")
            
            # 调用优化函数
            logger.info("即将调用优化服务...")
            # 为确保OptimizationService是一个实例而非类，尝试初始化它
            if hasattr(optimizer_func, '__call__') and not isinstance(optimizer_func, type):
                # 如果是可调用对象但不是类，直接调用
                result = optimizer_func(config, self._progress_callback)
            else:
                # 如果是类，先创建实例
                optimizer_instance = optimizer_func()
                logger.info(f"创建了优化服务实例: {type(optimizer_instance)}")
                result = optimizer_instance(config, self._progress_callback)
                
            logger.info("优化服务调用完成")
            
            # 检查结果
            if result is None:
                logger.error("优化结果为None，可能是优化过程中出现错误")
                self.result = {
                    'error': '优化结果为空',
                    'routes': [],
                    'total_cost': 0
                }
            else:
                logger.info(f"结果类型: {type(result)}")
                if isinstance(result, dict):
                    logger.info(f"结果键值: {result.keys()}")
                self.result = result
            
            # 更新会话状态
            if 'optimization_result' not in st.session_state:
                st.session_state.optimization_result = {}
                
            st.session_state.optimization_result = self.result
            st.session_state.optimization_status = 'completed'
            
            # 将结果保存到JSON文件
            try:
                # 将DesignSolution对象转换为可序列化的字典
                if 'design_solution' in self.result and self.result['design_solution'] is not None:
                    self.result['design_solution'] = self.result['design_solution'].to_dict()
                
                with open("optimization_result.json", "w", encoding="utf-8") as f:
                    json.dump(self.result, f, ensure_ascii=False, indent=4)
                logger.info("成功保存结果到文件")
            except Exception as e:
                logger.error(f"保存结果文件失败: {str(e)}")
            
        except Exception as e:
            logger.error(f"优化执行出错: {str(e)}")
            import traceback
            error_tb = traceback.format_exc()
            logger.error(error_tb)
            
            st.session_state.optimization_error = str(e)
            st.session_state.optimization_status = 'failed'
            
            # 创建错误结果
            self.result = {
                'error': str(e),
                'traceback': error_tb,
                'routes': [],
                'total_cost': 0
            }
        finally:
            # 确保最终进度为100%
            self.current_progress = 100
            logger.info(f"优化任务结束，最终结果: {self.result is not None}")
    
    def _progress_callback(self, progress: float) -> bool:
        """
        进度回调函数
        
        Args:
            progress: 进度百分比(0-100)
            
        Returns:
            如果应该停止，返回True
        """
        self.current_progress = progress
        
        # 每10%进度记录一次日志
        if int(progress) % 10 == 0:
            logger.info(f"优化进度: {progress:.1f}%")
        
        # 检查是否应该停止
        return self.stop_event.is_set()
    
    def stop_optimization(self):
        """停止优化任务"""
        if not self.is_running():
            return False
            
        self.stop_event.set()
        self.thread.join(timeout=1.0)  # 等待线程结束
        
        if self.thread.is_alive():
            st.warning("优化任务无法立即停止，正在后台继续")
            
        st.session_state.optimization_status = 'ready'
        return True
    
    def get_progress(self) -> float:
        """获取当前进度"""
        return self.current_progress