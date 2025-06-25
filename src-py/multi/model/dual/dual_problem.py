import numpy as np
from typing import List, Dict, Any, Tuple
from multi.model.dual.base_dual_model import BaseDualModel
from multi.utils.parameter import Parameter
from multi.utils.input_data import InputData
from multi.utils.default_setting import DefaultSetting
from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import logging
from dataclasses import dataclass
from multi.entity.request import Request
import threading
import time

# 配置日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class DualProblem(BaseDualModel):
    """对偶问题类
    
    实现了对偶问题的主要功能:
    1. 变量定义
    2. 约束构建
    3. 目标函数构建
    4. 求解方法
    """
    
    def __init__(self, input_data: InputData, param: Parameter, v_value: List[List[int]], u_value: List[float]):
        """初始化对偶问题
        
        Args:
            input_data: 输入数据
            param: 模型参数
            v_value: 船舶分配决策变量值
            u_value: 需求变化系数
        """
        super().__init__(input_data, param)
        
        # 设置模型名称
        self.model_name = f"DP-R{len(input_data.ship_route_set)}-T{param.time_horizon}-{DefaultSetting.FLEET_TYPE}-S{DefaultSetting.RANDOM_SEED}"
        
        # 决策变量值
        self.v_var_value = v_value
        self.u_value = u_value
        
        # 创建CPLEX模型
        try:
            self.cplex = Model(name=self.model_name)
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
            
            # 设置约束
            self.set_dual_constraint_x()
            self.set_dual_constraint_y()
            self.set_dual_constraint_z()
            self.set_dual_constraint_g()
            
            # 设置目标函数
            self.objective = self.get_obj_expr(self.v_var_value, self.u_value)
            self.cplex.set_objective("max", self.objective)
            
        except Exception as e:
            logger.error(f"Error in building model: {str(e)}")
            raise
            
    def solve_model(self):
        """求解对偶问题"""
        try:
            if DefaultSetting.WHETHER_EXPORT_MODEL:
                self.export_model()
                
            start_time = time.time()
            if self.cplex.solve():
                end_time = time.time()
                
                self.set_obj_val(self.cplex.objective_value)
                self.set_solve_time(end_time - start_time)
                self.set_obj_gap(self.cplex.solve_details.mip_relative_gap)
                
                if DefaultSetting.DEBUG_ENABLE and DefaultSetting.DUAL_ENABLE:
                    logger.info("------------------------------------------------------------------------")
                    logger.info(f"SolveTime = {end_time - start_time}ms")
                    logger.info(f"DP-Obj = {self.get_obj_val():.2f}")
                    self.print_solution()
                    logger.info("------------------------------------------------------------------------")
            else:
                logger.info("DualProblem No Solution")
        except Exception as e:
            logger.error(f"Error in solving model: {str(e)}")
            
    def print_solution(self):
        """打印解"""
        logger.info(f"The Worst Case(DP)(tau = {self.tau}):")
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
        
        # 需求变化项
        for i in range(len(self.param.demand)):
            uncertain_cost += (
                self.param.maximum_demand_variation[i] *
                self.u_value[i] *
                self.cplex.solution.get_value(self.alpha_var[i])
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
                
        # 第四部分：需求变化项
        for i in range(len(self.param.demand)):
            dual_obj_val += (
                self.param.maximum_demand_variation[i] *
                self.u_value[i] *
                self.cplex.solution.get_value(self.alpha_var[i])
            )
            
        return dual_obj_val 