import numpy as np
from typing import List, Dict, Any, Tuple
from multi.model.primal.base_primal_model import BasePrimalModel
from multi.utils.default_setting import DefaultSetting
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
    type: str

    def __init__(self, input_data: InputData = None, param: Parameter = None, type: str = "", model: Model = None):
        """初始化主问题
        
        Args:
            input_data: 输入数据
            param: 模型参数
            model: CPLEX模型实例
            type: 问题类型("Reactive"或"Stochastic"或"Robust")
        """
        super().__init__(input_data, param)
        self.type = type
        if input_data is not None and param is not None:
            self.model_name = f"MP-R{len(input_data.ship_route_set)}-T{param.time_horizon}-{self.fleet_type}-S{self.random_seed}"
        else:
            self.model_name = "MP-Undefined"
        try:
            if model is not None:
                self.cplex = model
            else:
                self.cplex = Model()
            self.public_setting(self.cplex)
            self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise
    
            
    def set_decision_vars(self):
        """设置决策变量"""
        # 第一阶段变量
        if self.type == "Reactive":
                self.set_reactive_decision_vars()
        elif self.type == "Stochastic":
                self.set_stochastic_decision_vars()
        else:
            self.set_vessel_decision_vars()
        
        # 辅助决策变量
        self.eta_var = self.cplex.continuous_var(0, float('inf'), name="Eta")
        
    def set_stochastic_auxiliary_decision_vars(self):
        """设置随机辅助决策变量"""
        self.eta_vars = {}
        for k in range(len(self.param.sample_scenes)):
            self.eta_vars[f"Eta{k}"] = self.cplex.continuous_var(0, float('inf'), name=f"Eta{k}")
            
        # 添加连接约束
        left = self.cplex.linear_expr()
        for k in range(len(self.param.sample_scenes)):
            left.add_term(coeff=1.0/len(self.param.sample_scenes), dvar=self.eta_vars[f"Eta{k}"])
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
        self.v_var2 = {}
        for h, vessel in enumerate(self.input_data.vessel_types):
            self.v_var2[h] = {}
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                var_name = f"V({self.param.vessel_set[h]})({self.param.vessel_path_set[w]})"
                self.v_var2[h][w] = self.cplex.binary_var(name=var_name)
        
        # 辅助决策变量
        self.eta_var = self.cplex.continuous_var(0, float('inf'), name="Yita")
        
    def get_v_vars(self) -> List[List]:
        """获取船舶分配变量"""
        return self.vVar
        
    def get_eta_var(self):
        """获取对偶变量"""
        return self.eta_var
        
    def get_eta_vars(self) -> Dict:
        """获取对偶变量列表"""
        return self.eta_vars
        
    def set_objectives(self):
        """设置目标函数"""
                # 第一阶段变量
        if self.type == "Reactive":
                self.set_reactive_objectives()
        else:
            obj = self.cplex.linear_expr()
            # 添加船舶运营成本
            obj = self.get_vessel_operation_cost_obj(obj)
            obj.add_term(coeff=1, dvar=self.eta_var)

            self.objective = obj
            self.cplex.minimize(obj)
        
    def set_reactive_objectives(self):
        """设置反应式目标函数"""
        obj = self.cplex.linear_expr()
        
        obj = self.get_vessel_operation_cost_obj(obj)
        
        # 添加船舶运营成本
        for w, vessel_path in enumerate(self.input_data.vessel_paths):
            r = self.input_data.vessel_path_set[w].route_id - 1
            for h, vessel in enumerate(self.input_data.vessel_types):
                obj.add_term(
                    coeff=self.param.vessel_type_and_ship_route[h][r] *
                    self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                    self.param.vessel_operation_cost[h],
                    dvar=self.v_var2[h][w]
                )
                
        obj.add_term(coeff=1, dvar=self.eta_var)
        
        self.objective = obj
        self.cplex.minimize(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        
        # 每条船舶航线分配一种类型的船舶
        self.set_constraint1()
        
    def set_constraint1(self):
        """设置船舶约束"""
        self.set_vessel_constraint()
        
    def set_constraint0(self, x_var: List[List], y_var: List[List], z_var: List[List], g_var: List):
        """设置切割约束（Benders分解中的割）
        
        数学模型:
        L(x, y, z, g) - η ≤ 0
        其中:
            L(x, y, z, g): 二阶段问题的目标函数表达式
            η: 辅助变量（Benders割）
        对应Java注释:
        /*
        Benders cut constraint
        L(x, y, z, g) - η ≤ 0
        */
        /**
        * 设置Benders分解中的切割约束
        * L(x, y, z, g) - η ≤ 0
        * 其中:
        * L(x, y, z, g): 二阶段目标函数
        * η: 辅助变量
        */
        """
        left = LinearExpr()
        left = self.get_request_trans_cost_obj(left, x_var, y_var, z_var, g_var)
        left.add_term(-1, self.eta_var)
        self.cplex.add_constraint(left <= 0)
        
    def set_constraint4(self, x_var: List[List], y_var: List[List], g_var: List, u_value: List[float]):
        """设置需求约束
        
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
        self.set_demand_constraint(x_var, y_var, g_var, u_value)
        
    def set_constraint5(self, x_var: List[List], y_var: List[List], z_var: List[List]):
        """设置容量约束
        
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
        self.set_capacity_constraint(x_var, y_var, z_var)
        
    def set_constraint5_reactive1(self, x_var: List[List], y_var: List[List]):
        """设置反应式容量约束1
        
        数学模型:
        Σ_i Σ_p (x_ip + y_ip) a_np ≤ Σ_h Σ_w V_hw C_h a_nw, ∀n ∈ N
        其中:
            a_np: 路径p是否使用弧n
            C_h: 船舶类型h的容量
            V_hw: 船舶类型h分配到路径w的二元变量
            x_ip, y_ip: 各类集装箱运输量
        对应Java注释:
        /*
        vessel capacity constraint (reactive)
        /sum{X+Y} <= V
        */
        /**
        * 设置船舶容量约束(反应式)
        * Σ_i Σ_p (x_ip + y_ip) a_np ≤ Σ_h Σ_w V_hw C_h a_nw, ∀n ∈ N
        * 其中:
        * a_np: 路径p是否使用弧n
        * C_h: 船舶类型h的容量
        */
        """
        for nn in range(len(self.param.traveling_arcs_set)):
            left = LinearExpr()
            
            for i in range(len(self.param.demand)):
                od = self.input_data.request_set[i]
                
                for k in range(od.number_of_laden_path):
                    j = od.laden_path_indexes[k]
                    left.add_term(self.param.arc_and_path[nn][j], x_var[i][k])
                    left.add_term(self.param.arc_and_path[nn][j], y_var[i][k])
                    
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                r = self.input_data.vessel_path_set[w].route_id - 1
                for h, vessel in enumerate(self.input_data.vessel_types):
                    left.add_term(
                        coeff=-self.param.vessel_type_and_ship_route[h][r] *
                        self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                        self.param.arc_and_vessel_path[nn][w] *
                        self.param.vessel_capacity[h],
                        dvar=self.vVars[h][r]
                    )
                    
            self.cplex.add_constraint(left <= 0, name=f"C3({nn+1})")
            
    def set_constraint5_reactive2(self, z_var: List[List]):
        """设置反应式容量约束2
        
        数学模型:
        Σ_i Σ_q z_iq a_nq ≤ Σ_h Σ_w V_hw C_h a_nw, ∀n ∈ N
        其中:
            a_nq: 路径q是否使用弧n
            C_h: 船舶类型h的容量
            V_hw: 船舶类型h分配到路径w的二元变量
            z_iq: 空箱运输量
        对应Java注释:
        /*
        vessel capacity constraint (reactive, empty)
        /sum{Z} <= V
        */
        /**
        * 设置船舶容量约束(反应式, 空箱)
        * Σ_i Σ_q z_iq a_nq ≤ Σ_h Σ_w V_hw C_h a_nw, ∀n ∈ N
        * 其中:
        * a_nq: 路径q是否使用弧n
        * C_h: 船舶类型h的容量
        */
        """
        for nn in range(len(self.param.traveling_arcs_set)):
            left = LinearExpr()
            
            for i in range(len(self.param.demand)):
                od = self.input_data.request_set[i]
                
                for k in range(od.number_of_empty_path):
                    j = od.empty_path_indexes[k]
                    left.add_term(
                        coeff=self.param.arc_and_path[nn][j], 
                        dvar=z_var[i][k]
                    )
                    
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                r = self.input_data.vessel_path_set[w].route_id - 1
                for h, vessel in enumerate(self.input_data.vessel_types):
                    left.add_term(
                        coeff=-self.param.vessel_type_and_ship_route[h][r] *
                        self.param.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.vessel_path_id] *
                        self.param.arc_and_vessel_path[nn][w] *
                        self.param.vessel_capacity[h],
                        dvar=self.v_var2[h][w]
                    )
                    
            self.cplex.add_constraint(left <= 0, name=f"C3({nn+1})")
            
    def set_constraint6(self, x_var: List[List], z_var: List[List]):
        """设置空箱平衡约束
        
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
        logger.debug("进入 add_optimality_cut")
        left = self.cplex.linear_expr()
        try:
            logger.debug(f"constant_item={constant_item}, beta_value={beta_value}")
            for n, arc in enumerate(self.input_data.traveling_arcs):
                logger.debug(f"n={n}, arc={arc}")
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    r = vessel_path.route_id - 1
                    logger.debug(f"w={w}, vessel_path={vessel_path}, r={r}")
                    for h, vessel_type in enumerate(self.input_data.vessel_types):
                        logger.debug(f"h={h}, vessel_type={vessel_type}")
                        if self.fleet_type == "Homo":
                            logger.debug(f"add_term: v_var[h][r]={self.vVars[h][r]}")
                            left.add_term(
                                coeff=self.param.arc_and_vessel_path[arc.arc_id][vessel_path.vessel_path_id] *
                                     self.param.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.vessel_path_id] *
                                     self.param.vessel_type_and_ship_route[vessel_type.id][vessel_path.route_id] *
                                     vessel_type.capacity *
                                     beta_value[n],
                                dvar=self.vVars[h][r]
                            )
                        elif self.fleet_type == "Hetero":
                            logger.debug(f"add_term: v_var[h][w]={self.vVars[h][w]}")
                            left.add_term(
                                coeff=self.param.arc_and_vessel_path[arc.arc_id][vessel_path.vessel_path_id] *
                                     vessel_type.capacity *
                                     beta_value[n],
                                dvar=self.vVars[h][w]
                            )
                        else:
                            logger.error("Error in Fleet type!")
            logger.debug("add_term: eta_var")
            left.add_term(
                coeff=-1, 
                dvar=self.eta_var
            )
            logger.debug("add_constraint: left <= -constant_item")
            self.cplex.add_constraint(left <= -constant_item)
            logger.debug("add_optimality_cut 执行完成")
        except Exception as e:
            logger.error(f"Error in add_optimality_cut: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
    def add_feasibility_cut(self, constant_item: float, beta_value: List[float]):
        """添加可行性切割"""
        left = self.cplex.linear_expr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                r = self.input_data.vessel_path_set[w].route_id - 1
                for h, vessel in enumerate(self.input_data.vessel_types):
                    if self.fleet_type == "Homo":
                        left.add_term(
                            coeff=self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.vessel_path_id] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta_value[n],
                            dvar=self.vVars[h][r]
                        )
                    elif self.fleet_type == "Hetero":
                        left.add_term(
                            coeff=self.param.arc_and_vessel_path[n][w] *
                            self.param.vessel_capacity[h] *
                            beta_value[n],
                            dvar=self.vVars[h][w]
                        )
                    else:
                        logger.error("Error in Fleet type!")
                        
        self.cplex.add_constraint(left <= -constant_item)
        
    def add_reactive_optimality_cut(self, constant_item: float, 
                                  beta1_value: List[float], beta2_value: List[float]):
        """添加反应式最优性切割"""
        left = LinearExpr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for r, route in enumerate(self.input_data.shipping_routes):
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    for h, vessel in enumerate(self.input_data.vessel_types):
                        left.add_term(
                            coeff=self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta1_value[n],
                            dvar=self.vVars[h][r]
                        )
                        
                        left.add_term(
                            coeff=self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta2_value[n],
                            dvar=self.v_var2[h][w]
                        )
                        
        left.add_term(
            coeff=-1, 
            dvar=self.eta_var
        )
        self.cplex.add_constraint(left <= -constant_item)
        
    def add_reactive_feasibility_cut(self, constant_item: float,
                                   beta1_value: List[float], beta2_value: List[float]):
        """添加反应式可行性切割"""
        left = LinearExpr()
        
        for n in range(len(self.param.traveling_arcs_set)):
            for r, route in enumerate(self.input_data.shipping_routes):
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    for h, vessel in enumerate(self.input_data.vessel_types):
                        left.add_term(
                            coeff=self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta1_value[n],
                            dvar=self.vVars[h][r]
                        )
                        
                        left.add_term(  
                            coeff=self.param.arc_and_vessel_path[n][w] *
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                            self.param.vessel_type_and_ship_route[h][r] *
                            self.param.vessel_capacity[h] *
                            beta2_value[n],
                            dvar=self.v_var2[h][w]
                        )
                        
        self.cplex.add_constraint(left <= -constant_item)
        
    def solve_model(self):
        """求解模型"""
        try:
            if DefaultSetting.WHETHER_EXPORT_MODEL:
                self.export_model()
                
            start_time = time.time()
            
            if self.cplex.solve():
                end_time = time.time()
                
                self.set_v_var_solution()
                self.set_eta_value(self.eta_var.solution_value)
                self.set_operation_cost(
                    self.cplex.solution.get_objective_value() - 
                    self.eta_var.solution_value
                )
                
                self.obj_val = self.cplex.objective_value
                self.solve_time = end_time - start_time
                self.obj_gap = self.cplex.solve_details.mip_relative_gap
                
                if DefaultSetting.WHETHER_PRINT_VESSEL_DECISION:
                    self.print_mp_solution()
                    
                if DefaultSetting.DEBUG_ENABLE and DefaultSetting.MASTER_ENABLE:
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
            if DefaultSetting.WHETHER_EXPORT_MODEL:
                self.export_model()
                
            start_time = time.time()
            
            if self.cplex.solve():
                end_time = time.time()
                self.set_v_vars_solution()
                
                vvv2 = np.zeros((len(self.param.vessel_set), 
                               len(self.param.vessel_path_set)), dtype=int)
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    for h, vessel in enumerate(self.input_data.vessel_types):
                        tolerance = self.cplex.parameters.mip.tolerances.integrality
                        if self.cplex.solution.get_value(self.v_var2[h][w]) >= 1 - tolerance:
                            vvv2[h][w] = 1
                            
                self.set_v_var_value2(vvv2)
                
                self.set_eta_value(self.eta_var.solution_value)
                self.set_obj_val(self.cplex.solution.get_objective_value())
                self.set_operation_cost(
                    self.cplex.solution.get_objective_value() - 
                    self.eta_var.solution_value
                )
                self.set_obj_gap(self.cplex.solve_details.mip_relative_gap)
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
        for w, vessel_path in enumerate(self.input_data.vessel_paths):
            for h, vessel in enumerate(self.input_data.vessel_types):
                if self.v_var_value2[h][w] != 0:
                    print(f"{self.param.vessel_path_set[w]}({self.param.vessel_set[h]})\t", end="") 