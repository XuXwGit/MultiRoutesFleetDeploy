from functools import lru_cache
import logging
from typing import Optional

import numpy as np
import pandas as pd

from ...utils.data_processing import calculate_distance_matrix
from ...utils.data_processing import load_port_data, generate_od_pairs
from ...utils.config import Config

class NetworkData:
    def __init__(self,
                 config: Optional[Config] = None,
                 ports_data: Optional[pd.DataFrame] = None,
                 num_ports: int = 10,
                 num_routes: int = 3,
                 num_ods: int = 5,
                 nr_lb = None,
                 nr_ub = None,
                 T_min = None,
                 T_max = None,
                 C_max = None,
                 random_seed = None,
                 problem_type = None,
                 ):
        if config != None:
            # 使用传入config参数
            self.config = config
            self.num_ports = config.P
            self.num_routes = config.R
            self.num_ods = config.K
            self.random_seed = config.seed
        else:
            self.ports_df: Optional[pd.DataFrame] = ports_data
            if ports_data is None:
                self.num_ports: int = num_ports if num_ports is not None else Config.DEFAULT_NUM_PORTS
            else:
                self.num_ports: int = len(ports_data)
            self.num_routes = num_routes if num_routes is not None else Config.DEFAULT_NUM_ROUTES
            self.num_ods = num_ods if num_ods is not None else Config.DEFAULT_NUM_ODS
            self.random_seed = random_seed if random_seed is not None else Config.DEFAULT_RANDOM_SEED
            self.num_ports = self.num_ports if self.num_ports is not None else 10
            self.num_ods = self.num_ods if self.num_ods is not None else 5
            self.num_routes = self.num_routes if self.num_routes is not None else 3
            
            self.config = Config(
                P=self.num_ports,
                K=self.num_ods,
                R=self.num_routes,
                seed=self.random_seed
            )

        self.min_length = nr_lb if nr_lb is not None else Config.MIN_PORT_CALLS
        self.max_length = nr_ub if nr_ub is not None else Config.MAX_PORT_CALLS
        self.T_min = T_min if T_min is not None else Config.MIN_ROTATION_TIME
        self.T_max = T_max if T_max is not None else Config.MAX_ROTATION_TIME
        self.C_max = C_max if C_max is not None else Config.MAX_BUDGET
        self.problem_type = problem_type if problem_type is not None else Config.DEFAULT_PROBLEM_TYPE
        self.num_types = self.num_ods
        self.num_samples = 1

        self.P = self.num_ports
        self.K = self.num_types
        self.R = self.num_routes


        # 初始化数据框架
        if ports_data is not None:
            self.ports_df = ports_data.sample(num_ports).reset_index(drop=True) if num_ports else ports_data
        else:
            self.ports_df = None
        self.nodes = [i for i in range(self.num_ports)]
        if self.ports_df is not None:
            self.fixed_cost = self.ports_df['FixedCost'].to_dict()
        else:
            self.fixed_cost = {}

        # 生成OD对
        if self.ports_df is not None and num_ods is not None:
            self.od_pairs, self.od_demands = generate_od_pairs(self.ports_df, num_ods)
        else:
            self.od_pairs, self.od_demands = [], []
        self.num_ods = len(self.od_pairs)
        self.od_to_idx = {self.od_pairs[idx]: idx for idx in range(self.num_ods)}

        # 计算距离矩阵
        coords = None
        if self.ports_df is not None:
            coords = np.column_stack((
                self.ports_df['NewLongitude'],
                self.ports_df['Latitude']
            ))
        self.distance_matrix = calculate_distance_matrix(coords, speed_knots=Config.DEFAULT_SPEED)

        # 生成网络拓扑
        self.arcs, self.virtual_arcs = self.generate_arcs(self.num_ports)
        self.arc_costs = {arc: self._calculate_arc_cost(arc) for arc in self.arcs}

        self.M = 1e8
        
        # each OD pair / type has a preference for travel time
        # demand = b[k] + alpha[k] * t + epsilon
        self.constants = np.random.randint(1, 10, self.num_ods)
        # generate preference matrix : p[k]
        if self.problem_type in ["Multi-Routes", "Lines"]:
            self.preference_matrix = - np.random.randint(0, 1, self.num_ods)
        elif self.problem_type == "Tour":
            self.preference_matrix = -np.random.randint(
                0, 1,
                size=(self.num_ods, self.num_ports)
            )
        self.varepsion = np.random.normal(0, 1, [self.num_ods, self.num_samples]).astype(int)
    
    def calculate_travel_time(self, arcs):
        return sum(self.distance_matrix[e[0]][e[1]] for e in arcs)

    @lru_cache(maxsize=128)
    def calculate_utility(self, time = 0, origin = 0, destination = 0):
        """获取对特定OD对的平均效用值"""
        idx = self.od_to_idx.get((origin, destination), -1)
        if idx == -1:
            return 0
        return self.constants[idx] + self.preference_matrix[idx] * time + sum(self.varepsion[idx]) / self.num_samples
    
    def generate_arcs(self, num_ports):
        self.arcs = []
        self.arc_costs = {}
        for i in range(num_ports):
            for j in range(i + 1, num_ports):
                self.arcs.append((i, j))
                self.arcs.append((j, i))
                self.arc_costs[(i, j)] = self.distance_matrix[i][j]
                self.arc_costs[(j, i)] = self.distance_matrix[i][j]

        self.virtual_arcs = []
        virtual_node = -1
        for i in range(num_ports):
            self.arcs.append((virtual_node, i))
            self.arcs.append((i, virtual_node))
            self.virtual_arcs.append((virtual_node, i))
            self.virtual_arcs.append((i, virtual_node))
            self.arc_costs[(virtual_node, i)] = 0
            self.arc_costs[(i, virtual_node)] = 0

        return self.arcs, self.virtual_arcs
    
    def _calculate_arc_cost(self, arc):
        return self.distance_matrix[arc[0]][arc[1]] if arc in self.arcs else 1e8

    def print_network_data(self):
        logging.info('=========== Instance Information ===========')
        logging.info(f'Random seed: {self.random_seed}')
        logging.info(f'Number of ports: {self.num_ports}')
        logging.info(f'Number of OD pairs: {self.num_ods}')
        logging.info(f'Number of routes need to design: {self.num_routes}')
        logging.info(f'Number of samples for each od: {self.num_samples}')
        logging.info(f'Route length range: [{self.min_length},{self.max_length}]')
        logging.info('=========== Instance Information ===========')