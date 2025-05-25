from dataclasses import dataclass, field
from typing import List, Optional
from ..entity.port import Port
from .arc import Arc

@dataclass
class ContainerPath:
    """
    集装箱路径类，表示集装箱从起点到终点的运输路径。
    
    该类包含了路径的所有相关信息，包括：
    - 路径基本信息（ID、起终点、时间等）
    - 转运信息
    - 港口序列
    - 弧序列
    - 成本信息
    
    Attributes:
        container_path_id: 路径ID
        origin_port: 起始港口
        origin_time: 起始时间
        destination_port: 目的港口
        destination_time: 到达时间
        path_time: 路径总时间
        transshipment_port: 转运港口数组
        transshipment_time: 转运时间数组
        total_transship_time: 总转运时间
        transshipment_ports: 转运港口对象列表
        number_of_path: 路径中的港口数量
        port_path: 港口序列
        ports_in_path: 路径中的港口对象列表
        number_of_arcs: 路径中的弧数量
        arcs_id: 弧ID数组
        arcs: 弧对象列表
        path_cost: 路径成本
    """
    container_path_id: int
    origin_port: str
    origin_time: int
    destination_port: str
    destination_time: int
    path_time: int = 0
    transshipment_port: List[str] = field(default_factory=list)
    transshipment_time: List[int] = field(default_factory=list)
    total_transship_time: int = 0
    transshipment_ports: List[Port] = field(default_factory=list)
    number_of_path: int = 0
    port_path: List[str] = field(default_factory=list)
    ports_in_path: List[Port] = field(default_factory=list)
    number_of_arcs: int = 0
    arcs_id: List[int] = field(default_factory=list)
    arcs: List[Arc] = field(default_factory=list)
    path_cost: float = 0.0

    def __post_init__(self):
        """
        初始化后处理：计算路径时间
        """
        self.path_time = self.destination_time - self.origin_time

    def get_total_transshipment_time(self) -> int:
        """
        计算总转运时间
        
        Returns:
            int: 总转运时间
        """
        if not self.transshipment_port:
            self.total_transship_time = 0
            return 0
        
        total_time = sum(self.transshipment_time)
        self.total_transship_time = total_time
        return total_time

    def get_total_demurrage_time(self) -> int:
        """
        计算总滞期时间
        
        如果转运时间超过7天，超出部分计入滞期时间
        
        Returns:
            int: 总滞期时间
        """
        if not self.transshipment_port:
            self.total_transship_time = 0
            return 0
        
        if len(self.transshipment_port) != len(self.transshipment_time):
            raise ValueError("转运港口数量与转运时间数量不匹配")
        
        total_transship_time = 0
        total_demurrage_time = 0
        
        for time in self.transshipment_time:
            total_transship_time += time
            if time > 7:
                total_demurrage_time += (time - 7)
        
        self.total_transship_time = total_transship_time
        return total_demurrage_time

    def __str__(self):
        """
        返回路径的字符串表示
        
        Returns:
            str: 路径的字符串描述
        """
        return (f"ContainerPath(id={self.container_path_id}, "
                f"from={self.origin_port}, "
                f"to={self.destination_port}, "
                f"time={self.path_time})")

    def add_transshipment(self, port: Port, time: int):
        """
        添加转运信息
        
        Args:
            port: 转运港口
            time: 转运时间
        """
        self.transshipment_port.append(port.port)
        self.transshipment_time.append(time)
        self.transshipment_ports.append(port)

    def add_port(self, port: Port):
        """
        添加港口到路径
        
        Args:
            port: 要添加的港口
        """
        self.port_path.append(port.port)
        self.ports_in_path.append(port)
        self.number_of_path += 1

    def add_arc(self, arc: Arc):
        """
        添加弧到路径
        
        Args:
            arc: 要添加的弧
        """
        self.arcs.append(arc)
        self.arcs_id.append(arc.id)
        self.number_of_arcs += 1 