import logging
import os
import random
import sys
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DefaultSetting:
    """
    默认设置类
    
    定义系统运行所需的默认参数和配置
    """
    
    # 数值实验测试
    VESSEL_CAPACITY_RANGE = "I"  # 船舶容量范围
    FLEET_TYPE = "Hetero"        # 船队类型：Homo/Hetero
    
    # 集装箱设置
    ALLOW_FOLDABLE_CONTAINER = True  # 是否允许折叠箱
    IS_EMPTY_REPOSITION = False      # 空箱调度方式：是否重定向
    
    # 策略设置
    REDUCE_PATH_PERCENTAGE = 0       # 路径减少百分比
    MAX_LADEN_PATHS_NUM = 5         # 最大重箱路径数
    MAX_EMPTY_PATHS_NUM = 5         # 最大空箱路径数
    USE_PARETO_OPTIMAL_CUT = True   # 是否使用帕累托最优切割
    USE_LOCAL_SEARCH = True         # 是否使用局部搜索
    
    # 默认数据参数设置
    DEFAULT_UNIT_RENTAL_COST = 50           # 默认单位租赁成本
    DEFAULT_LADEN_DEMURRAGE_COST = 175      # 默认重箱滞期成本
    DEFAULT_EMPTY_DEMURRAGE_COST = 100      # 默认空箱滞期成本
    DEFAULT_UNIT_LOADING_COST = 20          # 默认单位装载成本
    DEFAULT_UNIT_DISCHARGE_COST = 20        # 默认单位卸载成本
    DEFAULT_UNIT_TRANSSHIPMENT_COST = 30    # 默认单位转运成本
    DEFAULT_TURN_OVER_TIME = 14             # 默认周转时间
    DEFAULT_FOLD_CONTAINER_PERCENT = 0.15   # 默认折叠箱比例
    DEFAULT_FOLD_EMPTY_COST_BIAS = 15       # 默认折叠空箱成本偏差
    
    # 调试设置
    DEBUG_ENABLE = False            # 是否启用调试
    GENERATE_PARAM_ENABLE = False   # 是否在生成参数时显示设置信息
    SUB_ENABLE = True              # 是否在子问题中显示设置信息
    DUAL_ENABLE = False            # 是否在对偶问题中显示设置信息
    DUAL_SUB_ENABLE = True         # 是否在对偶子问题中显示设置信息
    MASTER_ENABLE = False          # 是否在主问题中显示设置信息
    
    # 输入数据设置
    REQUEST_INCLUDE_RANGE = 0               # 请求包含范围
    WHETHER_ALLOW_SAME_REGION_TRANS = True  # 是否允许同区域转运
    WHETHER_CUTTING_OVER_COST_PATHS = True  # 是否切割超成本路径
    
    # 随机设置
    DISTRIBUTION_TYPE = "Uniform"           # 分布类型：Log-Normal/Uniform/Normal
    RANDOM_SEED = 0                         # 随机种子
    WHETHER_GENERATE_SAMPLES = True         # 是否生成样本
    WHETHER_CALCULATE_MEAN_PERFORMANCE = False  # 是否计算平均性能
    WHETHER_WRITE_SAMPLE_TESTS = False      # 是否写入样本测试
    WHETHER_LOAD_SAMPLE_TESTS = False       # 是否加载样本测试
    NUM_SAMPLE_SCENES = 10                  # 样本场景数量
    LOG_NORMAL_SIGMA_FACTOR = 1.0           # 对数正态分布sigma因子
    BUDGET_COEFFICIENT = 1.0                # 预算系数
    DEFAULT_UNCERTAIN_DEGREE = 0.15         # 默认不确定度
    PENALTY_COEFFICIENT = 1.0               # 惩罚系数
    INITIAL_EMPTY_CONTAINERS = 28           # 初始空箱数量
    
    # 日志设置
    WHETHER_WRITE_FILE_LOG = False          # 是否写入文件日志
    WHETHER_PRINT_FILE_LOG = False          # 是否打印文件日志
    WHETHER_PRINT_DATA_STATUS = False       # 是否打印数据状态
    WHETHER_PRINT_VESSEL_DECISION = False   # 是否打印船舶决策
    WHETHER_PRINT_REQUEST_DECISION = False  # 是否打印请求决策
    WHETHER_PRINT_ITERATION = True          # 是否打印迭代信息
    WHETHER_PRINT_SOLVE_TIME = False        # 是否打印求解时间
    WHETHER_PRINT_PROCESS = True            # 是否打印处理过程
    
    # CPLEX求解器设置
    WHETHER_EXPORT_MODEL = False            # 是否导出模型
    WHETHER_CLOSE_OUTPUT_LOG = True         # 是否关闭输出日志
    MIP_GAP_LIMIT = 1e-3                    # MIP求解间隙限制
    MIP_TIME_LIMIT = 36000                  # MIP求解时间限制（秒）
    MAX_THREADS = os.cpu_count()            # 最大线程数
    MAX_WORK_MEM = sys.maxsize >> 20        # 最大工作内存
    
    # 算法设置
    MAX_ITERATION_NUM = 100                 # 最大迭代次数
    MAX_ITERATION_TIME = 3600               # 最大迭代时间
    BOUND_GAP_LIMIT = 1.0                   # 边界间隙限制
    WHETHER_SET_INITIAL_SOLUTION = False    # 是否设置初始解
    WHETHER_ADD_INITIALIZE_SCE = False      # 是否添加初始化场景
    CCG_PAP_USE_SP = True                   # 是否使用CCG-PAP-SP
    USE_HISTORY_SOLUTION = False            # 是否使用历史解
    
    # Python编程设置
    WHETHER_USE_MULTI_THREAD = False        # 是否使用多线程
    PROGRESS_BAR_WIDTH = 50                 # 进度条宽度
    
    # 路径设置
    ROOT_PATH = os.getcwd() + "/"           # 根路径
    DATA_PATH = "data/"                     # 数据路径
    CASE_PATH = "1/"                        # 案例路径
    EXPORT_MODEL_PATH = "model/"            # 模型导出路径
    ALGO_LOG_PATH = "log/"                  # 算法日志路径
    SOLUTION_PATH = "solution/"             # 解决方案路径
    TEST_RESULT_PATH = "result/"            # 测试结果路径
    
    @staticmethod
    def draw_progress_bar(progress: int):
        """
        在控制台打印带百分比的进度条
        
        Args:
            progress: 进度长度（0-100）
        """
        completed_bars = progress * DefaultSetting.PROGRESS_BAR_WIDTH // 100
        progress_bar = ["\r["]
        
        for i in range(DefaultSetting.PROGRESS_BAR_WIDTH):
            if i < completed_bars:
                progress_bar.append("=")
            elif i == completed_bars:
                progress_bar.append(">")
            else:
                progress_bar.append(" ")
        
        progress_bar.append(f"] {progress}%")
        progress_bar.append("\r")
        
        print("".join(progress_bar), end="", flush=True)
    
    @staticmethod
    def print_settings():
        """
        打印基本设置信息
        """
        logger.info("======================Settings======================")
        logger.info(f"Vessel Capacity Range: {DefaultSetting.VESSEL_CAPACITY_RANGE}")
        logger.info(f"Fleet Type: {DefaultSetting.FLEET_TYPE}")
        logger.info(f"Allow Foldable Container: {DefaultSetting.ALLOW_FOLDABLE_CONTAINER}")
        logger.info(f"Is Empty Reposition: {DefaultSetting.IS_EMPTY_REPOSITION}")
        logger.info(f"Use Pareto Optimal Cut: {DefaultSetting.USE_PARETO_OPTIMAL_CUT}")
        logger.info(f"Use Local Search: {DefaultSetting.USE_LOCAL_SEARCH}")
        logger.info(f"Distribution Type: {DefaultSetting.DISTRIBUTION_TYPE}")
        logger.info(f"Random Seed: {DefaultSetting.RANDOM_SEED}")
        logger.info(f"Number of Sample Scenes: {DefaultSetting.NUM_SAMPLE_SCENES}")
        logger.info(f"MIP Gap Limit: {DefaultSetting.MIP_GAP_LIMIT}")
        logger.info(f"MIP Time Limit: {DefaultSetting.MIP_TIME_LIMIT}")
        logger.info(f"Max Threads: {DefaultSetting.MAX_THREADS}")
        logger.info(f"Max Work Memory: {DefaultSetting.MAX_WORK_MEM}")
        logger.info(f"Max Iteration Number: {DefaultSetting.MAX_ITERATION_NUM}")
        logger.info(f"Max Iteration Time: {DefaultSetting.MAX_ITERATION_TIME}")
        logger.info(f"Bound Gap Limit: {DefaultSetting.BOUND_GAP_LIMIT}")
        logger.info("==================================================")
    
    @staticmethod
    def write_settings(file_writer):
        """
        将设置信息写入文件
        
        Args:
            file_writer: 文件写入器
        """
        try:
            file_writer.write("======================Settings======================\n")
            file_writer.write(f"Vessel Capacity Range: {DefaultSetting.VESSEL_CAPACITY_RANGE}\n")
            file_writer.write(f"Fleet Type: {DefaultSetting.FLEET_TYPE}\n")
            file_writer.write(f"Allow Foldable Container: {DefaultSetting.ALLOW_FOLDABLE_CONTAINER}\n")
            file_writer.write(f"Is Empty Reposition: {DefaultSetting.IS_EMPTY_REPOSITION}\n")
            file_writer.write(f"Use Pareto Optimal Cut: {DefaultSetting.USE_PARETO_OPTIMAL_CUT}\n")
            file_writer.write(f"Use Local Search: {DefaultSetting.USE_LOCAL_SEARCH}\n")
            file_writer.write(f"Distribution Type: {DefaultSetting.DISTRIBUTION_TYPE}\n")
            file_writer.write(f"Random Seed: {DefaultSetting.RANDOM_SEED}\n")
            file_writer.write(f"Number of Sample Scenes: {DefaultSetting.NUM_SAMPLE_SCENES}\n")
            file_writer.write(f"MIP Gap Limit: {DefaultSetting.MIP_GAP_LIMIT}\n")
            file_writer.write(f"MIP Time Limit: {DefaultSetting.MIP_TIME_LIMIT}\n")
            file_writer.write(f"Max Threads: {DefaultSetting.MAX_THREADS}\n")
            file_writer.write(f"Max Work Memory: {DefaultSetting.MAX_WORK_MEM}\n")
            file_writer.write(f"Max Iteration Number: {DefaultSetting.MAX_ITERATION_NUM}\n")
            file_writer.write(f"Max Iteration Time: {DefaultSetting.MAX_ITERATION_TIME}\n")
            file_writer.write(f"Bound Gap Limit: {DefaultSetting.BOUND_GAP_LIMIT}\n")
            file_writer.write("==================================================\n")
        except Exception as e:
            logger.error(f"Error writing settings: {str(e)}")
            raise 