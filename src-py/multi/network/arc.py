"""
@Author: xuxw
@Description: 网络弧类
@DateTime: 2024/12/18 16:30
"""
from typing import Optional
# from multi.network.node import Node  # 移除顶部import，延迟导入

class Arc:
    """
    弧/边类，表示网络中的连接
    对应Java类: multi.network.Arc
    """
    
    def __init__(self, 
                 arc_id: int = 0, 
                 origin_node: Optional["Node"] = None, 
                 destination_node: Optional["Node"] = None):
        """
        初始化Arc对象
        
        Args:
            arc_id: 弧的唯一标识符，默认为0
            origin_node: 起始节点，默认为None
            destination_node: 目标节点，默认为None
        """
        # 延迟导入，避免循环依赖
        # from multi.network.node import Node
        # 基本属性
        self._arc_id = arc_id  # 对应Java: private int arcID
        self._origin_node_id = origin_node.id  # 对应Java: private int originNodeID
        self._destination_node_id = destination_node.id  # 对应Java: private int destinationNodeID
        self._origin_port = origin_node.port  # 对应Java: private String originPort
        self._destination_port = destination_node.port  # 对应Java: private String destinationPort
        self._origin_node = origin_node  # 对应Java: private Node originNode
        self._destination_node = destination_node  # 对应Java: private Node destinationNode
        self._origin_call = origin_node.call  # 对应Java: private int originCall
        self._destination_call = destination_node.call  # 对应Java: private int destinationCall
        self._origin_time = origin_node.time  # 对应Java: private int originTime
        self._destination_time = destination_node.time  # 对应Java: private int destinationTime
        
        # 弧类型："Traveling Arc" or "Transship Arc"
        self._arc_type = ""  # 对应Java: private String arcType
        
        # 若节点不为空，将弧添加到节点的边集合中
        if origin_node:
            origin_node.add_outgoing_arc(self)
        if destination_node:
            destination_node.add_incoming_arc(self)
    
    # Getter和Setter方法
    @property
    def id(self) -> int:
        """
        获取弧ID
        对应Java: getter for id
        """
        return self._arc_id


    @property
    def arc_id(self) -> int:
        """
        获取弧ID
        对应Java: getter for arcID
        """
        return self._arc_id
    
    @arc_id.setter
    def arc_id(self, value: int):
        """
        设置弧ID
        对应Java: setter for arcID
        """
        self._arc_id = value
    
    @property
    def origin_node_id(self) -> int:
        """
        获取起始节点ID
        对应Java: getter for originNodeID
        """
        return self._origin_node_id
    
    @origin_node_id.setter
    def origin_node_id(self, value: int):
        """
        设置起始节点ID
        对应Java: setter for originNodeID
        """
        self._origin_node_id = value
    
    @property
    def destination_node_id(self) -> int:
        """
        获取目标节点ID
        对应Java: getter for destinationNodeID
        """
        return self._destination_node_id
    
    @destination_node_id.setter
    def destination_node_id(self, value: int):
        """
        设置目标节点ID
        对应Java: setter for destinationNodeID
        """
        self._destination_node_id = value
    
    @property
    def origin_port(self) -> str:
        """
        获取起始港口
        对应Java: getter for originPort
        """
        return self._origin_port
    
    @origin_port.setter
    def origin_port(self, value: str):
        """
        设置起始港口
        对应Java: setter for originPort
        """
        self._origin_port = value
    
    @property
    def destination_port(self) -> str:
        """
        获取目标港口
        对应Java: getter for destinationPort
        """
        return self._destination_port
    
    @destination_port.setter
    def destination_port(self, value: str):
        """
        设置目标港口
        对应Java: setter for destinationPort
        """
        self._destination_port = value
    
    @property
    def origin_node(self) -> Optional["Node"]:
        """
        获取起始节点
        对应Java: getter for originNode
        """
        return self._origin_node
    
    @origin_node.setter
    def origin_node(self, value: Optional["Node"]):
        """
        设置起始节点
        对应Java: setter for originNode
        """
        self._origin_node = value
    
    @property
    def destination_node(self) -> Optional["Node"]:
        """
        获取目标节点
        对应Java: getter for destinationNode
        """
        return self._destination_node
    
    @destination_node.setter
    def destination_node(self, value: Optional["Node"]):
        """
        设置目标节点
        对应Java: setter for destinationNode
        """
        self._destination_node = value
    
    @property
    def origin_call(self) -> int:
        """
        获取起始停靠
        对应Java: getter for originCall
        """
        return self._origin_call
    
    @origin_call.setter
    def origin_call(self, value: int):
        """
        设置起始停靠
        对应Java: setter for originCall
        """
        self._origin_call = value
    
    @property
    def destination_call(self) -> int:
        """
        获取目标停靠
        对应Java: getter for destinationCall
        """
        return self._destination_call
    
    @destination_call.setter
    def destination_call(self, value: int):
        """
        设置目标停靠
        对应Java: setter for destinationCall
        """
        self._destination_call = value
    
    @property
    def origin_time(self) -> int:
        """
        获取起始时间
        对应Java: getter for originTime
        """
        return self._origin_time
    
    @origin_time.setter
    def origin_time(self, value: int):
        """
        设置起始时间
        对应Java: setter for originTime
        """
        self._origin_time = value
    
    @property
    def destination_time(self) -> int:
        """
        获取目标时间
        对应Java: getter for destinationTime
        """
        return self._destination_time
    
    @destination_time.setter
    def destination_time(self, value: int):
        """
        设置目标时间
        对应Java: setter for destinationTime
        """
        self._destination_time = value
    
    @property
    def arc_type(self) -> str:
        """
        获取弧类型
        对应Java: getter for arcType
        """
        return self._arc_type
    
    @arc_type.setter
    def arc_type(self, value: str):
        """
        设置弧类型
        对应Java: setter for arcType
        """
        self._arc_type = value
    
    def __str__(self):
        """
        返回弧的字符串表示
        
        Returns:
            str: 弧的字符串描述
        """
        return f"Arc(id={self.arc_id}, from={self.origin_node_id}, to={self.destination_node_id})" 