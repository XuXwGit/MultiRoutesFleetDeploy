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
from multi.model.parameter import Parameter
from multi.model.primal.determine_model import DetermineModel
from multi.model.primal.determine_model_reactive import DetermineModelReactive
from multi.utils.default_setting import DefaultSetting
from multi.utils.input_data import InputData
from multi.utils.read_data import ReadData
from multi.utils.generate_parameter import GenerateParameter
from multi.utils.select_paths import SelectPaths

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class PerformanceExperiment:
    """Performance testing experiment class.
    
    This class implements various performance testing experiments to compare
    different algorithms and strategies.
    
    Test cases:
    1. Small scale (data1): 2 routes, 10 ports, 10 vessels
    2. Large scale (data2): 8 routes, 29 ports, 40 vessels
    3. Middle scale (data3): 3 routes, 21 ports, 35 vessels
    """
    
    def __init__(self, instance: int, type: int):
        """Initialize the performance experiment.
        
        Args:
            instance: Test instance number (1: small scale, 2: large scale, 3: middle scale)
            type: Experiment type number
        """
        # Create result file
        file_path = os.path.join(
            DefaultSetting.ROOT_PATH,
            DefaultSetting.TEST_RESULT_PATH,
            f"Performance{instance}-{type}-{DefaultSetting.RANDOM_SEED}.txt"
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
            self._experiment_test1(file_name)
        elif type == 2:
            self._experiment_test2(file_name)
        elif type == 3:
            self._experiment_test3(file_name)
        elif type == 4:
            self._experiment_test4(file_name)
        elif type == 6:
            self._experiment_test6(file_name)
        elif type == 7:
            self._experiment_test7(file_name)
        elif type == 8:
            self._experiment_test8(file_name)
        elif type == 9:
            self._experiment_test9(file_name)
        elif type == 10:
            self._experiment_test10(file_name)
            
        self.file_writer.close()
        
    def _experiment_test1(self, file_name: str):
        """Experiment 1: Compare performance of different algorithms.
        
        Compares:
        - BD (Benders Decomposition)
        - CCG&PAP (Column Generation with Price Adjustment Problem)
        - CCG (Column Generation)
        """
        logger.info("========================== Begin Performance Test =========================")
        logger.info("==============================" + "Experiment 1" + "=============================")
        
        for t in self.time_horizon_set:
            # Initialize data and parameters
            input_data = InputData()
            param = Parameter()
            ReadData(path=file_name, input_data=input_data, time_horizon=t)
            GenerateParameter(input_data= input_data, param=param, time_horizon=t, uncertain_degree=self.uncertain_degree)
            input_data.show_status()
            SelectPaths(input_data, param, 0.4)
            
            # Run algorithms
            ccg = CCG(input_data, param)
            ccgp = CCGwithPAP(input_data, param)
            bd = BendersDecomposition(input_data, param)
            dm = DetermineModel(input_data, param)
            
            # Log results
            logger.info("=====================================================================")
            logger.info("Algorithm :\t"
                       + "BD" + "\t"
                       + "CCG&PAP" + "\t"
                       + "CCG" + "\t"
            )
            logger.info("SolveTime :\t"
                       + f"{bd.solve_time}\t"
                       + f"{ccgp.solve_time}\t"
                       + f"{ccg.solve_time}\t"
            )
            
            if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                self.file_writer.write(f"\nTimeHorizon : {t}\n")
                self.file_writer.write(f"UncertainDegree : {self.uncertain_degree}\n")
                input_data.write_status(self.file_writer)
                
                self.file_writer.write("Algorithm :\t"
                                     + "BD" + "\t"
                                     + "CCG&PAP" + "\t"
                                     + "CCG" + "\t"
                                     + "\n"
                )
                self.file_writer.write("SolveTime :\t"
                                     + f"{bd.solve_time}\t"
                                     + f"{ccgp.solve_time}\t"
                                     + f"{ccg.solve_time}\t"
                                     + "\n"
                )
                self.file_writer.write("Objective  :\t"
                                     + f"{bd.obj_val:.2f}\t"
                                     + f"{ccgp.obj_val:.2f}\t"
                                     + f"{ccg.obj_val:.2f}\t"
                                     + "\n"
                )
                self.file_writer.write("Iteration    :\t"
                                     + f"{bd.iter}\t"
                                     + f"{ccgp.iter}\t"
                                     + f"{ccg.iter}\t"
                                     + "\n"
                )
                self.file_writer.write("\n")
                self.file_writer.flush()
                
    def _experiment_test2(self, file_name: str):
        """Experiment 2: Compare reactive and non-reactive strategies."""
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 2" + "=============================")
        
        for t in self.time_horizon_set:
            logger.info(f"TimeHorizon : {t}\n")
            logger.info(f"UncertainDegree : {self.uncertain_degree}\n")
            
            # Initialize data and parameters
            input_data = ReadData(file_name, t)
            param = Parameter()
            GenerateParameter(input_data, param, t, self.uncertain_degree)
            
            # Run algorithms
            de = DetermineModel(input_data, param)
            der = DetermineModelReactive(input_data, param)
            cp = CCGwithPAP(input_data, param)
            cpr = CCGwithPAP_Reactive(input_data, param)
            
            # Log results
            logger.info("==========================================")
            logger.info("Algorithm :\t"
                       + "Determine" + "\t"
                       + "Determine&Reactive" + "\t"
                       + "CCG&PAP" + "\t"
                       + "CCG&PAP&Reactive" + "\t"
            )
            logger.info("SolveTime :\t"
                       + f"{de.solve_time}\t"
                       + f"{der.solve_time}\t"
                       + f"{cp.solve_time}\t"
                       + f"{cpr.solve_time}\t"
            )
            logger.info("Objective  :\t"
                       + f"{de.obj_val:.2f}\t"
                       + f"{der.obj_val:.2f}\t"
                       + f"{cp.obj_val:.2f}\t"
                       + f"{cpr.obj_val:.2f}\t"
            )
            
    def _experiment_test3(self, file_name: str):
        """Experiment 3: Compare different path selection strategies."""
        self._print_data_status(file_name)
        
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 3" + "=============================")
        
        for t in self.time_horizon_set:
            logger.info(f"TimeHorizon : {t}\n")
            percent_set = [0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0]
            
            for percent in percent_set:
                logger.info(f"Path Percent : {percent}\n")
                
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                param = Parameter()
                GenerateParameter(input_data, param, t, self.uncertain_degree)
                input_data.show_status()
                SelectPaths(input_data, param, percent)
                
                # Run algorithms
                ccgp = CCGwithPAP(input_data, param)
                ccg = CCG(input_data, param)
                bd = BendersDecomposition(input_data, param)
                bdp = BendersDecompositionWithPAP(input_data, param)
                
                # Log results
                logger.info("=====================================================================")
                logger.info("Algorithm :\t"
                           + "BD&PAP" + "\t"
                           + "BD" + "\t"
                           + "CCG&PAP" + "\t"
                           + "CCG" + "\t"
                )
                logger.info("SolveTime :\t\t"
                           + f"{bdp.solve_time}\t"
                           + f"{bd.solve_time}\t"
                           + f"{ccgp.solve_time}\t"
                           + f"{ccg.solve_time}\t"
                )
                
    def _print_data_status(self, file_name: str):
        """Print data status for different time horizons."""
        logger.info("========================== Print Data Status =========================")
        
        for t in self.time_horizon_set:
            logger.info(f"TimeHorizon : {t}\n")
            input_data = ReadData(file_name, t)
            param = Parameter()
            GenerateParameter(input_data, param, t, self.uncertain_degree)
            logger.info(f"UncertainDegree : {self.uncertain_degree}\n")
            input_data.show_status()
            
    def _experiment_test4(self, file_name: str):
        """Experiment 4: Compare homogeneous and heterogeneous fleet performance."""
        DefaultSetting.CCG_PAP_USE_SP = True
        self._print_data_status(file_name)
        
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 4" + "=============================")
        
        self.file_writer.write("\n===========================================\n")
        self.file_writer.write("TimeHorizon\tHomo-Obj\tHetero-Obj\t"
                             + "Homo-OC\tHetero-OC\t"
                             + "Homo-LC\tHetero-LC\t"
                             + "Homo-EC\tHetero-EC\t"
                             + "Homo-RC\tHetero-RC\t"
                             + "Homo-PC\tHetero-PC\t"
                             + "Homo-WP\tHetero-WP\t"
                             + "\n")
        
        for t in self.time_horizon_set:
            logger.info(f"TimeHorizon : {t}\n")
            
            # Initialize data and parameters
            input_data = ReadData(file_name, t)
            input_data.show_status()
            param = Parameter()
            GenerateParameter(input_data, param, t, self.uncertain_degree)
            logger.info(f"UncertainDegree : {self.uncertain_degree}\n")
            SelectPaths(input_data, param, 0.4)
            
            # Run algorithm
            ccgp = CCGwithPAP(input_data, param, param.tau)
            
            if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                self.file_writer.write(f"{t}\t")
                self.file_writer.write(f"{ccgp.obj_val}\t")
                self.file_writer.write(f"{ccgp.operation_cost}\t")
                self.file_writer.write(f"{ccgp.laden_cost}\t")
                self.file_writer.write(f"{ccgp.empty_cost}\t")
                self.file_writer.write(f"{ccgp.rental_cost}\t")
                self.file_writer.write(f"{ccgp.penalty_cost}\t")
                self.file_writer.write(f"{ccgp.worst_performance}\t")
                self.file_writer.write("\n")
                self.file_writer.flush()
                
    def _experiment_test6(self, file_name: str):
        """Experiment 6: Test with different distribution types."""
        DefaultSetting.CCG_PAP_USE_SP = True
        logger.info("========================== Begin Performance Test =========================")
        logger.info("==========================" + "Experiment 6" + "==========================")
        logger.info(f"DistributionType : {DefaultSetting.DISTRIBUTION_TYPE}\n")
        
        self.file_writer.write("\n===========================================\n")
        self.file_writer.write("TimeHorizon\tObj.\t"
                             + "OC\t"
                             + "LC\t"
                             + "C\t"
                             + "RC\t"
                             + "PC\t"
                             + "WP\t"
                             + "\n")
                             
        t = self.default_time_horizon
        logger.info(f"TimeHorizon : {t}\n")
        sigma_factor_set = [1]
        
    def _experiment_test7(self, file_name: str):
        """Experiment 7: Compare mean and worst performance of different methods."""
        DefaultSetting.WHETHER_GENERATE_SAMPLES = True
        DefaultSetting.WHETHER_CALCULATE_MEAN_PERFORMANCE = True
        DefaultSetting.USE_HISTORY_SOLUTION = True
        DefaultSetting.CCG_PAP_USE_SP = True
        
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 7" + "=============================")
        
        self.file_writer.write("\n")
        self.file_writer.write("=====================================================================\n")
        self.file_writer.write("Methods\t"
                             + "DM-MeanPerformance\t"
                             + "DM-WorstPerformance\t"
                             + "BD-MeanPerformance\t"
                             + "BD-WorstPerformance\t"
                             + "CCG-MeanPerformance\t"
                             + "CCG-WorstPerformance\t"
                             + "CCG&PAP-MeanPerformance\t"
                             + "CCG&PAP-WorstPerformance\t"
                             + "\n")
                             
        DefaultSetting.write_settings(self.file_writer)
        DefaultSetting.print_settings()
        
        t = self.default_time_horizon
        DefaultSetting.USE_HISTORY_SOLUTION = False
        
        logger.info(f"TimeHorizon : {t}\n")
        logger.info(f"UncertainDegree : {self.uncertain_degree}\n")
        
        # Initialize data and parameters
        input_data = ReadData(file_name, t)
        param = Parameter()
        GenerateParameter(input_data, param, t, self.uncertain_degree)
        input_data.show_status()
        SelectPaths(input_data, param, 0.4)
        logger.info(f"Tau : {param.tau}")
        
        # Run algorithms
        dm = DetermineModel(input_data, param)
        ccgp = CCGwithPAP(input_data, param)
        
        # Write results
        self.file_writer.write(f"\nTimeHorizon : {t}\n")
        self.file_writer.write(f"UncertainDegree : {self.uncertain_degree}\n")
        self.file_writer.write(f"Tau : {param.tau}\n")
        self.file_writer.write(f"{t}\t"
                             + f"{dm.mean_performance}\t"
                             + f"{dm.worst_performance}\t"
                             + f"{ccgp.mean_performance}\t"
                             + f"{ccgp.worst_performance}\t"
                             + "\n")
        self.file_writer.write(f"{t}\t"
                             + f"{dm.mean_second_stage_cost}\t"
                             + f"{dm.worst_second_stage_cost}\t"
                             + f"{ccgp.mean_second_stage_cost}\t"
                             + f"{ccgp.worst_second_stage_cost}\t"
                             + "\n")
        self.file_writer.write("=====================================================================")
        self.file_writer.flush()
        self.file_writer.close()
        
    def _experiment_test8(self, file_name: str):
        """Experiment 8: Test SOwithBD algorithm."""
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 8" + "=============================")
        
        DefaultSetting.write_settings(self.file_writer)
        DefaultSetting.print_settings()
        
        for t in self.time_horizon_set:
            logger.info(f"TimeHorizon : {t}\n")
            logger.info(f"UncertainDegree : {self.uncertain_degree}\n")
            
            # Initialize data and parameters
            input_data = ReadData(file_name, t)
            param = Parameter()
            GenerateParameter(input_data, param, t, self.uncertain_degree)
            input_data.show_status()
            SelectPaths(input_data, param, 0.4)
            
            # Run algorithm
            so = SOwithBD(input_data, param)
            logger.info(f"SOwithBD : {so.obj_val}\t{so.solve_time}\t{so.iter}")
            
    def _experiment_test9(self, file_name: str):
        """Experiment 9: Compare BD with and without Pareto cuts."""
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 9" + "=============================")
        
        DefaultSetting.write_settings(self.file_writer)
        DefaultSetting.print_settings()
        
        for t in self.time_horizon_set:
            logger.info(f"TimeHorizon : {t}\n")
            logger.info(f"UncertainDegree : {self.uncertain_degree}\n")
            
            # Initialize data and parameters
            input_data = ReadData(file_name, t)
            param = Parameter()
            GenerateParameter(input_data, param, t, self.uncertain_degree)
            input_data.show_status()
            SelectPaths(input_data, param, 0.4)
            
            # Run algorithms
            bdpa = BDwithPareto(input_data, param)
            bd = BendersDecomposition(input_data, param)
            
            logger.info(f"BD with Pareto Cut: \t{bdpa.obj_val}\t{bdpa.solve_time}\t{bdpa.iter}")
            logger.info(f"BD : \t{bd.obj_val}\t{bd.solve_time}\t{bd.iter}")
            
    def _experiment_test10(self, file_name: str):
        """Experiment 10: Test with different initial container percentages."""
        logger.info("========================== Begin Performance Test =========================")
        logger.info("=============================" + "Experiment 10" + "=============================")
        
        fold_container_percent_sets = [0.1, 0.25, 0.5, 0.75, 1.0]
        
        for fcp in fold_container_percent_sets:
            logger.info(f"Fold Initial Container Percent: {fcp}")
            DefaultSetting.DEFAULT_FOLD_CONTAINER_PERCENT = fcp
            
            for t in self.time_horizon_set:
                # Initialize data and parameters
                input_data = ReadData(file_name, t)
                param = Parameter()
                GenerateParameter(input_data, param, t, self.uncertain_degree)
                input_data.show_status()
                
                # Run algorithms
                DetermineModel(input_data, param)
                SOwithBD(input_data, param)
                
                try:
                    SOwithSAA(input_data, param)
                except Exception as e:
                    logger.error("Error in solve SAA")
                    
                logger.info("=====================================================================")

DefaultSetting.VESSEL_CAPACITY_RANGE = [100, 200]
DefaultSetting.VESSEL_OPERATION_COST = 1000
DefaultSetting.EMPTY_CONTAINER_COST_RATIO = 0.5
DefaultSetting.PENALTY_COST_RATIO = 0.1
DefaultSetting.CONTAINER_RENTAL_COST = 100
DefaultSetting.INITIAL_EMPTY_CONTAINER_RATIO = 0.2
DefaultSetting.TURNOVER_TIME_RATIO = 0.1
DefaultSetting.DEMAND_MEAN_RATIO = 0.1
DefaultSetting.DEMAND_VARIATION_RATIO = 0.2 