import logging
import time
from typing import Optional

from multi.algos.algo_frame import AlgoFrame
from multi.model.primal.master_problem import MasterProblem
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_problem import DualProblem
from multi.utils.default_setting import DefaultSetting

logger = logging.getLogger(__name__)

class SOwithBD(AlgoFrame):
    """
    Stochastic Optimization with Benders Decomposition algorithm.
    
    This class implements a stochastic optimization algorithm using Benders decomposition.
    The main steps are:
    1. Initialize the master problem and dual problem models
    2. Add initial scenario if needed
    3. Set initial solution if needed
    4. Iteratively solve master problem and dual problem until convergence
    5. Record and output the results

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
    
    def __init__(self, in_data, p):
        """Initialize the SOwithBD algorithm.
        
        Args:
            in_data: Input data for the problem
            p: Parameters for the algorithm
        """
        super().__init__()
        self.in_data = in_data
        self.p = p
        self.tau = p.tau
        self.algo = "SO&BD"
        self.algo_id = (f"{self.algo}-R{len(in_data.ship_route_set)}"
                       f"-T{p.time_horizon}"
                       f"-{DefaultSetting.FLEET_TYPE}"
                       f"-S{DefaultSetting.RANDOM_SEED}"
                       f"-V{DefaultSetting.VESSEL_CAPACITY_RANGE}")
        self.dp = None  # Dual problem model
        self.frame()
        
    def _initialize_models(self) -> float:
        """Initialize the master problem and dual problem models.
        
        Returns:
            float: Time taken to initialize the models
        """
        start = time.time()
        
        # Initialize dual problem
        self.dp = DualProblem(self.in_data, self.p)
        
        # Initialize master problem
        self.mp = MasterProblem(self.in_data, self.p, "Stochastic")
        
        # Add initial scenario if needed
        if DefaultSetting.WHETHER_ADD_INITIALIZE_SCE:
            self.mp.add_scene(self.sce[0])
            
        # Set initial solution if needed
        if DefaultSetting.WHETHER_SET_INITIAL_SOLUTION:
            dm = DetermineModel(self.in_data, self.p)
            self.mp.set_initial_solution(dm.v_var_value)
            
        return time.time() - start
        
    def frame(self):
        """Execute the main algorithm steps:
        1. Initialize models
        2. Add initial scenario if needed
        3. Solve master problem and dual problem iteratively
        4. Check convergence
        5. Record and output results
        """
        self._initialize()
        
        # Add initial scenario if needed
        if DefaultSetting.WHETHER_ADD_INITIALIZE_SCE:
            self._initialize_sce(self.sce)
            
        # Initialize models
        time0 = time.time()
        self._initialize_models()
        
        # Print iteration title
        self._print_iter_title(self.file_writer, time.time() - time0)
        self._print_iteration(self.file_writer, self.lower[self.iteration], 
                            self.upper[self.iteration], 0, 0, 0)
        
        flag = 0
        start0 = time.time()
        
        # Main iteration loop
        while (self.upper_bound - self.lower_bound > DefaultSetting.BOUND_GAP_LIMIT
               and flag == 0
               and self.iteration < DefaultSetting.MAX_ITERATION_NUM
               and (time.time() - start0) < DefaultSetting.MAX_ITERATION_TIME):
            
            # Solve master problem
            start1 = time.time()
            self.mp.solve_model()
            end1 = time.time()
            
            # Check if solution changed
            if not self._add_solution_pool(self.mp.solution):
                flag = 1
                
            # Update lower bound
            if (self.mp.obj_val > self.lower_bound 
                and self.mp.solve_status == "Optimal"):
                self._set_lower_bound(self.mp.obj_val)
                
            # Solve dual problem for each scenario
            total_sp_cost = 0
            self.dp.change_objective_v_vars_coefficients(self.mp.v_var_value)
            start2 = time.time()
            
            for i in range(len(self.p.sample_scenes)):
                self.dp.change_objective_u_vars_coefficients(self.p.sample_scenes[i])
                self.dp.solve_model()
                total_sp_cost += self.dp.obj_val
                self.mp.cplex.add(self.dp.construct_optimal_cut(
                    self.mp.cplex, self.mp.v_vars, self.mp.eta_vars[i]))
                
            end2 = time.time()
            
            # Update upper bound
            avg_sp_cost = total_sp_cost / len(self.p.sample_scenes)
            if avg_sp_cost + self.mp.operation_cost < self.upper_bound:
                self._set_upper_bound(avg_sp_cost + self.mp.operation_cost)
                
            # Update iteration counter and bounds
            self.iteration += 1
            self.upper[self.iteration] = self.upper_bound
            self.lower[self.iteration] = self.lower_bound
            
            # Print iteration results
            self._print_iteration(self.file_writer, self.lower[self.iteration],
                                self.upper[self.iteration],
                                end2 - start2, end1 - start1,
                                time.time() - start0)
            
        # End the loop
        if flag == 1:
            logger.info("MP solution duplicate")
            
        # Set algorithm results
        self._set_algo_result()
        self._end()
        
    def _end_model(self):
        """End the master problem and dual problem models."""
        self.mp.end()
        self.dp.end() 