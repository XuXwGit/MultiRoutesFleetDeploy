from dataclasses import dataclass
from typing import Dict, List, Union
import logging

from multi.utils.default_setting import DefaultSetting

logger = logging.getLogger(__name__)

@dataclass
class Parameter:
    """模型参数类
    
    存储优化模型所需的所有参数
    
    主要参数分类:
    1. 时间参数: time_horizon, tau等
    2. 成本参数: rental_cost, penalty_cost_for_demand等
    3. 网络参数: traveling_arcs_set, transhipment_arcs_set等
    4. 船舶参数: vessel_set, vessel_capacity等
    5. 需求参数: demand_request_set, demand等
    
    所有参数单位:
    - 时间: 天
    - 成本: 美元
    - 容量: TEU(标准集装箱)
    """
    
    def __init__(self):
        # 时间参数
        self.time_horizon: int = 0  # 时间范围(天)
        self.tau: int = 0  # 需求响应时间窗口(天)
        self.uncertain_degree: float = 0.0  # 不确定度系数[0,1]
        
        # 成本参数
        self.rental_cost: float = 0.0  # 集装箱租赁成本(美元/TEU)
        
        # 网络参数
        self.traveling_arcs_set: List[int] = []  # 运输弧集合(弧ID数组)
        self.transhipment_arcs_set: List[int] = []  # 转运弧集合(弧ID数组)
        self.time_point_set: List[int] = []  # 时间点集合(天)
        self.shipping_route_set: List[int] = []  # 航线集合
        self.num_of_round_trips: List[int] = []  # 每个航线的往返次数
        self.vessel_set: List[int] = []  # 船舶集合
        self.vessel_path_set: List[int] = []  # 船舶路径集合
        self.num_vessel_paths: List[int] = []  # 每个船舶的路径数量
        self.path_set: List[int] = []  # 路径集合
        self.initial_empty_container: List[int] = []  # 初始空箱量
        self.demand_request_set: List[int] = []  # 需求请求集合
        self.turn_over_time: List[int] = []  # 周转时间
        self.vessel_capacity: List[int] = []  # 船舶容量
        self.travel_time_on_path: List[int] = []  # 路径上的旅行时间

        self.arc_and_vessel_path: Dict[int, Dict[int]] = dict  # 弧与船舶路径的关系矩阵
        self.arc_and_path: Dict[int, Dict[int]] = dict  # 弧与路径的关系矩阵
        self.ship_route_and_vessel_path: Dict[int, Dict[int]] = dict  # 航线与船舶路径的关系矩阵
        self.vessel_path_ship_route_index: Dict[int, int] = dict  # 船舶路径对应的航线索引
        self.shipping_route_vessel_num: Dict[int, int] = dict  # 每个航线的船舶数量
        self.vessel_type_and_ship_route: Dict[int, Dict[int]] = dict  # 船舶类型与航线的关系矩阵
        self.port_and_path: Dict[str, Dict[int]] = dict 
        
        # 港口参数
        self.port_set: List[str] = []  # 港口集合
        self.origin_of_demand: List[str] = []  # 需求的起始港口
        self.destination_of_demand: List[str] = []  # 需求的目的港口
        
        # 需求参数
        self.demand: List[float] = []  # 需求量
        self.vessel_operation_cost: List[float] = []  # 船舶运营成本
        self.penalty_cost_for_demand: List[float] = []  # 需求惩罚成本
        self.laden_demurrage_cost: List[float] = []  # 重箱滞期成本
        self.empty_demurrage_cost: List[float] = []  # 空箱滞期成本
        self.laden_path_demurrage_cost: List[float] = []  # 重箱路径滞期成本
        self.empty_path_demurrage_cost: List[float] = []  # 空箱路径滞期成本
        self.laden_path_cost: List[float] = []  # 重箱路径成本
        self.empty_path_cost: List[float] = []  # 空箱路径成本
        self.maximum_demand_variation: List[float] = []  # 最大需求变化
        self.sample_scenes: List[List[float]] = []  # 样本场景
        self.arc_capacity: Dict[int, int] = {}  # 弧容量
        
    def change_maximum_demand_variation(self, coeff: float):
        """修改最大需求变化系数"""
        new_max_demand_variation = [self.maximum_demand_variation[i] * coeff 
                                  for i in range(len(self.demand))]
        self.maximum_demand_variation = new_max_demand_variation
        
    def set_turn_over_time(self, turn_over_time: Union[int, List[int]]):
        """设置周转时间"""
        if isinstance(turn_over_time, int):
            self.turn_over_time = [turn_over_time] * len(self.port_set)
        else:
            self.turn_over_time = turn_over_time
            
    def change_penalty_cost_for_demand(self, penalty_cost_coeff: float):
        """修改需求惩罚成本系数"""
        new_penalty_cost = [self.penalty_cost_for_demand[i] * penalty_cost_coeff 
                          for i in range(len(self.demand))]
        self.penalty_cost_for_demand = new_penalty_cost
        
    def change_rental_cost(self, rental_cost_coeff: float):
        """修改租赁成本系数"""
        self.rental_cost = self.rental_cost * rental_cost_coeff
        
    def set_laden_demurrage_cost(self, laden_demurrage_cost: List[float]):
        """设置重箱滞期成本"""
        self.laden_demurrage_cost = laden_demurrage_cost
        
    def set_empty_demurrage_cost(self, empty_demurrage_cost: List[float]):
        """设置空箱滞期成本"""
        self.empty_demurrage_cost = empty_demurrage_cost
        
    def get_total_capacity_max(self) -> int:
        """计算最大总容量"""
        total_capacity = 0
        # r \in R
        for r in range(len(self.shipping_route_set)):
            # w \in \Omega
            # r(w) = r : p.get_ship_route_and_vessel_path()[r][w] == 1
            for w in range(len(self.vessel_path_set)):
                max_capacity = 0
                # h \in H_r
                # r(h) = r : p.get_vessel_type_and_ship_route()[h][r] == 1
                for h in range(len(self.vessel_set)):
                    if (self.vessel_type_and_ship_route[h][r] * 
                        self.ship_route_and_vessel_path[r][w] != 0):
                        if self.vessel_capacity[h] > max_capacity:
                            max_capacity = self.vessel_capacity[h]
                total_capacity += max_capacity
        return total_capacity
        
    def get_total_capacity_min(self) -> int:
        """计算最小总容量"""
        total_capacity = 0
        # r \in R
        for r in range(len(self.shipping_route_set)):
            # w \in \Omega
            # r(w) = r : p.get_ship_route_and_vessel_path()[r][w] == 1
            for w in range(len(self.vessel_path_set)):
                min_capacity = float('inf')
                # h \in H_r
                # r(h) = r : p.get_vessel_type_and_ship_route()[h][r] == 1
                for h in range(len(self.vessel_set)):
                    if (self.vessel_type_and_ship_route[h][r] * 
                        self.ship_route_and_vessel_path[r][w] != 0):
                        if self.vessel_capacity[h] < min_capacity:
                            min_capacity = self.vessel_capacity[h]
                total_capacity += min_capacity
        return total_capacity
        
    def get_total_demand(self) -> int:
        """计算总需求"""
        total_demand = 0
        for i in range(len(self.demand)):
            total_demand += self.demand[i] + self.maximum_demand_variation[i]
        return total_demand
        
    def get_operation_cost(self, v_value: List[List[int]]) -> float:
        """计算运营成本"""
        operation_cost = 0
        for h in range(len(self.vessel_set)):
            for w in range(len(self.vessel_path_set)):
                # r(ω) == r
                r = self.vessel_path_ship_route_index[w]
                
                if DefaultSetting.FLEET_TYPE == "Homo":
                    # vessel_type_and_ship_route == 1 : r(h) = r
                    operation_cost += (self.vessel_type_and_ship_route[h][r] *
                                     self.ship_route_and_vessel_path[r][w] *
                                     self.vessel_operation_cost[h] *
                                     v_value[h][r])
                elif DefaultSetting.FLEET_TYPE == "Hetero":
                    operation_cost += (self.vessel_operation_cost[h] *
                                     v_value[h][w])
        return operation_cost
        
    def solution_to_v_value(self, solution: List[int]) -> List[List[int]]:
        """将解决方案转换为v值矩阵"""
        v_value = []
        if DefaultSetting.FLEET_TYPE == "Homo":
            v_value = [[0] * len(self.shipping_route_set) 
                      for _ in range(len(self.vessel_set))]
            for r in range(len(self.shipping_route_set)):
                v_value[solution[r] - 1][r] = 1
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            v_value = [[0] * len(self.vessel_path_set) 
                      for _ in range(len(self.vessel_set))]
            for w in range(len(self.vessel_path_set)):
                v_value[solution[w] - 1][w] = 1
        else:
            logger.error("Error in Fleet type!")
        return v_value 