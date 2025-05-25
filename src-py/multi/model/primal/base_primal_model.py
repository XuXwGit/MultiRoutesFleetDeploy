from docplex.mp.model import Model
from docplex.mp.linear import LinearExpr
import logging
from typing import List, Dict, Any, Optional
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.base_model import BaseModel
import numpy as np
import time
from multi.entity.request import Request
import os

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
        self.operation_cost = 0.0
        
        # 解
        self.v_var_value = None
        self.solution = None
        
        # 设置输入数据和参数
        self.input_data = input_data
        self.param = param
        
        # 创建CPLEX模型
        try:
            self.cplex = Model(name=self.model_name)
            if input_data is not None and param is not None:
                self.public_setting(self.cplex)
                self.frame()
        except Exception as e:
            logger.error(f"Error in initialization: {str(e)}")
            raise
        
    def public_setting(self, model):
        """设置CPLEX求解器的公共参数"""
        logger.info("=========Setting CPLEX Parameters==========")
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
            logger.info("=========CPLEX Parameters Set==========")
        except Exception as e:
            logger.error(f"设置CPLEX参数时发生错误: {str(e)}")
            raise
        
    def frame(self):
        """框架方法，由子类实现具体内容"""
        logger.info("=========Building Model Framework==========")
        raise NotImplementedError("Subclass must implement abstract method")
        
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
        self.set_request_decision_vars_impl(self.xs, self.gVar)
        logger.info("=========Request Decision Variables Set==========")
        
    def set_request_decision_vars_impl(self, xs: Dict[str, List[List[Any]]], g_var: List[Any]):
        """设置请求决策变量的具体实现"""
        for i in range(len(self.param.demand)):
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
            for k in range(request.number_of_laden_path):
                j = request.laden_path_indexes[k]
                if "x" in self.xs:
                    obj.add_term(coeff=self.param.laden_path_cost[j], dvar=self.xs["x"][i][k])
                if "x1" in self.xs:
                    obj.add_term(coeff=self.param.laden_path_cost[j], dvar=self.xs["x1"][i][k])
                if "y" in self.xs:
                    obj.add_term(coeff=self.param.laden_path_cost[j], dvar=self.xs["y"][i][k])
                    obj.add_term(coeff=self.param.rental_cost * self.param.travel_time_on_path[j], 
                               dvar=self.xs["y"][i][k])
                if "z1" in self.xs:
                    obj.add_term(coeff=self.param.laden_path_cost[j] * 0.5, dvar=self.xs["z1"][i][k])
                if "z2" in self.xs:
                    obj.add_term(coeff=self.param.laden_path_cost[j] * 0.5 + 15, dvar=self.xs["z2"][i][k])
                    
            # 添加空箱运输成本
            if DefaultSetting.IsEmptyReposition:
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
                expr.add_term(coeff=self.param.vessel_type_and_ship_route[h][r], dvar=self.vVar[h][r])
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
            
        for i in range(len(self.param.demand)):
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
            
    def set_capacity_constraint(self):
        """设置容量约束：运输量不能超过船舶容量"""
        self.C2 = []
        for n in range(len(self.param.traveling_arcs_set)):
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
                if DefaultSetting.IsEmptyReposition:
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
            
    def set_empty_conservation_constraint(self):
        """设置空箱守恒约束"""
        if DefaultSetting.IsEmptyReposition:
            self.set_empty_conservation_constraint_impl(self.xVar, self.zVar, 1)
        else:
            self.set_empty_conservation_constraint_impl(self.xVar, self.z1Var, 1)
            if DefaultSetting.AllowFoldableContainer:
                self.set_empty_conservation_constraint_impl(self.x1Var, self.z2Var, 0.5)
                
    def set_empty_conservation_constraint_impl(self, x_var: List[List[Any]], 
                                             z_var: List[List[Any]], 
                                             initial_port_container_coeff: float):
        """设置空箱守恒约束的具体实现
        
        Args:
            x_var: 重箱运输变量
            z_var: 空箱运输变量
            initial_port_container_coeff: 初始港口集装箱系数
        """
        self.C3 = []
        for p in range(len(self.param.port_set)):
            for t in range(1, len(self.param.time_point_set)):
                expr = self.cplex.linear_expr()
                
                # 添加初始空箱量
                expr.add_term(1, self.param.initial_empty_container[p])
                
                # 添加空箱运输量
                for i in range(len(self.param.demand)):
                    request = self.input_data.requests[i]
                    for k in range(request.number_of_empty_path):
                        j = request.empty_path_indexes[k]
                        if (self.param.port_and_path[p][j] == 1 and
                            self.param.time_and_path[t][j] == 1):
                            expr.add_term(coeff=-1, dvar=z_var[i][k])
                            
                # 添加约束
                self.cplex.add_constraint(
                    expr >= -self.param.initial_empty_container[p] * initial_port_container_coeff,
                    f"C3_{p}_{t}"
                )
    
    def solve_model(self):
        """求解模型"""
        try:
            logger.info("=========Solving Model==========")
            # 求解模型
            self.cplex.solve()
            
            # 获取求解状态
            self.solve_status = self.cplex.solution.get_status()
            
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

    def calculate_sample_mean_performance(self, v_value: List[List[int]]) -> float:
        """计算样本平均性能
        
        Args:
            v_value: 船舶分配决策变量值
            
        Returns:
            float: 样本平均性能值
        """
        filename = f"{self.model_name}-R{len(self.input_data.ship_route_set)}" \
                  f"-T{self.param.time_horizon}-{DefaultSetting.FLEET_TYPE}" \
                  f"-Tau{self.param.tau}-U{self.param.uncertain_degree}" \
                  f"-S{self.random_seed}-SampleTestResult.txt"
                  
        file_path = os.path.join(DefaultSetting.ROOT_PATH, 
                                DefaultSetting.ALGO_LOG_PATH, 
                                filename)
                                
        with open(file_path, 'w') as f:
            f.write("Sample\tOperationCost\tTotalTransCost\tLadenCost\t" \
                   "EmptyCost\tRentalCost\tPenaltyCost\tTotalCost\n")
            
        # 计算运营成本
        mp_operation_cost = self.get_operation_cost(v_value)
        
        # 初始化样本成本数组
        sample_sub_opera_costs = [0] * self.num_sample_scenes
        sample_laden_costs = [0] * self.num_sample_scenes
        sample_empty_costs = [0] * self.num_sample_scenes
        sample_rental_costs = [0] * self.num_sample_scenes
        sample_penalty_costs = [0] * self.num_sample_scenes
        
        sum_sub_opera_costs = 0
        worst_total_cost = 0
        worst_second_cost = 0
        
        # 创建子问题并求解
        sp = SubProblem(self.input_data, self.param, v_value)
        for sce in range(self.num_sample_scenes):
            sp.change_demand_constraint_coefficients(self.param.sample_scenes[sce])
            sp.solve_model()
            
            # 记录成本
            sample_sub_opera_costs[sce] = sp.get_total_cost()
            sample_laden_costs[sce] = sp.get_laden_cost()
            sample_empty_costs[sce] = sp.get_empty_cost()
            sample_rental_costs[sce] = sp.get_rental_cost()
            sample_penalty_costs[sce] = sp.get_penalty_cost()
            
            sum_sub_opera_costs += sp.get_total_cost()
            
            # 更新最差性能
            if (mp_operation_cost + sample_sub_opera_costs[sce]) > worst_total_cost:
                worst_total_cost = mp_operation_cost + sample_sub_opera_costs[sce]
                worst_second_cost = sample_sub_opera_costs[sce]
                
            # 记录进度
            self.draw_progress_bar((sce + 1) * 100 / self.num_sample_scenes)
            
            # 写入结果
            with open(file_path, 'a') as f:
                f.write(f"{sce}\t{mp_operation_cost}\t"
                       f"{sample_sub_opera_costs[sce]}\t"
                       f"{sample_laden_costs[sce]}\t"
                       f"{sample_empty_costs[sce]}\t"
                       f"{sample_rental_costs[sce]}\t"
                       f"{sample_penalty_costs[sce]}\t"
                       f"{mp_operation_cost + sample_sub_opera_costs[sce]}\n")
                       
        # 更新性能指标
        self.worst_performance = worst_total_cost
        self.worst_second_stage_cost = worst_second_cost
        self.mean_performance = mp_operation_cost + sum_sub_opera_costs / self.num_sample_scenes
        self.mean_second_stage_cost = sum_sub_opera_costs / self.num_sample_scenes
        
        return self.mean_performance
        
    def calculate_mean_performance(self) -> float:
        """计算平均性能
        
        Returns:
            float: 平均性能值
        """
        logger.info("Calculating Mean Performance ...")
        
        if self.use_history_solution:
            if self.model_name in self.input_data.history_solution_set:
                self.calculate_sample_mean_performance(
                    self.solution_to_v_value(
                        self.input_data.history_solution_set[self.model_name]
                    )
                )
        else:
            self.calculate_sample_mean_performance(self.v_var_value)
            
        logger.info(f"MeanPerformance = {self.mean_performance}")
        logger.info(f"WorstPerformance = {self.worst_performance}")
        logger.info(f"WorstSecondStageCost = {self.worst_second_stage_cost}")
        logger.info(f"MeanSecondStageCost = {self.mean_second_stage_cost}")
        logger.info(f"AlgoObjVal = {self.obj_val}")
        
        return self.mean_performance

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