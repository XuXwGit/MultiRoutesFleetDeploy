from abc import ABC, abstractmethod

from design.core.algorithms.alns.destroy_operators import cost_based_destroy, random_destroy
from design.core.algorithms.alns.repair_operators import distance_greedy_repair, random_repair


class Operator(ABC):
    """算子抽象基类"""
    def __init__(self, name):
        self.name = name
        self.weight = 1.0
        self.score = 0
    
    @abstractmethod
    def apply(self, *args, **kwargs):
        pass

    def reset(self):
        # self.weight = 1.0
        self.score = 0

class OperatorWrapper(Operator):
        """算子包装器实现"""
        def __init__(self, func, name):
            super().__init__(name)
            self.func = func
            
        def apply(self, *args, **kwargs):
            return self.func(*args, **kwargs)
            
        def __call__(self, *args, **kwargs):
            return self.apply(*args, **kwargs)

class OperatorFactory:
    """算子工厂类（工厂模式）"""
    @staticmethod
    def create_destroy_operators():
        return [
            OperatorWrapper(random_destroy, 'random_destroy'),
            # OperatorWrapper(cost_based_destroy, 'cost_based_destroy')
        ]
    
    @staticmethod
    def create_repair_operators():
        return [
            OperatorWrapper(random_repair, 'random_repair'),
            OperatorWrapper(distance_greedy_repair, 'distance_greedy_repair')
        ]
