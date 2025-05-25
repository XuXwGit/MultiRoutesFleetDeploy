import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.algos.base_algo_frame import BaseAlgoFrame
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem import DualSubProblem

logger = logging.getLogger(__name__)

class AlgoFrame(BaseAlgoFrame):
    """
    算法框架类
    
    继承自BaseAlgoFrame,实现基本的算法框架
    
    主要功能:
    1. 维护主问题模型和子问题模型
    2. 实现基本的迭代求解流程
    3. 记录求解过程中的各种指标
    4. 提供结果输出功能
    """
    
    def __init__(self):
        """
        初始化算法框架
        """
        super().__init__()
        self.determine_model = None  # 主问题模型
        self.dual_sub_problem = None  # 子问题模型
        
        # 求解状态
        self.solve_status = False  # 是否求解成功
        self.total_time = 0  # 总运行时间
        self.build_model_time = 0  # 模型构建时间
        
        # 成本相关
        self.laden_cost = 0  # 重箱运输成本
        self.empty_cost = 0  # 空箱运输成本
        self.penalty_cost = 0  # 惩罚成本
        self.rental_cost = 0  # 租船成本
    
    def _initialize_models(self):
        """
        初始化模型
        """
        # 初始化主问题模型
        self.determine_model = DetermineModel(self.in_data, self.p)
        self.determine_model.build_model()
        
        # 初始化子问题模型
        self.dual_sub_problem = DualSubProblem(self.in_data, self.p)
        self.dual_sub_problem.build_model()
    
    def frame(self):
        """
        执行算法框架
        
        主要步骤:
        1. 初始化模型
        2. 主循环迭代直到收敛:
           a. 求解主问题(获取上界)
           b. 求解子问题(获取下界)
           c. 检查收敛条件
           d. 更新割平面
        3. 输出最终结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 初始化模型
            model_start_time = time.time()
            self._initialize_models()
            self.build_model_time = time.time() - model_start_time
            
            # 打开日志文件
            file_writer = None
            if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                file_writer = open(DefaultSetting.log_file_path, 'w')
            
            # 打印迭代标题
            self.print_iter_title(file_writer, self.build_model_time)
            
            # 主循环
            while self.iteration < DefaultSetting.MAX_ITERATION_NUM:
                # 求解主问题
                mp_start_time = time.time()
                self.determine_model.solve_model()
                mp_time = time.time() - mp_start_time
                
                # 获取主问题解
                self.upper_bound = self.determine_model.obj_val
                self.upper[self.iteration] = self.upper_bound
                
                # 求解子问题
                sp_start_time = time.time()
                self.dual_sub_problem.solve_model()
                sp_time = time.time() - sp_start_time
                
                # 获取子问题解
                self.lower_bound = self.dual_sub_problem.obj_val
                self.lower[self.iteration] = self.lower_bound
                
                # 计算总时间
                self.total_time = time.time() - start_time
                
                # 打印迭代信息
                self.print_iteration_detailed(file_writer, self.lower_bound, self.upper_bound,
                                           mp_time, sp_time, self.total_time)
                
                # 检查收敛
                if self._check_convergence():
                    self.solve_status = True
                    break
                
                # 更新迭代次数
                self.iteration += 1
            
            # 获取最终结果
            self._get_final_results()
            
            # 输出结果
            self._output_results()
            
            # 关闭日志文件
            if file_writer:
                file_writer.close()
            
        except Exception as e:
            logger.error(f"Algorithm execution failed: {str(e)}")
            self.solve_status = False
    
    def _check_convergence(self) -> bool:
        """
        检查是否收敛
        
        Returns:
            bool: 是否收敛
        """
        # 计算间隙
        self.gap = abs(self.upper_bound - self.lower_bound) / (abs(self.lower_bound) + 1e-10)
        
        # 检查收敛条件
        if self.gap <= DefaultSetting.gap_tolerance:
            return True
        
        return False
    
    def _get_final_results(self):
        """
        获取最终结果
        """
        # 获取目标函数值
        self.obj = self.determine_model.obj_val
        
        # 获取各种成本
        self.laden_cost = self.determine_model.laden_cost
        self.empty_cost = self.determine_model.empty_cost
        self.penalty_cost = self.determine_model.penalty_cost
        self.rental_cost = self.determine_model.rental_cost
    
    def _output_results(self):
        """
        输出结果
        """
        logger.info("Algorithm execution completed")
        logger.info(f"Solve status: {'Success' if self.solve_status else 'Failed'}")
        logger.info(f"Total time: {self.total_time:.2f}s")
        logger.info(f"Build model time: {self.build_model_time:.2f}s")
        logger.info(f"Final gap: {self.gap:.4f}")
        logger.info(f"Final objective value: {self.obj:.2f}")
        logger.info(f"Laden cost: {self.laden_cost:.2f}")
        logger.info(f"Empty cost: {self.empty_cost:.2f}")
        logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
        logger.info(f"Rental cost: {self.rental_cost:.2f}") 