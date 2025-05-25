"""
网络模型包，包含船舶调度与多类型集装箱联合调度问题所需的所有网络相关类。

该包定义了问题中的各种网络组件，包括：
- 节点（Node）
- 弧（Arc）及其子类（TravelingArc, TransshipArc）
"""

from multi.network.node import Node
from multi.network.arc import Arc
from multi.network.traveling_arc import TravelingArc
from multi.network.transship_arc import TransshipArc

__all__ = [
    'Node',
    'Arc',
    'TravelingArc',
    'TransshipArc',
] 