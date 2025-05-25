"""
@Author: XuXw
@Description: 转运弧类，继承自Arc类
@DateTime: 2024/12/4 21:54
"""
from .arc import Arc
from .node import Node


class TransshipArc(Arc):
    """
    转运弧类，继承自Arc
    对应Java类: multi.network.TransshipArc
    """
    
    def __init__(self, 
                 id: int = 0, 
                 port: str = "",
                 origin_node: Node = None, 
                 destination_node: Node = None,
                 from_route: int = 0,
                 to_route: int = 0,
                 transship_time: int = 0,
                 ):
        """
        初始化转运弧对象
        
        Args:
            arc_id: 弧的唯一标识符，默认为0
            origin_node: 起始节点，默认为None
            destination_node: 目标节点，默认为None
        """
        # 调用父类构造函数
        super().__init__(id, origin_node, destination_node)
        
        # 转运弧特有属性
        self._transship_arc_id = id  # 对应Java: private int transshipArcID
        self._port = port  # 对应Java: private String port
        self._transship_time = transship_time  # 对应Java: private int transshipTime
        self._from_route = from_route  # 对应Java: private int fromRoute
        self._to_route = to_route  # 对应Java: private int toRoute

    # Getter和Setter方法
    @property
    def id(self) -> int:
        """
        获取弧ID
        对应Java: getter for id
        """
        return self._transship_arc_id

    @property
    def transship_arc_id(self) -> int:
        """
        获取转运弧ID
        对应Java: getter for transshipArcID
        """
        return self._transship_arc_id
    
    @transship_arc_id.setter
    def transship_arc_id(self, value: int):
        """
        设置转运弧ID
        对应Java: setter for transshipArcID
        """
        self._transship_arc_id = value
    
    @property
    def port(self) -> str:
        """
        获取转运港口名称
        对应Java: getter for port
        """
        return self._port
    
    @port.setter
    def port(self, value: str):
        """
        设置转运港口名称
        对应Java: setter for port
        """
        self._port = value
    
    @property
    def transship_time(self) -> int:
        """
        获取转运时间
        对应Java: getter for transshipTime
        """
        return self._transship_time
    
    @transship_time.setter
    def transship_time(self, value: int):
        """
        设置转运时间
        对应Java: setter for transshipTime
        """
        self._transship_time = value
    
    @property
    def from_route(self) -> int:
        """
        获取起始航线
        对应Java: getter for fromRoute
        """
        return self._from_route
    
    @from_route.setter
    def from_route(self, value: int):
        """
        设置起始航线
        对应Java: setter for fromRoute
        """
        self._from_route = value
    
    @property
    def to_route(self) -> int:
        """
        获取终止航线
        对应Java: getter for toRoute
        """
        return self._to_route
    
    @to_route.setter
    def to_route(self, value: int):
        """
        设置终止航线
        对应Java: setter for toRoute
        """
        self._to_route = value
        
    def __str__(self):
        """
        返回转运弧的字符串表示
        
        Returns:
            str: 转运弧的字符串描述
        """
        return f"TransshipArc(id={self.arc_id}, port={self.port}, from_route={self.from_route}, to_route={self.to_route})" 