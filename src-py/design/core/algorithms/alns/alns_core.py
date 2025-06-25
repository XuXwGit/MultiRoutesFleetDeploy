import logging
import random
import matplotlib.pyplot as plt
from tqdm import tqdm
import numpy.random as rnd

from design.core.models.design_solution import DesignSolution
from design.core.models.route_solution import RouteSolution
import design.lib.alns as alns
from design.lib.alns.accept import HillClimbing
from design.lib.alns.select import RandomSelect
from design.lib.alns.stop import MaxRuntime
from design.lib.alns import ALNS

from design.core.algorithms.route_solution_pool import RouteSolutionPool
from design.core.models.network_data import NetworkData
from .destroy_operators import random_destroy_single_route, cost_based_destroy_single_route, random_removal
from .repair_operators import greedy_repair, random_repair, distance_greedy_repair
from .acceptance_criteria import SimulatedAnnealing
from .initial_solution import generate_initial_design_solution, generate_initial_route_solution
from .operator import OperatorFactory
from abc import ABC, abstractmethod

class ALNSSolver:
    def __init__(self,
                 network_data: NetworkData,
                 problem_type = "Multi-Routes",
                 obj_type = "Utility"
                 ):
        """
        Parameters
        ----------
        network_data
            Network data for the problem
        problem_type
            Type of problem to solve (default: "Multi-Routes")
        obj_type
            Type of objective ("Cost" for minimization, "Utility" for maximization)
            Default is "Cost"
        """
        self.network_data = network_data
        self.problem_type = problem_type
        self.obj_type = obj_type
        self.init_sol = None
       
    
    def set_initial_solution(self, initial_design_solution: DesignSolution):
        self.init_sol = initial_design_solution.copy()

    def set_obj_type(self, obj_type):
        self.obj_type = obj_type
        self.init_sol.obj_type = obj_type

    def solve(self, time_limit = 100, max_iterations = 1200):
        # Create the initial solution
        if self.init_sol is None:
            self.init_sol = generate_initial_design_solution(self.network_data)
        print(f"Initial solution objective is {self.init_sol.objective()}.")

        # Create ALNS and add one or more destroy and repair operators
        # Set optimization direction based on obj_type
        opt_dir = "minimize" if self.obj_type == "Cost" else "maximize"
        alns = ALNS(rnd.default_rng(seed=42), optimization_direction=opt_dir)
        alns.add_destroy_operator(random_removal)
        alns.add_repair_operator(greedy_repair)

        # Configure ALNS
        select = RandomSelect(num_destroy=1, num_repair=1)  # see alns.select for others
        accept = HillClimbing()  # see alns.accept for others
        stop = MaxRuntime(time_limit)  # 60 seconds; see alns.stop for others

        # Run the ALNS algorithm
        result = alns.iterate(self.init_sol, select, accept, stop, max_iterations= max_iterations)
        _, ax = plt.subplots(figsize=(12, 6))
        result.plot_objectives(ax=ax)

        # Retrieve the final solution
        best = result.best_state
        print(f"Best heuristic solution objective is {best.objective()}.")

        if isinstance(best, DesignSolution):
            return {
                'routes': {r: best.route_solutions[r].route for r in range(self.network_data.num_routes)},
                'port_calls': {r: best.route_solutions[r].port_call_sequence for r in range(self.network_data.num_routes)},
                'cycle_times': [round(best.route_solutions[r].round_trip_time, 1) for r in range(self.network_data.num_routes)],
                'total_cost': round(best.total_cost, 2),
                'design_solution': best
            }
        else:
            return None