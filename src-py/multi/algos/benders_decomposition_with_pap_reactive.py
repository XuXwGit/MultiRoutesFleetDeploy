import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.network import Port, Node, Arc, VesselPath, Request, ShipRoute, ContainerPath, VesselType, ODRange
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem_reactive import DualSubProblemReactive
from multi.algos.benders_lazy_cons_callback_reactive import BendersLazyConsCallbackReactive

logger = logging.getLogger(__name__)

class BendersDecompositionWithPAP_Reactive:
    """
    带有价格调整问题的Benders分解算法的反应式版本
    
    用于求解带有不确定需求的船舶调度问题,包括:
    1. 主问题求解
    2. 反应式对偶子问题求解
    3. 价格调整问题求解
    4. 反应式Benders切割生成
    5. 收敛检查
    
    主要步骤:
    1. 初始化模型
    2. 求解主问题
    3. 求解反应式对偶子问题
    4. 求解价格调整问题
    5. 生成反应式Benders切割
    6. 检查收敛条件
    7. 输出结果
    """
    
    def __init__(self, input_data: InputData, p: Parameter):
        """
        初始化带有价格调整问题的反应式Benders分解算法
        
        Args:
            input_data: 输入数据
            p: 模型参数
        """
        self.input_data = input_data
        self.p = p
        self.determine_model = None  # 主问题模型
        self.dual_sub_problem_reactive = None  # 反应式对偶子问题模型
        self.callback = None  # 反应式惰性约束回调
        self.obj_val = 0  # 目标函数值
        self.mip_gap = 0  # MIP间隙
        self.solve_status = ""  # 求解状态
        self.iteration = 0  # 迭代次数
        self.total_time = 0  # 总运行时间
        self.laden_cost = 0  # 重箱运输成本
        self.empty_cost = 0  # 空箱运输成本
        self.penalty_cost = 0  # 需求未满足惩罚成本
        self.rental_cost = 0  # 集装箱租赁成本
        self.v_var_value3 = None  # 第三组船舶分配方案
    
    def _initialize_models(self):
        """
        初始化模型
        """
        # 初始化主问题模型
        self.determine_model = DetermineModel(self.input_data, self.p)
        self.determine_model.build_model()
        
        # 初始化反应式对偶子问题模型
        self.dual_sub_problem_reactive = DualSubProblemReactive(self.input_data, self.p, self.p.tau)
        self.dual_sub_problem_reactive.build_model()
        
        # 初始化反应式惰性约束回调
        self.callback = BendersLazyConsCallbackReactive(self.input_data, self.p)
        self.callback.set_models(self.determine_model, self.dual_sub_problem_reactive)
    
    def frame(self):
        """
        执行带有价格调整问题的反应式Benders分解算法
        """
        try:
            # 初始化模型
            self._initialize_models()
            
            # 初始化迭代参数
            self.iteration = 0
            start_time = time.time()
            
            # 主循环
            while self.iteration < self.p.max_iteration:
                # 求解主问题
                self.determine_model.solve_reactive_model()
                
                # 获取主问题解
                v_value1 = self.determine_model.v_var_value
                v_value2 = self.determine_model.v_var_value2
                
                # 求解反应式对偶子问题
                self.dual_sub_problem_reactive.change_objective_v_coefficients(v_value1, v_value2)
                self.dual_sub_problem_reactive.solve_model()
                
                # 求解价格调整问题
                self._solve_price_adjustment_problem()
                
                # 生成反应式Benders切割
                self.callback.callback()
                
                # 检查收敛条件
                if self._check_convergence():
                    break
                
                # 更新迭代参数
                self.iteration += 1
            
            # 计算总运行时间
            self.total_time = time.time() - start_time
            
            # 获取最终结果
            self._get_final_results()
            
            # 输出结果
            self._output_results()
            
        except Exception as e:
            logger.error(f"Error in executing reactive Benders decomposition with PAP: {str(e)}")
            raise
    
    def _solve_price_adjustment_problem(self):
        """
        求解价格调整问题
        """
        try:
            # 获取子问题解
            alpha_value = self.dual_sub_problem_reactive.get_alpha_value()
            beta1_value = self.dual_sub_problem_reactive.get_beta1_value()
            beta2_value = self.dual_sub_problem_reactive.get_beta2_value()
            gamma_value = self.dual_sub_problem_reactive.get_gamma_value()
            lambda_value = self.dual_sub_problem_reactive.get_lambda_value()
            
            # 计算第三组船舶分配方案
            self.v_var_value3 = self._calculate_third_vessel_allocation(
                alpha_value, beta1_value, beta2_value, gamma_value, lambda_value
            )
            
            # 更新主问题的第三组船舶分配方案
            self.determine_model.set_v_value3(self.v_var_value3)
            
        except Exception as e:
            logger.error(f"Error in solving price adjustment problem: {str(e)}")
            raise
    
    def _calculate_third_vessel_allocation(self, alpha_value: List[float], beta1_value: List[float],
                                         beta2_value: List[float], gamma_value: List[List[float]],
                                         lambda_value: List[float]) -> List[List[int]]:
        """
        计算第三组船舶分配方案
        
        Args:
            alpha_value: alpha变量值
            beta1_value: beta1变量值
            beta2_value: beta2变量值
            gamma_value: gamma变量值
            lambda_value: lambda变量值
            
        Returns:
            第三组船舶分配方案
        """
        # 初始化第三组船舶分配方案
        v_value3 = [[0 for _ in range(self.input_data.route_num)] for _ in range(self.input_data.vessel_num)]
        
        # 计算每个航线的收益
        route_profits = []
        for j in range(self.input_data.route_num):
            route = self.input_data.ship_routes[j]
            profit = 0
            
            # 添加航段收益(第一组)
            for arc in route.arcs:
                arc_idx = self.input_data.arcs.index(arc)
                profit += beta1_value[arc_idx]
            
            # 添加航段收益(第二组)
            for arc in route.arcs:
                arc_idx = self.input_data.arcs.index(arc)
                profit += beta2_value[arc_idx]
            
            # 添加港口收益
            for port in route.ports:
                port_idx = self.input_data.ports.index(port)
                for t in range(1, self.input_data.time_horizon + 1):
                    profit += gamma_value[port_idx][t]
            
            route_profits.append((j, profit))
        
        # 按收益排序
        route_profits.sort(key=lambda x: x[1], reverse=True)
        
        # 分配船舶
        for i in range(self.input_data.vessel_num):
            vessel = self.input_data.vessel_types[i]
            assigned = False
            
            # 尝试分配收益最高的航线
            for j, _ in route_profits:
                if not assigned and self._is_route_feasible(i, j):
                    v_value3[i][j] = 1
                    assigned = True
                    break
        
        return v_value3
    
    def _is_route_feasible(self, vessel_idx: int, route_idx: int) -> bool:
        """
        检查航线是否可行
        
        Args:
            vessel_idx: 船舶索引
            route_idx: 航线索引
            
        Returns:
            是否可行
        """
        vessel = self.input_data.vessel_types[vessel_idx]
        route = self.input_data.ship_routes[route_idx]
        
        # 检查船舶容量
        for arc in route.arcs:
            if arc.demand > vessel.capacity:
                return False
        
        # 检查时间窗口
        for port in route.ports:
            if port.turnover_time > self.input_data.time_horizon:
                return False
        
        return True
    
    def _check_convergence(self) -> bool:
        """
        检查收敛条件
        
        Returns:
            是否收敛
        """
        # 检查目标函数值
        if abs(self.determine_model.obj_val - self.dual_sub_problem_reactive.obj_val) < self.p.gap_tolerance:
            return True
        
        # 检查MIP间隙
        if self.dual_sub_problem_reactive.mip_gap < self.p.mip_gap_tolerance:
            return True
        
        return False
    
    def _get_final_results(self):
        """
        获取最终结果
        """
        # 获取目标函数值
        self.obj_val = self.determine_model.obj_val
        
        # 获取MIP间隙
        self.mip_gap = self.dual_sub_problem_reactive.mip_gap
        
        # 获取求解状态
        self.solve_status = self.dual_sub_problem_reactive.solve_status
        
        # 获取各项成本
        self.laden_cost = self.dual_sub_problem_reactive.laden_cost
        self.empty_cost = self.dual_sub_problem_reactive.empty_cost
        self.penalty_cost = self.dual_sub_problem_reactive.penalty_cost
        self.rental_cost = self.dual_sub_problem_reactive.rental_cost
    
    def _output_results(self):
        """
        输出结果
        """
        logger.info("Reactive Benders decomposition with PAP results:")
        logger.info(f"Total iterations: {self.iteration}")
        logger.info(f"Total time: {self.total_time:.2f} seconds")
        logger.info(f"Objective value: {self.obj_val}")
        logger.info(f"MIP gap: {self.mip_gap}")
        logger.info(f"Solve status: {self.solve_status}")
        logger.info(f"Laden cost: {self.laden_cost}")
        logger.info(f"Empty cost: {self.empty_cost}")
        logger.info(f"Penalty cost: {self.penalty_cost}")
        logger.info(f"Rental cost: {self.rental_cost}")
        logger.info(f"Total cuts generated: {self.callback.cut_count}") 