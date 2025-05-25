import cplex
from typing import List, Dict
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.base_primal_model import BasePrimalModel

class SubProblem(BasePrimalModel):
    """子问题模型类
    
    用于求解给定主问题解下的第二阶段问题
    
    数学模型特点:
    1. 目标函数: 最小化第二阶段运营成本
       min Σ_a (c_x x_a + c_x1 x1_a + c_y y_a + c_z z_a) + Σ_i p_i u_i
    2. 约束条件:
       - 流量平衡约束
       - 容量约束(基于主问题解)
       - 需求满足约束(允许缺货u_i)
    
    其中:
    c_x, c_x1, c_y, c_z: 各类集装箱的单位成本
    x_a, x1_a, y_a, z_a: 各类集装箱的运输量
    p_i: 需求点i的缺货惩罚成本
    u_i: 需求点i的缺货量
    """
    
    def __init__(self, in_data: InputData, param: Parameter, v_var_value: List[List[int]] = None):
        """初始化子问题模型
        
        Args:
            in_data: 输入数据(网络结构、需求等)
            param: 模型参数(成本系数、容量等)
            v_var_value: 主问题的船舶分配解
        """
        super().__init__(in_data, param)
        self.model_name = (f"SP-R{len(in_data.ship_route_set)}"
                         f"-T{param.time_horizon}"
                         f"-{DefaultSetting.FleetType}"
                         f"-S{DefaultSetting.randomSeed}")
        
        # 存储主问题的船舶分配解
        if v_var_value is None:
            if DefaultSetting.FleetType == "Homo":
                self.v_var_value = [[0] * len(param.shipping_route_set) for _ in range(len(param.vessel_set))]
            elif DefaultSetting.FleetType == "Hetero":
                self.v_var_value = [[0] * len(param.vessel_path_set) for _ in range(len(param.vessel_set))]
            else:
                raise ValueError("Error in Fleet type!")
        else:
            self.v_var_value = v_var_value
            
        # 存储需求未满足量
        self.u_value = [0.0] * len(param.demand)
        
        # 成本指标
        self.total_cost = 0.0  # 总成本
        self.laden_cost = 0.0  # 重箱运输成本
        self.empty_cost = 0.0  # 空箱运输成本
        self.penalty_cost = 0.0  # 需求未满足惩罚成本
        self.rental_cost = 0.0  # 集装箱租赁成本
        
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
            obj.add_term(self.param.penalty_cost_for_demand[i], self.gVar[i])
            
            request = self.input_data.request_set[i]
            # 添加重箱运输成本
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                obj.add_term(self.param.laden_path_cost[j], self.xVar[i][k])
                obj.add_term(self.param.laden_path_cost[j], self.yVar[i][k])
                obj.add_term(self.param.rental_cost * self.param.travel_time_on_path[j], self.yVar[i][k])
                
            # 添加空箱运输成本
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                obj.add_term(self.param.empty_path_cost[j], self.zVar[i][k])
                
        self.cplex.objective.set_sense(self.cplex.objective.sense.minimize)
        self.cplex.objective.set_linear(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        self.set_constraint1()  # 需求满足约束
        self.set_constraint2()  # 容量约束
        self.set_constraint3()  # 流量平衡约束
        
    def set_constraint1(self):
        """设置需求满足约束: 运输量必须满足需求"""
        self.C1 = []
        for i in range(len(self.param.demand)):
            expr = self.cplex.linear_expr()
            request = self.input_data.request_set[i]
            
            # 添加重箱运输量
            for k in range(request.number_of_laden_path):
                expr.add_term(1.0, self.xVar[i][k])
                expr.add_term(1.0, self.yVar[i][k])
                
            # 添加需求未满足量
            expr.add_term(1.0, self.gVar[i])
            
            # 添加约束
            self.C1.append(self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["E"],
                rhs=[self.param.demand[i]],
                names=[f"C1_{i}"]
            )[0])
            
    def set_constraint2(self):
        """设置容量约束: 运输量不能超过船舶容量"""
        self.C2 = []
        for n in range(len(self.param.traveling_arcs_set)):
            expr = self.cplex.linear_expr()
            
            # 添加所有运输量
            for i in range(len(self.param.demand)):
                request = self.input_data.request_set[i]
                
                # 添加重箱运输量
                for k in range(request.number_of_laden_path):
                    j = request.laden_path_indexes[k]
                    if self.param.arc_and_path[n][j] == 1:
                        expr.add_term(1.0, self.xVar[i][k])
                        expr.add_term(1.0, self.yVar[i][k])
                        
                # 添加空箱运输量
                for k in range(request.number_of_empty_path):
                    j = request.empty_path_indexes[k]
                    if self.param.arc_and_path[n][j] == 1:
                        expr.add_term(1.0, self.zVar[i][k])
                        
            # 添加船舶容量(基于主问题解)
            for h in range(len(self.param.vessel_set)):
                for r in range(len(self.param.shipping_route_set)):
                    for w in range(len(self.param.vessel_path_set)):
                        if (self.param.arc_and_vessel_path[n][w] == 1 and
                            self.param.ship_route_and_vessel_path[r][w] == 1 and
                            self.param.vessel_type_and_ship_route[h][r] == 1):
                            expr.add_term(-self.param.vessel_capacity[h] * self.v_var_value[h][r], 1.0)
                            
            # 添加约束
            self.C2.append(self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["L"],
                rhs=[0.0],
                names=[f"C2_{n}"]
            )[0])
            
    def set_constraint3(self):
        """设置流量平衡约束: 每个节点的流入量等于流出量"""
        self.C3 = []
        for p in range(len(self.param.port_set)):
            self.C3.append([])
            for t in range(1, len(self.param.time_point_set)):
                expr = self.cplex.linear_expr()
                
                # 添加初始空箱量
                expr.add_term(1.0, self.param.initial_empty_container[p])
                
                # 添加空箱运输量
                for i in range(len(self.param.demand)):
                    request = self.input_data.request_set[i]
                    for k in range(request.number_of_empty_path):
                        j = request.empty_path_indexes[k]
                        if (self.param.port_and_path[p][j] == 1 and
                            self.param.time_and_path[t][j] == 1):
                            expr.add_term(-1.0, self.zVar[i][k])
                            
                # 添加约束
                self.C3[p].append(self.cplex.linear_constraints.add(
                    lin_expr=[expr],
                    senses=["E"],
                    rhs=[0.0],
                    names=[f"C3_{p}_{t}"]
                )[0])
                
    def get_dual_objective(self) -> float:
        """获取对偶目标函数值
        
        Returns:
            对偶目标函数值
        """
        dual_obj = 0.0
        
        # I. 第一部分: sum(normal_demand * alpha + max_var_demand*u*alpha)
        for i in range(len(self.param.demand)):
            dual_obj += self.param.demand[i] * self.cplex.solution.get_dual(self.C1[i])
            dual_obj += (self.param.maximum_demand_variation[i] *
                        self.u_value[i] *
                        self.cplex.solution.get_dual(self.C1[i]))
            
        # II. 第二部分: sum(vessel_capacity * V[h][r] * beta[arc])
        for n in range(len(self.param.traveling_arcs_set)):
            for r in range(len(self.param.shipping_route_set)):
                for w in range(len(self.param.vessel_path_set)):
                    for h in range(len(self.param.vessel_set)):
                        if (self.param.arc_and_vessel_path[n][w] == 1 and
                            self.param.ship_route_and_vessel_path[r][w] == 1 and
                            self.param.vessel_type_and_ship_route[h][r] == 1):
                            dual_obj += (self.param.arc_and_vessel_path[n][w] *
                                       self.param.ship_route_and_vessel_path[r][w] *
                                       self.param.vessel_type_and_ship_route[h][r] *
                                       self.param.vessel_capacity[h] *
                                       self.v_var_value[h][r] *
                                       self.cplex.solution.get_dual(self.C2[n]))
                            
        # III. 第三部分: 初始空箱量约束的对偶值
        for p in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                dual_obj += (self.param.initial_empty_container[p] *
                           self.cplex.solution.get_dual(self.C3[p][t]))
                
        return dual_obj
        
    def print_path_allocation_solutions(self):
        """打印路径分配解"""
        for i in range(len(self.param.demand)):
            print(f"Request {i}: ", end="")
            request = self.input_data.request_set[i]
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                print(f"X[{i}][{j}] = {self.cplex.solution.get_values(self.xVar[i][k])}\t"
                      f"Y[{i}][{j}] = {self.cplex.solution.get_values(self.yVar[i][k])}") 