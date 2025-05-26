import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting

logger = logging.getLogger(__name__)

class BaseAlgoFrame:
    """
    算法框架基类
    
    定义算法执行的通用框架和流程
    
    主要功能:
    1. 维护上下界(upperBound/lowerBound)
    2. 记录迭代过程(upper/lower数组)
    3. 提供算法执行的基本框架(frame方法)
    4. 记录算法性能指标(gap/obj/solveTime等)
    
    子类需要实现具体的算法逻辑
    """
    
    def __init__(self, input_data: InputData, param: Parameter):
        """
        初始化算法框架基类
        """
        self.input_data: InputData = input_data  # 输入数据
        self.param: Parameter = param  # 模型参数
        self.gap: float = 0  # 间隙
        self.obj: float = 0  # 目标函数值
        self.solve_time: float = 0  # 求解时间
        self.iter: int = 0  # 迭代次数
        self.iteration: int = 0  # 当前迭代次数
        
        # 记录上下界历史
        self.upper = [0] * (DefaultSetting.MAX_ITERATION_NUM + 1)
        self.lower = [0] * (DefaultSetting.MAX_ITERATION_NUM + 1)
        
        # 当前上下界
        self.upper_bound = float('inf')
        self.lower_bound = float('-inf')
    
    def frame(self):
        """
        算法框架主方法
        
        定义算法的基本执行流程:
        1. 初始化算法参数
        2. 主循环迭代直到收敛:
           a. 求解主问题(获取上界)
           b. 求解子问题(获取下界)
           c. 检查收敛条件
           d. 更新割平面(如Benders分解)
        3. 输出最终结果
        
        子类需要实现具体的算法逻辑
        """
        pass
    
    def print_iter_title(self, file_writer, build_model_time: float):
        """
        打印迭代标题
        
        Args:
            file_writer: 文件写入器
            build_model_time: 模型构建时间
        """
        if DefaultSetting.whether_print_process or DefaultSetting.whether_print_iteration:
            logger.info(f"BuildModelTime = {build_model_time:.2f}")
            logger.info("k\t\tLB\t\tUB\t\tTotal Time")
        
        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            file_writer.write("k\t\tLB\t\tUB\t\tTotal Time(s)\n")
            file_writer.flush()
    
    def print_iteration(self, file_writer, lb: float, ub: float, total_time: float):
        """
        打印迭代信息
        
        Args:
            file_writer: 文件写入器
            lb: 下界
            ub: 上界
            total_time: 总运行时间
        """
        if DefaultSetting.whether_print_process or DefaultSetting.whether_print_iteration:
            logger.info(f"{self.iteration}\t\t{lb:.2f}\t\t{ub:.2f}\t\t{total_time:.2f}")
        
        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            file_writer.write(f"{self.iteration}\t\t{lb:.2f}\t\t{ub:.2f}\t\t{total_time:.2f}\n")
            file_writer.flush()
    
    def print_iteration_detailed(self, file_writer, lb: float, ub: float, mp_time: float, 
                               sp_time: float, total_time: float):
        """
        打印详细迭代信息
        
        Args:
            file_writer: 文件写入器
            lb: 下界
            ub: 上界
            mp_time: 主问题求解时间
            sp_time: 子问题求解时间
            total_time: 总运行时间
        """
        if DefaultSetting.whether_print_process or DefaultSetting.whether_print_iteration:
            logger.info(f"{self.iteration}\t\t{lb:.2f}\t\t{ub:.2f}\t\t{mp_time:.2f}\t\t{sp_time:.2f}\t\t{total_time:.2f}")
        
        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            file_writer.write(f"{self.iteration}\t\t{lb:.2f}\t\t{ub:.2f}\t\t{mp_time:.2f}\t\t{sp_time:.2f}\t\t{total_time:.2f}\n")
            file_writer.flush()
    
    @property
    def obj_val(self) -> float:
        """
        获取目标函数值
        
        Returns:
            目标函数值
        """
        return self.obj 
    

    @property
    def in_data(self) -> InputData:
        """
        获取输入数据
        """
        return self.input_data
    
    @property
    def p(self) -> Parameter:
        """
        获取模型参数
        """
        return self.param
