import logging
from math import exp
from typing import List, Optional
from design.lib.alns.State import State
from design.core.models.candidate_path import CandidatePath
from design.core.models.network_data import NetworkData
from design.core.models.route_solution import RouteSolution
from design.utils.config import Config

class DesignSolution:
    """表示航运网络设计解决方案的类
    
    Attributes:
        network_data (NetworkData): 网络数据对象
        obj_type (str): 优化目标类型('Utility'/'Cost'/'Demand')
    """
    
    def __init__(self, network_data: NetworkData, route_solutions: list = None, obj_type: str = "Utility"):
        """初始化设计解决方案
        
        Args:
            network_data: 网络数据对象
            route_solutions: 初始路径解决方案列表
            obj_type: 优化目标类型('Utility'/'Cost'/'Demand')
        """
        self.network_data = network_data
        self.route_solutions = []
        self.route_solution_hashs = {}

        # 初始化指标
        self.total_cost = 0.0
        self.total_cover_cost = 0.0
        self.total_travel_cost = 0.0
        self.total_utility = 0.0
        self.total_capatured_demand = 0.0

        # 初始化覆盖节点和中转节点
        self.cover_nodes = {}
        self.transit_nodes = {}

        # 初始化OD候选路径列表
        self.od_candidate_paths = {}
        self.unassigned_nodes = []
        self.obj_type = obj_type
        self.optimization_direction = "minimize" if obj_type == "Cost" else "maximize"

        if route_solutions is not None and route_solutions != []:
            for route_solution in route_solutions:
                self.add_route_solution(route_solution=route_solution)

    def get(self,attribute: str, default=None):
        if hasattr(self, attribute):
            return getattr(self, attribute)
        return default

    def initialize(self):
        """重置所有解决方案指标和数据结构"""
        self.route_solutions = []
        self.route_solution_hashs = {}
        self.total_cost = 0
        self.total_cover_cost = 0
        self.total_travel_cost = 0
        self.total_utility = 0
        self.total_capatured_demand = 0
        self.cover_nodes = {}
        self.transit_nodes = {}
        self.od_candidate_paths = {}
        self.unassigned_nodes = []

    def copy(self) -> 'DesignSolution':
        """创建当前解决方案的深拷贝
        
        Returns:
            一个新的DesignSolution实例，包含当前解决方案的副本
        """
        route_solutions_copy = [route_solution.copy() for route_solution in self.route_solutions]
        return DesignSolution(network_data=self.network_data,
                            route_solutions=route_solutions_copy,
                            obj_type=self.obj_type)

    def update(self) -> None:
        """更新解决方案状态，重新计算所有指标
        
        先重置所有指标，然后基于当前路径解决方案重新计算
        """
        route_solutions = self.route_solutions.copy()
        self.initialize()
        if route_solutions:
            for route_solution in route_solutions:
                self.add_route_solution(route_solution=route_solution)

    def find_route_solution(self, node: int) -> Optional[RouteSolution]:
        """查找包含指定节点的路径解决方案
        
        Args:
            node: 要查找的节点ID
            
        Returns:
            包含该节点的RouteSolution实例，如果未找到则返回None
        """
        for route_solution in self.route_solutions:
            if node in route_solution.route:
                if len(route_solution.route) > self.network_data.min_length:
                    return route_solution

        logging.debug(f"No feasible route solution contains node {node}")
        return None

    def objective(self):
        """
        Computes the total route costs.
        """
        objective_value = 0
        if self.obj_type == "Utility":
            objective_value = self.total_utility
        elif self.obj_type == "Cost":
            objective_value = self.total_cost
        elif self.obj_type == "Demand":
            objective_value = self.total_capatured_demand
        return objective_value if self.optimization_direction == "minimize" else objective_value

    def add_route_solution(self, route_solution: RouteSolution):
        """增加路径解并更新相关数据结构
        Args:
            route_solution: 要添加的路径解
        """
        route_hash = RouteSolution.get_route_hash(route_solution.route)
        if route_hash in self.route_solution_hashs:
            return
        
        if route_solution.route is None or route_solution.route == []:
            return
        
        self.route_solution_hashs[route_hash] = len(self.route_solutions)

        self.route_solutions.append(route_solution)
        
        # 更新覆盖节点
        for node in set(route_solution.route):
            if node not in self.cover_nodes:
                self.cover_nodes[node] = 1
            else:
                self.cover_nodes[node] += 1
                if node not in self.transit_nodes:
                    self.cover_nodes[node] = self.cover_nodes.get(node, 0) + 1
                else:
                    self.transit_nodes[node] = self.transit_nodes.get(node, 0) + 1
            
        # 更新OD候选路径列表
        self.update_path_list(route_solution)

        # 更新指标
        self.update_design_metrics()

    def update_path_list(self, route_solution: RouteSolution) -> None:
        """更新路径列表，补充中转路径
        Args:
            route_solution: 新添加的路径解
        Raises:
            ValueError: 如果路径解无效
        """
        if not route_solution or not route_solution.route:
            logging.warning("Invalid route solution")
            return

        # 添加直达路径
        for o in route_solution.route:
            for d in route_solution.route:
                if o == d:
                    continue
                subpath = route_solution.get_subpath(o, d) if hasattr(route_solution, 'get_subpath') else []
                direct_path = CandidatePath(
                    od_pair=(o, d),
                    is_direct=True,
                    arcs=[(subpath[i], subpath[i+1]) for i in range(len(subpath) - 1)],
                    transit_count=0,
                    belong_route_solutions=[route_solution]
                )
                direct_path.travel_time = self.network_data.calculate_travel_time(direct_path.arcs)
                direct_path.utility = self.network_data.calculate_utility(direct_path.travel_time, o, d)
                if (o, d) not in self.od_candidate_paths:
                    self.od_candidate_paths[(o, d)] = []
                if direct_path is not None:
                    self.od_candidate_paths[(o, d)].append(direct_path)
        
        # 添加中转路径
        for od_pair in self.network_data.od_pairs:
            if od_pair not in self.od_candidate_paths:
                self.od_candidate_paths[od_pair] = []
            
            (o, d) = od_pair
            # 查找中转路径
            for transit_node in self.transit_nodes:
                if transit_node in od_pair:  # 中转节点不能是OD本身
                    continue
                
                # 当前路径解不存在此中转节点
                if transit_node not in route_solution.route:
                    continue
                    
                # 检查是否存在从O到中转节点和从中转节点到D的路径
                if o in route_solution.route:
                    o_to_transits = self.od_candidate_paths.get((o, transit_node), [])
                    # o 和 transit_node 均在route之中：新增 o_to_transit 为直达路径
                    o_to_transit = o_to_transits[-1]
                    # 从候选路径中提取 transit_to_d 运输路径
                    transit_to_ds = self.od_candidate_paths.get((transit_node, d), [])
                            
                    if o_to_transit and transit_to_ds != []:
                        for transit_to_d in transit_to_ds:
                            if transit_to_d.transit_count >= Config.MAXIMUM_TRANSIT_LIMIT:
                                continue
                            # 创建中转路径
                            transit_path = CandidatePath.merge(o_to_transit=o_to_transit, transit_to_d=transit_to_d)
                            transit_path.travel_time = self.network_data.calculate_travel_time(transit_path.arcs)
                            transit_path.utility = self.network_data.calculate_utility(transit_path.travel_time, o, d)
                            if transit_path is not None:
                                self.od_candidate_paths[od_pair].append(transit_path)

                if d in route_solution.route:
                    transit_to_ds = self.od_candidate_paths.get((transit_node, d), [])
                    # transit_node和 d 均在route之中：新增 transit_to_d 为直达路径
                    transit_to_d = transit_to_ds[-1]
                    # 从候选路径中提取 o_to_transit 运输路径
                    o_to_transits = self.od_candidate_paths.get((o, transit_node), [])
                            
                    if transit_to_d and o_to_transits != []:
                        for o_to_transit in o_to_transits:
                            if transit_to_d.transit_count >= Config.MAXIMUM_TRANSIT_LIMIT:
                                continue
                            # 创建中转路径
                            transit_path = CandidatePath.merge(o_to_transit=o_to_transit, transit_to_d=transit_to_d)
                            transit_path.travel_time = self.network_data.calculate_travel_time(transit_path.arcs)
                            transit_path.utility = self.network_data.calculate_utility(transit_path.travel_time, o, d)
                            if transit_path is not None:
                                self.od_candidate_paths[od_pair].append(transit_path)

    def update_design_metrics(self):
        self.total_cost = 0
        self.total_cover_cost = 0
        self.total_travel_cost = 0
        for route_solution in self.route_solutions:
            self.total_cost += route_solution.cost
            self.total_cover_cost += route_solution.cover_cost
            self.total_travel_cost += route_solution.travel_cost
        
        self.total_utility = 0
        for od in self.network_data.od_pairs:
            utility = 0
            for candidate_path in self.od_candidate_paths[od]:
                utility = max(utility, candidate_path.utility)
            self.total_utility += utility

        self.total_capatured_demand = 0
        for od in self.network_data.od_pairs:
            total_exp_utility = 1
            for candidate_path in self.od_candidate_paths[od]:
                total_exp_utility += exp(candidate_path.utility)
            
            choice_probability = 0
            for candidate_path in self.od_candidate_paths[od]:
                choice_probability = exp(candidate_path.utility) / total_exp_utility
                candidate_path.choice_probability = choice_probability
                candidate_path.capatured_demand = self.network_data.od_demands[od] * choice_probability
                self.total_capatured_demand += candidate_path.capatured_demand


    # remove infeasible route solution
    def print_metrics(self):
        logging.debug(
             f"Cost {self.total_cost:.2f} = {self.total_cover_cost:.2f} + {self.total_travel_cost:.2f} | "
             f"Utility: {self.total_utility:.2f} | "
             f"Capatured Demand: {self.total_capatured_demand:.2f}")

    def print_design_solution(self):
        logging.info('=========== Design Solution Information ===========')
        logging.info(f"Optimization Objective: {self.obj_type}")
        logging.info(f'Route Structure: ')
        for r in range(len(self.route_solutions)):
            logging.info(f"{r}: {self.route_solutions[r]}")
        logging.info(f"Total Cost: {self.total_cost:.2f}")
        logging.info(f"Total Cover Cost: {self.total_cover_cost:.2f}")
        logging.info(f"Total Travel Cost: {self.total_travel_cost:.2f}")
        logging.info(f"Total Utility: {self.total_utility}")
        logging.info(f"Total Capatured Demand: {self.total_capatured_demand:.2f}")
        total_candidate_path = 0
        total_candidate_path = sum(len(candidatepaths) for od, candidatepaths in self.od_candidate_paths.items())
        logging.info(f"The total number of candidate paths: {total_candidate_path}")
        logging.info('=========== Design Solution Information ===========')

    def to_dict(self) -> dict:
        """将DesignSolution对象转换为可序列化的字典格式
        
        Returns:
            dict: 包含解决方案所有重要信息的字典
        """
        return {
            'routes': {i: route.route for i, route in enumerate(self.route_solutions)},
            'port_calls': {i: route.port_call_sequence for i, route in enumerate(self.route_solutions)},
            'cycle_times': [round(route.round_trip_time, 1) for route in self.route_solutions],
            'total_cost': round(self.total_cost, 2),
            'total_utility': round(self.total_utility, 2),
            'total_captured_demand': round(self.total_capatured_demand, 2),
            'cover_nodes': self.cover_nodes,
            'transit_nodes': self.transit_nodes,
            'obj_type': self.obj_type,
            'optimization_direction': self.optimization_direction
        }