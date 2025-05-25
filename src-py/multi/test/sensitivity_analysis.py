import logging
import os
from typing import List, Optional

from multi.algos.benders_decomposition import BendersDecomposition
from multi.algos.benders_decomposition_with_pap import BendersDecompositionWithPAP
from multi.algos.benders_decomposition_with_pareto import BDwithPareto
from multi.algos.so_with_bd import SOwithBD
from multi.algos.so_with_saa import SOwithSAA
from multi.algos.ccg import CCG
from multi.algos.ccg_with_pap import CCGwithPAP
from multi.algos.ccg_with_pap_reactive import CCGwithPAP_Reactive
from multi.model.primal.determine_model import DetermineModel
from multi.model.primal.determine_model_reactive import DetermineModelReactive
from multi.utils.default_setting import DefaultSetting
from multi.utils.read_data import ReadData
from multi.utils.generate_parameter import GenerateParameter
from multi.utils.select_paths import SelectPaths

logger = logging.getLogger(__name__)

class SensitivityAnalysis:
    """Sensitivity analysis experiment class.
    
    This class implements various sensitivity analysis experiments to test
    the impact of different parameters on algorithm performance.
    
    Test cases:
    1. Small scale (data1): 2 routes, 10 ports, 10 vessels
    2. Large scale (data2): 8 routes, 29 ports, 40 vessels
    3. Middle scale (data3): 3 routes, 21 ports, 35 vessels
    """
    
    def __init__(self, instance: int, type: int, algo: str):
        """Initialize the sensitivity analysis.
        
        Args:
            instance: Test instance number (1: small scale, 2: large scale, 3: middle scale)
            type: Experiment type number
            algo: Algorithm to use for analysis
        """
        # Create result file
        file_path = os.path.join(
            DefaultSetting.ROOT_PATH,
            DefaultSetting.TEST_RESULT_PATH,
            f"Sensitivity{instance}-{type}-{DefaultSetting.RANDOM_SEED}.txt"
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        self.file_writer = open(file_path, "a")
        
        # Set time horizon based on instance
        if instance == 1:
            self.default_time_horizon = 70
            self.time_horizon_set = [56, 63, 70, 77, 84, 91]
        elif instance == 2:
            self.default_time_horizon = 90
            self.time_horizon_set = [60, 75, 90, 105, 120, 135]
        elif instance == 3:
            self.default_time_horizon = 90
            self.time_horizon_set = [90, 105, 120, 135, 150, 165, 180]
        elif instance == 4:
            self.default_time_horizon = 90
            self.time_horizon_set = [60, 75, 90, 105, 120, 135, 150, 165, 180]
        elif instance == 5:
            self.default_time_horizon = 90
            self.time_horizon_set = [49]
            
        # Set uncertain degree
        self.uncertain_degree = DefaultSetting.DEFAULT_UNCERTAIN_DEGREE
        
        # Get data file path
        file_name = os.path.join(DefaultSetting.DATA_PATH, DefaultSetting.CASE_PATH)
        
        # Run appropriate experiment
        if type == 1:
            self._experiment_test1(file_name, algo)
        elif type == 2:
            self._experiment_test2(file_name, algo)
        elif type == 3:
            self._experiment_test3(file_name, algo)
        elif type == 4:
            self._experiment_test4(file_name, algo)
        elif type == 5:
            self._experiment_test5(file_name, algo)
        elif type == 6:
            self._experiment_test6(file_name, algo)
        elif type == 7:
            self._experiment_test7(file_name, algo)
        elif type == 8:
            self._experiment_test8(file_name, algo)
        elif type == 9:
            self._experiment_test9(file_name, algo)
        elif type == 10:
            self._experiment_test10(file_name, algo)
            
        self.file_writer.close()
        
    def _experiment_test1(self, file_name: str, algo: str):
        """Experiment 1: Test sensitivity to uncertain degree."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 1" + "=============================")
        
        uncertain_degree_set = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        
        for ud in uncertain_degree_set:
            logger.info(f"Uncertain Degree : {ud}\n")
            self.uncertain_degree = ud
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"UncertainDegree : {ud}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test2(self, file_name: str, algo: str):
        """Experiment 2: Test sensitivity to container path cost."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 2" + "=============================")
        
        cost_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for cf in cost_factor_set:
            logger.info(f"Cost Factor : {cf}\n")
            DefaultSetting.CONTAINER_PATH_COST_FACTOR = cf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Cost Factor : {cf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test3(self, file_name: str, algo: str):
        """Experiment 3: Test sensitivity to rental container cost."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 3" + "=============================")
        
        rental_cost_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for rcf in rental_cost_factor_set:
            logger.info(f"Rental Cost Factor : {rcf}\n")
            DefaultSetting.RENTAL_CONTAINER_COST_FACTOR = rcf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Rental Cost Factor : {rcf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test4(self, file_name: str, algo: str):
        """Experiment 4: Test sensitivity to penalty cost."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 4" + "=============================")
        
        penalty_cost_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for pcf in penalty_cost_factor_set:
            logger.info(f"Penalty Cost Factor : {pcf}\n")
            DefaultSetting.PENALTY_COST_FACTOR = pcf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Penalty Cost Factor : {pcf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test5(self, file_name: str, algo: str):
        """Experiment 5: Test sensitivity to vessel capacity."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 5" + "=============================")
        
        capacity_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for cf in capacity_factor_set:
            logger.info(f"Capacity Factor : {cf}\n")
            DefaultSetting.VESSEL_CAPACITY_FACTOR = cf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Capacity Factor : {cf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test6(self, file_name: str, algo: str):
        """Experiment 6: Test sensitivity to time window."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 6" + "=============================")
        
        time_window_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for twf in time_window_factor_set:
            logger.info(f"Time Window Factor : {twf}\n")
            DefaultSetting.TIME_WINDOW_FACTOR = twf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Time Window Factor : {twf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test7(self, file_name: str, algo: str):
        """Experiment 7: Test sensitivity to port handling time."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 7" + "=============================")
        
        handling_time_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for htf in handling_time_factor_set:
            logger.info(f"Handling Time Factor : {htf}\n")
            DefaultSetting.PORT_HANDLING_TIME_FACTOR = htf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Handling Time Factor : {htf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test8(self, file_name: str, algo: str):
        """Experiment 8: Test sensitivity to sailing time."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 8" + "=============================")
        
        sailing_time_factor_set = [0.5, 0.75, 1.0, 1.25, 1.5]
        
        for stf in sailing_time_factor_set:
            logger.info(f"Sailing Time Factor : {stf}\n")
            DefaultSetting.SAILING_TIME_FACTOR = stf
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Sailing Time Factor : {stf}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test9(self, file_name: str, algo: str):
        """Experiment 9: Test sensitivity to initial container percentage."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 9" + "=============================")
        
        container_percent_set = [0.1, 0.25, 0.5, 0.75, 1.0]
        
        for cp in container_percent_set:
            logger.info(f"Initial Container Percent : {cp}\n")
            DefaultSetting.DEFAULT_FOLD_CONTAINER_PERCENT = cp
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, 0.4)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Initial Container Percent : {cp}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
    def _experiment_test10(self, file_name: str, algo: str):
        """Experiment 10: Test sensitivity to path selection percentage."""
        logger.info("========================== Begin Sensitivity Analysis =========================")
        logger.info("=============================" + "Experiment 10" + "=============================")
        
        path_percent_set = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0]
        
        for pp in path_percent_set:
            logger.info(f"Path Selection Percent : {pp}\n")
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                para = GenerateParameter(input_data, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, para, pp)
                
                # Run algorithm
                if algo == "BD":
                    result = BendersDecomposition(input_data, para)
                elif algo == "CCG":
                    result = CCG(input_data, para)
                elif algo == "CCG&PAP":
                    result = CCGwithPAP(input_data, para)
                else:
                    logger.error(f"Unknown algorithm: {algo}")
                    continue
                    
                # Log results
                logger.info(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}")
                
                if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                    self.file_writer.write(f"\nTimeHorizon : {t}\n")
                    self.file_writer.write(f"Path Selection Percent : {pp}\n")
                    input_data.write_status(self.file_writer)
                    self.file_writer.write(f"{algo} : {result.obj_val}\t{result.solve_time}\t{result.iter}\n")
                    self.file_writer.flush()
                    
DefaultSetting.VESSEL_CAPACITY_RANGE = [100, 200]
DefaultSetting.VESSEL_OPERATION_COST = 1000
DefaultSetting.EMPTY_CONTAINER_COST_RATIO = 0.5
DefaultSetting.PENALTY_COST_RATIO = 0.1
DefaultSetting.CONTAINER_RENTAL_COST = 100
DefaultSetting.INITIAL_EMPTY_CONTAINER_RATIO = 0.2
DefaultSetting.TURNOVER_TIME_RATIO = 0.1
DefaultSetting.DEMAND_MEAN_RATIO = 0.1
DefaultSetting.DEMAND_VARIATION_RATIO = 0.2 