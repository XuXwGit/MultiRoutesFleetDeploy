from flask import Blueprint, request, jsonify
import logging
import sys
from pathlib import Path
from ..algorithm_interface import AlgorithmInterface
from design.core.optimizer import ShippingNetworkOptimizer
from design.core.models.network_data import NetworkData
from design.utils.config import Config
from multi.utils.parameter import Parameter
from multi.utils.default_setting import DefaultSetting

class AlgorithmAdapter:
    @staticmethod
    def execute(algorithm: str, input_data, param):
        """执行网络规划算法
        
        Args:
            algorithm: 算法类型 (保留参数，暂不使用)
            input_data: 输入数据
            param: 参数对象
            
        Returns:
            算法执行结果
            
        Raises:
            Exception: 算法执行错误
        """
        try:
            # 创建配置对象
            config = Config()
            config.P = 30  # 港口数量
            config.K = 0   # OD对数量
            config.R = 5   # 航线数量
            config.seed = 0  # 随机种子
            
            # 创建网络数据
            network_data = NetworkData(
                config=config,
                ports_data=None,  # 实际使用时应传入港口数据
                num_ports=config.P,
                num_ods=config.K,
                num_routes=config.R,
                random_seed=config.seed
            )
            
            # 初始化并运行优化器
            optimizer = ShippingNetworkOptimizer(network_data=network_data)
            optimizer.add_test("ALNS", "Cost")
            optimizer.add_test("ALNS", "Utility")
            optimizer.add_test("ALNS", "Demand")
            
            # 执行优化
            results = optimizer.optimize()
            
            # 转换结果格式以兼容前端
            return {
                'time': results.get('time', 0),
                'objective': results.get('total_cost', 0),
                'solution': {},  # 实际使用时应填充航线分配方案
                'operation_cost': results.get('operation_cost', 0),
                'laden_cost': results.get('laden_cost', 0),
                'empty_cost': results.get('empty_cost', 0),
                'rental_cost': results.get('rental_cost', 0),
                'penalty_cost': results.get('penalty_cost', 0),
                'gap': results.get('gap', 0)
            }
            
        except Exception as e:
            logging.error(f"网络规划算法执行失败: {str(e)}", exc_info=True)
            raise
from multi.utils.generate_parameter import GenerateParameter
from multi.utils.input_data import InputData
from multi.utils.read_data import ReadData
import subprocess
import os
import json
import time
from ..database import Session
from ..models import Ship, Port

# 确保可以导入src-py模块
src_py_path = str(Path(__file__).parent.parent.parent / "src-py")
if src_py_path not in sys.path:
    sys.path.append(src_py_path)

optimize_bp = Blueprint('optimize', __name__)
algorithm_interface = AlgorithmInterface()

