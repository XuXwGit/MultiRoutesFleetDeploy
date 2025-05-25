import logging
import time
import os
import numpy as np
from typing import List, Dict, Any, Tuple
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
import docplex.mp.model as cpx

logger = logging.getLogger(__name__)

class BaseModel:
    """
    模型基类
    
    定义所有模型共用的属性和方法
    
    主要功能:
    1. 维护模型基本参数(in/p)
    2. 管理CPLEX求解器实例
    3. 记录求解结果(obj_val/obj_gap等)
    4. 提供基础设置方法(public_setting)
    
    关键属性:
    - input_data: 输入数据(网络结构、需求等)
    - param: 模型参数(成本系数、容量等)
    - model: CPLEX求解器实例
    - v_var_value: 船舶分配决策变量值
    - u_value: 对偶变量值
    """
    
    def __init__(self, input_data: InputData, param: Parameter):
        """
        模型基类构造函数
        
        初始化模型参数并创建CPLEX求解器实例
        
        Args:
            input_data: 输入数据(网络结构、需求等)
            param: 模型参数(成本系数、容量等)
        """
        self.input_data = input_data
        self.param = param
        self.model = None
        self.model_name = None
        self.obj_val = 0.0
        self.obj_gap = 0.0
        self.operation_cost = 0.0
        self.solve_time = 0.0
        self.v_var_value = None
        self.v_var_value_double = None
        self.u_value = None
        
        # 模型变量
        self.variables = {}
        
        # 模型约束
        self.constraints = {}
        
        # 模型目标函数
        self.objective = None
        
        # 求解状态
        self.solve_status = {
            'iter': 0,
            'obj_val': 0.0,
            'gap': float('inf'),
            'time': 0.0
        }
        
        # 历史信息
        self.history = {
            'obj_val': [],
            'gap': [],
            'time': []
        }
        
        try:
            self.model = self.create_model()
            self.public_setting(self.model)
            self.frame()
        except Exception as e:
            logger.error(f"Error initializing BaseModel: {str(e)}")
            raise
    
    def create_model(self):
        """
        创建CPLEX求解器实例
        
        Returns:
            docplex.mp.model.Model: CPLEX求解器实例
        """
        try:
            model = cpx.Model(name=self.model_name if self.model_name else "BaseModel")
            return model
        except Exception as e:
            logger.error(f"Error creating CPLEX model: {str(e)}")
            raise
    
    def public_setting(self, model):
        """
        设置CPLEX求解器参数
        
        Args:
            model: CPLEX求解器实例
        """
        if DefaultSetting.WHETHER_CLOSE_OUTPUT_LOG:
            model.set_log_output(False)
        
        model.parameters.mip.tolerances.mipgap = DefaultSetting.MIP_GAP_LIMIT
        model.parameters.timelimit = DefaultSetting.MIP_TIME_LIMIT
        model.parameters.threads = DefaultSetting.MAX_THREADS
        model.parameters.workmem = DefaultSetting.MAX_WORK_MEM
    
    def frame(self):
        """构建模型框架"""
        self.set_decision_vars()
        self.set_objectives()
        self.set_constraints()
        
    def set_decision_vars(self):
        """设置决策变量
        
        具体实现由子类完成
        """
        raise NotImplementedError("Subclass must implement set_decision_vars()")
        
    def set_objectives(self):
        """设置目标函数
        
        具体实现由子类完成
        """
        raise NotImplementedError("Subclass must implement set_objectives()")
        
    def set_constraints(self):
        """设置约束条件
        
        具体实现由子类完成
        """
        raise NotImplementedError("Subclass must implement set_constraints()")
    
    def end(self):
        """
        结束CPLEX求解器
        """
        if self.model:
            self.model.end()
    
    def get_solve_status(self) -> str:
        """
        获取求解状态
        
        Returns:
            str: 求解状态
        """
        return self.model.get_solve_status()
    
    def get_solve_status_string(self) -> str:
        """
        获取求解状态字符串
        
        Returns:
            str: 求解状态字符串
        """
        status = self.get_solve_status()
        if status == "Optimal":
            return "Optimal"
        elif status == "Feasible":
            return "Feasible"
        elif status == "Infeasible":
            return "Infeasible"
        elif status == "Bounded":
            return "Bounded"
        else:
            return "Others"
    
    def get_capacity_on_arcs(self, v_value: List[List[float]]) -> List[float]:
        """
        计算每个弧上的容量
        
        Args:
            v_value: 船舶分配方案
            
        Returns:
            List[float]: 每个弧上的容量
        """
        capacities = [0.0] * len(self.param.traveling_arc_set)
        
        for n in range(len(self.param.traveling_arc_set)):
            for w in range(len(self.param.vessel_path_set)):
                r = self.input_data.vessel_path_set[w].route_id - 1
                
                for h in range(len(self.param.vessel_set)):
                    if DefaultSetting.FLEET_TYPE == "Homo":
                        capacities[n] += (self.param.arc_and_vessel_path[n][w] *
                                       self.param.ship_route_and_vessel_path[r][w] *
                                       self.param.vessel_type_and_ship_route[h][r] *
                                       self.param.vessel_capacity[h] *
                                       v_value[h][r])
                    elif DefaultSetting.FLEET_TYPE == "Hetero":
                        capacities[n] += (self.param.arc_and_vessel_path[n][w] *
                                       self.param.vessel_capacity[h] *
                                       v_value[h][w])
                    else:
                        logger.error("Error in Fleet type!")
                        raise ValueError("Invalid fleet type")
        
        return capacities
    
    def get_capacity_on_arcs(self, v_value: List[List[int]]) -> List[float]:
        """
        计算每个弧上的容量
        
        Args:
            v_value: 船舶分配方案
            
        Returns:
            List[float]: 每个弧上的容量
        """
        v_value_double = [[float(v) for v in row] for row in v_value]
        return self.get_capacity_on_arcs(v_value_double)
    
    def export_model(self):
        """
        导出模型到LP文件
        """
        model_file_path = os.path.join(DefaultSetting.ROOT_PATH, 
                                     DefaultSetting.export_model_path)
        
        try:
            # 创建目录（如果不存在）
            os.makedirs(model_file_path, exist_ok=True)
            
            # 导出模型
            filename = f"{self.model_name}.lp"
            self.model.write(os.path.join(model_file_path, filename))
            
        except Exception as e:
            logger.error(f"Error exporting model: {str(e)}")
            raise

    def build_variables(self):
        """构建变量"""
        raise NotImplementedError("Subclasses must implement build_variables()")
        
    def build_constraints(self):
        """构建约束"""
        raise NotImplementedError("Subclasses must implement build_constraints()")
        
    def build_objective(self):
        """构建目标函数"""
        raise NotImplementedError("Subclasses must implement build_objective()")
        
    def solve(self) -> Tuple[float, Dict[str, Any]]:
        """求解模型
        
        Returns:
            Tuple[float, Dict[str, Any]]: 目标函数值和求解状态
        """
        try:
            # 构建问题
            self.build_variables()
            self.build_constraints()
            self.build_objective()
            
            # 求解问题
            self.optimize()
            
            return self.objective, self.solve_status
            
        except Exception as e:
            logger.error(f"Error in solving model: {str(e)}")
            raise
            
    def optimize(self):
        """优化求解"""
        raise NotImplementedError("Subclasses must implement optimize()")
        
    def get_solution(self) -> Dict[str, np.ndarray]:
        """获取解
        
        Returns:
            Dict[str, np.ndarray]: 解
        """
        return self.variables
        
    def get_objective(self) -> float:
        """获取目标函数值
        
        Returns:
            float: 目标函数值
        """
        return self.objective
        
    def get_solve_status(self) -> Dict[str, Any]:
        """获取求解状态
        
        Returns:
            Dict[str, Any]: 求解状态
        """
        return self.solve_status
        
    def update_solve_status(self, obj_val: float, gap: float, time: float):
        """更新求解状态
        
        Args:
            obj_val: 目标函数值
            gap: 对偶间隙
            time: 求解时间
        """
        self.solve_status['obj_val'] = obj_val
        self.solve_status['gap'] = gap
        self.solve_status['time'] = time
        
        # 更新历史信息
        self.history['obj_val'].append(obj_val)
        self.history['gap'].append(gap)
        self.history['time'].append(time)
        
    def calculate_objective(self) -> float:
        """计算目标函数值
        
        Returns:
            float: 目标函数值
        """
        return self.objective
        
    def calculate_gap(self) -> float:
        """计算对偶间隙
        
        Returns:
            float: 对偶间隙
        """
        return self.solve_status['gap']
        
    def calculate_solve_time(self) -> float:
        """计算求解时间
        
        Returns:
            float: 求解时间
        """
        return self.solve_status['time']
        
    def get_history(self) -> Dict[str, List[float]]:
        """获取历史信息
        
        Returns:
            Dict[str, List[float]]: 历史信息
        """
        return self.history
        
    def reset(self):
        """重置模型"""
        # 重置变量
        self.variables = {}
        
        # 重置约束
        self.constraints = {}
        
        # 重置目标函数
        self.objective = None
        
        # 重置求解状态
        self.solve_status = {
            'iter': 0,
            'obj_val': 0.0,
            'gap': float('inf'),
            'time': 0.0
        }
        
        # 重置历史信息
        self.history = {
            'obj_val': [],
            'gap': [],
            'time': []
        }
        
    def print_solution(self):
        """打印解"""
        logger.info("Solution:")
        logger.info(f"Objective value: {self.objective:.2f}")
        logger.info(f"Gap: {self.solve_status['gap']:.4f}")
        logger.info(f"Solve time: {self.solve_status['time']:.2f}s")
        
    def print_history(self):
        """打印历史信息"""
        logger.info("History:")
        logger.info(f"Objective values: {self.history['obj_val']}")
        logger.info(f"Gaps: {self.history['gap']}")
        logger.info(f"Solve times: {self.history['time']}")
        
    def save_solution(self, file_path: str):
        """保存解
        
        Args:
            file_path: 文件路径
        """
        import json
        
        solution = {
            'objective': self.objective,
            'variables': {k: v.tolist() for k, v in self.variables.items()},
            'solve_status': self.solve_status,
            'history': self.history
        }
        
        with open(file_path, 'w') as f:
            json.dump(solution, f, indent=4)
            
    def load_solution(self, file_path: str):
        """加载解
        
        Args:
            file_path: 文件路径
        """
        import json
        
        with open(file_path, 'r') as f:
            solution = json.load(f)
            
        self.objective = solution['objective']
        self.variables = {k: np.array(v) for k, v in solution['variables'].items()}
        self.solve_status = solution['solve_status']
        self.history = solution['history'] 