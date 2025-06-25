import logging
import time
from typing import Dict, List, Any
from multi.algos.algo_frame import AlgoFrame
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.network import Port, Node, Arc, VesselPath, Request, ShipRoute, ContainerPath, VesselType, ODRange
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem_reactive import DualSubProblemReactive
from multi.algos.benders_lazy_cons_callback_reactive import BendersLazyConsCallbackReactive

logger = logging.getLogger(__name__)

class BendersDecompositionReactive(AlgoFrame):
    """
    反应式Benders分解算法类
    
    继承自AlgoFrame,实现反应式Benders分解算法
    
    主要步骤:
    1. 初始化主问题模型和反应式子问题模型
    2. 主循环迭代直到收敛:
       a. 求解主问题(获取上界)
       b. 求解反应式子问题(获取下界)
       c. 生成反应式Benders割
       d. 检查收敛条件
    3. 输出最终结果

    主问题与子问题均包含如下容量约束:
    数学模型:
    Σ_i Σ_p (x_ip + y_ip + z_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
    其中:
        a_np: 路径p是否使用弧n
        C_h: 船舶类型h的容量
        V_hr: 船舶类型h分配到航线r的二元变量
        x_ip, y_ip, z_ip: 各类集装箱运输量
    对应Java注释:
    /*
    vessel capacity constraint
    /sum{X+Y+Z} <= V
    */
    /**
    * 设置船舶容量约束(对应数学模型中式8)
    * Σ_i Σ_p (x_ip + y_ip + z_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
    * 其中:
    * a_np: 路径p是否使用弧n
    * C_h: 船舶类型h的容量
    */
    """
    
    def __init__(self, input_data: InputData, p: Parameter):
        """
        初始化反应式Benders分解算法
        
        Args:
            input_data: 输入数据
            p: 模型参数
        """
        super().__init__()
        self.input_data = input_data
        self.p = p
        self.callback = None  # 反应式Benders回调
    
    def _initialize_models(self):
        """
        初始化模型
        """
        # 初始化主问题模型
        self.determine_model = DetermineModel(self.input_data, self.p)
        self.determine_model.build_model()
        
        # 初始化反应式子问题模型
        self.dual_sub_problem_reactive = DualSubProblemReactive(self.input_data, self.p)
        self.dual_sub_problem_reactive.build_model()
        
        # 初始化反应式Benders回调
        self.callback = BendersLazyConsCallbackReactive(self.input_data, self.p)
        self.callback.set_models(self.determine_model, self.dual_sub_problem_reactive)
    
    def frame(self):
        """
        执行反应式Benders分解算法
        
        主要步骤:
        1. 初始化模型
        2. 主循环迭代直到收敛:
           a. 求解主问题(获取上界)
           b. 求解反应式子问题(获取下界)
           c. 生成反应式Benders割
           d. 检查收敛条件
        3. 输出最终结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            
            # 初始化模型
            model_start_time = time.time()
            self._initialize_models()
            self.build_model_time = time.time() - model_start_time
            
            # 打开日志文件
            file_writer = None
            if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                file_writer = open(DefaultSetting.log_file_path, 'w')
            
            # 打印迭代标题
            self.print_iter_title(file_writer, self.build_model_time)
            
            # 主循环
            while self.iteration < DefaultSetting.MAX_ITERATION_NUM:
                # 求解主问题
                mp_start_time = time.time()
                self.determine_model.solve_model()
                mp_time = time.time() - mp_start_time
                
                # 获取主问题解
                self.upper_bound = self.determine_model.obj_val
                self.upper[self.iteration] = self.upper_bound
                
                # 求解反应式子问题
                sp_start_time = time.time()
                self.dual_sub_problem_reactive.solve_model()
                sp_time = time.time() - sp_start_time
                
                # 获取子问题解
                self.lower_bound = self.dual_sub_problem_reactive.obj_val
                self.lower[self.iteration] = self.lower_bound
                
                # 生成反应式Benders割
                self.callback.callback()
                
                # 计算总时间
                self.total_time = time.time() - start_time
                
                # 打印迭代信息
                self.print_iteration_detailed(file_writer, self.lower_bound, self.upper_bound,
                                           mp_time, sp_time, self.total_time)
                
                # 检查收敛
                if self._check_convergence():
                    self.solve_status = True
                    break
                
                # 更新迭代次数
                self.iteration += 1
            
            # 获取最终结果
            self._set_algo_results()
            
            # 输出结果
            self._output_results()
            
            # 关闭日志文件
            if file_writer:
                file_writer.close()
            
        except Exception as e:
            logger.error(f"Reactive Benders decomposition failed: {str(e)}")
            self.solve_status = False
    
    def _check_convergence(self) -> bool:
        """
        检查是否收敛
        
        Returns:
            bool: 是否收敛
        """
        # 计算间隙
        self.gap = abs(self.upper_bound - self.lower_bound) / (abs(self.lower_bound) + 1e-10)
        
        # 检查收敛条件
        if self.gap <= DefaultSetting.gap_tolerance:
            return True
        
        return False
    
    def _set_algo_results(self):
        """
        获取最终结果
        """
        # 获取目标函数值
        self.obj = self.determine_model.obj_val
        
        # 获取各种成本
        self.laden_cost = self.determine_model.laden_cost
        self.empty_cost = self.determine_model.empty_cost
        self.penalty_cost = self.determine_model.penalty_cost
        self.rental_cost = self.determine_model.rental_cost
    
    def _output_results(self):
        """
        输出结果
        """
        logger.info("Reactive Benders decomposition completed")
        logger.info(f"Solve status: {'Success' if self.solve_status else 'Failed'}")
        logger.info(f"Total time: {self.total_time:.2f}s")
        logger.info(f"Build model time: {self.build_model_time:.2f}s")
        logger.info(f"Final gap: {self.gap:.4f}")
        logger.info(f"Final objective value: {self.obj:.2f}")
        logger.info(f"Laden cost: {self.laden_cost:.2f}")
        logger.info(f"Empty cost: {self.empty_cost:.2f}")
        logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
        logger.info(f"Rental cost: {self.rental_cost:.2f}") 