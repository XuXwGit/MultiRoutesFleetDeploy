import logging
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB, quicksum

from design.core.algorithms.alns.alns_core import ALNSSolver
from design.core.algorithms.dual_var_values import DualVarValues
from design.core.models.network_data import NetworkData

class rowPSP:
    def __init__(self, 
                 network_design_data: NetworkData, 
                 dual_variables_values: DualVarValues):
        self.network_data = network_design_data
        self.problem_type = network_design_data.problem_type
        self.dual_variables_values = dual_variables_values

        self.optimizer_type = "Gurobi"

        # models in each iteration
        self.model = gp.Model('PSP')
        self.alns_for_rowPSP = ALNSSolver(self.network_data)

        # decision variable
        self.row_x = []
        self.row_x_in = []
        self.row_x_out = []

    def update(self):
        self.model.update()

    def build_rowPSP(self):
        # create decision variables
        self.create_variables()

        # add constraints
        self.add_constraints()

        # set objectives
        self.set_objective()

        self.model.write('model/RowPSP.lp')
        return self.model
    
    def create_variables(self):
        if self.problem_type == 'Tour':
            self.row_x = self.model.addVars(
                self.network_data.num_ports, 
                obj=-self.dual_variables_values.value_u1,
                vtype=GRB.BINARY, name='y'
            )
        elif self.problem_type == 'Multi-Routes':
            self.row_x_in = self.model.addVars(
                self.network_data.num_ports, 
                obj=-self.dual_variables_values.value_u1, 
                ub=1,
                vtype=GRB.BINARY, name='y_in'
            )
            self.row_x_out = self.model.addVars(
                self.network_data.num_ports, 
                obj=-self.dual_variables_values.value_u1, 
                ub=1,
                vtype=GRB.BINARY, name='y_out'
            )

        self.U = {}
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                self.U[(k, s)] = self.model.addVar(
                    vtype=gp.GRB.CONTINUOUS, 
                    lb=-gp.GRB.INFINITY, 
                    ub=gp.GRB.INFINITY, 
                    obj=0,
                    name=f'U_{k}-{s}'
                )
        self.alpha = []
        for k in range(self.network_data.num_types):
            alpha_k = []
            for s in range(self.network_data.num_samples):
                alpha_k.append(self.model.addVar(
                    vtype=gp.GRB.CONTINUOUS, 
                    lb=0, 
                    ub=gp.GRB.INFINITY, 
                    obj=1,
                    name=f'alpha[{self.network_data.od_pairs[k][0]}-{self.network_data.od_pairs[k][1]}][{s}]'
                ))
            self.alpha.append(alpha_k)
        self.t = []
        self.t_ii = []
        self.t_io = []
        self.t_oo = []
        self.t_oi = []
        if self.problem_type == 'Multi-Routes':
            self.t = self.model.addVars(self.network_data.num_types, obj=0, vtype=GRB.CONTINUOUS, name='t')
            self.t_ii = self.model.addVars(self.network_data.num_types, obj=0, vtype=GRB.CONTINUOUS, name='t-ii')
            self.t_io = self.model.addVars(self.network_data.num_types, obj=0, vtype=GRB.CONTINUOUS, name='t-io')
            self.t_oo = self.model.addVars(self.network_data.num_types, obj=0, vtype=GRB.CONTINUOUS, name='t-oi')
            self.t_oi = self.model.addVars(self.network_data.num_types, obj=0, vtype=GRB.CONTINUOUS, name='t-oo')
        
        self.mu_in = []
        self.mu_out = []
        if self.problem_type == 'Multi-Routes':
            self.mu_in = self.model.addVars(self.network_data.num_ports, obj=0, vtype=gp.GRB.CONTINUOUS, name='mu-in')
            self.mu_out = self.model.addVars(self.network_data.num_ports, obj=0, vtype=gp.GRB.CONTINUOUS, name='mu-out')

            
    def add_constraints(self):
        # # constr 1: routes length constraint
        if self.problem_type == 'Tour':
            self.model.addConstr(
                quicksum(self.row_x[i] for i in range(self.network_data.num_ports)) >= self.network_data.min_length,
                name='x-PSP-0'
            )
            self.model.addConstr(
                quicksum(self.row_x[i] for i in range(self.network_data.num_ports)) <= self.network_data.max_length,
                name='x-PSP-1'
            )
        elif self.problem_type == 'Multi-Routes':
            self.model.addConstr(
                quicksum(self.row_x_in[i] + self.row_x_out[i] for i in range(self.network_data.num_ports)) >= self.network_data.min_length,
                name='x-PSP-0'
            )
            self.model.addConstr(
                quicksum(self.row_x_in[i] + self.row_x_out[i] for i in range(self.network_data.num_ports)) <= self.network_data.max_length,
                name='x-PSP-1'
            )
    
        # # constr 2: 
        # mu_in[i] \leq M * y_in[i] \forall i \in P
        if self.problem_type == 'Multi-Routes':
            for i in range(self.network_data.num_ports):
                self.model.addConstr(self.mu_in[i] <= self.network_data.M * self.row_x_in[i], name=f'RowPSP-5_{i}')
                self.model.addConstr(self.mu_out[i] <= self.network_data.M * self.row_x_out[i], name=f'RowPSP-6_{i}')
                for j in range(i + 1, self.network_data.num_ports):
                    self.model.addConstr(
                        self.mu_in[i] - self.mu_in[j] + self.network_data.M * (self.row_x_in[i] + self.row_x_in[j]) <= 2 * self.network_data.M - self.network_data.distance_matrix[(i, j)],
                        name=f'MTZ-in-[{i}-{j}]'
                    )
                    self.model.addConstr(
                        self.mu_out[j] - self.mu_out[i] + self.network_data.M * (self.row_x_out[i] + self.row_x_out[j]) <= 2 * self.network_data.M - self.network_data.distance_matrix[(i, j)],
                        name=f'MTZ-out-[{i}-{j}]'
                    )

        ## constr 3:
        # calculate transport time
        if self.problem_type == 'Multi-Routes':
            T_r = self.model.addVar(obj=0, lb=0, vtype=gp.GRB.CONTINUOUS, name='T')
            self.model.addConstr(T_r == self.mu_out[0] - self.mu_in[0], name=f'T')
            for k in range(self.network_data.num_types):
                self.model.addConstr(
                    self.t[k] == gp.min_(self.t_ii[k], self.t_io[k], self.t_oo[k], self.t_oi[k], self.network_data.M), 
                    name=f't_{k}'
                )
                o = self.network_data.od_pairs[k][0]
                d = self.network_data.od_pairs[k][1]
                if o < d:
                    self.model.addConstr(
                        self.t_ii[k] == self.mu_in[d] - self.mu_in[o] + self.network_data.M * (2 - (self.row_x_in[o] + self.row_x_in[d])),
                        name=f"t-ii[{k}]"
                    )
                    self.model.addConstr(
                        self.t_io[k] == self.mu_out[d] - self.mu_in[o] + self.network_data.M * (2 - (self.row_x_in[o] + self.row_x_out[d])),
                        name=f"t-io[{k}]"
                    )
                    self.model.addConstr(
                        self.t_oo[k] == T_r + self.mu_out[d] - self.mu_out[o] + self.network_data.M * (2 - (self.row_x_out[o] + self.row_x_out[d])),
                        name=f"t-oo[{k}]"
                    )
                    self.model.addConstr(
                        self.t_oi[k] == T_r + self.mu_in[d] - self.mu_out[o] + self.network_data.M * (2 - (self.row_x_out[o] + self.row_x_in[d])),
                        name=f"t-oi[{k}]"
                    )
                else:
                    self.model.addConstr(
                        self.t_ii[k] == T_r + self.mu_in[d] - self.mu_in[o] + self.network_data.M * (2 - (self.row_x_in[o] + self.row_x_in[d])),
                        name=f"t-ii[{k}]"
                    )
                    self.model.addConstr(
                        self.t_io[k] == self.mu_out[d] - self.mu_in[o] + self.network_data.M * (2 - (self.row_x_in[o] + self.row_x_out[d])),
                        name=f"t-io[{k}]"
                    )
                    self.model.addConstr(
                        self.t_oo[k] == self.mu_out[d] - self.mu_out[o] + self.network_data.M * (2 - (self.row_x_out[o] + self.row_x_out[d])),
                        name=f"t-oo[{k}]"
                    )
                    self.model.addConstr(
                        self.t_oi[k] == T_r + self.mu_in[d] - self.mu_out[o] + self.network_data.M * (2 - (self.row_x_out[o] + self.row_x_in[d])),
                        name=f"t-oi[{k}]"
                    )
        
        ## constr 4
        # alpha = max{u-v, 0}
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                right = self.network_data.constants[k]
                if self.problem_type == 'Multi-Routes':
                    right += self.network_data.preference_matrix[k] * self.t[k]
                elif self.problem_type == 'Tour':
                    right += quicksum(self.network_data.preference_matrix[k][i] * self.row_x[i] 
                                      for i in range(self.network_data.num_ports))
                right += self.network_data.varepsion[k][s]
                self.model.addConstr(self.U[(k, s)] == right, name=f'Utility-{k}-{s}')
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                d_k_s = self.model.addVar(
                    vtype=gp.GRB.CONTINUOUS, lb=-gp.GRB.INFINITY, ub=gp.GRB.INFINITY, obj=0,
                    name=f'd[{k}][{s}]'
                )
                self.model.addConstr(d_k_s == self.U[(k, s)] - self.dual_variables_values.value_v[k][s], name=f'd=U[{k}][{s}]-v')
                self.model.addConstr(self.alpha[k][s] == gp.max_(d_k_s, 0), name=f'alpha=max([d{k}][{s}],0)')



    def set_objective(self):
        # min {u^0} + \sum_{i \in \cal N}(c_i - 1){(u^1_i + u^2)}({x}^{in}_{ir} + {x}^{out}_{ir})   - \sum_{k,s} w_{ks}^r 
        # part 1: u0
        obj = self.dual_variables_values.value_u0
        for i in range(self.network_data.num_ports):
            if self.problem_type == 'Tour':
                obj -= self.dual_variables_values.value_u1[i] * self.row_x[i]
            elif self.problem_type == 'Multi-Routes':
                obj += (self.network_data.ports_df.loc[i,'FixedCost'] - 1) * (self.dual_variables_values.value_u1[i] + self.dual_variables_values.value_u2) * (self.row_x_in[i] + self.row_x_out[i])
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                obj += self.alpha[k][s]
        self.model.setObjective(obj, gp.GRB.MAXIMIZE)


    def solve(self, time_limit = 600):
        """求解row-PSP问题
        
        根据optimizer_type选择求解方式：
        - "ALNS": 使用自适应大邻域搜索算法
        - 其他: 使用精确求解器(Gurobi)
        
        Args:
            time_limit: 求解时间限制(秒)
            
        Returns:
            tuple: (solution, objective_value)
                   solution: 求解得到的航线方案
                   objective_value: 目标函数值
        """
        if self.optimizer_type == "ALNS":
            # 使用ALNS求解
            logging.info('====>>>>==Solve row-PSP with ALNS==<<<<====')
            
            # 更新ALNS对偶变量
            self.alns_for_rowPSP.update_dual_values(self.dual_variables_values)
            
            # 调用ALNS求解
            best_route_solution, best_objective = self.alns_for_rowPSP.solve_rowPSP(
                max_iterations=100,
                time_limit=min(300, time_limit)  # ALNS时间限制不超过300秒
            )
            
            if best_route_solution is not None:
                logging.info(f'ALNS found solution with objective: {best_objective}')
                return best_route_solution, best_objective
            else:
                logging.warning('ALNS failed to find solution')
                return None, 0
        elif self.optimizer_type == "Gurobi":
            # 使用精确求解器(Gurobi)
            logging.info('====>>>>==Solve row-PSP with exact solver==<<<<====')
            self.model.Params.TimeLimit = time_limit
            self.model.optimize()
            
            logging.info(f'row-PSP {self.get_model_status_str(self.model)}')
            if self.model.Status == GRB.Status.OPTIMAL:
                solution = self.get_solution_from_rowPSP()
                return solution, self.model.objVal
            else:
                return None, 0
        else:
            logging.warning("未设置求解工具")
            return None, 0

    # update constr and objective based on new dual vars values
    def update_row_PSP(self):
        if self.optimizer_type == "ALNS":
            self.alns_for_rowPSP.update_dual_values(self.dual_variables_values)
            return 

        # modify the constr : alpha = max{u - v[k, s], 0}
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                self.model.getConstrByName(f'd=U[{k}][{s}]-v').setAttr(GRB.Attr.RHS, -self.dual_variables_values.value_v[k][s])
        # modify the objective
        obj = self.dual_variables_values.value_u0
        for i in range(self.network_data.num_ports):
            if self.problem_type == 'Tour':
                obj -= self.dual_variables_values.value_u1[i] * self.row_x[i]
            elif self.problem_type == 'Multi-Routes':
                obj += (self.network_data.ports_df.loc[i,'FixedCost'] - 1) * (self.dual_variables_values.value_u1[i] + self.dual_variables_values.value_u2) * (self.row_x_in[i] + self.row_x_out[i])
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                obj += self.alpha[k][s]
        self.model.setObjective(obj, GRB.MAXIMIZE)



    def get_model_status_str(self, model):
        if model.Status == GRB.OPTIMAL:
            return 'Optimal'
        elif model.Status == GRB.INFEASIBLE:
            return 'Infeasible'
        elif model.Status == GRB.UNBOUNDED:
            return 'Unbound'
        elif model.Status == GRB.INF_OR_UNBD:
            return 'Infeasible or Unbound'
        elif model.Status == GRB.TIME_LIMIT:
            return "Time Limit"
        else:
            return "Error"



    def add_infeasible_cut_to_row_PSP(self, solution):
        """添加不可行割到row-PSP问题
        
        根据optimizer_type选择不同的处理方式：
        - "ALNS": 记录不可行解到ALNS求解器
        - 其他: 添加割平面到Gurobi模型
        
        Args:
            solution: 需要排除的不可行解
        """
        if self.optimizer_type == "ALNS":
            # 记录不可行解到ALNS求解器
            if hasattr(self.alns_for_rowPSP, 'record_infeasible_solution'):
                self.alns_for_rowPSP.record_infeasible_solution(solution)
        else:
            # 添加割平面到Gurobi模型
            if self.problem_type == 'Tour':
                self.model.addConstr(
                    quicksum(self.row_x[i] for i in solution) <= len(solution) - 1,
                    name='RowPSP-Infeasible-Cut'
                )
            elif self.problem_type == 'Multi-Routes':
                solution_in, solution_out = solution
                self.model.addConstr(
                    quicksum(self.row_x_in[i] for i in solution_in) +
                    quicksum(self.row_x_out[i] for i in solution_out) <= len(solution) - 1,
                    name='RowPSP-Infeasible-Cut'
                )
            self.model.update()



    def get_solution_from_rowPSP(self):
        solution = []
        if self.problem_type == 'Tour':
            solution = [i for i in range(self.network_data.num_ports) if self.row_x[i].x > 0.5]
        elif self.problem_type == 'Multi-Routes':
            solution_in = [i for i in range(self.network_data.num_ports) if self.row_x_in[i].x > 0.5]
            solution_out = [i for i in range(self.network_data.num_ports) if self.row_x_out[i].x > 0.5]
            solution.append(solution_in)
            solution.append(solution_out)
        return solution
    
