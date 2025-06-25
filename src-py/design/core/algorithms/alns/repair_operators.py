from abc import ABC, abstractmethod
import random
import copy
import numpy.random as rnd

from design.core.models.design_solution import DesignSolution
from design.core.models.network_data import NetworkData
from design.core.models.route_solution import RouteSolution


def greedy_repair(state:DesignSolution, rng: rnd.Generator = rnd.default_rng()):
    """
    Inserts the unassigned customers in the best route. If there are no
    feasible insertions, then a new route is created.
    """
    rng.shuffle(state.unassigned_nodes)

    while len(state.unassigned_nodes) != 0:
        node = state.unassigned_nodes.pop()
        route_solution, idx = best_insert(node, state)

        if route_solution is not None:
            route_solution.route.insert(idx, node)
        else:
            state.route_solutions.append(RouteSolution(route=[node], network_data=state.network_data))

    state.update()
    return state


def best_insert(node, state:DesignSolution):
    """
    Finds the best feasible route and insertion idx for the customer.
    Return (None, None) if no feasible route insertions are found.
    """
    best_cost, best_route_solution, best_idx = None, None, None

    for route_solution in state.route_solutions:
        if can_insert(node, route_solution):
            for idx in range(len(route_solution.route)):
                cost = insert_cost(node, route_solution, idx)

                if best_cost is None or cost < best_cost:
                    best_cost, best_route_solution, best_idx = cost, route_solution, idx

    return best_route_solution, best_idx


def can_insert(node, route_solution: RouteSolution) -> bool:
    """
    Checks if inserting customer does not exceed vehicle capacity.
    """
    if len(route_solution.route) + 1 > route_solution._network_data.max_length:
        return False
    return True
    
    


def insert_cost(node, route_solution: RouteSolution, idx):
    """
    Computes the insertion cost for inserting customer in route at idx.
    """
    dist = route_solution._network_data.distance_matrix
    pred = 0 if idx == 0 else route_solution.route[idx - 1]
    succ = 0 if idx == len(route_solution.route) else route_solution.route[idx]

    # Increase in cost of adding customer, minus cost of removing old edge
    return dist[pred][node] + dist[node][succ] - dist[pred][succ]


class RepairOperator(ABC):
    """修复操作抽象基类"""
    @abstractmethod
    def execute(self, removed_ports, solution, network_data: NetworkData):
        pass

    def insert_in_bound(self, node, bounds: list, network_data: NetworkData):
        min_idx = -1
        min_cost = 1e8
        for i in range(len(bounds) - 1):
            if network_data.distance_matrix[bounds[i]][node] + network_data.distance_matrix[node][bounds[i+1]] - network_data.distance_matrix[bounds[i]][bounds[i+1]] < min_cost:
                min_idx = i
                min_cost = network_data.distance_matrix[bounds[i]][node] + network_data.distance_matrix[node][bounds[i+1]] - network_data.distance_matrix[bounds[i]][bounds[i+1]]
        bounds.insert(min_idx, node)

        return bounds

class RandomRepair(RepairOperator):
    """随机修复策略"""
    def execute(self, removed_ports, solution, network_data: NetworkData):
        if isinstance(removed_ports, list):
            random.shuffle(removed_ports)
        
        if isinstance(solution, DesignSolution):
            solution_copys = [copy.deepcopy(route_solution.route) for route_solution in solution.route_solutions]
            while removed_ports:
                port = removed_ports.pop(0)
                select_solution_idx = random.randint(0, len(solution_copys) - 1)
                if port in solution_copys[select_solution_idx] or port in solution_copys[select_solution_idx]:
                    continue
                solution_copys[select_solution_idx] = self.insert_in_bound(port, solution_copys[select_solution_idx], network_data)
            new_design_solution = DesignSolution(network_data=network_data)
            for new_route in solution_copys:
                new_design_solution.add_route_solution(RouteSolution(route=new_route, network_data= network_data))
            return new_design_solution
        elif isinstance(solution, RouteSolution):
            #...
            return
        elif isinstance(solution, list):
            solution_copy = copy.deepcopy(solution)
            for port in removed_ports:
                solution_copy = self.insert_in_bound(port, solution_copy)
            return solution_copy
        else:
            for port in removed_ports:
                solution_copy = copy.deepcopy(solution)
                if random.random() < 0.5:
                    solution_copy[0] = self.insert_in_bound(port, solution_copy[0], network_data)
                else:
                    solution_copy[1] = self.insert_in_bound(port, solution_copy[1], network_data)
            return solution_copy
        return solution_copy

class DistanceGreedyRepair(RepairOperator):
    """基于距离的贪心修复策略"""
    def execute(self, removed_ports, route_solution, network_data: NetworkData):
        removed_ports = copy.deepcopy(removed_ports)
        
        while removed_ports:
            port = removed_ports.pop(0)
            best_insertion = None
            min_distance = float('inf')
            
            if isinstance(route_solution, RouteSolution):
                ## need to modify
                route_solution.route = self.insert_in_bound(port, route_solution.route)
            
            elif isinstance(route_solution, DesignSolution):
                solution_copys = [copy.deepcopy(route_solution.route) for route_solution in route_solution.route_solutions]
                for r, route in enumerate(solution_copys):
                        for i in range(len(route)):
                            if network_data.distance_matrix[route[i-1]][port] + network_data.distance_matrix[port][route[i]] - network_data.distance_matrix[route[i-1]][route[i]] < min_distance:
                                best_insertion = (r, i)
                                min_distance = network_data.distance_matrix[route[i-1]][port] + network_data.distance_matrix[port][route[i]] - network_data.distance_matrix[route[i-1]][route[i]]
                if port not in solution_copys[best_insertion[0]]:
                    solution_copys[best_insertion[0]].insert(best_insertion[1], port)
                new_design_solution = DesignSolution(network_data=network_data)
                for new_route in solution_copys:
                    new_design_solution.add_route_solution(RouteSolution(route=new_route, network_data= network_data))
                return new_design_solution

        return route_solution

class RepairOperatorFactory:
    """修复操作工厂类"""
    @staticmethod
    def create(operator_type):
        operators = {
            'random': RandomRepair(),
            'distance_greedy': DistanceGreedyRepair()
        }
        return operators.get(operator_type, RandomRepair())

# 保持原有函数接口兼容
def random_repair(*args, **kwargs):
    return RandomRepair().execute(*args, **kwargs)

def distance_greedy_repair(*args, **kwargs):
    return DistanceGreedyRepair().execute(*args, **kwargs)
