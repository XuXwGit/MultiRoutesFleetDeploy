from typing import List
import numpy as np

class Scenario:
    """场景类
    
    用于存储场景相关的数据:
    1. 需求数据
    2. 最差需求集合
    """
    
    def __init__(self, request: List[float] = None):
        """初始化场景
        
        Args:
            request: 需求数据列表
        """
        self.request = request
        self.worse_request_set = None
        
    def get_request(self) -> List[float]:
        """获取需求数据
        
        Returns:
            List[float]: 需求数据列表
        """
        return self.request
        
    def set_request(self, request: List[float]):
        """设置需求数据
        
        Args:
            request: 需求数据列表
        """
        self.request = request
        
    def get_worse_request_set(self) -> List[int]:
        """获取最差需求集合
        
        Returns:
            List[int]: 最差需求集合
        """
        return self.worse_request_set
        
    def set_worse_request_set(self, worse_request_set: List[int]):
        """设置最差需求集合
        
        Args:
            worse_request_set: 最差需求集合
        """
        self.worse_request_set = worse_request_set
        
    def __eq__(self, other) -> bool:
        """判断两个场景是否相等
        
        Args:
            other: 另一个场景对象
            
        Returns:
            bool: 是否相等
        """
        if self is other:
            return True
        if other is None or type(self) != type(other):
            return False
        return (np.array_equal(self.request, other.request) and 
                self.worse_request_set == other.worse_request_set)
        
    def __hash__(self) -> int:
        """计算场景的哈希值
        
        Returns:
            int: 哈希值
        """
        return hash((tuple(self.request) if self.request is not None else None,
                    tuple(self.worse_request_set) if self.worse_request_set is not None else None)) 