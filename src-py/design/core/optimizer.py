import logging
import sys
from pathlib import Path
from typing import Optional
# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

try:
    import gurobipy as gp
    from gurobipy import *
except ImportError:
    raise ImportError("Gurobi not installed. Please install Gurobi optimizer first")
import numpy as np

from .algorithms.algo import AlgoCore
from .models.network_data import NetworkData
from .models.network_model import NetworkModel
from ..utils.config import Config
from ..utils.visualization import NetworkVisualizer
from ..utils.data_processing import calculate_distance_matrix

class ShippingNetworkOptimizer:
    def __init__(self, network_data: NetworkData, run_mode: str = "APP", service_logger: Optional[logging.Logger] = None):
        """初始化模型，接收数据类实例"""
        self.network_data = network_data
        self.run_mode = run_mode
        self.service_logger = service_logger if service_logger is not None else logging.getLogger('algo_logger')
        self.network_model = NetworkModel(network_data, model_type='MILP')

        self.algo = AlgoCore(network_design_data=network_data, service_logger=self.service_logger)

        self.results = {}


    def add_test(self, algo_type = "ALNS", obj_type = "Cost"):
        self.results[obj_type] = {}
        self.results[obj_type]['algo_type'] = algo_type
        if algo_type == "ALNS":
            self.results[obj_type]['label'] = f"Objective: {obj_type}"
        elif algo_type == "Gurobi":
            self.results[obj_type]['label'] = f'Objective: {obj_type}'

    def optimize(self):
        ## benchmark method : solve MIQP with solver
        self.service_logger.info('============= Begin Optimize =============')
        res = {}
        res = self.network_model.solve(time_limit=self.network_data.config.MODEL_SOLVE_TIME_LIMIT) 
        # res = self.network_model.solve(time_limit=Config.MODEL_SOLVE_TIME_LIMIT) # 0.2小时超时
        # self.search_route_model.solve()
        initial_design_solution = res["design_solution"]

        # 记录Gurobi求解得到的初始解
        self.results["Gurobi"] = res

        for obj_type, _ in self.results.items():
            # 设置初始解
            self.algo.set_initial_solution(initial_design_solution)
            self.algo.set_obj_type(obj_type=obj_type)
            # 算法求解
            # inter_results = self.algo.solve(time_limit=Config.MODEL_SOLVE_TIME_LIMIT, max_iterations= Config.ALGO_MAXIMUM_ITERATIONS)
            inter_results = self.algo.solve(time_limit=self.network_data.config.MODEL_SOLVE_TIME_LIMIT, 
                                            max_iterations= self.network_data.config.ALGO_MAXIMUM_ITERATIONS)
            # 记录结果
            if inter_results is not None:
                self.results[obj_type].update(inter_results)

            if self.run_mode == 'TEST_ALGO':
                try:
                    # 可视化结果并保存
                    visualizer = NetworkVisualizer(network_data= self.network_data)
                    visualizer.plot_network(self.network_data.ports_df, inter_results["routes"])
                except Exception as e:
                    self.service_logger.debug(f"绘制结果出错：{e}")
        
        self.service_logger.info('============= End Optimize =============')
        return self.results