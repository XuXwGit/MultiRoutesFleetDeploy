from dataclasses import dataclass, field
from typing import Any, Optional
from abc import ABC
from .node import Node
from ..entity.vessel_type import VesselType

@dataclass
class Arc:
    """
    网络弧的抽象基类，表示运输网络中的连接。
    
    弧是连接两个节点的有向边，表示船舶或集装箱的移动。
    每个弧都有成本、容量等基本属性，以及起点和终点节点。
    
    Attributes:
        id: 弧的唯一标识符
        origin_node: 起始节点
        destination_node: 目标节点
        cost: 使用该弧的成本
        capacity: 弧的容量限制
    """
    id: int
    origin_node: Any  # Node
    destination_node: Any  # Node
    cost: float
    capacity: float

    def __init__(self, id: int, origin_node: Node, destination_node: Node, cost: float = 0, capacity: float = 0):
        self.id = id
        self.origin_node = origin_node
        self.destination_node = destination_node
        self.cost = cost
        self.capacity = capacity

    def __post_init__(self):
        """
        初始化后处理：将弧添加到起点和终点的边集合中
        """
        self.origin_node.add_outgoing_arc(self)
        self.destination_node.add_incoming_arc(self)

    def __str__(self):
        """
        返回弧的字符串表示
        
        Returns:
            str: 弧的字符串描述
        """
        return f"Arc(id={self.id}, from={self.origin_node}, to={self.destination_node})"

@dataclass
class TravelingArc(Arc):
    """
    航行弧类，表示船舶在两个港口之间的航行。
    
    继承自Arc类，增加了与船舶航行相关的特定属性。
    
    Attributes:
        vessel_type: 船舶类型
        travel_time: 航行时间
        fuel_cost: 燃料成本
        co2_emission: 二氧化碳排放量
    """
    vessel_type: VesselType  # VesselType
    travel_time: int
    fuel_cost: float
    co2_emission: float

    def __str__(self):
        """
        返回航行弧的字符串表示
        
        Returns:
            str: 航行弧的字符串描述
        """
        return f"TravelingArc(id={self.id}, from={self.origin_node}, to={self.destination_node}, vessel_type={self.vessel_type})"

@dataclass
class TransshipArc(Arc):
    """
    转运弧类，表示集装箱在港口内的转运操作。
    
    继承自Arc类，增加了与集装箱转运相关的特定属性。
    
    Attributes:
        handling_cost: 处理成本
        handling_time: 处理时间
        container_type: 集装箱类型（'LADEN'表示重箱，'EMPTY'表示空箱）
    """
    handling_cost: float
    handling_time: int
    container_type: str  # 'LADEN' or 'EMPTY'

    def __str__(self):
        """
        返回转运弧的字符串表示
        
        Returns:
            str: 转运弧的字符串描述
        """
        return f"TransshipArc(id={self.id}, from={self.origin_node}, to={self.destination_node}, container_type={self.container_type})" 