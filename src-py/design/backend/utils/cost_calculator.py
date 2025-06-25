"""
成本计算工具：用于计算航运成本
"""
import math
from typing import Dict, List, Any, Optional, Tuple


def calculate_fuel_cost(distance: float, vessel_type: str = 'container',
                      speed: float = 20.0, fuel_price: float = 500.0) -> float:
    """
    计算燃油成本
    
    Args:
        distance: 距离（海里）
        vessel_type: 船舶类型
        speed: 航速（节，即海里/小时）
        fuel_price: 燃油价格（美元/吨）
        
    Returns:
        燃油成本（美元）
    """
    # 不同船舶类型的燃油消耗系数（吨/海里）
    fuel_consumption_rates = {
        'container': 0.3,
        'bulk': 0.25,
        'tanker': 0.35,
        'reefer': 0.4
    }
    
    # 速度影响因子（高速消耗更多燃油）
    speed_factor = (speed / 14.0) ** 2
    
    # 获取燃油消耗率
    consumption_rate = fuel_consumption_rates.get(vessel_type, 0.3)
    
    # 计算总燃油消耗
    fuel_consumption = distance * consumption_rate * speed_factor
    
    # 计算燃油成本
    fuel_cost = fuel_consumption * fuel_price
    
    return fuel_cost


def calculate_time_cost(duration: float, vessel_type: str = 'container',
                       daily_cost: float = 8000.0) -> float:
    """
    计算时间相关成本（租船成本）
    
    Args:
        duration: 航行时间（天）
        vessel_type: 船舶类型
        daily_cost: 日租金（美元/天）
        
    Returns:
        时间成本（美元）
    """
    # 不同船舶类型的日租金调整系数
    daily_cost_factors = {
        'container': 1.0,
        'bulk': 0.8,
        'tanker': 1.2,
        'reefer': 1.5
    }
    
    # 获取调整系数
    cost_factor = daily_cost_factors.get(vessel_type, 1.0)
    
    # 计算时间成本
    time_cost = duration * daily_cost * cost_factor
    
    return time_cost


def calculate_port_cost(port_data: Dict[str, Any], vessel_type: str = 'container') -> float:
    """
    计算港口成本
    
    Args:
        port_data: 港口数据
        vessel_type: 船舶类型
        
    Returns:
        港口成本（美元）
    """
    # 基础港口费用
    base_cost = port_data.get('handling_cost', 5000.0)
    
    # 不同船舶类型的港口费用调整系数
    port_cost_factors = {
        'container': 1.0,
        'bulk': 0.9,
        'tanker': 1.3,
        'reefer': 1.2
    }
    
    # 获取调整系数
    cost_factor = port_cost_factors.get(vessel_type, 1.0)
    
    # 计算港口成本
    port_cost = base_cost * cost_factor
    
    return port_cost


def calculate_total_route_cost(route_data: Dict[str, Any], fuel_price: float = 500.0,
                              daily_cost: float = 8000.0) -> Dict[str, float]:
    """
    计算路线总成本
    
    Args:
        route_data: 路线数据
        fuel_price: 燃油价格（美元/吨）
        daily_cost: 日租金（美元/天）
        
    Returns:
        成本明细字典
    """
    distance = route_data.get('distance', 0.0)
    duration = route_data.get('duration', 0.0)
    vessel_type = route_data.get('vessel_type', 'container')
    ports = route_data.get('ports', [])
    
    # 计算燃油成本
    fuel_cost = calculate_fuel_cost(distance, vessel_type, fuel_price=fuel_price)
    
    # 计算时间成本
    time_cost = calculate_time_cost(duration, vessel_type, daily_cost=daily_cost)
    
    # 计算港口成本
    port_costs = sum(calculate_port_cost(port, vessel_type) for port in ports)
    
    # 计算杂项成本（如运河通行费、保险等）
    misc_costs = route_data.get('misc_costs', 0.0)
    
    # 计算总成本
    total_cost = fuel_cost + time_cost + port_costs + misc_costs
    
    # 返回成本明细
    return {
        'fuel_cost': fuel_cost,
        'time_cost': time_cost,
        'port_costs': port_costs,
        'misc_costs': misc_costs,
        'total_cost': total_cost
    }


def estimate_co2_emissions(distance: float, vessel_type: str = 'container',
                         speed: float = 20.0) -> float:
    """
    估算CO2排放量
    
    Args:
        distance: 距离（海里）
        vessel_type: 船舶类型
        speed: 航速（节，即海里/小时）
        
    Returns:
        CO2排放量（吨）
    """
    # 不同船舶类型的CO2排放系数（吨CO2/吨燃油）
    co2_factors = {
        'container': 3.1,
        'bulk': 3.0,
        'tanker': 3.2,
        'reefer': 3.3
    }
    
    # 不同船舶类型的燃油消耗系数（吨/海里）
    fuel_consumption_rates = {
        'container': 0.3,
        'bulk': 0.25,
        'tanker': 0.35,
        'reefer': 0.4
    }
    
    # 速度影响因子
    speed_factor = (speed / 14.0) ** 2
    
    # 获取燃油消耗率和CO2排放系数
    consumption_rate = fuel_consumption_rates.get(vessel_type, 0.3)
    co2_factor = co2_factors.get(vessel_type, 3.1)
    
    # 计算总燃油消耗
    fuel_consumption = distance * consumption_rate * speed_factor
    
    # 计算CO2排放量
    co2_emissions = fuel_consumption * co2_factor
    
    return co2_emissions 