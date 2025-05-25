from typing import List
import cplex
import docplex

class PrimalDecision:
    """决策变量类
    
    存储模型中的决策变量:
    - xVar: 普通箱运输量决策变量
    - yVar: 租赁箱运输量决策变量
    - zVar: 空箱重定向决策变量
    - gVar: 需求未满足惩罚变量
    """
    
    def __init__(self):
        self.xVar: List[List[cplex.Variable]] = []  # 普通箱运输量决策变量
        self.yVar: List[List[cplex.Variable]] = []  # 租赁箱运输量决策变量
        self.zVar: List[List[cplex.Variable]] = []  # 空箱重定向决策变量
        self.gVar: List[cplex.Variable] = []  # 需求未满足惩罚变量 