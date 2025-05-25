import numpy as np
from typing import List, Dict, Any, Tuple
from multi.model.base_model import BaseModel
from multi.utils.parameter import Parameter
from multi.utils.input_data import InputData
from multi.utils.default_setting import DefaultSetting
from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import logging
from dataclasses import dataclass
from multi.entity.request import Request
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('base_dual_model.log')  # 文件输出
    ]
)

# 获取日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 确保日志处理器不会重复
if not logger.handlers:
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)

class BaseDualModel(BaseModel):
    """对偶问题基类
    
    实现了对偶问题的基础功能:
    1. 变量定义
    2. 约束构建
    3. 目标函数构建
    4. 求解方法
    """
    
    def __init__(self, in_data: InputData, param: Parameter):
        """初始化对偶问题
        
        Args:
            in_data: 输入数据
            param: 模型参数
        """
        super().__init__(in_data, param)
        
        # 对偶变量
        self.dual_variables = {
            'lambda': None,  # 容量约束对偶变量
            'mu': None,      # 需求约束对偶变量
            'nu': None,      # 时间约束对偶变量
            'xi': None,      # 路径约束对偶变量
            'eta': None      # 船舶约束对偶变量
        }
        
        # 对偶目标值
        self.dual_objective = 0.0
        
        # 对偶间隙
        self.dual_gap = 0.0
        
        # 基本属性
        self.tau = 0
        self.obj_expr = None
        self.scene = None
        
        # 决策变量
        self.alpha_var = []  # α[i]
        self.beta_var = []   # β[nn']
        self.gamma_var = []  # γ[p][t]
        
        # 约束条件
        self.c1 = []  # 对偶约束X
        self.c2 = []  # 对偶约束Y
        self.c3 = []  # 对偶约束Z
        self.c4 = []  # 对偶约束G
        
        # 目标函数
        self.objective = None
        
        # 设置输入数据和参数
        self.in_data = in_data
        self.param = param
        
        # 创建CPLEX模型
        try:
            self.cplex = Model(name="BaseDualModel")
            if in_data is not None and param is not None:
                self.public_setting(self.cplex)
                self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise
        
    def build_variables(self):
        """构建变量"""
        # 容量约束对偶变量
        self.dual_variables['lambda'] = np.zeros((
            len(self.in_data.port_set),
            len(self.in_data.time_point_set)
        ))
        
        # 需求约束对偶变量
        self.dual_variables['mu'] = np.zeros((
            len(self.in_data.request_set),
            len(self.in_data.time_point_set)
        ))
        
        # 时间约束对偶变量
        self.dual_variables['nu'] = np.zeros((
            len(self.in_data.port_set),
            len(self.in_data.time_point_set)
        ))
        
        # 路径约束对偶变量
        self.dual_variables['xi'] = np.zeros((
            len(self.in_data.container_path_set),
            len(self.in_data.time_point_set)
        ))
        
        # 船舶约束对偶变量
        self.dual_variables['eta'] = np.zeros((
            len(self.in_data.vessel_set),
            len(self.in_data.ship_route_set)
        ))
        
    def build_constraints(self):
        """构建约束"""
        # 容量约束
        self.build_capacity_constraints()
        
        # 需求约束
        self.build_demand_constraints()
        
        # 时间约束
        self.build_time_constraints()
        
        # 路径约束
        self.build_path_constraints()
        
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_objective(self):
        """构建目标函数"""
        # 容量约束项
        capacity_term = np.sum(
            self.dual_variables['lambda'] * self.param.vessel_capacity
        )
        
        # 需求约束项
        demand_term = np.sum(
            self.dual_variables['mu'] * self.param.demand
        )
        
        # 时间约束项
        time_term = np.sum(
            self.dual_variables['nu'] * self.param.turnover_time
        )
        
        # 路径约束项
        path_term = np.sum(
            self.dual_variables['xi'] * self.param.travel_time_on_path
        )
        
        # 船舶约束项
        vessel_term = np.sum(
            self.dual_variables['eta'] * self.param.vessel_operation_cost
        )
        
        # 总目标
        self.dual_objective = (
            capacity_term +
            demand_term +
            time_term +
            path_term +
            vessel_term
        )
        
    def solve(self) -> Tuple[float, Dict[str, np.ndarray]]:
        """求解对偶问题
        
        Returns:
            Tuple[float, Dict[str, np.ndarray]]: 对偶目标值和变量值
        """
        # 构建变量
        self.build_variables()
        
        # 构建约束
        self.build_constraints()
        
        # 构建目标函数
        self.build_objective()
        
        # 求解
        self.optimize()
        
        return self.dual_objective, self.dual_variables
        
    def optimize(self):
        """优化求解
        
        具体实现由子类完成
        """
        raise NotImplementedError("Subclass must implement optimize()")
        
    def calculate_dual_gap(self, primal_objective: float):
        """计算对偶间隙
        
        Args:
            primal_objective: 原问题目标值
        """
        self.dual_gap = abs(primal_objective - self.dual_objective) / abs(primal_objective)
        
    def get_dual_variables(self) -> Dict[str, np.ndarray]:
        """获取对偶变量
        
        Returns:
            Dict[str, np.ndarray]: 对偶变量字典
        """
        return self.dual_variables
        
    def get_dual_objective(self) -> float:
        """获取对偶目标值
        
        Returns:
            float: 对偶目标值
        """
        return self.dual_objective
        
    def get_dual_gap(self) -> float:
        """获取对偶间隙
        
        Returns:
            float: 对偶间隙
        """
        return self.dual_gap

    def set_scene(self, scene):
        """设置场景"""
        self.scene = scene
        
    def get_scene(self):
        """获取场景"""
        return self.scene
        
    def set_dual_decision_vars(self):
        """设置对偶决策变量"""
        logger.info("=========Setting Dual Decision Variables==========")
        
        # 创建对偶变量
        # α[i]
        self.alpha_var = [None] * len(self.param.demand)
        # β[nn']
        self.beta_var = [None] * len(self.param.traveling_arcs_set)
        # γ[p][t]
        self.gamma_var = [[None for _ in range(len(self.param.time_point_set))] 
                         for _ in range(len(self.param.port_set))]
        
        # 创建α变量
        for i in range(len(self.param.demand)):
            var_name = f"alpha({i})"
            self.alpha_var[i] = self.cplex.continuous_var(
                lb=float('-inf'),
                ub=self.param.penalty_cost_for_demand[i],
                name=var_name
            )
            
        # 创建β变量
        for nn in range(len(self.param.traveling_arcs_set)):
            var_name = f"beta({nn})"
            self.beta_var[nn] = self.cplex.continuous_var(
                lb=float('-inf'),
                ub=0,
                name=var_name
            )
            
        # 创建γ变量
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                var_name = f"gamma({pp})({t})"
                self.gamma_var[pp][t] = self.cplex.continuous_var(
                    lb=0,
                    ub=float('inf'),
                    name=var_name
                )
                
        logger.info("=========Dual Decision Variables Set==========")
        
    def get_obj_expr(self, v_value: List[List[int]], u_value: List[float]) -> LinearExpr:
        """获取目标函数表达式
        
        Args:
            v_value: 船舶分配决策变量值
            u_value: 需求变化系数
            
        Returns:
            目标函数表达式
        """
        obj_expr = self.get_determine_obj(v_value)
        
        # 添加需求变化项
        for i in range(len(self.param.demand)):
            obj_expr.add_term(
                self.param.maximum_demand_variation[i] * u_value[i],
                self.alpha_var[i]
            )
            
        return obj_expr
        
    def get_determine_obj(self, v_var_value: List[List[int]]) -> LinearExpr:
        """获取确定性目标函数表达式
        
        Args:
            v_var_value: 船舶分配决策变量值
            
        Returns:
            确定性目标函数表达式
        """
        obj_expr = self.cplex.linear_expr()
        
        # I. 第一部分：正常需求项
        for i in range(len(self.param.demand)):
            obj_expr.add_term(self.param.demand[i], self.alpha_var[i])
            
        # II. 第二部分：船舶容量项
        capacitys = self.get_capacity_on_arcs(v_var_value)
        for n in range(len(self.param.traveling_arcs_set)):
            obj_expr.add_term(capacitys[n], self.beta_var[n])
            
        # III. 第三部分：初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                obj_expr.add_term(
                    -self.param.initial_empty_container[pp],
                    self.gamma_var[pp][t]
                )
                
        return obj_expr
        
    def set_dual_constraint_x(self):
        """设置对偶约束X"""
        logger.info("=========Setting Dual Constraint X==========")
        self.c1 = []
        
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            c1_k = [None] * request.number_of_laden_path
            self.c1.append(c1_k)
            
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                left = self.cplex.linear_expr()
                
                # 第一项：α[i]
                left.add_term(1, self.alpha_var[i])
                
                # 第二项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left.add_term(
                        self.param.arc_and_path[nn][j],
                        self.beta_var[nn]
                    )
                    
                # 第三项：γ[p][t]
                for t in range(1, len(self.param.time_point_set)):
                    for pp in range(len(self.param.port_set)):
                        # p == d(i)
                        if self.param.port_set[pp] == self.param.destination_of_demand[i]:
                            for nn in range(len(self.param.traveling_arcs_set)):
                                if (self.in_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                    self.in_data.traveling_arc_set[nn].destination_time <= t - self.param.turn_over_time[pp] and
                                    self.in_data.traveling_arc_set[nn].destination_time >= 1):
                                    left.add_term(
                                        self.param.arc_and_path[nn][j],
                                        self.gamma_var[pp][t]
                                    )
                                    
                        # p == o(i)
                        elif self.param.port_set[pp] == self.param.origin_of_demand[i]:
                            for nn in range(len(self.param.traveling_arcs_set)):
                                if (self.in_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                                    self.in_data.traveling_arc_set[nn].origin_time <= t and
                                    self.in_data.traveling_arc_set[nn].origin_time >= 1):
                                    left.add_term(
                                        -self.param.arc_and_path[nn][j],
                                        self.gamma_var[pp][t]
                                    )
                                    
                # 添加约束
                constr_name = f"C-X_{i}_{k}"
                self.c1[i][k] = self.cplex.add_constraint(
                    left <= self.param.laden_path_cost[j],
                    constr_name
                )
                
        logger.info("=========Dual Constraint X Set==========")
        
    def set_dual_constraint_y(self):
        """设置对偶约束Y"""
        logger.info("=========Setting Dual Constraint Y==========")
        self.c2 = []
        
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            c2_k = [None] * request.number_of_laden_path
            self.c2.append(c2_k)
            
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                left = self.cplex.linear_expr()
                
                # 第一项：α[i]
                left.add_term(1, self.alpha_var[i])
                
                # 第二项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left.add_term(
                        self.param.arc_and_path[nn][j],
                        self.beta_var[nn]
                    )
                    
                # 添加约束
                constr_name = f"C-Y_{i}_{k}"
                self.c2[i][k] = self.cplex.add_constraint(
                    left <= self.param.rental_cost * self.param.travel_time_on_path[j] + 
                           self.param.laden_path_cost[j],
                    constr_name
                )
                
        logger.info("=========Dual Constraint Y Set==========")
        
    def set_dual_constraint_z(self):
        """设置对偶约束Z"""
        logger.info("=========Setting Dual Constraint Z==========")
        if DefaultSetting.WHETHER_USE_MULTI_THREADS:
            self.set_dual_constraint_z_with_multi_threads()
        else:
            self.set_dual_constraint_z_with_single_thread()
            
        logger.info("=========Dual Constraint Z Set==========")
        
    def set_dual_constraint_z_with_single_thread(self):
        """使用单线程设置对偶约束Z"""
        self.c3 = []
        
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            c3_k = [None] * request.number_of_empty_path
            self.c3.append(c3_k)
            
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                left = self.cplex.linear_expr()
                
                # 第一项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left.add_term(
                        self.param.arc_and_path[nn][j],
                        self.beta_var[nn]
                    )
                    
                    # 第二项和第三项：γ[p][t]
                    for t in range(1, len(self.param.time_point_set)):
                        for pp in range(len(self.param.port_set)):
                            # p == o(i)
                            if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                                if (self.in_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                    self.in_data.traveling_arc_set[nn].destination_time <= t and
                                    self.in_data.traveling_arc_set[nn].destination_time >= 1):
                                    left.add_term(
                                        self.param.arc_and_path[nn][j],
                                        self.gamma_var[pp][t]
                                    )
                                    
                            # p
                            if (self.in_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                                self.in_data.traveling_arc_set[nn].origin_time <= t and
                                self.in_data.traveling_arc_set[nn].origin_time >= 1):
                                left.add_term(
                                    -self.param.arc_and_path[nn][j],
                                    self.gamma_var[pp][t]
                                )
                                
                # 添加约束
                constr_name = f"C-Z_{i}_{k}"
                self.c3[i][k] = self.cplex.add_constraint(
                    left <= self.param.empty_path_cost[j],
                    constr_name
                )
                
    def set_dual_constraint_z_with_multi_threads(self):
        """使用多线程设置对偶约束Z"""
        self.c3 = []
        left_items = {}
        lock = threading.Lock()
        
        # 创建工作队列
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            
            for i in range(len(self.param.demand)):
                request = self.in_data.request_set[i]
                c3_k = [None] * request.number_of_empty_path
                self.c3.append(c3_k)
                
                # 提交任务
                future = executor.submit(
                    self._process_constraint_z,
                    i,
                    request,
                    left_items,
                    lock
                )
                futures.append(future)
                
            # 等待所有任务完成
            for future in futures:
                future.result()
                
        # 添加约束
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                constr_name = f"C-Z_{i}_{k}"
                self.c3[i][k] = self.cplex.add_constraint(
                    left_items[i][k] <= self.param.empty_path_cost[j],
                    constr_name
                )
                
    def _process_constraint_z(self, i: int, request: Request, left_items: Dict, lock: threading.Lock):
        """处理对偶约束Z的单个任务
        
        Args:
            i: 需求索引
            request: 请求对象
            left_items: 左侧表达式字典
            lock: 线程锁
        """
        lefts = [None] * request.number_of_empty_path
        
        for k in range(request.number_of_empty_path):
            j = request.empty_path_indexes[k]
            left = self.cplex.linear_expr()
            
            # 第一项：β[nn']
            for nn in range(len(self.param.traveling_arcs_set)):
                left.add_term(
                    self.param.arc_and_path[nn][j],
                    self.beta_var[nn]
                )
                
                # 第二项和第三项：γ[p][t]
                for t in range(1, len(self.param.time_point_set)):
                    for pp in range(len(self.param.port_set)):
                        # p == o(i)
                        if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                            if (self.in_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                self.in_data.traveling_arc_set[nn].destination_time <= t and
                                self.in_data.traveling_arc_set[nn].destination_time >= 1):
                                left.add_term(
                                    self.param.arc_and_path[nn][j],
                                    self.gamma_var[pp][t]
                                )
                                
                        # p
                        if (self.in_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                            self.in_data.traveling_arc_set[nn].origin_time <= t and
                            self.in_data.traveling_arc_set[nn].origin_time >= 1):
                            left.add_term(
                                -self.param.arc_and_path[nn][j],
                                self.gamma_var[pp][t]
                            )
                            
            lefts[k] = left
            
        with lock:
            left_items[i] = lefts
            
    def set_dual_constraint_g(self):
        """设置对偶约束G"""
        logger.info("=========Setting Dual Constraint G==========")
        self.c4 = [None] * len(self.param.demand)
        
        for i in range(len(self.param.demand)):
            constr_name = f"C-G_{i}"
            self.c4[i] = self.cplex.add_constraint(
                self.alpha_var[i] <= self.param.penalty_cost_for_demand[i],
                constr_name
            )
            
        logger.info("=========Dual Constraint G Set==========")
        
    def change_objective_v_vars_coefficients(self, v_value: List[List[int]]):
        """更改目标函数中船舶变量的系数
        
        Args:
            v_value: 船舶分配决策变量值
        """
        # 获取船舶容量
        capacitys = self.get_capacity_on_arcs(v_value)
        
        # 更新目标函数系数
        for n in range(len(self.param.traveling_arcs_set)):
            self.cplex.set_linear_coefficient(
                self.objective,
                self.beta_var[n],
                capacitys[n]
            )
            
    def change_objective_u_vars_coefficients(self, u_value: List[float]):
        """更改目标函数中需求变量的系数
        
        Args:
            u_value: 需求变化系数
        """
        for i in range(len(self.param.demand)):
            self.cplex.set_linear_coefficient(
                self.objective,
                self.alpha_var[i],
                self.param.demand[i] + self.param.maximum_demand_variation[i] * u_value[i]
            )
            
    def change_objective_coefficients(self, v_value: List[List[int]], u_value: List[float]):
        """更改目标函数系数
        
        Args:
            v_value: 船舶分配决策变量值
            u_value: 需求变化系数
        """
        self.change_objective_u_vars_coefficients(u_value)
        self.change_objective_v_vars_coefficients(v_value)
        
    def get_constant_item(self) -> float:
        """获取常数项
        
        Returns:
            常数项值
        """
        constant_item = 0
        
        # 第一部分：正常需求项
        for i in range(len(self.param.demand)):
            constant_item += (
                (self.param.demand[i] + self.param.maximum_demand_variation[i] * self.u_value[i]) *
                self.cplex.get_value(self.alpha_var[i])
            )
            
        # 第三部分：初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                constant_item += (
                    -self.param.initial_empty_container[pp] *
                    self.cplex.get_value(self.gamma_var[pp][t])
                )
                
        return constant_item
        
    def construct_optimal_cut(self, v_vars: List[List[Any]], eta_var: Any) -> Any:
        """构造最优切割
        
        Args:
            v_vars: 船舶分配决策变量
            eta_var: 对偶变量
            
        Returns:
            最优切割约束
        """
        if self.cplex.get_solve_status() == "optimal":
            constant_item = self.get_constant_item()
            beta_value = self.get_beta_value()
            left = self.cplex.linear_expr()
            
            for n in range(len(self.param.traveling_arcs_set)):
                if beta_value[n] == 0:
                    continue
                    
                for w in range(len(self.param.vessel_path_set)):
                    r = self.in_data.vessel_path_set[w].route_id - 1
                    
                    for h in range(len(self.param.vessel_set)):
                        if DefaultSetting.FLEET_TYPE == "Homo":
                            if (self.param.arc_and_vessel_path[n][w] *
                                self.param.ship_route_and_vessel_path[r][w] *
                                self.param.vessel_type_and_ship_route[h][r] *
                                self.param.vessel_capacity[h] > 0):
                                left.add_term(
                                    self.param.arc_and_vessel_path[n][w] *
                                    self.param.ship_route_and_vessel_path[r][w] *
                                    self.param.vessel_type_and_ship_route[h][r] *
                                    self.param.vessel_capacity[h] *
                                    beta_value[n],
                                    v_vars[h][r]
                                )
                        elif DefaultSetting.FLEET_TYPE == "Hetero":
                            left.add_term(
                                self.param.arc_and_vessel_path[n][w] *
                                self.param.vessel_capacity[h] *
                                beta_value[n],
                                v_vars[h][w]
                            )
                        else:
                            logger.error("Error in Fleet type!")
                            
            left.add_term(-1, eta_var)
            
            return self.cplex.add_constraint(left <= -constant_item)
            
        return None
        
    def get_alpha_value(self) -> List[float]:
        """获取α变量值
        
        Returns:
            α变量值列表
        """
        alpha_value = [0.0] * len(self.param.demand)
        
        if self.cplex.get_solve_status() == "optimal":
            for i in range(len(self.param.demand)):
                alpha_value[i] = self.cplex.get_value(self.alpha_var[i])
                
        return alpha_value
        
    def get_beta_value(self) -> List[float]:
        """获取β变量值
        
        Returns:
            β变量值列表
        """
        beta_value = [0.0] * len(self.param.traveling_arcs_set)
        
        if self.cplex.get_solve_status() == "optimal":
            for nn in range(len(self.param.traveling_arcs_set)):
                beta_value[nn] = self.cplex.get_value(self.beta_var[nn])
                
        return beta_value
        
    def get_gamma_value(self) -> List[List[float]]:
        """获取γ变量值
        
        Returns:
            γ变量值二维列表
        """
        gamma_value = [[0.0 for _ in range(len(self.param.time_point_set))]
                      for _ in range(len(self.param.port_set))]
        
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                gamma_value[pp][t] = self.cplex.get_value(self.gamma_var[pp][t])
                
        return gamma_value
        
    def check_dual_constraint_x(self, alpha_value: List[float], 
                              beta_value: List[float], 
                              gamma_value: List[List[float]]) -> bool:
        """检查对偶约束X
        
        Args:
            alpha_value: α变量值
            beta_value: β变量值
            gamma_value: γ变量值
            
        Returns:
            是否满足约束
        """
        flag = True
        
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                left = 0
                
                # 第一项：α[i]
                left += alpha_value[i]
                
                # 第二项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left += self.param.arc_and_path[nn][j] * beta_value[nn]
                    
                # 第三项：γ[p][t]
                for t in range(1, len(self.param.time_point_set)):
                    for pp in range(len(self.param.port_set)):
                        # p == d(i)
                        if self.param.port_set[pp] == self.param.destination_of_demand[i]:
                            for nn in range(len(self.param.traveling_arcs_set)):
                                if (self.in_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                    self.in_data.traveling_arc_set[nn].destination_time <= t - self.param.turn_over_time[pp] and
                                    self.in_data.traveling_arc_set[nn].destination_time >= 1):
                                    left += self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                    
                        # p == o(i)
                        if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                            for nn in range(len(self.param.traveling_arcs_set)):
                                if (self.in_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                                    self.in_data.traveling_arc_set[nn].origin_time <= t and
                                    self.in_data.traveling_arc_set[nn].origin_time >= 1):
                                    left += -self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                    
                constr_name = f"C-X_{i}_{k}"
                constraint_slack = self.cplex.get_slack(self.c1[i][k])
                
                if constraint_slack < 0:
                    logger.info(f"Cplex: {constr_name} is violated with {constraint_slack}")
                    
                if left > self.param.laden_path_cost[j]:
                    logger.info(f"Dual Constraint X {constr_name} is violated! {left} {self.param.laden_path_cost[j]}")
                    flag = False
                    
        return flag
        
    def check_dual_constraint_y(self, alpha_value: List[float], 
                              beta_value: List[float]) -> bool:
        """检查对偶约束Y
        
        Args:
            alpha_value: α变量值
            beta_value: β变量值
            
        Returns:
            是否满足约束
        """
        flag = True
        
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                left = 0
                
                # 第一项：α[i]
                left += alpha_value[i]
                
                # 第二项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left += self.param.arc_and_path[nn][j] * beta_value[nn]
                    
                constr_name = f"C-Y_{i}_{k}"
                constraint_slack = self.cplex.get_slack(self.c2[i][k])
                
                if constraint_slack < 0:
                    logger.info(f"Cplex: {constr_name} is violated with {constraint_slack}")
                    
                if left > self.param.rental_cost * self.param.travel_time_on_path[j] + self.param.laden_path_cost[j]:
                    logger.info(f"Dual Constraint Y {constr_name} is violated! {left} {self.param.rental_cost * self.param.travel_time_on_path[j] + self.param.laden_path_cost[j]}")
                    flag = False
                    
        return flag
        
    def check_dual_constraint_z(self, beta_value: List[float], 
                              gamma_value: List[List[float]]) -> bool:
        """检查对偶约束Z
        
        Args:
            beta_value: β变量值
            gamma_value: γ变量值
            
        Returns:
            是否满足约束
        """
        flag = True
        
        for i in range(len(self.param.demand)):
            request = self.in_data.request_set[i]
            
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                left = 0
                
                # 第一项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left += self.param.arc_and_path[nn][j] * beta_value[nn]
                    
                    # 第二项和第三项：γ[p][t]
                    for t in range(1, len(self.param.time_point_set)):
                        for pp in range(len(self.param.port_set)):
                            # p == o(i)
                            if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                                if (self.in_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                    self.in_data.traveling_arc_set[nn].destination_time <= t and
                                    self.in_data.traveling_arc_set[nn].destination_time >= 1):
                                    left += self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                    
                            # p
                            if (self.in_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                                self.in_data.traveling_arc_set[nn].origin_time <= t and
                                self.in_data.traveling_arc_set[nn].origin_time >= 1):
                                left += -self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                
                constr_name = f"C-Z_{i}_{k}"
                constraint_slack = self.cplex.get_slack(self.c3[i][k])
                
                if constraint_slack < 0:
                    logger.info(f"Cplex: {constr_name} is violated with {constraint_slack}")
                    
                if left > self.param.empty_path_cost[j]:
                    logger.info(f"Dual Constraint Z {constr_name} is violated! {left} {self.param.empty_path_cost[j]}")
                    flag = False
                    
        return flag
        
    def get_capacity_on_arcs(self, v_value: List[List[int]]) -> List[float]:
        """计算航段上的运力
        
        Args:
            v_value: 船舶分配决策变量值
            
        Returns:
            航段运力列表
        """
        capacitys = [0.0] * len(self.param.traveling_arcs_set)
        
        for h in range(len(self.param.vessel_set)):
            for r in range(len(self.param.ship_route_set)):
                if v_value[h][r] == 1:
                    for n in range(len(self.param.traveling_arcs_set)):
                        if self.param.traveling_arcs_set[n] in self.param.ship_route_set[r].arcs:
                            capacitys[n] += self.param.vessel_set[h].capacity
                            
        return capacitys
        
    def public_setting(self, model: Model):
        """设置公共参数
        
        Args:
            model: CPLEX模型
        """
        # 设置求解参数
        model.parameters.mip.tolerances.mipgap = DefaultSetting.MIPGap
        model.parameters.timelimit = DefaultSetting.TimeLimit
        model.parameters.threads = DefaultSetting.Threads
        model.parameters.mip.tolerances.integrality = DefaultSetting.IntegralityTolerance
        
        # 设置输出参数
        model.parameters.mip.display = DefaultSetting.MIPDisplay
        model.parameters.simplex.display = DefaultSetting.SimplexDisplay
        
    def export_model(self):
        """导出模型"""
        self.cplex.export_as_lp(f"{self.model_name}.lp") 