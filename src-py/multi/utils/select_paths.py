import logging
import random
from typing import List, Dict
from dataclasses import dataclass
from multi.entity import VesselPath

logger = logging.getLogger(__name__)

@dataclass
class PathSelectionConfig:
    """路径选择配置参数"""
    min_paths: int = 5
    max_paths: int = 20
    selection_ratio: float = 0.4
    weight_factor: float = 0.7

class SelectPaths:
    def __init__(self, input_data, params, config: PathSelectionConfig = None):
        """
        初始化路径选择器
        :param input_data: 输入数据对象
        :param params: 算法参数对象
        :param config: 路径选择配置
        """
        self.input_data = input_data
        self.params = params
        self.config = config or PathSelectionConfig()
        self.selected_paths: List[VesselPath] = []

    def select_paths(self) -> List[VesselPath]:
        """执行路径选择主逻辑"""
        try:
            logger.info("Starting path selection process...")
            
            # 过滤有效路径
            valid_paths = self._filter_valid_paths()
            
            # 计算路径权重
            weighted_paths = self._calculate_weights(valid_paths)
            
            # 排序并选择路径
            self.selected_paths = self._select_top_paths(weighted_paths)
            
            logger.info(f"Selected {len(self.selected_paths)} paths")
            return self.selected_paths
            
        except Exception as e:
            logger.error("Path selection failed", exc_info=True)
            raise RuntimeError("Path selection error") from e

    def _filter_valid_paths(self) -> List[VesselPath]:
        """过滤符合时间要求的路径"""
        current_time = self.params.time_horizon
        return [
            path for path in self.input_data.vessel_paths
            if path.departure_time <= current_time <= path.arrival_time
        ]

    def _calculate_weights(self, paths: List[VesselPath]) -> Dict[VesselPath, float]:
        """计算路径综合权重"""
        weights = {}
        for path in paths:
            time_factor = 1 / (path.duration ** self.config.weight_factor)
            cost_factor = 1 / path.operational_cost
            weights[path] = (time_factor + cost_factor) / 2
        return weights

    def _select_top_paths(self, weighted_paths: Dict[VesselPath, float]) -> List[VesselPath]:
        """选择最优路径集合"""
        # 按权重降序排序
        sorted_paths = sorted(weighted_paths.items(), 
                            key=lambda x: x[1], 
                            reverse=True)
        
        # 计算选择数量
        max_select = min(self.config.max_paths, 
                        max(self.config.min_paths, 
                            int(len(sorted_paths) * self.config.selection_ratio)))
        
        return [path for path, _ in sorted_paths[:max_select]]

    def visualize_selection(self):
        """可视化路径选择结果（待实现）"""
        pass