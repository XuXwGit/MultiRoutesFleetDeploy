import logging
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from multi.algos.base_algo_frame import BaseAlgoFrame
from multi.model.primal.master_problem import MasterProblem
from multi.model.primal.sub_problem import SubProblem
from multi.utils.input_data import InputData
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.model.primal.determine_model import DetermineModel
from multi.model.dual.dual_sub_problem import DualSubProblem

logger = logging.getLogger(__name__)

class AlgoFrame(BaseAlgoFrame):
    """
    算法框架类
    
    继承自BaseAlgoFrame,实现基本的算法框架
    
    主要功能:
    1. 维护主问题模型和子问题模型
    2. 实现基本的迭代求解流程
    3. 记录求解过程中的各种指标
    4. 提供结果输出功能
    """
    
    def __init__(self):
        """
        初始化算法框架
        """
        super().__init__()
        
        # 算法参数
        self.tau: int = 0
        self.algo: str = ""
        self.algo_id: str = ""
        self.file_writer = None
        
        # 模型
        self.dsp: DualSubProblem = None
        self.mp: MasterProblem = None
        
        # 时间
        self.start: float = 0
        
        # 解相关
        self.solution: List[List[int]] = []
        self.solution_pool: set = set()
        self.scenario_pool: set = set()
        self.sce: List = []
        self.master_obj: List[float] = [0.0] * (DefaultSetting.MAX_ITERATION_NUM + 1)
        self.sub_obj: List[float] = [0.0] * (DefaultSetting.MAX_ITERATION_NUM + 1)
        self.v_value: List[List[int]] = []
        
        # 结果指标
        self.worst_performance: float = 0.0
        self.mean_performance: float = 0.0
        self.worst_second_stage_cost: float = 0.0
        self.mean_second_stage_cost: float = 0.0
        
        # 成本
        self.total_cost: float = 0.0
        self.operation_cost: float = 0.0
        self.rental_cost: float = 0.0
        self.laden_cost: float = 0.0
        self.empty_cost: float = 0.0
        self.penalty_cost: float = 0.0
        
        # 求解状态
        self.solve_status: bool = False
        self.total_time: float = 0.0
        self.build_model_time: float = 0.0
    
    def frame(self):
        """
        执行算法框架
        """
        try:
            self.initialize()

            if DefaultSetting.WHETHER_ADD_INITIALIZE_SCE:
                self.initialize_sce(self.sce)

            build_model_time = self.initial_model()

            self.print_iter_title(self.file_writer, build_model_time)
            self.print_iteration(self.file_writer, 
                               self.lower[self.iteration], 
                               self.upper[self.iteration],
                               0, 0, 0,
                               "--", 0,
                               "--", 0)
            
            flag = 0
            start0 = time.time() * 1000
            while (self.upper_bound - self.lower_bound > DefaultSetting.BOUND_GAP_LIMIT
                   and flag == 0
                   and self.iteration < DefaultSetting.MAX_ITERATION_NUM
                   and (time.time() * 1000 - start0) / 1000 < DefaultSetting.MAX_ITERATION_TIME):
                
                start1 = time.time() * 1000
                self.mp.solve_model()
                end1 = time.time() * 1000

                if not self.add_solution_pool(self.mp.get_solution()):
                    flag = 1
                    break

                self.dsp.change_objective_v_vars_coefficients(self.mp.get_v_var_value())
                start2 = time.time() * 1000
                self.dsp.solve_model()
                end2 = time.time() * 1000

                self.update_bound_and_mp()

                self.iteration += 1
                self.upper[self.iteration] = self.upper_bound
                self.lower[self.iteration] = self.lower_bound

                self.print_iteration(self.file_writer, 
                                   self.lower[self.iteration], 
                                   self.upper[self.iteration],
                                   end2 - start2, 
                                   end1 - start1, 
                                   time.time() * 1000 - start0,
                                   self.dsp.get_solve_status_string(), 
                                   self.dsp.get_obj_gap(),
                                   self.mp.get_solve_status_string(), 
                                   self.mp.get_obj_gap())
            
            if flag == 1:
                logger.info("MP solution duplicate")
            elif flag == 2:
                logger.info("Worse case duplicate")
            elif flag == 3:
                logger.info("DSP solution infeasible")
            
            self.set_algo_result()
            self.end()
            
        except Exception as e:
            logger.error(f"Algorithm execution failed: {str(e)}")
            self.solve_status = False

    def initialize(self):
        """
        初始化算法框架
        """
        logger.info(f"==============={self.algo}================")
        self.create_file_writer(f"{self.algo_id}.txt")

        self.sce = []

        self.upper[0] = self.upper_bound
        self.lower[0] = self.lower_bound

        self.solution_pool = set()
        self.scenario_pool = set()

        self.start = time.time() * 1000

        
    def initialize_sce(self, sce: List):
        """
        初始化场景
        """
        sss = [0.0] * len(self.in_data.request_set)

        # beta = min{k , I/k}
        beta = len(self.p.demand) / float(self.tau) if float(self.tau) > len(self.p.demand) / float(self.tau) else float(self.tau)

        v = float(self.tau) / len(self.p.demand) * (1 / (len(self.p.demand) ** 0.5))
        for i in range(len(self.p.demand)):
            sss[i] = beta * v

        sce.append(Scenario(sss))
        
    def initial_model(self) -> float:
        """
        初始化模型
        """
        start = time.time() * 1000

        self.dsp = DualSubProblem(self.in_data, self.p, self.tau)
        self.mp = MasterProblem(self.in_data, self.p)

        if DefaultSetting.WHETHER_ADD_INITIALIZE_SCE:
            self.mp.add_scene(self.sce[0])

        if DefaultSetting.WHETHER_SET_INITIAL_SOLUTION:
            dm = DetermineModel(self.in_data, self.p)
            self.mp.set_initial_solution(dm.get_v_var_value())

        return time.time() * 1000 - start
        
    def _initialize_models(self):
        """
        初始化模型
        """
        # 初始化主问题模型
        self.mp = MasterProblem(self.in_data, self.p)
        self.mp.build_model()
        
        # 初始化子问题模型
        self.dsp = DualSubProblem(self.in_data, self.p)
        self.dsp.build_model()

    def update_bound_and_mp(self):
        """
        更新下界和主问题
        """
        if self.mp.obj_val > self.lower_bound:
            self.lower_bound = self.mp.obj_val

        if self.dsp.obj_val + self.mp.operation_cost < self.upper_bound:
            self.upper_bound = self.dsp.obj_val + self.mp.operation_cost
            self.mp.add_optimality_cut(self.dsp.get_constant_item(), self.dsp.get_beta_value())

    def _set_algo_results(self):
        """
        获取最终结果
        """
        # 获取目标函数值
        self.obj = self.mp.obj_val
        
        # 获取各种成本
        self.laden_cost = self.mp.laden_cost
        self.empty_cost = self.mp.empty_cost
        self.penalty_cost = self.mp.penalty_cost
        self.rental_cost = self.mp.rental_cost
    
    def _output_results(self):
        """
        输出结果
        """
        logger.info("Algorithm execution completed")
        logger.info(f"Solve status: {'Success' if self.solve_status else 'Failed'}")
        logger.info(f"Total time: {self.total_time:.2f}s")
        logger.info(f"Build model time: {self.build_model_time:.2f}s")
        logger.info(f"Final gap: {self.gap:.4f}")
        logger.info(f"Final objective value: {self.obj:.2f}")
        logger.info(f"Laden cost: {self.laden_cost:.2f}")
        logger.info(f"Empty cost: {self.empty_cost:.2f}")
        logger.info(f"Penalty cost: {self.penalty_cost:.2f}")
        logger.info(f"Rental cost: {self.rental_cost:.2f}")

    def create_file_writer(self, file_name: str):
        """
        创建文件写入器
        """
        log_path = DefaultSetting.ROOT_PATH + DefaultSetting.ALGO_LOG_PATH

        import os
        os.makedirs(log_path, exist_ok=True)

        file_path = os.path.join(log_path, file_name)
        if not os.path.exists(file_path):
            open(file_path, 'a').close()

        self.file_writer = open(file_path, 'a')
        DefaultSetting.write_settings(self.file_writer)
        self.file_writer.write("=====================================================================\n")
        self.in_data.write_status(self.file_writer)

    def calculate_mean_performance(self):
        """
        计算平均性能
        """
        logger.info("Calculating Mean Performance ...")
        if DefaultSetting.USE_HISTORY_SOLUTION:
            if self.in_data.history_solution_set.get(self.algo_id) is not None:
                self.calculate_sample_mean_performance(self.p.solution_to_v_value(
                    self.in_data.history_solution_set.get(self.algo_id)))
        else:
            self.calculate_sample_mean_performance(self.mp.get_v_var_value())

        self.file_writer.write(f"MeanPerformance = {self.mean_performance}\n")
        self.file_writer.write(f"WorstPerformance = {self.worst_performance}\n")
        self.file_writer.write(f"WorstSecondStageCost = {self.worst_second_stage_cost}\n")
        self.file_writer.write(f"MeanSecondStageCost = {self.mean_second_stage_cost}\n")
        self.file_writer.write(f"AlgoObjVal = {self.obj_val}\n")
        self.file_writer.flush()
        
        logger.info(f"MeanPerformance = {self.mean_performance}")
        logger.info(f"WorstPerformance = {self.worst_performance}")
        logger.info(f"WorstSecondStageCost = {self.worst_second_stage_cost}")
        logger.info(f"MeanSecondStageCost = {self.mean_second_stage_cost}")
        logger.info(f"AlgoObjVal = {self.obj_val}")

    def add_solution_pool(self, solution) -> bool:
        """
        添加解到解池
        """
        if solution in self.solution_pool:
            return False
        else:
            self.solution_pool.add(solution)
            return True

    def add_scenario_pool(self, scenario) -> bool:
        """
        添加场景到场景池
        
        Args:
            scenario: 场景
            
        Returns:
            bool: 是否添加成功
        """
        if scenario in self.scenario_pool:
            return False
        else:
            self.scenario_pool.add(scenario)
            return True

    def set_algo_result(self):
        """
        设置算法结果
        """
        self.solve_time = time.time() - self.start
        self.obj = self.upper_bound
        self.iter = self.iteration
        self.v_value = self.mp.get_v_var_value()
        self.gap = (self.upper_bound - self.lower_bound) / self.lower_bound
        self.solution = self.mp.get_v_var_value()
        self.write_solution(self.mp.get_v_var_value(), self.file_writer)
        
        if DefaultSetting.WHETHER_PRINT_PROCESS:
            self.print_solution(self.v_value)
            
        if DefaultSetting.WHETHER_CALCULATE_MEAN_PERFORMANCE:
            self.calculate_mean_performance()

    def end(self):
        """
        结束算法
        """
        if DefaultSetting.WHETHER_PRINT_PROCESS or DefaultSetting.WHETHER_PRINT_ITERATION:
            logger.info(f"{self.algo} Objective = {self.obj_val:.2f}")
            logger.info(f"{self.algo} SolveTime = {self.solve_time}ms")
            logger.info("==================================")
            
        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            self.file_writer.write(f"{self.algo} Objective = {self.obj_val}\n")
            self.file_writer.write(f"{self.algo} SolveTime = {self.solve_time}ms\n")
            self.file_writer.write("==================================")
            
        self.file_writer.close()
        
        self.end_model()

    def end_model(self):
        """
        结束模型
        """
        self.mp.end()
        self.dsp.end()

    def calculate_sample_mean_performance(self, v_value) -> float:
        """
        计算样本平均性能
        
        Args:
            v_value: 变量值
            
        Returns:
            float: 平均性能
        """
        filename = (f"{self.algo}-R{len(self.in_data.ship_route_set)}"
                   f"-T{self.p.time_horizon}"
                   f"-{DefaultSetting.FLEET_TYPE}"
                   f"-Tau{self.p.tau}"
                   f"-U{self.p.uncertain_degree}"
                   f"-S{DefaultSetting.RANDOM_SEED}"
                   f"-SampleTestResult.txt")
                   
        file_path = os.path.join(DefaultSetting.ROOT_PATH, DefaultSetting.ALGO_LOG_PATH, filename)
        
        with open(file_path, 'w') as file_writer:
            file_writer.write("Sample\tOperationCost\tTotalTransCost\tLadenCost\tEmptyCost\tRentalCost\tPenaltyCost\tTotalCost\n")
            
            mp_operation_cost = self.p.get_operation_cost(v_value)
            
            sample_sub_opera_costs = [0] * DefaultSetting.NUM_SAMPLE_SCENES
            sample_laden_costs = [0] * DefaultSetting.NUM_SAMPLE_SCENES
            sample_empty_costs = [0] * DefaultSetting.NUM_SAMPLE_SCENES
            sample_rental_costs = [0] * DefaultSetting.NUM_SAMPLE_SCENES
            sample_penalty_costs = [0] * DefaultSetting.NUM_SAMPLE_SCENES
            
            sum_sub_opera_costs = 0
            worst_total_cost = 0
            worst_second_cost = 0
            
            sp = SubProblem(self.in_data, self.p, v_value)
            
            for sce in range(DefaultSetting.NUM_SAMPLE_SCENES):
                sp.change_demand_constraint_coefficients(self.p.get_sample_scenes()[sce])
                sp.solve_model()
                
                sample_sub_opera_costs[sce] = sp.total_cost
                sample_laden_costs[sce] = sp.laden_cost
                sample_empty_costs[sce] = sp.empty_cost
                sample_rental_costs[sce] = sp.rental_cost
                sample_penalty_costs[sce] = sp.penalty_cost
                
                sum_sub_opera_costs += sp.total_cost
                if (mp_operation_cost + sample_sub_opera_costs[sce]) > worst_total_cost:
                    worst_total_cost = mp_operation_cost + sample_sub_opera_costs[sce]
                    worst_second_cost = sample_sub_opera_costs[sce]
                    
                DefaultSetting.draw_progress_bar((sce) * 100 / DefaultSetting.NUM_SAMPLE_SCENES)
                
                file_writer.write(f"{sce}\t{mp_operation_cost}\t"
                                f"{sample_sub_opera_costs[sce]}\t"
                                f"{sample_laden_costs[sce]}\t"
                                f"{sample_empty_costs[sce]}\t"
                                f"{sample_rental_costs[sce]}\t"
                                f"{sample_penalty_costs[sce]}\t"
                                f"{mp_operation_cost + sample_sub_opera_costs[sce]}\n")
                file_writer.flush()
                
            self.worst_performance = worst_total_cost
            self.worst_second_stage_cost = worst_second_cost
            self.mean_performance = mp_operation_cost + sum_sub_opera_costs / DefaultSetting.NUM_SAMPLE_SCENES
            self.mean_second_stage_cost = sum_sub_opera_costs / DefaultSetting.NUM_SAMPLE_SCENES
            
        return mp_operation_cost + sum_sub_opera_costs / DefaultSetting.NUM_SAMPLE_SCENES

    def print_iter_title(self, file_writer, build_model_time):
        """
        打印迭代标题
        
        Args:
            file_writer: 文件写入器
            build_model_time: 模型构建时间
        """
        if DefaultSetting.WHETHER_PRINT_PROCESS or DefaultSetting.WHETHER_PRINT_ITERATION:
            logger.info(f"BuildModelTime = {build_model_time:.2f}")
            logger.info("k\t\tLB\t\tUB\t\tDSP-SolveTime(s)\t\tMP-SolveTime(s)\t\tTotal Time\t\tDSP-Status\t\tMP-Status")
            
        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            file_writer.write("k\t\tLB\t\tUB\t\tDSP-SolveTime(ms)\t\tMP-SolveTime(ms)\t\tTotal Time(ms)\t\tDSP-Status(Gap)\t\tMP-Status(Gap)\n")
            file_writer.flush()

    def print_iteration_detailed(self, file_writer, lb, ub, dsp_time, mp_time, total_time,
                               dsp_solve_status_string, dsp_mip_gap,
                               mp_solve_status_string, mp_mip_gap):
        """
        打印详细迭代信息
        
        Args:
            file_writer: 文件写入器
            lb: 下界
            ub: 上界
            dsp_time: DSP求解时间
            mp_time: MP求解时间
            total_time: 总时间
            dsp_solve_status_string: DSP求解状态
            dsp_mip_gap: DSP MIP间隙
            mp_solve_status_string: MP求解状态
            mp_mip_gap: MP MIP间隙
        """
        if DefaultSetting.WHETHER_PRINT_PROCESS or DefaultSetting.WHETHER_PRINT_ITERATION:
            logger.info(f"{self.iteration}\t\t{lb:.2f}\t\t{ub:.2f}\t\t{dsp_time:.2f}\t\t{mp_time:.2f}\t\t{total_time:.2f}\t\t"
                       f"{dsp_solve_status_string}({dsp_mip_gap:.4f})\t\t{mp_solve_status_string}({mp_mip_gap:.4f})")
            
        if DefaultSetting.WHETHER_WRITE_FILE_LOG:
            file_writer.write(f"{self.iteration}\t\t{lb:.2f}\t\t{ub:.2f}\t\t{dsp_time:.2f}\t\t{mp_time:.2f}\t\t{total_time:.2f}\t\t"
                            f"{dsp_solve_status_string}({dsp_mip_gap:.4f})\t\t{mp_solve_status_string}({mp_mip_gap:.4f})\n")
            file_writer.flush()

    def print_solution(self, v_value):
        """
        打印解
        
        Args:
            v_value: 变量值
        """
        logger.info("VesselType Decision vVar : ")
        for r in range(len(self.p.shipping_route_set)):
            print(self.p.shipping_route_set[r], end=":")
            
            if DefaultSetting.FLEET_TYPE == "Homo":
                for h in range(len(self.p.vessel_set)):
                    if v_value[h][r] != 0:
                        print(f"{self.p.vessel_set[h]}\t", end="")
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for w in range(len(self.p.vessel_path_set)):
                    if self.p.ship_route_and_vessel_path[r][w] != 1:
                        continue
                    for h in range(len(self.p.vessel_set)):
                        if v_value[h][w] != 0 and self.p.ship_route_and_vessel_path[r][w] == 1:
                            print(f"{self.p.vessel_path_set[w]}({self.p.vessel_set[h]})\t", end="")
            else:
                logger.info("Error in Fleet type!")

    def write_solution(self, v_value, file_writer):
        """
        写入解
        
        Args:
            v_value: 变量值
            file_writer: 文件写入器
        """
        file_writer.write("VesselType Decision vVar : \n")
        for r in range(len(self.p.shipping_route_set)):
            file_writer.write(f"{self.p.shipping_route_set[r]}: ")
            
            if DefaultSetting.FLEET_TYPE == "Homo":
                for h in range(len(self.p.vessel_set)):
                    if v_value[h][r] != 0:
                        file_writer.write(f"{self.p.vessel_set[h]}\t")
            elif DefaultSetting.FLEET_TYPE == "Hetero":
                for w in range(len(self.p.vessel_path_set)):
                    if self.p.ship_route_and_vessel_path[r][w] != 1:
                        continue
                    for h in range(len(self.p.vessel_set)):
                        if v_value[h][w] != 0 and self.p.ship_route_and_vessel_path[r][w] == 1:
                            file_writer.write(f"{self.p.vessel_path_set[w]}({self.p.vessel_set[h]})\t")
                file_writer.write("\n")
            else:
                logger.info("Error in Fleet type!")
        file_writer.write("\n")

    def diff_vessel_value(self, old_v_var_value, new_v_var_value) -> float:
        """
        计算船舶变量值的差异
        
        Args:
            old_v_var_value: 旧的变量值
            new_v_var_value: 新的变量值
            
        Returns:
            float: 差异值
        """
        diff = 0
        for h in range(len(old_v_var_value)):
            for w in range(len(old_v_var_value[0])):
                diff += abs(new_v_var_value[h][w] - old_v_var_value[h][w])
        return diff

    def update_vvv(self, vvv, new_v_var_value):
        """
        更新变量值
        
        Args:
            vvv: 变量值
            new_v_var_value: 新的变量值
            
        Returns:
            list: 更新后的变量值
        """
        for h in range(len(new_v_var_value)):
            for w in range(len(new_v_var_value[0])):
                vvv[h][w] = new_v_var_value[h][w]
        return vvv 