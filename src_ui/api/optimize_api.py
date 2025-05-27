from flask import Blueprint, request, jsonify
import logging
from algorithm_interface import AlgorithmInterface
from multi.algos.benders_decomposition import BendersDecomposition
from multi.algos.benders_decomposition_with_pap import BendersDecompositionWithPAP
from multi.algos.ccg import CCG
from multi.algos.ccg_with_pap import CCGwithPAP
from multi.model.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.utils.generate_parameter import GenerateParameter
from multi.utils.input_data import InputData
from multi.utils.read_data import ReadData
import subprocess
import os
import json
import time
from database import Session
from models import Ship, Port

optimize_bp = Blueprint('optimize', __name__)
algorithm_interface = AlgorithmInterface()

@optimize_bp.route('/api/optimize', methods=['POST'])
def optimize():
    try:
        log_messages = []
        def log_callback(message):
            log_messages.append(message)
            print(message)
        log_callback("="*50)
        log_callback("开始处理优化请求...")
        data = request.get_json()
        log_callback(f"接收到的参数: {data}")
        try:
            # 模型参数      
                model_params = {
                'time_window': int(data.get('time_window', 60)),
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
        except Exception as e:
            log_callback(f"模型参数更新失败: {e}")
        try:
            algo_params = {
                'algorithm': data.get('algorithm', 'bd'),
                'max_iter': int(data.get('max_iter', 100)),
                'max_time': int(data.get('max_time', 600)),
                'mip_gap': float(data.get('mip_gap', 0.01)),
            }
            DefaultSetting.update_setting_from_dict(algo_params)
            log_callback(f"算法参数读取完成")
        except Exception as e:
            log_callback(f"算法参数更新失败: {e}")
        try:
            log_callback("开始执行优化计算...")
            
            input_data = InputData()

            reader = ReadData(
                path="data/",
                input_data=input_data,
                time_horizon=DefaultSetting.DEFAULT_TIME_HORIZON,
                use_db=True,
                db_path="ships.db"
            )
            log_callback("数据读取完成")

            param = Parameter(input_data=input_data)
            GenerateParameter(input_data=input_data, 
                              param=param, 
                              time_horizon=DefaultSetting.DEFAULT_TIME_HORIZON, 
                              uncertain_degree=DefaultSetting.DEFAULT_UNCERTAIN_DEGREE,
                              )
            log_callback("参数生成完成")

            result = {}
            if data.get('algorithm') == "bd":
                try:
                    log_callback("使用Benders分解算法")
                    bd = BendersDecomposition(input_data=input_data, param=param)
                    result = bd.solve()
                except Exception as e:
                    log_callback(f"Benders分解算法执行失败: {e}")
            elif data.get('algorithm') == "ccg":
                log_callback("使用列生成算法")
                cp = CCG(input_data=input_data, param=param)
                result = cp.solve()
            elif data.get('algorithm') == "bdpap":
                log_callback("使用带PAP策略的Benders分解算法")
                bdpap = BendersDecompositionWithPAP(input_data=input_data, param=param)
                result = bdpap.solve()
            elif data.get('algorithm') == "ccgpap":
                log_callback("使用带PAP策略的列生成算法")
                ccgpap = CCGwithPAP(input_data=input_data, param=param)
                result = ccgpap.solve()
            else:
                log_callback(f"算法类型错误：{data.get('algorithm')}")
                
            log_callback("算法执行完成")

            log_callback("优化完成！")
            log_callback(f"优化结果: {result}")

            # ========== 新增：查数据库获取名称映射 ==========
            deploy_plan = result.get('solution', {})  # 航线ID: 船舶ID
            session = Session()
            # 航线ID->名称
            from models import Route, Ship
            route_info = {str(r.id): r.ports_of_call or f"航线{r.id}" for r in session.query(Route).all()}
            vessel_info = {str(s.id): s.name or f"船舶{s.id}" for s in session.query(Ship).all()}
            session.close()
            # ========== END ==========


            return jsonify({
                'status': 'success',
                'result_time': f"{result.get('time', 0):.1f}s",
                'total_cost': result.get('objective', 0),
                'solution': result.get('solution', {}),
                'deploy_plan': deploy_plan,
                'route_info': route_info,
                'vessel_info': vessel_info,
                'oc': result.get('operation_cost', 0),
                'lc': result.get('laden_cost', 0),
                'ec': result.get('empty_cost', 0),
                'rc': result.get('rental_cost', 0),
                'pc': result.get('penalty_cost', 0),
                'gap': result.get('gap', 0),
                'log': '\n'.join(log_messages)
            })
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
    if not algorithm_interface.validate_input_data(data):
        return jsonify({
            "status": "error",
            "message": "输入数据无效"
        }), 400
    result = algorithm_interface.run_scheduling_algorithm(
        ships_data=data.get('ships', []),
        ports_data=data.get('ports', [])
    )
    if result['status'] == 'error':
        return jsonify(result), 500
    return jsonify(result)

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