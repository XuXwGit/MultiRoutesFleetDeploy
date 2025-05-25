import logging
import time
from typing import List, Dict, Any, Tuple

import numpy as np
from multi.model.dual.dual_problem import DualProblem
from multi.model.dual.dual_sub_problem import DualSubProblem
from multi.model.dual.dual_sub_problem_reactive import DualSubProblemReactive
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.algos.algo_frame import AlgoFrame

logger = logging.getLogger(__name__)

class BDwithPareto(AlgoFrame):
    """带有Pareto最优的Benders分解算法类
    
    实现了带有Pareto最优的Benders分解算法:
    1. 主问题求解
    2. 子问题求解
    3. Pareto最优切割生成
    4. 收敛性检查
    """
    
    def __init__(self, in_data: InputData, param: Parameter):
        """初始化Benders分解算法
        
        Args:
            in_data: 输入数据
            param: 模型参数
        """
        super().__init__()
        self.in_data = in_data
        self.param = param
        
        # 对偶问题
        self.dual_problem = DualProblem(in_data, param)
        
        # 反应式对偶子问题
        self.reactive_sub_problem = DualSubProblemReactive(in_data, param)
        
        # 迭代参数
        self.iter_params = {
            'max_iter': DefaultSetting.MaxIterations,
            'tol': DefaultSetting.ConvergenceTolerance,
            'step_size': DefaultSetting.InitialStepSize
        }
        
        # 求解状态
        self.solve_status = {
            'iter': 0,
            'obj_val': 0.0,
            'gap': float('inf'),
            'time': 0.0
        }
        
        # Pareto最优切割
        self.pareto_cuts = []
        
        # 历史信息
        self.history = {
            'obj_val': [],
            'gap': [],
            'time': []
        }
        
    def _initialize_models(self):
        """初始化模型"""
        # 初始化对偶问题
        self.dual_problem.build_variables()
        self.dual_problem.build_constraints()
        self.dual_problem.build_objective()
        
        # 初始化反应式对偶子问题
        self.reactive_sub_problem.build_variables()
        self.reactive_sub_problem.build_constraints()
        self.reactive_sub_problem.build_objective()
        
    def frame(self):
        """执行Benders分解算法"""
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
                self.solve_master_problem()
                mp_time = time.time() - mp_start_time
                
                # 获取主问题解
                self.upper_bound = self.master_objective
                self.upper[self.iteration] = self.upper_bound
                
                # 求解子问题
                sp_start_time = time.time()
                self.solve_sub_problem()
                sp_time = time.time() - sp_start_time
                
                # 获取子问题解
                self.lower_bound = self.sub_objective
                self.lower[self.iteration] = self.lower_bound
                
                # 生成Pareto最优切割
                self.generate_pareto_cuts()
                
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
            self._set_algo_results()
            
            # 输出结果
            self._output_results()
            
            # 关闭日志文件
            if file_writer:
                file_writer.close()
            
        except Exception as e:
            logger.error(f"Benders decomposition failed: {str(e)}")
            self.solve_status = False
            
    def solve_master_problem(self):
        """求解主问题"""
        try:
            # 构建主问题
            self.build_master_problem()
            
            # 求解主问题
            self.optimize_master_problem()
            
            # 获取主问题解
            self.get_master_solution()
            
        except Exception as e:
            logger.error(f"Error in solving master problem: {str(e)}")
            raise
            
    def solve_sub_problem(self):
        """求解子问题"""
        try:
            # 构建子问题
            self.build_sub_problem()
            
            # 求解子问题
            self.optimize_sub_problem()
            
            # 获取子问题解
            self.get_sub_solution()
            
        except Exception as e:
            logger.error(f"Error in solving sub problem: {str(e)}")
            raise
            
    def generate_pareto_cuts(self):
        """生成Pareto最优切割"""
        try:
            # 计算对偶解
            dual_solution = self.calculate_dual_solution()
            
            # 生成Pareto最优切割
            pareto_cut = self.generate_pareto_cut(dual_solution)
            
            # 添加切割
            self.pareto_cuts.append(pareto_cut)
            
        except Exception as e:
            logger.error(f"Error in generating Pareto cuts: {str(e)}")
            raise
            
    def calculate_dual_solution(self) -> Dict[str, np.ndarray]:
        """计算对偶解
        
        Returns:
            Dict[str, np.ndarray]: 对偶解
        """
        # 求解对偶问题
        self.dual_problem.optimize()
        
        # 获取对偶变量
        dual_variables = self.dual_problem.get_dual_variables()
        
        return dual_variables
        
    def generate_pareto_cut(self, dual_solution: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """生成Pareto最优切割
        
        Args:
            dual_solution: 对偶解
            
        Returns:
            Dict[str, Any]: Pareto最优切割
        """
        # 计算切割系数
        coefficients = self.calculate_cut_coefficients(dual_solution)
        
        # 计算右端项
        rhs = self.calculate_cut_rhs(dual_solution)
        
        # 构建切割
        cut = {
            'coefficients': coefficients,
            'rhs': rhs
        }
        
        return cut
        
    def calculate_cut_coefficients(self, dual_solution: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """计算切割系数
        
        Args:
            dual_solution: 对偶解
            
        Returns:
            Dict[str, np.ndarray]: 切割系数
        """
        coefficients = {}
        
        # 路径选择系数
        coefficients['x'] = dual_solution['lambda'] + dual_solution['xi']
        
        # 船舶分配系数
        coefficients['y'] = dual_solution['nu'] + dual_solution['eta']
        
        # 需求满足系数
        coefficients['z'] = dual_solution['mu']
        
        return coefficients
        
    def calculate_cut_rhs(self, dual_solution: Dict[str, np.ndarray]) -> float:
        """计算切割右端项
        
        Args:
            dual_solution: 对偶解
            
        Returns:
            float: 右端项
        """
        # 计算常数项
        constant_term = self.calculate_constant_term(dual_solution)
        
        # 计算对偶项
        dual_term = self.calculate_dual_term(dual_solution)
        
        return constant_term + dual_term
        
    def calculate_constant_term(self, dual_solution: Dict[str, np.ndarray]) -> float:
        """计算常数项
        
        Args:
            dual_solution: 对偶解
            
        Returns:
            float: 常数项
        """
        # 容量约束项
        capacity_term = np.sum(
            dual_solution['lambda'] * self.param.vessel_capacity
        )
        
        # 需求约束项
        demand_term = np.sum(
            dual_solution['mu'] * self.param.demand
        )
        
        # 时间约束项
        time_term = np.sum(
            dual_solution['nu'] * self.param.turnover_time
        )
        
        # 路径约束项
        path_term = np.sum(
            dual_solution['xi'] * self.param.travel_time_on_path
        )
        
        # 船舶约束项
        vessel_term = np.sum(
            dual_solution['eta'] * self.param.vessel_operation_cost
        )
        
        return (
            capacity_term +
            demand_term +
            time_term +
            path_term +
            vessel_term
        )
        
    def calculate_dual_term(self, dual_solution: Dict[str, np.ndarray]) -> float:
        """计算对偶项
        
        Args:
            dual_solution: 对偶解
            
        Returns:
            float: 对偶项
        """
        # 路径选择项
        path_term = np.sum(
            dual_solution['lambda'] * self.master_problem['x'] +
            dual_solution['xi'] * self.master_problem['x']
        )
        
        # 船舶分配项
        vessel_term = np.sum(
            dual_solution['nu'] * self.master_problem['y'] +
            dual_solution['eta'] * self.master_problem['y']
        )
        
        # 需求满足项
        demand_term = np.sum(
            dual_solution['mu'] * self.master_problem['z']
        )
        
        return path_term + vessel_term + demand_term
        
    def _check_convergence(self) -> bool:
        """检查收敛性
        
        Returns:
            bool: 是否收敛
        """
        # 计算目标函数变化
        objective_change = abs(
            self.solve_status['obj_val'] - self.previous_objective
        )
        
        # 检查是否收敛
        if objective_change < self.iter_params['tol']:
            return True
        else:
            self.previous_objective = self.solve_status['obj_val']
            return False
            
    def update_iteration_info(self):
        """更新迭代信息"""
        # 更新迭代次数
        self.solve_status['iter'] += 1
        
        # 更新目标函数值
        self.solve_status['obj_val'] = self.master_objective
        
        # 更新对偶间隙
        self.solve_status['gap'] = abs(
            self.master_objective - self.sub_objective
        ) / abs(self.master_objective)
        
        # 更新求解时间
        self.solve_status['time'] = self.calculate_solve_time()
        
        # 更新历史信息
        self.update_history()
        
    def update_history(self):
        """更新历史信息"""
        # 更新目标函数值历史
        self.history['obj_val'].append(self.solve_status['obj_val'])
        
        # 更新对偶间隙历史
        self.history['gap'].append(self.solve_status['gap'])
        
        # 更新求解时间历史
        self.history['time'].append(self.solve_status['time'])
        
    def calculate_solve_time(self) -> float:
        """计算求解时间
        
        Returns:
            float: 求解时间
        """
        # 获取当前时间
        current_time = self.get_current_time()
        
        # 计算求解时间
        solve_time = current_time - self.start_time
        
        return solve_time
        
    def get_current_time(self) -> float:
        """获取当前时间
        
        Returns:
            float: 当前时间
        """
        import time
        return time.time()
        
    def _set_algo_results(self):
        """获取最终结果"""
        # 获取目标函数值
        self.obj = self.master_objective
        
        # 获取各种成本
        self.laden_cost = self.calculate_laden_cost()
        self.empty_cost = self.calculate_empty_cost()
        self.penalty_cost = self.calculate_penalty_cost()
        self.rental_cost = self.calculate_rental_cost()
        
    def _output_results(self):
        """输出结果"""
        logger.info("Benders decomposition with Pareto cuts completed")
        logger.info(f"Solve status: {'Success' if self.solve_status else 'Failed'}")
        logger.info(f"Total time: {self.total_time:.2f}s")
        logger.info(f"Build model time: {self.build_model_time:.2f}s")
        logger.info(f"Final gap: {self.gap:.4f}")
        logger.info(f"Final objective value: {self.obj:.2f}")
        logger.info(f"Laden cost: {self.laden_cost:.2f}")
        logger.info(f"Empty cost: {self.empty_cost:.2f}")
        logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
        logger.info(f"Rental cost: {self.rental_cost:.2f}") 