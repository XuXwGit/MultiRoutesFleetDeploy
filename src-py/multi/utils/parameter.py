import logging
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class Parameter:
    """
    模型参数类
    
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
    
    # 时间参数
    time_horizon: int = 0  # 时间范围(天)
    tau: int = 0           # 需求响应时间窗口(天)
    uncertain_degree: float = 0.0  # 不确定度系数[0,1]
    
    # 成本参数
    rental_cost: float = 0.0  # 集装箱租赁成本(美元/TEU)
    
    # 网络参数
    traveling_arcs_set: List[int] = field(default_factory=list)  # 运输弧集合
    transhipment_arcs_set: List[int] = field(default_factory=list)  # 转运弧集合
    time_point_set: List[int] = field(default_factory=list)  # 时间点集合
    shipping_route_set: List[int] = field(default_factory=list)  # 航线集合
    num_of_round_trips: List[int] = field(default_factory=list)  # 每个航线的往返次数
    vessel_set: List[int] = field(default_factory=list)  # 船舶集合
    vessel_path_set: List[int] = field(default_factory=list)  # 船舶路径集合
    num_vessel_paths: List[int] = field(default_factory=list)  # 每个船舶的路径数
    path_set: List[int] = field(default_factory=list)  # 路径集合
    initial_empty_container: List[int] = field(default_factory=list)  # 初始空箱数量
    demand_request_set: List[int] = field(default_factory=list)  # 需求请求集合
    turn_over_time: List[int] = field(default_factory=list)  # 周转时间
    vessel_capacity: List[int] = field(default_factory=list)  # 船舶容量
    travel_time_on_path: List[int] = field(default_factory=list)  # 路径上的旅行时间
    
    # 关联矩阵
    arc_and_vessel_path: List[List[int]] = field(default_factory=list)  # 弧和船舶路径的关联矩阵
    arc_and_path: List[List[int]] = field(default_factory=list)  # 弧和路径的关联矩阵
    ship_route_and_vessel_path: List[List[int]] = field(default_factory=list)  # 航线和船舶路径的关联矩阵
    vessel_path_ship_route_index: List[int] = field(default_factory=list)  # 船舶路径的航线索引
    shipping_route_vessel_num: List[int] = field(default_factory=list)  # 每个航线的船舶数量
    vessel_type_and_ship_route: List[List[int]] = field(default_factory=list)  # 船舶类型和航线的关联矩阵
    port_and_path: Dict[int, Dict[int, int]] = field(default_factory=dict)  # 港口和路径的关联矩阵
    
    # 港口和需求参数
    port_set: List[str] = field(default_factory=list)  # 港口集合
    origin_of_demand: List[str] = field(default_factory=list)  # 需求起点
    destination_of_demand: List[str] = field(default_factory=list)  # 需求终点
    demand: List[float] = field(default_factory=list)  # 需求值
    vessel_operation_cost: List[float] = field(default_factory=list)  # 船舶运营成本
    penalty_cost_for_demand: List[float] = field(default_factory=list)  # 需求惩罚成本
    laden_demurrage_cost: List[float] = field(default_factory=list)  # 重箱滞期成本
    empty_demurrage_cost: List[float] = field(default_factory=list)  # 空箱滞期成本
    laden_path_demurrage_cost: List[float] = field(default_factory=list)  # 重箱路径滞期成本
    empty_path_demurrage_cost: List[float] = field(default_factory=list)  # 空箱路径滞期成本
    laden_path_cost: List[float] = field(default_factory=list)  # 重箱路径成本
    empty_path_cost: List[float] = field(default_factory=list)  # 空箱路径成本
    maximum_demand_variation: List[float] = field(default_factory=list)  # 最大需求变化
    sample_scenes: List[List[float]] = field(default_factory=list)  # 样本场景
    arc_capacity: Dict[int, int] = field(default_factory=dict)  # 弧容量
    
    def change_maximum_demand_variation(self, coeff: float):
        """
        改变最大需求变化
        
        Args:
            coeff: 变化系数
        """
        self.maximum_demand_variation = [v * coeff for v in self.maximum_demand_variation]
    
    def set_turn_over_time(self, turn_over_time: List[int]):
        """
        设置周转时间
        
        Args:
            turn_over_time: 周转时间列表
        """
        self.turn_over_time = turn_over_time
    
    def set_turn_over_time(self, turn_over_time: int):
        """
        设置所有港口的周转时间
        
        Args:
            turn_over_time: 周转时间
        """
        self.turn_over_time = [turn_over_time] * len(self.port_set)
    
    def change_penalty_cost_for_demand(self, penalty_cost_coeff: float):
        """
        改变需求惩罚成本
        
        Args:
            penalty_cost_coeff: 惩罚成本系数
        """
        self.penalty_cost_for_demand = [c * penalty_cost_coeff for c in self.penalty_cost_for_demand]
    
    def change_rental_cost(self, rental_cost_coeff: float):
        """
        改变租赁成本
        
        Args:
            rental_cost_coeff: 租赁成本系数
        """
        self.rental_cost *= rental_cost_coeff
    
    def set_laden_demurrage_cost(self, laden_demurrage_cost: List[float]):
        """
        设置重箱滞期成本
        
        Args:
            laden_demurrage_cost: 重箱滞期成本列表
        """
        self.laden_demurrage_cost = laden_demurrage_cost
    
    def set_empty_demurrage_cost(self, empty_demurrage_cost: List[float]):
        """
        设置空箱滞期成本
        
        Args:
            empty_demurrage_cost: 空箱滞期成本列表
        """
        self.empty_demurrage_cost = empty_demurrage_cost
    
    def get_total_capacity_max(self) -> int:
        """
        获取最大总容量
        
        Returns:
            int: 最大总容量
        """
        total_capacity = 0
        
        for r in range(len(self.shipping_route_set)):
            for w in range(len(self.vessel_path_set)):
                max_capacity = 0
                
                for h in range(len(self.vessel_set)):
                    if (self.vessel_type_and_ship_route[h][r] * 
                        self.ship_route_and_vessel_path[r][w] != 0):
                        if self.vessel_capacity[h] > max_capacity:
                            max_capacity = self.vessel_capacity[h]
                
                total_capacity += max_capacity
        
        return total_capacity
    
    def get_total_capacity_min(self) -> int:
        """
        获取最小总容量
        
        Returns:
            int: 最小总容量
        """
        total_capacity = 0
        
        for r in range(len(self.shipping_route_set)):
            for w in range(len(self.vessel_path_set)):
                min_capacity = float('inf')
                
                for h in range(len(self.vessel_set)):
                    if (self.vessel_type_and_ship_route[h][r] * 
                        self.ship_route_and_vessel_path[r][w] != 0):
                        if self.vessel_capacity[h] < min_capacity:
                            min_capacity = self.vessel_capacity[h]
                
                total_capacity += min_capacity
        
        return total_capacity
    
    def get_total_demand(self) -> int:
        """
        获取总需求
        
        Returns:
            int: 总需求
        """
        total_demand = 0
        for i in range(len(self.demand)):
            total_demand += self.demand[i] + self.maximum_demand_variation[i]
        return total_demand
    
    def get_operation_cost(self, v_value: List[List[int]]) -> float:
        """
        计算运营成本
        
        Args:
            v_value: 船舶分配方案
            
        Returns:
            float: 运营成本
        """
        operation_cost = 0.0
        
        for h in range(len(self.vessel_set)):
            for r in range(len(self.shipping_route_set)):
                if v_value[h][r] == 1:
                    operation_cost += self.vessel_operation_cost[h]
        
        return operation_cost
    
    def solution_to_v_value(self, solution: List[int]) -> List[List[int]]:
        """
        将解决方案转换为船舶分配方案
        
        Args:
            solution: 解决方案
            
        Returns:
            List[List[int]]: 船舶分配方案
        """
        v_value = []
        
        for h in range(len(self.vessel_set)):
            v_value_h = []
            for r in range(len(self.shipping_route_set)):
                v_value_h.append(solution[h * len(self.shipping_route_set) + r])
            v_value.append(v_value_h)
        
        return v_value 