"""
距离计算工具：用于计算港口间距离
"""
import math
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    使用Haversine公式计算两点间的球面距离
    
    Args:
        lat1: 第一点纬度
        lon1: 第一点经度
        lat2: 第二点纬度
        lon2: 第二点经度
        
    Returns:
        距离（海里）
    """
    # 地球半径（海里）
    R = 3440.065  # 1海里 = 1.852公里，地球半径约6371公里
    
    # 将经纬度转换为弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine公式
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance


def create_distance_matrix(ports: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    为港口列表创建距离矩阵
    
    Args:
        ports: 港口列表，每个港口包含id、latitude和longitude
        
    Returns:
        距离矩阵DataFrame
    """
    n = len(ports)
    port_ids = [port['id'] for port in ports]
    
    # 创建空距离矩阵
    distance_matrix = np.zeros((n, n))
    
    # 计算每对港口之间的距离
    for i in range(n):
        for j in range(n):
            if i != j:
                lat1, lon1 = ports[i].get('latitude', 0), ports[i].get('longitude', 0)
                lat2, lon2 = ports[j].get('latitude', 0), ports[j].get('longitude', 0)
                
                # 如果端口数据使用lat/lon代替latitude/longitude
                if lat1 == 0 and 'lat' in ports[i]:
                    lat1 = ports[i].get('lat', 0)
                if lon1 == 0 and 'lon' in ports[i]:
                    lon1 = ports[i].get('lon', 0)
                if lat2 == 0 and 'lat' in ports[j]:
                    lat2 = ports[j].get('lat', 0)
                if lon2 == 0 and 'lon' in ports[j]:
                    lon2 = ports[j].get('lon', 0)
                
                distance = haversine_distance(lat1, lon1, lat2, lon2)
                distance_matrix[i, j] = distance
    
    # 创建DataFrame
    df = pd.DataFrame(distance_matrix, index=port_ids, columns=port_ids)
    
    return df


def estimate_transit_time(distance: float, speed: float = 20.0) -> float:
    """
    估算航行时间
    
    Args:
        distance: 距离（海里）
        speed: 航速（节，即海里/小时）
        
    Returns:
        航行时间（天）
    """
    transit_hours = distance / speed
    transit_days = transit_hours / 24.0
    
    return transit_days


def calculate_route_distance(ports: List[Dict[str, Any]], route: List[int]) -> float:
    """
    计算给定路线的总距离
    
    Args:
        ports: 港口列表
        route: 路线（港口索引序列）
        
    Returns:
        总距离（海里）
    """
    total_distance = 0.0
    
    for i in range(len(route) - 1):
        port1 = ports[route[i]]
        port2 = ports[route[i + 1]]
        
        lat1 = port1.get('latitude', port1.get('lat', 0))
        lon1 = port1.get('longitude', port1.get('lon', 0))
        lat2 = port2.get('latitude', port2.get('lat', 0))
        lon2 = port2.get('longitude', port2.get('lon', 0))
        
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        total_distance += distance
        
    return total_distance 