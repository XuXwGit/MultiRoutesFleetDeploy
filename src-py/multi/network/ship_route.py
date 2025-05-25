from dataclasses import dataclass, field
from typing import List, Dict, Optional
from ..entity.port import Port
from ..entity.vessel_path import VesselPath
from ..entity.vessel_type import VesselType

@dataclass
class ShipRoute:
    """
    航线类
    
    存储航线相关的属性和信息
    
    属性:
        ship_route_id: 航线ID
        cycle_time: 周期时间
        num_round_trips: 往返次数
        number_of_ports: 港口数量
        ports: 港口列表
        port_calls: 港口停靠映射(停靠索引->港口)
        number_of_call: 停靠次数
        ports_of_call: 停靠港口列表
        time_points_of_call: 停靠时间点列表
        num_vessel_paths: 船舶路径数量
        vessel_paths: 船舶路径列表
        vessel_type: 船舶类型
        fleet: 船队映射(轮次索引->船舶类型)
        available_vessels: 可用船舶映射(船舶ID->船舶类型)
    """
    def __init__(self, 
                 ship_route_id: int, 
                 time_points_of_call: List[int], 
                 ports_of_call: List[str]):
        self.ship_route_id = ship_route_id
        self.cycle_time = time_points_of_call[-1] - time_points_of_call[0]
        self.num_round_trips = self.cycle_time / 7  # 默认7天一个周期
        self.ports_of_call = ports_of_call
        self.number_of_ports = len(ports_of_call)
        self.number_of_call = 0

    ship_route_id: int  # 航线ID
    cycle_time: int  # 周期时间
    num_round_trips: int  # 往返次数
    number_of_ports: int  # 港口数量
    number_of_call: int  # 停靠次数
    num_vessel_paths: int  # 船舶路径数量
    ports: List[str] = field(default_factory=list)  # 港口列表
    port_calls: Dict[int, Port] = field(default_factory=dict)  # 港口停靠映射
    ports_of_call: List[str] = field(default_factory=list)  # 停靠港口列表
    vessel_paths: List[VesselPath] = field(default_factory=list)  # 船舶路径列表
    vessel_type: Optional[VesselType] = None  # 船舶类型
    fleet: Dict[int, VesselType] = field(default_factory=dict)  # 船队映射
    available_vessels: Dict[int, VesselType] = field(default_factory=dict)  # 可用船舶映射
    

    def add_port_call(self, port: Port):
        """
        添加港口停靠
        
        Args:
            port: 港口对象 

        Returns:
            int: 停靠索引，如果未找到则返回-1
        """
        self.ports_of_call.append(port)
        self.number_of_call += 1
        return self.number_of_call - 1
    
    def get_call_index_of_port(self, port: str) -> int:
        """
        获取港口的停靠索引
        
        Args:
            port: 港口名称
            
        Returns:
            int: 停靠索引，如果未找到则返回-1
        """
        for p in range(self.number_of_call - 1):
            if port == self.ports_of_call[p]:
                return p
        return -1 