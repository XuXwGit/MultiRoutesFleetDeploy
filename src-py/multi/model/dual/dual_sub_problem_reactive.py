import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.dual.base_dual_model import BaseDualModel
import numpy as np
from multi.model.dual.dual_sub_problem import DualSubProblem
from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import threading
import time

logger = logging.getLogger(__name__)

class DualSubProblemReactive(DualSubProblem):
    """
    反应式对偶子问题模型类
    
    用于生成Benders切割,包括:
    1. 对偶变量
    2. 目标函数
    3. 约束条件
    
    主要变量:
    1. alpha[i]: 需求i的对偶变量
    2. beta1[n]: 航段n运力约束的对偶变量(第一组)
    3. beta2[n]: 航段n运力约束的对偶变量(第二组)
    4. gamma[p][t]: 时刻t港口p空箱量的对偶变量
    5. lambda[i]: 辅助变量,用于线性化
    6. miu[i]: 不确定需求变量
    
    主要约束:
    1. 对偶约束
    2. 不确定集约束
    3. 线性化约束
    """
    
    def __init__(self, input_data: InputData, param: Parameter, tau: int):
        """
        初始化反应式对偶子问题模型
        
        Args:
            input_data: 输入数据
            param: 模型参数
            tau: 预算约束参数
        """
        super().__init__(input_data, param, tau)
        
        # 设置模型名称
        self.model_name = f"DSPR-R{len(input_data.ship_route_set)}-T{param.time_horizon}-{DefaultSetting.FLEET_TYPE}-S{DefaultSetting.RANDOM_SEED}"
        
        # 反应式参数
        self.reactive_params = {
            'alpha': DefaultSetting.ReactiveAlpha,  # 反应系数
            'beta': DefaultSetting.ReactiveBeta,    # 调整系数
            'gamma': DefaultSetting.ReactiveGamma   # 学习率
        }
        
        # 历史信息
        self.history = {
            'path_selection': [],    # 路径选择历史
            'vessel_assignment': [], # 船舶分配历史
            'demand_satisfaction': [] # 需求满足历史
        }
        
        self.tau = tau  # 不确定集边界
        self.v_var_value1 = [[0 for _ in range(param.shipping_route_num)] for _ in range(param.vessel_num)]  # 第一组v变量值
        self.v_var_value2 = [[0 for _ in range(param.vessel_path_num)] for _ in range(param.vessel_num)]  # 第二组v变量值
        self.alpha_var = {}  # 需求对偶变量
        self.beta_var1 = {}  # 运力约束对偶变量(第一组)
        self.beta_var2 = {}  # 运力约束对偶变量(第二组)
        self.gamma_var = {}  # 空箱量对偶变量
        self.lambda_var = {}  # 辅助变量
        self.miu_var = {}  # 不确定需求变量
        self.u_constr = None  # 不确定集约束
        self.obj_val = 0  # 目标函数值
        self.sub_obj = 0  # 子问题目标函数值
        self.mip_gap = 0  # MIP间隙
        
        # 迭代记录
        self.iteration_history = {
            'objective_values': [],
            'tau_values': [],
            'u_values': []
        }
    
    def build_model(self):
        """
        构建反应式对偶子问题模型
        """
        try:
            # 创建变量
            self._create_variables()
            
            # 创建目标函数
            self._create_objective()
            
            # 创建约束
            self._create_constraints()
            
            # 设置求解参数
            self._set_solver_parameters()
            
        except Exception as e:
            logger.error(f"Error in building reactive dual sub problem: {str(e)}")
            raise
    
    def _create_variables(self):
        """
        创建决策变量
        """
        # 需求对偶变量 alpha[i]
        for i in range(self.input_data.request_num):
            self.alpha_var[i] = self.model.addVar(
                vtype="C",
                name=f"alpha_{i}"
            )
        
        # 运力约束对偶变量 beta1[n]和beta2[n]
        for n in range(self.input_data.arc_num):
            self.beta_var1[n] = self.model.addVar(
                vtype="C",
                ub=0,  # beta <= 0
                name=f"beta1_{n}"
            )
            self.beta_var2[n] = self.model.addVar(
                vtype="C",
                ub=0,  # beta <= 0
                name=f"beta2_{n}"
            )
        
        # 空箱量对偶变量 gamma[p][t]
        for p in range(self.input_data.port_num):
            self.gamma_var[p] = {}
            for t in range(1, self.input_data.time_horizon + 1):
                self.gamma_var[p][t] = self.model.addVar(
                    vtype="C",
                    lb=0,  # gamma >= 0
                    name=f"gamma_{p}_{t}"
                )
        
        # 辅助变量 lambda[i]
        for i in range(self.input_data.request_num):
            self.lambda_var[i] = self.model.addVar(
                vtype="C",
                name=f"lambda_{i}"
            )
        
        # 不确定需求变量 miu[i]
        for i in range(self.input_data.request_num):
            self.miu_var[i] = self.model.addVar(
                vtype="B",
                name=f"miu_{i}"
            )
    
    def _create_objective(self):
        """
        创建目标函数
        """
        # 第一部分: 需求项
        demand_term = sum(
            self.input_data.requests[i].demand * self.alpha_var[i]
            for i in range(self.input_data.request_num)
        )
        
        # 第二部分: 运力项(第一组)
        capacity_term1 = sum(
            self._get_capacity_on_arc1(n) * self.beta_var1[n]
            for n in range(self.input_data.arc_num)
        )
        
        # 第二部分: 运力项(第二组)
        capacity_term2 = sum(
            self._get_capacity_on_arc2(n) * self.beta_var2[n]
            for n in range(self.input_data.arc_num)
        )
        
        # 第三部分: 空箱量项
        empty_term = sum(
            -self.input_data.ports[p].initial_empty * self.gamma_var[p][t]
            for p in range(self.input_data.port_num)
            for t in range(1, self.input_data.time_horizon + 1)
        )
        
        # 设置目标函数
        self.model.setObjective(
            demand_term + capacity_term1 + capacity_term2 + empty_term,
            sense="maximize"
        )
    
    def _create_constraints(self):
        """
        创建约束条件
        """
        # 对偶约束
        self._create_dual_constraints()
        
        # 不确定集约束
        self._create_uncertain_set_constraints()
        
        # 线性化约束
        self._create_linearization_constraints()
    
    def _create_dual_constraints(self):
        """
        创建对偶约束
        """
        # 需求约束
        for i in range(self.input_data.request_num):
            for j in range(self.input_data.requests[i].path_num):
                path = self.input_data.requests[i].paths[j]
                
                # 构建约束左端
                left = self.alpha_var[i]
                
                # 添加航段项(第一组)
                for n in range(self.input_data.arc_num):
                    if self.input_data.arcs[n] in path.arcs:
                        left += self.beta_var1[n]
                
                # 添加航段项(第二组)
                for n in range(self.input_data.arc_num):
                    if self.input_data.arcs[n] in path.arcs:
                        left += self.beta_var2[n]
                
                # 添加港口项
                for p in range(self.input_data.port_num):
                    for t in range(1, self.input_data.time_horizon + 1):
                        if self.input_data.ports[p] == path.destination_port and t <= path.destination_time - self.input_data.ports[p].turnover_time:
                            left += self.gamma_var[p][t]
                        if self.input_data.ports[p] == path.origin_port and t <= path.origin_time:
                            left -= self.gamma_var[p][t]
                
                # 添加约束
                self.model.addConstr(
                    left <= path.cost,
                    name=f"dual_demand_{i}_{j}"
                )
        
        # 运力约束(第一组)
        for n in range(self.input_data.arc_num):
            for i in range(self.input_data.request_num):
                for j in range(self.input_data.requests[i].path_num):
                    path = self.input_data.requests[i].paths[j]
                    if self.input_data.arcs[n] in path.arcs:
                        self.model.addConstr(
                            self.beta_var1[n] <= 0,
                            name=f"dual_capacity1_{n}_{i}_{j}"
                        )
        
        # 运力约束(第二组)
        for n in range(self.input_data.arc_num):
            for i in range(self.input_data.request_num):
                for j in range(self.input_data.requests[i].path_num):
                    path = self.input_data.requests[i].paths[j]
                    if self.input_data.arcs[n] in path.arcs:
                        self.model.addConstr(
                            self.beta_var2[n] <= 0,
                            name=f"dual_capacity2_{n}_{i}_{j}"
                        )
        
        # 空箱量约束
        for p in range(self.input_data.port_num):
            for t in range(1, self.input_data.time_horizon + 1):
                self.model.addConstr(
                    self.gamma_var[p][t] >= 0,
                    name=f"dual_empty_{p}_{t}"
                )
    
    def _create_uncertain_set_constraints(self):
        """
        创建不确定集约束
        """
        # 预算约束
        self.u_constr = self.model.addConstr(
            sum(self.miu_var[i] for i in range(self.input_data.request_num)) <= self.tau,
            name="uncertain_set"
        )
    
    def _create_linearization_constraints(self):
        """
        创建线性化约束
        """
        M = 1e6  # 大M值
        
        for i in range(self.input_data.request_num):
            # lambda[i] <= alpha[i]
            self.model.addConstr(
                self.lambda_var[i] <= self.alpha_var[i],
                name=f"linear_1_{i}"
            )
            
            # lambda[i] >= alpha[i] - M*(1-miu[i])
            self.model.addConstr(
                self.lambda_var[i] >= self.alpha_var[i] - M*(1 - self.miu_var[i]),
                name=f"linear_2_{i}"
            )
            
            # lambda[i] <= M*miu[i]
            self.model.addConstr(
                self.lambda_var[i] <= M*self.miu_var[i],
                name=f"linear_3_{i}"
            )
            
            # lambda[i] >= -M*miu[i]
            self.model.addConstr(
                self.lambda_var[i] >= -M*self.miu_var[i],
                name=f"linear_4_{i}"
            )
    
    def _get_capacity_on_arc1(self, arc_idx: int) -> float:
        """
        计算航段上的运力(第一组)
        
        Args:
            arc_idx: 航段索引
            
        Returns:
            航段运力
        """
        capacity = 0
        arc = self.input_data.arcs[arc_idx]
        
        for i in range(self.input_data.vessel_num):
            for j in range(self.input_data.route_num):
                if self.v_var_value1[i][j] == 1:
                    vessel = self.input_data.vessel_types[i]
                    route = self.input_data.ship_routes[j]
                    if arc in route.arcs:
                        capacity += vessel.capacity
        
        return capacity
    
    def _get_capacity_on_arc2(self, arc_idx: int) -> float:
        """
        计算航段上的运力(第二组)
        
        Args:
            arc_idx: 航段索引
            
        Returns:
            航段运力
        """
        capacity = 0
        arc = self.input_data.arcs[arc_idx]
        
        for i in range(self.input_data.vessel_num):
            for j in range(self.input_data.path_num):
                if self.v_var_value2[i][j] == 1:
                    vessel = self.input_data.vessel_types[i]
                    path = self.input_data.vessel_paths[j]
                    if arc in path.arcs:
                        capacity += vessel.capacity
        
        return capacity
    
    def solve_model(self):
        """
        求解反应式对偶子问题
        """
        try:
            if DefaultSetting.WHETHER_EXPORT_MODEL:
                self.export_model()
                
            start_time = time.time()
            if self.cplex.solve():
                end_time = time.time()
                
                self.set_obj_val(self.cplex.objective_value)
                self.set_solve_time(end_time - start_time)
                self.set_obj_gap(self.cplex.solve_details.mip_relative_gap)
                
                # 更新u值
                self.u_value = np.zeros(len(self.param.demand), dtype=float)
                request = np.zeros(len(self.param.demand), dtype=float)
                request_list = []
                
                for i in range(len(self.param.demand)):
                    request[i] = self.cplex.solution.get_value(self.miu_var[i])
                    if self.cplex.solution.get_value(self.miu_var[i]) != 0:
                        tolerance = self.cplex.parameters.mip.tolerances.integrality
                        if self.cplex.solution.get_value(self.miu_var[i]) >= 1 - tolerance:
                            self.u_value[i] = 1
                            request_list.append(i)
                            
                # 创建场景
                from multi.entity.scenario import Scenario
                scene = Scenario()
                scene.set_request(request)
                scene.set_worse_request_set(request_list)
                self.set_scene(scene)
                
                if DefaultSetting.DEBUG_ENABLE and DefaultSetting.DUAL_SUB_ENABLE:
                    logger.info("------------------------------------------------------------------------")
                    logger.info(f"SolveTime = {end_time - start_time}ms")
                    logger.info(f"DSPR-Obj = {self.get_obj_val():.2f}")
                    self.print_solution()
                    logger.info("------------------------------------------------------------------------")
                    
                    from multi.model.primal.sub_problem import SubProblem
                    from multi.model.dual.dual_problem import DualProblem
                    
                    sp = SubProblem(self.input_data, self.param, self.v_var_value, request)
                    sp.solve_model()
                    
                    dp = DualProblem(self.input_data, self.param, self.v_var_value, request)
                    dp.solve_model()
                    
                    logger.info(f"SP-Obj = \t{sp.get_obj_val():.2f}")
                    logger.info(f"DP-Obj = \t{dp.get_obj_val():.2f}")
                    logger.info(f"DSPR-Obj = \t{self.get_obj_val():.2f}")
                    logger.info(f"Dual-Obj = \t{self.calculate_dual_obj_val(self.v_var_value):.2f}")
                    
                    logger.info(f"Determine Cost(DSPR) = \t{self.calculate_determine_cost():.2f}")
                    logger.info(f"Determine Cost(DP) = \t{dp.calculate_determine_cost():.2f}")
                    
                    logger.info(f"Uncertain Cost(DSPR) = \t{self.calculate_uncertain_cost():.2f}")
                    logger.info(f"Uncertain Cost(DP) = \t{dp.calculate_uncertain_cost():.2f}")
                    
                    logger.info("------------------------------------------------------------------------")
            else:
                logger.info("DualSubProblemReactive No Solution")
        except Exception as e:
            logger.error(f"Error in solving model: {str(e)}")
            
    def set_uncertain_set_bound(self, new_tau: int):
        """
        设置不确定集边界
        
        Args:
            new_tau: 新的预算约束参数
        """
        self.u_constr.set_ub(new_tau)
        
    def change_objective_v_coefficients(self, v_value: List[List[int]]):
        """修改目标函数中v变量的系数
        
        Args:
            v_value: 新的v变量值
        """
        self.v_var_value = v_value
        self.cplex.update()
        
    def print_solution(self):
        """打印解"""
        logger.info(f"The Worst Case(DSPR)(tau = {self.tau}):")
        for i in range(len(self.param.demand)):
            if self.u_value[i] != 0:
                print(f"{i}({self.u_value[i]})\t", end="")
        print()
        
    def get_iteration_history(self) -> Dict[str, List]:
        """获取迭代历史
        
        Returns:
            迭代历史记录
        """
        return self.iteration_history
        
    def print_solution(self):
        """打印解"""
        super().print_solution()
        
        # 打印迭代历史
        logger.info("Iteration History:")
        logger.info("Objective Values:")
        for i, obj_val in enumerate(self.iteration_history['objective_values']):
            logger.info(f"Iteration {i}: {obj_val:.2f}")
            
        logger.info("Tau Values:")
        for i, tau_val in enumerate(self.iteration_history['tau_values']):
            logger.info(f"Iteration {i}: {tau_val}")
            
        logger.info("U Values:")
        for i, u_val in enumerate(self.iteration_history['u_values']):
            logger.info(f"Iteration {i}: {u_val}")
    
    def optimize(self):
        """优化求解
        
        使用反应式动态规划求解子问题
        """
        # 初始化状态
        self.initialize_states()
        
        # 前向递推
        self.forward_recursion()
        
        # 后向追踪
        self.backward_tracking()
        
        # 反应式调整
        self.reactive_adjustment()
        
    def reactive_adjustment(self):
        """反应式调整"""
        # 调整路径选择
        self.adjust_path_selection()
        
        # 调整船舶分配
        self.adjust_vessel_assignment()
        
        # 调整需求满足
        self.adjust_demand_satisfaction()
        
        # 更新历史信息
        self.update_history()
        
    def adjust_path_selection(self):
        """调整路径选择"""
        # 对每条路径
        for j in range(len(self.input_data.container_path_set)):
            # 对每个时间点
            for t in range(len(self.param.time_point_set)):
                # 计算调整值
                adjustment = self.calculate_path_adjustment(j, t)
                
                # 更新路径选择变量
                self.sub_problem_variables['x'][j, t] += adjustment
                
    def adjust_vessel_assignment(self):
        """调整船舶分配"""
        # 对每艘船舶
        for h in range(len(self.input_data.vessel_set)):
            # 对每条航线
            for r in range(len(self.input_data.ship_route_set)):
                # 计算调整值
                adjustment = self.calculate_vessel_adjustment(h, r)
                
                # 更新船舶分配变量
                self.sub_problem_variables['y'][h, r] += adjustment
                
    def adjust_demand_satisfaction(self):
        """调整需求满足"""
        # 对每个需求
        for i in range(len(self.input_data.request_set)):
            # 对每个时间点
            for t in range(len(self.param.time_point_set)):
                # 计算调整值
                adjustment = self.calculate_demand_adjustment(i, t)
                
                # 更新需求满足变量
                self.sub_problem_variables['z'][i, t] += adjustment
                
    def calculate_path_adjustment(self, path: int, time: int) -> float:
        """计算路径选择调整值
        
        Args:
            path: 路径索引
            time: 时间点索引
            
        Returns:
            float: 调整值
        """
        # 获取历史信息
        history = self.get_path_history(path, time)
        
        # 计算历史趋势
        trend = self.calculate_trend(history)
        
        # 计算调整值
        adjustment = (
            self.reactive_params['alpha'] * trend +
            self.reactive_params['beta'] * self.calculate_path_value(path, time) +
            self.reactive_params['gamma'] * self.calculate_path_value_backward(path, time)
        )
        
        return adjustment
        
    def calculate_vessel_adjustment(self, vessel: int, route: int) -> float:
        """计算船舶分配调整值
        
        Args:
            vessel: 船舶索引
            route: 航线索引
            
        Returns:
            float: 调整值
        """
        # 获取历史信息
        history = self.get_vessel_history(vessel, route)
        
        # 计算历史趋势
        trend = self.calculate_trend(history)
        
        # 计算调整值
        adjustment = (
            self.reactive_params['alpha'] * trend +
            self.reactive_params['beta'] * self.calculate_vessel_value(vessel, route, 0) +
            self.reactive_params['gamma'] * self.calculate_vessel_value_backward(vessel, route, 0)
        )
        
        return adjustment
        
    def calculate_demand_adjustment(self, request: int, time: int) -> float:
        """计算需求满足调整值
        
        Args:
            request: 需求索引
            time: 时间点索引
            
        Returns:
            float: 调整值
        """
        # 获取历史信息
        history = self.get_demand_history(request, time)
        
        # 计算历史趋势
        trend = self.calculate_trend(history)
        
        # 计算调整值
        adjustment = (
            self.reactive_params['alpha'] * trend +
            self.reactive_params['beta'] * self.calculate_demand_value(request, time) +
            self.reactive_params['gamma'] * self.calculate_demand_value_backward(request, time)
        )
        
        return adjustment
        
    def get_path_history(self, path: int, time: int) -> List[float]:
        """获取路径选择历史
        
        Args:
            path: 路径索引
            time: 时间点索引
            
        Returns:
            List[float]: 历史值列表
        """
        history = []
        for h in self.history['path_selection']:
            if h['path'] == path and h['time'] == time:
                history.append(h['value'])
        return history
        
    def get_vessel_history(self, vessel: int, route: int) -> List[float]:
        """获取船舶分配历史
        
        Args:
            vessel: 船舶索引
            route: 航线索引
            
        Returns:
            List[float]: 历史值列表
        """
        history = []
        for h in self.history['vessel_assignment']:
            if h['vessel'] == vessel and h['route'] == route:
                history.append(h['value'])
        return history
        
    def get_demand_history(self, request: int, time: int) -> List[float]:
        """获取需求满足历史
        
        Args:
            request: 需求索引
            time: 时间点索引
            
        Returns:
            List[float]: 历史值列表
        """
        history = []
        for h in self.history['demand_satisfaction']:
            if h['request'] == request and h['time'] == time:
                history.append(h['value'])
        return history
        
    def calculate_trend(self, history: List[float]) -> float:
        """计算历史趋势
        
        Args:
            history: 历史值列表
            
        Returns:
            float: 趋势值
        """
        if len(history) < 2:
            return 0.0
            
        # 计算差分
        diffs = [history[i] - history[i-1] for i in range(1, len(history))]
        
        # 计算趋势
        trend = sum(diffs) / len(diffs)
        
        return trend
        
    def update_history(self):
        """更新历史信息"""
        # 更新路径选择历史
        for j in range(len(self.input_data.container_path_set)):
            for t in range(len(self.param.time_point_set)):
                self.history['path_selection'].append({
                    'path': j,
                    'time': t,
                    'value': self.sub_problem_variables['x'][j, t]
                })
                
        # 更新船舶分配历史
        for h in range(len(self.input_data.vessel_set)):
            for r in range(len(self.input_data.ship_route_set)):
                self.history['vessel_assignment'].append({
                    'vessel': h,
                    'route': r,
                    'value': self.sub_problem_variables['y'][h, r]
                })
                
        # 更新需求满足历史
        for i in range(len(self.input_data.request_set)):
            for t in range(len(self.param.time_point_set)):
                self.history['demand_satisfaction'].append({
                    'request': i,
                    'time': t,
                    'value': self.sub_problem_variables['z'][i, t]
                })
                
        # 限制历史长度
        max_history_length = DefaultSetting.MaxHistoryLength
        for key in self.history:
            if len(self.history[key]) > max_history_length:
                self.history[key] = self.history[key][-max_history_length:] 

    def adaptive_adjust_tau(self):
        """自适应调整预算约束参数"""
        if len(self.iteration_history['objective_values']) < 2:
            return
            
        # 计算目标值变化
        obj_change = (
            self.iteration_history['objective_values'][-1] -
            self.iteration_history['objective_values'][-2]
        )
        
        # 根据目标值变化调整tau
        if obj_change > 0:
            # 目标值增加，增加tau
            self.tau = int(self.tau * self.reactive_params['gamma'])
        elif obj_change < 0:
            # 目标值减少，减少tau
            self.tau = int(self.tau * self.reactive_params['beta'])
            
        # 确保tau在合理范围内
        self.tau = max(1, min(self.tau, len(self.param.demand)))
        
        # 更新约束
        self.update_tau_constraint()
        
    def update_tau_constraint(self):
        """更新预算约束"""
        # 移除旧约束
        if hasattr(self, 'u_constr'):
            self.cplex.remove_constraint(self.u_constr)
            
        # 添加新约束
        self.set_uncertain_set_constraints()
        
    def set_uncertain_set_constraints(self):
        """设置不确定集约束"""
        # 移除旧约束
        if hasattr(self, 'u_constr'):
            self.cplex.remove_constraint(self.u_constr)
            
        # 添加新约束
        self.u_constr = self.cplex.addConstr(
            sum(self.miu_var[i] for i in range(self.input_data.request_num)) <= self.tau,
            name="uncertain_set"
        ) 