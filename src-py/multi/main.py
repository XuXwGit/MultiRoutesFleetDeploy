import logging
import random
import sys
from typing import Optional
from multiprocessing import cpu_count

from multi.test.performance_experiment import PerformanceExperiment
from multi.test.sensitivity_analysis import SensitivityAnalysis
from multi.utils.default_setting import DefaultSetting

logger = logging.getLogger(__name__)

def main():
    """Main entry point of the program.
    
    Command line arguments:
    1. instance: Test instance number (1: small scale, 2: large scale, 3: middle scale)
    2. experiment: Experiment type number
    3. root_path: Root path for data and results (optional)
    4. mip_gap_limit: MIP gap limit (optional)
    5. random_seed: Random seed for reproducibility (optional)
    6. budget_coefficient: Budget coefficient (optional)
    7. uncertain_degree: Default uncertain degree (optional)
    8. flag: Experiment type flag - P for Performance Test, S for Sensitivity Analysis (optional)
    """
    logger.info(f"Instance: {sys.argv[1]}")
    DefaultSetting.CASE_PATH = f"{sys.argv[1]}/"
    logger.info(f"Experiment: {sys.argv[2]}")
    
    instance = int(sys.argv[1])
    experiment = int(sys.argv[2])
    
    # Set root path if provided
    if len(sys.argv) >= 4 and sys.argv[3] != "-":
        DefaultSetting.ROOT_PATH = sys.argv[3]
        logger.info(f"RootPath: {DefaultSetting.ROOT_PATH}")
        
    # Set MIP gap limit if provided
    if len(sys.argv) >= 5 and sys.argv[4] != "-":
        DefaultSetting.MIP_GAP_LIMIT = float(sys.argv[4])
        logger.info(f"MIPGapLimit: {sys.argv[4]}")
        
    # Set random seed if provided
    if len(sys.argv) >= 6:
        DefaultSetting.RANDOM_SEED = int(sys.argv[5])
        logger.info(f"Random Seed: {sys.argv[5]}")
        
    # Set budget coefficient if provided
    if len(sys.argv) >= 7:
        DefaultSetting.BUDGET_COEFFICIENT = float(sys.argv[6])
        logger.info(f"Budget Coefficient: {sys.argv[6]}")
        
    # Set uncertain degree if provided
    if len(sys.argv) >= 8:
        DefaultSetting.DEFAULT_UNCERTAIN_DEGREE = float(sys.argv[7])
        logger.info(f"Uncertain Degree: {sys.argv[7]}")
        
    # Set experiment type flag
    flag = 1  # Default to Performance Test
    if len(sys.argv) >= 9:
        if sys.argv[8] == "P":
            flag = 1
            logger.info("Numerical: Performance Test")
        elif sys.argv[8] == "S":
            flag = 2
            logger.info("Numerical: Sensitivity Analysis")
            
    # Print system information
    logger.info(f"Free Memory = {sys.getsizeof([]) >> 20}M")
    logger.info(f"Max heap Memory = {sys.maxsize >> 20}M")
    logger.info(f"Total heap Memory = {sys.getsizeof({}) >> 20}M")
    logger.info(f"Max Available Cores = {cpu_count()}")
    
    # Set random seed
    DefaultSetting.random = random.Random(DefaultSetting.RANDOM_SEED)
    logger.info(f"=============== Seed = {DefaultSetting.RANDOM_SEED}===============")
    logger.info(f"Fleet Type DefaultSetting: {DefaultSetting.FLEET_TYPE}")
    
    # Set new DefaultSetting variables
    DefaultSetting.VESSEL_CAPACITY_RANGE = [100, 200]
    DefaultSetting.VESSEL_OPERATION_COST = 1000
    DefaultSetting.EMPTY_CONTAINER_COST_RATIO = 0.5
    DefaultSetting.PENALTY_COST_RATIO = 0.1
    DefaultSetting.CONTAINER_RENTAL_COST = 100
    DefaultSetting.INITIAL_EMPTY_CONTAINER_RATIO = 0.2
    DefaultSetting.TURNOVER_TIME_RATIO = 0.1
    DefaultSetting.DEMAND_MEAN_RATIO = 0.1
    DefaultSetting.DEMAND_VARIATION_RATIO = 0.2
    
    # Run appropriate experiment
    if flag == 1:
        # Performance test
        PerformanceExperiment(instance, experiment)
    elif flag == 2:
        # Sensitivity analysis
        SensitivityAnalysis(instance, experiment, "CCG&PAP")
    else:
        logger.error("Error in Get Flag")

if __name__ == "__main__":
    main()