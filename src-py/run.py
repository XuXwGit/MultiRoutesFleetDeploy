import argparse
from multi.utils.logger_config import setup_logger
from multi.algos.benders_decomposition import BendersDecomposition
from multi.algos.benders_decomposition_with_pap import BendersDecompositionWithPAP
from multi.algos.ccg import CCG
from multi.algos.ccg_with_pap import CCGwithPAP
from multi.model.parameter import Parameter
from multi.utils.generate_parameter import GenerateParameter
from multi.utils.input_data import InputData
from multi.utils.read_data import ReadData
from multi.utils.default_setting import DefaultSetting

# 配置日志记录器
logger = setup_logger('algorithm')

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行多航线船舶调度算法')
    ## 测试用例参数
    # '1' '1' 'D:\Master\Codes\2-MultiRoutesFleetDeploy' '0.01' '42' '1.0' '0.5' 'P'
    parser.add_argument('--instance', type=str, default='1', help='测试用例名称')
    parser.add_argument('--experiment', type=int, default=1, help='试验编号')
    parser.add_argument('--root', type=str, default='D:\Master\Codes\2-MultiRoutesFleetDeploy', help='根路径')
    parser.add_argument('--mip_gap', type=float, default=0.01, help='MIP gap')
    parser.add_argument('--random_seed', type=int, default=42, help='随机数种子')
    parser.add_argument('--budget_coeff', type=float, default=0.1, help='预算系数')
    parser.add_argument('--uncertain_degree', type=float, default=0.5, help='需求波动/不确定度')
    parser.add_argument('--analysis_flag', type=str, default='P', help='分析标志(P/A)')
    ## 模型参数
    parser.add_argument('--time_horizon', type=int, default=60, help='时间窗口')
    parser.add_argument('--turn_over_time', type=int, default=14, help='空箱周转时间')
    parser.add_argument('--empty_rent_cost', type=float, default=30, help='空箱单位租赁成本')
    parser.add_argument('--penalty_coeff', type=float, default=1.0, help='违约惩罚系数')
    parser.add_argument('--port_load_cost', type=int, default=30, help='港口装载操作成本')
    parser.add_argument('--port_unload_cost', type=int, default=30, help='港口卸载操作成本')
    parser.add_argument('--port_transship_cost', type=int, default=50, help='港口转运操作成本')
    parser.add_argument('--laden_stay_cost', type=float, default=160, help='重箱港口滞留成本')
    parser.add_argument('--laden_stay_free_time', type=int, default=7, help='重箱港口滞留豁免时间')
    parser.add_argument('--empty_stay_cost', type=float, default=80, help='空箱港口滞留成本')
    parser.add_argument('--empty_stay_free_time', type=int, default=7, help='空箱港口滞留豁免时间')
    parser.add_argument('--robustness', type=int, default=100, help='鲁棒系数')
    parser.add_argument('--demand_fluctuation', type=float, default=0.1, help='需求波动')

    ## 算法参数
    parser.add_argument('--algorithm', type=str, default='bd', help='求解算法')
    parser.add_argument('--max_iter', type=int, default=100, help='最大迭代次数')
    parser.add_argument('--max_time', type=int, default=100, help='最大运行时间')
    parser.add_argument('--max_gap', type=float, default=0.01, help='MIP gap')
    parser.add_argument('--algorithm_params', type=str, default='', help='算法参数')

    ## 其他参数
    parser.add_argument('--use_db', action='store_true', help='是否使用数据库')
    parser.add_argument('--db_path', type=str, default='ships.db', help='数据库文件路径')
    parser.add_argument('--whether_print_data_status', action='store_true', help='是否打印数据状态')
    parser.add_argument('--whether_load_sample_tests', action='store_true', help='是否加载样本测试')
    parser.add_argument('--use_history_solution', action='store_true', help='是否使用历史解决方案')

    args = parser.parse_args()
    
    # 更新默认设置
    DefaultSetting.update_setting_from_args(args)
    
    try:
        logger.info("开始执行算法...")
        logger.info(f"参数设置: {args}")
        
        # 初始化输入数据
        input_data = InputData()
        
        # 读取数据
        reader = ReadData(
            path="data/",
            input_data=input_data,
            time_horizon=args.time_horizon,
            use_db=args.use_db,
            db_path=args.db_path
        )
        logger.info("数据读取完成")
        
        param = Parameter(input_data=input_data)
        GenerateParameter(input_data=input_data, param=param, time_horizon=args.time_horizon, uncertain_degree=args.demand_fluctuation)
        logger.info("参数生成完成")
        
        # 执行算法
        result = {}
        if args.algorithm == "bd":
            logger.info("使用Benders分解算法")
            bd = BendersDecomposition(input_data=input_data, param=param)
            result = bd.solve()
        elif args.algorithm == "ccg":
            logger.info("使用列生成算法")
            cp = CCG(input_data=input_data, param=param)
            result = cp.solve()
        elif args.algorithm == "bdpap":
            logger.info("使用带PAP的Benders分解算法")
            bdpap = BendersDecompositionWithPAP(input_data=input_data, param=param)
            result = bdpap.solve()
        elif args.algorithm == "ccgpap":
            logger.info("使用带PAP的列生成算法")
            ccgpap = CCGwithPAP(input_data=input_data, param=param)
            result = ccgpap.solve()
        logger.info("算法执行完成")
        
        return result
    except Exception as e:
        logger.error(f"算法执行失败: {str(e)}", exc_info=True)
        raise

if __name__ == '__main__':
    main() 