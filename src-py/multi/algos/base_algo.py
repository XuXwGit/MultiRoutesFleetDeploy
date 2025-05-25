from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from multi.data import InputData
from multi.model import Parameter

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """优化结果数据类"""
    objective_value: float = 0.0
    solve_time: float = 0.0
    iterations: int = 0
    is_optimal: bool = False
    operation_cost: float = 0.0
    laden_cost: float = 0.0
    empty_cost: float = 0.0
    rental_cost: float = 0.0
    penalty_cost: float = 0.0
    worst_performance: float = 0.0

class BaseAlgorithm(ABC):
    """算法基类"""
    
    def __init__(self, input_data: InputData, params: Parameter):
        """
        初始化算法实例
        :param input_data: 输入数据对象
        :param params: 算法参数对象
        """
        self.input_data = input_data
        self.params = params
        self.result = OptimizationResult()
        self._model = None  # 优化模型实例

    @abstractmethod
    def build_model(self):
        """构建优化模型"""
        pass

    @abstractmethod
    def solve(self) -> OptimizationResult:
        """执行求解过程"""
        pass

    def validate_solution(self) -> bool:
        """验证解的有效性"""
        # 基础验证逻辑
        if not self.result.is_optimal:
            logger.warning("Solution is not optimal")
            return False
        
        # 检查目标值合理性
        if self.result.objective_value < 0:
            logger.error("Invalid objective value")
            return False
            
        return True

    def save_results(self, file_path: Path):
        """保存优化结果到文件"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"=== Optimization Results ===\n")
                f.write(f"Objective Value: {self.result.objective_value:.2f}\n")
                f.write(f"Solve Time: {self.result.solve_time:.2f}s\n")
                f.write(f"Iterations: {self.result.iterations}\n")
                f.write(f"Optimal: {self.result.is_optimal}\n")
                f.write("\nCost Breakdown:\n")
                f.write(f"Operation Cost: {self.result.operation_cost:.2f}\n")
                f.write(f"Laden Cost: {self.result.laden_cost:.2f}\n")
                f.write(f"Empty Cost: {self.result.empty_cost:.2f}\n")
                f.write(f"Rental Cost: {self.result.rental_cost:.2f}\n")
                f.write(f"Penalty Cost: {self.result.penalty_cost:.2f}\n")
                f.write(f"Worst Performance: {self.result.worst_performance:.2f}\n")
            logger.info(f"Results saved to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save results: {str(e)}")
            raise

    def _log_solution_status(self):
        """记录解的状态信息"""
        logger.info(f"Objective Value: {self.result.objective_value:.2f}")
        logger.info(f"Solve Time: {self.result.solve_time:.2f}s")
        logger.info(f"Iterations: {self.result.iterations}")
        logger.info(f"Optimal Status: {'Optimal' if self.result.is_optimal else 'Suboptimal'}")