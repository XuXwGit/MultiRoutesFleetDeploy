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
    
    def __init__(self, input_data: InputData, param: Parameter, v_var_value: List[List[int]] = None):
        """初始化子问题模型
        
        模型名示例: SP-R{航线数}-T{时间周期}-{船队类型}-S{随机种子}
        
        Args:
            input_data: 输入数据(网络结构、需求等)
            param: 模型参数(成本系数、容量等)
            v_var_value: 主问题的船舶分配解
        """
        super().__init__(input_data, param)

        self.initialize()

        self.model_name = (f"SP-R{len(input_data.ship_route_set)}"
                         f"-T{param.time_horizon}"
                         f"-{DefaultSetting.FLEET_TYPE}"
                         f"-S{DefaultSetting.RANDOM_SEED}")
        
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
        obj = self.get_request_trans_cost_obj(obj)

        self.cplex.minimize(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        self.set_constraint1()  # 需求满足约束
        self.set_constraint2()  # 容量约束
        self.set_constraint3()  # 流量平衡约束
        
    def set_constraint1(self):
        """设置需求满足约束: 运输量必须满足需求"""

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
        self.C2 = {}

        capacities = self.get_capacity_on_arcs(self.v_var_value)
        for n, arc in enumerate(self.input_data.traveling_arcs):
            expr = self.cplex.linear_expr()
            expr = self.accumulate_trans_on_arc(arc, expr)

            rhs_val = capacities[n]
            self.capacity_rhs_vars[n] = self.cplex.continuous_var(lb=rhs_val, ub=rhs_val, name=f"capacity_rhs_{n}")
            expr.add_term(coeff=-1.0, dvar=self.capacity_rhs_vars[n])
            self.C2[f"C2_{n}"] = self.cplex.add_constraint(expr <= 0.0, f"C2_{n}")
            
    def set_constraint3(self):
        """设置流量平衡约束: 每个节点的流入量等于流出量
        """

        self.set_empty_conservation_constraint()
                
    def get_dual_objective(self) -> float:
        """获取对偶目标函数值
        
        Returns:
            对偶目标函数值
        """
        dual_obj = 0.0
        
        # I. 第一部分: sum(normal_demand * alpha + max_var_demand*u*alpha)
        for i in range(len(self.param.demand)):
            dual_obj += self.param.demand[i] * self.cplex.solution.get_dual(self.C1[f"C1_{i}"])
            dual_obj += (self.param.maximum_demand_variation[i] *
                        self.u_value[i] *
                        self.cplex.solution.get_dual(self.C1[f"C1_{i}"]))
            
        # II. 第二部分: sum(vessel_capacity * V[h][r] * beta[arc])
        for n, arc in enumerate(self.input_data.traveling_arcs):
            for r, route in enumerate(self.input_data.shipping_routes):
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    for h, vessel_type in enumerate(self.input_data.vessel_types):
                        if (self.param.arc_and_vessel_path[arc.id][vessel_path.id] == 1 and
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and
                            self.param.vessel_type_and_ship_route[vessel_type.id][route.id] == 1):
                            dual_obj += (self.param.arc_and_vessel_path[arc.id][vessel_path.id] *
                                       self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                                       self.param.vessel_type_and_ship_route[vessel_type.id][route.id] *
                                       self.param.vessel_capacity[h] *
                                       self.v_var_value[h][r] *
                                       self.cplex.solution.get_dual(self.C2[f"C2_{n}"]))
                            
        # III. 第三部分: 初始空箱量约束的对偶值
        for p in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                dual_obj += (self.param.initial_empty_container[p] *
                           self.cplex.solution.get_dual(self.C3[f"C3_{p}"][t]))
                
        return dual_obj
        
    def print_path_allocation_solutions(self):
        """打印路径分配解
        
        输出每个请求的重箱运输变量X、Y的分配结果
        """
        for i in range(len(self.param.demand)):
            print(f"Request {i}: ", end="")
            request = self.input_data.requests[i]
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                print(f"X[{i}][{j}] = {self.cplex.solution.get_values(self.xVars[i][k])}\t"
                      f"Y[{i}][{j}] = {self.cplex.solution.get_values(self.yVars[i][k])}")

    def solve_model(self):
        """求解模型并保存解
        
        对应Java: solveModel
        """
        try:
            self.cplex.solve()
            self.set_detail_cost()
        except Exception as e:
            print(f"SubProblem No solution: {e}")

    def set_detail_cost(self):
        """分解并保存各项成本
        
        对应Java: setDetailCost
        """
        total_laden_cost = 0.0
        total_empty_cost = 0.0
        total_rental_cost = 0.0
        total_penalty_cost = 0.0
        try:
            for i, request in enumerate(self.input_data.requests):
                # 需求未满足惩罚成本
                total_penalty_cost += request.penalty_cost * self.cplex.solution.get_value(self.gVars[i])
                for k, laden_path in enumerate(request.laden_paths):
                    j = laden_path.path_id
                    if "x" in self.xs:
                        total_laden_cost += laden_path.cost * self.cplex.solution.get_value(self.xs["x"][i][k])
                    if "x1" in self.xs:
                        total_laden_cost += laden_path.cost * self.cplex.solution.get_value(self.xs["x1"][i][k])
                    if "y" in self.xs:
                        total_laden_cost += laden_path.cost * self.cplex.solution.get_value(self.xs["y"][i][k])
                    if "z1" in self.xs:
                        total_empty_cost += laden_path.empty_path_cost * self.cplex.solution.get_value(self.xs["z1"][i][k])
                    if "z2" in self.xs:
                        total_empty_cost += (laden_path.empty_path_cost +15) * self.cplex.solution.get_value(self.xs["z2"][i][k])
                for k, empty_path in enumerate(request.empty_paths):
                    j = empty_path.path_id
                    if "z" in self.xs:
                        total_empty_cost += empty_path.empty_path_cost * self.cplex.solution.get_value(self.xs["z"][i][k])
        except Exception as e:
            print(f"SubProblem setDetailCost error: {e}")

        self.laden_cost = total_laden_cost
        self.empty_cost = total_empty_cost
        self.rental_cost = total_rental_cost
        self.penalty_cost = total_penalty_cost
        self.total_cost = total_laden_cost + total_empty_cost + total_rental_cost + total_penalty_cost

    def write_solution(self, filename: str):
        """写出解到文件
        
        对应Java: writeSolution
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for i, request in enumerate(self.input_data.request_set):
                total_request_cost = 0.0
                f.write(f"Request{i}({request.origin_port}->{request.destination_port})({self.param.demand[i]}):\n\t")
                f.write(f"LadenContainerPath({request.number_of_laden_path}):")
                for k in range(request.number_of_laden_path):
                    x_val = self.cplex.solution.get_values(self.xVars[i][k])
                    y_val = self.cplex.solution.get_values(self.yVars[i][k])
                    if x_val != 0 or y_val != 0:
                        f.write(f"{k}({self.param.laden_path_cost[k]}x{x_val:.2f}+{(self.param.rental_cost*self.param.travel_time_on_path[k]+self.param.laden_path_cost[k])}x{y_val:.2f})")
                    total_request_cost += self.param.laden_path_cost[k]*x_val + (self.param.laden_path_cost[k]+self.param.rental_cost*self.param.travel_time_on_path[k])*y_val
                f.write("\t")
                g_val = self.cplex.solution.get_values(self.gVars[i])
                f.write(f"Unfulfilled: {self.param.penalty_cost_for_demand[i]}x{g_val:.2f}\t\t")
                total_request_cost += self.param.penalty_cost_for_demand[i]*g_val
                f.write(f"EmptyContainerPath({request.number_of_empty_path}):\t")
                for k in range(request.number_of_empty_path):
                    z_val = self.cplex.solution.get_values(self.zVars[i][k])
                    if z_val != 0:
                        f.write(f"{k}({self.param.empty_path_cost[k]}x{z_val:.2f})")
                    total_request_cost += self.param.empty_path_cost[k]*z_val
                f.write(f"\ttotalRequestCost = {total_request_cost}\n")

    def write_dual_solution(self, filename: str):
        """写出对偶解到文件
        
        对应Java: writeDualSolution
        """
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("Alpha : \n")
            for i in range(len(self.param.demand)):
                f.write(f"alpha[{i}] = {self.cplex.solution.get_dual(self.C1[f'C1_{i}'])}\n")
            f.write("Beta : \n")
            for n, arc in enumerate(self.input_data.traveling_arcs):
                f.write(f"beta[{n}] = {self.cplex.solution.get_dual(self.C2[f'C2_{n}'])}\n")
            f.write("Gamma : \n")
            for p in range(len(self.param.port_set)):
                for t in range(1, len(self.param.time_point_set)):
                    f.write(f"gamma[{p}][{t}] = {self.cplex.solution.get_dual(self.C3[f'C3_{p}'][t])}\n")

    def write_port_containers(self, filename: str):
        """写出端口空箱量到文件
        
        对应Java: writePortContainers
        """
        Lpt = [[0 for _ in range(len(self.param.time_point_set))] for _ in range(len(self.param.port_set))]
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("TimePoint\t" + "\t".join([str(port) for port in self.input_data.port_set]) + "\n")
            for t in range(len(self.param.time_point_set)):
                f.write(f"{t}\t")
                for p in range(len(self.input_data.port_set)):
                    if t == 0:
                        Lpt[p][t] = self.param.initial_empty_container[p]
                    else:
                        Lpt[p][t] = Lpt[p][t-1]
                        for i in range(len(self.param.demand)):
                            request = self.input_data.requests[i]
                            # Input Z flow
                            if self.input_data.port_set[p] == self.param.origin_of_demand[i]:
                                for k in range(request.number_of_empty_path):
                                    j = request.empty_path_indexes[k]
                                    for n, arc in enumerate(self.input_data.traveling_arcs):
                                        arc = self.input_data.traveling_arc_set[n]
                                        if arc.destination_port == self.input_data.port_set[p] and arc.destination_time == t:
                                            Lpt[p][t] += self.param.arc_and_path[n][j] * self.cplex.solution.get_values(self.zVars[i][k])
                            # Input X flow
                            if self.input_data.port_set[p] == self.param.destination_of_demand[i]:
                                for k in range(request.number_of_laden_path):
                                    j = request.laden_path_indexes[k]
                                    for n, arc in enumerate(self.input_data.traveling_arcs):
                                        arc = self.input_data.traveling_arc_set[n]
                                        if arc.destination_port == self.input_data.port_set[p] and arc.destination_time == t - self.param.turn_over_time[p]:
                                            Lpt[p][t] += self.param.arc_and_path[n][j] * self.cplex.solution.get_values(self.xVars[i][k])
                            # Output X flow
                            if self.input_data.port_set[p] == self.param.origin_of_demand[i]:
                                for k in range(request.number_of_laden_path):
                                    j = request.laden_path_indexes[k]
                                    for n, arc in enumerate(self.input_data.traveling_arcs):
                                        arc = self.input_data.traveling_arc_set[n]
                                        if arc.origin_port == self.input_data.port_set[p] and arc.origin_time == t:
                                            Lpt[p][t] -= self.param.arc_and_path[n][j] * self.cplex.solution.get_values(self.xVars[i][k])
                            # Output Z flow
                            for k in range(request.number_of_empty_path):
                                j = request.empty_path_indexes[k]
                                for n, arc in enumerate(self.input_data.traveling_arcs):
                                    arc = self.input_data.traveling_arc_set[n]
                                    if arc.origin_port == self.input_data.port_set[p] and arc.origin_time == t:
                                        Lpt[p][t] -= self.param.arc_and_path[n][j] * self.cplex.solution.get_values(self.zVars[i][k])
                    f.write(f"{Lpt[p][t]}\t")
                f.write("\n")

    def change_demand_constraint_coefficients(self, u_value):
        """动态调整需求约束右端项"""
        self.u_value = u_value
        for i in range(len(self.param.demand)):
            new_rhs = self.param.demand[i] + self.param.maximum_demand_variation[i] * u_value[i]
            self.demand_rhs_vars[i].lb = new_rhs
            self.demand_rhs_vars[i].ub = new_rhs

    def change_capacity_constraint_coefficients(self, v_var_value):
        """动态调整容量约束右端项"""
        self.v_var_value = v_var_value
        capacitys = self.get_capacity_on_arcs(v_var_value)
        for n, arc in enumerate(self.input_data.traveling_arcs):
            self.capacity_rhs_vars[n].lb = capacitys[n]
            self.capacity_rhs_vars[n].ub = capacitys[n]
            

    def change_constraint_coefficients(self, v_var_value, u_value):
        """同时调整两类约束右端项
        
        对应Java: changeConstraintCoefficients
        """
        self.change_demand_constraint_coefficients(u_value)
        self.change_capacity_constraint_coefficients(v_var_value) 