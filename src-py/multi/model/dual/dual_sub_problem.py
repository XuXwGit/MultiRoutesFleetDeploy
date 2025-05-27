import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.dual.base_dual_model import BaseDualModel
import numpy as np
from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import threading
import time

logger = logging.getLogger(__name__)

class DualSubProblem(BaseDualModel):
    """
    对偶子问题模型类
    
    用于生成Benders切割,包括:
    1. 对偶变量
    2. 目标函数
    3. 约束条件
    
    主要变量:
    1. alpha[i]: 需求i的对偶变量
    2. beta[n]: 航段n运力约束的对偶变量
    3. gamma[p][t]: 时刻t港口p空箱量的对偶变量
    4. lambda[i]: 辅助变量,用于线性化
    5. miu[i]: 不确定需求变量
    
    主要约束:
    1. 对偶约束
    2. 不确定集约束
    3. 线性化约束
    """
    
    def __init__(self, input_data: InputData, param: Parameter, tau: int):
        """
        初始化对偶子问题模型
        
        Args:
            in_data: 输入数据
            param: 模型参数
            tau: 预算约束参数
        """
        super().__init__(input_data, param)
        self.lambda_var = {}  # 辅助变量
        self.miu_var = {}  # 不确定需求变量
        self.u_constr = {}  # 不确定集约束
        self.sub_obj = 0  # 子问题目标函数值
        
        # 子问题索引
        self.sub_problem_index = 0
        
        # 子问题变量
        self.sub_problem_variables = {}
        
        # 设置模型名称
        self.model_name = f"DSP-R{len(input_data.ship_route_set)}-T{param.time_horizon}-{DefaultSetting.FLEET_TYPE}-S{DefaultSetting.RANDOM_SEED}"
        
        # 初始化变量
        if DefaultSetting.FLEET_TYPE == "Homo":
            self.v_var_value = np.zeros((len(param.vessel_set), len(param.shipping_route_set)), dtype=int)
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            self.v_var_value = np.zeros((len(param.vessel_set), len(param.vessel_path_set)), dtype=int)
        else:
            logger.error("Error in Fleet type!")
            
        self.tau = tau
        self.u_value = np.zeros(len(param.demand), dtype=float)

        self.initialize()

    
    def initialize(self):
        """初始化模型"""
        # 创建CPLEX模型
        try:
            self.cplex = Model(name="DualSubProblem")
            self.public_setting(self.cplex)
            self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise

    def frame(self):
        """构建模型框架"""
        try:
            # 设置决策变量
            self.set_dual_decision_vars()
            self.set_uncertain_vars()
            
            # 设置约束
            self.set_dual_constraint_x()
            self.set_dual_constraint_y()
            self.set_dual_constraint_z()
            self.set_dual_constraint_g()
            self.set_uncertain_set_constraints()
            
            # 设置目标函数
            self.objective = self.get_dual_obj_expr()
            self.cplex.set_objective("max", self.objective)
            
        except Exception as e:
            logger.error(f"Error in building model: {str(e)}")
            raise
            
    def set_uncertain_vars(self):
        """设置不确定变量"""
        # 不确定需求变量
        for i in range(len(self.param.demand)):
            var_name = f"miu({i})"
            self.miu_var[i] = self.cplex.binary_var(name=var_name)
            
    def set_uncertain_set_constraints(self):
        """设置不确定集约束"""
        # 预算约束
        self.cplex.add_constraint(
            self.cplex.sum(self.miu_var[i] for i in range(len(self.param.demand))) <= self.tau,
            "Budget"
        )
        
    def get_dual_obj_expr(self) -> LinearExpr:
        """获取目标函数表达式
        
        Returns:
            目标函数表达式
        """
        obj_expr = self.cplex.linear_expr()
        
        # 第一部分：正常需求项
        for i in range(len(self.param.demand)):
            obj_expr.add_term(
                coeff=self.param.demand[i],
                dvar=self.alpha_var[i]
            )
            
        # 第二部分：船舶容量项
        capacitys = self.get_capacity_on_arcs(self.v_var_value)
        for n in range(len(self.param.traveling_arcs_set)):
            obj_expr.add_term(
                coeff=capacitys[n],
                dvar=self.beta_var[n]
            )
            
        # 第三部分：初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                obj_expr.add_term(
                    coeff=-self.param.initial_empty_container[pp],
                    dvar=self.gamma_var[pp][t]
                )
                
        # 第四部分：不确定需求项
        # logger.info(f"self.param.maximum_demand_variation: {self.param.maximum_demand_variation}")
        for i in range(len(self.param.demand)):
            obj_expr.add_term(
                coeff=self.param.maximum_demand_variation[i],
                dvar=self.miu_var[i]
            )
            
        return obj_expr
        
    def solve_model(self):
        """求解对偶子问题"""
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
                for i in range(len(self.param.demand)):
                    if self.cplex.solution.get_value(self.miu_var[i]) > 0.5:
                        self.u_value[i] = 1.0
                        
                if DefaultSetting.DEBUG_ENABLE and DefaultSetting.DUAL_SUB_ENABLE:
                    logger.info("------------------------------------------------------------------------")
                    logger.info(f"SolveTime = {end_time - start_time}ms")
                    logger.info(f"DSP-Obj = {self.get_obj_val():.2f}")
                    self.print_solution()
                    logger.info("------------------------------------------------------------------------")
            else:
                logger.info("DualSubProblem No Solution")
        except Exception as e:
            logger.error(f"Error in solving model: {str(e)}")
            
    def print_solution(self):
        """打印解"""
        logger.info(f"The Worst Case(DSP)(tau = {self.tau}):")
        for i in range(len(self.param.demand)):
            if self.u_value[i] != 0:
                print(f"{i}({self.u_value[i]})\t", end="")
        print()
        
    def calculate_determine_cost(self) -> float:
        """计算确定性成本
        
        Returns:
            确定性成本
        """
        determine_cost = 0
        
        # 第一部分：正常需求项
        for i in range(len(self.param.demand)):
            determine_cost += (
                self.param.demand[i] *
                self.cplex.solution.get_value(self.alpha_var[i])
            )
            
        # 第二部分：船舶容量项
        capacitys = self.get_capacity_on_arcs(self.v_var_value)
        for n in range(len(self.param.traveling_arcs_set)):
            determine_cost += (
                capacitys[n] *
                self.cplex.solution.get_value(self.beta_var[n])
            )
            
        # 第三部分：初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                determine_cost += (
                    -self.param.initial_empty_container[pp] *
                    self.cplex.solution.get_value(self.gamma_var[pp][t])
                )
                
        return determine_cost
        
    def calculate_uncertain_cost(self) -> float:
        """计算不确定性成本
        
        Returns:
            不确定性成本
        """
        uncertain_cost = 0
        
        # 不确定需求项
        for i in range(len(self.param.demand)):
            uncertain_cost += (
                self.param.maximum_demand_variation[i] *
                self.cplex.solution.get_value(self.miu_var[i])
            )
            
        return uncertain_cost
        
    def calculate_dual_obj_val(self, v_value: List[List[int]]) -> float:
        """计算对偶目标值
        
        Args:
            v_value: 船舶分配决策变量值
            
        Returns:
            对偶目标值
        """
        dual_obj_val = 0
        
        # 第一部分：正常需求项
        for i in range(len(self.param.demand)):
            dual_obj_val += (
                self.param.demand[i] *
                self.cplex.solution.get_value(self.alpha_var[i])
            )
            
        # 第二部分：船舶容量项
        capacitys = self.get_capacity_on_arcs(v_value)
        for n in range(len(self.param.traveling_arcs_set)):
            dual_obj_val += (
                capacitys[n] *
                self.cplex.solution.get_value(self.beta_var[n])
            )
            
        # 第三部分：初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                dual_obj_val += (
                    -self.param.initial_empty_container[pp] *
                    self.cplex.solution.get_value(self.gamma_var[pp][t])
                )
                
        # 第四部分：不确定需求项
        for i in range(len(self.param.demand)):
            dual_obj_val += (
                self.param.maximum_demand_variation[i] *
                self.cplex.solution.get_value(self.miu_var[i])
            )
            
        return dual_obj_val
    
    def build_model(self):
        """
        构建对偶子问题模型
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
            logger.error(f"Error in building dual sub problem: {str(e)}")
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
        
        # 运力约束对偶变量 beta[n]
        for n in range(self.input_data.arc_num):
            self.beta_var[n] = self.model.addVar(
                vtype="C",
                ub=0,  # beta <= 0
                name=f"beta_{n}"
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
        self.miu_var = [None] * len(self.param.demand)
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
        
        # 第二部分: 运力项
        capacity_term = sum(
            self._get_capacity_on_arc(n) * self.beta_var[n]
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
            demand_term + capacity_term + empty_term,
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
                
                # 添加航段项
                for n in range(self.input_data.arc_num):
                    if self.input_data.arcs[n] in path.arcs:
                        left += self.beta_var[n]
                
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
        
        # 运力约束
        for n in range(self.input_data.arc_num):
            for i in range(self.input_data.request_num):
                for j in range(self.input_data.requests[i].path_num):
                    path = self.input_data.requests[i].paths[j]
                    if self.input_data.arcs[n] in path.arcs:
                        self.model.addConstr(
                            self.beta_var[n] <= 0,
                            name=f"dual_capacity_{n}_{i}_{j}"
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
        self.u_constr[f"uncertain_set"] = self.cplex.add_constraint(
            self.cplex.sum(self.miu_var[i] for i in range(self.input_data.request_num)) <= self.tau,
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
    
    def _get_capacity_on_arc(self, arc_idx: int) -> float:
        """
        计算航段上的运力
        
        Args:
            arc_idx: 航段索引
            
        Returns:
            航段运力
        """
        capacity = 0
        arc = self.input_data.arcs[arc_idx]
        
        for i in range(self.input_data.vessel_num):
            for j in range(self.input_data.route_num):
                if self.v_var_value[i][j] == 1:
                    vessel = self.input_data.vessel_types[i]
                    route = self.input_data.ship_routes[j]
                    if arc in route.arcs:
                        capacity += vessel.capacity
        
        return capacity
    
    def set_dual_decision_vars(self):
        """设置决策变量"""
        
        # 创建辅助变量
        self.lambda_var = {}
        # 创建变量
        for i in range(len(self.param.demand)):
            var_name = f"lambda({i})"
            self.lambda_var[i] = self.cplex.continuous_var(
                lb=0,
                ub=self.param.penalty_cost_for_demand[i],
                name=var_name
            )
    

        # alpha
        
        # beta

        # gamma

        # lambda

        self.build_variables()
            
    
    def set_objectives(self):
        """设置目标函数"""
        self.obj_expr = self.get_obj_expr(self.v_var_value)
        self.objective = self.obj_expr
        self.cplex.maximize(self.obj_expr)
        
    def get_obj_expr(self, v_value: List[List[int]]) -> LinearExpr:
        """获取目标函数表达式
        
        Args:
            v_value: 船舶分配决策变量值
            
        Returns:
            目标函数表达式
        """
        # 确定性目标函数
        obj_expr = self.get_determine_obj(v_value)
        
        # 不确定性目标函数
        for i in range(len(self.param.demand)):
            obj_expr.add_term(
                coeff=self.param.maximum_demand_variation[i],
                dvar=self.lambda_var[i]
            )
            
        return obj_expr
        
    def set_constraints(self):
        """设置约束条件"""
        # 对偶约束
        self.set_constraint1()
        self.set_constraint2()
        self.set_constraint3()
        self.set_constraint4()
        
        # 不确定集约束
        self.set_constraint5()
        
        # 线性化约束
        self.set_constraint6()
        self.set_constraint7()
        self.set_constraint8()
        self.set_constraint9()
        
    def set_constraint1(self):
        """设置约束1"""
        self.set_dual_constraint_x()
        
    def set_constraint2(self):
        """设置约束2"""
        self.set_dual_constraint_y()
        
    def set_constraint3(self):
        """设置约束3"""
        self.set_dual_constraint_z()
        
    def set_constraint4(self):
        """设置约束4"""
        self.set_dual_constraint_g()
        
    def set_constraint5(self):
        """设置约束5: 预算约束"""
        left = self.cplex.linear_expr()
        
        for i in range(len(self.param.demand)):
            left.add_term(
                coeff=1, 
                dvar=self.miu_var[i]
            )
            
        self.u_constr[f"C-U"] = self.cplex.add_constraint(
            left <= self.tau,
            "C-U"
        )
        
    def set_constraint6(self):
        """设置约束6: λ[i] <= α[i]"""
        for i in range(len(self.param.demand)):
            left = self.cplex.linear_expr()
            left.add_term(
                coeff=1, 
                dvar=self.lambda_var[i]
            )
            left.add_term(
                coeff=-1, 
                dvar=self.alpha_var[i]
            )
            self.cplex.add_constraint(left <= 0)
            
    def set_constraint7(self):
        """设置约束7: λ[i] >= α[i] - M*(1-u[i])"""
        for i in range(len(self.param.demand)):
            M = self.param.penalty_cost_for_demand[i]
            left = self.cplex.linear_expr()
            
            left.add_term(
                coeff=1, 
                dvar=self.lambda_var[i]
            )
            left.add_term(
                coeff=-M, 
                dvar=self.miu_var[i]
            )
            left.add_term(
                coeff=-1, 
                dvar=self.alpha_var[i]
            )
            
            self.cplex.add_constraint(left >= -M)
            
    def set_constraint8(self):
        """设置约束8: λ[i] <= u[i]*M"""
        for i in range(len(self.param.demand)):
            M = self.param.penalty_cost_for_demand[i]
            left = self.cplex.linear_expr()
            
            left.add_term(
                coeff=1, 
                dvar=self.lambda_var[i]
            )
            left.add_term(
                coeff=-M, 
                dvar=self.miu_var[i]
            )
            
            self.cplex.add_constraint(left <= 0)
            
    def set_constraint9(self):
        """设置约束9: λ[i] >= -u[i]*M"""
        for i in range(len(self.param.demand)):
            M = self.param.penalty_cost_for_demand[i]
            left = self.cplex.linear_expr()
            
            left.add_term(
                coeff=1, 
                dvar=self.lambda_var[i]
            )
            left.add_term(
                coeff=M, 
                dvar=self.miu_var[i]
            )
            
            self.cplex.add_constraint(left >= 0)
    
    def set_start_scene(self, start_case: List[float]):
        """设置初始场景
        
        Args:
            start_case: 初始场景值
        """
        self.cplex.add_mip_start(self.miu_var, start_case)
        
    def get_u_value_double(self) -> List[float]:
        """获取u值的浮点数形式
        
        Returns:
            u值列表
        """
        return [float(u) for u in self.u_value]
        
    def calculate_dual_obj_val(self, v_value: List[List[int]]) -> float:
        """计算对偶目标值
        
        Args:
            v_value: 船舶分配决策变量值
            
        Returns:
            对偶目标值
        """
        obj_val = self.get_constant_item()
        
        # II. 第二部分: 船舶容量项
        capacitys = self.get_capacity_on_arcs(v_value)
        beta_value = self.get_beta_value()
        for n in range(len(self.param.traveling_arcs_set)):
            obj_val += capacitys[n] * beta_value[n]
            
        return obj_val
        
    def calculate_determine_cost(self) -> float:
        """计算确定性成本
        
        Returns:
            确定性成本值
        """
        cost = 0.0
        
        # I. 第一部分: 正常需求项
        for i in range(len(self.param.demand)):
            cost += self.param.demand[i] * self.cplex.solution.get_value(self.alpha_var[i])
            
        # II. 第二部分: 船舶容量项
        capacitys = self.get_capacity_on_arcs(self.v_var_value)
        for n in range(len(self.param.traveling_arcs_set)):
            cost += capacitys[n] * self.cplex.solution.get_value(self.beta_var[n])
            
        # III. 第三部分: 初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                cost += -self.param.initial_empty_container[pp] * self.cplex.solution.get_value(self.gamma_var[pp][t])
                
        return cost
        
    def calculate_uncertain_cost(self) -> float:
        """计算不确定性成本
        
        Returns:
            不确定性成本值
        """
        cost = 0.0
        for i in range(len(self.param.demand)):
            cost += self.param.maximum_demand_variation[i] * self.cplex.solution.get_value(self.lambda_var[i])
        return cost
        
    def print_solution(self):
        """打印解"""
        logger.info(f"The Worst Case(DSP)(tau = {self.tau}):")
        for i in range(len(self.param.demand)):
            if self.u_value[i] != 0:
                print(f"{i}({self.u_value[i]})\t", end="")
        print() 


    @property
    def tau(self) -> int:
        """对应Java: getTau() 通过@Getter自动生成"""
        return self._tau
    
    @tau.setter
    def tau(self, value: int):
        self._tau = value