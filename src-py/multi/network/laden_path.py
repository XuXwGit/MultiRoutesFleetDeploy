from dataclasses import dataclass, field
from typing import List, Optional
from .arc import Arc
from .container_path import ContainerPath

@dataclass
class LadenPath:
    """
    重箱路径类
    
    存储重箱路径相关的属性和信息
    
    属性:
        container_path: 集装箱路径对象
        request_id: 请求ID
        origin_port: 起始港口
        origin_time: 起始时间
        destination_port: 终止港口
        round_trip: 往返次数
        earliest_setup_time: 最早设置时间
        arrival_time_to_destination: 到达目的地时间
        path_time: 路径时间
        transshipment_port: 转运港口列表
        transshipment_time: 转运时间列表
        port_path: 港口路径列表
        path_id: 路径ID
        number_of_arcs: 弧的数量
        arcs_id: 弧ID列表
        arcs: 弧对象列表
    """
    
    request_id: int  # 请求ID
    origin_port: str  # 起始港口
    origin_time: int  # 起始时间
    destination_port: str  # 终止港口
    round_trip: int  # 往返次数
    earliest_setup_time: int  # 最早设置时间
    arrival_time_to_destination: int  # 到达目的地时间
    path_time: int  # 路径时间
    path_id: int  # 路径ID
    number_of_arcs: int  # 弧的数量
    container_path: Optional[ContainerPath] = None  # 集装箱路径对象
    transshipment_port: List[str] = field(default_factory=list)  # 转运港口列表
    transshipment_time: List[int] = field(default_factory=list)  # 转运时间列表
    port_path: List[str] = field(default_factory=list)  # 港口路径列表
    arc_ids: List[int] = field(default_factory=list)  # 弧ID列表
    arcs: List[Arc] = field(default_factory=list)  # 弧对象列表
    
    def __init__(self, request_id: int):
        self.request_id = request_id
        self.container_path = None
        self.transshipment_port = []
        self.transshipment_time = []
        self.port_path = []
        self.arc_ids = []
        self.arcs = []
        self.number_of_arcs = 0
        self.origin_port = ""
        self.origin_time = 0
        self.destination_port = ""
        self.round_trip = 0
        self.earliest_setup_time = 0
        self.arrival_time_to_destination = 0
        self.path_time = 0
        self.path_id = -1

    def get_transshipment_time(self) -> int:
        """
        获取总转运时间
        
        Returns:
            int: 总转运时间
        """
        return sum(self.transshipment_time) 