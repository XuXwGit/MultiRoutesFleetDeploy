import logging

from typing import List, Optional, Tuple

from design.core.models.route_solution import RouteSolution

class CandidatePath:
    """表示运输网络中的候选路径
    
    Attributes:
        _od_pair: (origin, destination)元组
        _is_direct: 是否直达路径
        _arcs: 途径航段弧列表
        _transit_count: 中转次数
        _utility: 运输效用
        _travel_time: 运输时间
        _choice_probability: 选择概率
        _captured_demand: 捕获的运输需求
        _is_available: 路径是否可用
    """
    
    def __init__(self,
                 od_pair: Tuple[int, int],
                 is_direct: bool,
                 arcs: List[Tuple[int, int]],
                 transit_count: int = 0,
                 belong_route_solutions: Optional[List['RouteSolution']] = None
        ):
        """初始化候选路径
        
        Args:
            od_pair: (origin, destination)元组
            is_direct: 是否直达路径
            arcs: 途径航段弧列表
            transit_count: 中转次数，默认为0
            belong_route_solutions: 所属的RouteSolution列表，默认为None
        """
        self.od_pair = od_pair
        self.is_direct = is_direct
        self.arcs = arcs
        self.transit_count = transit_count
        self.belong_route_solutions = belong_route_solutions or []
        self.utility = 0.0
        self.travel_time = 0.0
        self.choice_probability = 0.0
        self.captured_demand = 0.0
        self.is_available = True
        
        if self.arcs == []:
            return None

        self.sequence = [e[0] for e in arcs]
        self.sequence.append(arcs[-1][1])

        if not self.check_feasible():
            return None
        

    def check_feasible(self) -> bool:
        """检查候选运输路径是否可行
        
        Returns:
            bool: 如果路径可行返回True，否则返回False
            
        Raises:
            ValueError: 如果路径弧列表为空
        """
        if not self.arcs:
            raise ValueError("路径弧列表不能为空")
            
        o, d = self.od_pair
        sequence = [arc[0] for arc in self.arcs]
        sequence.append(self.arcs[-1][1])
        
        # 检查起点和终点是否匹配
        if sequence[0] != o or sequence[-1] != d:
            return False
            
        # 检查起点和终点是否出现在路径中间
        if o in sequence[1:-1] or d in sequence[1:-1]:
            return False
            
        return True

    @staticmethod
    def merge(o_to_transit: 'CandidatePath', transit_to_d: 'CandidatePath') -> 'CandidatePath':
        """合并两条路径创建中转路径
        Args:
            o_to_transit: 从起点到中转节点的路径
            transit_to_d: 从中转节点到终点的路径
        Returns:
            合并后的中转路径
        Raises:
            ValueError: 如果路径无法合并
        """
        try:
            if not o_to_transit or not transit_to_d:
                raise ValueError("输入路径不能为空")
                
            # 检查中转节点是否匹配
            if o_to_transit.od_pair[1] != transit_to_d.od_pair[0]:
                raise ValueError(f"中转节点不匹配: {o_to_transit.od_pair[1]} != {transit_to_d.od_pair[0]}")
                
            # 检查路径连续性
            if o_to_transit.arcs and transit_to_d.arcs:
                last_arc = o_to_transit.arcs[-1]
                first_arc = transit_to_d.arcs[0]
                if last_arc[1] != first_arc[0]:
                    raise ValueError(f"路径不连续: {last_arc[1]} != {first_arc[0]}")
        except Exception as e:
            logging.warning(f"{o_to_transit.arcs} + {transit_to_d.arcs} 无法合成中转路径")
            return None
        
        transit_path = CandidatePath(
            od_pair=(o_to_transit.od_pair[0], transit_to_d.od_pair[1]),
            is_direct=False,
            arcs=o_to_transit.arcs + transit_to_d.arcs,
            transit_count=o_to_transit.transit_count + transit_to_d.transit_count + 1,
            belong_route_solutions=o_to_transit.belong_route_solutions + transit_to_d.belong_route_solutions    # 合并所属的RouteSolution
        )
    
        return transit_path