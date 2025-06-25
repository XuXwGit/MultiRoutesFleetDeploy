import logging
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB, quicksum
from core.algorithms.crg.RMP import RMP
from core.algorithms.crg.xPSP import xPSP
from core.algorithms.crg.rowPSP import rowPSP
import time
import warnings

from design.core.algorithms.dual_var_values import DualVarValues
from design.core.algorithms.route_solution_pool import RouteSolutionPool
from design.core.models.network_data import NetworkData


class ColumnRowGenerationAlgo:
    """列和行生成算法实现类
    
    实现论文4.2节描述的列和行生成算法框架，包含：
    - 主问题(RMP)求解
    - 价格子问题(PSP)求解
    - 行价格子问题(row-PSP)求解
    
    算法流程：
    1. 初始化候选路线集合
    2. 构建RMP、PSP和row-PSP模型
    3. 迭代求解：
       a. 求解RMP获取对偶变量
       b. 求解PSP生成新列
       c. 如果PSP无改进，求解row-PSP
    4. 收敛后求解最终主问题
    
    Attributes:
        network_data: 网络设计数据
        route_solution_set: 候选路线集合
        dual_variables_values: 对偶变量值
        RMP: 主问题模型
        xPSP: 价格子问题模型
        rowPSP: 行价格子问题模型
        optimal_route_set: 最优路线集合
        optimal_port_call_set: 最优港口访问序列
    """
    def __init__(self, network_design_data: NetworkData):
        self.network_data = network_design_data
        
        self.route_solution_set = RouteSolutionPool(network_design_data)
        
        self.dual_variables_values = DualVarValues()
        self.problem_type = network_design_data.problem_type

        # # models in each iteration
        # self.RMP = gp.Model('RMP')
        self.RMP = RMP(network_design_data= network_design_data, 
                       route_solution_set= self.route_solution_set, 
                       dual_variables_values= self.dual_variables_values)
        # self.PSP = gp.Model('PSP')
        self.xPSP = xPSP(network_design_data, self.dual_variables_values)
        # self.rowPSP = gp.Model('RowPSP')
        self.rowPSP = rowPSP(network_design_data, self.dual_variables_values)

        # attrs about output logs
        self.print_solve_log = True
        self.print_dual_values = True
        self.print_primal_values = True
        self.CRG_TimeLimit = 3600
        self.max_iteration = 1000
        self.optimal_route_set = []
        self.optimal_port_call_set = []
    

    # framework
    def solve(self, time_limit: float = 1200) -> dict:
        """执行列和行生成算法
        
        算法主入口，设置参数并启动迭代过程
        
        Args:
            time_limit: 算法时间限制(秒)
            
        Returns:
            dict: 包含最优路线和港口访问序列的字典
        """
        # set output log
        self.setAttr('Solver_OutputFlag', 0 )
        self.setAttr("MIPGap", 0.05)
        self.setAttr('Dual_Values_Flag', 0 )
        self.setAttr('Primal_Values_Flag', 0 )
        self.setAttr('CRG_TimeLimit', time_limit)

        # design_data.RowPSP.Params.TimeLimit = 10
        # set initial solution
        initial_route_set = []
        self.initilaize_design_data(initial_route_set)
        self.build_models()

        # # use column-and-row generation
        self.row_and_column_generation()

        # # draw the iteration cure
        # self.draw_RMP_obj_value()
        # # !!!!!!
        # # Note :
        # # The Column-and-row generation algorithm can't find optimal solution
        # # check the optimal condition of C&RG
        # # not all iteration get the basis
        # # !!!!!!
        routes = {}
        port_calls = {r: [] for r in range(self.network_data.num_routes)}
        for r in range(self.optimal_route_set):
            routes[r] = self.optimal_route_set[r]
            port_calls[r] = self.optimal_port_call_set[r]
        return {
            'routes':routes, 
            'port_calls':port_calls,
            }


    # core iteration algo 
    # solve with column-and-row generation
    def row_and_column_generation(self) -> None:
        """列和行生成算法核心迭代过程
        
        实现论文算法1的迭代流程：
        1. 求解RMP获取对偶变量(算法1步骤3)
        2. 求解PSP检查reduced cost(算法1步骤4-6)
        3. 如果PSP无改进，求解row-PSP(算法1步骤7-9)
        4. 添加新列到RMP(算法1步骤10)
        5. 重复直到收敛
        
        终止条件：
        - 达到最大迭代次数
        - 超过时间限制
        - PSP和row-PSP都无改进(reduced cost ≤ 0)
        """
        logging.info('=========================Start Column-and-Row Generation=========================')
        flag = True
        solve_row_PSP = False
        iteration = 0
        start_time = time.time()
        while flag and iteration < self.max_iteration and time.time() - start_time < self.CRG_TimeLimit:
            logging.info(f'=========================Iteration: {iteration}=========================')
            iteration += 1
            logging.info(f'====>>>>==Solve RMP {iteration}:==<<<<====')
            self.RMP.solve()
            # self.set_select_ports_to_PSP(self.heuristic_select_ports(self.dual_variables_values))
            ## case A
            logging.info(f'====>>>>==Solve PSP {iteration}:==<<<<====')
            self.xPSP.update_PSP()
            self.xPSP.solve()
            # check reduced cost (the optimal solution of PSP)
            if self.xPSP.model.Status != GRB.Status.OPTIMAL or self.xPSP.model.objVal <= 1e-8:
                solve_row_PSP = True
                if self.xPSP.model.Status == GRB.Status.OPTIMAL:
                    logging.info(f'Maximum x-price Reduced Cost ={self.xPSP.model.objVal} <= threshold (1e-8)')
                    logging.info(f'PSP solution: {self.xPSP.get_solution_from_PSP()}')
            else:
                solve_row_PSP = False
                logging.info(f'Maximum x-price Reduced Cost ={self.xPSP.model.objVal} >= 0')
                solution = self.xPSP.get_solution_from_PSP()
                # add new column to RMP
                if self.RMP.add_column_to_RMP(solution):
                    logging.info(f"add column from row-price:{solution}")
                else:
                    continue
                self.xPSP.add_infeasible_cut_to_x_PSP(solution)
                self.rowPSP.add_infeasible_cut_to_row_PSP(solution)
                
            ## case B
            if solve_row_PSP:
                logging.info(f'====>>>>==Solve row-PSP {iteration}:==<<<<====')
                self.rowPSP.update_row_PSP()
                solution, objVal = self.rowPSP.solve()
                # check reduced cost (the optimal solution of row-PSP)
                if self.rowPSP.model.Status != GRB.Status.OPTIMAL or objVal <= 1e-6:
                    flag = False
                    if self.rowPSP.model.Status == GRB.Status.OPTIMAL:
                        logging.info(f'Maximum row-price Reduced Cost ={objVal} <= 0')
                else:
                    logging.info(f'Maximum row-price Reduced Cost ={objVal} >= 0')
                    # add new column to RMP
                    if self.RMP.add_column_to_RMP(solution):
                        logging.info(f"add column from row-price:{solution}")
                    else:
                        continue
                    self.xPSP.add_infeasible_cut_to_x_PSP(solution)
                    self.rowPSP.add_infeasible_cut_to_row_PSP(solution)
            
        # final column generation
        # set RMP to be MP
        self.RMP.set_RMP_to_MP()
        logging.info('====>>>>==Solve MP:==<<<<====')
        self.RMP.solve()
        self.RMP.print_solution()
        # print MP objective
        logging.info('=========================End Column-and-Row Generation=========================')

        # set the optimal routes
        for r in range(self.route_solution_set.num_feasible_routes):
            if self.RMP.x[r].X > 0.5:
                self.optimal_route_set.append(self.route_solution_set.route_set[r])
                self.optimal_port_call_set.append(self.route_solution_set.solution_set[r])



    def initilaize_design_data(self, initial_route_set: list = []) -> 'ColumnRowGenerationAlgo':
        """初始化算法数据
        
        根据论文4.1节生成初始候选路线集合：
        - 如果提供初始路线，直接使用
        - 否则生成简单序列路线
        
        Args:
            initial_route_set: 初始路线集合
            
        Returns:
            ColumnRowGenerationAlgo: 返回self以支持链式调用
        """
        if len(initial_route_set) != 0:
            for r in range(len(initial_route_set)):
                self.route_solution_set.add_new_solution(initial_route_set[r])
        else:
            # generate a initial solution
            start = 0
            flag = True
            while flag:
                solution = []
                if self.problem_type == 'Tour':
                    end = min(start + self.network_data.max_length, self.network_data.num_ports)
                    solution = np.array(range(start, end)).tolist()
                elif self.problem_type == 'Multi-Routes':
                    if start + self.network_data.max_length <= self.network_data.num_ports:
                        end = start + self.network_data.min_length
                        # in-bound
                        solution.append(np.array(range(start, end)).tolist())
                        # out-bound: note to reverse the port call sequence
                        solution.append(np.array(range(end, end + self.network_data.max_length - len(solution[0]))).tolist()[::-1])
                        if len(solution[0] + solution[1] )< self.network_data.max_length:
                            solution[1] = solution[1]+(np.array(range(0, self.network_data.max_length -  len(solution[0] + solution[1]))[::-1]).tolist())
                    else:
                        end = self.network_data.num_ports
                        # in-bound
                        solution.append(np.array(range(start, end)).tolist())
                        # out-bound
                        solution.append(np.array(range(0, self.network_data.max_length - (end - start))).tolist()[::-1])
                    # logging.info(solution)
                logging.info(f'Initial solution:{solution}')
                self.route_solution_set.add_new_solution(solution)
                if end == self.network_data.num_ports:
                    flag = False
                else:
                    start += int(self.network_data.min_length)
        logging.info('Initialize route solution set: %d' % self.route_solution_set.num_feasible_routes)
        self.route_solution_set.print_solution_set()
        
        self.dual_variables_values.initialize(
            self.network_data.num_ports, 
            self.network_data.num_types,
            self.network_data.num_samples, 
            self.route_solution_set.num_feasible_routes
        )
        return self




    def setAttr(self, attr_name, attr_value):
        if attr_name == 'Solver_OutputFlag':
            self.print_solve_log = attr_value
            self.RMP.model.Params.OutputFlag = attr_value
            self.xPSP.model.Params.OutputFlag = attr_value
            self.rowPSP.model.Params.OutputFlag = attr_value
        elif attr_name == 'Dual_Values_Flag':
            self.print_dual_values = attr_value
        elif attr_name == 'Primal_Values_Flag':
            self.print_primal_values = attr_value
        elif attr_name == 'CRG_TimeLimit':
            self.CRG_TimeLimit = attr_value
        elif attr_name == 'MIPGap':
            self.rowPSP.model.Params.MIPGap = attr_value



    def calculate_total_utility_route_capture(self):
        for r in range(self.route_solution_set.num_feasible_routes):
            total_utility_r = 0
            for k in range(self.network_data.num_types):
                for s in range(self.network_data.num_samples):
                    total_utility_r += self.route_solution_set.route_utility_set[(r, k)][s] * self.z[r][k][s].x
            logging.info("Route ", r, " : ", total_utility_r)
        return True
    



    def set_select_ports_to_PSP(self, select_ports):
        self.xPSP.build_PSP()
        self.rowPSP.build_rowPSP()
        for i in range(self.network_data.num_ports):
            if i not in select_ports:
                self.psp_y_in[i].ub = 0
                self.psp_y_out[i].ub = 0
                self.row_y_in[i].ub = 0
                self.row_y_out[i].ub = 0
        self.xPSP.model.update()
        self.rowPSP.model.update()



    def heuristic_select_ports(self, dual_value):
        value_u0 = dual_value.value_u0
        value_u1 = dual_value.value_u1
        value_u2 = dual_value.value_u2
        value_v = dual_value.value_v
        alpha_v = {}
        for k in range(self.network_data.num_types):
            for s in range(self.network_data.num_samples):
                alpha_v[(k, s)] = self.network_data.constants[k] + self.network_data.varepsion[k][s] - value_v[k][s]
        sorted_alpha_v = sorted(alpha_v.items(), key=lambda x: x[1], reverse=True)
        select_ports = []
        iter = 0
        while len(select_ports) < self.network_data.max_length:
            k = sorted_alpha_v[iter][0][0]
            origin_k = self.network_data.od_pairs[k][0]
            destination_k = self.network_data.od_pairs[k][1]
            if origin_k not in select_ports:
                select_ports.append(origin_k)
            if destination_k not in select_ports:
                select_ports.append(destination_k)
            iter += 1
        return select_ports



    
    def build_models(self):
        self.RMP.bulid_RMP()
        self.xPSP.build_PSP()
        self.rowPSP.build_rowPSP()



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




    def build_check_model(self, solution_set):
        column_set = RouteSolutionPool(self.network_data)
        for solution in solution_set:
            column_set.add_new_solution(solution)
        CMP = gp.Model('CMP')
        x = []
        for r in range(column_set.num_feasible_routes):
            x_r = CMP.addVar(vtype=GRB.BINARY, lb=0, obj=0, name=f'x[{r}]')
            x.append(x_r)
        z = []
        for r in range(column_set.num_feasible_routes):
            z_r = []
            for k in range(self.network_data.num_types):
                z_r_k = []
                for s in range(self.network_data.num_samples):
                    z_r_k_s = CMP.addVar(
                        vtype=GRB.BINARY, lb=0,
                        obj=column_set.route_utility_set[(r, k)][s],
                        name=f'z[{r}][{k}][{s}]'
                    )
                    z_r_k.append(z_r_k_s)
                z_r.append(z_r_k)
            z.append(z_r)
        CMP.addConstr(quicksum(x) <= self.network_data.num_routes, name='CMP-U0')
        for i in range(self.network_data.num_ports):
            CMP.addConstr(
                quicksum(x_r for r, x_r in enumerate(x) 
                         if i in column_set.route_set[r]) >= 1,
                name=f'CMP-U1_{i}'
            )
        for k in range(self.network_data.num_types):
            v_k = []
            for s in range(self.network_data.num_samples):
                v_k.append(CMP.addConstr(
                    quicksum(z_r[k][s] for r, z_r in enumerate(z)) <= 1,
                    name=f'CMP-V_{k}_{s}'
                ))
        for r in range(column_set.num_feasible_routes):
            w_r = []
            for k in range(self.network_data.num_types):
                w_k_s = []
                for s in range(self.network_data.num_samples):
                    w_k_s.append(CMP.addConstr(z[r][k][s] <= x[r], name=f'CMP-W[{k}][{s}][{r}]'))
                w_r.append(w_k_s)
            self.constr_w.append(w_r)
        CMP.ModelSense = GRB.MAXIMIZE
        CMP.update()
        return CMP