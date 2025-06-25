import logging
import numpy as np
import pandas as pd
import gurobipy as gp
from gurobipy import GRB, quicksum
from design.core.algorithms.crg.RMP import RMP
from design.core.algorithms.crg.xPSP import xPSP
from design.core.algorithms.crg.rowPSP import rowPSP
import time
import warnings

from design.core.algorithms.alns.alns_core import ALNSSolver
from design.core.algorithms.crg.CRG_core import ColumnRowGenerationAlgo
from design.core.algorithms.dual_var_values import DualVarValues
from design.core.algorithms.route_solution_pool import RouteSolutionPool
from design.core.models.design_solution import DesignSolution
from design.core.models.route_solution import RouteSolution
from design.core.models.network_data import NetworkData


class AlgoCore:
    def __init__(self, network_design_data: NetworkData, service_logger: logging.Logger):
        self.network_data = network_design_data
        self.service_logger = service_logger if service_logger is not None else logging.getLogger('algo_logger')
        
        self.route_solution_set = RouteSolutionPool(network_design_data)
        self.column_and_row_generation = ColumnRowGenerationAlgo(network_design_data)
        self.alns_for_multi_routes = ALNSSolver(network_data= self.network_data, problem_type="Multi-Routes", obj_type="Utility")
        self.design_solutions = DesignSolution(network_design_data)

    def set_initial_solution(self, initial_design_solution: DesignSolution):
        self.alns_for_multi_routes.set_initial_solution(initial_design_solution)

    def set_obj_type(self, obj_type = "Utility"):
        self.alns_for_multi_routes.set_obj_type(obj_type=obj_type)

    # framework
    def print_algorithm_parameters(self):
        """打印算法关键参数"""
        self.service_logger.info("============ Algorithm Parameters ===========")
        self.service_logger.info(f"Algorithm Type: {'ALNS' if hasattr(self, 'alns_for_multi_routes') else 'Column-Row Generation'}")
        if hasattr(self, 'alns_for_multi_routes'):
            self.service_logger.info(f"Objective Type: {getattr(self.alns_for_multi_routes, 'obj_type', 'Not set')}")
        self.service_logger.info(f"Time Limit: {getattr(self, 'time_limit', 'Not set')} seconds")
        self.service_logger.info(f"Maximum Iterations: {getattr(self, 'max_iterations', 'Not set')}")
        self.service_logger.info("=============================================")

    def solve(self, time_limit: float = 1200, max_iterations: int = 1200) -> dict:
        """算法主入口，设置参数并启动迭代过程
        Args:
            time_limit: 算法时间限制(秒)
            
        Returns:
            dict: 包含最优路线和港口访问序列的字典
        """
        self.time_limit = time_limit
        self.max_iterations = max_iterations
        self.print_algorithm_parameters()
        
        try:
            # # # use column-and-row generation
            # routes = self.column_and_row_generation.solve(time_limit)

            # # use ALNS to solve
            self.service_logger.info("============ Run Core Algo Optimization Start ===========")
            routes = self.alns_for_multi_routes.solve(time_limit=time_limit, max_iterations=self.max_iterations)
            self.service_logger.info("============ Run Core Algo Optimization End ===========")

            self.design_solutions.initialize()
            self.design_solutions = routes["design_solution"].copy()

            self.service_logger.info("============ Print Algo Optimization Solution Start ===========")
            self.design_solutions.print_design_solution()
            self.service_logger.info("============ Print Algo Optimization Solution End ===========")
            
            return {
                'routes':routes['routes'], 
                'port_calls':routes['port_calls'],
                "design_solution": self.design_solutions.copy()
            }
        except Exception as e:
            self.service_logger.debug(f"There is error while running: {e}")

            return None
