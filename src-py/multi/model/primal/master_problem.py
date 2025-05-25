import numpy as np
from typing import List, Dict, Any, Tuple
from multi.model.primal.base_primal_model import BasePrimalModel
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.entity.scenario import Scenario
import logging
import time
from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr

logger = logging.getLogger(__name__)

class MasterProblem(BasePrimalModel):
    """主问题类
    
    实现了Benders分解中的主问题:
    1. 变量定义
    2. 约束构建
    3. 目标函数构建
    4. 求解方法
    """
    
    def __init__(self, model: Model, input_data: InputData, param: Parameter):
        """初始化主问题
        
        Args:
            model: CPLEX模型实例
            input_data: 输入数据
            param: 模型参数
        """
        super().__init__()
        self.in_data = input_data
        self.param = param
        self.model_name = f"MP-R{len(input_data.ship_route_set)}-T{param.time_horizon}-{self.fleet_type}-S{self.random_seed}"
        
        try:
            self.cplex = model
            self.public_setting(self.cplex)
            self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise
            
    def __init__(self, input_data: InputData, param: Parameter):
        """初始化主问题(无模型实例)
        
        Args:
            input_data: 输入数据
            param: 模型参数
        """
        super().__init__()
        self.in_data = input_data
        self.param = param
        self.model_name = f"MP-R{len(input_data.ship_route_set)}-T{param.time_horizon}-{self.fleet_type}-S{self.random_seed}"
        
        try:
            self.cplex = Model()
            self.public_setting(self.cplex)
            self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise
            
    def __init__(self, input_data: InputData, param: Parameter, type: str):
        """初始化主问题(指定类型)
        
        Args:
            input_data: 输入数据
            param: 模型参数
            type: 问题类型("Reactive"或"Stochastic")
        """
        super().__init__()
        self.in_data = input_data
        self.param = param
        
        try:
            if type == "Reactive":
                self.cplex = Model()
                self.public_setting(self.cplex)
                self.set_reactive_decision_vars()
                self.set_reactive_objectives()
                self.set_constraints()
            elif type == "Stochastic":
                self.cplex = Model()
                self.public_setting(self.cplex)
                self.set_stochastic_decision_vars()
                self.set_objectives()
                self.set_constraints()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise
            
    def set_decision_vars(self):
        """设置决策变量"""
        # 第一阶段变量
        self.set_vessel_decision_vars()
        
        # 辅助决策变量
        self.eta_var = self.cplex.continuous_var(0, float('inf'), name="Eta")
        
    def set_stochastic_auxiliary_decision_vars(self):
        """设置随机辅助决策变量"""
        self.eta_vars = []
        for k in range(len(self.param.sample_scenes)):
            self.eta_vars.append(
                self.cplex.continuous_var(0, float('inf'), name=f"Eta{k}")
            )
            
        # 添加连接约束
        left = LinearExpr()
        for k in range(len(self.param.sample_scenes)):
            left.add_term(1.0/len(self.param.sample_scenes), self.eta_vars[k])
        self.cplex.add_constraint(self.eta_var == left)
        
    def set_stochastic_decision_vars(self):
        """设置随机决策变量"""
        self.set_decision_vars()
        self.set_stochastic_auxiliary_decision_vars()
        
    def set_reactive_decision_vars(self):
        """设置反应式决策变量"""
        # 第一阶段变量
        self.set_vessel_decision_vars()
        
        # 第一阶段变量
        self.v_var2 = []
        for h in range(len(self.param.vessel_set)):
            row = []
            for w in range(len(self.param.vessel_path_set)):
                var_name = f"V({self.param.vessel_set[h]})({self.param.vessel_path_set[w]})"
                row.append(self.cplex.binary_var(name=var_name))
            self.v_var2.append(row)
            
        # 辅助决策变量
        self.eta_var = self.cplex.continuous_var(0, float('inf'), name="Yita")
        
    def get_v_vars(self) -> List[List]:
        """获取船舶分配变量"""
        return self.v_var
        
    def get_eta_var(self):
        """获取对偶变量"""
        return self.eta_var
        
    def get_eta_vars(self) -> List:
        """获取对偶变量列表"""
        return self.eta_vars
        
    def set_objectives(self):
        """设置目标函数"""
        obj = LinearExpr()
        
        # 添加船舶运营成本
        obj = self.get_vessel_operation_cost_obj(obj)
        
        obj.add_term(1, self.eta_var)
        
        self.cplex.minimize(obj)
        
    def set_reactive_objectives(self):
        """设置反应式目标函数"""
        obj = LinearExpr()
        
        obj = self.get_vessel_operation_cost_obj(obj)
        
        # 添加船舶运营成本
        for w in range(len(self.param.vessel_path_set)):
            r = self.in_data.vessel_path_set[w].route_id - 1
            for h in range(len(self.param.vessel_set)):
                obj.add_term(
                    self.param.vessel_type_and_ship_route[h][r] *
                    self.param.ship_route_and_vessel_path[r][w] *
                    self.param.vessel_operation_cost[h],
                    self.v_var2[h][w]
                )
                
        obj.add_term(1, self.eta_var)
        
        self.cplex.minimize(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        # 每条船舶航线分配一种类型的船舶
        self.set_constraint1()
        
    def set_constraint1(self):
        """设置船舶约束"""
        self.set_vessel_constraint()
        
    def set_constraint0(self, x_var: List[List], y_var: List[List], 
                       z_var: List[List], g_var: List):
        """设置切割约束"""
        left = LinearExpr()
        
        left = self.get_request_trans_cost_obj(left, x_var, y_var, z_var, g_var)
        
        left.add_term(-1, self.eta_var)
        
        self.cplex.add_constraint(left <= 0)
        
    def set_constraint4(self, x_var: List[List], y_var: List[List], 
                       g_var: List, u_value: List[float]):
        """设置需求约束"""
        self.set_demand_constraint(x_var, y_var, g_var, u_value)
        
    def set_constraint5(self, x_var: List[List], y_var: List[List], 
                       z_var: List[List]):
        """设置容量约束"""
        self.set_capacity_constraint(x_var, y_var, z_var)
        
    def set_constraint5_reactive1(self, x_var: List[List], y_var: List[List]):
        """设置反应式容量约束1"""
        for nn in range(len(self.param.traveling_arcs_set)):
            left = LinearExpr()
            
            for i in range(len(self.param.demand)):
                od = self.in_data.request_set[i]
                
                for k in range(od.number_of_laden_path):
                    j = od.laden_path_indexes[k]
                    left.add_term(self.param.arc_and_path[nn][j], x_var[i][k])
                    left.add_term(self.param.arc_and_path[nn][j], y_var[i][k])
                    
            for w in range(len(self.param.vessel_path_set)):
                r = self.in_data.vessel_path_set[w].route_id - 1
                for h in range(len(self.param.vessel_set)):
                    left.add_term(
                        -self.param.vessel_type_and_ship_route[h][r] *
                        self.param.ship_route_and_vessel_path[r][w] *
                        self.param.arc_and_vessel_path[nn][w] *
                        self.param.vessel_capacity[h],
                        self.v_var[h][r]
                    )
                    
            self.cplex.add_constraint(left <= 0, name=f"C3({nn+1})")
            
    def set_constraint5_reactive2(self, z_var: List[List]):
        """设置反应式容量约束2"""
        for nn in range(len(self.param.traveling_arcs_set)):
            left = LinearExpr()
            
            for i in range(len(self.param.demand)):
                od = self.in_data.request_set[i]
                
                for k in range(od.number_of_empty_path):
                    j = od.empty_path_indexes[k]
                    left.add_term(self.param.arc_and_path[nn][j], z_var[i][k])
                    
            for w in range(len(self.param.vessel_path_set)):
                r = self.in_data.vessel_path_set[w].route_id - 1
                for h in range(len(self.param.vessel_set)):
                    left.add_term(
                        -self.param.vessel_type_and_ship_route[h][r] *
                        self.param.ship_route_and_vessel_path[r][w] *
                        self.param.arc_and_vessel_path[nn][w] *
                        self.param.vessel_capacity[h],
                        self.v_var2[h][w]
                    )
                    
            self.cplex.add_constraint(left <= 0, name=f"C3({nn+1})")
            
    def set_constraint6(self, x_var: List[List], z_var: List[List]):
        """设置空箱平衡约束"""
        self.set_empty_conservation_constraint(x_var, z_var, 1)
        
    def set_eta_value(self, eta_value: float):
        """设置对偶变量值"""
        self.eta_value = eta_value
        
    def add_scene(self, scene_k: Scenario):
        """添加场景"""
        # 第二阶段变量
        xx_var_k = []
        yy_var_k = []
        zz_var_k = []
        g_var_k = []
        
        self.set_request_decision_vars(xx_var_k, yy_var_k, zz_var_k, g_var_k)
        
        request = scene_k.request
        
        self.set_constraint0(xx_var_k, yy_var_k, zz_var_k, g_var_k)
        self.set_constraint4(xx_var_k, yy_var_k, g_var_k, request)
        self.set_constraint5(xx_var_k, yy_var_k, zz_var_k)
        self.set_constraint6(xx_var_k, zz_var_k)
        
    def add_reactive_scene(self, scene_k: Scenario):
        """添加反应式场景"""
        xx_var_k = []
        yy_var_k = []
        zz_var_k = []
        g_var_k = []
        
        self.set_request_decision_vars(xx_var_k, yy_var_k, zz_var_k, g_var_k)
        
        request = scene_k.request
        
        self.set_constraint0(xx_var_k, yy_var_k, zz_var_k, g_var_k)
        self.set_constraint4(xx_var_k, yy_var_k, g_var_k, request)
        self.set_constraint5_reactive1(xx_var_k, yy_var_k)
        self.set_constraint5_reactive2(zz_var_k)
        self.set_constraint6(xx_var_k, zz_var_k)
        
    def add_optimality_cut(self, constant_item: float, beta_value: List[float]):
        """添加最优性切割"""
        left = LinearExpr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for w in range(len(self.param.vessel_path_set)):
                r = self.in_data.vessel_path_set[w].route_id - 1
                for h in range(len(self.param.vessel_set)):
                    if self.fleet_type == "Homo":
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta_value[n],
                            self.v_var[h][r]
                        )
                    elif self.fleet_type == "Hetero":
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.vessel_capacity[h] *
                            beta_value[n],
                            self.v_var[h][w]
                        )
                    else:
                        logger.error("Error in Fleet type!")
                        
        left.add_term(-1, self.eta_var)
        self.cplex.add_constraint(left <= -constant_item)
        
    def add_feasibility_cut(self, constant_item: float, beta_value: List[float]):
        """添加可行性切割"""
        left = LinearExpr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for w in range(len(self.param.vessel_path_set)):
                r = self.in_data.vessel_path_set[w].route_id - 1
                for h in range(len(self.param.vessel_set)):
                    if self.fleet_type == "Homo":
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta_value[n],
                            self.v_var[h][r]
                        )
                    elif self.fleet_type == "Hetero":
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.vessel_capacity[h] *
                            beta_value[n],
                            self.v_var[h][w]
                        )
                    else:
                        logger.error("Error in Fleet type!")
                        
        self.cplex.add_constraint(left <= -constant_item)
        
    def add_reactive_optimality_cut(self, constant_item: float, 
                                  beta1_value: List[float], beta2_value: List[float]):
        """添加反应式最优性切割"""
        left = LinearExpr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for r in range(len(self.param.shipping_route_set)):
                for w in range(len(self.param.vessel_path_set)):
                    for h in range(len(self.param.vessel_set)):
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta1_value[n],
                            self.v_var[h][r]
                        )
                        
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta2_value[n],
                            self.v_var2[h][w]
                        )
                        
        left.add_term(-1, self.eta_var)
        self.cplex.add_constraint(left <= -constant_item)
        
    def add_reactive_feasibility_cut(self, constant_item: float,
                                   beta1_value: List[float], beta2_value: List[float]):
        """添加反应式可行性切割"""
        left = LinearExpr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for r in range(len(self.param.shipping_route_set)):
                for w in range(len(self.param.vessel_path_set)):
                    for h in range(len(self.param.vessel_set)):
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta1_value[n],
                            self.v_var[h][r]
                        )
                        
                        left.add_term(
                            self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta2_value[n],
                            self.v_var2[h][w]
                        )
                        
        self.cplex.add_constraint(left <= -constant_item)
        
    def solve_model(self):
        """求解模型"""
        try:
            if self.whether_export_model:
                self.export_model()
                
            start_time = time.time()
            
            if self.cplex.solve():
                end_time = time.time()
                
                self.set_v_vars_solution()
                self.set_eta_value(self.cplex.get_value(self.eta_var))
                self.set_operation_cost(
                    self.cplex.get_objective_value() - 
                    self.cplex.get_value(self.eta_var)
                )
                
                self.set_obj_val(self.cplex.get_objective_value())
                self.set_solve_time(end_time - start_time)
                self.set_obj_gap(self.cplex.get_mip_relative_gap())
                
                if self.whether_print_vessel_decision:
                    self.print_mp_solution()
                    
                if self.debug_enable and self.master_enable:
                    logger.info("-" * 72)
                    logger.info(f"SolveTime = {self.get_solve_time()}")
                    self.print_mp_solution()
                    logger.info("-" * 72)
            else:
                logger.info("MasterProblem No solution")
                
        except Exception as e:
            logger.error(f"Concert Error: {str(e)}")
            
    def solve_reactive_model(self):
        """求解反应式模型"""
        try:
            if self.whether_export_model:
                self.export_model()
                
            start_time = time.time()
            
            if self.cplex.solve():
                end_time = time.time()
                self.set_v_vars_solution()
                
                vvv2 = np.zeros((len(self.param.vessel_set), 
                               len(self.param.vessel_path_set)), dtype=int)
                for w in range(len(self.param.vessel_path_set)):
                    for h in range(len(self.param.vessel_set)):
                        tolerance = self.cplex.parameters.mip.tolerances.integrality
                        if self.cplex.get_value(self.v_var2[h][w]) >= 1 - tolerance:
                            vvv2[h][w] = 1
                            
                self.set_v_var_value2(vvv2)
                
                self.set_eta_value(self.cplex.get_value(self.eta_var))
                self.set_obj_val(self.cplex.get_objective_value())
                self.set_operation_cost(
                    self.cplex.get_objective_value() - 
                    self.cplex.get_value(self.eta_var)
                )
                self.set_obj_gap(self.cplex.get_mip_relative_gap())
                self.set_solve_time(end_time - start_time)
                
                if self.debug_enable and self.master_enable:
                    logger.info("-" * 72)
                    logger.info(f"SolveTime = {self.get_solve_time()}")
                    self.print_mp_solution()
                    logger.info("-" * 72)
            else:
                logger.info("MasterProblem No solution")
                
        except Exception as e:
            logger.error(f"Concert Error: {str(e)}")
            
    def get_v_var_value2(self) -> np.ndarray:
        """获取船舶分配变量值2"""
        return self.v_var_value2
        
    def set_v_var_value2(self, v_var_value2: np.ndarray):
        """设置船舶分配变量值2"""
        self.v_var_value2 = v_var_value2
        
    def get_eta_value(self) -> float:
        """获取对偶变量值"""
        return self.eta_value
        
    def print_mp_solution(self):
        """打印主问题解"""
        logger.info(f"Master Objective = {self.get_obj_val():.2f}")
        logger.info(f"Mp-OperationCost = {self.get_operation_cost():.2f}")
        logger.info(f"Mp-OtherCost = {self.get_eta_value():.2f}")
        self.print_solution()
        
    def print_reactive_solution(self):
        """打印反应式解"""
        print("V[h][w] : ", end="")
        for w in range(len(self.param.vessel_path_set)):
            for h in range(len(self.param.vessel_set)):
                if self.v_var_value2[h][w] != 0:
                    print(f"{self.param.vessel_path_set[w]}({self.param.vessel_set[h]})\t", end="") 