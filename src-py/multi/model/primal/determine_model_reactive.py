from asyncio.log import logger
import time
import cplex
from typing import List, Dict
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.base_primal_model import BasePrimalModel

class DetermineModelReactive(BasePrimalModel):
    """反应式确定性模型类
    
    基于均值需求的反应式确定性优化模型
    
    数学模型特点:
    1. 使用需求均值E[ξ]代替随机变量ξ
    2. 目标函数: 最小化总运营成本
       min Σ_h Σ_r c_hr V_hr + Σ_a (c_x x_a + c_x1 x1_a + c_y y_a + c_z z_a)
    3. 约束条件:
       - 船舶分配约束 Σ_h V_hr = 1
       - 流量平衡约束
       - 容量约束
       - 需求满足约束
       - 反应式调整约束
    
    其中:
    c_hr: 船舶类型h在航线r上的运营成本
    V_hr: 船舶分配决策变量
    c_x, c_x1, c_y, c_z: 各类集装箱的单位成本
    x_a, x1_a, y_a, z_a: 各类集装箱的运输量
    """
    
    def __init__(self, in_data: InputData, param: Parameter):
        """初始化反应式确定性模型
        
        Args:
            in_data: 输入数据(网络结构、需求等)
            param: 模型参数(成本系数、容量等)
        """
        super().__init__(in_data, param)
        self.model_name = (f"DMR-R{len(in_data.ship_route_set)}"
                         f"-T{param.time_horizon}"
                         f"-{DefaultSetting.FleetType}"
                         f"-S{DefaultSetting.randomSeed}")
        
        if DefaultSetting.WhetherPrintProcess:
            logger.info("=========DetermineModel (Reactive Strategy)==========")
            
        start = time.time()
        self.frame()
        begin = time.time()
        self.solve_model()
        end = time.time()
        self.solve_time = end - start
        
        if DefaultSetting.WhetherPrintProcess:
            logger.info(f"BuildTime = {begin - start:.2f}\t\t"
                       f"SolveTime = {end - start:.2f}")
            logger.info(f"Determine Objective = {self.obj_val:.2f}")
            self.print_solution()
            logger.info("================================")
            
    def frame(self):
        """构建模型框架"""
        self.set_decision_vars()
        self.set_objectives()
        self.set_constraints() 
        
    def set_decision_vars(self):
        """设置决策变量"""
        # 设置船舶分配决策变量
        self.vVars = []
        for h, vessel in enumerate(self.input_data.vessel_types):
            v_var_row = []
            for r, route in enumerate(self.input_data.shipping_routes):
                var_name = f"v_{h}_{r}"
                v_var_row.append(self.cplex.variables.add(
                    types=[self.cplex.variables.type.binary],
                    names=[var_name]
                )[0])
            self.vVar.append(v_var_row)
            
        # 设置第二次船舶分配决策变量
        self.vVar2 = []
        for h, vessel in enumerate(self.input_data.vessel_types):
            v_var_row = []
            for r, route in enumerate(self.input_data.shipping_routes):
                var_name = f"v2_{h}_{r}"
                v_var_row.append(self.cplex.variables.add(
                    types=[self.cplex.variables.type.binary],
                    names=[var_name]
                )[0])
            self.vVar2.append(v_var_row)
            
        # 设置请求决策变量
        self.set_request_decision_vars()
        
    def set_objectives(self):
        """设置目标函数"""
        obj = self.cplex.linear_expr()
        
        # 添加船舶运营成本
        obj = self.get_vessel_operation_cost_obj(obj)
        
        # 添加集装箱运输成本
        for i in range(len(self.param.demand)):
            # 添加需求未满足惩罚成本
            obj.add_term(self.param.penalty_cost_for_demand[i], self.gVars[i])
            
            request = self.input_data.requests[i]
            # 添加重箱运输成本
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                obj.add_term(self.param.laden_path_cost[j], self.xVar[i][k])
                obj.add_term(self.param.laden_path_cost[j], self.yVars[i][k])
                obj.add_term(self.param.rental_cost * self.param.travel_time_on_path[j], self.yVars[i][k])
                
            # 添加空箱运输成本
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                obj.add_term(self.param.empty_path_cost[j], self.zVars[i][k])
                
        self.cplex.objective.set_sense(self.cplex.objective.sense.minimize)
        self.cplex.objective.set_linear(obj)
        
    def set_constraints(self):
        """设置约束条件"""
        self.set_constraint0()  # 船舶分配约束
        self.set_constraint1()  # 需求满足约束
        self.set_constraint2()  # 容量约束
        self.set_constraint3()  # 流量平衡约束
        self.set_constraint4()  # 反应式调整约束
        
    def set_constraint0(self):
        """设置船舶分配约束: 每条航线必须分配一艘船舶"""
        for r, route in enumerate(self.input_data.shipping_routes):
            expr = self.cplex.linear_expr()
            for h, vessel in enumerate(self.input_data.vessel_types):
                expr.add_term(1.0, self.vVars[h][r])
            self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["E"],
                rhs=[1.0],
                names=[f"C0_{r}"]
            )
            
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
            self.C1[(i, k)] = self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["E"],
                rhs=[self.param.demand[i]],
                names=[f"C1_{i}_{k}"]
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
                        
            # 添加船舶容量
            for h, vessel in enumerate(self.input_data.vessel_types):
                for r, route in enumerate(self.input_data.shipping_routes):
                    for w, vessel_path in enumerate(self.input_data.vessel_paths):
                        if (self.param.arc_and_vessel_path[n][w] == 1 and
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and
                            self.param.vessel_type_and_ship_route[h][r] == 1):
                            expr.add_term(-self.param.vessel_capacity[h], self.vVars[h][r])
                            
            # 添加约束
            self.C2[(n, i, k)] = self.cplex.linear_constraints.add(
                lin_expr=[expr],
                senses=["L"],
                rhs=[0.0],
                names=[f"C2_{n}_{i}_{k}"]
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
                self.C3[p][(t, i, k)] = self.cplex.linear_constraints.add(
                    lin_expr=[expr],
                    senses=["E"],
                    rhs=[0.0],
                    names=[f"C3_{p}_{t}_{i}_{k}"]
                )[0]
                
    def set_constraint4(self):
        """设置反应式调整约束: 第二次船舶分配必须与第一次分配一致"""
        for h, vessel in enumerate(self.input_data.vessel_types):
            for r, route in enumerate(self.input_data.shipping_routes):
                expr = self.cplex.linear_expr()
                expr.add_term(1.0, self.vVars[h][r])
                expr.add_term(-1.0, self.vVar2[h][r])
                self.cplex.linear_constraints.add(
                    lin_expr=[expr],
                    senses=["E"],
                    rhs=[0.0],
                    names=[f"C4_{h}_{r}"]
                )
                
    def print_solution(self):
        """打印求解结果"""
        if self.solve_status == "optimal":
            logger.info("Optimal solution found!")
            logger.info(f"Objective value: {self.obj_val:.2f}")
            logger.info("Vessel allocation:")
            for h, vessel in enumerate(self.input_data.vessel_types):
                for r, route in enumerate(self.input_data.shipping_routes):
                    if self.cplex.solution.get_values(self.vVars[h][r]) > 0.5:
                        logger.info(f"Vessel {h} assigned to route {r}")
        else:
            logger.info(f"No optimal solution found. Status: {self.solve_status}") 