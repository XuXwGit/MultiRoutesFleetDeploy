import logging
import time
from docplex.mp.model import Model
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.base_primal_model import BasePrimalModel

logger = logging.getLogger(__name__)

class DetermineModel(BasePrimalModel):
    """确定性模型类
    
    基于均值需求的确定性优化模型
    
    数学模型特点:
    1. 使用需求均值E[ξ]代替随机变量ξ
    2. 目标函数: 最小化总运营成本
       min Σ_h Σ_r c_hr V_hr + Σ_a (c_x x_a + c_x1 x1_a + c_y y_a + c_z z_a)
    3. 约束条件:
       - 船舶分配约束 Σ_h V_hr = 1
       - 流量平衡约束
       - 容量约束
       - 需求满足约束
    
    其中:
    c_hr: 船舶类型h在航线r上的运营成本
    V_hr: 船舶分配决策变量
    c_x, c_x1, c_y, c_z: 各类集装箱的单位成本
    x_a, x1_a, y_a, z_a: 各类集装箱的运输量
    """
    
    def __init__(self, in_data: InputData, param: Parameter, model_type: str = "UseMeanValue"):
        """
        初始化确定性模型
        
        Args:
            in_data: 输入数据
            p: 模型参数
            model_type: 模型类型，默认为"UseMeanValue"
        """
        self.input_data = in_data
        self.param = param

        # 设置模型属性
        self.model_str = "DM"
        self.model_type = model_type
        self.model_name = (f"{self.model_str}-R{len(self.input_data.ship_route_set)}"
                         f"-T{self.param.time_horizon}"
                         f"-{DefaultSetting.FLEET_TYPE}"
                         f"-S{DefaultSetting.RANDOM_SEED}"
                         f"-V{DefaultSetting.VESSEL_CAPACITY_RANGE}")
        if model_type != "UseMeanValue":
            self.model_name += f"-{model_type}"

        self.initialize()

    def solve(self):
        """求解模型"""
        start_time = time.time()
        self.solve_model()
        solve_time = time.time() - start_time
        logger.info(f"SolveTime = {solve_time:.2f}")
        
        if DefaultSetting.WHETHER_CALCULATE_MEAN_PERFORMANCE:
            self.calculate_mean_performance()

    
    def initialize(self):
        """初始化模型"""
        if DefaultSetting.WHETHER_PRINT_PROCESS or DefaultSetting.WHETHER_PRINT_ITERATION:
            logger.info("=========DetermineModel==========")
        try:
            self.cplex = Model(name=self.model_name)
            self.public_setting(self.cplex)
            start_time = time.time()
            self.frame()
            build_time = time.time() - start_time
            logger.info(f"BuildTime = {build_time:.2f}")
        except Exception as e:
            logger.error(f"Error initializing BaseModel: {str(e)}")
            raise

        
    def frame(self):
        """构建模型框架"""
        self.build_model()

    def build_model(self):
        """构建模型"""
        self.set_decision_vars()
        self.set_objectives()
        self.set_constraints()
        
    def set_decision_vars(self):
        """设置决策变量"""
        # 设置船舶分配决策变量
        self.set_vessel_decision_vars()
            
        # 设置请求决策变量
        self.set_request_decision_vars()
        
    def set_objectives(self):
        """设置目标函数"""
        obj = self.cplex.linear_expr()
        
        # 添加船舶运营成本
        obj = self.get_vessel_operation_cost_obj(obj)
        
        # 添加集装箱运输成本
        obj = self.get_request_trans_cost_obj(obj)
                
        self.cplex.minimize(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        logger.info("=========Setting Vessel Allocation Constraint Start==========")
        self.set_constraint0()  # 船舶分配约束
        logger.info("=========Setting Vessel Allocation Constraint End==========")

        logger.info("=========Setting Demand Constraint Start==========")
        self.set_constraint1()  # 需求满足约束
        logger.info("=========Setting Demand Constraint End==========")

        logger.info("=========Setting Capacity Constraint Start==========")
        self.set_constraint2()  # 容量约束
        logger.info("=========Setting Capacity Constraint End==========")

        logger.info("=========Setting Empty Conservation Constraint Start==========")
        self.set_constraint3()  # 流量平衡约束
        logger.info("=========Setting Empty Conservation Constraint End==========")
        
    def set_constraint0(self):
        """设置船舶分配约束: 每条航线必须分配一艘船舶"""
        for r, route in enumerate(self.input_data.shipping_routes):
            expr = self.cplex.linear_expr()
            for h, vessel in enumerate(self.input_data.vessel_types):
                expr.add_term(coeff=1.0, dvar=self.vVars[h][r])
            self.cplex.add_constraint(expr == 1.0, f"C0_{r}")
            
    def set_constraint1(self):
        """设置需求满足约束: 运输量必须满足需求
        
        数学模型:
        Σ_p (x_ip + y_ip) + g_i = d_i, ∀i ∈ I
        其中:
            d_i: 需求量
            g_i: 需求未满足量
            x_ip, y_ip: 各类集装箱运输量
        对应Java注释:
        /*
        demand satisfaction constraint
        /sum{X+Y}+g = d
        */
        /**
        * 设置需求满足约束
        * Σ_p (x_ip + y_ip) + g_i = d_i, ∀i ∈ I
        * 其中:
        * d_i: 需求量
        * g_i: 需求未满足量
        */
        """
        self.set_demand_constraint()
        
            
    def set_constraint2(self):
        """设置容量约束: 运输量不能超过船舶容量
        
        数学模型:
        Σ_i Σ_p (x_ip + y_ip + z_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
        其中:
            a_np: 路径p是否使用弧n
            C_h: 船舶类型h的容量
            V_hr: 船舶类型h分配到航线r的二元变量
            x_ip, y_ip, z_ip: 各类集装箱运输量
        对应Java注释:
        /*
        vessel capacity constraint
        /sum{X+Y+Z} <= V
        */
        /**
        * 设置船舶容量约束(对应数学模型中式8)
        * Σ_i Σ_p (x_ip + y_ip + z_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
        * 其中:
        * a_np: 路径p是否使用弧n
        * C_h: 船舶类型h的容量
        */
        """
        self.set_capacity_constraint()
            
    def set_constraint3(self):
        """设置流量平衡约束: 每个节点的流入量等于流出量
        
        数学模型:
        初始空箱量 + Σ_输入流 - Σ_输出流 = 0, ∀p ∈ P, t ∈ T
        其中:
            p: 港口
            t: 时间点
            输入流/输出流: 各类集装箱的流入/流出
        对应Java注释:
        /*
        empty container conservation constraint
        inflow - outflow = initial
        */
        /**
        * 设置空箱守恒约束
        * 初始空箱量 + Σ_输入流 - Σ_输出流 = 0, ∀p ∈ P, t ∈ T
        */
        """
        self.set_empty_conservation_constraint()
        
                
    def calculate_mean_performance(self):
        """计算平均性能指标"""
        # TODO: 实现平均性能计算
        pass

    def solve_reactive_model(self):
        """
        求解响应式模型
        """
        try:
            # 求解模型
            self.cplex.solve()
            
            # 获取求解状态
            self.solve_status = self.cplex.solution.get_status()
            
            # 如果求解成功,获取结果
            if self.solve_status == "optimal":
                # 获取目标函数值
                self.obj_val = self.cplex.solution.get_objective_value()
                
                # 获取船舶分配变量值
                self.vVar_value = [
                    [self.vVars[h][r].solution_value for r in range(len(self.param.shipping_route_set))]
                    for h, vessel in enumerate(self.input_data.vessel_types)
                ]
                
                # 获取第二次船舶分配变量值
                self.vVar_value2 = [
                    [self.vVars[h][r].solution_value for r in range(len(self.param.shipping_route_set))]
                    for h, vessel in enumerate(self.input_data.vessel_types)
                ]
                
                # 获取期望成本变量值
                self.eta_value = self.eta_var.solution_value
                
                # 计算运营成本
                self.operation_cost = sum(
                    self.param.vessel_operation_cost[h] * self.vVar_value[h][r]
                    for h, vessel in enumerate(self.input_data.vessel_types)
                    for r in range(len(self.param.shipping_route_set))
                )
                
                logger.info(f"Determine model solved successfully. Objective value: {self.obj_val}")
            else:
                logger.warning(f"Determine model not solved to optimality. Status: {self.solve_status}")
            
        except Exception as e:
            logger.error(f"Error in solving determine model: {str(e)}")
            raise
    
    def add_scene(self, scene: Dict[str, Any]):
        """
        添加新场景
        
        数学模型:
        对于每个新场景r:
        Σ_k y_{rk} - scene_x_r = 0
        其中:
            y_{rk}: 场景r下的决策变量
            scene_x_r: 场景r的辅助变量
        对应Java注释:
        /*
        scenario extension constraint
        /sum{y_{rk}} - scene_x_r = 0
        */
        /**
        * 添加场景扩展约束
        * Σ_k y_{rk} - scene_x_r = 0
        * 其中:
        * y_{rk}: 场景r下的决策变量
        * scene_x_r: 场景r的辅助变量
        */
        """
        try:
            # 添加场景相关变量
            scene_vars = {}
            for r in range(len(self.param.demand)):
                scene_vars[r] = self.cplex.binary_var(name=f"scene_x_{r}")
            # 添加场景相关约束
            for r in range(len(self.param.demand)):
                expr = self.cplex.linear_expr()
                for k in range(len(self.param.shipping_route_set)):
                    expr.add_term(coeff=1.0, dvar=self.yVars[r][k])
                expr.add_term(coeff=-1.0, dvar=scene_vars[r])
                self.cplex.linear_constraints.add(
                    lin_expr=[expr],
                    senses=["E"],
                    rhs=[0.0],
                    names=[f"scene_request_satisfaction_{r}"]
                )
            # 更新目标函数
            scene_cost = sum(
                scene["request"][r].cost * scene_vars[r]
                for r in range(len(self.param.demand))
            )
            self.cplex.objective.set_linear(
                self.cplex.linear_expr() + scene_cost
            )
        except Exception as e:
            logger.error(f"Error in adding scene to determine model: {str(e)}")
            raise
    
    def get_solution(self) -> Dict[str, Any]:
        """
        获取模型解
        
        Returns:
            模型解信息
        """
        return {
            "vVar_value": self.vVar_value,
            "vVar_value2": self.vVar_value2,
            "eta_value": self.eta_value,
            "operation_cost": self.operation_cost,
            "obj_val": self.obj_val
        } 