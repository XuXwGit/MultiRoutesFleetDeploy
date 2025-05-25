"""
@Author: XuXw
@Description: OD范围类，表示起讫点组对的需求和运费上下界
@DateTime: 2024/12/4 22:06

this class include the lower and upper bound
of demand and freight (unit penalty cost)
for a group pairs (origin group and destination group)
"""


class ODRange:
    """
    OD范围类，表示起讫点组对的需求和运费上下界
    对应Java类: multi.network.ODRange
    
    该类用于定义不同起讫点组对之间的需求量范围和运费范围，
    用于生成随机需求和确定惩罚成本等。
    """
    
    def __init__(self, 
                 origin_group: int,
                 destination_group: int,
                 demand_lower_bound: int,
                 demand_upper_bound: int,
                 freight_lower_bound: int,
                 freight_upper_bound: int):
        """
        初始化OD范围对象
        
        对应Java构造函数:
        public ODRange(int originGroup,
                      int destinationGroup,
                      int demandLowerBound,
                      int demandUpperBound,
                      int freightLowerBound,
                      int freightUpperBound)
                      
        Args:
            origin_group: 起始港口组
            destination_group: 目标港口组
            demand_lower_bound: 需求下界
            demand_upper_bound: 需求上界
            freight_lower_bound: 运费下界
            freight_upper_bound: 运费上界
        """
        # 使用final对应的只读属性
        self._origin_group = origin_group  # 对应Java: private final int originGroup
        self._destination_group = destination_group  # 对应Java: private final int destinationGroup
        self._demand_lower_bound = demand_lower_bound  # 对应Java: private final int demandLowerBound
        self._demand_upper_bound = demand_upper_bound  # 对应Java: private final int demandUpperBound
        self._freight_lower_bound = freight_lower_bound  # 对应Java: private final int freightLowerBound
        self._freight_upper_bound = freight_upper_bound  # 对应Java: private final int freightUpperBound
    
    # 只提供getter方法，因为Java中这些是final字段
    @property
    def origin_group(self) -> int:
        """
        获取起始港口组
        对应Java: getOriginGroup()
        """
        return self._origin_group
    
    @property
    def destination_group(self) -> int:
        """
        获取目标港口组
        对应Java: getDestinationGroup()
        """
        return self._destination_group
    
    @property
    def demand_lower_bound(self) -> int:
        """
        获取需求下界
        对应Java: getDemandLowerBound()
        """
        return self._demand_lower_bound
    
    @property
    def demand_upper_bound(self) -> int:
        """
        获取需求上界
        对应Java: getDemandUpperBound()
        """
        return self._demand_upper_bound
    
    @property
    def freight_lower_bound(self) -> int:
        """
        获取运费下界
        对应Java: getFreightLowerBound()
        """
        return self._freight_lower_bound
    
    @property
    def freight_upper_bound(self) -> int:
        """
        获取运费上界
        对应Java: getFreightUpperBound()
        """
        return self._freight_upper_bound

    def __str__(self):
        """
        返回范围的字符串表示
        
        Returns:
            str: 范围的字符串描述
        """
        return (f"ODRange(origin={self.origin_group}, "
                f"destination={self.destination_group}, "
                f"demand=[{self.demand_lower_bound}, {self.demand_upper_bound}], "
                f"freight=[{self.freight_lower_bound}, {self.freight_upper_bound}])")

    def contains_demand(self, demand: int) -> bool:
        """
        检查给定的需求是否在范围内
        
        Args:
            demand: 要检查的需求值
            
        Returns:
            bool: 如果需求在范围内返回True，否则返回False
        """
        return self.demand_lower_bound <= demand <= self.demand_upper_bound

    def contains_freight(self, freight: int) -> bool:
        """
        检查给定的运价是否在范围内
        
        Args:
            freight: 要检查的运价值
            
        Returns:
            bool: 如果运价在范围内返回True，否则返回False
        """
        return self.freight_lower_bound <= freight <= self.freight_upper_bound 