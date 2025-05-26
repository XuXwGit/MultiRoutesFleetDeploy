from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import logging
from typing import List, Dict, Any, Optional
from multi.network.traveling_arc import TravelingArc
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.base_model import BaseModel
import numpy as np
import time
from multi.entity.request import Request
import os
from tqdm import tqdm
import concurrent.futures
from collections import defaultdict

# 配置根日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('base_primal_model.log')  # 文件输出
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

class BasePrimalModel(BaseModel):
    """
    原始问题基础模型类
    
    作为所有原始问题模型的基类，提供共同的功能：
    1. 模型构建
    2. 变量创建
    3. 目标函数创建
    4. 约束创建
    5. 求解
    6. 结果获取
    """

    # 决策变量
    vVars: List[List[Any]] = []
    xVars: List[List[Any]] = []
    x1Vars: List[List[Any]] = []
    yVars: List[List[Any]] = []
    zVars: List[List[Any]] = []
    z1Vars: List[List[Any]] = []
    z2Vars: List[List[Any]] = []

    
    def __init__(self, input_data: InputData = None, param: Parameter = None):
        """
        初始化基础原始模型
        
        Args:
            input_data: 输入数据
            param: 模型参数
        """
        super().__init__(input_data, param)
        
        # 基本属性
        self.model_name = "BasePrimalModel"
        self.v_var_value = None
        self.u_value = []
        self.solve_status = None
        self.solution = None
        
        # 决策变量  
        self.vVars: List[List[Any]] = []  # 船舶分配决策变量
        self.xVars: List[List[Any]] = []  # 普通箱运输量决策变量
        self.x1Vars: List[List[Any]] = []  # 折叠箱运输量决策变量
        self.yVars: List[List[Any]] = []  # 租赁箱运输量决策变量
        self.zVars: List[List[Any]] = []  # 空箱重定向决策变量
        self.z1Vars: List[List[Any]] = []  # 调度空普通箱
        self.z2Vars: List[List[Any]] = []  # 调度空折叠箱
        self.xs: Dict[str, List[List[Any]]] = {}  # 运输量决策变量字典
        self.gVars: List[Any] = []  # 需求未满足惩罚变量
        
        # 约束条件
        self.C1: Dict[str, Any] = {}  # 需求满足约束
        self.C2: Dict[str, Any] = {}  # 容量约束
        self.C3: Dict[str, Any] = {}  # 空箱守恒约束
        
        # 性能指标
        self.worst_performance = 0.0
        self.mean_performance = 0.0
        self.worst_second_stage_cost = 0.0
        self.mean_second_stage_cost = 0.0

        self.demand_rhs_vars = {}  # 用于动态调整需求约束右端项
        self.capacity_rhs_vars = {}  # 用于锁定右端项变量的等式约束

    def initialize(self):
        """初始化模型"""
        # 创建CPLEX模型
        try:
            self.cplex = Model(name=self.model_name)
            if self.input_data is not None and self.param is not None:
                self.public_setting(self.cplex)
                self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise

    def public_setting(self, model):
        """设置CPLEX求解器的公共参数"""
        logger.info("=========Setting CPLEX Parameters Start==========")
        logger.info("开始设置CPLEX参数...")
        
        try:
            # model.parameters.display = 1  # 启用结果输出
            # logger.info("已设置display参数为1")
            
            model.parameters.timelimit = DefaultSetting.MIP_TIME_LIMIT  # 设置时间限制
            logger.info(f"已设置时间限制: {DefaultSetting.MIP_TIME_LIMIT}")
            
            model.parameters.mip.tolerances.mipgap = DefaultSetting.MIP_GAP_LIMIT  # 设置MIP间隙
            logger.info(f"已设置MIP间隙: {DefaultSetting.MIP_GAP_LIMIT}")
            
            model.parameters.randomseed = DefaultSetting.RANDOM_SEED  # 设置随机种子
            logger.info(f"已设置随机种子: {DefaultSetting.RANDOM_SEED}")
            
            logger.info("CPLEX参数设置完成")
            logger.info("========= Setting CPLEX Parameters End==========")
        except Exception as e:
            logger.error(f"设置CPLEX参数时发生错误: {str(e)}")
            raise
        
    def frame(self):
        """框架方法，由子类实现具体内容"""
        logger.info("=========Building Model Framework Start==========")
        self.set_decision_vars()
        self.set_objectives()
        self.set_constraints()
        logger.info("=========Building Model Framework End==========")
        
    def set_decision_vars(self):
        """
        设置决策变量，子类需要重写此方法
        对应Java: protected void setDecisionVars() throws IloException
        """
        pass
    
    def set_constraints(self):
        """
        设置约束条件，子类需要重写此方法
        对应Java: protected void setConstraints() throws IloException
        """
        pass
    
    def set_objectives(self):
        """
        设置目标函数，子类需要重写此方法
        对应Java: protected void setObjectives() throws IloException
        """
        pass


    def set_vessel_decision_vars(self):
        """设置船舶决策变量"""
        logger.info("=========Setting Vessel Decision Variables==========")
        if DefaultSetting.FLEET_TYPE == "Homo":
            self.vVars = [[None for _ in range(len(self.param.shipping_route_set))] 
                        for _ in range(len(self.param.vessel_set))]
            self.v_var_value = [[0 for _ in range(len(self.param.shipping_route_set))] 
                              for _ in range(len(self.param.vessel_set))]
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            self.vVars = [[None for _ in range(len(self.param.vessel_path_set))] 
                        for _ in range(len(self.param.vessel_set))]
            self.v_var_value = [[0 for _ in range(len(self.param.vessel_path_set))] 
                              for _ in range(len(self.param.vessel_set))]
        else:
            logger.error("Error in Fleet type!")
            raise ValueError("Invalid fleet type")
            
        # 创建变量
        for h, vessel in enumerate(self.input_data.vessel_types):
            if DefaultSetting.FLEET_TYPE == "Homo":
                for r, route in enumerate(self.input_data.shipping_routes):
                    var_name = f"V({self.param.vessel_set[h]})({self.param.shipping_route_set[r]})"
                    self.vVars[h][r] = self.cplex.binary_var(name=var_name)
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    var_name = f"V({self.param.vessel_set[h]})({self.param.vessel_path_set[w]})"
                    self.vVars[h][w] = self.cplex.binary_var(name=var_name)
                    
        logger.info("=========Vessel Decision Variables Set==========")
        
    def set_request_decision_vars(self):
        """设置请求决策变量"""
        logger.info("=========Setting Request Decision Variables==========")
        self.xs = {}
        self.xVars = []
        self.xs["x"] = self.xVars
        
        if DefaultSetting.ALLOW_FOLDABLE_CONTAINER:
            self.x1Vars = []
            self.xs["x1"] = self.x1Vars
            
        self.yVars = []
        self.xs["y"] = self.yVars
        
        if DefaultSetting.IS_EMPTY_REPOSITION:
            self.zVars = []
            self.xs["z"] = self.zVars
        else:
            self.z1Vars = []
            self.xs["z1"] = self.z1Vars
            self.z2Vars = []
            self.xs["z2"] = self.z2Vars
            
        self.gVars = [None] * len(self.param.demand)

        logger.info("=========Setting Request Decision Variables Start==========")
        self.set_request_decision_vars_impl(self.xs, self.gVars)
        logger.info("=========Setting Request Decision Variables End==========")
        
    def set_request_decision_vars_impl(self, xs: Dict[str, List[List[Any]]], g_var: List[Any]):
        """设置请求决策变量的具体实现"""

        for i in tqdm(range(len(self.param.demand)), desc="创建二阶段决策变量", ncols=80):
            request = self.input_data.requests[i]
            
            # 创建重箱运输变量
            if "x" in xs:
                xs["x"].append([None] * request.number_of_laden_path)
            if "x1" in xs:
                xs["x1"].append([None] * request.number_of_laden_path)
            if "y" in xs:
                xs["y"].append([None] * request.number_of_laden_path)
            if "z1" in xs:
                xs["z1"].append([None] * request.number_of_laden_path)
            if "z2" in xs:
                xs["z2"].append([None] * request.number_of_laden_path)
                
            # 创建空箱运输变量
            if DefaultSetting.IS_EMPTY_REPOSITION:
                if "z" in xs:
                    xs["z"].append([None] * request.number_of_empty_path)
                
            # 创建变量
            for k in range(request.number_of_laden_path):
                if "x" in xs:
                    var_name = f"x({i+1})({request.laden_path_indexes[k]})"
                    xs["x"][i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                if "x1" in xs:
                    var_name = f"x1({i+1})({request.laden_path_indexes[k]})"
                    xs["x1"][i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                if "y" in xs:
                    var_name = f"y({i+1})({request.laden_path_indexes[k]})"
                    xs["y"][i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                if "z1" in xs:
                    var_name = f"z1({i+1})({request.laden_path_indexes[k]})"
                    xs["z1"][i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                if "z2" in xs:
                    var_name = f"z2({i+1})({request.laden_path_indexes[k]})"
                    xs["z2"][i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                    
            if DefaultSetting.IS_EMPTY_REPOSITION:
                for k in range(request.number_of_empty_path):
                    if "z" in xs:
                        var_name = f"z({i+1})({request.empty_path_indexes[k]})"
                        xs["z"][i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                    
            # 创建需求未满足惩罚变量
            var_name = f"g({i+1})"
            g_var[i] = self.cplex.continuous_var(lb=0, name=var_name)
        
    def get_vessel_operation_cost_obj(self, obj: LinearExpr) -> LinearExpr:
        """获取船舶运营成本目标函数
        
        Args:
            obj: 目标函数表达式
            
        Returns:
            添加船舶运营成本后的目标函数表达式
        """
        # 添加固定运营成本
        for h, vessel_type in enumerate(self.input_data.vessel_types):
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                # r(航线) == r
                r = self.input_data.vessel_paths[w].route_id - 1
                
                if DefaultSetting.FLEET_TYPE == "Homo":
                    # vesselTypeAndShipRoute == 1 : r(h) = r
                    obj.add_term(
                        coeff=self.param.vessel_type_and_ship_route[vessel_type.vessel_id][vessel_type.route_id] *
                        self.param.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.vessel_path_id] *
                        self.param.vessel_operation_cost[h],
                        dvar=self.vVars[h][r]
                    )
                elif DefaultSetting.FLEET_TYPE == "Hetero":
                    obj.add_term(
                        coeff=self.param.vessel_operation_cost[h],
                        dvar=self.vVars[h][w]
                    )
                    
        return obj
    
    def get_request_trans_cost_obj(self, obj: LinearExpr) -> LinearExpr:
        """获取请求运输成本目标函数
        
        Args:
            obj: 目标函数表达式
            
        Returns:
            添加请求运输成本后的目标函数表达式
        """
        for i in range(len(self.param.demand)):
            # 添加需求未满足惩罚成本
            obj.add_term(coeff=self.param.penalty_cost_for_demand[i], dvar=self.gVars[i])
            
            request = self.input_data.requests[i]
            # 添加重箱运输成本
            for k, laden_path in enumerate(request.laden_paths):
                if "x" in self.xs:
                    obj.add_term(coeff=laden_path.laden_path_cost, dvar=self.xs["x"][i][k])
                if "x1" in self.xs:
                    obj.add_term(coeff=laden_path.laden_path_cost, dvar=self.xs["x1"][i][k])
                if "y" in self.xs:
                    obj.add_term(coeff=laden_path.laden_path_cost, dvar=self.xs["y"][i][k])
                    obj.add_term(coeff=self.param.rental_cost * laden_path.travel_time_on_path, 
                               dvar=self.xs["y"][i][k])
                if "z1" in self.xs:
                    obj.add_term(coeff=laden_path.empty_path_cost, dvar=self.xs["z1"][i][k])
                if "z2" in self.xs:
                    obj.add_term(coeff=laden_path.empty_path_cost + 15, dvar=self.xs["z2"][i][k])
                    
            # 添加空箱运输成本
            if DefaultSetting.IS_EMPTY_REPOSITION:
                for k in range(request.number_of_empty_path):
                    j = request.empty_path_indexes[k]
                    obj.add_term(coeff=self.param.empty_path_cost[j], dvar=self.zVars[i][k])
                    
        return obj  
        
    def set_vessel_constraint(self):
        """设置船舶约束"""
        if DefaultSetting.FLEET_TYPE == "Homo":
            self.set_vessel_constraint_homo()
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            self.set_vessel_constraint_hetero()
        else:
            logger.error("Error in Fleet type!")
            raise ValueError("Invalid fleet type")
            
    def set_vessel_constraint_homo(self):
        """设置同质船队约束"""
        for r, route in enumerate(self.input_data.shipping_routes):
            expr = self.cplex.linear_expr()
            for h, vessel in enumerate(self.input_data.vessel_types):
                expr.add_term(
                            coeff=self.param.vessel_type_and_ship_route[vessel.vessel_id][route.route_id], 
                              dvar=self.vVars[h][r])
            self.cplex.add_constraint(expr == 1, f"C0_{r}")
            
    def set_vessel_constraint_hetero(self):
        """设置异质船队约束"""
        # 约束1：每条航线必须分配一艘船舶
        for w, vessel_path in enumerate(self.input_data.vessel_paths):
            expr = self.cplex.linear_expr()
            for h, vessel in enumerate(self.input_data.vessel_types):
                expr.add_term(coeff=1, dvar=self.vVars[h][w])
            self.cplex.add_constraint(expr == 1, f"C0_{w}")
            
        # 约束2：每艘船舶在同一时间只能分配一次
        index_to_vessel_path_id = {w: vessel_path.vessel_path_id for w, vessel_path in enumerate(self.input_data.vessel_paths)}
        for h, vessel in enumerate(self.input_data.vessel_types):
            expr = self.cplex.linear_expr()
            for r, route in enumerate(self.input_data.shipping_routes):
                n_r = self.param.num_of_round_trips[r]
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    if self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1:
                        for w2, vessel_path2 in enumerate(self.input_data.vessel_paths):
                            if w != w2 and vessel_path.route_id == vessel_path2.route_id:
                                expr.add_term(coeff=1, dvar=self.vVars[h][w2])
                        for i in range(n_r):
                            if w + i >= len(self.param.vessel_path_set):
                                break
                            if self.param.ship_route_and_vessel_path[route.route_id][index_to_vessel_path_id[w+i]] == 1:
                                expr.add_term(coeff=1, dvar=self.vVars[h][w+i])
                        break
            self.cplex.add_constraint(expr <= 1, f"C1_{h}")
            
        # 约束3：船舶循环约束
        index_to_vessel_path_id = {w: vessel_path.vessel_path_id for w, vessel_path in enumerate(self.input_data.vessel_paths)}
        for w, vessel_path in enumerate(self.input_data.vessel_paths):
            r = self.input_data.vessel_paths[w].route_id - 1
            n_r = self.param.num_of_round_trips[r]
            if w + n_r > len(self.param.vessel_path_set) - 1:
                continue
            for h, vessel in enumerate(self.input_data.vessel_types):
                if (self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and 
                    self.param.ship_route_and_vessel_path[route.route_id][index_to_vessel_path_id[w+n_r]] == 1):
                    expr = self.cplex.linear_expr()
                    expr.add_term(coeff=1, dvar=self.vVars[h][w])
                    expr.add_term(coeff=-1, dvar=self.vVars[h][w+n_r])
                    self.cplex.add_constraint(expr == 0, f"C2_{h}_{w}")
                    
    def set_capacity_constraint_with_single_thread(self):
        """设置容量约束：运输量不能超过船舶容量（单线程原版）
        
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
        self.C2 = {}
        for n in tqdm(range(len(self.param.traveling_arcs_set)), desc="设置容量约束", ncols=80):
            expr = self.cplex.linear_expr()
            # 添加所有运输量
            expr = self.accumulate_trans_on_arc(n, expr)

            # 添加船舶容量
            for h, vessel in enumerate(self.input_data.vessel_types):
                for r, route in enumerate(self.input_data.shipping_routes):
                    for w, vessel_path in enumerate(self.input_data.vessel_paths):
                        if DefaultSetting.FLEET_TYPE == "Homo":
                            if (self.param.arc_and_vessel_path[n][w] == 1 and
                                self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and
                                self.param.vessel_type_and_ship_route[h][r] == 1):
                                expr.add_term(coeff=-self.param.vessel_capacity[h], dvar=self.vVars[h][r])
                        elif DefaultSetting.FLEET_TYPE == "Hetero":
                            if (self.param.arc_and_vessel_path[n][w] == 1):
                                expr.add_term(coeff=-self.param.vessel_capacity[h], dvar=self.vVars[h][w])
            
            # 添加约束
            self.C2[f"C2_{n}"] = self.cplex.add_constraint(
                expr <= 0.0,
                f"C2_{n}"
            )


    def accumulate_trans_on_arc(self, n: TravelingArc, expr: LinearExpr):
        """累加运输量"""
        # 添加所有运输量
        for i in range(len(self.param.demand)):
                request = self.input_data.requests[i]
                # 添加重箱运输量
                for k, laden_path in enumerate(request.laden_paths):
                    if "x" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][laden_path.laden_path_id], dvar=self.xs["x"][i][k])
                    if "x1" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][laden_path.laden_path_id], dvar=self.xs["x1"][i][k])
                    if "y" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][laden_path.laden_path_id], dvar=self.xs["y"][i][k])
                    if "z1" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][laden_path.laden_path_id], dvar=self.xs["z1"][i][k])
                    if "z2" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][laden_path.laden_path_id] * 0.25, dvar=self.xs["z2"][i][k])
                # 添加空箱运输量
                if DefaultSetting.IS_EMPTY_REPOSITION:
                    for k, empty_path in enumerate(request.empty_paths):
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][empty_path.empty_path_id], dvar=self.zVars[i][k])
            
        return expr

    def set_capacity_constraint_with_multi_threads(self):
        """设置容量约束：运输量不能超过船舶容量（多线程优化版）"""
        import concurrent.futures
        self.C2 = {}
        def process_arc(n: TravelingArc):
            expr = self.cplex.linear_expr()
            # 添加所有运输量
            expr = self.accumulate_trans_on_arc(n, expr)
            
            # 添加船舶容量
            if DefaultSetting.FLEET_TYPE == "Homo":
                for h, vessel in enumerate(self.input_data.vessel_types):
                    for r, route in enumerate(self.input_data.shipping_routes):
                        for w, vessel_path in enumerate(self.input_data.vessel_paths):
                            if (self.param.arc_and_vessel_path[n.arc_id][vessel_path.vessel_path_id] == 1 and
                                self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and
                                self.param.vessel_type_and_ship_route[vessel.vessel_id][route.route_id] == 1):
                                expr.add_term(coeff=-vessel.capacity, dvar=self.vVars[h][r])
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for h, vessel in enumerate(self.input_data.vessel_types):
                    for w, vessel_path in enumerate(self.input_data.vessel_paths):
                        if (self.param.arc_and_vessel_path[n.arc_id][vessel_path.vessel_path_id] == 1):
                                expr.add_term(coeff=-vessel.capacity, dvar=self.vVars[h][w])
            # 添加约束
            return self.cplex.add_constraint(
                expr <= 0.0,
                f"C2_{n}"
            )
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_arc, self.input_data.traveling_arcs))
        for key, value in results:
            self.C2[key] = value

    def set_capacity_constraint(self):
        """设置容量约束：运输量不能超过船舶容量（默认多线程封装）"""
        if DefaultSetting.WHETHER_USE_MULTI_THREADS:
            return self.set_capacity_constraint_with_multi_threads()
        else:
            return self.set_capacity_constraint_with_single_thread()

    def set_demand_constraint(self, u_value: List[float] = None):
        """设置需求满足约束: 运输量必须满足需求（右端项用变量+上下界锁定）"""
        self.C1 = {}
        if u_value is None:
            u_value = [0] * len(self.param.demand)
        # 注意：右端项采用变量表达，避免docplex移除/重建约束导致的indices differ等内部索引错乱问题。
        # 这里用上下界锁定变量值，等价于等式约束，但不会引发移除约束的副作用。
        for i in tqdm(range(len(self.param.demand)), desc="设置需求约束", ncols=80):
            expr = self.cplex.linear_expr()
            request = self.input_data.requests[i]
            # 添加重箱运输量
            for k in range(request.number_of_laden_path):
                if "x" in self.xs:
                    expr.add_term(coeff=1, dvar=self.xs["x"][i][k])
                if "x1" in self.xs:
                    expr.add_term(coeff=1, dvar=self.xs["x1"][i][k])
                if "y" in self.xs:
                    expr.add_term(coeff=1, dvar=self.xs["y"][i][k])
            # 添加需求未满足量
            expr.add_term(coeff=1, dvar=self.gVars[i])

            # 创建右端项变量（用于动态调整需求约束右端项）
            rhs_val = self.param.demand[i] + self.param.maximum_demand_variation[i] * u_value[i]
            self.demand_rhs_vars[i] = self.cplex.continuous_var(lb=rhs_val, ub=rhs_val, name=f"rhs_{i}")
            # 添加约束，右端项用变量表达
            self.C1[f"C1_{i}"] = self.cplex.add_constraint(expr == self.demand_rhs_vars[i], f"C1_{i}")

    def change_demand_constraint_coefficients(self, u_value):
        """动态调整需求约束右端项（通过调整变量上下界锁定新值）"""
        self.u_value = u_value
        for i in range(len(self.param.demand)):
            new_rhs = self.param.demand[i] + self.param.maximum_demand_variation[i] * u_value[i]
            self.demand_rhs_vars[i].lb = new_rhs
            self.demand_rhs_vars[i].ub = new_rhs

    def set_empty_conservation_constraint(self):
        """设置空箱守恒约束"""
        if DefaultSetting.IS_EMPTY_REPOSITION:
            self.set_empty_conservation_constraint_impl(self.xVars, self.zVars, 1)
        else:
            self.set_empty_conservation_constraint_impl(self.xVars, self.z1Vars, 1)
            if DefaultSetting.ALLOW_FOLDABLE_CONTAINER:
                self.set_empty_conservation_constraint_impl(self.x1Vars, self.z2Vars, 0.5)
                
    def set_empty_conservation_constraint_impl_with_single_thread(self, x_var: List[List[Any]], 
                                             z_var: List[List[Any]], 
                                             initial_port_container_coeff: float):
        """设置空箱守恒约束的具体实现（单线程原版）
        
        数学模型:
        初始空箱量 + Σ_输入流 - Σ_输出流 = 0, ∀p ∈ P, t ∈ T
        其中:
            p: 港口
            t: 时间点
            输入流/输出流: 各类集装箱的流入/流出
        对应Java注释:
        /*
        empty container conservation constraint
        inflow - outflow = initial
        */
        /**
        * 设置空箱守恒约束
        * 初始空箱量 + Σ_输入流 - Σ_输出流 = 0, ∀p ∈ P, t ∈ T
        */
        """
        self.C3 = {}
        for p in range(len(self.param.port_set)):
            port = self.param.port_set[p]
            left = self.cplex.linear_expr()
            for t in range(1, len(self.param.time_point_set)):
                for i in range(len(self.param.demand)):
                    request = self.input_data.requests[i]
                    # Input Z flow
                    if DefaultSetting.IS_EMPTY_REPOSITION:
                        if request.origin_port == port:
                            for k in range(request.number_of_empty_path):
                                j = request.empty_path_indexes[k]
                                for nn in range(len(self.param.traveling_arcs_set)):
                                    arc = self.input_data.traveling_arc_set[nn]
                                    if arc.destination_port == port and arc.destination_time == t:
                                        left.add_term(self.param.arc_and_path[nn][j], z_var[i][k])
                    # Input X flow
                    if request.destination_port == port:
                        for k in range(request.number_of_laden_path):
                            j = request.laden_path_indexes[k]
                            for nn in range(len(self.param.traveling_arcs_set)):
                                arc_id = self.param.traveling_arcs_set[nn]
                                arc = self.input_data.traveling_arc_set[arc_id]
                                if arc.destination_port == port and arc.destination_time == t - DefaultSetting.DEFAULT_TURN_OVER_TIME:
                                    left.add_term(self.param.arc_and_path[nn][j], x_var[i][k])
                                    if DefaultSetting.ALLOW_FOLDABLE_CONTAINER and not DefaultSetting.IS_EMPTY_REPOSITION:
                                        left.add_term(self.param.arc_and_path[nn][j], z_var[i][k])
                    # Output X flow
                    if request.origin_port == port:
                        for k in range(request.number_of_laden_path):
                            j = request.laden_path_indexes[k]
                            for nn in range(len(self.param.traveling_arcs_set)):
                                arc_id = self.param.traveling_arcs_set[nn]
                                arc = self.input_data.traveling_arc_set[arc_id]
                                if arc.origin_port == port and arc.origin_time == t:
                                    left.add_term(-self.param.arc_and_path[nn][j], x_var[i][k])
                                    if DefaultSetting.ALLOW_FOLDABLE_CONTAINER and not DefaultSetting.IS_EMPTY_REPOSITION:
                                        left.add_term(-self.param.arc_and_path[nn][j], z_var[i][k])
                    # Output Z flow
                    if DefaultSetting.IS_EMPTY_REPOSITION:
                        for k in range(request.number_of_empty_path):
                            j = request.empty_path_indexes[k]
                            for nn in range(len(self.param.traveling_arcs_set)):
                                arc_id = self.param.traveling_arcs_set[nn]
                                arc = self.input_data.traveling_arc_set[arc_id]
                                if arc.origin_port == port and arc.origin_time == t:
                                    left.add_term(-self.param.arc_and_path[nn][j], z_var[i][k])
            initial_port_containers = self.param.initial_empty_container[p] * initial_port_container_coeff
            self.C3[f"C3_{p}"] = self.cplex.add_constraint(left >= -initial_port_containers, f"C3_{p}")

    def set_empty_conservation_constraint_impl_with_multi_threads(self, x_var: List[List[Any]], 
                                             z_var: List[List[Any]], 
                                             initial_port_container_coeff: float):
        """设置空箱守恒约束的具体实现（多线程优化版）
        Args:
            x_var: 重箱运输变量
            z_var: 空箱运输变量
            initial_port_container_coeff: 初始港口集装箱系数
        """
        self.C3 = {}
        arc_dest_map = defaultdict(lambda: defaultdict(list))  # arc_dest_map[port][time] = [arc_idx, ...]
        arc_orig_map = defaultdict(lambda: defaultdict(list))  # arc_orig_map[port][time] = [arc_idx, ...]
        for nn, arc in enumerate(self.input_data.traveling_arcs):
            arc_dest_map[arc.destination_port][arc.destination_time].append(nn)
            arc_orig_map[arc.origin_port][arc.origin_time].append(nn)
        origin_port_to_requests = defaultdict(list)
        dest_port_to_requests = defaultdict(list)
        for i, req in enumerate(self.input_data.requests):
            origin_port_to_requests[req.origin_port].append(i)
            dest_port_to_requests[req.destination_port].append(i)
        def process_port(p):
            port = self.param.port_set[p]
            left = self.cplex.linear_expr()
            for t in range(1, len(self.param.time_point_set)):
                # Input Z flow
                if DefaultSetting.IS_EMPTY_REPOSITION:
                    for i in origin_port_to_requests[port]:
                        request = self.input_data.requests[i]
                        for k in range(request.number_of_empty_path):
                            j = request.empty_path_indexes[k]
                            for nn in arc_dest_map[port][t]:
                                left.add_term(self.param.arc_and_path[nn][j], z_var[i][k])
                # Input X flow
                for i in dest_port_to_requests[port]:
                    request = self.input_data.requests[i]
                    for k in range(request.number_of_laden_path):
                        j = request.laden_path_indexes[k]
                        t_x = t - DefaultSetting.DEFAULT_TURN_OVER_TIME
                        if t_x in arc_dest_map[port]:
                            for nn in arc_dest_map[port][t_x]:
                                left.add_term(
                                    coeff=self.param.arc_and_path[nn][j], 
                                    dvar=x_var[i][k]
                                )
                                if DefaultSetting.ALLOW_FOLDABLE_CONTAINER and not DefaultSetting.IS_EMPTY_REPOSITION:
                                    left.add_term(
                                        coeff=self.param.arc_and_path[nn][j], 
                                        dvar=z_var[i][k]
                                    )
                # Output X flow
                for i in origin_port_to_requests[port]:
                    request = self.input_data.requests[i]
                    for k in range(request.number_of_laden_path):
                        j = request.laden_path_indexes[k]
                        for nn in arc_orig_map[port][t]:
                            left.add_term(
                                coeff=-self.param.arc_and_path[nn][j], 
                                dvar=x_var[i][k]
                            )
                            if DefaultSetting.ALLOW_FOLDABLE_CONTAINER and not DefaultSetting.IS_EMPTY_REPOSITION:
                                left.add_term(
                                    coeff=-self.param.arc_and_path[nn][j], 
                                    dvar=z_var[i][k]
                                )
                # Output Z flow
                if DefaultSetting.IS_EMPTY_REPOSITION:
                    for i in origin_port_to_requests[port]:
                        request = self.input_data.requests[i]
                        for k in range(request.number_of_empty_path):
                            j = request.empty_path_indexes[k]
                            for nn in arc_orig_map[port][t]:
                                left.add_term(
                                    coeff=-self.param.arc_and_path[nn][j], 
                                    dvar=z_var[i][k]
                                )
            initial_port_containers = self.param.initial_empty_container[p] * initial_port_container_coeff
            return self.cplex.add_constraint(left >= -initial_port_containers, f"C3_{p}")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_port, range(len(self.param.port_set))))
        for p, constraint in enumerate(results):
            self.C3[f"C3_{p}"] = constraint

    def set_empty_conservation_constraint_impl(self, x_var: List[List[Any]], 
                                             z_var: List[List[Any]], 
                                             initial_port_container_coeff: float):
        """设置空箱守恒约束的具体实现（默认多线程封装）
        Args:
            x_var: 重箱运输变量
            z_var: 空箱运输变量
            initial_port_container_coeff: 初始港口集装箱系数
        """
        return self.set_empty_conservation_constraint_impl_with_multi_threads(x_var, z_var, initial_port_container_coeff)
    
    def solve_model(self):
        """求解模型"""
        try:
            logger.info("=========Solving Model==========")
            # 求解模型
            self.cplex.solve()
            
            # 获取求解状态
            self.solve_status = self.cplex.get_solve_status()
            
            # 如果求解成功,获取结果
            if self.solve_status == "optimal":
                # 获取目标函数值
                self.obj_val = self.cplex.solution.get_objective_value()
                
                # 获取求解时间
                self.solve_time = self.cplex.solution.get_solve_time()
                
                logger.info(f"Model solved successfully. Objective value: {self.obj_val}")
                logger.info(f"Solving time: {self.solve_time:.2f} seconds")
            else:
                logger.warning(f"Model not solved to optimality. Status: {self.solve_status}")
            logger.info("=========Model Solving Completed==========")
                
        except Exception as e:
            logger.error(f"Error in solving model: {str(e)}")
            raise
    
    def get_solution(self) -> Dict[str, Any]:
        """获取求解结果
        
        Returns:
            Dict[str, Any]: 包含求解结果的字典
        """
        if self.solve_status != "optimal":
            logger.warning("Model not solved to optimality, cannot get solution")
            return {}
            
        return {
            "objective_value": self.obj_val,
            "solve_time": self.solve_time,
            "solve_status": self.solve_status
        } 

    def set_v_var_solution(self):
        """
        根据船队类型自动提取CPLEX解，赋值给v_var_value和solution
        对应Java: protected void setVVarsSolution()
        """
        if DefaultSetting.FLEET_TYPE == 'Homo':
            self.set_homo_vessel_solution()
        elif DefaultSetting.FLEET_TYPE == 'Hetero':
            self.set_hetero_vessel_solution()
        else:
            logger.error("Error in Fleet type!")

    def set_homo_vessel_solution(self):
        """
        提取同质船队的vVar解
        对应Java: private void setHomoVesselSolution()
        """
        m = len(self.vVars)
        n = len(self.vVars[0])
        vvv = [[0 for _ in range(n)] for _ in range(m)]
        solution = [0 for _ in range(n)]
        for r in range(n):
            for h in range(m):
                try:
                    val = self.cplex.solution.get_value(self.vVars[h][r])
                except Exception:
                    val = 0
                if val >= 0.99:  # 容差
                    vvv[h][r] = 1
                    solution[r] = h + 1
        self.set_v_var_value(vvv)
        self.set_solution(solution)

    def set_hetero_vessel_solution(self):
        """
        提取异质船队的vVar解
        对应Java: private void setHeteroVesselSolution()
        """
        m = len(self.vVars)
        n = len(self.vVars[0])
        vvv = [[0 for _ in range(n)] for _ in range(m)]
        solution = [0 for _ in range(n)]
        for w in range(n):
            for h in range(m):
                try:
                    val = self.cplex.solution.get_value(self.vVars[h][w])
                except Exception:
                    val = 0
                if val >= 0.99:
                    vvv[h][w] = 1
                    solution[w] = h + 1
        self.set_v_var_value(vvv)
        self.set_solution(solution)

    def solution_to_v_value(self, solution: List[int]) -> List[List[int]]:
        """
        将解决方案转换为船舶分配决策变量值
        对应Java: public int[][] solutionToVValue(int[] solution)
        """
        v_value = []
        if DefaultSetting.FLEET_TYPE == "Homo":
            v_value = [[0 for _ in range(len(self.param.shipping_route_set))] 
                      for _ in range(len(self.param.vessel_set))]
            for r, route in enumerate(self.input_data.shipping_routes):
                v_value[solution[r] - 1][r] = 1
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            v_value = [[0 for _ in range(len(self.param.vessel_path_set))] 
                      for _ in range(len(self.param.vessel_set))]
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                v_value[solution[w] - 1][w] = 1
        else:
            logger.error("Error in Fleet type!")
        return v_value
        
    def print_solution(self):
        """打印解决方案"""
        logger.info(f"Objective = {self.obj_val:.2f}")
        print(f"Objective = {self.obj_val:.2f}")
        print("VesselType Decision vVar : ", end="")
        
        for r, route in enumerate(self.input_data.shipping_routes):
            print(f"{self.param.shipping_route_set[r]}:", end="")
            
            if DefaultSetting.FLEET_TYPE == "Homo":
                for h, vessel in enumerate(self.input_data.vessel_types):
                    if self.v_var_value[h][r] != 0:
                        print(f"{self.param.vessel_set[h]}\t", end="")
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for w, vessel_path in enumerate(self.input_data.vessel_paths):
                    if self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] != 1:
                        continue
                    for h, vessel in enumerate(self.input_data.vessel_types):
                        if (self.v_var_value[h][w] != 0 and 
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1):
                            print(f"{self.param.vessel_path_set[w]}({self.param.vessel_set[h]})\t", end="")
            else:
                logger.error("Error in Fleet type!")
                
        print()

    def get_operation_cost(self, v_value: List[List[int]]) -> float:
        """获取运营成本
        
        Args:
            v_value: 船舶分配决策变量值
            
        Returns:
            float: 运营成本
        """
        operation_cost = 0
        for h, vessel in enumerate(self.input_data.vessel_types):
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                # r(航线) == r
                r = self.input_data.vessel_paths[w].route_id - 1
                
                if DefaultSetting.FLEET_TYPE == "Homo":
                    # vesselTypeAndShipRoute == 1 : r(h) = r
                    operation_cost += (self.param.vessel_type_and_ship_route[h][r] *
                                     self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] *
                                     self.param.vessel_operation_cost[h] *
                                     v_value[h][r])
                elif DefaultSetting.FLEET_TYPE == "Hetero":
                    operation_cost += (self.param.vessel_operation_cost[h] *
                                     v_value[h][w])
                    
        return operation_cost
        
    def draw_progress_bar(self, percent: float):
        """绘制进度条
        
        Args:
            percent: 进度百分比
        """
        bar_length = 50
        filled_length = int(bar_length * percent / 100)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        print(f'\r[{bar}] {percent:.1f}%', end='')
        if percent == 100:
            print() 

    def output_result(self):
        """输出求解结果"""
        logger.info("=========Outputting Results==========")
        try:
            # 输出目标函数值
            logger.info(f"目标函数值: {self.obj_val}")
            
            # 输出船舶分配结果
            logger.info("\n船舶分配结果:")
            for h, vessel in enumerate(self.input_data.vessel_types):
                if DefaultSetting.FLEET_TYPE == "Homo":
                    for r, route in enumerate(self.input_data.shipping_routes):
                        if self.v_var_value[h][r] > 0.5:
                            logger.info(f"船舶 {self.param.vessel_set[h]} 分配到航线 {self.param.shipping_route_set[r]}")
                elif DefaultSetting.FLEET_TYPE == "Hetero":
                    for w, vessel_path in enumerate(self.input_data.vessel_paths):
                        if self.v_var_value[h][w] > 0.5:
                            logger.info(f"船舶 {self.param.vessel_set[h]} 分配到路径 {self.param.vessel_path_set[w]}")
                            
            # 输出运输决策结果
            logger.info("\n运输决策结果:")
            for i in range(len(self.param.demand)):
                request = self.input_data.requests[i]
                logger.info(f"\n请求 {i+1}:")
                
                # 输出重箱运输决策
                for k in range(request.number_of_laden_path):
                    if "x" in self.xs and self.xs["x"][i][k] > 0.5:
                        logger.info(f"使用自有集装箱通过路径 {request.laden_path_indexes[k]}")
                    if "x1" in self.xs and self.xs["x1"][i][k] > 0.5:
                        logger.info(f"使用自有折叠集装箱通过路径 {request.laden_path_indexes[k]}")
                    if "y" in self.xs and self.xs["y"][i][k] > 0.5:
                        logger.info(f"使用租赁集装箱通过路径 {request.laden_path_indexes[k]}")
                    if "z1" in self.xs and self.xs["z1"][i][k] > 0.5:
                        logger.info(f"使用自有折叠集装箱通过路径 {request.laden_path_indexes[k]}")
                    if "z2" in self.xs and self.xs["z2"][i][k] > 0.5:
                        logger.info(f"使用租赁折叠集装箱通过路径 {request.laden_path_indexes[k]}")
                        
                # 输出空箱运输决策
                if DefaultSetting.IsEmptyReposition:
                    for k in range(request.number_of_empty_path):
                        if self.zVars[i][k] > 0.5:
                            logger.info(f"空箱通过路径 {request.empty_path_indexes[k]}")
                            
            logger.info("结果输出完成")
        except Exception as e:
            logger.error(f"输出结果失败: {str(e)}")
            raise
        logger.info("=========Results Outputted==========") 

    def set_operation_cost(self, value: float):
        self.operation_cost = value
        

    def set_v_var_value(self, v_var_value: List[List[int]]):
        """
        设置船舶分配决策变量值
        对应Java: public void setVVarValue(int[][] vVarValue)
        """
        self.v_var_value = v_var_value

    def get_v_var_value(self) -> List[List[int]]:
        """
        获取船舶分配决策变量值
        对应Java: public int[][] getVVarValue()
        """
        return self.v_var_value

    def set_solution(self, solution: List[int]):
        """
        设置当前解
        对应Java: protected void setSolution(int[] solution)
        """
        self.solution = solution

    def calculate_sample_mean_performance(self, v_value: List[List[int]]) -> float:
        """
        计算样本均值性能
        对应Java: protected double calculateSampleMeanPerformance(int[][] vValue)
        """
        # 这里只做结构补全，具体实现需结合样本场景与子问题模型
        logger.info("计算样本均值性能（calculate_sample_mean_performance）—— 需根据实际子类实现")
        # TODO: 结合样本场景与子问题模型实现
        return 0.0

    def calculate_mean_performance(self) -> float:
        """
        计算均值性能
        对应Java: protected double calculateMeanPerformance()
        """
        logger.info("计算均值性能（calculate_mean_performance）—— 需根据实际子类实现")
        # TODO: 结合历史解与当前解调用calculate_sample_mean_performance
        return 0.0 