"""
优化服务：负责处理航运路线优化算法
"""
from datetime import datetime
import logging
import random
import time
import numpy as np
import pandas as pd
# import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Callable

from design.core.models.network_data import NetworkData
from design.core.optimizer import ShippingNetworkOptimizer
from src.utils.config import Config

# 配置日志
service_logger = logging.getLogger('app')
service_logger.setLevel(logging.DEBUG)
# 确保有文件处理器
if not service_logger.handlers:
    fh = logging.FileHandler('optimization_service.log')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    service_logger.addHandler(fh)

class OptimizationService:
    """优化服务类：提供航运网络优化相关的功能"""
    
    def __init__(self):
        """初始化优化服务"""
        self.optimization_history = []
        self.current_solution = None
        self.optimization_methods = {
            'alns': self._alns_optimize,
            'ALNS': self._alns_optimize,
            'genetic': self._optimize_genetic,
            'simulated_annealing': self._optimize_simulated_annealing,
            'linear_programming': self._optimize_linear_programming
        }
    
    def __call__(self, params, progress_callback=None):
        """
        OptimizerExecutor调用的入口点
        
        Args:
            params: 参数配置字典，包含算法和数据
            progress_callback: 进度回调函数
            
        Returns:
            优化结果
        """
        service_logger.info("航线网络优化服务启动...")
        
        # 增加调试日志
        service_logger.info("="*50)
        service_logger.info("OptimizationService被调用")
        service_logger.info(f"配置参数: {params.keys()}")
        if 'ports_data' in params:
            service_logger.info(f"港口数量: {len(params['ports_data'])}")
        if 'algorithm' in params:
            service_logger.info(f"求解算法: {params['algorithm']}")
        service_logger.info("="*50)
        
        # 提取数据
        # 模型参数
        ports_data = params.get('ports_data', [])
        demands_data = params.get('demands_data', [])

        max_route_count = params.get('constraints', {}).get('max_route_count', 5)
        max_ports_per_route = params.get('constraints', {}).get('max_ports_per_route', 10)
        num_of_ODs = params.get('constraints', {}).get('num_of_ODs', 100)
        default_speed = params.get('default_speed', 20)

        # 算法参数
        algorithm = params.get('algorithm', 'alns')
        max_iterations = params.get('max_iterations', 100)
        max_time = params.get('max_time', 100)

        # 记录开始时间
        start_time = time.time()
        
        # 准备数据结构
        data = {
            'ports': ports_data,
            'demands': demands_data,
            'origins': ports_data,  # 简化例子，所有港口都可作为起源
            'routes': []  # 初始无路线
        }
        
        # 算法参数
        algorithm_params = params.get('algorithm_params', {})
        algorithm_params.update({
            'max_iterations': max_iterations,
            'max_time': max_time
        })

        # 记录参数
        print(f"最大迭代次数: {max_iterations}, 最大时间: {max_time}秒")
        print(f"默认航速: {default_speed}节")
        print(f"服务运输OD数量: {num_of_ODs}")
        print(f"最大规划航行数量: {max_route_count}")
        # 初始化ALNS
        config = Config(
                P=len(data['ports']),
                K=num_of_ODs,
                R=max_route_count,
                seed=42
            )
        # 算法参数
        config.ALGO_MAXIMUM_ITERATIONS = max_iterations
        config.MODEL_SOLVE_TIME_LIMIT = max_time
        # 模型参数
        config.P = len(data['ports'])
        config.K = num_of_ODs
        config.R = max_route_count
        config.MAX_PORT_CALLS = max_ports_per_route
        config.DEFAULT_SPEED = default_speed

        # 打印基本信息
        service_logger.info(f"启动 {algorithm} 算法优化")
        service_logger.info(f"港口数: {len(ports_data)}")
        
        # 更新进度
        if progress_callback:
            progress_callback(5)  # 5%进度
        
        try:
            # 调用相应的优化方法
            method_name = algorithm.lower()
            result = None
            
            service_logger.info(f"优化方法: {method_name}")
            if method_name in self.optimization_methods:
                # 执行优化
                result = self.optimize_routes(data=data, method=method_name, config=config, parameters=algorithm_params)
                
                # 添加统计信息
                if result:
                    routes = result.get('routes', [])
                    total_cost = result.get('total_cost', 0)
                    solve_time = result.get('solve_time', 0)
                    execution_time = result.get('execution_time', 0)
                    num_cover_ports = result.get('num_cover_ports', 0)
                    num_transit_ports = result.get('num_transit_ports', 0)

                    # 添加统计信息
                    result['statistics'] = {
                        'total_cost': total_cost,
                        'num_routes': len(routes),
                        'execution_time': execution_time,
                        'solve_time': solve_time,
                        'num_cover_ports': num_cover_ports,
                        'num_transit_ports': num_transit_ports
                    }
                    
                    # 添加港口数据
                    result['ports'] = ports_data
                    result['design_solution'] = result.get('design_solution', None).copy()
            else:
                service_logger.error(f"不支持的优化方法: {method_name}")
                result = {
                    'error': f"不支持的优化方法: {method_name}"
                }
            
            # 最终进度
            if progress_callback:
                progress_callback(100)  # 100%进度
                
            # 返回最终结果
            return result
            
        except Exception as e:
            service_logger.error(f"优化过程出错: {str(e)}")
            import traceback
            service_logger.error(traceback.format_exc())
            
            if progress_callback:
                progress_callback(100)  # 错误也设置为100%完成
                
            return {
                'error': str(e),
                'routes': [],
                'total_cost': 0
            }
    
    def optimize_routes(self, 
                        data: Dict[str, Any], 
                        method: str = 'genetic', 
                        config: Config = None,
                        parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        优化航运路线
        
        Args:
            data: 输入数据，包含港口、距离、成本等信息
            method: 优化方法，支持'genetic'、'simulated_annealing'、'linear_programming'
            parameters: 优化参数
            
        Returns:
            优化结果字典
        """
        if method not in self.optimization_methods:
            service_logger.info(f"不支持的优化方法: {method}")
            raise ValueError(f"不支持的优化方法: {method}")
        
        # 使用指定的优化方法
        result = self.optimization_methods[method](data=data, algo_params=parameters or {}, config=config)
        
        # 记录优化历史
        self.optimization_history.append({
            'method': method,
            'parameters': parameters,
            'result_summary': {
                'cost': result.get('total_cost', 0),
                'route_count': len(result.get('routes', [])),
                'timestamp': pd.Timestamp.now(),
                'num_cover_ports': result.get('num_cover_ports', 0),
                'num_transit_ports': result.get('num_transit_ports', 0)
            },
            'design_solution': result.get('design_solution', None)
        })
        
        # 更新当前解决方案
        self.current_solution = result
        
        return result
    
    def _alns_optimize(self, 
                       data: Dict[str, Any], 
                       algo_params: Dict[str, Any], 
                       config: Config = None) -> Dict[str, Any]:
        """
        使用ALNS优化航运路线
        """
        # 输出明确的调试信息
        print("\n===================== ALNS优化开始 =====================")
        print(f"输入港口数据: {len(data['ports'])} 个")


        # 提取ALNS参数
        if algo_params.get('max_iterations') is not None:
            max_iterations = algo_params.get('max_iterations', 1200)
            max_time = algo_params.get('max_time', 1200)

            # 初始化ALNS
            config.ALGO_MAXIMUM_ITERATIONS = max_iterations
            config.MODEL_SOLVE_TIME_LIMIT = max_time


        # 记录参数
        print(f"最大迭代次数: {max_iterations}, 最大时间: {max_time}秒")
        try:

            service_logger.info(f"参数信息 Config: P={config.P}, K={config.K}, R={config.R}")
            
            # 准备港口数据
            try:
                ports_df = pd.DataFrame(data['ports'])
                required_columns = ['id', 'name', 'latitude', 'longitude', 'FixedCost']
                ports_df["id"] = ports_df["港口ID"]
                ports_df["name"] = ports_df["港口名称"]
                ports_df["latitude"] = ports_df["纬度"]
                ports_df["Latitude"] = ports_df["纬度"]
                ports_df["NewLatitude"] = ports_df["纬度"]
                ports_df["longitude"] = ports_df["经度"]
                ports_df["Longitude"] = ports_df["经度"]
                ports_df["NewLongitude"] = ports_df["经度"]
                ports_df["Region"] = ports_df["区域"]
                
                # 确保FixedCost列存在，如果不存在添加一个默认值
                if "FixedCost" not in ports_df.columns:
                    service_logger.info("添加缺失的FixedCost列")
                    ports_df["FixedCost"] = np.random.randint(100, 1000, size=len(ports_df))
                
                # 检查列是否存在
                for col in required_columns:
                    if col not in ports_df.columns:
                        service_logger.info(f"警告: 缺少列 '{col}'，添加默认值")
                        
                        # 添加缺失的列
                        if col == 'id':
                            ports_df['id'] = range(len(ports_df))
                        elif col == 'name':
                            ports_df['name'] = [f"Port {i}" for i in range(len(ports_df))]
                        elif col == 'latitude':
                            ports_df['latitude'] = 0.0
                        elif col == 'longitude':
                            ports_df['longitude'] = 0.0
                        elif col == 'FixedCost':
                            ports_df['FixedCost'] = np.random.randint(100, 1000, size=len(ports_df))
                
                service_logger.info(f"港口数据准备完成: {len(ports_df)}行, 列: {ports_df.columns.tolist()}")
                # 打印前5行数据用于检查
                service_logger.info("数据前5行样本:")
                for col in ['id', 'latitude', 'longitude', 'FixedCost']:
                    if col in ports_df.columns:
                        service_logger.info(f"{col}: {ports_df[col].head().tolist()}")
                    else:
                        service_logger.info(f"{col}: 列缺失")
                
            except Exception as e:
                print(f"处理港口数据出错: {e}")
                # 创建最小化的测试数据帧
                ports_df = pd.DataFrame({
                    'id': range(len(data['ports'])),
                    'name': [f"Port {i}" for i in range(len(data['ports']))],
                    'latitude': [p.get('latitude', 0) for p in data['ports']],
                    'longitude': [p.get('longitude', 0) for p in data['ports']],
                    "Region": [p.get('区域', '') for p in data['ports']],
                    "FixedCost": np.random.randint(100, 1000, size=len(data['ports']))
                })
            
            service_logger.info("正在创建数据...")
            
            # 创建网络数据
            try:
                service_logger.info("正在创建NetworkData...")
                network_data = NetworkData(
                    config=config,
                    ports_data=ports_df,
                    num_ports=config.P,
                    num_ods=config.K,
                    num_routes=config.R,
                    random_seed=config.seed
                )
                service_logger.info("NetworkData创建成功")
            except Exception as e:
                print(f"创建NetworkData失败: {e}")
                import traceback
                print(traceback.format_exc())
                raise

            # 初始化并运行优化器
            service_logger.info("初始化ShippingNetworkOptimizer...")
            service_logger.info(f"模型构建中...")
            optimizer = ShippingNetworkOptimizer(network_data=network_data)
            service_logger.info("添加测试配置...")
            if algo_params.get('solve_algorithm', 'ALNS') == 'ALNS' or algo_params.get('solve_algorithm', 'ALNS') == 'alns':
                if algo_params.get('obj_type', 'Cost') == 'Cost':
                    optimizer.add_test("ALNS", "Cost")
                elif algo_params.get('obj_type', 'Cost') == 'Utility':
                    optimizer.add_test("ALNS", "Utility")
                elif algo_params.get('obj_type', 'Cost') == 'Demand':
                    optimizer.add_test("ALNS", "Demand")
                else:
                    service_logger.info("不支持的目标函数类型")
                    raise ValueError("不支持的目标函数类型")
            

            service_logger.info("开始运行优化...")
            start_time = time.time()
            results = optimizer.optimize()
            elapsed_time = time.time() - start_time
            service_logger.info(f"优化完成，用时: {elapsed_time:.2f}秒")
            service_logger.info("\n===================== ALNS优化结束 =====================")
            
            
            service_logger.info(f"结果类型: {type(results)}")
            service_logger.info(f"结果键: {results.keys() if isinstance(results, dict) else 'Not a dict'}")
            
            # 简化的结果处理
            if results is not None:
                # 尝试获取routes和成本
                routes = []
                total_cost = 0
                
                # 从design_solution求解结果中获取routes
                design_solution = None
                if algo_params.get('obj_type', 'Cost') == 'Cost':
                    design_solution = results.get("Cost", None).get("design_solution", None)
                elif algo_params.get('obj_type', 'Cost') == 'Utility':
                    design_solution = results.get("Utility", None).get("design_solution", None)
                elif algo_params.get('obj_type', 'Cost') == 'Demand':
                    design_solution = results.get("Demand", None).get("design_solution", None)
                elif algo_params.get('obj_type', 'Cost') == 'Gurobi':
                    design_solution = results.get("Gurobi", None).get("design_solution", None)
                else:
                    service_logger.info("算法求解结果为空")
                                    # 从Gurobi求解结果中获取routes
                if design_solution is not None:
                    routes = [route_solution.route for route_solution in design_solution.route_solutions]
                    total_cost = design_solution.total_cost
                else:
                    # 如果都没有，生成测试路线
                    service_logger.info("没有找到路线，生成测试数据")
                    routes = self._generate_sample_routes(data, 3)
                
                # 构建简单的结果字典
                result_dict = {
                    'datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'method': 'ALNS',
                    'total_cost': total_cost,
                    'routes': routes,
                    'solve_time': elapsed_time,
                    'statistics': {
                        'total_cost': total_cost,
                        'num_routes': len(routes),
                        'solve_time': elapsed_time,
                        'num_cover_ports': len(design_solution.cover_nodes) if design_solution else 0,
                        'num_transit_ports': len(design_solution.transit_nodes) if design_solution else 0
                    },
                    'design_solution': design_solution
                }
                
                service_logger.info("求解结果准备完成")
                return result_dict
            
                
        except Exception as e:
            service_logger.error(f"ALNS优化过程出错: {e}")
            import traceback
            service_logger.error(traceback.format_exc())
            
            # 发生错误时，返回默认结果
            routes = self._generate_sample_routes(data, 3)
            total_cost = sum(route.get('cost', 1000) for route in routes)
            
            result_dict = {
                'method': 'ALNS',
                'total_cost': total_cost,
                'routes': routes,
                'execution_time': 0,
                'iterations': 0,
                'error': f'优化失败: {str(e)}',
                'ports': data['ports'],
                'statistics': {
                    'total_cost': total_cost,
                    'num_routes': len(routes),
                    'execution_time': 0,
                    'num_cover_ports': 0,
                    'num_transit_ports': 0
                }
            }
            service_logger.info("\n===================== ALNS优化结束(错误) =====================")
            return result_dict
    
    def _optimize_genetic(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用遗传算法优化航运路线
        
        Args:
            data: 输入数据
            params: 算法参数
            
        Returns:
            优化结果
        """
        # 提取遗传算法参数
        population_size = params.get('population_size', 100)
        generations = params.get('generations', 50)
        mutation_rate = params.get('mutation_rate', 0.1)
        crossover_rate = params.get('crossover_rate', 0.8)
        
        # 实现遗传算法的优化逻辑
        # 这里仅作为示例
        
        # 生成模拟结果
        routes = self._generate_sample_routes(data, 5)
        total_cost = sum(route.get('cost', 0) for route in routes)
        
        return {
            'method': 'genetic',
            'total_cost': total_cost,
            'routes': routes,
            'execution_time': 10.5,  # 模拟执行时间
            'iterations': generations
        }
    
    def _optimize_simulated_annealing(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用模拟退火算法优化航运路线
        
        Args:
            data: 输入数据
            params: 算法参数
            
        Returns:
            优化结果
        """
        # 提取模拟退火算法参数
        initial_temp = params.get('initial_temp', 100.0)
        cooling_rate = params.get('cooling_rate', 0.95)
        iterations = params.get('iterations', 1000)
        
        # 实现模拟退火算法的优化逻辑
        # 这里仅作为示例
        
        # 生成模拟结果
        routes = self._generate_sample_routes(data, 4)
        total_cost = sum(route.get('cost', 0) for route in routes)
        
        return {
            'method': 'simulated_annealing',
            'total_cost': total_cost,
            'routes': routes,
            'execution_time': 8.2,  # 模拟执行时间
            'iterations': iterations
        }
    
    def _optimize_linear_programming(self, data: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用线性规划优化航运路线
        
        Args:
            data: 输入数据
            params: 算法参数
            
        Returns:
            优化结果
        """
        # 提取线性规划参数
        solver = params.get('solver', 'default')
        time_limit = params.get('time_limit', 3600)
        
        # 实现线性规划的优化逻辑
        # 这里仅作为示例
        
        # 生成模拟结果
        routes = self._generate_sample_routes(data, 3)
        total_cost = sum(route.get('cost', 0) for route in routes)
        
        return {
            'method': 'linear_programming',
            'total_cost': total_cost,
            'routes': routes,
            'execution_time': 5.7,  # 模拟执行时间
            'solver': solver
        }
    
    def _generate_sample_routes(self, data: Dict[str, Any], count: int) -> List[Dict[str, Any]]:
        """
        生成示例路线（用于示例）
        
        Args:
            data: 输入数据
            count: 路线数量
            
        Returns:
            路线列表
        """
        routes = []
        if 'ports_data' not in data or not data['ports_data']:
            # 如果没有港口数据，返回空列表
            return routes
            
        ports = data['ports_data']
        
        # 为每条路线随机选择3-6个港口
        for i in range(count):
            route_ports = random.sample(ports, min(random.randint(3, 6), len(ports)))
            
            # 计算路线距离（简化示例）
            distance = random.uniform(1000, 5000)
            
            # 计算路线成本（简化示例）
            cost = distance * 2 + 1000
            
            # 装载率（示例）
            load_factor = random.uniform(0.5, 0.9)
            
            # 创建路线对象
            route = {
                'id': f'R{i+1}',
                'distance': distance,
                'cost': cost,
                'load_factor': load_factor,
                'ports': []
            }
            
            # 添加港口信息
            for j, port in enumerate(route_ports):
                port_info = {
                    'id': port.get('id', f'P{j}'),
                    'name': port.get('name', f'Port {j}'),
                    'lat': port.get('latitude', 0),
                    'lon': port.get('longitude', 0),
                    'arrival_time': f'Day {j}',
                    'departure_time': f'Day {j}',
                    'load_quantity': random.randint(500, 2000)
                }
                route['ports'].append(port_info)
            
            routes.append(route)
        
        return routes
    
    def compare_methods(self, data: Dict[str, Any], 
                        config: Config = None,
                        methods: List[str] = None, 
                       parameters: Dict[str, Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
        """
        比较不同优化方法的结果
        
        Args:
            data: 输入数据
            methods: 要比较的方法列表
            parameters: 各方法的参数字典
            
        Returns:
            比较结果字典
        """
        if methods is None:
            methods = list(self.optimization_methods.keys())
        
        if parameters is None:
            parameters = {method: {} for method in methods}
        
        results = {}
        
        for method in methods:
            if method not in self.optimization_methods:
                continue
            
            # 运行优化
            result = self.optimize_routes(data=data, params=parameters.get(method, {}), config=config)
            results[method] = result

        return results
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        获取优化历史
        
        Returns:
            优化历史记录
        """
        return self.optimization_history
    
    def get_best_solution(self, criterion: str = 'total_cost') -> Dict[str, Any]:
        """
        获取最佳解决方案
        
        Args:
            criterion: 评判标准，如'total_cost'
            
        Returns:
            最佳解决方案
        """
        pass