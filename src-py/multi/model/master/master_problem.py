import numpy as np
from typing import List, Dict, Any, Tuple
from multi.model.base_model import BaseModel
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
import logging

logger = logging.getLogger(__name__)

class MasterProblem(BaseModel):
    """主问题类
    
    实现了Benders分解中的主问题:
    1. 变量定义
    2. 约束构建
    3. 目标函数构建
    4. 求解方法
    """
    
    def __init__(self, input_data: InputData, param: Parameter):
        """初始化主问题
        
        Args:
            input_data: 输入数据
            param: 模型参数
        """
        super().__init__(input_data, param)
        self.model_name = "MasterProblem"
        
        # 主问题变量
        self.v_var = None  # 船舶分配变量
        self.u_var = None  # 对偶变量
        
        # 主问题约束
        self.vessel_constraints = []  # 船舶约束
        self.cut_constraints = []     # 切割约束
        
        # 主问题目标函数
        self.obj_val = 0.0
        
    def set_decision_vars(self):
        """设置决策变量"""
        # 船舶分配变量
        self.v_var = self.model.binary_var_matrix(
            len(self.param.vessel_set),
            len(self.param.ship_route_set),
            name="v"
        )
        
        # 对偶变量
        self.u_var = self.model.continuous_var(name="u")
        
    def set_constraints(self):
        """设置约束条件"""
        # 船舶约束
        for h in range(len(self.param.vessel_set)):
            self.vessel_constraints.append(
                self.model.add_constraint(
                    self.model.sum(self.v_var[h, r] for r in range(len(self.param.ship_route_set))) <= 1,
                    name=f"vessel_{h}"
                )
            )
            
        # 切割约束在迭代过程中动态添加
        
    def set_objectives(self):
        """设置目标函数"""
        # 船舶运营成本
        vessel_cost = self.model.sum(
            self.param.vessel_operation_cost[h][r] * self.v_var[h, r]
            for h in range(len(self.param.vessel_set))
            for r in range(len(self.param.ship_route_set))
        )
        
        # 对偶项
        dual_term = self.u_var
        
        # 总目标
        self.model.minimize(vessel_cost + dual_term)
        
    def add_cut(self, cut_coefficients: List[List[float]], cut_rhs: float):
        """添加切割约束
        
        Args:
            cut_coefficients: 切割约束系数
            cut_rhs: 切割约束右端项
        """
        # 构建切割约束
        cut = self.model.sum(
            cut_coefficients[h][r] * self.v_var[h, r]
            for h in range(len(self.param.vessel_set))
            for r in range(len(self.param.ship_route_set))
        ) + self.u_var >= cut_rhs
        
        # 添加约束
        self.cut_constraints.append(
            self.model.add_constraint(cut, name=f"cut_{len(self.cut_constraints)}")
        )
        
    def solve(self) -> Tuple[float, Dict[str, Any]]:
        """求解主问题
        
        Returns:
            Tuple[float, Dict[str, Any]]: 目标函数值和求解状态
        """
        try:
            # 求解问题
            solution = self.model.solve()
            
            if solution:
                # 更新目标函数值
                self.obj_val = solution.get_objective_value()
                
                # 更新船舶分配变量值
                self.v_var_value = np.zeros((len(self.param.vessel_set), len(self.param.ship_route_set)))
                for h in range(len(self.param.vessel_set)):
                    for r in range(len(self.param.ship_route_set)):
                        self.v_var_value[h][r] = solution.get_value(self.v_var[h, r])
                
                # 更新对偶变量值
                self.u_value = solution.get_value(self.u_var)
                
                # 更新求解状态
                self.update_solve_status(
                    self.obj_val,
                    solution.get_mip_relative_gap(),
                    solution.get_solve_time()
                )
                
                return self.obj_val, self.solve_status
            else:
                logger.error("Failed to solve master problem")
                raise Exception("Failed to solve master problem")
                
        except Exception as e:
            logger.error(f"Error in solving master problem: {str(e)}")
            raise
            
    def get_vessel_allocation(self) -> np.ndarray:
        """获取船舶分配方案
        
        Returns:
            np.ndarray: 船舶分配方案
        """
        return self.v_var_value
        
    def get_dual_value(self) -> float:
        """获取对偶变量值
        
        Returns:
            float: 对偶变量值
        """
        return self.u_value
        
    def get_objective_value(self) -> float:
        """获取目标函数值
        
        Returns:
            float: 目标函数值
        """
        return self.obj_val
        
    def reset(self):
        """重置主问题"""
        super().reset()
        
        # 重置变量
        self.v_var = None
        self.u_var = None
        
        # 重置约束
        self.vessel_constraints = []
        self.cut_constraints = []
        
        # 重置目标函数
        self.obj_val = 0.0 