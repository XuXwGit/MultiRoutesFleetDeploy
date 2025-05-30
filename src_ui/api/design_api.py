from flask import Blueprint, jsonify, request
import json
import pandas as pd
import numpy as np
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3

# 创建蓝图
design_bp = Blueprint('design', __name__)

# 数据库连接
Base = declarative_base()
engine = create_engine('sqlite:///ships.db')
Session = sessionmaker(bind=engine)

# 定义模型
class DesignPort(Base):
    __tablename__ = 'design_ports'
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    throughput = Column(Integer, default=0)
    region = Column(String(32), default='未分类')
    is_hub = Column(Boolean, default=False)

class DesignRoute(Base):
    __tablename__ = 'design_routes'
    id = Column(Integer, primary_key=True)
    name = Column(String(64))
    port_sequence = Column(Text)  # 存储为JSON格式
    arrival_times = Column(Text)  # 存储为JSON格式
    distance = Column(Float)
    cost = Column(Float)

class DesignResult(Base):
    __tablename__ = 'design_results'
    id = Column(Integer, primary_key=True)
    datetime = Column(String(64))
    method = Column(String(64))
    total_cost = Column(Float)
    routes = Column(Text)  # 存储为JSON格式
    statistics = Column(Text)  # 存储为JSON格式

# 确保表存在
Base.metadata.create_all(engine)

