import logging

import numpy as np

from design.core.models.design_solution import DesignSolution
from design.core.models.network_data import NetworkData
from design.core.models.route_solution import RouteSolution


class RouteSolutionPool:
    """管理候选路线解决方案的集合(包含可行和不可行路径)
    
    该类负责存储和管理所有候选路线解决方案，包括：
    - 路线解决方案集合(可行和不可行)
    - 路线状态管理
    - 路线效用计算
    - 路线往返时间计算
    
    Attributes:
        feasible_solutions (dict): 可行路线解决方案 {hash: RouteSolution}
        infeasible_solutions (dict): 不可行路线解决方案 {hash: RouteSolution}
        route_utility_set (dict): 路线效用字典 (route_hash, od_idx) -> utility_list
        round_trip_time_set (dict): 每条路线的往返时间 {route_hash: time}
        network_data (NetworkData): 网络数据对象
        problem_type (str): 问题类型('Tour'或'Multi-Routes')
        M (float): 大M值(用于距离计算)
    """
    def __init__(self, network_data: NetworkData):
        self.feasible_solutions = {}  # {route_hash: RouteSolution}
        self.infeasible_solutions = {}  # {route_hash: RouteSolution}
        self.route_utility_set = {}
        self.round_trip_time_set = {}
        self.network_data = network_data
        self.problem_type = network_data.problem_type
        self.M = 1e8
        self.design_solutions = DesignSolution(network_data)
        
    @property
    def num_feasible_routes(self) -> int:
        """获取可行路线数量"""
        return len(self.feasible_solutions)
        
    @property
    def num_infeasible_routes(self) -> int:
        """获取不可行路线数量"""
        return len(self.infeasible_solutions)

    def add_new_solution(self, solution: list, is_feasible: bool = True) -> bool:
        """添加新的路线解决方案到池中
        
        根据论文中的数学模型(3.4节)，计算每条路线的效用值并存储，扩展中转路径
        
        Args:
            solution: 路线解决方案，格式取决于problem_type:
                - 'Tour': [port1, port2, ...]
                - 'Multi-Routes': [inbound_ports, outbound_ports]
            is_feasible: 路线是否可行
                
        Returns:
            bool: 是否成功添加(False表示重复解决方案)
        """
        route_hash = RouteSolutionPool.get_solution_hash(solution)
        if route_hash in self.feasible_solutions or route_hash in self.infeasible_solutions:
            return None
            
        route_solution = RouteSolution(solution, self.network_data)
        route = self.turn_solution_to_route(solution)
        
        # 计算往返时间
        distance_matrix = self.network_data.distance_matrix
        round_trip_time = sum(
            distance_matrix[route[i]][route[i + 1]]
            for i in range(len(route) - 1)
        ) + distance_matrix[route[-1]][route[0]]
        
        # 计算效用值
        utility_dict = {}
        for k in range(self.network_data.num_ods):
            utility_list = []
            for s in range(self.network_data.num_samples):
                utility = self.network_data.constants[k]
                utility_list.append(route_solution.utility[(k, s)])
            utility_dict[(route_hash, k)] = utility_list
        
        # 存储解决方案
        if is_feasible:
            self.feasible_solutions[route_hash] = route_solution
            self.design_solutions.add_route_solution(route_solution= route_solution)
        else:
            self.infeasible_solutions[route_hash] = route_solution
            
        self.round_trip_time_set[route_hash] = round_trip_time
        self.route_utility_set.update(utility_dict)
        return route_solution
    
    @staticmethod
    def get_solution_hash(solution: list) -> str:
        """生成解决方案的唯一哈希值"""
        return str((tuple(solution[0]), tuple(solution[1])))
    
    @staticmethod
    def get_route_hash(route: list) -> str:
        """生成解决方案的唯一哈希值"""
        return str(route)

    def initialize(self):
        """重置所有解决方案"""
        self.feasible_solutions.clear()
        self.infeasible_solutions.clear()
        self.round_trip_time_set.clear()
        self.route_utility_set.clear()

    def set_initial_solution_set(self, solution_set: list, is_feasible: bool = True):
        """批量设置初始解决方案集合
        
        Args:
            solution_set: 解决方案列表
            is_feasible: 解决方案是否可行
        """
        self.initialize()
        for solution in solution_set:
            self.add_new_solution(solution, is_feasible)

    def remove_solution(self, solution: list):
        """移除指定解决方案
        
        Args:
            solution: 要移除的解决方案
        """
        route_hash = RouteSolutionPool.get_solution_hash(solution)
        if route_hash in self.feasible_solutions:
            del self.feasible_solutions[route_hash]
        elif route_hash in self.infeasible_solutions:
            del self.infeasible_solutions[route_hash]
            
        # 清理相关数据
        for key in list(self.route_utility_set.keys()):
            if key[0] == route_hash:
                del self.route_utility_set[key]
                
        if route_hash in self.round_trip_time_set:
            del self.round_trip_time_set[route_hash]

    def calculate_shortest_distance(self, route: list, od: tuple, d: list, T: float) -> float:
        """计算OD对在给定路线中的最短运输距离
        
        根据论文3.2节中的运输时间计算方法，考虑正向和逆向路径
        
        Args:
            route: 港口访问序列
            od: (origin, destination)元组
            d: 距离矩阵
            T: 路线总往返时间
            
        Returns:
            float: 最短运输距离，若无可行路径返回大M值
        """
        o, dest = od
        o_positions = [i for i, x in enumerate(route) if x == o]
        dest_positions = [i for i, x in enumerate(route) if x == dest]
        distances = []
        for o_pos in o_positions:
            for dest_pos in dest_positions:
                distance = 0
                if o_pos < dest_pos:
                    for i in range(o_pos, dest_pos):
                        distance += d[route[i]][route[i + 1]]
                    distances.append(distance)
                else:
                    for i in range(dest_pos, o_pos):
                        distance += d[route[i]][route[i + 1]]
                    distances.append(T - distance)
        return min(distances) if distances else self.M

    def turn_solution_to_route(self, solution: list) -> list:
        """将解决方案转换为港口访问序列
        
        根据问题类型处理不同的解决方案格式：
        - 'Tour': 直接返回解决方案
        - 'Multi-Routes': 合并inbound和outbound序列
        
        Args:
            solution: 输入的解决方案
            
        Returns:
            list: 港口访问序列
        """
        route_solution = []
        if self.problem_type == 'Tour':
            route_solution = solution
        elif self.problem_type == 'Multi-Routes':
            solution_in, solution_out = solution
            # 去掉末尾重复的起点港口
            if solution_in and solution_out:
                route_solution = solution_in + solution_out
            elif solution_out == []:
                route_solution = solution_in
            elif solution_in == []:
                route_solution = solution_out
            else:
                route_solution = []
        return route_solution

    def change_solution_status(self, solution: list, new_status: bool):
        """更改解决方案的状态(可行/不可行)
        
        Args:
            solution: 要更改的解决方案
            new_status: True表示可行，False表示不可行
        """
        route_hash = RouteSolutionPool.get_solution_hash(solution)
        if new_status:
            if route_hash in self.infeasible_solutions:
                self.feasible_solutions[route_hash] = self.infeasible_solutions.pop(route_hash)
        else:
            if route_hash in self.feasible_solutions:
                self.infeasible_solutions[route_hash] = self.feasible_solutions.pop(route_hash)

    def get_feasible_solutions(self) -> list:
        """获取所有可行解决方案"""
        return list(self.feasible_solutions.values())
        
    def get_infeasible_solutions(self) -> list:
        """获取所有不可行解决方案"""
        return list(self.infeasible_solutions.values())
        
    def print_solution_set(self):
        """打印解决方案集合信息"""
        logging.info(f"可行路线数量: {self.num_feasible_routes}")
        logging.info(f"不可行路线数量: {self.num_infeasible_routes}")
        
        for i, (route_hash, route_solution) in enumerate(self.feasible_solutions.items()):
            logging.info(f"可行路线 {i}: {route_solution.route}")
            logging.info(f"往返时间: {self.round_trip_time_set.get(route_hash, 'N/A')}")
