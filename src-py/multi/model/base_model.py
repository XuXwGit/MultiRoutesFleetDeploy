"""
模型基类

定义所有模型共用的属性和方法

主要功能:
1. 维护模型基本参数(in/p)
2. 管理CPLEX求解器实例
3. 记录求解结果(obj_val/obj_gap等)
4. 提供基础设置方法(public_setting)

关键属性:
- in_data: 输入数据(网络结构、需求等)
- p: 模型参数(成本系数、容量等)
- cplex: CPLEX求解器实例
- v_var_value: 船舶分配决策变量值
- u_value: 对偶变量值

@Author: XuXw
@DateTime: 2024/12/4 21:54
"""
import logging
import time
import os
from docplex.mp.model import Model  # 使用docplex.mp.model而非cplex
from typing import List, Optional, Tuple, Any
import numpy as np

from multi.utils.default_setting import DefaultSetting
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.int_array2d_wrapper import IntArray2DWrapper  # 正确导入包装类
# 设置日志
logger = logging.getLogger(__name__)


class BaseModel:
    """模型基类"""
    
    cplex: Model = None
    _fleet_type = DefaultSetting.FLEET_TYPE
    _random_seed = DefaultSetting.RANDOM_SEED

    def __init__(self, input_data: Optional[InputData] = None, p: Optional[Parameter] = None):
        """
        对应Java构造函数：
        - public BaseModel()
        - public BaseModel(InputData in, Parameter p)
        """
        # 如果是默认无参数构造函数，则不进行初始化
        if input_data is None or p is None:
            return
            
        # 基本属性
        self._input_data = input_data  # 对应Java: protected InputData in
        self._p = p  # 对应Java: protected Parameter p

        self._model = ""  # 对应Java: protected String model

        # 统一为实例变量
        self.obj_val = 0.0
        self.obj_gap = 0.0
        self.solve_time = 0.0
        self.v_var_value = []
        self.u_value = []
        self.operation_cost = 0.0
        self.laden_cost = 0.0
        self.empty_cost = 0.0
        self.rental_cost = 0.0
        self.penalty_cost = 0.0

        self.cplex = None
        self.objective = None

    def initialize(self):
        """
        初始化模型
        """
        try:
            # 创建CPLEX求解器实例（使用docplex中的Model）
            self.cplex = Model(name=self._model_name or "base_model")
        except Exception as e:
            # 对应Java的: throw new RuntimeException(e)
            raise RuntimeError(f"初始化CPLEX求解器失败: {str(e)}")

        try:
            # 设置CPLEX求解器参数
            self.public_setting(self.cplex)
        except Exception as e:
            raise RuntimeError(f"设置求解器参数失败: {str(e)}")

        try:
            # 创建基本决策变量并添加基本约束
            self.frame()    
        except Exception as e:
            raise RuntimeError(f"初始化模型失败: {str(e)}") 


    def public_setting(self, cplex_model: Model):
        """
        设置CPLEX公共参数
        对应Java: protected void publicSetting(IloCplex cplex)
        """
        # 关闭输出日志
        if DefaultSetting.WHETHER_CLOSE_OUTPUT_LOG:
            cplex_model.context.solver.log_output = False
        
        # 设置工作内存（docplex中的设置方式）
        cplex_model.parameters.workmem = DefaultSetting.MAX_WORK_MEM
        # 设置时间限制
        cplex_model.parameters.timelimit = DefaultSetting.MIP_TIME_LIMIT
        # 设置MIP Gap限制
        cplex_model.parameters.mip.tolerances.mipgap = DefaultSetting.MIP_GAP_LIMIT
        # 设置线程数
        cplex_model.parameters.threads = DefaultSetting.MAX_THREADS
    
    def frame(self):
        """
        创建模型框架，设置决策变量、目标函数和约束条件
        对应Java: public void frame() throws IloException
        """
        # 记录开始时间
        start = time.time()
        
        # 设置决策变量
        try:
            self.set_decision_vars()
            logger.debug(f"Set <{self._model_name}> DecisionVars Time = {(time.time() - start) * 1000}")
        except Exception as e:
            raise RuntimeError(f"设置决策变量失败: {str(e)}")
        
        # 设置目标函数
        start = time.time()
        try:
            self.set_objectives()
            logger.debug(f"Set <{self._model_name}> Objectives Time = {(time.time() - start) * 1000}")
        except Exception as e:
            raise RuntimeError(f"设置目标函数失败: {str(e)}")
        
        # 设置约束条件
        start = time.time()
        try:
            self.set_constraints()
            logger.debug(f"Set <{self._model_name}> Constraints Time = {(time.time() - start) * 1000}")
        except Exception as e:
            raise RuntimeError(f"设置约束条件失败: {str(e)}")
    
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
    
    def end(self):
        """
        结束CPLEX实例
        对应Java: public void end()
        """
        if self.cplex:
            self.cplex.end()
    
    def get_solve_status(self) -> int:
        """
        获取求解状态
        对应Java: public IloCplex.Status getSolveStatus() throws IloException
        """
        if self.cplex and hasattr(self.cplex, 'solve_details'):
            return self.cplex.solve_details.status_code
        return -1
    
    def get_solve_status_string(self) -> str:
        """
        获取求解状态字符串
        对应Java: public String getSolveStatusString() throws IloException
        """
        if not self.cplex:
            return "No CPLEX instance"
        
        if not hasattr(self.cplex, 'solve_details'):
            return "Not solved yet"
            
        status = self.cplex.solve_details.status
        
        # DocPLEX状态映射
        if "optimal" in status:
            return "Optimal"
        elif "feasible" in status:
            return "Feasible"
        elif "infeasible" in status:
            return "Infeasible"
        elif "unbounded" in status:
            return "Unbounded"
        return "Others"
    
    def get_capacity_on_arcs(self, v_value) -> List[float]:
        """
        计算航线上的容量
        对应Java重载方法:
        - protected double[] getCapacityOnArcs(double[][] vValue)
        - protected double[] getCapacityOnArcs(int[][] vValue)
        """
        # 初始化容量数组
        capacities = [0.0] * len(self._p.traveling_arcs_set)
        
        if v_value is None or len(v_value) == 0:
            return capacities

        # 计算每条弧上的容量
        for n, arc in enumerate(self.input_data.traveling_arcs):
            # 对应Java: capacities[n] = 0;
            capacities[n] = 0.0
            
            # 遍历所有船舶路径 w∈Ω
            for w, vessel_path in enumerate(self.input_data.vessel_paths):
                # 获取路径w对应的航线r
                r =vessel_path.route_id - 1
                
                # 遍历所有船舶类型 h \in Hr
                for h, vessel_type in enumerate(self.input_data.vessel_types):
                    try:
                        if DefaultSetting.FLEET_TYPE == "Homo":
                            capacities[n] += self.p.arc_and_vessel_path[arc.id][vessel_path.id] * self.p.ship_route_and_vessel_path[vessel_path.route_id][vessel_path.id] * self.p.vessel_type_and_ship_route[vessel_type.id][vessel_path.route_id] * vessel_type.capacity * v_value[h][r]
                        elif DefaultSetting.FLEET_TYPE == "Hetero":
                            capacities[n] += self.p.arc_and_vessel_path[arc.id][vessel_path.id] * vessel_type.capacity * v_value[h][w]
                        else:
                            logger.error("Error in Fleet type!")
                    except Exception as e:
                        logger.error(f"Error in getCapacityOnArcs: {str(e)}")

        return capacities
    
    def export_model(self):
        """
        导出模型文件
        对应Java: protected void exportModel() throws IloException
        """
        # 构建模型文件路径
        model_file_path = os.path.join(DefaultSetting.ROOT_PATH, DefaultSetting.EXPORT_MODEL_PATH)
        
        # 确保目录存在
        os.makedirs(model_file_path, exist_ok=True)
        
        # 构建文件名
        filename = f"{self._model_name}.lp"
        full_path = os.path.join(model_file_path, filename)
        
        # 导出模型
        if self.cplex:
            self.cplex.export_as_lp(full_path)
    
    # Getter和Setter方法
    @property
    def input_data(self) -> InputData:
        """对应Java: getIn() 通过@Getter自动生成"""
        return self._input_data
    
    @input_data.setter
    def input_data(self, value: InputData):
        """对应Java: setIn() 通过@Setter自动生成"""
        self._input_data = value
    
    @property
    def p(self) -> Parameter:
        """对应Java: getP() 通过@Getter自动生成"""
        return self._p
    
    @property
    def param(self) -> Parameter:
        """对应Java: getParam() 通过@Getter自动生成"""
        return self._p
    
    @param.setter
    def param(self, value: Parameter):
        """对应Java: setP() 通过@Setter自动生成"""
        self._p = value
    
    @property
    def tau(self) -> int:
        """对应Java: getTau() 通过@Getter自动生成"""
        return self._tau
    
    @property
    def model(self) -> str:
        """对应Java: getModel() 通过@Getter自动生成"""
        return self._model
    
    @model.setter
    def model(self, value: str):
        """对应Java: setModel() 通过@Setter自动生成"""
        self._model = value
    
    @property
    def model_name(self) -> str:
        """对应Java: getModelName() 通过@Getter自动生成"""
        return self._model_name
    
    @model_name.setter
    def model_name(self, value: str):
        """对应Java: setModelName() 通过@Setter自动生成"""
        self._model_name = value
    
    @property
    def obj_val(self) -> float:
        """对应Java: getObjVal() 通过@Getter自动生成"""
        return self._obj_val
    
    @obj_val.setter
    def obj_val(self, value: float):
        """对应Java: setObjVal() 通过@Setter自动生成"""
        self._obj_val = value
    
    def set_obj_val(self, value: float):
        """对应Java: setObjVal() 通过@Setter自动生成"""
        self._obj_val = value

    @property
    def obj_gap(self) -> float:
        """对应Java: getObjGap() 通过@Getter自动生成"""
        return self._obj_gap
    
    @obj_gap.setter
    def obj_gap(self, value: float):
        """对应Java: setObjGap() 通过@Setter自动生成"""
        self._obj_gap = value

    def set_obj_gap(self, value: float):
        """对应Java: setObjGap() 通过@Setter自动生成"""
        self._obj_gap = value

    @property
    def operation_cost(self) -> float:
        """对应Java: getOperationCost() 通过@Getter自动生成"""
        return self._operation_cost
    
    @operation_cost.setter
    def operation_cost(self, value: float):
        """对应Java: setOperationCost() 通过@Setter自动生成"""
        self._operation_cost = value
    
    def set_operation_cost(self, value: float):
        """对应Java: setOperationCost() 通过@Setter自动生成"""
        self._operation_cost = value

    @property
    def solve_time(self) -> float:
        """对应Java: getSolveTime() 通过@Getter自动生成"""
        return self._solve_time
    
    @solve_time.setter
    def solve_time(self, value: float):
        """对应Java: setSolveTime() 通过@Setter自动生成"""
        self._solve_time = value
    
    def set_solve_time(self, value: float):
        """对应Java: setSolveTime() 通过@Setter自动生成"""
        self._solve_time = value

    @property
    def v_var_value(self) -> List[List[int]]:
        """对应Java: getVVarValue() 通过@Getter自动生成"""
        return self._v_var_value
    
    @v_var_value.setter
    def v_var_value(self, value: List[List[int]]):
        """对应Java: setVVarValue() 通过@Setter自动生成"""
        self._v_var_value = value

    @v_var_value.setter
    def v_var_value(self, value: List[List[float]]):
        """对应Java: setVVarValue() 通过@Setter自动生成"""
        self._v_var_value = value

    def set_v_var_value(self, value):
        """对应Java: setVVarValue() 通过@Setter自动生成"""
        self._v_var_value = value

    @property
    def v_var_value_double(self) -> List[List[float]]:
        """对应Java: getVVarValueDouble() 通过@Getter自动生成"""
        return self._v_var_value_double
    
    @v_var_value_double.setter
    def v_var_value_double(self, value: List[List[float]]):
        """对应Java: setVVarValueDouble() 通过@Setter自动生成"""
        self._v_var_value_double = value
    
    @property
    def u_value(self) -> List[float]:
        """对应Java: getUValue() 通过@Getter自动生成"""
        return self._u_value
    
    @u_value.setter
    def u_value(self, value: List[float]):
        """对应Java: setUValue() 通过@Setter自动生成"""
        self._u_value = value 

    def set_u_value(self, value: List[float]):
        """对应Java: setUValue() 通过@Setter自动生成"""
        self._u_value = value

    @property
    def fleet_type(self) -> str:
        """对应Java: getFleetType() 通过@Getter自动生成"""
        return self._fleet_type
    
    @fleet_type.setter
    def fleet_type(self, value: str):
        """对应Java: setFleetType() 通过@Setter自动生成"""
        self._fleet_type = value


    @property
    def random_seed(self) -> int:
        """对应Java: getRandomSeed() 通过@Getter自动生成"""
        return self._random_seed
    
    @random_seed.setter
    def random_seed(self, value: int):
        """对应Java: setRandomSeed() 通过@Setter自动生成"""
        self._random_seed = value
