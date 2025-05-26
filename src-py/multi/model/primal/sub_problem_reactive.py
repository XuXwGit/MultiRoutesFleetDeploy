import logging
import cplex
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.base_primal_model import BasePrimalModel

logger = logging.getLogger(__name__)

class SubProblemReactive(BasePrimalModel):
    """
    反应式子问题模型类
    
    用于求解反应式子问题,包括:
    1. 决策变量
    2. 目标函数
    3. 约束条件
    
    主要变量:
    1. x[i][j]: 需求i在路径j上运输的自有集装箱数量
    2. y[i][j]: 需求i在路径j上运输的租赁集装箱数量
    3. z[i][j]: 需求i在路径j上调运的空集装箱数量
    4. g[i]: 需求i未满足的数量
    
    主要约束:
    1. 需求约束
    2. 运力约束(两组)
    3. 空箱量约束
    """
    
    def __init__(self, in_data: InputData, p: Parameter):
        """
        初始化反应式子问题模型
        
        Args:
            in_data: 输入数据
            p: 模型参数
        """
        super().__init__(in_data, p)
        self.model_name = f"SPR-R{in_data.ship_route_num}-T{p.time_horizon}-{DefaultSetting.FLEET_TYPE}-S{DefaultSetting.RANDOM_SEED}"
        self.v_var_value1 = [[0 for _ in range(p.shipping_route_num)] for _ in range(p.vessel_num)]  # 第一组v变量值
        self.v_var_value2 = [[0 for _ in range(p.vessel_path_num)] for _ in range(p.vessel_num)]  # 第二组v变量值
        self.u_value = [0 for _ in range(p.demand_num)]  # 不确定需求变量值
        self.laden_cost = 0  # 重箱运输成本
        self.empty_cost = 0  # 空箱运输成本
        self.penalty_cost = 0  # 需求未满足惩罚成本
        self.rental_cost = 0  # 集装箱租赁成本
        
        # 约束
        self.c1 = None  # 需求约束
        self.c2_1 = None  # 运力约束(第一组)
        self.c2_2 = None  # 运力约束(第二组)
        self.c3 = None  # 空箱量约束
    
    def build_model(self):
        """
        构建反应式子问题模型
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
            logger.error(f"Error in building reactive sub problem: {str(e)}")
            raise
    
    def _create_variables(self):
        """
        创建决策变量
        """
        # 需求i在路径j上运输的自有集装箱数量 x[i][j]
        self.x_var = {}
        for i in range(self.input_data.request_num):
            self.x_var[i] = {}
            for j in range(self.input_data.requests[i].path_num):
                self.x_var[i][j] = self.model.addVar(
                    vtype="C",
                    lb=0,
                    name=f"x_{i}_{j}"
                )
        
        # 需求i在路径j上运输的租赁集装箱数量 y[i][j]
        self.y_var = {}
        for i in range(self.input_data.request_num):
            self.y_var[i] = {}
            for j in range(self.input_data.requests[i].path_num):
                self.y_var[i][j] = self.model.addVar(
                    vtype="C",
                    lb=0,
                    name=f"y_{i}_{j}"
                )
        
        # 需求i在路径j上调运的空集装箱数量 z[i][j]
        self.z_var = {}
        for i in range(self.input_data.request_num):
            self.z_var[i] = {}
            for j in range(self.input_data.requests[i].empty_path_num):
                self.z_var[i][j] = self.model.addVar(
                    vtype="C",
                    lb=0,
                    name=f"z_{i}_{j}"
                )
        
        # 需求i未满足的数量 g[i]
        self.g_var = {}
        for i in range(self.input_data.request_num):
            self.g_var[i] = self.model.addVar(
                vtype="C",
                lb=0,
                name=f"g_{i}"
            )
    
    def _create_objective(self):
        """
        创建目标函数
        """
        # 第一部分: 需求未满足惩罚成本
        penalty_term = sum(
            self.p.penalty_cost_for_demand[i] * self.g_var[i]
            for i in range(self.input_data.request_num)
        )
        
        # 第二部分: 重箱运输成本
        laden_term = sum(
            self.p.laden_path_cost[j] * (self.x_var[i][k] + self.y_var[i][k])
            for i in range(self.input_data.request_num)
            for k in range(self.input_data.requests[i].path_num)
            for j in [self.input_data.requests[i].path_indexes[k]]
        )
        
        # 第三部分: 空箱运输成本
        empty_term = sum(
            self.p.empty_path_cost[j] * self.z_var[i][k]
            for i in range(self.input_data.request_num)
            for k in range(self.input_data.requests[i].empty_path_num)
            for j in [self.input_data.requests[i].empty_path_indexes[k]]
        )
        
        # 第四部分: 集装箱租赁成本
        rental_term = sum(
            self.p.rental_cost * self.p.travel_time_on_path[j] * self.y_var[i][k]
            for i in range(self.input_data.request_num)
            for k in range(self.input_data.requests[i].path_num)
            for j in [self.input_data.requests[i].path_indexes[k]]
        )
        
        # 设置目标函数
        self.model.setObjective(
            penalty_term + laden_term + empty_term + rental_term,
            sense="minimize"
        )
    
    def _create_constraints(self):
        """
        创建约束条件
        """
        # 需求约束
        self._create_demand_constraints()
        
        # 运力约束(第一组)
        self._create_capacity_constraints1()
        
        # 运力约束(第二组)
        self._create_capacity_constraints2()
        
        # 空箱量约束
        self._create_empty_container_constraints()
    
    def _create_demand_constraints(self):
        """
        创建需求约束
        """
        self.c1 = {}
        for i in range(self.input_data.request_num):
            # 构建约束左端
            left = sum(
                self.x_var[i][k] + self.y_var[i][k]
                for k in range(self.input_data.requests[i].path_num)
            )
            left += self.g_var[i]
            
            # 添加约束
            self.c1[i] = self.model.addConstr(
                left == self.p.demand[i] + self.p.max_demand_variation[i] * self.u_value[i],
                name=f"demand_{i}"
            )
    
    def _create_capacity_constraints1(self):
        """创建运力约束(第一组)
        
        数学模型:
        Σ_i Σ_p (x_ip + y_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
        其中:
            a_np: 路径p是否使用弧n
            C_h: 船舶类型h的容量
            V_hr: 船舶类型h分配到航线r的二元变量
            x_ip, y_ip: 各类集装箱运输量
        对应Java注释:
        /*
        vessel capacity constraint (reactive)
        /sum{X+Y} <= V
        */
        /**
        * 设置船舶容量约束(反应式)
        * Σ_i Σ_p (x_ip + y_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
        * 其中:
        * a_np: 路径p是否使用弧n
        * C_h: 船舶类型h的容量
        */
        """
        self.c2_1 = {}
        for n in range(self.input_data.arc_num):
            # 构建约束左端
            left = sum(
                self.p.arc_and_path[n][j] * (self.x_var[i][k] + self.y_var[i][k])
                for i in range(self.input_data.request_num)
                for k in range(self.input_data.requests[i].path_num)
                for j in [self.input_data.requests[i].path_indexes[k]]
            )
            
            # 计算航段运力
            capacity = 0
            for w in range(self.input_data.vessel_path_num):
                r = self.input_data.vessel_paths[w].route_id - 1
                for h in range(self.input_data.vessel_num):
                    capacity += (
                        self.p.arc_and_vessel_path[n][w] *
                        self.p.ship_route_and_vessel_path[r][w] *
                        self.p.vessel_type_and_ship_route[h][r] *
                        self.p.vessel_capacity[h] *
                        self.v_var_value1[h][r]
                    )
            
            # 添加约束
            self.c2_1[n] = self.model.addConstr(
                left <= capacity,
                name=f"capacity1_{n}"
            )
    
    def _create_capacity_constraints2(self):
        """创建运力约束(第二组)
        
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
        self.c2_2 = {}
        for n in range(self.input_data.arc_num):
            # 构建约束左端
            left = sum(
                self.p.arc_and_path[n][j] * self.z_var[i][k]
                for i in range(self.input_data.request_num)
                for k in range(self.input_data.requests[i].empty_path_num)
                for j in [self.input_data.requests[i].empty_path_indexes[k]]
            )
            
            # 计算航段运力
            capacity = 0
            for w in range(self.input_data.vessel_path_num):
                r = self.input_data.vessel_paths[w].route_id - 1
                for h in range(self.input_data.vessel_num):
                    capacity += (
                        self.p.arc_and_vessel_path[n][w] *
                        self.p.ship_route_and_vessel_path[r][w] *
                        self.p.vessel_type_and_ship_route[h][r] *
                        self.p.vessel_capacity[h] *
                        self.v_var_value2[h][w]
                    )
            
            # 添加约束
            self.c2_2[n] = self.model.addConstr(
                left <= capacity,
                name=f"capacity2_{n}"
            )
    
    def _create_empty_container_constraints(self):
        """
        创建空箱量约束
        """
        self.c3 = {}
        for p in range(self.input_data.port_num):
            self.c3[p] = {}
            for t in range(1, self.input_data.time_horizon + 1):
                # 构建约束左端
                left = 0
                
                # 输入流
                for i in range(self.input_data.request_num):
                    # 空箱输入
                    if self.input_data.ports[p] == self.p.origin_of_demand[i]:
                        for k in range(self.input_data.requests[i].empty_path_num):
                            j = self.input_data.requests[i].empty_path_indexes[k]
                            for n in range(self.input_data.arc_num):
                                if (
                                    self.input_data.arcs[n].destination_port == self.input_data.ports[p] and
                                    1 <= self.input_data.arcs[n].destination_time <= t
                                ):
                                    left += self.p.arc_and_path[n][j] * self.z_var[i][k]
                    
                    # 重箱输入
                    if self.input_data.ports[p] == self.p.destination_of_demand[i]:
                        for k in range(self.input_data.requests[i].path_num):
                            j = self.input_data.requests[i].path_indexes[k]
                            for n in range(self.input_data.arc_num):
                                if (
                                    self.input_data.arcs[n].destination_port == self.input_data.ports[p] and
                                    1 <= self.input_data.arcs[n].destination_time <= t - self.p.turnover_time[p]
                                ):
                                    left += self.p.arc_and_path[n][j] * self.x_var[i][k]
                
                # 输出流
                for i in range(self.input_data.request_num):
                    # 重箱输出
                    if self.input_data.ports[p] == self.p.origin_of_demand[i]:
                        for k in range(self.input_data.requests[i].path_num):
                            j = self.input_data.requests[i].path_indexes[k]
                            for n in range(self.input_data.arc_num):
                                if (
                                    self.input_data.arcs[n].origin_port == self.input_data.ports[p] and
                                    1 <= self.input_data.arcs[n].origin_time <= t
                                ):
                                    left -= self.p.arc_and_path[n][j] * self.x_var[i][k]
                    
                    # 空箱输出
                    for k in range(self.input_data.requests[i].empty_path_num):
                        j = self.input_data.requests[i].empty_path_indexes[k]
                        for n in range(self.input_data.arc_num):
                            if (
                                self.input_data.arcs[n].origin_port == self.input_data.ports[p] and
                                1 <= self.input_data.arcs[n].origin_time <= t
                            ):
                                left -= self.p.arc_and_path[n][j] * self.z_var[i][k]
                
                # 添加约束
                self.c3[p][t] = self.model.addConstr(
                    left >= -self.p.initial_empty_container[p],
                    name=f"empty_{p}_{t}"
                )
    
    def solve_model(self):
        """
        求解反应式子问题
        """
        try:
            # 求解模型
            self.model.optimize()
            
            # 获取求解状态
            self.solve_status = self.model.getStatus()
            
            # 如果求解成功,获取结果
            if self.solve_status == "Optimal":
                # 获取目标函数值
                self.obj_val = self.model.getObjective().getValue()
                
                # 获取MIP间隙
                self.mip_gap = self.model.getMIPGap()
                
                # 计算各项成本
                self._calculate_costs()
                
                logger.info(f"Reactive sub problem solved successfully. Objective value: {self.obj_val}")
            else:
                logger.warning(f"Reactive sub problem not solved to optimality. Status: {self.solve_status}")
            
        except Exception as e:
            logger.error(f"Error in solving reactive sub problem: {str(e)}")
            raise
    
    def _calculate_costs(self):
        """
        计算各项成本
        """
        # 重箱运输成本
        self.laden_cost = sum(
            self.p.laden_path_cost[j] * (self.x_var[i][k].x + self.y_var[i][k].x)
            for i in range(self.input_data.request_num)
            for k in range(self.input_data.requests[i].path_num)
            for j in [self.input_data.requests[i].path_indexes[k]]
        )
        
        # 空箱运输成本
        self.empty_cost = sum(
            self.p.empty_path_cost[j] * self.z_var[i][k].x
            for i in range(self.input_data.request_num)
            for k in range(self.input_data.requests[i].empty_path_num)
            for j in [self.input_data.requests[i].empty_path_indexes[k]]
        )
        
        # 需求未满足惩罚成本
        self.penalty_cost = sum(
            self.p.penalty_cost_for_demand[i] * self.g_var[i].x
            for i in range(self.input_data.request_num)
        )
        
        # 集装箱租赁成本
        self.rental_cost = sum(
            self.p.rental_cost * self.p.travel_time_on_path[j] * self.y_var[i][k].x
            for i in range(self.input_data.request_num)
            for k in range(self.input_data.requests[i].path_num)
            for j in [self.input_data.requests[i].path_indexes[k]]
        )
    
    def change_constraint_coefficients(self, v_value1: List[List[int]], v_value2: List[List[int]], u_value: List[int]):
        """
        修改约束系数
        
        Args:
            v_value1: 新的第一组v变量值
            v_value2: 新的第二组v变量值
            u_value: 新的不确定需求变量值
        """
        self.v_var_value1 = v_value1
        self.v_var_value2 = v_value2
        self.u_value = u_value
        
        # 更新需求约束
        for i in range(self.input_data.request_num):
            self.c1[i].rhs = self.p.demand[i] + self.p.max_demand_variation[i] * self.u_value[i]
        
        # 更新运力约束(第一组)
        for n in range(self.input_data.arc_num):
            capacity = 0
            for w in range(self.input_data.vessel_path_num):
                r = self.input_data.vessel_paths[w].route_id - 1
                for h in range(self.input_data.vessel_num):
                    capacity += (
                        self.p.arc_and_vessel_path[n][w] *
                        self.p.ship_route_and_vessel_path[r][w] *
                        self.p.vessel_type_and_ship_route[h][r] *
                        self.p.vessel_capacity[h] *
                        self.v_var_value1[h][r]
                    )
            self.c2_1[n].rhs = capacity
        
        # 更新运力约束(第二组)
        for n in range(self.input_data.arc_num):
            capacity = 0
            for w in range(self.input_data.vessel_path_num):
                r = self.input_data.vessel_paths[w].route_id - 1
                for h in range(self.input_data.vessel_num):
                    capacity += (
                        self.p.arc_and_vessel_path[n][w] *
                        self.p.ship_route_and_vessel_path[r][w] *
                        self.p.vessel_type_and_ship_route[h][r] *
                        self.p.vessel_capacity[h] *
                        self.v_var_value2[h][w]
                    )
            self.c2_2[n].rhs = capacity
        
        # 更新模型
        self.model.update()

    def frame(self):
        """构建模型框架"""
        self.set_decision_vars()
        self.set_objectives()
        self.set_constraints()
        
    def set_decision_vars(self):
        """设置决策变量"""
        self.set_request_decision_vars()
        
    def set_objectives(self):
        """设置目标函数"""
        obj = self.cplex.linear_expr()
        
        # 添加集装箱运输成本
        for i in range(len(self.param.demand)):
            # 添加需求未满足惩罚成本
            obj.add_term(coeff=self.param.penalty_cost_for_demand[i], dvar=self.gVars[i])
            
            request = self.input_data.requests[i]
            # 添加重箱运输成本
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                obj.add_term(coeff=self.param.laden_path_cost[j], dvar=self.xVar[i][k])
                obj.add_term(coeff=self.param.laden_path_cost[j], dvar=self.yVars[i][k])
                obj.add_term(coeff=self.param.rental_cost * self.param.travel_time_on_path[j], dvar=self.yVars[i][k])
                
            # 添加空箱运输成本
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                obj.add_term(coeff=self.param.empty_path_cost[j], dvar=self.zVars[i][k])
                
        self.cplex.objective.set_sense(self.cplex.objective.sense.minimize)
        self.cplex.objective.set_linear(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        self.set_constraint1()  # 需求满足约束
        self.set_constraint2()  # 容量约束
        self.set_constraint3()  # 流量平衡约束
        
    def set_constraint1(self):
        """设置需求满足约束: 运输量必须满足需求"""
        self.C1 = {}
        for i in range(len(self.param.demand)):
            expr = self.cplex.linear_expr()
            request = self.input_data.requests[i]
            
            # 添加重箱运输量
            for k in range(request.number_of_laden_path):
                expr.add_term(1.0, self.xVar[i][k])
                expr.add_term(1.0, self.yVars[i][k])
                
            # 添加需求未满足量
            expr.add_term(1.0, self.gVars[i])
            
            # 添加约束
            self.C1[i] = self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["E"],
                rhs=[self.param.demand[i]],
                names=[f"C1_{i}"]
            )[0]
            
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
        self.C2 = {}
        for n in range(len(self.param.traveling_arcs_set)):
            expr = self.cplex.linear_expr()
            # 添加所有运输量
            for i in range(len(self.param.demand)):
                request = self.input_data.requests[i]
                # 添加重箱运输量
                for k in range(request.number_of_laden_path):
                    j = request.laden_path_indexes[k]
                    if self.param.arc_and_path[n][j] == 1:
                        expr.add_term(1.0, self.xVar[i][k])
                        expr.add_term(1.0, self.yVars[i][k])
                # 添加空箱运输量
                for k in range(request.number_of_empty_path):
                    j = request.empty_path_indexes[k]
                    if self.param.arc_and_path[n][j] == 1:
                        expr.add_term(1.0, self.zVars[i][k])
            # 添加船舶容量(基于主问题解)
            for h, vessel in enumerate(self.input_data.vessel_types):
                for r, route in enumerate(self.input_data.shipping_routes):
                    for w, vessel_path in enumerate(self.input_data.vessel_paths):
                        if (self.param.arc_and_vessel_path[n][w] == 1 and
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and
                            self.param.vessel_type_and_ship_route[h][r] == 1):
                            expr.add_term(-self.param.vessel_capacity[h] * self.v_var_value1[h][r], 1.0)
            # 添加约束
            self.C2[n] = self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["L"],
                rhs=[0.0],
                names=[f"C2_{n}"]
            )[0]
            
    def set_constraint3(self):
        """设置流量平衡约束: 每个节点的流入量等于流出量"""
        self.C3 = {}
        for p in range(len(self.param.port_set)):
            self.C3[p] = {}
            for t in range(1, len(self.param.time_point_set)):
                expr = self.cplex.linear_expr()
                
                # 添加初始空箱量
                expr.add_term(1.0, self.param.initial_empty_container[p])
                
                # 添加空箱运输量
                for i in range(len(self.param.demand)):
                    request = self.input_data.requests[i]
                    for k in range(request.number_of_empty_path):
                        j = request.empty_path_indexes[k]
                        if (self.param.port_and_path[p][j] == 1 and
                            self.param.time_and_path[t][j] == 1):
                            expr.add_term(-1.0, self.zVars[i][k])
                            
                # 添加约束
                self.C3[p][t] = self.cplex.linear_constraints.add(
                    lin_expr=[expr],
                    senses=["E"],
                    rhs=[0.0],
                    names=[f"C3_{p}_{t}"]
                )[0]
                
    def print_solution(self):
        """打印求解结果"""
        if self.solve_status == "optimal":
            logger.info("Optimal solution found!")
            logger.info(f"Objective value: {self.obj_val:.2f}")
            logger.info("Cost breakdown:")
            logger.info(f"Laden cost: {self.laden_cost:.2f}")
            logger.info(f"Empty cost: {self.empty_cost:.2f}")
            logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
            logger.info(f"Rental cost: {self.rental_cost:.2f}")
        else:
            logger.info(f"No optimal solution found. Status: {self.solve_status}") 