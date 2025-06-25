import logging
import time
from typing import Optional

from multi.algos.algo_frame import AlgoFrame
from multi.model.primal.master_problem import MasterProblem
from multi.utils.default_setting import DefaultSetting

logger = logging.getLogger(__name__)

class SOwithSAA(AlgoFrame):
    """Stochastic Optimization with Sample Average Approximation algorithm.
    
    This class implements a stochastic optimization algorithm using sample average approximation (SAA).
    The main steps are:
    1. Initialize the master problem model
    2. Add sample scenarios to the master problem
    3. Solve the master problem to get the solution
    4. Record and output the results
    """
    
    def __init__(self, input_data, p):
        """Initialize the SOwithSAA algorithm.
        
        Args:
            input_data: Input data for the problem
            p: Parameters for the algorithm
        """
        super().__init__()
        self.input_data = input_data
        self.p = p
        self.tau = p.tau
        self.algo = "SO&SAA"
        self.algo_id = (f"{self.algo}-R{len(input_data.ship_route_set)}"
                       f"-T{p.time_horizon}"
                       f"-{DefaultSetting.FLEET_TYPE}"
                       f"-S{DefaultSetting.RANDOM_SEED}"
                       f"-V{DefaultSetting.VESSEL_CAPACITY_RANGE}")
        self.frame()
        
    def _initialize_models(self) -> float:
        """Initialize the master problem model and add sample scenarios.
        
        Returns:
            float: Time taken to initialize the models
        """
        start = time.time()
        
        # Initialize master problem
        self.mp = MasterProblem(self.input_data, self.p, "Stochastic")
        
        # Add sample scenarios
        for i in range(len(self.p.sample_scenes)):
            self.mp.add_scene(self.input_data.scenarios[i])
            
        return time.time() - start
        
    def frame(self):
        """Execute the main algorithm steps:
        1. Initialize models
        2. Solve master problem
        3. Record results
        4. Output results
        """
        self._initialize()
        
        # Initialize models
        self._initialize_models()
        
        # Solve master problem
        self.mp.solve_model()
        
        # Update upper bound
        self.upper_bound = self.mp.obj_val
        
        # Set algorithm results
        self._set_algo_result()
        self._end()
        
    def _end_model(self):
        """End the master problem model."""
        self.mp.end() 