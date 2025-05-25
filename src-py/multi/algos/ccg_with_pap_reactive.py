import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.network import Port, Node, Arc, VesselPath, Request, ShipRoute, ContainerPath, VesselType, ODRange
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem_reactive import DualSubProblemReactive
from multi.model.primal.sub_problem_reactive import SubProblemReactive
from multi.algos.ccg_with_pap import CCGwithPAP
from multi.algos.algo_frame import AlgoFrame

logger = logging.getLogger(__name__)

class CCGwithPAP_Reactive(AlgoFrame):
    """
    带价格调整问题的反应式列生成算法类
    
    继承自AlgoFrame,实现带价格调整问题的反应式列生成算法
    
    主要步骤:
    1. 初始化主问题模型和反应式子问题模型
    2. 主循环迭代直到收敛:
       a. 求解主问题(获取上界)
       b. 求解反应式子问题(获取下界)
       c. 生成新列
       d. 求解价格调整问题
       e. 检查收敛条件
    3. 输出最终结果
    """
    
    def __init__(self, in_data: InputData, p: Parameter):
        """
        初始化带价格调整问题的反应式列生成算法
        
        Args:
            in_data: 输入数据
            p: 模型参数
        """
        super().__init__()
        self.in_data = in_data
        self.p = p
        self.sub_problem_reactive = None  # 反应式子问题模型
        self.dual_sub_problem_reactive = None  # 反应式对偶子问题模型
        self.reactive_obj_val = 0  # 反应式子问题目标函数值
        self.reactive_mip_gap = 0  # 反应式子问题MIP间隙
        self.reactive_solve_status = ""  # 反应式子问题求解状态
        self.reactive_laden_cost = 0  # 反应式子问题重箱运输成本
        self.reactive_empty_cost = 0  # 反应式子问题空箱运输成本
        self.reactive_penalty_cost = 0  # 反应式子问题需求未满足惩罚成本
        self.reactive_rental_cost = 0  # 反应式子问题集装箱租赁成本
    
    def _initialize_models(self):
        """
        初始化模型
        """
        # 初始化主问题模型
        self.determine_model = DetermineModel(self.in_data, self.p)
        self.determine_model.build_model()
        
        # 初始化对偶子问题模型
        self.dual_sub_problem = DualSubProblemReactive(self.in_data, self.p, self.p.tau)
        self.dual_sub_problem.build_model()
        
        # 初始化反应式子问题模型
        self.sub_problem_reactive = SubProblemReactive(self.in_data, self.p)
        self.sub_problem_reactive.build_model()
        
        # 初始化反应式对偶子问题模型
        self.dual_sub_problem_reactive = DualSubProblemReactive(self.in_data, self.p, self.p.tau)
        self.dual_sub_problem_reactive.build_model()
    
    def frame(self):
        """
        执行带价格调整问题的反应式列生成算法
        
        主要步骤:
        1. 初始化模型
        2. 主循环迭代直到收敛:
           a. 求解主问题(获取上界)
           b. 求解反应式子问题(获取下界)
           c. 生成新列
           d. 求解价格调整问题
           e. 检查收敛条件
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
                self.sub_problem_reactive.solve_model()
                sp_time = time.time() - sp_start_time
                
                # 获取子问题解
                self.lower_bound = self.sub_problem_reactive.obj_val
                self.lower[self.iteration] = self.lower_bound
                
                # 生成新列
                self._generate_new_columns()
                
                # 求解价格调整问题
                self._solve_price_adjustment_problem()
                
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
            self._get_final_results()
            
            # 输出结果
            self._output_results()
            
            # 关闭日志文件
            if file_writer:
                file_writer.close()
            
        except Exception as e:
            logger.error(f"Reactive column generation with PAP failed: {str(e)}")
            self.solve_status = False
    
    def _generate_new_columns(self):
        """
        生成新列
        """
        # 获取子问题解
        x_var = self.sub_problem_reactive.x_var
        y_var = self.sub_problem_reactive.y_var
        z_var = self.sub_problem_reactive.z_var
        g_var = self.sub_problem_reactive.g_var
        
        # 添加新列到主问题
        self.determine_model.add_new_columns(x_var, y_var, z_var, g_var)
    
    def _solve_price_adjustment_problem(self):
        """
        求解价格调整问题
        """
        # 获取主问题解
        x_var = self.determine_model.x_var
        y_var = self.determine_model.y_var
        z_var = self.determine_model.z_var
        g_var = self.determine_model.g_var
        
        # 计算第二组变量值
        x_var2 = self._calculate_second_vessel_allocation(x_var)
        
        # 更新主问题变量
        self.determine_model.update_variables(x_var2)
    
    def _calculate_second_vessel_allocation(self, x_var: Dict) -> Dict:
        """
        计算第二组船舶分配
        
        Args:
            x_var: 第一组船舶分配
            
        Returns:
            Dict: 第二组船舶分配
        """
        x_var2 = {}
        
        # 遍历所有船舶和航线
        for v in self.in_data.vessels:
            for r in self.in_data.routes:
                # 检查航线是否可行
                if self._is_route_feasible(v, r):
                    # 计算航线利润
                    profit = self._calculate_route_profit(v, r)
                    
                    # 如果利润为正,则分配船舶
                    if profit > 0:
                        x_var2[v, r] = 1
                    else:
                        x_var2[v, r] = 0
                else:
                    x_var2[v, r] = 0
        
        return x_var2
    
    def _is_route_feasible(self, vessel: Any, route: Any) -> bool:
        """
        检查航线是否可行
        
        Args:
            vessel: 船舶
            route: 航线
            
        Returns:
            bool: 是否可行
        """
        # 检查容量约束
        for arc in route.arcs:
            if arc in vessel.arcs:
                if vessel.capacity < arc.demand:
                    return False
        
        # 检查时间窗口约束
        for arc in route.arcs:
            if arc in vessel.arcs:
                if not self._check_time_window(vessel, arc):
                    return False
        
        return True
    
    def _check_time_window(self, vessel: Any, arc: Any) -> bool:
        """
        检查时间窗口约束
        
        Args:
            vessel: 船舶
            arc: 弧
            
        Returns:
            bool: 是否满足时间窗口约束
        """
        # 获取船舶到达时间
        arrival_time = vessel.get_arrival_time(arc)
        
        # 检查是否在时间窗口内
        if arrival_time < arc.earliest_time or arrival_time > arc.latest_time:
            return False
        
        return True
    
    def _calculate_route_profit(self, vessel: Any, route: Any) -> float:
        """
        计算航线利润
        
        Args:
            vessel: 船舶
            route: 航线
            
        Returns:
            float: 航线利润
        """
        # 计算收入
        revenue = 0
        for arc in route.arcs:
            if arc in vessel.arcs:
                revenue += arc.price * min(vessel.capacity, arc.demand)
        
        # 计算成本
        cost = 0
        for arc in route.arcs:
            if arc in vessel.arcs:
                cost += arc.cost * vessel.capacity
        
        return revenue - cost
    
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
    
    def _get_final_results(self):
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
        logger.info("Reactive column generation with PAP completed")
        logger.info(f"Solve status: {'Success' if self.solve_status else 'Failed'}")
        logger.info(f"Total time: {self.total_time:.2f}s")
        logger.info(f"Build model time: {self.build_model_time:.2f}s")
        logger.info(f"Final gap: {self.gap:.4f}")
        logger.info(f"Final objective value: {self.obj:.2f}")
        logger.info(f"Laden cost: {self.laden_cost:.2f}")
        logger.info(f"Empty cost: {self.empty_cost:.2f}")
        logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
        logger.info(f"Rental cost: {self.rental_cost:.2f}") 