# 获取所有设计港口
@design_bp.route('/api/design/ports')
def get_design_ports():
    session = Session()
    try:
        ports = session.query(DesignPort).all()
        result = []
        for port in ports:
            result.append({
                'id': port.id,
                'name': port.name,
                'longitude': port.longitude,
                'latitude': port.latitude,
                'throughput': port.throughput,
                'region': port.region,
                'is_hub': port.is_hub
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

# 获取最新的网络设计结果
@design_bp.route('/api/design/network')
def get_design_network():
    session = Session()
    try:
        # 获取最新的结果
        result = session.query(DesignResult).order_by(DesignResult.id.desc()).first()
        if not result:
            # 如果没有结果，返回空数据结构
            return jsonify({
                'ports': [],
                'routes': [],
                'statistics': {}
            })
        
        # 获取所有港口
        ports = session.query(DesignPort).all()
        ports_data = []
        for port in ports:
            ports_data.append({
                'id': port.id,
                'name': port.name,
                'longitude': port.longitude,
                'latitude': port.latitude,
                'throughput': port.throughput,
                'region': port.region,
                'is_hub': port.is_hub
            })
        
        # 解析路由数据
        routes_data = json.loads(result.routes) if result.routes else []
        statistics_data = json.loads(result.statistics) if result.statistics else {}
        
        return jsonify({
            'ports': ports_data,
            'routes': routes_data,
            'statistics': statistics_data,
            'datetime': result.datetime,
            'method': result.method,
            'total_cost': result.total_cost
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

# 获取历史优化结果
@design_bp.route('/api/design/history')
def get_design_history():
    session = Session()
    try:
        results = session.query(DesignResult).order_by(DesignResult.id.desc()).all()
        history_data = []
        
        for result in results:
            routes_data = json.loads(result.routes) if result.routes else []
            statistics_data = json.loads(result.statistics) if result.statistics else {}
            
            history_data.append({
                'id': result.id,
                'datetime': result.datetime,
                'method': result.method,
                'total_cost': result.total_cost,
                'routes': routes_data,
                'statistics': statistics_data
            })
        
        return jsonify(history_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

# 上传港口数据
@design_bp.route('/api/design/ports', methods=['POST'])
def upload_design_ports():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400
    
    try:
        # 获取文件扩展名
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        
        # 根据文件类型读取
        if file_ext == 'csv':
            df = pd.read_csv(file)
        elif file_ext in ['xls', 'xlsx']:
            df = pd.read_excel(file)
        else:
            return jsonify({'error': '不支持的文件格式'}), 400
        
        # 处理列名映射
        column_mappings = {
            'id': ['id', 'ID', 'port_id', 'PortID', '港口ID'],
            'name': ['name', 'Name', 'port_name', 'PortName', '港口名称', '名称'],
            'longitude': ['longitude', 'Longitude', 'lon', 'LON', '经度'],
            'latitude': ['latitude', 'Latitude', 'lat', 'LAT', '纬度'],
            'throughput': ['throughput', 'Throughput', 'capacity', 'Capacity', '吞吐量'],
            'region': ['region', 'Region', 'area', 'Area', '区域', '地区'],
            'is_hub': ['is_hub', 'IsHub', 'hub', 'Hub', '是否枢纽', '枢纽']
        }
        
        # 创建映射字典
        column_map = {}
        for standard_name, possible_names in column_mappings.items():
            for name in possible_names:
                if name in df.columns:
                    column_map[standard_name] = name
                    break
        
        # 检查必要的列
        required_columns = ['longitude', 'latitude']
        missing_columns = [col for col in required_columns if col not in column_map]
        if missing_columns:
            return jsonify({'error': f'缺少必要的列: {", ".join(missing_columns)}'}), 400
        
        # 转换为标准列名
        standardized_df = pd.DataFrame()
        for standard_name, original_name in column_map.items():
            standardized_df[standard_name] = df[original_name]
        
        # 添加缺失的可选列
        for col in ['id', 'name', 'throughput', 'region', 'is_hub']:
            if col not in standardized_df.columns:
                if col == 'id':
                    standardized_df[col] = range(1, len(standardized_df) + 1)
                elif col == 'name':
                    standardized_df[col] = [f'Port_{i}' for i in range(1, len(standardized_df) + 1)]
                elif col == 'throughput':
                    standardized_df[col] = 0
                elif col == 'region':
                    standardized_df[col] = '未分类'
                elif col == 'is_hub':
                    standardized_df[col] = False
        
        # 导入到数据库
        session = Session()
        
        # 清空现有数据
        session.query(DesignPort).delete()
        
        # 添加新数据
        for _, row in standardized_df.iterrows():
            port = DesignPort(
                id=int(row['id']) if not pd.isna(row['id']) else None,
                name=str(row['name']),
                longitude=float(row['longitude']),
                latitude=float(row['latitude']),
                throughput=int(row['throughput']) if not pd.isna(row['throughput']) else 0,
                region=str(row['region']) if not pd.isna(row['region']) else '未分类',
                is_hub=bool(row['is_hub']) if not pd.isna(row['is_hub']) else False
            )
            session.add(port)
        
        session.commit()
        session.close()
        
        return jsonify({'success': True, 'message': f'成功导入 {len(standardized_df)} 条港口数据'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 添加单个港口
@design_bp.route('/api/design/port', methods=['POST'])
def add_design_port():
    data = request.json
    
    required_fields = ['name', 'longitude', 'latitude']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'缺少必要字段: {field}'}), 400
    
    try:
        session = Session()
        
        # 检查ID是否已存在
        if 'id' in data and data['id']:
            existing = session.query(DesignPort).filter_by(id=data['id']).first()
            if existing:
                return jsonify({'error': f'ID {data["id"]} 已存在'}), 400
        
        # 创建新港口
        port = DesignPort(
            id=data.get('id'),
            name=data['name'],
            longitude=float(data['longitude']),
            latitude=float(data['latitude']),
            throughput=int(data.get('throughput', 0)),
            region=data.get('region', '未分类'),
            is_hub=bool(data.get('is_hub', False))
        )
        
        session.add(port)
        session.commit()
        
        # 返回新添加的港口信息
        result = {
            'id': port.id,
            'name': port.name,
            'longitude': port.longitude,
            'latitude': port.latitude,
            'throughput': port.throughput,
            'region': port.region,
            'is_hub': port.is_hub
        }
        
        session.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 获取优化进度（示例数据）
@design_bp.route('/api/design/progress')
def get_optimization_progress():
    # 这里返回示例数据，实际应用中可能需要从缓存或数据库中获取实时进度
    return jsonify({
        'current_iteration': 50,
        'max_iterations': 100,
        'best_solution': 125000,
        'improvement_rate': 23.5,
        'running_time': 45,
        'status': 'running',
        'iterations': [
            {'iteration': i, 'current_value': 200000 - i*1500 + np.random.randint(-2000, 2000), 
             'best_value': min(200000, 200000 - i*1500)} for i in range(1, 51)
        ]
    }) 