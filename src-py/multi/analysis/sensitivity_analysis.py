import logging
from pathlib import Path
from typing import List

from multi.algos.ccg import CCGwithPAP
from multi.utils.input_data import InputData
from multi.utils.read_data import ReadData
from multi.entity.port import Port
from multi.utils.default_setting import DefaultSetting
from multi.model.parameter import Parameter, GenerateParameter
from multi.utils.select_paths import SelectPaths

logger = logging.getLogger(__name__)

class SensitivityAnalysis(DefaultSetting):
    default_time_horizon: int
    uncertain_degree_set: List[float] = [0.005, 0.015, 0.025, 0.035, 0.045, 0.055, 0.065, 0.075, 0.085, 0.095]
    container_path_cost_set: List[float] = [0.80, 0.825, 0.85, 0.875, 0.90, 0.925, 0.95, 0.975, 
        1.025, 1.05, 1.0725, 1.10, 1.125, 1.15, 1.175, 1.20]
    rental_container_cost_set: List[float] = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00,
        1.05, 1.10, 1.15, 1.20, 1.25, 1.30, 1.35, 1.40]
    penalty_cost_set: List[float] = [1.025, 1.075, 1.125, 1.175]
    turn_over_time_set: List[int] = list(range(29))
    initial_container_set: List[int] = list(range(43))
    time_horizon_set: List[int] = [60, 75, 90, 105, 120, 135, 150, 165, 180]

    def __init__(self, instance: int, analysis_type: int, algo: str):
        super().__init__()
        self.algo = algo
        self.file_writer = None

        try:
            if DefaultSetting.WHETHER_WRITE_FILE_LOG:
                result_path = Path(DefaultSetting.ROOT_PATH) / DefaultSetting.TEST_RESULT_PATH
                file_path = result_path / f"SensitivityAnalysis{instance}-{analysis_type}-{self.random_seed}.txt"
                file_path.parent.mkdir(parents=True, exist_ok=True)
                self.file_writer = open(file_path, "a", encoding="utf-8")

            data_path_map = {
                1: ("data1/", 70),
                2: ("data2/", 90),
                3: ("data3/", 90)
            }
            data_dir, self.default_time_horizon = data_path_map.get(instance, ("data1/", 70))
            
            input_data = InputData()
            ReadData(Path(DefaultSetting.DATA_PATH) / data_dir, input_data, self.default_time_horizon)
            input_data.show_status()

            logger.info("Experiment %d:", analysis_type)
            analysis_methods = {
                1: self.vary_turn_over_time,
                2: self.vary_penalty_cost,
                3: self.vary_rental_cost
            }
            analysis_methods.get(analysis_type, lambda x: None)(input_data)

        except Exception as e:
            logger.exception("Error occurred in sensitivity analysis")
            if self.file_writer:
                self.file_writer.close()
            raise

    def vary_uncertain_degree(self, input_data: InputData) -> None:
        logger.info("=========Varying UncertainDegree from 0 to 0.20==========")
        if self.file_writer:
            self.file_writer.write("=========Varying UncertainDegree from 0 to 0.20==========\n")

        for ud in self.uncertain_degree_set:
            logger.info("uncertain_degree = %f", ud)
            param = Parameter()
            GenerateParameter(param, input_data, self.default_time_horizon, ud)

            ccg = CCGwithPAP(input_data, param, int(len(input_data.request_set)**0.5))

            log_template = (
                "UD\tLPC\tEPC\tLC+EC\tRC\tPC\tOC\tTC\n"
                f"{ud:.3f}\t{ccg.laden_cost:.2f}\t{ccg.empty_cost:.2f}\t"
                f"{ccg.empty_cost + ccg.laden_cost:.2f}\t{ccg.rental_cost:.2f}\t"
                f"{ccg.penalty_cost:.2f}\t{ccg.operation_cost:.2f}\t{ccg.total_cost:.2f}"
            )
            logger.info(log_template)

            if self.file_writer:
                self.file_writer.write(log_template + "\n")

    def vary_load_discharge_cost(self, input_data: InputData) -> None:
        logger.info("=========Varying Unit L&D&T Cost========")
        for coeff in self.container_path_cost_set:
            logger.info("Unit ContainerPath Cost = %f", coeff)
            param = Parameter()
            GenerateParameter(param, input_data, self.default_time_horizon, self.uncertain_degree)
            
            # Update path costs
            param.laden_path_cost = [
                path.path_cost * coeff + demurrage 
                for path, demurrage in zip(input_data.container_paths, param.laden_path_demurrage_cost)
            ]
            param.empty_path_cost = [
                path.path_cost * 0.5 * coeff + demurrage 
                for path, demurrage in zip(input_data.container_paths, param.empty_path_demurrage_cost)
            ]

            ccg = CCGwithPAP(input_data, param)
            logger.info(
                "DemurrageCostCoeff\tLPC\tEPC\tLC+EC\tRC\tPC\tOC\tTC\n"
                f"{coeff:.2f}\t{ccg.laden_cost:.2f}\t{ccg.empty_cost:.2f}\t"
                f"{ccg.empty_cost + ccg.laden_cost:.2f}\t{ccg.rental_cost:.2f}\t"
                f"{ccg.penalty_cost:.2f}\t{ccg.operation_cost:.2f}\t{ccg.total_cost:.2f}"
            )

    def vary_rental_cost(self, input_data: InputData) -> None:
        logger.info("=========Varying Unit Container Rental Cost (0.5~1.5)x20========")
        if self.file_writer:
            self.file_writer.write("=========Varying Unit Container Rental Cost (0.5~1.5)x20========\n")

        for coeff in self.rental_container_cost_set:
            logger.info("RentalCost = %f", coeff)
            param = Parameter()
            GenerateParameter(param, input_data, self.default_time_horizon, self.uncertain_degree)
            SelectPaths(input_data, param, 0.4).select()
            
            param.change_rental_cost(coeff)
            ccg = CCGwithPAP(input_data, param)

            log_data = (
                f"{coeff:.2f}\t{ccg.laden_cost:.2f}\t{ccg.empty_cost:.2f}\t"
                f"{ccg.empty_cost + ccg.laden_cost:.2f}\t{ccg.rental_cost:.2f}\t"
                f"{ccg.penalty_cost:.2f}\t{ccg.operation_cost:.2f}\t{ccg.total_cost:.2f}"
            )
            logger.info("RentalCostCoeff\tLPC\tEPC\tLC+EC\tRC\tPC\tOC\tTC\n%s", log_data)
            
            if self.file_writer:
                self.file_writer.write(log_data + "\n")

    def vary_penalty_cost(self, input_data: InputData) -> None:
        logger.info("=========Varying Unit Demand Penalty Cost (80%~120%)=========")
        if self.file_writer:
            self.file_writer.write("=========Varying Unit Demand Penalty Cost (80%~120%)=========\n")

        for coeff in self.penalty_cost_set:
            logger.info("PenaltyCostCoeff = %f", coeff)
            param = Parameter()
            GenerateParameter(param, input_data, self.default_time_horizon, self.uncertain_degree)
            SelectPaths(input_data, param, 0.4).select()
            
            param.change_penalty_cost_for_demand(coeff)
            ccg = CCGwithPAP(input_data, param)

            log_data = (
                f"{coeff:.2f}\t{ccg.laden_cost:.2f}\t{ccg.empty_cost:.2f}\t"
                f"{ccg.empty_cost + ccg.laden_cost:.2f}\t{ccg.rental_cost:.2f}\t"
                f"{ccg.penalty_cost:.2f}\t{ccg.operation_cost:.2f}\t{ccg.total_cost:.2f}"
            )
            logger.info("PenaltyCostCoeff\tLPC\tEPC\tLC+EC\tRC\tPC\tOC\tTC\n%s", log_data)

    def vary_turn_over_time(self, input_data: InputData) -> None:
        logger.info("=========Varying TurnOverTime (0~28) =========")
        for time in self.turn_over_time_set:
            logger.info("******************** TurnOverTime = %d ********************", time)
            param = Parameter()
            GenerateParameter(param, input_data, self.default_time_horizon, self.uncertain_degree)
            SelectPaths(input_data, param, 0.4).select()
            
            param.turn_over_time = time
            ccg = CCGwithPAP(input_data, param)

            log_data = (
                f"{time}\t{ccg.laden_cost:.2f}\t{ccg.empty_cost:.2f}\t"
                f"{ccg.empty_cost + ccg.laden_cost:.2f}\t{ccg.rental_cost:.2f}\t"
                f"{ccg.penalty_cost:.2f}\t{ccg.operation_cost:.2f}\t{ccg.total_cost:.2f}"
            )
            logger.info("turnOverTime\tLPC\tEPC\tLC+EC\tRC\tPC\tOC\tTC\n%s", log_data)

    def __del__(self):
        if self.file_writer:
            self.file_writer.close()