@optimize_bp.route('/api/optimize', methods=['POST'])
def optimize():
    try:
        log_messages = []
        def log_callback(message):
            log_messages.append(message)
            logging.info(message)
        log_callback("="*50)
        log_callback("开始处理优化请求...")
        data = request.get_json()
        log_callback(f"接收到的参数: {json.dumps(data, indent=2, ensure_ascii=False)}")
        # 模型参数 - 统一前端参数命名
        model_params = {
            'time_horizon': int(data.get('time_horizon', data.get('time_window', 60))),
            'turn_over_time': int(data.get('turn_over_time', 14)),
            'robustness': int(data.get('robustness', 1)),
            'demand_fluctuation': float(data.get('demand_fluctuation', 0.1)),
            'empty_rent_cost': float(data.get('empty_rent_cost', 100)),
            'penalty_coeff': float(data.get('penalty_coeff', 1.0)),
            'port_load_cost': float(data.get('port_load_cost', 30)),
            'port_unload_cost': float(data.get('port_unload_cost', 30)),
            'port_transship_cost': float(data.get('port_transship_cost', 50)),
            'laden_stay_cost': float(data.get('laden_stay_cost', 160)),
            'laden_stay_free_time': int(data.get('laden_stay_free_time', 7)),
            'empty_stay_cost': float(data.get('empty_stay_cost', 80)),
            'empty_stay_free_time': int(data.get('empty_stay_free_time', 7)),
        }
        DefaultSetting.update_setting_from_dict(model_params)
        log_callback(f"模型参数读取完成")
        log_callback(f"模型参数: {model_params}")
        # 算法参数
        algo_params = {
            'algorithm': str(data.get('algorithm', 'bd')),
            'max_iter': int(data.get('max_iter', 100)),
            'max_time': int(data.get('max_time', 600)),
            'mip_gap': float(data.get('mip_gap', 0.01)),
        }
        DefaultSetting.update_setting_from_dict(algo_params)
        log_callback(f"算法参数读取完成")
        log_callback(f"算法参数: {algo_params}")
        try:
            log_callback("开始执行优化计算...")
            
            try:
                input_data = InputData()
                db_path = os.path.abspath("ships.db")
                log_callback(f"数据库路径: {db_path}")
                
                reader = ReadData(
                    path=os.path.abspath("data/"),
                    input_data=input_data,
                    time_horizon=model_params['time_horizon'],
                    use_db=True,
                    db_path=db_path
                )
            except Exception as e:
                log_callback(f"数据读取失败: {str(e)}")
                raise
            log_callback("数据读取完成")

            # 创建参数对象
            from multi.model.parameter import Parameter as ModelParameter
            param = ModelParameter()
            GenerateParameter(input_data=input_data,
                             param=param,
                             time_horizon=model_params['time_horizon'],
                             uncertain_degree=DefaultSetting.DEFAULT_UNCERTAIN_DEGREE)
            log_callback("参数生成完成")

            result = {}
            algo_params = algo_params or {}
            algo_str = str(algo_params.get('algorithm', 'bd')).lower()
            try:
                log_callback(f"使用{algo_str}算法")
                result = AlgorithmAdapter.execute(algo_str, input_data, param)
                log_callback(f"算法执行结果: {json.dumps(result, indent=2)}")
            except Exception as e:
                log_callback(f"算法执行失败: {str(e)}")
                logging.exception("算法执行异常")
                raise
                
            log_callback("算法执行完成")

            log_callback("优化完成！")
            log_callback(f"优化结果: {result}")

            # ========== 新增：查数据库获取名称映射 ==========
            deploy_plan = {}
            if result and hasattr(result, 'get'):
                deploy_plan = result.get('solution', {})  # 航线ID: 船舶ID
            session = Session()
            # 航线ID->名称
            from ..models import Route, Ship
            route_info = {str(r.id): r.id or f"航线{r.id}" for r in session.query(Route).all()}
            # 航线ID->港口
            ports_of_call_info = {str(r.id): r.ports_of_call or f"航线{r.id}" for r in session.query(Route).all()}
            # 船舶ID->名称
            vessel_info = {str(s.id): s.name or f"船舶{s.id}" for s in session.query(Ship).all()}
            session.close()
            # ========== END ==========


            response_data = {
                'status': 'success',
                'log': '\n'.join(log_messages),
                'result': None
            }
            
            if result and hasattr(result, 'get'):
                # 将所有结果转换为字符串格式
                result_data = {
                    'result_time': f"{result.get('time', 0):.1f}s",
                    'total_cost': f"{result.get('objective', 0):.2f}",
                    'solution': json.dumps(result.get('solution', {})),
                    'deploy_plan': json.dumps(deploy_plan),
                    'route_info': json.dumps({str(k): str(v) for k, v in route_info.items()}),
                    'ports_of_call_info': json.dumps({str(k): str(v) for k, v in ports_of_call_info.items()}),
                    'vessel_info': json.dumps({str(k): str(v) for k, v in vessel_info.items()}),
                    'oc': f"{result.get('operation_cost', 0):.2f}",
                    'lc': f"{result.get('laden_cost', 0):.2f}",
                    'ec': f"{result.get('empty_cost', 0):.2f}",
                    'rc': f"{result.get('rental_cost', 0):.2f}",
                    'pc': f"{result.get('penalty_cost', 0):.2f}",
                    'gap': f"{result.get('gap', 0):.4f}"
                }
                response_data['result'] = result_data
            
            return jsonify(response_data)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f"算法执行失败: {str(e)}",
                'log': '\n'.join(log_messages)
            }), 500
    except Exception as e:
        error_msg = f"优化过程出错: {str(e)}"
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500

@optimize_bp.route('/api/schedule', methods=['POST'])
def update_schedule():
    data = request.json
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "输入数据必须是JSON对象"
        }), 400

    try:
        # 简单验证必填字段
        required_fields = ['ships', 'ports']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"缺少必填字段: {field}"
                }), 400

        # 执行调度算法
        result = algorithm_interface.run_scheduling_algorithm(
            data={
                'ships': data['ships'],
                'ports': data['ports']
            },
            algorithm_type="schedule"
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"调度算法执行失败: {str(e)}"
        }), 500

@optimize_bp.route('/api/run_algorithm', methods=['POST'])
def run_algorithm():
    try:
        data = request.get_json()
        algorithm_params = data.get('algorithm_params', {})
        run_script = os.path.join(os.path.dirname(__file__), '..', 'src-py', 'run.py')
        cmd = ['python', run_script]
        if algorithm_params.get('use_db', False):
            cmd.append('--use_db')
        param_mapping = {
            'time_horizon': '--time_horizon',
            'turn_over_time': '--turn_over_time',
            'empty_rent_cost': '--empty_rent_cost',
            'penalty_coeff': '--penalty_coeff',
            'port_load_cost': '--port_load_cost',
            'port_unload_cost': '--port_unload_cost',
            'port_transship_cost': '--port_transship_cost',
            'laden_stay_cost': '--laden_stay_cost',
            'laden_stay_free_time': '--laden_stay_free_time',
            'empty_stay_cost': '--empty_stay_cost',
            'empty_stay_free_time': '--empty_stay_free_time',
            'robustness': '--robustness',
            'demand_fluctuation': '--demand_fluctuation',
            'algorithm': '--algorithm',
            'max_iter': '--max_iter',
            'max_time': '--max_time',
            'mip_gap': '--mip_gap',
        }
        for param, value in algorithm_params.items():
            if param in param_mapping and value is not None:
                cmd.extend([param_mapping[param], str(value)])
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': '算法执行成功',
                'output': stdout
            })
        else:
            return jsonify({
                'status': 'error',
                'message': '算法执行失败',
                'error': stderr
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误',
            'error': str(e)
        }), 500 