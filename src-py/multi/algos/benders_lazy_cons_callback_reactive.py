import logging
from typing import Dict, List, Any
from ..input_data import InputData
from ..utils.generate_parameter import Parameter
from ..default_setting import DefaultSetting
from ..model.primal.determine_model import DetermineModel
from ..model.dual.dual_sub_problem_reactive import DualSubProblemReactive

logger = logging.getLogger(__name__)

class BendersLazyConsCallbackReactive:
    """
    反应式Benders分解的惰性约束回调类
    
    用于在求解过程中生成反应式Benders割
    
    主要步骤:
    1. 获取主问题解
    2. 求解反应式子问题
    3. 生成反应式Benders割
    4. 将割添加到主问题中
    """
    
    def __init__(self, input_data: InputData, p: Parameter):
        """
        初始化回调类
        
        Args:
            input_data: 输入数据
            p: 模型参数
        """
        self.input_data = input_data
        self.p = p
        self.determine_model = None  # 主问题模型
        self.dual_sub_problem_reactive = None  # 反应式子问题模型
        self.cut_count = 0  # 割平面计数
        self.max_cuts = DefaultSetting.max_cuts  # 最大割平面数
        self.gap_tolerance = DefaultSetting.gap_tolerance  # 间隙容差
    
    def set_models(self, determine_model: DetermineModel, dual_sub_problem_reactive: DualSubProblemReactive):
        """
        设置模型
        
        Args:
            determine_model: 主问题模型
            dual_sub_problem_reactive: 反应式子问题模型
        """
        self.determine_model = determine_model
        self.dual_sub_problem_reactive = dual_sub_problem_reactive
    
    def callback(self):
        """
        回调函数
        
        在求解过程中被调用,用于生成反应式Benders割
        """
        try:
            # 获取主问题解
            x_var = self.determine_model.x_var
            y_var = self.determine_model.y_var
            z_var = self.determine_model.z_var
            g_var = self.determine_model.g_var
            
            # 求解反应式子问题
            self.dual_sub_problem_reactive.solve_model()
            
            # 检查子问题是否可行
            if self.dual_sub_problem_reactive.solve_status:
                # 生成反应式Benders割
                self._generate_benders_cut(x_var, y_var, z_var, g_var)
            else:
                # 生成可行性割
                self._generate_feasibility_cut(x_var, y_var, z_var, g_var)
            
            # 检查是否达到最大割平面数
            if self.cut_count >= self.max_cuts:
                logger.warning(f"Reached maximum number of cuts: {self.max_cuts}")
                return
            
        except Exception as e:
            logger.error(f"Error in callback: {str(e)}")
    
    def _generate_benders_cut(self, x_var: Dict, y_var: Dict, z_var: Dict, g_var: Dict):
        """
        生成反应式Benders割
        
        Args:
            x_var: 主问题x变量
            y_var: 主问题y变量
            z_var: 主问题z变量
            g_var: 主问题g变量
        """
        # 获取子问题解
        v_var_value1 = self.dual_sub_problem_reactive.v_var_value1
        v_var_value2 = self.dual_sub_problem_reactive.v_var_value2
        u_value = self.dual_sub_problem_reactive.u_value
        
        # 构建割平面
        cut = self.determine_model.model_str.add_constraint(
            self.determine_model.theta >= 
            sum(v_var_value1[r] * (sum(x_var[v, r] for v in self.input_data.vessels) - 1) 
                for r in self.input_data.routes) +
            sum(v_var_value2[r] * (sum(x_var[v, r] for v in self.input_data.vessels) - 1) 
                for r in self.input_data.routes) +
            sum(u_value[a] * (sum(g_var[v, a] for v in self.input_data.vessels) - 
                            sum(y_var[r, a] for r in self.input_data.routes))
                for a in self.input_data.arcs)
        )
        
        # 更新割平面计数
        self.cut_count += 1
        logger.info(f"Generated reactive Benders cut {self.cut_count}")
    
    def _generate_feasibility_cut(self, x_var: Dict, y_var: Dict, z_var: Dict, g_var: Dict):
        """
        生成可行性割
        
        Args:
            x_var: 主问题x变量
            y_var: 主问题y变量
            z_var: 主问题z变量
            g_var: 主问题g变量
        """
        # 获取子问题解
        v_var_value1 = self.dual_sub_problem_reactive.v_var_value1
        v_var_value2 = self.dual_sub_problem_reactive.v_var_value2
        u_value = self.dual_sub_problem_reactive.u_value
        
        # 构建可行性割
        cut = self.determine_model.model_str.add_constraint(
            sum(v_var_value1[r] * (sum(x_var[v, r] for v in self.input_data.vessels) - 1) 
                for r in self.input_data.routes) +
            sum(v_var_value2[r] * (sum(x_var[v, r] for v in self.input_data.vessels) - 1) 
                for r in self.input_data.routes) +
            sum(u_value[a] * (sum(g_var[v, a] for v in self.input_data.vessels) - 
                            sum(y_var[r, a] for r in self.input_data.routes))
                for a in self.input_data.arcs) <= 0
        )
        
        # 更新割平面计数
        self.cut_count += 1
        logger.info(f"Generated feasibility cut {self.cut_count}")
    
    def _get_capacity_on_arc(self, vessel: Any, route: Any) -> float:
        """
        计算弧上的容量
        
        Args:
            vessel: 船舶
            route: 航线
            
        Returns:
            float: 容量
        """
        capacity = 0
        for arc in route.arcs:
            if arc in vessel.arcs:
                capacity += vessel.capacity
        return capacity 