import logging
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB, quicksum

from design.core.models.network_data import NetworkData

class xPSP:
    def __init__(self, network_design_data: NetworkData, dual_variables_values):
        self.network_data = network_design_data
        self.problem_type = network_design_data.problem_type
        self.dual_variables_values = dual_variables_values
        # models in each iteration
        self.model = gp.Model('PSP')

        # decision variable
        self.psp_x = []
        self.psp_x_in = []
        self.psp_x_out = []



    def build_PSP(self):
        # create decision variables
        self.create_variables()

        # add constraints
        self.add_constraints()

        # set objectives
        self.set_objective()

        self.model.write('model/PSP.lp')
        return self.model
    


    def create_variables(self):
        # create decision variables
        if self.problem_type == 'Tour':
            self.psp_x = self.model.addVars(
                self.network_data.num_ports, 
                lb=0, ub=1,
                obj=-self.dual_variables_values.value_u1,
                vtype=GRB.CONTINUOUS, 
                name='y'
            )
        elif self.problem_type == 'Multi-Routes':
            self.psp_x_in = self.model.addVars(
                self.network_data.num_ports, 
                obj=0, # objective coefficient based on dual value
                vtype=GRB.BINARY, 
                name='y_in'
            )
            self.psp_x_out = self.model.addVars(
                self.network_data.num_ports, 
                obj=0, # objective coefficient based on dual value
                vtype=GRB.BINARY, 
                name='y_out'
            )

        # time variable
        self.mu_in = []
        self.mu_out = []
        if self.problem_type == 'Multi-Routes':
            self.mu_in = self.model.addVars(self.network_data.num_ports, obj=0, vtype=gp.GRB.CONTINUOUS, name='mu-in')
            self.mu_out = self.model.addVars(self.network_data.num_ports, obj=0, vtype=gp.GRB.CONTINUOUS, name='mu-out')



    def add_constraints(self):
        # # constr 1: routes length constraint
        if self.problem_type == 'Tour':
            self.model.addConstr(
                quicksum(self.psp_x[i] for i in range(self.network_data.num_ports)) >= self.network_data.min_length,
                name='x-PSP-0'
            )
            self.model.addConstr(
                quicksum(self.psp_x[i] for i in range(self.network_data.num_ports)) <= self.network_data.max_length,
                name='x-PSP-1'
            )
        elif self.problem_type == 'Multi-Routes':
            # lower bound
            self.model.addConstr(
                quicksum(self.psp_x_in[i] + self.psp_x_out[i] for i in range(self.network_data.num_ports)) >= self.network_data.min_length,
                name='x-PSP-0'
            )
            # upper bound
            self.model.addConstr(
                quicksum(self.psp_x_in[i] + self.psp_x_out[i] for i in range(self.network_data.num_ports)) <= self.network_data.max_length,
                name='x-PSP-1'
            )

        # # constr 2: 
        if self.problem_type == 'Multi-Routes':
            for i in range(self.network_data.num_ports):
                self.model.addConstr(self.mu_in[i] <= self.network_data.M * self.psp_x_in[i], name=f'RowPSP-5_{i}')
                self.model.addConstr(self.mu_out[i] <= self.network_data.M * self.psp_x_out[i], name=f'RowPSP-6_{i}')
                for j in range(i + 1, self.network_data.num_ports):
                    self.model.addConstr(
                        self.mu_in[i] - self.mu_in[j] + self.network_data.M * (self.psp_x_in[i] + self.psp_x_in[j]) <= 2 * self.network_data.M - self.network_data.distance_matrix[(i, j)],
                        name=f'MTZ-in-[{i}-{j}]'
                    )
                    self.model.addConstr(
                        self.mu_out[j] - self.mu_out[i] + self.network_data.M * (self.psp_x_out[i] + self.psp_x_out[j]) <= 2 * self.network_data.M - self.network_data.distance_matrix[(i, j)],
                        name=f'MTZ-out-[{i}-{j}]'
                    )



    def set_objective(self):
        # min {u^0} + \sum_{i \in \cal N}(c_i - 1){(u^1_i + u^2)}({x}^{in}_{ir} + {x}^{out}_{ir})   - \sum_{k,s} w_{ks}^r 
        # part 1: u0
        obj = self.dual_variables_values.value_u0
        for i in range(self.network_data.num_ports):
            if self.problem_type == 'Tour':
                obj -= self.dual_variables_values.value_u1[i] * self.psp_x[i]
            elif self.problem_type == 'Multi-Routes':
                # part 2: sum{i} (ci - 1) (u1[i] + u2) (x_in + x_out)
                obj += (self.network_data.ports_df.loc[i,'FixedCost'] - 1) * (self.dual_variables_values.value_u1[i] + self.dual_variables_values.value_u2) * (self.psp_x_in[i] + self.psp_x_out[i])
        self.model.setObjective(obj, GRB.MAXIMIZE)



    def update_PSP(self):
        obj = self.dual_variables_values.value_u0
        for i in range(self.network_data.num_ports):
            if self.problem_type == 'Tour':
                obj -= self.dual_variables_values.value_u1[i] * self.psp_x[i]
            elif self.problem_type == 'Multi-Routes':
                # part 2: sum{i} (ci - 1) (u1[i] + u2) (x_in + x_out)
                obj += (self.network_data.ports_df.loc[i,'FixedCost'] - 1) * (self.dual_variables_values.value_u1[i] + self.dual_variables_values.value_u2) * (self.psp_x_in[i] + self.psp_x_out[i])
        self.model.setObjective(obj, GRB.MAXIMIZE)



    def add_infeasible_cut_to_x_PSP(self, solution):
        if self.problem_type == 'Tour':
            self.model.addConstr(
                quicksum(self.psp_x[i] for i in solution) <= len(solution) - 1,
                name='x-PSP-InfeasibleCut'
            )
        else:
            solution_in, solution_out = solution
            self.model.addConstr(
                quicksum(self.psp_x_in[i] for i in solution_in) + quicksum(self.psp_x_out[i] for i in solution_out) <= len(solution) - 1,
                name='x-PSP-InfeasibleCut'
            )
        self.model.update()

    def update(self):
        self.model.update()



    def solve(self, time_limit = 60):
        self.model.Params.TimeLimit = time_limit
        self.model.optimize()
        if self.get_model_status(self.model) == 'Optimal':
            logging.info(f'x-PSP {self.get_model_status(self.model)}\t Obj-Val {self.model.objVal}')
            return self.model.objVal
        else:
            return 0



    def get_solution_from_PSP(self):
        solution = []
        if self.problem_type == 'Tour':
            solution = [i for i in range(self.network_data.num_ports) if self.psp_x[i].x > 0.5]
        elif self.problem_type == 'Multi-Routes':
            solution_in = [i for i in range(self.network_data.num_ports) if self.psp_x_in[i].x > 0.5]
            solution_in.sort(key=lambda i: self.mu_in[i].x)
            solution.append(solution_in)
            solution_out = [i for i in range(self.network_data.num_ports) if self.psp_x_out[i].x > 0.5]
            solution_out.sort(key=lambda i: self.mu_out[i].x)
            solution.append(solution_out)
        return solution



    def get_model_status(self, model):
        if model.Status == GRB.OPTIMAL:
            return 'Optimal'
        elif model.Status == GRB.INFEASIBLE:
            return 'Infeasible'
        elif model.Status == GRB.UNBOUNDED:
            return 'Unbound'
        elif model.Status == GRB.INF_OR_UNBD:
            return 'Infeasible or Unbound'
        else:
            return "Error"