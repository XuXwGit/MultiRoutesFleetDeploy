from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..entity.port import Port

@dataclass
class Node:
    """
    网络节点类，表示运输网络中的一个节点。
    对应Java类: multi.network.Node
    """
    
    def __init__(self, 
                 id: int = 0, 
                 route: int = 0, 
                 call: int = 0, 
                 port_string: str = "", 
                 round_trip: int = 0, 
                 time: int = 0, 
                 port: Optional[Port] = None):
        """
        初始化节点对象
        
        Args:
            port_string: 港口字符串，默认为空字符串
            id: 节点ID，默认为0
            route: 航线，默认为0
            call: 停靠次数，默认为0
            round_trip: 往返次数，默认为0
            time: 时间点，默认为0
            port: 关联的港口对象，默认为None
        """
        # 基本属性，对应Java类中的字段
        self._port_string = port_string  # 对应Java: private String portString
        self._node_id = id  # 对应Java: private int nodeID
        self._route = route  # 对应Java: private int route
        self._call = call  # 对应Java: private int call
        self._round_trip = round_trip  # 对应Java: private int roundTrip
        self._time = time  # 对应Java: private int time
        self._port = port  # 对应Java: private Port port
        
        # 附加属性（Python实现中用于网络构建）
        self.incoming_arcs: List[Any] = []  # 入边列表
        self.outgoing_arcs: List[Any] = []  # 出边列表

    # Getter和Setter方法
    @property
    def port_string(self) -> str:
        """
        获取港口字符串
        对应Java: getter for portString
        """
        return self._port_string
    
    @port_string.setter
    def port_string(self, value: str):
        """
        设置港口字符串
        对应Java: setter for portString
        """
        self._port_string = value
    
    @property
    def id(self) -> int:
        """
        获取节点ID
        对应Java: getter for id
        """
        return self._node_id

    @property
    def node_id(self) -> int:
        """
        获取节点ID
        对应Java: getter for nodeID
        """
        return self._node_id
    
    @node_id.setter
    def node_id(self, value: int):
        """
        设置节点ID
        对应Java: setter for nodeID
        """
        self._node_id = value
    
    @property
    def route(self) -> int:
        """
        获取航线
        对应Java: getter for route
        """
        return self._route
    
    @route.setter
    def route(self, value: int):
        """
        设置航线
        对应Java: setter for route
        """
        self._route = value
    
    @property
    def call(self) -> int:
        """
        获取停靠次数
        对应Java: getter for call
        """
        return self._call
    
    @call.setter
    def call(self, value: int):
        """
        设置停靠次数
        对应Java: setter for call
        """
        self._call = value
    
    @property
    def round_trip(self) -> int:
        """
        获取往返次数
        对应Java: getter for roundTrip
        """
        return self._round_trip
    
    @round_trip.setter
    def round_trip(self, value: int):
        """
        设置往返次数
        对应Java: setter for roundTrip
        """
        self._round_trip = value
    
    @property
    def time(self) -> int:
        """
        获取时间点
        对应Java: getter for time
        """
        return self._time
    
    @time.setter
    def time(self, value: int):
        """
        设置时间点
        对应Java: setter for time
        """
        self._time = value
    
    @property
    def port(self) -> Optional[Port]:
        """
        获取关联的港口对象
        对应Java: getter for port
        """
        return self._port
    
    @port.setter
    def port(self, value: Optional[Port]):
        """
        设置关联的港口对象
        对应Java: setter for port
        """
        self._port = value
    
    def add_incoming_arc(self, arc: Any):
        """
        添加一条入边到节点
        
        Args:
            arc: 要添加的弧对象
        """
        self.incoming_arcs.append(arc)

    def add_outgoing_arc(self, arc: Any):
        """
        添加一条出边到节点（Python特有方法，用于网络构建）
        
        Args:
            arc: 要添加的弧对象
        """
        self.outgoing_arcs.append(arc)

    def __str__(self):
        """
        返回节点的字符串表示
        
        Returns:
            str: 节点的字符串描述
        """
        return f"Node(id={self.node_id}, port={self.port_string}, time={self.time})" 