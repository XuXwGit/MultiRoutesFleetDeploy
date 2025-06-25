from .alns_core import ALNS_solver
from .destroy_operators import random_destroy_single_route, cost_based_destroy_single_route
from .repair_operators import random_repair, distance_greedy_repair

class OperatorFactory:
    """算子工厂类（工厂模式+单例模式）"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def create_destroy_operators(self):
        """创建破坏算子实例"""
        return [
            ALNS_solver.OperatorWrapper(random_destroy_single_route, 'random_destroy'),
            ALNS_solver.OperatorWrapper(cost_based_destroy_single_route, 'cost_based_destroy')
        ]
    
    def create_repair_operators(self):
        """创建修复算子实例"""
        return [
            ALNS_solver.OperatorWrapper(random_repair, 'random_repair'),
            ALNS_solver.OperatorWrapper(distance_greedy_repair, 'distance_greedy_repair')
        ]
