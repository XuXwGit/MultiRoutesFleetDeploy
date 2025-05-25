import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.algos.base_algo_frame import BaseAlgoFrame
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.entity.scenario import Scenario
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem import DualSubProblem

logger = logging.getLogger(__name__)

class CCG(BaseAlgoFrame):
    """
    列与约束生成算法类
    
    实现列与约束生成算法,用于求解大规模优化问题
    
    主要步骤:
    1. 求解主问题(获取下界)
    2. 求解子问题(获取上界)
    3. 生成新的列和约束
    4. 检查收敛条件
    
    特点:
    1. 通过动态生成列和约束来求解大规模问题
    2. 支持场景生成
    3. 支持上下界更新
    """
    
    def __init__(self, input_data: InputData, param: Parameter):
        """
        初始化列与约束生成算法
        
        Args:
            in_data: 输入数据
            p: 模型参数
        """
        super().__init__()
        self.in_data = input_data
        self.p = param
        
        # 主问题和子问题模型
        self.master_model: Optional[DetermineModel] = None
        self.sub_model: Optional[DualSubProblem] = None
        
        # 场景集合
        self.scenarios: List[Scenario] = []
        
        # 算法参数
        self.max_iterations = DefaultSetting.MAX_ITERATION_NUM
        self.time_limit = DefaultSetting.MAX_ITERATION_TIME
        self.gap_tolerance = DefaultSetting.BOUND_GAP_LIMIT
    
    
    def frame(self):
        """
        执行列与约束生成算法
        
        主要步骤:
        1. 初始化主问题和子问题
        2. 主循环迭代直到收敛:
           a. 求解主问题
           b. 求解子问题
           c. 生成新的列和约束
           d. 检查收敛条件
        3. 输出最终结果
        """
        try:
            # 初始化模型
            start_time = time.time()
            self._initialize_models()
            build_time = time.time() - start_time
            
            # 打印迭代标题
            if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                with open(DefaultSetting.ALGO_LOG_PATH + "ccg.log", "w") as f:
                    self.print_iter_title(f, build_time)
                    self.print_iteration(f, self.lower[0], self.upper[0], 0, 0, 0, "--", 0, "--", 0)
            
            # 主循环
            flag = 0
            while self.upper_bound - self.lower_bound > self.gap_tolerance and flag == 0 and self.iteration < self.max_iterations and (time.time() - start_time) < self.time_limit:
                iteration_start = time.time()
                
                # 如果不是第一次迭代,添加新场景到主问题
                if self.iteration != 0:
                    self.master_model.add_scene(self.scenarios[-1])
                
                # 求解主问题
                master_start = time.time()
                self.master_model.solve_model()
                master_time = time.time() - master_start
                
                # 获取主问题的解
                master_objective = self.master_model.obj_val
                self.set_operation_cost(self.master_model.operation_cost)
                self.set_total_cost(self.master_model.obj_val)
                
                # 检查主问题解是否重复
                if not self._add_solution_pool(self.master_model.get_solution()):
                    logger.info("Master problem solution duplicate")
                    flag = 1
                
                # 更新下界
                if self.master_model.obj_val > self.lower_bound and self.master_model.get_solve_status() == "Optimal":
                    self.set_lower_bound(self.master_model.obj_val)
                
                # 求解子问题
                sub_start = time.time()
                self.sub_model.change_objective_v_vars_coefficients(self.master_model.v_var_value)
                self.sub_model.solve_model()
                sub_time = time.time() - sub_start
                
                # 添加新场景
                if self._add_scenario_pool(self.sub_model.get_scene()):
                    self.scenarios.append(self.sub_model.get_scene())
                else:
                    flag = 1
                
                # 更新上界
                if self.sub_model.obj_val + self.master_model.operation_cost < self.upper_bound and self.sub_model.get_solve_status() == "Optimal":
                    self.set_upper_bound(self.sub_model.obj_val + self.master_model.operation_cost)
                
                # 更新迭代计数
                self.iteration += 1
                self.upper[self.iteration] = self.upper_bound
                self.lower[self.iteration] = self.lower_bound
                self.master_obj[self.iteration] = master_objective
                self.sub_obj[self.iteration] = self.sub_model.obj_val
                
                # 打印迭代信息
                total_time = time.time() - iteration_start
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    with open(DefaultSetting.ALGO_LOG_PATH + "ccg.log", "a") as f:
                        self.print_iteration_with_times(
                            f, self.lower_bound, self.upper_bound,
                            master_time, sub_time, total_time,
                            self.sub_model.get_solve_status_string(),
                            self.sub_model.get_obj_gap(),
                            self.master_model.get_solve_status_string(),
                            self.master_model.get_obj_gap()
                        )
            
            # 设置最终结果
            self.set_total_cost(self.upper_bound)
            self.set_operation_cost(self.master_model.obj_val - self.master_model.eta_value)
            
            # 输出最终结果
            self._output_results()
            
            # 恢复最大需求变化
            self.p.set_maximum_demand_variation(self.max_demand_var)
            
        except Exception as e:
            logger.error(f"Error in CCG: {str(e)}")
            raise
    
    def _initialize_models(self):
        """
        初始化主问题和子问题模型
        """
        # 初始化主问题
        self.master_model = DetermineModel(self.in_data, self.p)
        
        # 初始化子问题
        self.sub_model = DualSubProblem(self.in_data, self.p)
        
        # 初始化场景
        self._initialize_scenarios()
    
    def _initialize_scenarios(self):
        """
        初始化场景集合
        """
        if DefaultSetting.whether_add_initialize_sce:
            # 创建初始场景
            request = [1.0] * self.p.tau  # 初始场景的请求值设为1
            self.scenarios.append(Scenario(request=request))
    
    def _add_solution_pool(self, solution: List[List[int]]) -> bool:
        """
        添加解到解池
        
        Args:
            solution: 主问题的解
            
        Returns:
            bool: 如果解是新的返回True,否则返回False
        """
        # TODO: 实现解池管理
        return True
    
    def _add_scenario_pool(self, scene: Scenario) -> bool:
        """
        添加场景到场景池
        
        Args:
            scene: 子问题生成的场景
            
        Returns:
            bool: 如果场景是新的返回True,否则返回False
        """
        # TODO: 实现场景池管理
        return True

    def solve(self):
        """
        执行列与约束生成算法
        """
        self.logger.info("开始列与约束生成算法求解...")
        try:
            self.frame()
            self.logger.info("列与约束生成算法求解完成")
            return {
                "status": "success",
                "obj": self.obj,
                'objective': self.obj,
                "gap": self.gap,
                "iteration": self.iteration,
                "solve_time": self.solve_time,
                "lower_bound": self.lower_bound,
                "upper_bound": self.upper_bound,
                "total_cost": self.total_cost,
                "operation_cost": self.operation_cost,
                }   
        except Exception as e:
            self.logger.error(f"列与约束生成算法求解失败: {str(e)}")
            raise

    def _output_results(self):
        """
        输出最终结果
        """
        logger.info("\n=== CCG Results ===")
        logger.info(f"Final Objective Value: {self.obj:.2f}")
        logger.info(f"Final Gap: {self.gap:.4f}")
        logger.info(f"Total Iterations: {self.iteration}")
        logger.info(f"Total Time: {self.solve_time:.2f}s")
        logger.info("==================") 