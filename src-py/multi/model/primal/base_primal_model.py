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
        self.obj_val = 0  # 目标函数值
        self.solve_status = None  # 求解状态
        self.solve_time = 0  # 求解时间
        
        # 决策变量
        self.vVar: List[List[Any]] = []  # 船舶分配决策变量
        self.xVar: List[List[Any]] = []  # 普通箱运输量决策变量
        self.x1Var: List[List[Any]] = []  # 折叠箱运输量决策变量
        self.yVar: List[List[Any]] = []  # 租赁箱运输量决策变量
        self.zVar: List[List[Any]] = []  # 空箱重定向决策变量
        self.z1Var: List[List[Any]] = []  # 调度空普通箱
        self.z2Var: List[List[Any]] = []  # 调度空折叠箱
        self.xs: Dict[str, List[List[Any]]] = {}  # 运输量决策变量字典
        self.gVar: List[Any] = []  # 需求未满足惩罚变量
        
        # 约束条件
        self.C1: List[Any] = []  # 需求满足约束
        self.C2: List[Any] = []  # 容量约束
        self.C3: List[List[Any]] = []  # 流量平衡约束
        
        # 性能指标
        self.worst_performance = 0.0
        self.mean_performance = 0.0
        self.worst_second_stage_cost = 0.0
        self.mean_second_stage_cost = 0.0

        # cost
        self.operation_cost = 0.0
        self.laden_cost = 0.0
        self.empty_cost = 0.0
        self.rental_cost = 0.0
        self.penalty_cost = 0.0

        
        # 解
        self.v_var_value = None
        self.solution = None
        
        # 设置输入数据和参数
        self.input_data = input_data
        self.param = param
    
        

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
        logger.error("=========Building Model Framework End==========")
        
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
            self.vVar = [[None for _ in range(len(self.param.shipping_route_set))] 
                        for _ in range(len(self.param.vessel_set))]
            self.v_var_value = [[0 for _ in range(len(self.param.shipping_route_set))] 
                              for _ in range(len(self.param.vessel_set))]
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            self.vVar = [[None for _ in range(len(self.param.vessel_path_set))] 
                        for _ in range(len(self.param.vessel_set))]
            self.v_var_value = [[0 for _ in range(len(self.param.vessel_path_set))] 
                              for _ in range(len(self.param.vessel_set))]
        else:
            logger.error("Error in Fleet type!")
            raise ValueError("Invalid fleet type")
            
        # 创建变量
        for h in range(len(self.param.vessel_set)):
            if DefaultSetting.FLEET_TYPE == "Homo":
                for r in range(len(self.param.shipping_route_set)):
                    var_name = f"V({self.param.vessel_set[h]})({self.param.shipping_route_set[r]})"
                    self.vVar[h][r] = self.cplex.binary_var(name=var_name)
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for w in range(len(self.param.vessel_path_set)):
                    var_name = f"V({self.param.vessel_set[h]})({self.param.vessel_path_set[w]})"
                    self.vVar[h][w] = self.cplex.binary_var(name=var_name)
                    
        logger.info("=========Vessel Decision Variables Set==========")
        
    def set_request_decision_vars(self):
        """设置请求决策变量"""
        logger.info("=========Setting Request Decision Variables==========")
        self.xs = {}
        self.xVar = []
        self.xs["x"] = self.xVar
        
        if DefaultSetting.ALLOW_FOLDABLE_CONTAINER:
            self.x1Var = []
            self.xs["x1"] = self.x1Var
            
        self.yVar = []
        self.xs["y"] = self.yVar
        
        if DefaultSetting.IS_EMPTY_REPOSITION:
            self.zVar = []
        else:
            self.z1Var = []
            self.xs["z1"] = self.z1Var
            self.z2Var = []
            self.xs["z2"] = self.z2Var
            
        self.gVar = [None] * len(self.param.demand)

        logger.info("=========Setting Request Decision Variables Start==========")
        self.set_request_decision_vars_impl(self.xs, self.gVar)
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
                self.zVar.append([None] * request.number_of_empty_path)
                
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
                    var_name = f"z({i+1})({request.empty_path_indexes[k]})"
                    self.zVar[i][k] = self.cplex.continuous_var(lb=0, name=var_name)
                    
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
        for h in range(len(self.param.vessel_set)):
            for w in range(len(self.param.vessel_path_set)):
                # r(航线) == r
                r = self.input_data.vessel_paths[w].route_id - 1
                
                if DefaultSetting.FLEET_TYPE == "Homo":
                    # vesselTypeAndShipRoute == 1 : r(h) = r
                    obj.add_term(
                        coeff=self.param.vessel_type_and_ship_route[h][r] *
                        self.param.ship_route_and_vessel_path[r][w] *
                        self.param.vessel_operation_cost[h],
                        dvar=self.vVar[h][r]
                    )
                elif DefaultSetting.FLEET_TYPE == "Hetero":
                    obj.add_term(
                        coeff=self.param.vessel_operation_cost[h],
                        dvar=self.vVar[h][w]
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
            obj.add_term(coeff=self.param.penalty_cost_for_demand[i], dvar=self.gVar[i])
            
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
                    obj.add_term(coeff=self.param.empty_path_cost[j], dvar=self.zVar[i][k])
                    
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
        for r in range(len(self.param.shipping_route_set)):
            expr = self.cplex.linear_expr()
            for h in range(len(self.param.vessel_set)):
                expr.add_term(
                            coeff=self.param.vessel_type_and_ship_route[h][r], 
                              dvar=self.vVar[h][r])
            self.cplex.add_constraint(expr == 1, f"C0_{r}")
            
    def set_vessel_constraint_hetero(self):
        """设置异质船队约束"""
        # 约束1：每条航线必须分配一艘船舶
        for w in range(len(self.param.vessel_path_set)):
            expr = self.cplex.linear_expr()
            for h in range(len(self.param.vessel_set)):
                expr.add_term(coeff=1, dvar=self.vVar[h][w])
            self.cplex.add_constraint(expr == 1, f"C0_{w}")
            
        # 约束2：每艘船舶在同一时间只能分配一次
        for h in range(len(self.param.vessel_set)):
            expr = self.cplex.linear_expr()
            for r in range(len(self.param.shipping_route_set)):
                n_r = self.param.num_of_round_trips[r]
                for w in range(len(self.param.vessel_path_set)):
                    if self.param.ship_route_and_vessel_path[r][w] == 1:
                        for i in range(n_r):
                            if w + i >= len(self.param.vessel_path_set):
                                break
                            if self.param.ship_route_and_vessel_path[r][w+i] == 1:
                                expr.add_term(coeff=1, dvar=self.vVar[h][w+i])
                        break
            self.cplex.add_constraint(expr <= 1, f"C1_{h}")
            
        # 约束3：船舶循环约束
        for w in range(len(self.param.vessel_path_set)):
            r = self.input_data.vessel_paths[w].route_id - 1
            n_r = self.param.num_of_round_trips[r]
            if w + n_r > len(self.param.vessel_path_set) - 1:
                continue
            for h in range(len(self.param.vessel_set)):
                if (self.param.ship_route_and_vessel_path[r][w] == 1 and 
                    self.param.ship_route_and_vessel_path[r][w+n_r] == 1):
                    expr = self.cplex.linear_expr()
                    expr.add_term(coeff=1, dvar=self.vVar[h][w])
                    expr.add_term(coeff=-1, dvar=self.vVar[h][w+n_r])
                    self.cplex.add_constraint(expr == 0, f"C2_{h}_{w}")
                    
    def set_demand_constraint(self, u_value: List[float] = None):
        """设置需求约束
        
        Args:
            u_value: 需求变化系数
        """
        self.C1 = []
        if u_value is None:
            u_value = [0] * len(self.param.demand)
            
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
            expr.add_term(coeff=1, dvar=self.gVar[i])
            
            # 添加约束
            self.C1.append(self.cplex.add_constraint(
                expr == self.param.demand[i] + 
                self.param.maximum_demand_variation[i] * u_value[i],
                f"C1_{i}"
            ))
            
    def set_capacity_constraint_with_single_thread(self):
        """设置容量约束：运输量不能超过船舶容量（单线程原版）"""
        self.C2 = []
        for n in tqdm(range(len(self.param.traveling_arcs_set)), desc="设置容量约束", ncols=80):
            expr = self.cplex.linear_expr()
            # 添加所有运输量
            for i in range(len(self.param.demand)):
                request = self.input_data.requests[i]
                # 添加重箱运输量
                for k in range(request.number_of_laden_path):
                    j = request.laden_path_indexes[k]
                    if "x" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n][j], dvar=self.xs["x"][i][k])
                    if "x1" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n][j], dvar=self.xs["x1"][i][k])
                    if "y" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n][j], dvar=self.xs["y"][i][k])
                    if "z1" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n][j], dvar=self.xs["z1"][i][k])
                    if "z2" in self.xs:
                        expr.add_term(coeff=self.param.arc_and_path[n][j] * 0.25, dvar=self.xs["z2"][i][k])
                # 添加空箱运输量
                if DefaultSetting.IS_EMPTY_REPOSITION:
                    for k in range(request.number_of_empty_path):
                        j = request.empty_path_indexes[k]
                        expr.add_term(coeff=self.param.arc_and_path[n][j], dvar=self.zVar[i][k])
            # 添加船舶容量
            for h in range(len(self.param.vessel_set)):
                for r in range(len(self.param.shipping_route_set)):
                    for w in range(len(self.param.vessel_path_set)):
                        if (self.param.arc_and_vessel_path[n][w] == 1 and
                            self.param.ship_route_and_vessel_path[r][w] == 1 and
                            self.param.vessel_type_and_ship_route[h][r] == 1):
                            expr.add_term(coeff=-self.param.vessel_capacity[h], dvar=self.vVar[h][r])
            # 添加约束
            self.C2.append(self.cplex.add_constraint(
                expr <= 0.0,
                f"C2_{n}"
            ))

    def set_capacity_constraint_with_multi_threads(self):
        """设置容量约束：运输量不能超过船舶容量（多线程优化版）"""
        import concurrent.futures
        self.C2 = []
        def process_arc(n: TravelingArc):
            expr = self.cplex.linear_expr()
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
                        expr.add_term(coeff=self.param.arc_and_path[n.arc_id][empty_path.empty_path_id], dvar=self.zVar[i][k])
            # 添加船舶容量
            for h, vessel in enumerate(self.input_data.vessel_types):
                for r, route in enumerate(self.input_data.shipping_routes):
                    for w, vessel_path in enumerate(self.input_data.vessel_paths):
                        if (self.param.arc_and_vessel_path[n.arc_id][vessel_path.vessel_path_id] == 1 and
                            self.param.ship_route_and_vessel_path[route.route_id][vessel_path.vessel_path_id] == 1 and
                            self.param.vessel_type_and_ship_route[vessel.vessel_id][route.route_id] == 1):
                            expr.add_term(coeff=-vessel.capacity, dvar=self.vVar[h][r])
            # 添加约束
            return self.cplex.add_constraint(
                expr <= 0.0,
                f"C2_{n}"
            )
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(process_arc, self.input_data.traveling_arcs))
        self.C2.extend(results)

    def set_capacity_constraint(self):
        """设置容量约束：运输量不能超过船舶容量（默认多线程封装）"""
        return self.set_capacity_constraint_with_multi_threads()
        # return self.set_capacity_constraint_with_single_thread()

    def set_empty_conservation_constraint(self):
        """设置空箱守恒约束"""
        if DefaultSetting.IS_EMPTY_REPOSITION:
            self.set_empty_conservation_constraint_impl(self.xVar, self.zVar, 1)
        else:
            self.set_empty_conservation_constraint_impl(self.xVar, self.z1Var, 1)
            if DefaultSetting.ALLOW_FOLDABLE_CONTAINER:
                self.set_empty_conservation_constraint_impl(self.x1Var, self.z2Var, 0.5)
                
    def set_empty_conservation_constraint_impl_with_single_thread(self, x_var: List[List[Any]], 
                                             z_var: List[List[Any]], 
                                             initial_port_container_coeff: float):
        """设置空箱守恒约束的具体实现（单线程原版）
        Args:
            x_var: 重箱运输变量
            z_var: 空箱运输变量
            initial_port_container_coeff: 初始港口集装箱系数
        """
        self.C3 = []
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
            self.C3.append(self.cplex.add_constraint(left >= -initial_port_containers, f"C3_{p}"))

    def set_empty_conservation_constraint_impl_with_multi_threads(self, x_var: List[List[Any]], 
                                             z_var: List[List[Any]], 
                                             initial_port_container_coeff: float):
        """设置空箱守恒约束的具体实现（多线程优化版）
        Args:
            x_var: 重箱运输变量
            z_var: 空箱运输变量
            initial_port_container_coeff: 初始港口集装箱系数
        """
        self.C3 = []
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
        self.C3.extend(results)

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



    def solution_to_v_value(self, solution: List[int]) -> List[List[int]]:
        """将解决方案转换为船舶分配决策变量值
        
        Args:
            solution: 解决方案
            
        Returns:
            List[List[int]]: 船舶分配决策变量值
        """
        v_value = []
        if DefaultSetting.FLEET_TYPE == "Homo":
            v_value = [[0 for _ in range(len(self.param.shipping_route_set))] 
                      for _ in range(len(self.param.vessel_set))]
            for r in range(len(self.param.shipping_route_set)):
                v_value[solution[r] - 1][r] = 1
        elif DefaultSetting.FLEET_TYPE == "Hetero":
            v_value = [[0 for _ in range(len(self.param.vessel_path_set))] 
                      for _ in range(len(self.param.vessel_set))]
            for w in range(len(self.param.vessel_path_set)):
                v_value[solution[w] - 1][w] = 1
        else:
            logger.error("Error in Fleet type!")
            
        return v_value
        
    def print_solution(self):
        """打印解决方案"""
        logger.info(f"Objective = {self.obj_val:.2f}")
        print(f"Objective = {self.obj_val:.2f}")
        print("VesselType Decision vVar : ", end="")
        
        for r in range(len(self.param.shipping_route_set)):
            print(f"{self.param.shipping_route_set[r]}:", end="")
            
            if DefaultSetting.FLEET_TYPE == "Homo":
                for h in range(len(self.param.vessel_set)):
                    if self.v_var_value[h][r] != 0:
                        print(f"{self.param.vessel_set[h]}\t", end="")
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for w in range(len(self.param.vessel_path_set)):
                    if self.param.ship_route_and_vessel_path[r][w] != 1:
                        continue
                    for h in range(len(self.param.vessel_set)):
                        if (self.v_var_value[h][w] != 0 and 
                            self.param.ship_route_and_vessel_path[r][w] == 1):
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
        for h in range(len(self.param.vessel_set)):
            for w in range(len(self.param.vessel_path_set)):
                # r(航线) == r
                r = self.input_data.vessel_paths[w].route_id - 1
                
                if DefaultSetting.FLEET_TYPE == "Homo":
                    # vesselTypeAndShipRoute == 1 : r(h) = r
                    operation_cost += (self.param.vessel_type_and_ship_route[h][r] *
                                     self.param.ship_route_and_vessel_path[r][w] *
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
            for h in range(len(self.param.vessel_set)):
                if DefaultSetting.FLEET_TYPE == "Homo":
                    for r in range(len(self.param.shipping_route_set)):
                        if self.v_var_value[h][r] > 0.5:
                            logger.info(f"船舶 {self.param.vessel_set[h]} 分配到航线 {self.param.shipping_route_set[r]}")
                elif DefaultSetting.FLEET_TYPE == "Hetero":
                    for w in range(len(self.param.vessel_path_set)):
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
                        if self.zVar[i][k] > 0.5:
                            logger.info(f"空箱通过路径 {request.empty_path_indexes[k]}")
                            
            logger.info("结果输出完成")
        except Exception as e:
            logger.error(f"输出结果失败: {str(e)}")
            raise
        logger.info("=========Results Outputted==========") 