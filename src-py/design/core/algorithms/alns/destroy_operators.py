import random
import copy

from design.core.models.design_solution import DesignSolution
from design.core.models.route_solution import RouteSolution


def random_removal(state: DesignSolution, rng) -> DesignSolution:
    """
    Removes a number of randomly selected customers from the passed-in solution.
    """
    destroyed = state.copy()
    degree_of_destruction = 0.05
    nodes_to_remove = int((state.network_data.num_ports - 1) * degree_of_destruction)
    for node in rng.choice(
        range(0, state.network_data.num_ports), nodes_to_remove, replace=False
    ):
        destroyed.unassigned_nodes.append(node)
        route_solution = destroyed.find_route_solution(node)
        if route_solution is not None:
            route_solution.remove_node(node)

    return remove_empty_routes(destroyed)


def remove_empty_routes(state: DesignSolution)-> DesignSolution:
    """
    Remove empty routes after applying the destroy operator.
    """
    state.route_solutions = [route_solution for route_solution in state.route_solutions if len(route_solution.route) != 0]
    return state


def random_destroy(solution: DesignSolution, destroy_rate: float) -> DesignSolution:
    """
    随机移除一定比例的港口
    """
    solution_copy = solution.copy()
    for route_solution in solution.route_solutions:
        route_solution = random_destroy_single_route(route_solution, destroy_rate=destroy_rate)

    return solution_copy

def random_destroy_single_route(solution: RouteSolution, destroy_rate: float) -> RouteSolution:
    """
    随机移除一定比例的港口
    """
    solution_copy = copy.deepcopy(solution)
    all_ports = solution_copy.route
    num_ports_to_remove = int(len(all_ports) * destroy_rate)
    removed_ports = random.sample(all_ports, num_ports_to_remove)
    
    # 更新solution_copy的route
    solution_copy._route = [p for p in solution_copy.route if p not in removed_ports]
    solution_copy.update(solution_copy.route)

    return solution_copy

def cost_based_destroy(solution, destroy_rate):
    if isinstance(solution, DesignSolution):
        total_removed_ports = []
        total_design_solution = DesignSolution(network_data= solution.network_data)
        for route_solution in solution.route_solutions:
            removed_ports, solution_copy = cost_based_destroy_single_route(route_solution, destroy_rate=destroy_rate)
            total_removed_ports += removed_ports
            total_design_solution.add_route_solution(route_solution=solution_copy)
        return total_design_solution

def cost_based_destroy_single_route(solution: RouteSolution, destroy_rate: float) -> RouteSolution:
    """
    基于【成本】移除港口
    """
    solution_copy = copy.deepcopy(solution)
    ports_with_cost = []
    
    for port in solution_copy.route:
        ports_with_cost.append((port, solution_copy._network_data.fixed_cost[port]))
    
    ports_with_cost.sort(key=lambda x: x[1], reverse=True)
    num_ports_to_remove = int(len(ports_with_cost) * destroy_rate)
    removed_ports = [p[0] for p in ports_with_cost[:num_ports_to_remove]]
    
    # 更新solution_copy的route
    solution_copy._route = [p for p in solution_copy.route if p not in removed_ports]
    solution_copy.update(solution_copy.route)
    
    return solution_copy