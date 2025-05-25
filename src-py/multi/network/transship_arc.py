from dataclasses import dataclass
from .arc import Arc
from .node import Node

@dataclass
class TransshipArc(Arc):
    """
    转运弧类
    
    继承自Arc类，表示运输网络中的转运弧
    
    属性:
        transship_arc_id: 转运弧ID
        port: 转运港口
        transship_time: 转运时间
        from_route: 起始航线
        to_route: 终止航线
    """
    def __init__(self, id: int, port: str, transship_time: int, from_route: int, to_route: int, origin_node: Node, destination_node: Node, cost: float = 0, capacity: float = 0):
        super().__init__(id, origin_node, destination_node, cost, capacity)
        self.id = id
        self.transship_arc_id = id
        self.port = port
        self.transship_time = transship_time
        self.from_route = from_route
        self.to_route = to_route

    transship_arc_id: int  # 转运弧ID
    port: str  # 转运港口
    transship_time: int  # 转运时间
    from_route: int  # 起始航线
    to_route: int  # 终止航线 