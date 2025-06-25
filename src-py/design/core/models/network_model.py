from typing import Optional
import logging
import gurobipy as gp
from gurobipy import GRB, LinExpr
import numpy as np
import json
from datetime import datetime

from ..algorithms.route_solution_pool import RouteSolutionPool
from .network_data import NetworkData
from .route_solution import RouteSolution
from .design_solution import DesignSolution
from ...utils.config import Config
from utils.data_processing import calculate_distance_matrix

class NetworkModel:
    def __init__(self, network_data: NetworkData, model_type='MILP', obj_type="Cost", mode = "Optimize", max_solutions: Optional[int] = None):
        """初始化模型，接收数据类实例
        Args:
            network_data: 网络数据
            model_type: 模型类型
            obj_type: 目标函数类型
            max_solutions: 最大保存解数量
        """
        self.network_data = network_data
        self.model = gp.Model(f"RouteDesign(P{network_data.P}R{self.network_data.R}K{self.network_data.K})")
        self.model.Params.OutputFlag = 0  # 完全禁用gurobi输出
        self.model_type = model_type
        self.mode = mode
        self.obj_type = obj_type   # 默认目标类型
        self.M = 1e6  # 大M值
        self._variables = {}  # 统一变量存储
        self.route_solution_pool = RouteSolutionPool(network_data=network_data)
        self.max_solutions = max_solutions
        self._build_model()
        
    # ======== 变量创建 ========
    def _create_variables(self):
        """创建所有决策变量"""
        self._create_port_variables()
        self._create_arc_variables()
        self._create_time_variables()
        self._create_od_variables()
        self.model.update()
        
    def _create_port_variables(self):
        """创建与港口相关的变量"""
        self._variables["x_in"] = self.model.addVars(
            self.network_data.num_ports, self.network_data.num_routes,
            vtype=GRB.BINARY, 
            name="x_in"
        )
        self._variables["x_out"] = self.model.addVars(
            self.network_data.num_ports, self.network_data.num_routes,
            vtype=GRB.BINARY, 
            name="x_out"
        )
        
    def _create_arc_variables(self):
        """创建与航段相关的变量"""
        self._variables["y_in"] = self.model.addVars(
            len(self.network_data.arcs), self.network_data.num_routes,
            vtype=GRB.BINARY, 
            name="y_in"
        )
        self._variables["y_out"] = self.model.addVars(
            len(self.network_data.arcs), 
            self.network_data.num_routes,
            vtype=GRB.BINARY, name="y_out"
        )
        
    def _create_time_variables(self):
        """创建与时间相关的变量"""
        self._variables["mu_in"] = self.model.addVars(
            self.network_data.num_ports, self.network_data.num_routes,
            lb=0, 
            vtype=GRB.CONTINUOUS,
            name="mu_in"
        )        
        self._variables["mu_out"] = self.model.addVars(
            self.network_data.num_ports, self.network_data.num_routes,
            lb=0, 
            vtype=GRB.CONTINUOUS,
            name="mu_out"
        )
        # 创建虚拟节点
        self._variables["mu_in"][-1] = self.model.addVars(self.network_data.num_routes,
                                                          lb= 0,
                                                          vtype= GRB.CONTINUOUS,
                                                          name="mu_in_v"
                                                          )
        self._variables["mu_out"][-1] = self.model.addVars(self.network_data.num_routes,
                                                          lb= 0,
                                                          vtype= GRB.CONTINUOUS,
                                                          name="mu_out_v"
                                                          )
        self._variables["T"] = self.model.addVars(
            self.network_data.num_routes, 
            lb=0, 
            vtype=GRB.CONTINUOUS,
            name="T"
        )
        
    def _create_od_variables(self):
        """创建与OD相关的变量"""
        self._variables["t"] = self.model.addVars(
            self.network_data.num_ods, vtype=GRB.CONTINUOUS, lb=0, name="t"
        )
        for suffix in ["ii", "io", "oo", "oi"]:
            self._variables[f"t_{suffix}"] = self.model.addVars(
                self.network_data.num_ods, self.network_data.num_routes,
                vtype=GRB.CONTINUOUS, lb=0, name=f"t_{suffix}"
            )
            self._variables[f"z_{suffix}"] = self.model.addVars(
                self.network_data.num_ods, self.network_data.num_routes,
                vtype=GRB.CONTINUOUS, lb=0, ub=1, name=f"z_{suffix}"
            )
    
    # ======== 约束添加 ========
    def _add_constraints(self):
        """添加所有约束"""
        self._add_coverage_constraints()
        self._add_route_structure_constraints()
        self._add_flow_balance_constraints()
        self._add_MTZ_constraints()
        self._add_time_constraints()
        
    def _add_coverage_constraints(self):
        """添加端口覆盖约束"""
        for i in range(self.network_data.num_ports):
            expr = gp.quicksum(
                self._variables["x_in"][i, r] + self._variables["x_out"][i, r]
                for r in range(self.network_data.num_routes)
            )
            self.model.addConstr(expr >= 1, name=f"coverage_{i}")
            
    def _add_route_structure_constraints(self):
        """添加航次结构约束"""
        # # 起始/终点港口约束
        # for r in range(self.network_data.num_routes):
        #     self.model.addConstr(self._variables["x_in"][0, r] == 1)
        #     self.model.addConstr(self._variables["x_in"][self.network_data.num_ports-1, r] == 1)
        #     self.model.addConstr(self._variables["x_out"][0, r] == 1)
        #     self.model.addConstr(self._variables["x_out"][self.network_data.num_ports-1, r] == 1)
            
        # 航次长度约束
        for r in range(self.network_data.num_routes):
            expr = gp.quicksum(
                self._variables["x_in"][i, r] + self._variables["x_out"][i, r]
                for i in range(self.network_data.num_ports)
            )
            self.model.addConstr(expr >= self.network_data.min_length, name=f"sizeLB_{r}")
            self.model.addConstr(expr <= self.network_data.max_length, name=f"sizeUB_{r}")
            
        # 预算约束
        budget_expr = gp.quicksum(
            (self.network_data.ports_df.loc[i, 'FixedCost'] if self.network_data.ports_df is not None else 0) *
            (self._variables["x_in"][i, r] + self._variables["x_out"][i, r])
            for i in range(self.network_data.num_ports)
            for r in range(self.network_data.num_routes)
        )
        self.model.addConstr(budget_expr <= self.network_data.C_max, name="budget")
        
    def _add_flow_balance_constraints(self):
        """添加流平衡约束"""
        for r in range(self.network_data.num_routes):
            # 港口节点流平衡
            for i in range(self.network_data.num_ports):
                # 入港流平衡
                sum_in = gp.quicksum(
                    self._variables["y_in"][e, r]
                    for e in range(len(self.network_data.arcs))
                    if self.network_data.arcs[e][1] == i
                )
                self.model.addConstr(sum_in == self._variables["x_in"][i, r], name=f"flow_in_inbound_{i}_{r}")
                
                # 出港流平衡
                sum_out = gp.quicksum(
                    self._variables["y_out"][e, r]
                    for e in range(len(self.network_data.arcs))
                    if self.network_data.arcs[e][0] == i
                )
                self.model.addConstr(sum_out == self._variables["x_out"][i, r], name=f"flow_out_inbound_{i}_{r}")
    
            # 虚拟节点流平衡
            # 入流平衡
            sum_in = gp.quicksum(
                self._variables["y_in"][e, r]
                    for e in range(len(self.network_data.arcs))
                    if self.network_data.arcs[e][1] == -1
            )
            for i in range(self.network_data.num_ports):
                self.model.addConstr(sum_in == self._variables["x_in"][i, r], name=f"flow_in_inbound_vir_{r}")
                
            # 出流平衡
            sum_out = gp.quicksum(
                    self._variables["y_out"][e, r]
                    for e in range(len(self.network_data.arcs))
                    if self.network_data.arcs[e][0] == -1
            )
            for i in range(self.network_data.num_ports):
                self.model.addConstr(sum_out == self._variables["x_out"][i, r], name=f"flow_out_inbound_vir_{r}")

    def _add_MTZ_constraints(self):
        """添加MTZ约束"""
        for r in range(self.network_data.num_routes):
            # \mu_i^{in} - \mu_j^{in} + M y_{ijr}^{in}\leq M - t_{ij}
            for e in range(len(self.network_data.arcs)):
                (i, j) = self.network_data.arcs[e]
                if i == -1 or j == -1:
                    continue
                self.model.addConstr(
                    self._variables["mu_in"][i, r] - self._variables["mu_in"][j, r] + self.M * self._variables["y_in"][e, r] <= self.M - self.network_data.distance_matrix[i][j],
                    name=f"MTZ_in_{i}-{j}_{r}"
                )
                self.model.addConstr(
                    self._variables["mu_out"][i, r] - self._variables["mu_out"][j, r] + self.M * self._variables["y_out"][e, r] <= self.M - self.network_data.distance_matrix[i][j],
                    name=f"MTZ_out_{i}-{j}_{r}"
                )

    def _add_time_constraints(self):
        """添加时间相关约束"""
        self._add_big_m_constraints()
        self._add_cycle_time_constraints()
        self._add_od_time_constraints()
        
    def _add_big_m_constraints(self):
        """添加Big-M约束"""
        for r in range(self.network_data.num_routes):
            for i in range(self.network_data.num_ports):
                self.model.addConstr(
                    self._variables["mu_in"][i, r] <= self.M * self._variables["x_in"][i, r],
                    name=f"mu_in_link_{i}_{r}"
                )
                self.model.addConstr(
                    self._variables["mu_out"][i, r] <= self.M * self._variables["x_out"][i, r],
                    name=f"mu_out_link_{i}_{r}"
                )
                
    def _add_cycle_time_constraints(self):
        """添加周期时间约束"""
        for r in range(self.network_data.num_routes):
            self.model.addConstr(
                self._variables["T"][r] == self._variables["mu_out"][0, r] - self._variables["mu_in"][0, r],
                name=f"cycle_{r}"
            )
            self.model.addConstr(
                self._variables["T"][r] >= self.network_data.T_min, name=f"cycleLB_{r}"
            )
            self.model.addConstr(
                self._variables["T"][r] <= self.network_data.T_max, name=f"cycleUB_{r}"
            )
            
    def _add_od_time_constraints(self):
        """添加OD时间约束"""
        for od in range(self.network_data.num_ods):
            o, d = self.network_data.od_pairs[od]
            for r in range(self.network_data.num_routes):
                # 根据OD方向选择不同的时间计算方式
                if o < d:
                    self._add_od_time_constraint(od, r, o, d, is_forward=True)
                else:
                    self._add_od_time_constraint(od, r, o, d, is_forward=False)
                    
    def _add_od_time_constraint(self, od, r, o, d, is_forward):
        """添加单个OD时间约束"""
        t_ii = self._variables["t_ii"][od, r]
        t_io = self._variables["t_io"][od, r]
        t_oo = self._variables["t_oo"][od, r]
        t_oi = self._variables["t_oi"][od, r]
        
        if is_forward:
            self.model.addConstr(t_ii == self._variables["mu_in"][d, r] - self._variables["mu_in"][o, r] + self.M * (2 - (self._variables["x_in"][o, r] + self._variables["x_in"][d, r])))
            self.model.addConstr(t_io == self._variables["mu_out"][d, r] - self._variables["mu_in"][o, r] + self.M * (2 - (self._variables["x_in"][o, r] + self._variables["x_out"][d, r])))
            self.model.addConstr(t_oo == self._variables["T"][r] + self._variables["mu_out"][d, r] - self._variables["mu_out"][o, r] + self.M * (2 - (self._variables["x_out"][o, r] + self._variables["x_out"][d, r])))
            self.model.addConstr(t_oi == self._variables["T"][r] + self._variables["mu_in"][d, r] - self._variables["mu_out"][o, r] + self.M * (2 - (self._variables["x_out"][o, r] + self._variables["x_in"][d, r])))
        else:
            self.model.addConstr(t_ii == self._variables["T"][r] + self._variables["mu_in"][d, r] - self._variables["mu_in"][o, r] + self.M * (2 - (self._variables["x_in"][o, r] + self._variables["x_in"][d, r])))
            self.model.addConstr(t_io == self._variables["mu_out"][d, r] - self._variables["mu_in"][o, r] + self.M * (2 - (self._variables["x_in"][o, r] + self._variables["x_out"][d, r])))
            self.model.addConstr(t_oo == self._variables["mu_out"][d, r] - self._variables["mu_out"][o, r] + self.M * (2 - (self._variables["x_out"][o, r] + self._variables["x_out"][d, r])))
            self.model.addConstr(t_oi == self._variables["T"][r] + self._variables["mu_in"][d, r] - self._variables["mu_out"][o, r] + self.M * (2 - (self._variables["x_out"][o, r] + self._variables["x_in"][d, r])))
    
    # ======== 目标函数设置 ========
    def _set_objective(self):
        """设置目标函数"""
        if self.obj_type == "Cost":
            self._set_minimize_cost_objective()
        elif self.obj_type == "Time":
            self._set_minimize_time_objective()
        elif self.obj_type == "Utility":
            self._set_maximize_utility_objective()
            
    def _set_minimize_cost_objective(self):
        """设置最小化成本目标函数"""
        obj = LinExpr(0)
        
        # 节点覆盖成本
        for r in range(self.network_data.num_routes):
            obj += gp.quicksum(
                (self.network_data.ports_df.loc[i, 'FixedCost'] if self.network_data.ports_df is not None else 0) *
                (self._variables["x_in"][i, r] + self._variables["x_out"][i, r])
                for i in range(self.network_data.num_ports)
            )
            
        # 航段运输成本
        for r in range(self.network_data.num_routes):
            obj += gp.quicksum(
                self.network_data.arc_costs[self.network_data.arcs[e]] * self._variables["y_in"][e, r]
                for e in range(len(self.network_data.arcs))
            )
            obj += gp.quicksum(
                self.network_data.arc_costs[self.network_data.arcs[e]] * self._variables["y_out"][e, r]
                for e in range(len(self.network_data.arcs))
            )
            
        self.model.setObjective(obj, GRB.MINIMIZE)
        
    def _set_minimize_time_objective(self):
        """设置最小化时间目标函数"""
        obj = LinExpr(0)
        for od in range(self.network_data.num_ods):
            obj += self._variables["t"][od]
        for r in range(self.network_data.num_routes):
            obj += self._variables["T"][r]
            
        self.model.setObjective(obj, GRB.MINIMIZE)
        
    def _set_maximize_utility_objective(self):
        """设置最大化效用目标函数"""
        pass  # 实现待补充
        
    # ======== 模型构建流程 ========
    def _build_model(self):
        """分步构建模型"""
        self._create_variables()
        self._add_constraints()
        self._set_objective()
        
    # ======== 求解与结果提取 ========
    def solve(self, time_limit=10):
        """求解模型并收集中间解
        Args:
            time_limit: 求解时间限制(分钟)
        Returns:
            最终解
        """
        try:
            self.model_solution_pool = []  # 初始化解池
            self.model.Params.TimeLimit = time_limit
            self.model.Params.LogToConsole = 0  # 禁用控制台日志
            if self.mode == "Optimize":
                self.model.optimize()
            
                if self.model.status == GRB.OPTIMAL:
                    model_solution = self._extract_solution()
                    self.model_solution_pool.append(model_solution)
                    return model_solution
                elif self.model.status == GRB.TIME_LIMIT and self.model.SolCount >= 1:
                    model_solution = self._extract_solution(allow_suboptimal=True)
                    self.model_solution_pool.append(model_solution)
                    return model_solution
                else:
                    self._handle_failure(self.model.status)
            
            elif self.mode == "PreSearch":
                self.model.Params.PoolSearchMode = 2  # 积极搜索多个解
                self.model.Params.PoolSolutions = self.max_solutions  # 最大解数量
                
                def callback(model, where):
                    if where == GRB.Callback.MIPNODE:
                        status = model.cbGet(GRB.Callback.MIPNODE_STATUS)
                        if status == GRB.OPTIMAL:
                            obj = model.cbGet(GRB.Callback.MIPNODE_OBJBST)
                            if self.max_solutions is not None and len(self.model_solution_pool) < self.max_solutions:
                                self.model_solution_pool.append({
                                    'objVal': obj,
                                    'time': model.cbGet(GRB.Callback.RUNTIME)
                                })
                
                self.model.optimize(callback)
                
                # 收集所有找到的解
                max_sol = self.max_solutions if self.max_solutions is not None else self.model.SolCount
                for i in range(min(self.model.SolCount, max_sol)):
                    self.model.Params.SolutionNumber = i
                    model_solution = self._extract_solution(allow_suboptimal=True)
                    if i < len(self.model_solution_pool):
                        self.model_solution_pool[i].update(model_solution)
                    else:
                        self.model_solution_pool.append(model_solution)
                    for idx, solution in model_solution["port_calls"].items():
                        self.route_solution_pool.add_new_solution(solution=solution)
                
                if self.model.status == GRB.OPTIMAL:
                    return self.model_solution_pool[-1]
                elif self.model.status == GRB.TIME_LIMIT and self.model.SolCount >= 1:
                    return self.model_solution_pool[-1]
                else:
                    self._handle_failure(self.model.status)
                
        except gp.GurobiError as e:
            self.model.dispose()
            raise RuntimeError(f"Gurobi求解异常: {str(e)}")
            
    def _extract_solution(self, allow_suboptimal=False):
        """提取求解结果"""
        # 初始化存储列表
        routes = {}
        port_calls = {r: [] for r in range(self.network_data.num_routes)}
        # 构建RouteSolution对象列表
        route_solutions = []
        for r in range(self.network_data.num_routes):
            in_nodes = sorted(
                [i for i in range(self.network_data.num_ports) if self._variables["x_in"][i, r].X > 0.5],
                key=lambda x: self._variables["mu_in"][x, r].X
            )
            out_nodes = sorted(
                [i for i in range(self.network_data.num_ports) if self._variables["x_out"][i, r].X > 0.5],
                key=lambda x: self._variables["mu_out"][x, r].X
            )
            
            # 合并进出港顺序
            route = in_nodes + out_nodes[len(out_nodes)-1:]
            if route and route[0] == route[-1]:
                route = route[:-1]
                
            routes[r] = route
            port_calls[r] = [in_nodes, out_nodes]
            
            route_sol = RouteSolution(
                solution= list(in_nodes) + list(out_nodes),
                network_data=self.network_data
            )
            route_solutions.append(route_sol)

        # 构建DesignSolution对象
        design_solution = DesignSolution(network_data=self.network_data)
        for route_solution in route_solutions:
            design_solution.add_route_solution(route_solution=route_solution)
        design_solution.print_design_solution()

        return {
            'algo_type': 'Gurobi',
            'routes': routes,
            'port_calls': port_calls,
            'cycle_times': [round(self._variables["T"][r].X, 2) for r in range(self.network_data.num_routes)],
            'total_cost': round(self.model.ObjVal, 2),
            'is_optimal': self.model.status == GRB.OPTIMAL,
            'objVal': self.model.ObjVal,
            'Gap': self.model.MIPGap,
            'route_solutions': route_solutions,
            'design_solution': design_solution
        }
        
    def _handle_failure(self, status):
        """处理求解失败情况"""
        error_messages = {
            GRB.INFEASIBLE: "模型不可行",
            GRB.UNBOUNDED: "目标函数无界",
            GRB.INF_OR_UNBD: "问题不可行或无界",
            GRB.INTERRUPTED: "求解被中断",
            GRB.NUMERIC: "数值问题导致求解失败"
        }
        
        if status in error_messages:
            self.model.computeIIS()
            self.model.write("model.ilp")
            logging.error(f"{error_messages[status]}. 已导出冲突分析到model.ilp")
            # raise RuntimeError(f"{error_messages[status]}. 已导出冲突分析到model.ilp")
        else:
            logging.error(f"未知求解状态: {status}")
            # raise RuntimeError(f"未知求解状态: {status}")

    def save_solutions_to_file(self, filename="solutions.json"):
        """将解池中的解保存到JSON文件
        Args:
            filename: 保存文件名
        """
        if not hasattr(self, 'solution_pool') or not self.model_solution_pool:
            raise ValueError("没有可保存的解，请先运行solve()方法")

        solutions_data = {
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "model_type": self.model_type,
                "objective_type": self.obj_type,
                "mode": self.mode,
                "num_solutions": len(self.model_solution_pool),
                "network_params": {
                    "P": self.network_data.P,
                    "R": self.network_data.R,
                    "K": self.network_data.K
                }
            },
            "solutions": self.model_solution_pool
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(solutions_data, f, indent=2)
            return f"成功保存{len(self.model_solution_pool)}个解到{filename}"
        except Exception as e:
            raise RuntimeError(f"保存文件失败: {str(e)}")