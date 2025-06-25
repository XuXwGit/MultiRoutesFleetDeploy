import re
import logging
import random
import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, asin

from .config import Config

def parse_coordinate(coord_str):
    """
    解析地理坐标字符串（支持N/S/E/W格式）
    返回：十进制度数值（浮点数）
    """
    try:
        direction = 1
        if isinstance(coord_str, (int, float)):
            return float(coord_str)
            
        if 'S' in coord_str or 'W' in coord_str:
            direction = -1
        
        # 提取数字部分
        numeric_part = re.sub(r'[^\d.]', '', coord_str)
        return direction * float(numeric_part)
    except Exception as e:
        logging.error(f"坐标解析错误: {coord_str} | 错误: {str(e)}")
        raise ValueError(f"无效的坐标格式: {coord_str}")

def haversine(lat1, lon1, lat2, lon2):
    """
    计算两点间大圆距离（千米）
    """
    # 转换为弧度
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    return 6371 * 2 * asin(np.sqrt(a))  # 地球平均半径6371km

def load_port_data(file_path: str = None, instance: str = None):
    """
    加载并预处理港口数据
    返回：包含标准化坐标的DataFrame
    """
    if file_path == None:
         file_path = Config.DATA_DIR / instance / "ports.csv"
    else:
         file_path = file_path
    df = pd.read_csv(file_path, encoding='GBK')
    
    # 坐标转换
    df['Longitude'] = df['Longitude'].apply(parse_coordinate)
    df['Latitude'] = df['Latitude'].apply(parse_coordinate)

    df['FixedCost'] = np.random.randint(500, 1001, size=len(df))  # 包含1000
    df['Operation'] = np.random.randint(10000, 100001, size=len(df)) * 10
        
    # 调整经度以太平洋为中心
    logging.info("调整经度以太平洋为中心...")
    delta = 110
    shift = delta
    shift -= 180 
    df['NewLongitude'] = df['Longitude'].apply(lambda x : x - delta if x > shift else x + 360 - delta)
    
    return df.reset_index(drop=True)

def generate_od_pairs(ports_df: pd.DataFrame, num_ods = 100):
    """生成跨区域OD对"""
    try:
        logging.info("生成OD对...")
        
        # 生成跨区域OD对
        od_pairs = []
        for o in range(len(ports_df)):
                    for d in range(o + 1, len(ports_df)):
                        if ports_df.loc[o, 'Region'] != ports_df.loc[d, 'Region']:
                            # 双向OD
                            od_pairs.append((o, d))
                            od_pairs.append((d, o))
        
        logging.info(f"共生成 {len(od_pairs)} 个OD对")
        od_pairs = random.sample(od_pairs, min(num_ods, len(od_pairs)))
        od_demands = {}
        total_demand = 0
        for (o, d) in od_pairs:
             od_demands[(o, d)] = random.randint(1000, 5000)
             total_demand += od_demands[(o, d)]

        logging.info(f'随机抽取 {len(od_demands)} 个od对，总需求量：{total_demand}')
        return od_pairs, od_demands
    except KeyError as e:
        logging.error(f"区域数据异常，请检查Region列: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"生成OD对失败: {str(e)}")
        raise



def calculate_distance_matrix(coords, speed_knots=20):
    """
    生成距离时间矩阵（以小时为单位）
    参数：
        coords: 包含(longitude, latitude)的Nx2数组
        speed_knots: 船舶速度（节）
    返回：NxN numpy数组
    """
    n = len(coords)
    dist = np.zeros((n, n))
    
    # 向量化计算
    lats = np.deg2rad(coords[:, 0])
    lons = np.deg2rad(coords[:, 1])
    
    # 利用广播机制计算所有点对
    dlat = lats[:, None] - lats
    dlon = lons[:, None] - lons
    
    a = np.sin(dlat/2)**2 + np.cos(lats[:, None])*np.cos(lats)*np.sin(dlon/2)**2
    distances = 6371 * 2 * np.arcsin(np.sqrt(a))
    
    # 转换为时间（小时），1节=1.852公里/小时
    return np.round(distances / (speed_knots * 1.852), 0)

