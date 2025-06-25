import random
import numpy as np
import logging
from design.core.models.design_solution import DesignSolution
from design.core.models.route_solution import RouteSolution
from design.core.models.network_data import NetworkData


def generate_initial_design_solution(network_data: NetworkData) -> DesignSolution:
    """
    Generate an initial design solution for the ALNS algorithm.
    """
    try:
        print("正在生成初始设计解决方案...")
        # 创建一个设计解决方案对象
        design_solution = DesignSolution(network_data)
        
        # 设置默认目标类型（如果需要）
        design_solution.obj_type = "Cost"  # 默认为成本最小化
        
        # 通过循环为每条路线创建解决方案
        num_routes = getattr(network_data, 'num_routes', 0)
        print(f"网络中有 {num_routes} 条路线")
        
        if num_routes <= 0:
            # 如果没有路线，直接返回空解决方案
            print("警告: 网络中没有路线，返回空解决方案")
            return design_solution
            
        for r in range(num_routes):
            # 为每条路线创建一个初始RouteSolution
            route_solution = generate_initial_route_solution(network_data, r)
            design_solution.route_solutions[r] = route_solution
            
        # 验证解决方案的有效性
        try:
            objective_value = design_solution.objective()
            print(f"初始解目标函数值: {objective_value}")
        except Exception as e:
            print(f"计算初始解目标函数值时出错: {e}")
            # 即使出错也返回解决方案
            
        return design_solution
    except Exception as e:
        print(f"生成初始设计解决方案时发生错误: {e}")
        import traceback
        print(traceback.format_exc())
        
        # 创建一个最简单的解决方案
        minimal_solution = DesignSolution(network_data)
        minimal_solution.obj_type = "Cost"
        return minimal_solution


def generate_initial_route_solution(network_data: NetworkData, route_idx: int) -> RouteSolution:
    """
    Generate an initial route solution for a specific route.
    """
    try:
        # 创建一个路线解决方案对象
        route_solution = RouteSolution(network_data, route_idx)
        
        # 简单地添加一些随机港口到路线中
        # 这里只是一个示例，实际实现可能需要更复杂的逻辑
        ports = list(range(network_data.num_ports))
        if ports:  # 确保有港口可用
            # 随机选择2-5个港口
            num_ports = min(random.randint(2, 5), len(ports))
            selected_ports = random.sample(ports, num_ports)
            
            # 创建路线
            route_solution.route = selected_ports
            
            # 这里可以添加更多的初始化逻辑，如装载量、停靠时间等
            
        return route_solution
    except Exception as e:
        print(f"生成初始路线解决方案时发生错误: {e}")
        # 返回一个空的路线解决方案
        return RouteSolution(network_data, route_idx)