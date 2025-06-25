from design.core.models.network_data import NetworkData
from functools import lru_cache
from typing import List, Dict, Tuple, Optional

from design.utils.config import Config

class RouteSolution:
    def __init__(self, solution: list = [], route: list = None, network_data: NetworkData = None):
        self._solution = solution
        

        self._network_data = network_data
        self._route = route
        self._round_trip_time = None
        self._port_call_sequence = None
        self._id_to_port_calls = None
        self._utility = None
        self._cost = None
        self._cover_cost = None
        self._travel_cost = None
        self._travel_distance = None
        self.hash = None
        
        self._initialize()

    def copy(self) -> 'RouteSolution':
        return RouteSolution(route= self.route.copy(), network_data=self._network_data)
    
    def __str__(self):
        """自定义RouteSolution对象的字符串表示"""
        if not self.route:
            return "Empty RouteSolution"
            
        return f"RouteSolution(route={self.route}, time={self.round_trip_time:.2f}, cost={self.cost:.2f})"
    
    def __repr__(self):
        """确保日志记录器能正确显示"""
        return self.__str__()
    
    def get(self, attr: str, default: float = None) -> float:
        """获取属性值"""
        return getattr(self, attr, default)
    
    @staticmethod
    def get_solution_hash(solution: list) -> str:
        """生成解决方案的唯一哈希值"""
        return str((tuple(solution[0]), tuple(solution[1])))
    
    @staticmethod
    def get_route_hash(route: list) -> str:
        """生成解决方案的唯一哈希值"""
        return str(route)

    def _initialize(self):
        """初始化所有计算属性"""
        if self.solution is not None and self.solution != []:
            self._route = self._turn_solution_to_route()
        self._round_trip_time = self._calculate_round_trip_time()
        self._port_call_sequence, self._id_to_port_calls = self._calculate_port_call_arrival_time()
        self._utility = self._calculate_utility()
        self._cost, self._cover_cost, self._travel_cost, self._travel_distance = self._calculate_cost()


    def remove_node(self, node):
        self.route.remove(node)
        self.update(self.route)


    def update(self, route: None):
        if route is not None:
            if not self.check_route():
                new_route = []
                for i in range(len(self.route) - 1):
                    if self.route[i] == self.route[i+1]:
                        continue
                    new_route.append(self.route[i])
                self._route = new_route
            if self.solution == []:
                return
            self._solution = []

            self._initialize()
    
    def check_route(self) -> bool:
        for i in range(len(self.route) - 1):
            if self.route[i] == self.route[i+1]:
                return False
            
        return True


    def _turn_solution_to_route(self) -> List[int]:
        """将解决方案转换为路线"""
        if self._network_data.problem_type in ['Tour', 'Lines']:
            return self._solution
        elif self._network_data.problem_type == 'Multi-Routes':
            solution_in, solution_out = self._solution
            route = []
            if solution_in == [] or solution_out == []:
                route = solution_in + solution_out
                return route

            if solution_in[0] == solution_out[-1]:
                route = solution_in + solution_out[:-1]
            elif solution_in[-1] == solution_out[0]:
                route = solution_in[:-1] + solution_out
            else:
                route = solution_in + solution_out
            return   route
        return []

    def _calculate_round_trip_time(self) -> float:
        """计算往返时间"""
        if not self._route:
            return 0.0
        
        total_time = 0.0
        for i in range(len(self._route)):
            total_time += self._network_data.distance_matrix[self._route[i-1]][self._route[i]]
        return total_time

    def _calculate_port_call_arrival_time(self) -> Tuple[List[Dict], Dict[int, List[Dict]]]:
        """计算港口调用序列和到达时间"""
        if not self._route:
            return [], {}
        
        port_call_sequence = []
        id_to_port_calls = {p: [] for p in self._route}
        
        # 初始化第一个港口调用
        first_port_call = {
            'port_id': self._route[0],
            'port_call': 1,
            'arrival_time': 0.0
        }
        port_call_sequence.append(first_port_call)
        id_to_port_calls[self._route[0]].append(first_port_call)
        
        # 计算后续港口调用
        for i in range(1, len(self._route)):
            previous_call = port_call_sequence[i - 1]
            current_port = self._route[i]
            arrival_time = previous_call['arrival_time'] + self._network_data.distance_matrix[self._route[i-1]][current_port]
            
            current_call = {
                'port_id': current_port,
                'port_call': i + 1,
                'arrival_time': arrival_time
            }
            port_call_sequence.append(current_call)
            id_to_port_calls[current_port].append(current_call)
            
        return port_call_sequence, id_to_port_calls

    def _calculate_utility(self) -> Dict[Tuple[int, int], float]:
        """计算并存储解的效用值"""
        utility = {}
        for k in range(self._network_data.num_types):
            for s in range(self._network_data.num_samples):
                U_ks = self._network_data.constants[k]
                
                if self._network_data.problem_type == 'Multi-Routes':
                    U_ks += self._network_data.preference_matrix[k] * self.calculate_transport_time(
                        self._network_data.od_pairs[k][0],
                        self._network_data.od_pairs[k][1]
                    )
                elif self._network_data.problem_type == 'Tour':
                    for i in self._solution:
                        U_ks += self._network_data.preference_matrix[k][i] * self._solution.count(i)
                
                U_ks += self._network_data.varepsion[k][s]
                utility[(k, s)] = U_ks
                
        return utility
    
    def _calculate_cost(self) -> float:
        """计算线路成本"""
        cost = 0
        cover_cost = 0
        travel_cost = 0
        travel_distance = 0
        for i in range(len(self.route)):
            cover_cost += self._network_data.fixed_cost[self.route[i]]
            travel_cost += self._network_data.distance_matrix[self.route[i-1]][self.route[i]] * Config.UNIT_TRAVEL_COST
            travel_distance += self._network_data.distance_matrix[self.route[i-1]][self.route[i]] * Config.DEFAULT_SPEED
        cost = cover_cost + travel_cost
        return cost, cover_cost, travel_cost, travel_distance

    @property
    def solution(self) -> List[int]:
        """获取 in-bound / out-bound"""
        return self._solution

    @property
    def route(self) -> List[int]:
        """获取路线"""
        return self._route

    @property
    def round_trip_time(self) -> float:
        """获取往返时间"""
        return self._round_trip_time

    @property
    def port_call_sequence(self) -> List[Dict]:
        """获取港口调用序列"""
        return self._port_call_sequence

    @property
    def utility(self) -> Dict[Tuple[int, int], float]:
        """获取效用值"""
        return self._utility
    
    @property
    def cost(self) -> float:
        # 获取路径总成本
        return self._cost

    @property
    def cover_cost(self) -> float:
        # 获取覆盖节点成本
        return self._cover_cost
    
    @property
    def travel_cost(self) -> float:
        # 获取航行成本
        return self._travel_cost
    
    @property
    def travel_distance(self) -> float:
        # 获取航行距离
        return self._travel_distance


    @lru_cache(maxsize=128)
    def calculate_transport_time(self, o: int, d: int) -> float:
        """计算运输时间"""
        if self._route == [] or self._route is None or self._route == 0:
            return 1e8

        if o not in self._route or d not in self._route:
            return 1e8
        
        min_time = float('inf')
        for o_call in self._id_to_port_calls[o]:
            for d_call in self._id_to_port_calls[d]:
                if d_call["arrival_time"] > o_call["arrival_time"]:
                    direct_time = d_call["arrival_time"] - o_call["arrival_time"]
                else:
                    direct_time = self._round_trip_time - (o_call["arrival_time"] - d_call["arrival_time"])
                if direct_time < min_time:
                    min_time = direct_time
        
        return min_time if min_time != float('inf') else 1e8

    @lru_cache(maxsize=128)
    def get_subpath(self, o: int, d: int) -> List[int]:
        """获取从o到d的最短子路径"""
        if o not in self._route or d not in self._route:
            return []
        
        is_loop = self._route[0] == self._route[-1]
        search_route = self._route[:-1] if is_loop else self._route
        
        o_indices = [i for i, x in enumerate(search_route) if x == o]
        d_indices = [i for i, x in enumerate(search_route) if x == d]
        
        if not o_indices or not d_indices:
            return []
            
        subpaths = []
        for o_idx in o_indices:
            for d_idx in d_indices:
                if o_idx <= d_idx:
                    subpaths.append(search_route[o_idx:d_idx+1])
                elif is_loop:
                    subpaths.append(search_route[o_idx:] + search_route[1:d_idx+1])
                else:
                    subpaths.append(search_route[o_idx:] + search_route[0:d_idx+1])
        
        if not subpaths:
            return []
            
        return min(subpaths, key=lambda x: len(x))

    @lru_cache(maxsize=128)
    def get_utility(self, o: int, d: int) -> float:
        """获取对特定OD对的平均效用值"""
        if not self._utility:
            return 0.0
            
        od_pair = (o, d)
        if od_pair in self._network_data.od_pairs:
            k = self._network_data.od_pairs.index(od_pair)
            sample_utilities = [self._utility.get((k, s), 0.0) 
                              for s in range(self._network_data.num_samples)]
            return sum(sample_utilities) / len(sample_utilities)
        return 0.0