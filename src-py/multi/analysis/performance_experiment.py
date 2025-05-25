import logging
from pathlib import Path
from typing import Dict, List
from multi.data.input_data import InputData, ReadInputData
from multi.model.parameter import Parameter, GenerateParameter
from multi.utils.select_paths import SelectPaths
from multi.algos import CCG, BD, CCGwithPAP, DetermineModel

logger = logging.getLogger(__name__)

class PerformanceExperiment:
    def __init__(self, instance: int, exp_type: int):
        self.instance = instance
        self.exp_type = exp_type
        self.file_writer = None
        self.time_horizon_set: List[int] = []
        self.default_time_horizon: int = 0
        self.uncertain_degree: float = 0.05
        self.data_path = Path(f"data/data{instance}")

        # 初始化结果文件
        result_file = Path(f"results/Performance_{instance}-{exp_type}.txt")
        result_file.parent.mkdir(parents=True, exist_ok=True)
        self.file_writer = result_file.open('a', encoding='utf-8')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file_writer:
            self.file_writer.close()

    def run(self):
        """执行实验主入口"""
        self._configure_experiment()
        try:
            if self.exp_type == 1:
                self._run_experiment1()
            elif self.exp_type == 2:
                self._run_experiment2()
            # 其他实验类型处理...
        except Exception as e:
            logger.error(f"实验执行失败: {str(e)}", exc_info=True)
        finally:
            if self.file_writer:
                self.file_writer.close()

    def _configure_experiment(self):
        """配置实验参数"""
        config_map = {
            1: ([56, 63, 70, 77, 84, 91], 70),
            2: ([90], 90),
            3: ([90, 105, 120, 135, 150, 165, 180], 180)
        }
        self.time_horizon_set, self.default_time_horizon = config_map.get(
            self.instance, ([], 0)
        )

    def _run_experiment1(self):
        """实验1：算法性能对比"""
        logger.info("======== 开始算法性能对比实验 ========")
        for t in self.time_horizon_set:
            try:
                # 数据初始化
                input_data = InputData()
                ReadInputData.load(input_data, self.data_path, t)
                
                # 参数生成
                params = Parameter()
                GenerateParameter.generate(params, input_data, t, self.uncertain_degree)
                
                # 路径选择
                SelectPaths(input_data, params).select_paths(0.4)

                # 算法执行
                algorithms = {
                    "CCG": CCG(input_data, params),
                    "CCG&PAP": CCGwithPAP(input_data, params),
                    "BD": BD(input_data, params),
                    "Determine": DetermineModel(input_data, params)
                }
                
                # 运行并记录结果
                self._execute_and_record(t, input_data, algorithms)

            except Exception as e:
                logger.error(f"时间跨度{t}实验失败: {str(e)}")
                continue

    def _execute_and_record(self, t: int, input_data: InputData, algorithms: Dict):
        """执行算法并记录结果"""
        # 运行所有算法
        results = {}
        for name, algo in algorithms.items():
            try:
                results[name] = algo.solve()
                algo.validate_solution()
                algo.save_results(Path(f"results/{name}_T{t}.txt"))  # 保存详细结果
            except Exception as e:
                logger.error(f"{name}算法执行失败: {str(e)}")
                results[name] = None

        # 控制台输出
        logger.info(f"\n=== 时间跨度: {t} ===")
        logger.info("算法\t求解时间\t目标值\t迭代次数")
        for name, res in results.items():
            if res:
                logger.info(f"{name}\t{res.solve_time:.2f}\t{res.objective_value:.2f}\t{res.iterations}")

        # 文件记录
        if self.file_writer:
            self.file_writer.write(f"\n=== 时间跨度: {t} ===\n")
            input_data.write_status(self.file_writer)
            
            self.file_writer.write("算法,求解时间,目标值,迭代次数\n")
            for name, res in results.items():
                if res:
                    self.file_writer.write(
                        f"{name},{res.solve_time:.2f},{res.objective_value:.2f},{res.iterations}\n"
                    )
            self.file_writer.flush()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("experiment.log"),
            logging.StreamHandler()
        ]
    )
    
    with PerformanceExperiment(instance=1, exp_type=1) as exp:
        exp.run()