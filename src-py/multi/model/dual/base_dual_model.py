import traceback
import numpy as np
from typing import List, Dict, Any, Tuple

from tqdm import tqdm
from multi.model.base_model import BaseModel
from multi.utils.parameter import Parameter
from multi.utils.input_data import InputData
from multi.utils.default_setting import DefaultSetting
from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import logging
from dataclasses import dataclass
from multi.entity.request import Request
from concurrent.futures import ThreadPoolExecutor
import threading
import time

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('base_dual_model.log')  # 文件输出
    ]
)

# 获取日志记录器
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 确保日志处理器不会重复
if not logger.handlers:
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加处理器到日志记录器
    logger.addHandler(console_handler)

class BaseDualModel(BaseModel):
    """对偶问题基类
    
    实现了对偶问题的基础功能:
    1. 变量定义
    2. 约束构建
    3. 目标函数构建
    4. 求解方法
    """
    _tau: int = 0


    def __init__(self, input_data: InputData, param: Parameter):
        """初始化对偶问题
        
        Args:
            in_data: 输入数据
            param: 模型参数
        """
        super().__init__(input_data, param)
        
        # 对偶变量
        self.dual_variables = {
            'lambda': None,  # 容量约束对偶变量
            'alpha': None,      # 需求约束对偶变量
            'beta': None,      # 容量约束对偶变量
            'gamma': None,      # 空箱流约束对偶变量
        }
        
        # 对偶目标值
        self.dual_objective = 0.0
        
        # 对偶间隙
        self.dual_gap = 0.0
        
        self._tau = 0

        # 基本属性
        self.obj_expr = None
        self.scene = None
        
        # 决策变量
        self.alpha_var = []  # α[i]
        self.beta_var = []   # β[nn']
        self.gamma_var = []  # γ[p][t]
        
        # 约束条件
        self.c1 = {}  # 对偶约束X
        self.c2 = {}  # 对偶约束Y
        self.c3 = {}  # 对偶约束Z
        self.c4 = {}  # 对偶约束G
        
        # 目标函数
        self.objective = None
        
        # 设置输入数据和参数
        self.input_data = input_data
        self.param = param
        
        self.obj_val = 0.0
        self.obj_gap = 0.0
        self.solve_time = 0.0
        self.v_var_value = None
        self.u_value = []
        self.operation_cost = 0.0
        self.laden_cost = 0.0
        self.empty_cost = 0.0
        self.rental_cost = 0.0
        self.penalty_cost = 0.0
        self.solve_status = None
        self.solution = None
    
    
    def initialize(self):
        """初始化模型"""
        # 创建CPLEX模型
        try:
            self.cplex = Model(name="BaseDualModel")
            if self.input_data is not None and self.param is not None:
                self.public_setting(self.cplex)
                self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise

    def build_variables(self):
        """构建变量"""

        # 需求约束对偶变量
        self.alpha_var = [None] * len(self.input_data.requests)
        for i, request in enumerate(self.input_data.requests):
            self.alpha_var[i] = self.cplex.continuous_var(
                lb=float('-inf'),
                ub=request.penalty_cost,
                name=f"alpha({i})"
            )
        self.dual_variables['alpha'] = self.alpha_var

        # 容量约束对偶变量
        self.beta_var = [None] * len(self.input_data.traveling_arcs)
        for nn, arc in enumerate(self.input_data.traveling_arcs):
            self.beta_var[nn] = self.cplex.continuous_var(
                lb=float('-inf'),
                ub=0,
                name=f"beta({nn})"
            )
        self.dual_variables['beta'] = self.beta_var
                
        # 空箱约束对偶变量
        self.gamma_var = [[None for _ in range(len(self.param.time_point_set))] 
                         for _ in range(len(self.input_data.port_set))]
        for pp in range(len(self.input_data.port_set)):
            for t in range(0, len(self.param.time_point_set)):
                self.gamma_var[pp][t] = self.cplex.continuous_var(
                    lb=0,
                    ub=float('inf'),
                    name=f"gamma({pp})({t})"
                )
        self.dual_variables['gamma'] = self.gamma_var
        
        
    def build_constraints(self):
        """构建约束"""
        # 容量约束
        self.build_capacity_constraints()
        
        # 需求约束
        self.build_demand_constraints()
        
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_capacity_constraints(self):
        """设置容量约束（对偶）
        
        数学模型:
        β_n ≤ 0, ∀n ∈ N
        其中:
            β_n: 船舶容量约束的对偶变量
        对应Java注释:
        /*
        dual vessel capacity constraint
        β <= 0
        */
        /**
        * 设置对偶容量约束
        * β_n ≤ 0, ∀n ∈ N
        * 其中:
        * β_n: 船舶容量约束的对偶变量
        */
        """
        # 容量约束
        self.build_capacity_constraints()
        
        # 需求约束
        self.build_demand_constraints()
        
        # 时间约束
        self.build_time_constraints()
        
        # 路径约束
        self.build_path_constraints()
        
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_demand_constraints(self):
        """设置需求约束（对偶）
        
        数学模型:
        α_i ≤ 惩罚成本, ∀i ∈ I
        其中:
            α_i: 需求约束的对偶变量
        对应Java注释:
        /*
        dual demand constraint
        α <= penalty
        */
        /**
        * 设置对偶需求约束
        * α_i ≤ 惩罚成本, ∀i ∈ I
        * 其中:
        * α_i: 需求约束的对偶变量
        */
        """
        # 需求约束
        self.build_demand_constraints()
        
        # 时间约束
        self.build_time_constraints()
        
        # 路径约束
        self.build_path_constraints()
        
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_time_constraints(self):
        """设置时间约束（对偶）
        
        数学模型:
        γ_pt ≥ 0, ∀p ∈ P, t ∈ T
        其中:
            γ_pt: 空箱流约束的对偶变量
        对应Java注释:
        /*
        dual empty container constraint
        γ >= 0
        */
        /**
        * 设置对偶空箱流约束
        * γ_pt ≥ 0, ∀p ∈ P, t ∈ T
        * 其中:
        * γ_pt: 空箱流约束的对偶变量
        */
        """
        # 时间约束
        self.build_time_constraints()
        
        # 路径约束
        self.build_path_constraints()
        
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_path_constraints(self):
        """设置路径约束（对偶）
        
        数学模型:
        ...（补全具体路径约束公式）
        对应Java注释:
        /*
        dual path constraint
        */
        /**
        * 设置对偶路径约束
        */
        """
        # 路径约束
        self.build_path_constraints()
        
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_vessel_constraints(self):
        """设置船舶约束（对偶）
        
        数学模型:
        ...（补全具体船舶约束公式）
        对应Java注释:
        /*
        dual vessel assignment constraint
        */
        /**
        * 设置对偶船舶分配约束
        */
        """
        # 船舶约束
        self.build_vessel_constraints()
        
    def build_objective(self):
        """构建目标函数"""
        # 容量约束项
        capacity_term = np.sum(
            self.dual_variables['lambda'] * self.param.vessel_capacity
        )
        
        # 需求约束项
        demand_term = np.sum(
            self.dual_variables['mu'] * self.param.demand
        )
        
        # 时间约束项
        time_term = np.sum(
            self.dual_variables['nu'] * self.param.turnover_time
        )
        
        # 路径约束项
        path_term = np.sum(
            self.dual_variables['xi'] * self.param.travel_time_on_path
        )
        
        # 船舶约束项
        vessel_term = np.sum(
            self.dual_variables['eta'] * self.param.vessel_operation_cost
        )
        
        # 总目标
        self.dual_objective = (
            capacity_term +
            demand_term +
            time_term +
            path_term +
            vessel_term
        )
        
    def solve(self) -> Tuple[float, Dict[str, np.ndarray]]:
        """求解对偶问题
        
        Returns:
            Tuple[float, Dict[str, np.ndarray]]: 对偶目标值和变量值
        """
        # 构建变量
        try:
            self.build_variables()
        except Exception as e:
            raise RuntimeError(f"构建变量失败: {str(e)}")
        
        # 构建约束
        try:    
            self.build_constraints()
        except Exception as e:
            raise RuntimeError(f"构建约束失败: {str(e)}")
        
        # 构建目标函数
        try:
            self.build_objective()
        except Exception as e:
            raise RuntimeError(f"构建目标函数失败: {str(e)}")
        
        # 求解
        self.optimize()
        
        return self.dual_objective, self.dual_variables
        
    def optimize(self):
        """优化求解
        
        具体实现由子类完成
        """
        raise NotImplementedError("Subclass must implement optimize()")
        
    def calculate_dual_gap(self, primal_objective: float):
        """计算对偶间隙
        
        Args:
            primal_objective: 原问题目标值
        """
        self.dual_gap = abs(primal_objective - self.dual_objective) / abs(primal_objective)
        
    def get_dual_variables(self) -> Dict[str, np.ndarray]:
        """获取对偶变量
        
        Returns:
            Dict[str, np.ndarray]: 对偶变量字典
        """
        return self.dual_variables
        
    def get_dual_objective(self) -> float:
        """获取对偶目标值
        
        Returns:
            float: 对偶目标值
        """
        return self.dual_objective
        
    def get_dual_gap(self) -> float:
        """获取对偶间隙
        
        Returns:
            float: 对偶间隙
        """
        return self.dual_gap

    def set_scene(self, scene):
        """设置场景"""
        self.scene = scene
        
    def get_scene(self):
        """获取场景"""
        return self.scene
        
    def set_dual_decision_vars(self):
        """设置对偶决策变量"""
        logger.info("=========Setting Dual Decision Variables==========")
        
        # 创建对偶变量
        # α[i]
        self.alpha_var = [None] * len(self.param.demand)
        # β[nn']
        self.beta_var = [None] * len(self.param.traveling_arcs_set)
        # γ[p][t]
        self.gamma_var = [[None for _ in range(len(self.param.time_point_set))] 
                         for _ in range(len(self.param.port_set))]
        
        # 创建α变量
        for i in range(len(self.param.demand)):
            var_name = f"alpha({i})"
            self.alpha_var[i] = self.cplex.continuous_var(
                lb=float('-inf'),
                ub=self.param.penalty_cost_for_demand[i],
                name=var_name
            )
            
        # 创建β变量
        for nn in range(len(self.param.traveling_arcs_set)):
            var_name = f"beta({nn})"
            self.beta_var[nn] = self.cplex.continuous_var(
                lb=float('-inf'),
                ub=0,
                name=var_name
            )
            
        # 创建γ变量
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                var_name = f"gamma({pp})({t})"
                self.gamma_var[pp][t] = self.cplex.continuous_var(
                    lb=0,
                    ub=float('inf'),
                    name=var_name
                )
                
        logger.info("=========Dual Decision Variables Set==========")
        
    def get_obj_expr(self, v_value: List[List[int]], u_value: List[float]) -> LinearExpr:
        """获取目标函数表达式
        
        Args:
            v_value: 船舶分配决策变量值
            u_value: 需求变化系数
            
        Returns:
            目标函数表达式
        """
        obj_expr = self.get_determine_obj(v_value)
        
        # 添加需求变化项
        for i in range(len(self.param.demand)):
            obj_expr.add_term(
                coeff=self.param.maximum_demand_variation[i] * u_value[i],
                dvar=self.alpha_var[i]
            )
            
        return obj_expr
        
    def get_determine_obj(self, v_var_value: List[List[int]]) -> LinearExpr:
        """获取确定性目标函数表达式
        
        Args:
            v_var_value: 船舶分配决策变量值
            
        Returns:
            确定性目标函数表达式
        """
        obj_expr = self.cplex.linear_expr()
        
        # I. 第一部分：正常需求项
        for i in range(len(self.param.demand)):
            obj_expr.add_term(
                coeff=self.param.demand[i],
                dvar=self.alpha_var[i]
            )
            
        # II. 第二部分：船舶容量项
        capacitys = self.get_capacity_on_arcs(v_var_value)
        for n in range(len(self.param.traveling_arcs_set)):
            obj_expr.add_term(
                coeff=capacitys[n],
                dvar=self.beta_var[n]
            )
            
        # III. 第三部分：初始空箱项
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                obj_expr.add_term(
                    coeff=-self.param.initial_empty_container[pp],
                    dvar=self.gamma_var[pp][t]
                )
                
        return obj_expr
        
    def set_dual_constraint_x_with_single_thread(self):
        """设置对偶约束X（单线程原版）"""
        logger.info("=========Setting Dual Constraint X==========")
        self.c1 = {}
        for i, request in enumerate(self.input_data.requests):
            c1_k = {}
            self.c1[i] = c1_k
            for k, laden_path in enumerate(request.laden_paths):
                j = request.laden_path_indexes[k]
                laden_path = request.laden_paths[k]
                left = self.cplex.linear_expr()
                # 第一项：α[i]
                left.add_term(
                    coeff=1, 
                    dvar=self.alpha_var[i]
                )
                # 第二项：β[nn']
                for nn, arc in enumerate(self.input_data.traveling_arcs):
                    left.add_term(
                        coeff=self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id],
                        dvar=self.beta_var[nn]
                    )
                # 第三项：γ[p][t]
                for t in range(1, len(self.param.time_point_set)):
                    for pp in range(len(self.param.port_set)):
                        # p == d(i)
                        if self.param.port_set[pp] == self.param.destination_of_demand[i]:
                            for nn, arc in enumerate(self.input_data.traveling_arcs):
                                if (arc.destination_port == self.param.port_set[pp] and
                                    arc.destination_time <= t - self.param.turn_over_time[pp] and
                                    arc.destination_time >= 1):
                                    left.add_term(
                                        coeff=self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id],
                                        dvar=self.gamma_var[pp][t]
                                    )
                        # p == o(i)
                        elif self.param.port_set[pp] == self.param.origin_of_demand[i]:
                            for nn, arc in enumerate(self.input_data.traveling_arcs):
                                if (arc.origin_port == self.param.port_set[pp] and
                                    arc.origin_time <= t and
                                    arc.origin_time >= 1):
                                    left.add_term(
                                        coeff=-self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id],
                                        dvar=self.gamma_var[pp][t]
                                    )
                # 添加约束
                constr_name = f"C-X_{i}_{k}"
                self.c1[i][k] = self.cplex.add_constraint(
                    left <= laden_path.laden_path_cost,
                    constr_name
                )
        logger.info("=========Dual Constraint X Set==========")

    def set_dual_constraint_x_with_multi_threads(self):
        """设置对偶约束X（多线程优化版）"""
        import concurrent.futures
        from collections import defaultdict
        logger.info("=========Setting Dual Constraint X (Multi-Threads)==========")
        self.c1 = {}
        arc_dest_map = defaultdict(lambda: defaultdict(list))
        arc_orig_map = defaultdict(lambda: defaultdict(list))
        for nn, arc in enumerate(self.input_data.traveling_arcs):
            arc_dest_map[arc.destination_port][arc.destination_time].append(nn)
            arc_orig_map[arc.origin_port][arc.origin_time].append(nn)
        args_list = []
        for i, request in enumerate(self.input_data.requests):
            request = self.input_data.requests[i]
            c1_k = {}
            self.c1[i] = c1_k
            for k in range(request.number_of_laden_path):
                args_list.append((i, k))
        def process_dual_constraint_x(args):
            try:
                i, k = args
                request = self.input_data.requests[i]
                laden_path = request.laden_paths[k]
                left = self.cplex.linear_expr()
                left.add_term(
                    coeff=1, 
                    dvar=self.alpha_var[i]
                )
                for nn, arc in enumerate(self.input_data.traveling_arcs):
                    left.add_term(
                        coeff=self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id], 
                        dvar=self.beta_var[nn]
                    )
                for t in range(1, len(self.param.time_point_set)):
                    # p == d(i)
                    pp = self.param.port_set.index(self.param.destination_of_demand[i])
                    t_d = t - self.param.turn_over_time[pp]
                    if t_d >= 1:
                        for nn in arc_dest_map[self.param.port_set[pp]][t_d]:
                            if 1 <= self.input_data.traveling_arcs[nn].destination_time <= t_d:
                                left.add_term(
                                    coeff=self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id], 
                                    dvar=self.gamma_var[pp][t]
                                )
                    # p == o(i)
                    pp = self.param.port_set.index(self.param.origin_of_demand[i])
                    for nn in arc_orig_map[self.param.port_set[pp]][t]:
                        if 1 <= self.input_data.traveling_arcs[nn].origin_time <= t:
                            left.add_term(
                                coeff=-self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id], 
                                dvar=self.gamma_var[pp][t]
                            )
                constr_name = f"C-X_{i}_{k}"
                return (i, k, self.cplex.add_constraint(left <= laden_path.laden_path_cost, constr_name))
            except Exception as e:
                logger.error(f"设置对偶约束X失败: {str(e)} {i} {k}")
                return (i, k, None)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_dual_constraint_x, args_list))
        for i, k, constraint in results:
            self.c1[i][k] = constraint
        logger.info("=========Dual Constraint X Set (Multi-Threads)==========")

    def set_dual_constraint_x(self):
        """设置对偶约束X
        
       数学模型:
        α_i + Σ_n β_n a_{nj} + Σ_{p,t} γ_{pt} φ_{i,k,p,t} ≤ c_{i,k}, ∀i, k
        其中:
            α_i: 需求约束对偶变量
            β_n: 容量约束对偶变量
            γ_{pt}: 空箱流对偶变量
            a_{nj}: 弧n与路径j的关系
            φ_{i,k,p,t}: 路径与港口、时间的关系
            c_{i,k}: 路径运输成本
        对应Java注释:
        /*
        dual constraint X
        α + β + γ ≤ c
        */
        /**
        * 设置对偶约束X
        * α_i + Σ_n β_n a_{nj} + Σ_{p,t} γ_{pt} φ_{i,k,p,t} ≤ c_{i,k}, ∀i, k
        * 其中:
        * α_i: 需求约束对偶变量
        * β_n: 容量约束对偶变量
        * γ_{pt}: 空箱流对偶变量
        */
        """
        if DefaultSetting.WHETHER_USE_MULTI_THREADS:
            logger.info("=========Setting Dual Constraint X (Multi-Threads)==========")
            self.set_dual_constraint_x_with_multi_threads()
            logger.info("=========Dual Constraint X Set (Multi-Threads)==========")
        else:
            logger.info("=========Setting Dual Constraint X==========")
            self.set_dual_constraint_x_with_single_thread()
            logger.info("=========Dual Constraint X Set==========")
        
    def set_dual_constraint_y(self):
        """设置对偶约束Y
        
        数学模型:
        α_i + Σ_n β_n a_{nj} ≤ r_{i,k} t_{i,k} + c_{i,k}, ∀i, k
        其中:
            α_i: 需求约束对偶变量
            β_n: 容量约束对偶变量
            a_{nj}: 弧n与路径j的关系
            r_{i,k}: 租赁成本
            t_{i,k}: 路径运输时间
            c_{i,k}: 路径运输成本
        对应Java注释:
        /*
        dual constraint Y
        α + β ≤ r t + c
        */
        /**
        * 设置对偶约束Y
        * α_i + Σ_n β_n a_{nj} ≤ r_{i,k} t_{i,k} + c_{i,k}, ∀i, k
        * 其中:
        * α_i: 需求约束对偶变量
        * β_n: 容量约束对偶变量
        */
        """
        logger.info("=========Setting Dual Constraint Y==========")
        self.c2 = {}
        
        for i in tqdm(range(len(self.param.demand)), desc="设置对偶约束Y", ncols=80):
            request = self.input_data.requests[i]
            c2_k = {}
            self.c2[i] = c2_k
            
            for k, laden_path in enumerate(request.laden_paths):
                laden_path = request.laden_paths[k]
                j = laden_path.laden_path_id
                left = self.cplex.linear_expr()
                
                # 第一项：α[i]
                left.add_term(
                    coeff=1, 
                    dvar=self.alpha_var[i]
                )
                
                # 第二项：β[nn']
                for nn, arc in enumerate(self.input_data.traveling_arcs):
                    left.add_term(
                        coeff=self.param.arc_and_path[arc.traveling_arc_id][laden_path.laden_path_id],
                        dvar=self.beta_var[nn]
                    )
                    
                # 添加约束
                constr_name = f"C-Y_{i}_{k}"
                self.c2[i][k] = self.cplex.add_constraint(
                    left <= self.param.rental_cost * laden_path.travel_time + 
                           laden_path.laden_path_cost,
                    constr_name
                )
                
        logger.info("=========Dual Constraint Y Set==========")
        
    def set_dual_constraint_z_with_single_thread(self):
        """使用单线程设置对偶约束Z"""
        self.c3 = {}
        for i in tqdm(range(len(self.param.demand)), desc="设置对偶约束Z", ncols=80):
            request = self.input_data.requests[i]
            c3_k = {}
            self.c3[i] = c3_k
            for k in range(request.number_of_empty_path):
                empty_path = request.empty_paths[k]
                j = empty_path.empty_path_id
                left = self.cplex.linear_expr()
                for nn, arc in enumerate(self.input_data.traveling_arcs):
                    arc_id = self.param.traveling_arcs_set[nn]
                    arc = self.input_data.traveling_arc_set[arc_id]
                    left.add_term(
                        coeff=self.param.arc_and_path[arc.traveling_arc_id][empty_path.empty_path_id],
                        dvar=self.beta_var[nn]
                    )
                    for t in range(1, len(self.param.time_point_set)):
                        for pp in range(len(self.param.port_set)):
                            # p == o(i)
                            if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                                if (arc.destination_port.port == self.param.port_set[pp] and
                                    arc.destination_time <= t and
                                    arc.destination_time >= 1):
                                    left.add_term(
                                        coeff=self.param.arc_and_path[arc.traveling_arc_id][empty_path.empty_path_id],
                                        dvar=self.gamma_var[pp][t]
                                    )
                            # p 
                            if (arc.origin_port.port == self.param.port_set[pp] and
                                arc.origin_time <= t and
                                arc.origin_time >= 1):
                                left.add_term(
                                    coeff=-self.param.arc_and_path[arc.traveling_arc_id][empty_path.empty_path_id],
                                    dvar=self.gamma_var[pp][t]
                                )
                constr_name = f"C-Z_{i}_{k}"
                self.c3[i][k] = self.cplex.add_constraint(
                    left <= empty_path.empty_path_cost,
                    constr_name
                )

    def set_dual_constraint_z_with_multi_threads(self):
        """使用多线程设置对偶约束Z（以(i,k)为单位并行+预处理映射）"""
        import concurrent.futures
        from collections import defaultdict
        self.c3 = {}
        args_list = []
        # 预处理 destination_port, origin_port 到弧的映射
        dest_port_to_arcs = defaultdict(list)
        orig_port_to_arcs = defaultdict(list)
        for nn, arc_id in enumerate(self.param.traveling_arcs_set):
            arc = self.input_data.traveling_arc_set[arc_id]
            dest_port_to_arcs[arc.destination_port.port].append((nn, arc))
            orig_port_to_arcs[arc.origin_port.port].append((nn, arc))
        for i in range(len(self.param.demand)):
            request = self.input_data.requests[i]
            c3_k = {}
            self.c3[i] = c3_k
            for k in range(request.number_of_empty_path):
                args_list.append((i, k, request))
        def process_z(args):
            i, k, request = args
            j = request.empty_path_indexes[k]
            empty_path = request.empty_paths[k]
            left = self.cplex.linear_expr()
            # β项
            for nn, arc in enumerate(self.input_data.traveling_arcs):
                left.add_term(
                    coeff=self.param.arc_and_path[arc.traveling_arc_id][empty_path.empty_path_id], 
                    dvar=self.beta_var[nn]
                )
            # γ项
            for pp in range(len(self.param.port_set)):
                port = self.param.port_set[pp]
                # p == o(i)
                if port == self.param.origin_of_demand[i]:
                    for nn, arc in dest_port_to_arcs[port]:
                        for t in range(1, len(self.param.time_point_set)):
                            if arc.destination_time <= t and arc.destination_time >= 1:
                                left.add_term(
                                    coeff=self.param.arc_and_path[arc.traveling_arc_id][empty_path.empty_path_id], 
                                    dvar=self.gamma_var[pp][t]
                                )
                # p
                for nn, arc in orig_port_to_arcs[port]:
                    for t in range(1, len(self.param.time_point_set)):
                        if arc.origin_time <= t and arc.origin_time >= 1:
                            left.add_term(
                                coeff=-self.param.arc_and_path[arc.traveling_arc_id][empty_path.empty_path_id], 
                                dvar=self.gamma_var[pp][t]
                            )
            constr_name = f"C-Z_{i}_{k}"
            return (i, k, self.cplex.add_constraint(left <= empty_path.empty_path_cost, constr_name))
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_z, args_list))
        for i, k, constraint in results:
            self.c3[i][k] = constraint

    def set_dual_constraint_z(self):
        """设置对偶约束Z
        
        数学模型:
        Σ_n β_n a_{nj} + Σ_{p,t} γ_{pt} ψ_{i,k,p,t} ≤ e_{i,k}, ∀i, k
        其中:
            β_n: 容量约束对偶变量
            γ_{pt}: 空箱流对偶变量
            a_{nj}: 弧n与路径j的关系
            ψ_{i,k,p,t}: 路径与港口、时间的关系
            e_{i,k}: 空箱运输成本
        对应Java注释:
        /*
        dual constraint Z
        β + γ ≤ e
        */
        /**
        * 设置对偶约束Z
        * Σ_n β_n a_{nj} + Σ_{p,t} γ_{pt} ψ_{i,k,p,t} ≤ e_{i,k}, ∀i, k
        * 其中:
        * β_n: 容量约束对偶变量
        * γ_{pt}: 空箱流对偶变量
        */
        """
        if DefaultSetting.WHETHER_USE_MULTI_THREADS:
            logger.info("=========Setting Dual Constraint Z (Multi-Threads)==========")
            self.set_dual_constraint_z_with_multi_threads()
            logger.info("=========Dual Constraint Z Set (Multi-Threads)==========")
        else:
            logger.info("=========Setting Dual Constraint Z==========")
            self.set_dual_constraint_z_with_single_thread()
            logger.info("=========Dual Constraint Z Set==========")
        
    def set_dual_constraint_g(self):
        """设置对偶约束G
        
        数学模型:
        α_i ≤ p_i, ∀i
        其中:
            α_i: 需求约束对偶变量
            p_i: 需求点i的惩罚成本
        对应Java注释:
        /*
        dual constraint G
        α ≤ penalty
        */
        /**
        * 设置对偶约束G
        * α_i ≤ p_i, ∀i
        * 其中:
        * α_i: 需求约束对偶变量
        * p_i: 需求点i的惩罚成本
        */
        """
        logger.info("=========Setting Dual Constraint G==========")
        self.c4 = {}
        
        for i, request in enumerate(self.input_data.requests):
            constr_name = f"C-G_{i}"
            self.c4[i] = self.cplex.add_constraint(
                self.alpha_var[i] <= request.penalty_cost,
                constr_name
            )
            
        logger.info("=========Dual Constraint G Set==========")
        
    def change_objective_v_vars_coefficients(self, v_value):
        """更改目标函数中船舶变量的系数
        
        Args:
            v_value: 船舶分配决策变量值
        """
        # # 获取船舶容量
        # capacitys = self.get_capacity_on_arcs(v_value)
        
        # # 更新目标函数系数
        # for n in range(len(self.param.traveling_arcs_set)):
        #     self.objective.set_linear_coef(
        #         self.beta_var[n],
        #         capacitys[n]
        #     )

        self.v_var_value = v_value
        self.set_objectives()
            
    def change_objective_u_vars_coefficients(self, u_value):
        """更改目标函数中需求变量的系数
        
        Args:
            u_value: 需求变化系数
        """
        for i in range(len(self.param.demand)):
            self.cplex.set_linear_coef(
                self.alpha_var[i],
                self.param.demand[i] + self.param.maximum_demand_variation[i] * u_value[i]
            )
            
    def change_objective_coefficients(self, v_value: List[List[int]], u_value: List[float]):
        """更改目标函数系数
        
        Args:
            v_value: 船舶分配决策变量值
            u_value: 需求变化系数
        """
        self.change_objective_u_vars_coefficients(u_value)
        self.change_objective_v_vars_coefficients(v_value)
        
    def get_constant_item(self) -> float:
        """获取常数项
        
        Returns:
            常数项值
        """
        constant_item = 0
        
        try:
            # 第一部分：正常需求项
            for i in range(len(self.param.demand)):
                constant_item += (
                    (self.param.demand[i] + self.param.maximum_demand_variation[i] * self.u_value[i]) *
                    self.cplex.solution.get_value(self.alpha_var[i])
                )
        except Exception as e:
            logger.error(f"Error in get_constant_item (1): {e}")
            logger.error(traceback.format_exc())
            return 0

        try:
            # 第三部分：初始空箱项
            for pp in range(len(self.param.port_set)):
                for t in range(1, len(self.param.time_point_set)):
                    constant_item += (
                        -self.param.initial_empty_container[pp] *
                        self.cplex.solution.get_value(self.gamma_var[pp][t])
                    )

        except Exception as e:
            logger.error(f"Error in get_constant_item: {e}")
            logger.error(traceback.format_exc())
            return 0
                
        return constant_item
        
    def construct_optimal_cut(self, v_vars: List[List[Any]], eta_var: Any) -> Any:
        """构造最优切割
        
        Args:
            v_vars: 船舶分配决策变量
            eta_var: 对偶变量
            
        Returns:
            最优切割约束
        """
        if not self.cplex.solution:
            logger.error("模型未求解成功，无法取变量值")
            return
        
        constant_item = self.get_constant_item()
        beta_value = self.get_beta_value()
        left = self.cplex.linear_expr()
        
        for n, arc in enumerate(self.input_data.traveling_arcs):
            if beta_value[n] == 0:
                continue
                    
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                r = vessel_path.route_id - 1
                    
                for h, vessel_type in enumerate(self.input_data.vessel_types):
                    if DefaultSetting.FLEET_TYPE == "Homo":
                        if (self.param.arc_and_vessel_path[arc.traveling_arc_id][vessel_path.id] *
                            self.param.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.id] *
                            self.param.vessel_type_and_ship_route[vessel_type.id][vessel_path.route_id] *
                            vessel_type.capacity > 0):
                            left.add_term(
                                coeff=self.param.arc_and_vessel_path[arc.traveling_arc_id][vessel_path.id] *
                                self.param.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.id] *
                                self.param.vessel_type_and_ship_route[vessel_type.id][vessel_path.route_id] *
                                vessel_type.capacity,
                                dvar=v_vars[h][r]
                            )
                    elif DefaultSetting.FLEET_TYPE == "Hetero":
                        left.add_term(
                            coeff=self.param.arc_and_vessel_path[arc.traveling_arc_id][vessel_path.id] *
                            self.param.vessel_capacity[h],
                            dvar=v_vars[h][w]
                        )
                    else:
                        logger.error("Error in Fleet type!")
                            
        left.add_term(
            coeff=-1, 
            dvar=eta_var
        )
        
        return self.cplex.add_constraint(left <= -constant_item)
            
    def get_alpha_value(self) -> List[float]:
        """获取α变量值
        
        Returns:
            α变量值列表
        """
        alpha_value = [0.0] * len(self.param.demand)
        
        if self.cplex.get_solve_status() == "optimal":
            for i in range(len(self.param.demand)):
                alpha_value[i] = self.cplex.solution.get_value(self.alpha_var[i])
                
        return alpha_value
        
    def get_beta_value(self) -> List[float]:
        """获取β变量值
        
        Returns:
            β变量值列表
        """
        beta_value = [0.0] * len(self.param.traveling_arcs_set)
        
        if self.get_solve_status_string() == "Optimal":
            for nn in range(len(self.param.traveling_arcs_set)):
                beta_value[nn] = self.cplex.solution.get_value(self.beta_var[nn])
                
        return beta_value
        
    def get_gamma_value(self) -> List[List[float]]:
        """获取γ变量值
        
        Returns:
            γ变量值二维列表
        """
        gamma_value = [[0.0 for _ in range(len(self.param.time_point_set))]
                      for _ in range(len(self.param.port_set))]
        
        for pp in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                gamma_value[pp][t] = self.cplex.solution.get_value(self.gamma_var[pp][t])
                
        return gamma_value
        
    def check_dual_constraint_x(self, alpha_value: List[float], 
                              beta_value: List[float], 
                              gamma_value: List[List[float]]) -> bool:
        """检查对偶约束X
        
        Args:
            alpha_value: α变量值
            beta_value: β变量值
            gamma_value: γ变量值
            
        Returns:
            是否满足约束
        """
        flag = True
        
        for i in range(len(self.param.demand)):
            request = self.input_data.request_set[i]
            
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                left = 0
                
                # 第一项：α[i]
                left += alpha_value[i]
                
                # 第二项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left += self.param.arc_and_path[nn][j] * beta_value[nn]
                    
                # 第三项：γ[p][t]
                for t in range(1, len(self.param.time_point_set)):
                    for pp in range(len(self.param.port_set)):
                        # p == d(i)
                        if self.param.port_set[pp] == self.param.destination_of_demand[i]:
                            for nn in range(len(self.param.traveling_arcs_set)):
                                if (self.input_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                    self.input_data.traveling_arc_set[nn].destination_time <= t - self.param.turn_over_time[pp] and
                                    self.input_data.traveling_arc_set[nn].destination_time >= 1):
                                    left += self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                    
                        # p == o(i)
                        if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                            for nn in range(len(self.param.traveling_arcs_set)):
                                if (self.input_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                                    self.input_data.traveling_arc_set[nn].origin_time <= t and
                                    self.input_data.traveling_arc_set[nn].origin_time >= 1):
                                    left += -self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                    
                constr_name = f"C-X_{i}_{k}"
                constraint_slack = self.cplex.get_slack(self.c1[i][k])
                
                if constraint_slack < 0:
                    logger.info(f"Cplex: {constr_name} is violated with {constraint_slack}")
                    
                if left > self.param.laden_path_cost[j]:
                    logger.info(f"Dual Constraint X {constr_name} is violated! {left} {self.param.laden_path_cost[j]}")
                    flag = False
                    
        return flag
        
    def check_dual_constraint_y(self, alpha_value: List[float], 
                              beta_value: List[float]) -> bool:
        """检查对偶约束Y
        
        Args:
            alpha_value: α变量值
            beta_value: β变量值
            
        Returns:
            是否满足约束
        """
        flag = True
        
        for i in range(len(self.param.demand)):
            request = self.input_data.request_set[i]
            
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                left = 0
                
                # 第一项：α[i]
                left += alpha_value[i]
                
                # 第二项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left += self.param.arc_and_path[nn][j] * beta_value[nn]
                    
                constr_name = f"C-Y_{i}_{k}"
                constraint_slack = self.cplex.get_slack(self.c2[i][k])
                
                if constraint_slack < 0:
                    logger.info(f"Cplex: {constr_name} is violated with {constraint_slack}")
                    
                if left > self.param.rental_cost * self.param.travel_time_on_path[j] + self.param.laden_path_cost[j]:
                    logger.info(f"Dual Constraint Y {constr_name} is violated! {left} {self.param.rental_cost * self.param.travel_time_on_path[j] + self.param.laden_path_cost[j]}")
                    flag = False
                    
        return flag
        
    def check_dual_constraint_z(self, beta_value: List[float], 
                              gamma_value: List[List[float]]) -> bool:
        """检查对偶约束Z
        
        Args:
            beta_value: β变量值
            gamma_value: γ变量值
            
        Returns:
            是否满足约束
        """
        flag = True
        
        for i in range(len(self.param.demand)):
            request = self.input_data.request_set[i]
            
            for k in range(request.number_of_empty_path):
                j = request.empty_path_indexes[k]
                left = 0
                
                # 第一项：β[nn']
                for nn in range(len(self.param.traveling_arcs_set)):
                    left += self.param.arc_and_path[nn][j] * beta_value[nn]
                    
                    # 第二项和第三项：γ[p][t]
                    for t in range(1, len(self.param.time_point_set)):
                        for pp in range(len(self.param.port_set)):
                            # p == o(i)
                            if self.param.port_set[pp] == self.param.origin_of_demand[i]:
                                if (self.input_data.traveling_arc_set[nn].destination_port == self.param.port_set[pp] and
                                    self.input_data.traveling_arc_set[nn].destination_time <= t and
                                    self.input_data.traveling_arc_set[nn].destination_time >= 1):
                                    left += self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                    
                            # p
                            if (self.input_data.traveling_arc_set[nn].origin_port == self.param.port_set[pp] and
                                self.input_data.traveling_arc_set[nn].origin_time <= t and
                                self.input_data.traveling_arc_set[nn].origin_time >= 1):
                                left += -self.param.arc_and_path[nn][j] * gamma_value[pp][t]
                                
                constr_name = f"C-Z_{i}_{k}"
                constraint_slack = self.cplex.get_slack(self.c3[i][k])
                
                if constraint_slack < 0:
                    logger.info(f"Cplex: {constr_name} is violated with {constraint_slack}")
                    
                if left > self.param.empty_path_cost[j]:
                    logger.info(f"Dual Constraint Z {constr_name} is violated! {left} {self.param.empty_path_cost[j]}")
                    flag = False
                    
        return flag
        
        
    def public_setting(self, model: Model):
        """设置公共参数
        
        Args:
            model: CPLEX模型
        """
        # 设置求解参数
        model.parameters.mip.tolerances.mipgap = DefaultSetting.MIP_GAP_LIMIT
        model.parameters.timelimit = DefaultSetting.MIP_TIME_LIMIT
        model.parameters.threads = DefaultSetting.MAX_THREADS
        
        # 设置输出参数
        # model.parameters.mip.display = DefaultSetting.MIPDisplay
        # model.parameters.simplex.display = DefaultSetting.SimplexDisplay
        
    def export_model(self):
        """导出模型"""
        self.cplex.export_as_lp(f"{self.model_name}.lp") 