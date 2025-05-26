"""
@Author: XuXw
@Description: 订单/需求 类
@DateTime: 2024/12/4 21:31
"""
import logging
from typing import Dict, List, Optional
from .port import Port
from .container_path import ContainerPath

# 设置日志
logger = logging.getLogger(__name__)


class Request:
    """
    订单/需求类
    对应Java类: multi.network.Request
    
    该类包含了运输请求的所有相关信息，包括：
    - 请求基本信息（ID、到达时间等）
    - 需求统计信息（均值、方差）
    - 起终点信息（港口对象、港口名称、港口组）
    - 时间窗口（最早提货时间、最晚到达时间）
    - 路径信息（重箱路径和空箱路径）
    - 惩罚成本（未满足需求的惩罚）
    """
    
    def __init__(self, 
                 request_id: int = 0, 
                 origin_port: str = "", 
                 destination_port: str = "", 
                 earliest_pickup_time: int = 0, 
                 latest_destination_time: int = 0):
        """
        初始化Request对象
        
        Args:
            request_id: 请求ID，默认为0
            origin_port: 起始港口名称，默认为空字符串
            destination_port: 目标港口名称，默认为空字符串
            earliest_pickup_time: 最早提货时间，默认为0
            latest_destination_time: 最晚到达时间，默认为0
        """
        # 基本属性
        self._request_id = request_id  # 对应Java: private int requestID
        self._arrival_time = 0  # 对应Java: private int arrivalTime
        
        # 需求相关属性
        self._mean_demand = 0.0  # 对应Java: private double meanDemand
        self._variance_demand = 0.0  # 对应Java: private double varianceDemand
        
        # 成本属性
        self._penalty_cost = 0.0  # 对应Java: private double penaltyCost
        
        # 港口对象
        self._origin = None  # 对应Java: private Port origin
        self._destination = None  # 对应Java: private Port destination
        
        # 港口字符串表示
        self._origin_port = origin_port  # 对应Java: private String originPort
        self._destination_port = destination_port  # 对应Java: private String destinationPort
        self._origin_group = 0  # 对应Java: private int originGroup
        self._destination_group = 0  # 对应Java: private int destinationGroup
        self._earliest_pickup_time = earliest_pickup_time  # 对应Java: private int earliestPickupTime
        self._latest_destination_time = latest_destination_time  # 对应Java: private int latestDestinationTime
        
        # 重箱路径相关
        self._laden_path_set = {}  # 对应Java: private List<ContainerPath> ladenPathSet
        self._laden_paths = []  # 对应Java: private ContainerPath[] ladenPaths
        self._laden_path_indexes = []  # 对应Java: private int[] ladenPathIndexes
        self._number_of_laden_path = 0  # 对应Java: private int numberOfLadenPath
        
        # 空箱路径相关
        self._empty_path_set = []  # 对应Java: private List<ContainerPath> emptyPathSet
        self._empty_paths = []  # 对应Java: private int[] emptyPaths
        self._empty_path_indexes = []  # 对应Java: private int[] emptyPathIndexes
        self._number_of_empty_path = 0  # 对应Java: private int numberOfEmptyPath
    
    # Getter和Setter方法 - 对应Java的@Getter @Setter
    
    @property
    def request_id(self) -> int:
        """
        获取请求ID
        对应Java: getRequestID()
        """
        return self._request_id
    
    @request_id.setter
    def request_id(self, value: int):
        """
        设置请求ID
        对应Java: setRequestID(int requestID)
        """
        self._request_id = value
    
    @property
    def arrival_time(self) -> int:
        """
        获取到达时间
        对应Java: getArrivalTime()
        """
        return self._arrival_time
    
    @arrival_time.setter
    def arrival_time(self, value: int):
        """
        设置到达时间
        对应Java: setArrivalTime(int arrivalTime)
        """
        self._arrival_time = value
    
    @property
    def mean_demand(self) -> float:
        """
        获取需求均值
        对应Java: getMeanDemand()
        """
        return self._mean_demand
    
    @mean_demand.setter
    def mean_demand(self, value: float):
        """
        设置需求均值
        对应Java: setMeanDemand(double meanDemand)
        """
        self._mean_demand = value
    
    @property
    def variance_demand(self) -> float:
        """
        获取需求方差
        对应Java: getVarianceDemand()
        """
        return self._variance_demand
    
    @variance_demand.setter
    def variance_demand(self, value: float):
        """
        设置需求方差
        对应Java: setVarianceDemand(double varianceDemand)
        """
        self._variance_demand = value
    
    @property
    def penalty_cost(self) -> float:
        """
        获取惩罚成本
        对应Java: getPenaltyCost()
        """
        return self._penalty_cost
    
    @penalty_cost.setter
    def penalty_cost(self, value: float):
        """
        设置惩罚成本
        对应Java: setPenaltyCost(double penaltyCost)
        """
        self._penalty_cost = value
    
    @property
    def origin(self) -> Optional[Port]:
        """
        获取起始港口对象
        对应Java: getOrigin()
        """
        return self._origin
    
    @origin.setter
    def origin(self, value: Optional[Port]):
        """
        设置起始港口对象
        对应Java: setOrigin(Port origin)
        """
        self._origin = value
    
    @property
    def destination(self) -> Optional[Port]:
        """
        获取目标港口对象
        对应Java: getDestination()
        """
        return self._destination
    
    @destination.setter
    def destination(self, value: Optional[Port]):
        """
        设置目标港口对象
        对应Java: setDestination(Port destination)
        """
        self._destination = value
    
    @property
    def origin_port(self) -> str:
        """
        获取起始港口名称
        对应Java: getOriginPort()
        """
        return self._origin_port
    
    @origin_port.setter
    def origin_port(self, value: str):
        """
        设置起始港口名称
        对应Java: setOriginPort(String originPort)
        """
        self._origin_port = value
    
    @property
    def destination_port(self) -> str:
        """
        获取目标港口名称
        对应Java: getDestinationPort()
        """
        return self._destination_port
    
    @destination_port.setter
    def destination_port(self, value: str):
        """
        设置目标港口名称
        对应Java: setDestinationPort(String destinationPort)
        """
        self._destination_port = value
    
    @property
    def origin_group(self) -> int:
        """
        获取起始港口组
        对应Java: getOriginGroup()
        """
        return self._origin_group
    
    @origin_group.setter
    def origin_group(self, value: int):
        """
        设置起始港口组
        对应Java: setOriginGroup(int originGroup)
        """
        self._origin_group = value
    
    @property
    def destination_group(self) -> int:
        """
        获取目标港口组
        对应Java: getDestinationGroup()
        """
        return self._destination_group
    
    @destination_group.setter
    def destination_group(self, value: int):
        """
        设置目标港口组
        对应Java: setDestinationGroup(int destinationGroup)
        """
        self._destination_group = value
    
    @property
    def earliest_pickup_time(self) -> int:
        """
        获取最早提货时间
        对应Java: getEarliestPickupTime()
        """
        return self._earliest_pickup_time
    
    @earliest_pickup_time.setter
    def earliest_pickup_time(self, value: int):
        """
        设置最早提货时间
        对应Java: setEarliestPickupTime(int earliestPickupTime)
        """
        self._earliest_pickup_time = value
    
    @property
    def latest_destination_time(self) -> int:
        """
        获取最晚到达时间
        对应Java: getLatestDestinationTime()
        """
        return self._latest_destination_time
    
    @latest_destination_time.setter
    def latest_destination_time(self, value: int):
        """
        设置最晚到达时间
        对应Java: setLatestDestinationTime(int latestDestinationTime)
        """
        self._latest_destination_time = value
    
    @property
    def laden_path_set(self) -> Dict[int, ContainerPath]:
        """
        获取重箱路径集合
        对应Java: getLadenPathSet()
        """
        return self._laden_path_set
    
    @laden_path_set.setter
    def laden_path_set(self, value: Dict[int, ContainerPath]):
        """
        设置重箱路径集合
        对应Java: setLadenPathSet(List<ContainerPath> ladenPathSet)
        """
        self._laden_path_set = value
    
    @property
    def laden_paths(self) -> List[ContainerPath]:
        """
        获取重箱路径列表（List[ContainerPath]）
        """
        return self._laden_paths
    
    @laden_paths.setter
    def laden_paths(self, value: List[ContainerPath]):
        """
        设置重箱路径列表（List[ContainerPath]）
        """
        self._laden_paths = value
    
    @property
    def laden_path_indexes(self) -> List[int]:
        """
        获取重箱路径索引列表（List[int]，通常为container_path_id-1）
        """
        return self._laden_path_indexes
    
    @laden_path_indexes.setter
    def laden_path_indexes(self, value: List[int]):
        """
        设置重箱路径索引列表（List[int]，通常为container_path_id-1）
        """
        self._laden_path_indexes = value
    
    @property
    def number_of_laden_path(self) -> int:
        """
        获取重箱路径数量
        对应Java: getNumberOfLadenPath()
        """
        return self._number_of_laden_path
    
    @number_of_laden_path.setter
    def number_of_laden_path(self, value: int):
        """
        设置重箱路径数量
        对应Java: setNumberOfLadenPath(int numberOfLadenPath)
        """
        self._number_of_laden_path = value
    
    @property
    def empty_path_set(self) -> List[ContainerPath]:
        """
        获取空箱路径集合
        对应Java: getEmptyPathSet()
        """
        return self._empty_path_set
    
    @empty_path_set.setter
    def empty_path_set(self, value: List[ContainerPath]):
        """
        设置空箱路径集合
        对应Java: setEmptyPathSet(List<ContainerPath> emptyPathSet)
        """
        self._empty_path_set = value
    
    @property
    def empty_paths(self) -> List[ContainerPath]:
        """
        获取空箱路径列表（List[ContainerPath]）
        """
        return self._empty_paths
    
    @empty_paths.setter
    def empty_paths(self, value: List[ContainerPath]):
        """
        设置空箱路径列表（List[ContainerPath]）
        """
        self._empty_paths = value
    
    @property
    def empty_path_indexes(self) -> List[int]:
        """
        获取空箱路径索引列表（List[int]，通常为container_path_id-1）
        """
        return self._empty_path_indexes
    
    @empty_path_indexes.setter
    def empty_path_indexes(self, value: List[int]):
        """
        设置空箱路径索引列表（List[int]，通常为container_path_id-1）
        """
        self._empty_path_indexes = value
    
    @property
    def number_of_empty_path(self) -> int:
        """
        获取空箱路径数量
        对应Java: getNumberOfEmptyPath()
        """
        return self._number_of_empty_path
    
    @number_of_empty_path.setter
    def number_of_empty_path(self, value: int):
        """
        设置空箱路径数量
        对应Java: setNumberOfEmptyPath(int numberOfEmptyPath)
        """
        self._number_of_empty_path = value
        
    def __str__(self) -> str:
        """
        返回请求的字符串表示
        
        Returns:
            str: 请求的字符串描述
        """
        return (f"Request(id={self.request_id}, "
                f"from={self.origin_port}, "
                f"to={self.destination_port}, "
                f"demand={self.mean_demand})")
                
    def add_laden_path(self, path: ContainerPath) -> None:
        """
        添加重箱路径
        
        Args:
            path: 要添加的重箱路径
        """
        self._laden_path_set.append(path)
        if hasattr(path, 'container_path_id'):
            self._laden_paths.append(path.container_path_id)
        else:
            # 如果没有container_path_id属性，尝试使用id属性
            self._laden_paths.append(path.id if hasattr(path, 'id') else 0)
        self._number_of_laden_path += 1

    def add_empty_path(self, path: ContainerPath) -> None:
        """
        添加空箱路径
        
        Args:
            path: 要添加的空箱路径
        """
        self._empty_path_set.append(path)
        if hasattr(path, 'container_path_id'):
            self._empty_paths.append(path.container_path_id)
        else:
            # 如果没有container_path_id属性，尝试使用id属性
            self._empty_paths.append(path.id if hasattr(path, 'id') else 0)
        self._number_of_empty_path += 1 