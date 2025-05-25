from dataclasses import dataclass, field
from typing import List, Optional
import logging
from ..entity.port import Port
from .arc import Arc

logger = logging.getLogger(__name__)

@dataclass
class ContainerPath:
    """
    集装箱路径类
    
    存储集装箱路径相关的属性和信息
    
    属性:
        container_path_id: 集装箱路径ID
        origin_port: 起始港口
        origin_time: 起始时间
        destination_port: 终止港口
        destination_time: 终止时间
        path_time: 路径时间
        transshipment_port: 转运港口列表
        transshipment_time: 转运时间列表
        total_transship_time: 总转运时间
        transshipment_ports: 转运港口对象列表
        number_of_path: 路径数量
        port_path: 港口路径列表
        ports_in_path: 路径中的港口对象列表
        number_of_arcs: 弧的数量
        arcs_id: 弧ID列表
        arcs: 弧对象列表
        path_cost: 路径成本
    """
    container_path_id: int  # 集装箱路径ID
    origin_port: str  # 起始港口
    origin_time: int  # 起始时间
    destination_port: str  # 终止港口
    destination_time: int  # 终止时间
    path_time: int  # 路径时间
    number_of_path: int  # 路径数量
    number_of_arcs: int  # 弧的数量
    path_cost: float  # 路径成本
    transshipment_port: List[str] = field(default_factory=list)  # 转运港口列表
    transshipment_time: List[int] = field(default_factory=list)  # 转运时间列表
    total_transship_time: int = 0  # 总转运时间
    total_demurrage_time: int = 0  # 总滞期时间
    transshipment_ports: List[Port] = field(default_factory=list)  # 转运港口对象列表
    port_path: List[str] = field(default_factory=list)  # 港口路径列表
    ports_in_path: List[Port] = field(default_factory=list)  # 路径中的港口对象列表
    arcs_id: List[int] = field(default_factory=list)  # 弧ID列表
    arcs: List[Arc] = field(default_factory=list)  # 弧对象列表
    
    def __init__(self, container_path_id: int, origin_port: str, origin_time: int, destination_port: str, destination_time: int, path_time: int):
        self.container_path_id = container_path_id
        self.origin_port = origin_port
        self.origin_time = origin_time
        self.destination_port = destination_port
        self.destination_time = destination_time
        self.path_time = path_time
        self.number_of_path = 0
        self.number_of_arcs = 0
        self.path_cost = 0
        self.transshipment_port = []
        self.transshipment_time = []
        self.total_transship_time = 0
        self.transshipment_ports = []
        self.port_path = []
        self.ports_in_path = []
        self.arcs_id = []
        self.arcs = []
        
        

    def add_transshipment(self, port: Port, time: int):
        """
        添加转运港口和时间
        
        Args:
            port: 转运港口

        Returns:
            int: 转运港口索引
        """
        self.transshipment_port.append(port)
        self.transshipment_time.append(time)
        return len(self.transshipment_port) - 1
    
    def add_port_in_path(self, port: Port):
        """
        添加港口到路径中
        
        Args:
            port: 港口
        """
        self.port_path.append(port.port)
        self.ports_in_path.append(port)
        self.number_of_path += 1
        
    def add_arc(self, arc: Arc):
        """
        添加弧到路径中
        
        Args:
            arc: 弧

        Returns:
            int: 弧索引
        """
        self.arcs.append(arc)
        self.arcs_id.append(arc.id)
        self.number_of_arcs += 1
        return len(self.arcs) - 1

            

    def get_total_transshipment_time(self) -> int:
        """
        获取总转运时间
        
        Returns:
            int: 总转运时间
        """

        if not self.transshipment_port:
            self.total_transship_time = 0
            return 0
        
        total_transshipment_time = sum(self.transshipment_time)
        self.total_transship_time = total_transshipment_time
        return total_transshipment_time
    
    def get_total_demurrage_time(self) -> int:
        """
        获取总滞期时间
        
        Returns:
            int: 总滞期时间
        """
        if not self.transshipment_port:
            self.total_transship_time = 0
            return 0
        
        if len(self.transshipment_port) != len(self.transshipment_time):
            logger.error("Error in transshipment port num!")
        
        total_transshipment_time = 0
        total_demurrage_time = 0
        
        for time in self.transshipment_time:
            total_transshipment_time += time
            if time > 7:
                total_demurrage_time += (time - 7)
        
        self.total_transship_time = total_transshipment_time
        self.total_demurrage_time = total_demurrage_time
        return total_demurrage_time 