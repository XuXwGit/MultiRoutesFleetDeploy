import logging
import pandas as  pd

from design.core.models.network_data import NetworkData
from src.test.experiment_runner import ExperimentRunner
from src.utils.config import Config
from src.utils.data_processing import load_port_data
from src.utils.visualization import NetworkVisualizer


class ExperimentAnalyzer:
    """实验分析器类，用于分析不同实验结果"""

    def __init__(self, 
                 ports_df: pd.DataFrame = None, 
                 instance: str = "1"):
        self.runner = ExperimentRunner()
        self.instance = instance
        self.ports_df = ports_df if ports_df != None else self.load_instance_data(self.instance)

    def load_instance_data(self, instance: str):
        # 加载港口数据
        logging.info(f"正在加载【案例{instance}】港口数据...")
        ports_df = load_port_data(instance = instance)
        logging.info(f"成功加载 【P = {len(ports_df)}】个港口信息")

        return ports_df

    def od_pairs_analysis(self):
        """OD对算法结果的影响分析"""
        # 配置优化参数
        ods_set = []
        if self.instance == '1':
            ods_set = [100, 200, 300, 400, 500, 600]
        elif self.instance == "2":
            # ods_set = [400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 1800]
            ods_set = [1100, 1300, 1500, 1700]
        random_seeds = [999]

        # 运行所有组合
        for ods in ods_set:
            for seed in random_seeds:
                 config = Config(Instance= self.instance, 
                                 P = len(self.ports_df), 
                                 K = ods, 
                                 seed= seed)
                 self.runner.run_optimization(
                    config= config,
                    ports_df= self.ports_df, 
                    P = len(self.ports_df),
                    K= ods, 
                    seed= seed
                )
        logging.info("【OD数量】试验结束")

    def transit_limit_analysis(self):
        """中转次数对算法结果的影响分析"""
        # 限制中转次数
        transit_limits = [0, 1, 2, 3, 4, 5]
        ods_set = [350]

        random_seed = 66

        # 运行所有组合
        for transit_limit in transit_limits:
            for ods in ods_set:
                config = Config(Instance= self.instance, 
                                P = len(self.ports_df), 
                                K = ods, 
                                T = transit_limit,
                                seed= random_seed)
                config.T = transit_limit
                Config.MAXIMUM_TRANSIT_LIMIT = transit_limit
                self.runner.run_optimization(
                        config= config,
                        ports_df= self.ports_df, 
                        P = len(self.ports_df),
                        K= ods, 
                        seed= random_seed
                    )
        logging.info("【中转次数】试验结束")


    def routes_number_analysis(self):
        """线路数量对算法结果的影响分析"""
        routes_number = []
        ods_set = []
        if self.instance == '1':
            routes_number = [4, 5, 6]
            ods_set = [200, 300, 400, 500, 600]
        elif self.instance == "2":
            routes_number = [6, 7, 8, 9, 10]
            ods_set = [600, 800, 1000, 1200, 1400]

        random_seed = 44

        # 运行所有组合
        for numR in routes_number:
            for ods in ods_set:
                config = Config(Instance= self.instance, 
                                P = len(self.ports_df), 
                                K = ods, 
                                R = numR,
                                seed= random_seed)
                Config.NUM_ROUTES = numR
                self.runner.run_optimization(
                        config= config,
                        ports_df= self.ports_df, 
                        P = len(self.ports_df),
                        K= ods, 
                        seed= random_seed
                    )
        logging.info("【线路数量】试验结束")