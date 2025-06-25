from datetime import datetime
import logging
from pathlib import Path
import matplotlib.colors as mcolors
import os

class Config:  
    def __init__(self, 
                Instance: str = '1', 
                P: int = 30, 
                K:int = 350, 
                R: int = 8, 
                T: int = 3,
                seed:int = 0
                ):
         self.Instance = Instance
         self.P = P
         self.K = K
         self.R = R
         self.T = T
         self.seed = seed
         Config.INSTANCE = Instance
         Config.NUM_PORTS = P
         Config.NUM_ODS = K
         Config.NUM_ROUTES = R
         Config.MAXIMUM_TRANSIT_LIMIT = T
         Config.RANDOM_SEED = seed

    # RUN_MODE
    # "APP" for running in app
    # "TEST_ALGO" for testing algorithms
    RUN_MODE = 'APP'

    # Instance Parameter (need to set before running)
    INSTANCE = '-1'
    NUM_ODS = -1
    NUM_PORTS = -1
    NUM_ROUTES = -1
    RANDOM_SEED = -1
    MAXIMUM_TRANSIT_LIMIT = 3
    UNIT_TRAVEL_COST = 100

    # 求解时间限制
    MODEL_SOLVE_TIME_LIMIT = 60
    ALGO_MAXIMUM_ITERATIONS = 120

    # 路径配置
    PROJECT_DIR = Path.cwd()
    DATA_DIR = PROJECT_DIR / "data" 
    DEFAULT_PORT_FILE = DATA_DIR / INSTANCE / "ports.csv"
    LOGS_DIR = PROJECT_DIR / "logs"
    MODELS_DIR = PROJECT_DIR / "models"
    OUTPUT_DIR = PROJECT_DIR / "output"
    WORLD_MAP_DIR = DATA_DIR / "110m_cultural"


    # 模型参数
    DEFAULT_SPEED = 20  # 节
    MAX_ROUTES = 5

    # 问题类型
    DEFAULT_PROBLEM_TYPE = "Multi-Routes"
    
    # 网络配置参数
    # 默认值
    DEFAULT_NUM_PORTS = 30
    DEFAULT_NUM_ROUTES = 8
    DEFAULT_NUM_ODS = 10
    DEFAULT_RANDOM_SEED = 42  # 随机种子
    # 航线配置参数
    MIN_PORT_CALLS = 5  # 最小挂靠次数
    MAX_PORT_CALLS = 10  # 最大挂靠次数
    MIN_ROTATION_TIME = 7 * 24  # 最小周期时间(小时)
    MAX_ROTATION_TIME = 84 * 24  # 最大周期时间
    MAX_BUDGET = 1e6  # 最大预算


    # 字体与样式配置
    FONT_CONFIG = {
        'zh': {'family': 'SimSun', 'size': 12},
        'en': {'family': 'Times New Roman', 'size': 12}
    }
    
    # 绘制线型设置
    PLOT_STYLE = {
        'titlesize': 14,
        'fontsize': 12,
        'linewidth': 1.5,
        'dpi': 600,
        'marker_size': 8,
        'bar_width': 0.2
    }

    DEFAULT_LEGEND_LOC = 'upper right'

    # 求解方法 与 评价指标
    METHODS = ["Cost", "Utility", "Demand"]
    METRICS = ["Cost", "Utility", "Demand"]

    # 折线类型
    PLOT_ALGO_STYLE_MAP = {
         "Cost": {
              "color": "red",
              "marker": 's',
              "linestyle": 'solid',
         },
         "Utility":{
              "color": "blue",
              "marker": 'v',
              "linestyle": 'solid',
         }, 
         "Demand":{
              "color": "green",
              "marker": 'x',
              "linestyle": 'solid',
         }, 
         "Gurobi":{
              "color": "orange",
              "marker": 'd',
              "linestyle": 'solid',
         },
    }

    # 子图编号
    SUBPLOT_INDEXES = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)", "(h)", "(i)", "(j)", "(k)"]

    OBJ_TO_MODEL_MAP = {
         "Cost": "SND-A",
         "Utility": "SND-B",
         "Demand": "SND-C",
    }

    # 多语言标签配置
    LANGUAGE_LABEL_MAP = {
        'T': {
            'title': {'zh': '最大中转次数对结果的影响', 'en': 'The impact of the maximum number of transhipment'},
            'xlabel': {'zh': '最大中转次数', 'en': 'The maximum number of transhipment'},
            'ylabel': {'zh': '最大中转次数', 'en': 'The maximum number of transhipment'}
        },
        'K': {
            'title': {'zh': '运输需求OD数对结果的影响', 'en': 'The impact of the number of OD'},
            'xlabel': {'zh': '运输需求OD数', 'en': 'The number of OD'},
            'ylabel': {'zh': '运输需求OD数', 'en': 'The number of OD'}
        },
        "R": {
            'title': {'zh': '航线数量对结果的影响', 'en': 'The impact of the number of shipping routes'},
            'xlabel': {'zh': '航线数量', 'en': 'The number of shipping routes'},
            'ylabel': {'zh': '航线数量', 'en': 'The number of shipping routes'}
        }
    }

    # 定义 Route 到颜色的映射
    ROUTE_COLORS = {
            0: 'black',
            1: 'green',
            2: 'blue',
            3: 'red',
            4: 'yellow',
            5: 'purple',
            6: 'pink',
            7: 'brown',
            8: 'gray',
            9: 'cyan',
            10: 'magenta',
            11: 'olive',
            12: 'teal',
            13: 'coral',
            14: 'lavender',
            15: 'salmon',
            16: 'khaki',
            17: 'plum',
            18: 'sandybrown',
            19: 'lightgreen',
            20: 'lightblue',
            # 可以根据需要添加更多 Route 到颜色的映射
        }

    # Region_ID
    REGION_ID = {
        'East Asia': 1,
        'North America': 2,
        'South America': 3,  # 补充 South America 的 ID
        'Oceania': 4,
        'Europe': 5,
        'Mediterranean': 6,
        'North Europe': 7,
        'Default': 0
    }

    # 可视化配置
    COLOR_MAP = {
        'East Asia': mcolors.to_hex("#e74c3c"),          # 红色
        'North America': mcolors.to_hex("#3498db"),      # 蓝色
        'South America': mcolors.to_hex("#f1c40f"),      # 黄色
        'Oceania': mcolors.to_hex("#2ecc71"),            # 绿色
        'Europe': mcolors.to_hex("#9b59b6"),             # 紫色
        'Mediterranean': mcolors.to_hex("#f39c12"),      # 橙色
        'North Europe': mcolors.to_hex("#95a5a6"),       # 灰色
        'Default': mcolors.to_hex("#000000")             # 黑色
    }

    # 定义不同区域的颜色
    COLORS = {
        'East Asia': 'red',          # 红色
        'North America': 'blue',     # 蓝色
        'South America': 'yellow',   # 黄色
        'Oceania': 'green',          # 绿色
        'Europe': 'purple',          # 紫色
        'Mediterranean': 'orange',   # 橙色
        'North Europe': 'gray',      # 灰色
        'Default': 'black'           # 黑色
    }

    # 局部放大配置
    INSET_CONFIG = {
        'position': [0.6, 0.3, 0.35, 0.35],
        'xlim': (130, 160),
        'ylim': (20, 45)
    }

    @staticmethod
    def reset_logger():
        """初始化全局日志记录器（只执行一次）"""
        logger = logging.getLogger()

        # 清除已有handler避免重复
        if logger.hasHandlers():
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)

        logger.setLevel(logging.INFO)

        # 设置gurobipy日志级别为WARNING以减少输出
        gurobi_logger = logging.getLogger('gurobipy')
        gurobi_logger.setLevel(logging.WARNING)

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # 控制台日志（单例）
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger


    def setup_logger(self, ods = 0, seed: int = 0):
        """初始化全局日志记录器（只执行一次）"""
        logger = Config.reset_logger()

        # 设置gurobipy日志级别为ERROR以减少输出
        gurobi_logger = logging.getLogger('gurobipy')
        gurobi_logger.setLevel(logging.ERROR)

        log_file = self.create_log_file(ods= ods, seed= seed)
        formatter = logger.handlers[0].formatter

        # 文件日志（单例）
        if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # 确保gurobipy日志不会传播到根logger
        gurobi_logger.propagate = False

        self.print_config()
        return logger

    def create_log_file(self, ods: int = 0, seed: int = 0):
        """创建带时间戳的日志文件名"""
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        log_dir = Config.LOGS_DIR / f"{self.Instance}"  / f"P{Config.NUM_PORTS}" / f"R{Config.NUM_ROUTES}" / f"K{Config.NUM_ODS}"
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f"Instance_P{Config.NUM_PORTS}_R{Config.NUM_ROUTES}_K{ods}_T{Config.MAXIMUM_TRANSIT_LIMIT}_S{seed}_{timestamp}.log")
    
    @staticmethod
    def get_input_path(filename, instance = "1"):
        instance = str(instance)  # 确保instance是字符串
        input_path_dir = Config.DATA_DIR / instance
        if not input_path_dir.exists():
                os.makedirs(input_path_dir)
        return str(input_path_dir / filename)
    
    @staticmethod
    def get_output_path(filename, instance = '1'):
        instance = str(instance)  # 确保instance是字符串
        output_path_dir = Config.OUTPUT_DIR / instance 
        if not os.path.exists(output_path_dir):
                # 创建案例结果目录
                os.makedirs(output_path_dir)
        return str(output_path_dir / filename)
    
    def print_config(self):
        """打印当前配置信息"""
        logging.info("=========== Config Information ===========")
        logging.info(f"Running Time: {datetime.now().strftime('%Y/%m/%d-%H:%M:%S')}")
        logging.info(f"Instance: {self.Instance}")
        logging.info(f"Ports: P={self.P}")
        logging.info(f"OD Pairs: K={self.K}")
        logging.info(f"Routes: R={self.R}")
        logging.info(f"Transit Limit: T={self.T}")
        logging.info(f"Seed: {self.seed}")
        logging.info(f"Unit Travel Cost: {Config.UNIT_TRAVEL_COST}")
        logging.info(f"Algo Solve Time Limie: {Config.MODEL_SOLVE_TIME_LIMIT} s")
        logging.info(f"Maximum Iterations Limit: {Config.ALGO_MAXIMUM_ITERATIONS}")
        logging.info(f"Project Dir: {Config.PROJECT_DIR}")
        logging.info(f"Data Dir: {Config.DATA_DIR}")
        logging.info(f"Logs Dir: {Config.LOGS_DIR}")
        logging.info(f"Output Dir: {Config.OUTPUT_DIR}")