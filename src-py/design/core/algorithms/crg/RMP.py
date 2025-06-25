import logging
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB, quicksum, Column

from design.core.algorithms.dual_var_values import DualVarValues
from design.core.algorithms.route_solution_pool import RouteSolutionPool
from design.core.models.network_data import NetworkData

class RMP:
    def __init__(self, 
                 network_design_data: NetworkData, 
                 route_solution_set: RouteSolutionPool, 
                 dual_variables_values: DualVarValues
                 ):
        self.network_data = network_design_data
        self.problem_type = network_design_data.problem_type
        self.route_solution_set = route_solution_set

        # models in each iteration
        self.model = gp.Model('RMP')
        self.model_type = 'LP'

        # decision variable
        self.x = []
        self.z = []

        # dual variable get from RMP in each iteration
        self.dual_variables_values = dual_variables_values

        self.alpha = []

        # constraints
        self.constr_u0 = []
        self.constr_u1s = []
        self.constr_u2 = []
        self.constr_v = []
        self.constr_w = []

        self.print_dual_values = False
        self.print_primal_values = False

        self.RMP_obj_value_log = []

    def update(self):
        self.model.update()

    # initial model
    # three part:
    # - create variables
    # - add constraints
    # - set objective
    def bulid_RMP(self):
        ## create decision variables
        self.create_variables()

        ## add constraints
        self.add_constraints()

        ## set objectives
        self.set_objective()

        self.model.write('model/RMP.lp')
        return self.model


    def create_variables(self):
        self.x = []
        self.x = []
        self.z = []
        self.route_index_map = {}  # 存储route_hash到索引的映射
        
        # 使用items()获取route_hash和solution的对应关系
        for idx, (route_hash, solution) in enumerate(self.route_solution_set.feasible_solutions.items()):
            x_r = self.model.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=1, obj=0, name=f'x_{idx}')
            self.x.append(x_r)
            self.route_index_map[route_hash] = idx
            
            z_r = []
            for k in range(self.network_data.num_ods):
                z_r_k = []
                for s in range(self.network_data.num_samples):
                    z_r_k_s = self.model.addVar(
                        vtype=GRB.CONTINUOUS,
                        lb=0,
                        ub=1,
                        obj=solution.utility.get((k, s), 0),
                        name=f'z_{idx}_{k}-{s}'
                    )
                    z_r_k.append(z_r_k_s)
                z_r.append(z_r_k)
            self.z.append(z_r)

    def add_constraints(self):
        # constr1: shipping routes number limit
        self.constr_u0 = self.model.addConstr(quicksum(self.x) <= self.network_data.num_routes,
                                            name='RMP-U0')
        # constr2: port cover constraint
        self.constr_u1s = []
        for i in range(self.network_data.num_ports):
            self.constr_u1s.append(self.model.addConstr(
                quicksum(
                    route_solution.route.count(i) * self.x[idx]
                    for route_hash, route_solution in self.route_solution_set.feasible_solutions.items()
                    for idx in [self.route_index_map[route_hash]]
                ) >= 1,
                name=f'RMP-U1_{i}'
            ))
        # constr3: total budget constraint
        self.constr_u2 = self.model.addConstr(
            quicksum(
                route_solution.route.count(i) * self.network_data.ports_df.loc[i,'FixedCost'] * self.x[idx]
                for route_hash, route_solution in self.route_solution_set.feasible_solutions.items()
                for idx in [self.route_index_map[route_hash]]
                for i in range(self.network_data.num_ports)
            ) <= self.network_data.C_max,
            name='RMP-U2'
        )
        # constr4: choice once constraint
        self.constr_v = []
        for k in range(self.network_data.num_types):
            v_k = []
            for s in range(self.network_data.num_samples):
                v_k.append(self.model.addConstr(
                    quicksum(z_r[k][s] for r, z_r in enumerate(self.z)) <= 1,
                    name=f'RMP-V_{k}_{s}'
                ))
            self.constr_v.append(v_k)
        # constr5: linking constraints
        self.constr_w = []
        for route_hash, solution in self.route_solution_set.feasible_solutions.items():
            r = self.route_index_map[route_hash]
            w_r = []
            for k in range(self.network_data.num_types):
                w_k_s = []
                for s in range(self.network_data.num_samples):
                    w_k_s.append(self.model.addConstr(
                        self.z[r][k][s] <= self.x[r],
                        name=f'RMP-W_{k}_{s}_{r}'
                    ))
                w_r.append(w_k_s)
            self.constr_w.append(w_r)

    def set_objective(self):
        self.model.setObjective(
            quicksum(
                self.route_solution_set.route_utility_set[(route_hash, k)][s] * self.z[r][k][s]
                for route_hash, solution in self.route_solution_set.feasible_solutions.items()
                for r in [self.route_index_map[route_hash]]
                for k in range(self.network_data.num_types)
                for s in range(self.network_data.num_samples)
            ),
            GRB.MAXIMIZE
        )


    # add column x_r to RMP
    # input:
    #   new_solution: in-bound + out-bound
    # do:
    #   column_x_r: the coefficient of column x_r, i.e, the solution of x-price subproblem
    # output:
    #   new RMP model
    def add_column_to_RMP(self, new_solution):
        # add the new route to route_solution_set
        if self.route_solution_set.add_new_solution(new_solution) is not None:
            route_hash = self.route_solution_set.get_solution_hash(new_solution)
            logging.info(f"Add new column :,{str(self.route_solution_set.num_feasible_routes - 1)},{new_solution}")
        else:
            logging.info("The column is already in the RMP!")
            logging.info("Add Infeasible Cut to x-PSP/Row-PSP")
            # self.add_infeasible_cut_to_x_PSP(new_solution)
            # self.add_infeasible_cut_to_row_PSP(new_solution)
            self.dual_variables_values.num_feasible_routes -= 1
            return False
        
        # create new column to RMP
        column_x_r = gp.Column()
        # update constraints u0 : add new item to the left of constraint u0
        column_x_r.addTerms(1, self.constr_u0)
        # update constraints u1[i] : add new item to the left of constraint u1[i]
        for i in range(self.network_data.num_ports):
            if self.problem_type == 'Tour':
                if i in new_solution:
                    column_x_r.addTerms(1, self.constr_u1s[i])
            elif self.problem_type == 'Multi-Routes':
                solution_in, solution_out = new_solution
                if i in solution_in:
                    column_x_r.addTerms(1, self.constr_u1s[i])
                if i in solution_out:
                    column_x_r.addTerms(1, self.constr_u1s[i])
        # update constraints u2[i] : add new item to the left of constraint u2[i]
        for i in range(self.network_data.num_ports):
            if self.problem_type == 'Tour':
                if i in new_solution:
                    column_x_r.addTerms(1, self.constr_u2)
            elif self.problem_type == 'Multi-Routes':
                solution_in, solution_out = new_solution
                if i in solution_in:
                    column_x_r.addTerms(self.network_data.ports_df.loc[i,'FixedCost'], self.constr_u2)
                if i in solution_out:
                    column_x_r.addTerms(self.network_data.ports_df.loc[i,'FixedCost'], self.constr_u2)
        # add x_r (column) to RMP
        self.x.append(self.model.addVar(vtype = GRB.CONTINUOUS, 
                                        lb = 0, 
                                        ub = 1, 
                                        obj = 0, 
                                        name = f'x_{len(self.x)}', 
                                        column = column_x_r))

        # create new columns for z_{ks}^r to RMP
        z_r = []
        for k in range(self.network_data.num_types):
            z_r_k = []
            for s in range(self.network_data.num_samples):
                column_z_r_k_s = Column()
                # update constraints v[k][s] : add new item to the left of constraint v[k][s]
                column_z_r_k_s.addTerms(1, self.constr_v[k][s])
                # add variable z_{ks}^r to RMP
                r = len(self.x) - 1
                z_r_k_s = self.model.addVar(vtype = GRB.CONTINUOUS, 
                                            lb = 0, 
                                            ub = 1,
                                            obj = self.route_solution_set.route_utility_set[(route_hash,k)][s],
                                            name = f'z_{len(self.x)-1}_{k}_{s}', 
                                            column = column_z_r_k_s)
                z_r_k.append(z_r_k_s)
            z_r.append(z_r_k)
        self.z.append(z_r)

        # add linking constraints: w[r][k][s] : z_{ks}^r <= x_r, k \in K, s \in S 
        w_r = []
        for k in range(self.network_data.num_types):
            w_k_s = []
            for s in range(self.network_data.num_samples):
                w_k_s.append(self.model.addConstr(self.z[-1][k][s] <= self.x[-1], name = f'RMP-4_{k}_{s}_{len(self.x)-1}'))
            w_r.append(w_k_s)
        self.constr_w.append(w_r)

        #(update RMP model)
        self.model.update()

        return True




    def get_dual_value(self):
        logging.info(f'The number of feasible routes: {self.dual_variables_values.num_feasible_routes}')
        value_u0 = self.constr_u0.Pi
        value_u1 = np.zeros(self.network_data.num_ports)
        for i in range(self.network_data.num_ports):
            value_u1[i] = self.constr_u1s[i].Pi
        value_u2 = self.constr_u2.Pi
        value_v = np.zeros([self.network_data.num_types, 
                            self.network_data.num_samples])
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                value_v[k][s] = self.constr_v[k][s].Pi
        value_w = np.zeros([self.route_solution_set.num_feasible_routes, 
                            self.network_data.num_types, 
                            self.network_data.num_samples])
        feasible_solutions = self.route_solution_set.get_feasible_solutions()
        for r in range(len(feasible_solutions)):
            for k in range(self.network_data.num_types):
                for s in range(self.network_data.num_samples):
                    value_w[r][k][s] = self.constr_w[r][k][s].Pi
        if self.print_dual_values:
            logging.info(f'The dual value of constraint u0: {value_u0}')
            log_message = 'The dual value of constraint u1:'
            for i in range(self.network_data.num_ports):
                log_message += str(value_u1[i]) + ' '
            logging.info(log_message)
            logging.info(f'The dual value of constraint u2: {value_u2}')
            log_message = 'The dual value of constraint v:'
            for k in range(self.network_data.num_types):
                for s in range(self.network_data.num_samples):
                    log_message += str(value_v[k][s]) + ' '
            logging.info(log_message)
            for r in range(self.dual_variables_values.num_feasible_routes):
                log_message = f'The dual value of constraint w[{r}]:'
                for k in range(self.network_data.num_types):
                    for s in range(self.network_data.num_samples):
                        log_message += str(value_w[r][k][s])
                logging.info(log_message)
        return value_u0, value_u1, value_u2, value_v, value_w


    def solve(self, time_limit = 600):
        # self.model.write('model/RMP.lp')
        self.model.Params.TimeLimit = time_limit
        self.model.optimize()
        RMP_obj = self.model.objVal
        if self.model.status == GRB.OPTIMAL and self.model_type == 'LP':
            u0, u1, u2, v, w = self.get_dual_value()
            self.dual_variables_values.update_dual_var_values(u0, u1, u2, v, w)
        logging.info(f'RMP {self.get_model_status(self.model)}')
        self.RMP_obj_value_log.append(self.model.objVal)
        self.print_solution()
        if self.print_primal_values:
            logging.info("RMP solution:")
            log_message = ''
            feasible_solutions = self.route_solution_set.get_feasible_solutions()
            for r in range(len(feasible_solutions)):
                log_message += f'x{r}: {self.x[r].x}'
            logging.info(log_message)
            for r in range(len(feasible_solutions)):
                log_message = ''
                for k in range(self.network_data.num_types):
                    for s in range(self.network_data.num_samples):
                        log_message += f'z[{r}][{k}][{s}]: {self.z[r][k][s].x}' + ' '
                logging.info(log_message)
            logging.info()
        return RMP_obj




    def print_solution(self):
        logging.info(f"RMP objective: {self.model.objVal}")
        route_count = 0
        logging.info(f"The number of candidate routes: {self.route_solution_set.num_feasible_routes}")
        log_message = ''
        feasible_solutions = self.route_solution_set.get_feasible_solutions()
        for r in range(len(feasible_solutions)):
            if self.x[r].X > 0.01:
                log_message += f'x[{r}]={self.x[r].X}' + '\t'
                log_message += f'route{route_count + 1}: {r} {feasible_solutions[r].route}' + '\t'
                log_message += f'port-call{feasible_solutions[r].route}' + '\n'
                route_count += 1
        logging.info(log_message)




    def set_RMP_to_MP(self):
        logging.info("Set X from Continue to Binary")
        self.model_type = 'MILP'
        for r in range(self.route_solution_set.num_feasible_routes):
            self.x[r].vtype = GRB.BINARY
        self.model.update()



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