import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.model.primal.master_problem import MasterProblem
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem import DualSubProblem
from multi.algos.benders_lazy_cons_callback import BendersLazyConsCallback
from multi.algos.algo_frame import AlgoFrame
from multi.entity.scenario import Scenario
from multi.utils.logger_config import setup_logger
from multi.model.primal.base_primal_model import BasePrimalModel
from multi.model.dual.base_dual_model import BaseDualModel

logger = logging.getLogger(__name__)


class BendersDecomposition(AlgoFrame):
    """
    Benders分解算法类
    
    继承自AlgoFrame,实现Benders分解算法
    
    主要步骤:
    1. 初始化主问题模型和子问题模型
    2. 主循环迭代直到收敛:
       a. 求解主问题(获取上界)
       b. 求解子问题(获取下界)
       c. 生成Benders割
       d. 检查收敛条件
    3. 输出最终结果
    """
    
    def __init__(self, input_data: InputData, param: Parameter):
        """
        初始化Benders分解算法
        
        Args:
            input_data: 输入数据
            p: 模型参数
        """
        super().__init__()
        self.logger = setup_logger('benders_decomposition')
        self.input_data = input_data
        self.p = param
        self.in_data = input_data
        self.callback = None  # Benders回调

        self.primal_model = BasePrimalModel(input_data, param)
        self.dual_model = BaseDualModel(input_data, param)

        logger.info(f"BendersDecomposition初始化完成")
    
    def _initialize_models(self):
        """
        初始化模型
        """
        # 初始化主问题模型
        self.mp = MasterProblem(self.in_data, self.p, type="Robust")
        
        # 初始化子问题模型
        self.dsp = DualSubProblem(input_data=self.in_data, param=self.p, tau=DefaultSetting.ROBUSTNESS)
        
    
    def frame(self):
        """
        执行Benders分解算法
        
        主要步骤:
        1. 初始化模型
        2. 主循环迭代直到收敛:
           a. 求解主问题(获取上界)
           b. 求解子问题(获取下界)
           c. 生成Benders割
           d. 检查收敛条件
        3. 输出最终结果
        """
        try:
            self.initialize();
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
            flag = 0
            while  self.upper_bound - self.lower_bound > DefaultSetting.BOUND_GAP_LIMIT\
                    and flag == 0 \
                    and self.iteration < DefaultSetting.MAX_ITERATION_NUM \
                    and time.time() - start_time < DefaultSetting.MAX_ITERATION_TIME :
                # 求解主问题
                mp_start_time = time.time()
                self.mp.solve_model()
                mp_time = time.time() - mp_start_time
                
                # check if the mp-solution changed
                if not self.add_solution_pool(self.mp.solution):
                    flag=1;

                # // LB = max{LB , MP.Objective}
                # // LB = MP.Objective = MP.OperationCost + Eta
                if self.mp.obj_val > self.lower_bound and self.mp.get_solve_status_string == "Optimal":
                    self.lower_bound = self.mp.obj_val
                
                # 求解子问题
                self.dsp.change_objective_v_vars_coefficients(self.mp.get_v_vars())
                sp_start_time = time.time()
                self.dsp.solve_model()
                sp_time = time.time() - sp_start_time
                
                # 获取子问题解
                self.lower_bound = self.dsp.obj_val
                self.lower[self.iteration] = self.lower_bound

                if not self.update_bound_and_mp():
                    flag = 3

                # 更新迭代次数
                self.iteration += 1
                self.upper.append(self.upper_bound)
                self.lower.append(self.lower_bound)

                # 计算总时间
                self.total_time = time.time() - start_time
                # 打印迭代信息
                self.print_iteration_detailed(file_writer, 
                                              self.lower_bound, 
                                              self.upper_bound,
                                              mp_time, 
                                              sp_time, 
                                              total_time=self.total_time)

            # // end the loop
            if flag == 1:
                logger.info("MP solution duplicate")
            elif flag == 2:
                logger.info("Worse case duplicate")
            elif flag == 3:
                logger.info("DSP solution infeasible")


            # 获取最终结果
            self._set_algo_results()
            
            # 输出结果
            self._output_results()
            
            # 关闭日志文件
            if file_writer:
                file_writer.close()
            
        except Exception as e:
            self.logger.error(f"Benders decomposition failed: {str(e)}", exc_info=True)
            self.solve_status = False
    
    
    def _set_algo_results(self):
        """
        获取最终结果
        """
        self.solve_time = time.time() - self.start
        # 获取目标函数值
        self.obj = self.upper_bound

        self.iter = self.iteration
        self.v_value = self.mp.v_var_value
        self.gap = (self.upper_bound - self.lower_bound)/self.lower_bound
        self.solution = self.mp.solution
        
        # 获取各种成本
        self.laden_cost = self.mp.laden_cost
        self.empty_cost = self.mp.empty_cost
        self.penalty_cost = self.mp.penalty_cost
        self.rental_cost = self.mp.rental_cost

        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            self.write_solution(self.mp.v_var_value, self.file_writer) 

        if DefaultSetting.WHETHER_PRINT_PROCESS:
            self.print_solution(self.v_value)

        if DefaultSetting.WHETHER_CALCULATE_MEAN_PERFORMANCE:
            self.calculate_mean_performance()
    
    def _output_results(self):
        """
        输出结果
        """
        self.logger.info("Benders decomposition completed")
        self.logger.info(f"Solve status: {'Success' if self.solve_status else 'Failed'}")
        self.logger.info(f"Total time: {self.total_time:.2f}s")
        self.logger.info(f"Build model time: {self.build_model_time:.2f}s")
        self.logger.info(f"Final gap: {self.gap:.4f}")
        self.logger.info(f"Final objective value: {self.obj:.2f}")
        self.logger.info(f"Laden cost: {self.laden_cost:.2f}")
        self.logger.info(f"Empty cost: {self.empty_cost:.2f}")
        self.logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
        self.logger.info(f"Rental cost: {self.rental_cost:.2f}")

    def solve(self):
        """执行Benders分解算法求解
        
        Returns:
            dict: 求解结果，包含状态、目标值等信息
        """
        self.logger.info("开始Benders分解算法求解...")
        try:
            # 使用frame方法执行算法
            self.frame()
            
            # 返回结果
            return {
                'status': 'success',

                'objective': self.obj,
                'time': self.total_time,
                'laden_cost': self.laden_cost,
                'empty_cost': self.empty_cost,
                'rental_cost': self.rental_cost,
                'penalty_cost': self.penalty_cost,
                'iterations': self.iteration,
                'gap': self.gap
            }
            
        except Exception as e:
            self.logger.error(f"Benders分解算法求解失败: {str(e)}", exc_info=True)
            raise 