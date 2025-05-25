from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..entity.port import Port

@dataclass
class Node:
    """
    网络节点类，表示运输网络中的一个时空节点。
    
    每个节点代表在特定时间点特定港口的状态，用于构建时空网络。
    节点包含入边和出边，用于表示船舶和集装箱的移动。
    
    Attributes:
        id: 节点唯一标识符
        port_id: 所属港口ID
        port_string: 港口字符串
        node_id: 节点ID
        route: 航线
        call: 停靠次数
        round_trip: 所属往返
        time: 时间点
        port: 关联的港口对象
        incoming_arcs: 入边列表，表示到达该节点的所有弧
        outgoing_arcs: 出边列表，表示从该节点出发的所有弧
        attributes: 其他属性字典，用于存储额外的节点信息
    """
    id: int
    time_period: int
    port_string: str  # 港口字符串
    node_id: int  # 节点ID
    route: int  # 航线
    call: int  # 停靠次数
    round_trip: int  # 往返次数
    time: int  # 时间点
    port: Optional[Port] = None  # 关联的港口对象
    incoming_arcs: List[Any] = field(default_factory=list)  # List of Arc
    outgoing_arcs: List[Any] = field(default_factory=list)  # List of Arc
    attributes: Dict[str, Any] = field(default_factory=dict)

    def __init__(self, id: int, port_string: str, node_id: int, route: int, call: int, round_trip: int, time: int, port: Optional[Port] = None):
        self.id = id
        self.time = time
        self.port_string = port_string
        self.node_id = node_id
        self.route = route
        self.call = call
        self.round_trip = round_trip
        self.port = port
    

    def add_incoming_arc(self, arc: Any):
        """
        添加一条入边到节点
        
        Args:
            arc: 要添加的弧对象
        """
        self.incoming_arcs.append(arc)

    def add_outgoing_arc(self, arc: Any):
        """
        添加一条出边到节点
        
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
        return f"Node(id={self.id}, port={self.port_id}, time={self.time_period})" 