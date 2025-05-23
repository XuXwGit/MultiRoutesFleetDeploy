from flask import Flask, render_template, jsonify, request, Response
import json
import pandas as pd
from algorithm_interface import AlgorithmInterface
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import logging
import time
import sys
import subprocess
from pathlib import Path
from sqlalchemy import text
# 设置日志回调 
import sys
from io import StringIO
import queue
# 添加src-py到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src-py'))

from multi.algos.benders_decomposition import BendersDecomposition
from multi.algos.benders_decomposition_with_pap import BendersDecompositionWithPAP
from multi.algos.ccg import CCG
from multi.algos.ccg_with_pap import CCGwithPAP
from multi.model.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.utils.generate_parameter import GenerateParameter
from multi.utils.input_data import InputData
from multi.utils.read_data import ReadData
sys.setrecursionlimit(10000)  # 设置更大的递归深度限制

# 创建消息队列用于存储实时日志
log_queue = queue.Queue()

app = Flask(__name__)
CORS(app)
algorithm_interface = AlgorithmInterface()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 默认船舶参数
DEFAULT_SHIP_PARAMS = {
    "type": "集装箱船",
    "status": "在航",
    "current_port": "上海港",
    "next_port": "新加坡港",
    "eta": "2024-05-20 08:00:00",
    "position": [121.48, 31.22]
}

# 全局数据存储
SHIPS_DATA = []
ROUTES_DATA = []
PORTS_DATA = []
NODES_DATA = []
TRANS_DATA = []
TRAVEL_DATA = []
PATHS_DATA = []
REQUESTS_DATA = []

# ================== 数据库字段名 -> 标准字段名映射 ==================
DB_COLUMN_MAPS = {
    'ports': {
        'port_id': 'PortID',
        'name': 'Port',
        'whether_trans': 'WhetherTrans',
        'region': 'Region',
        'group': 'Group',
    },
    'ships': {
        'id': 'VesselID',
        'name': 'VesselName',
        'capacity': 'Capacity',
        'operating_cost': 'OperatingCost',
        'route_id': 'RouteID',
        'max_num': 'MaxNum',
        # 其他字段如type、status等可按需补充
    },
    'routes': {
        'id': 'ID',
        'number_of_ports': 'NumberOfPorts',
        'ports': 'Ports',
        'number_of_calls': 'NumberOfCall',
        'ports_of_call': 'PortsofCall',
        'times': 'Time',
    },
    'nodes': {
        'id': 'ID',
        'route': 'Route',
        'call': 'Call',
        'port': 'Port',
        'round_trip': 'RoundTrip',
        'time': 'Time',
    },
    'transship_arcs': {
        'id': 'TransshipArcID',
        'port': 'Port',
        'origin_node_id': 'OriginNodeID',
        'origin_time': 'OriginTime',
        'transship_time': 'TransshipTime',
        'destination_node_id': 'DestinationNodeID',
        'destination_time': 'DestinationTime',
        'from_route': 'FromRoute',
        'to_route': 'ToRoute',
    },
    'traveling_arcs': {
        'id': 'TravelingArcID',
        'route': 'Route',
        'origin_node_id': 'OriginNodeID',
        'origin_call': 'OriginCall',
        'origin_port': 'OriginPort',
        'round_trip': 'RoundTrip',
        'origin_time': 'OriginTime',
        'traveling_time': 'TravelingTime',
        'destination_node_id': 'DestinationNodeID',
        'destination_call': 'DestinationCall',
        'destination_port': 'DestinationPort',
        'destination_time': 'DestinationTime',
    },
    'paths': {
        'id': 'ContainerPathID',
        'origin_port': 'OriginPort',
        'origin_time': 'OriginTime',
        'destination_port': 'DestinationPort',
        'destination_time': 'DestinationTime',
        'path_time': 'PathTime',
        'transship_port': 'TransshipPort',
        'transship_time': 'TransshipTime',
        'port_path': 'PortPath',
        'arcs_id': 'Arcs_ID',
        'container_path_id': 'ContainerPathID',
    },
    'requests': {
        'id': 'RequestID',
        'origin_port': 'OriginPort',
        'destination_port': 'DestinationPort',
        'w_i_earlist': 'EarliestPickupTime',
        'latest_destination_time': 'LatestDestinationTime',
        'laden_paths': 'LadenPaths',
        'number_of_laden_path': 'NumberOfLadenPath',
        'empty_paths': 'EmptyPaths',
        'number_of_empty_path': 'NumberOfEmptyPath',
    },
    # 其他表可按需补充
}

def write_df_to_db(df: pd.DataFrame, table_name: str, db_path: str, if_exists: str = 'replace', index: bool = False):
    """
    将DataFrame写入数据库，自动将列名重命名为README.md标准字段名
    Args:
        df: 待写入的DataFrame
        table_name: 数据库表名（需与DB_COLUMN_MAPS的key一致）
        db_path: 数据库文件路径
        if_exists: 写入模式
        index: 是否写入索引
    """
    std_map = DB_COLUMN_MAPS.get(table_name, None)
    if std_map:
        db_to_std = {v: v for v in std_map.values()}
        df = df.rename(columns=db_to_std)
        df = df[[v for v in std_map.values() if v in df.columns]]
    engine = create_engine(f'sqlite:///{db_path}')
    df.to_sql(table_name, engine, if_exists=if_exists, index=index, method=None)

Base = declarative_base()

class Ship(Base):
    __tablename__ = 'ships'
    id = Column(String, primary_key=True)
    name = Column(String)
    type = Column(String)
    capacity = Column(Float)
    speed = Column(Float)
    status = Column(String)
    current_port = Column(String)
    next_port = Column(String)
    eta = Column(String)
    operating_cost = Column(Float)
    route_id = Column(Integer)
    max_num = Column(Integer)

class Route(Base):
    __tablename__ = 'routes'
    id = Column(Integer, primary_key=True)
    number_of_ports = Column(Integer)
    ports = Column(Text)
    number_of_calls = Column(Integer)
    ports_of_call = Column(Text)
    times = Column(Text)

class Port(Base):
    __tablename__ = 'ports'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    whether_trans = Column(Integer)
    region = Column(String)
    group = Column(Integer)


class Node(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    route = Column(Integer)
    call = Column(Integer)
    port = Column(String)
    round_trip = Column(Integer)
    time = Column(Float)

class TransshipArc(Base):
    __tablename__ = 'transship_arcs'
    id = Column(Integer, primary_key=True)
    port = Column(String)
    origin_node_id = Column(Integer)
    origin_time = Column(Float)
    transship_time = Column(Float)
    destination_node_id = Column(Integer)
    destination_time = Column(Float)
    from_route = Column(Integer)
    to_route = Column(Integer)

class TravelingArc(Base):
    __tablename__ = 'traveling_arcs'
    id = Column(Integer, primary_key=True)
    route = Column(Integer)
    origin_node_id = Column(Integer)
    origin_call = Column(Integer)
    origin_port = Column(String)
    round_trip = Column(Integer)
    origin_time = Column(Float)
    traveling_time = Column(Float)
    destination_node_id = Column(Integer)
    destination_call = Column(Integer)
    destination_port = Column(String)
    destination_time = Column(Float)

class Path(Base):
    __tablename__ = 'paths'
    id = Column(Integer, primary_key=True)
    origin_port = Column(String)
    origin_time = Column(Integer)
    destination_port = Column(String)
    destination_time = Column(Integer)
    path_time = Column(Integer)
    transship_port = Column(String)  # 存储为逗号分隔的字符串
    transship_time = Column(String)  # 存储为逗号分隔的字符串
    port_path = Column(String)  # 存储为逗号分隔的字符串
    arcs_id = Column(String)  # 存储为逗号分隔的字符串
    container_path_id = Column(Integer)  # 添加container_path_id字段

    def get_transship_port_list(self):
        """获取转运港口列表"""
        return [] if self.transship_port == '0' else self.transship_port.split(',')

    def get_transship_time_list(self):
        """获取转运时间列表"""
        return [] if self.transship_time == '0' else [int(x) for x in self.transship_time.split(',')]

    def get_port_path_list(self):
        """获取港口路径列表"""
        return [] if self.port_path == '0' else self.port_path.split(',')

    def get_arcs_id_list(self):
        """获取弧ID列表"""
        return [] if self.arcs_id == '0' else [int(x) for x in self.arcs_id.split(',')]

class Request(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    origin_port = Column(String)
    destination_port = Column(String)
    w_i_earlist = Column(Float)
    latest_destination_time = Column(Float)
    laden_paths = Column(String)  # 存储为逗号分隔的字符串
    number_of_laden_path = Column(Integer)
    empty_paths = Column(String)  # 存储为逗号分隔的字符串
    number_of_empty_path = Column(Integer)

    def get_laden_paths_list(self):
        """获取重箱路径列表"""
        return [] if self.laden_paths == '0' else [int(x) for x in self.laden_paths.split(',')]

    def get_empty_paths_list(self):
        """获取空箱路径列表"""
        return [] if self.empty_paths == '0' else [int(x) for x in self.empty_paths.split(',')]

####################################################################################


# 数据库初始化
def update_database_schema():
    """更新数据库表结构，添加缺失的列"""
    try:
        # 创建数据库连接
        engine = create_engine('sqlite:///ships.db')
        
        # 创建所有表（如果不存在）
        Base.metadata.create_all(engine)
        
        # 检查并添加缺失的列
        with engine.connect() as conn:
            # 检查paths表是否存在port_path列
            result = conn.execute(text("PRAGMA table_info(paths)"))
            columns = [row[1] for row in result.fetchall()]
            
            # 如果port_path列不存在，添加它
            if columns and 'port_path' not in columns:
                conn.execute(text("ALTER TABLE paths ADD COLUMN port_path TEXT"))
                logger.info("已添加 port_path 列到 paths 表")
            
            # 如果container_path_id列不存在，添加它
            if columns and 'container_path_id' not in columns:
                conn.execute(text("ALTER TABLE paths ADD COLUMN container_path_id INTEGER"))
                logger.info("已添加 container_path_id 列到 paths 表")
            
            conn.commit()
        
        logger.info("数据库表结构更新完成")
        return engine
    except Exception as e:
        logger.error(f"更新数据库表结构失败: {str(e)}")
        raise

# 初始化数据库
engine = update_database_schema()
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/overview')
def overview():
    return render_template('overview.html')

@app.route('/data')
def data():
    return render_template('data.html')

@app.route('/optimization')
def optimization():
    return render_template('optimization.html')

@app.route('/analysis')
def analysis():
    return render_template('analysis.html')


####################################################################################
# 数据读取
# GET接口
# 每个接口返回数据库中所有数据
@app.route('/api/ships')
def get_ships():
    session = Session()
    ships = session.query(Ship).all()
    result = [s.__dict__ for s in ships]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)


@app.route('/api/routes')
def get_routes():
    session = Session()
    routes = session.query(Route).all()
    result = [r.__dict__ for r in routes]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@app.route('/api/ports')
def get_ports():
    session = Session()
    ports = session.query(Port).all()
    result = [p.__dict__ for p in ports]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@app.route('/api/nodes')
def get_nodes():
    session = Session()
    nodes = session.query(Node).all()
    result = [n.__dict__ for n in nodes]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@app.route('/api/transship')
def get_transship():
    session = Session()
    arcs = session.query(TransshipArc).all()
    result = [a.__dict__ for a in arcs]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@app.route('/api/traveling')
def get_traveling():
    session = Session()
    arcs = session.query(TravelingArc).all()
    result = [a.__dict__ for a in arcs]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@app.route('/api/paths')
def get_paths():
    session = Session()
    paths = session.query(Path).all()
    result = [p.__dict__ for p in paths]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@app.route('/api/requests')
def get_requests():
    session = Session()
    reqs = session.query(Request).all()
    result = [r.__dict__ for r in reqs]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

####################################################################################


@app.route('/api/import', methods=['POST'])
def import_data():
    try:
        data = request.get_json()
        # 处理导入数据
        return jsonify({'status': 'success', 'message': '数据导入成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/export')
def export_data():
    try:
        data_type = request.args.get('type')
        format = request.args.get('format', 'json')
        # 处理导出数据
        return jsonify({'status': 'success', 'message': '数据导出成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400


class LogCapture:
            def __init__(self, callback):
                self.callback = callback
                self.buffer = StringIO()
                
            def write(self, message):
                self.buffer.write(message)
                if message.strip():
                    self.callback(message.strip())
                    
            def flush(self):
                pass


####################################################################################
# 数据导入
# 导入接口（POST）
# 每个接口支持txt/csv格式，导入时会清空表再批量写入
@app.route('/api/import/ships', methods=['POST'])
def import_ships():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "没有上传文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400
    file_format = request.form.get('format', 'csv')
    if not file.filename.endswith(f'.{file_format}'):
        return jsonify({"status": "error", "message": f"文件格式必须是 {file_format}"}), 400
    try:
        # 解析文件内容（与原逻辑一致）
        if file_format == 'csv':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            headers = lines[0].strip().split(',')
            data = []
            for line in lines[1:]:
                values = line.strip().split(',')
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))
        elif file_format == 'txt':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            headers = lines[0].strip().split('\t')
            data = []
            for line in lines[1:]:
                values = line.strip().split('\t')
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))
        elif file_format == 'json':
            data = json.loads(file.read().decode('utf-8'))
            if not isinstance(data, list):
                data = [data]
        else:
            return jsonify({"status": "error", "message": "不支持的文件格式"}), 400
        required_fields = ['VesselID', 'Capacity', 'OperatingCost', 'RouteID', 'MaxNum']
        ships_data = []
        for item in data:
            if not all(field in item for field in required_fields):
                continue
            try:
                ship = {
                    "id": f"SH{int(float(item['VesselID'])):03d}",
                    "name": f"船舶{int(float(item['VesselID']))}",
                    "capacity": float(item['Capacity']),
                    "operating_cost": float(item['OperatingCost']),
                    "route_id": int(float(item['RouteID'])),
                    "max_num": int(float(item['MaxNum'])),
                    "type": "集装箱船",
                    "status": "待航",
                    "current_port": "上海港",
                    "next_port": "新加坡港",
                    "eta": "2024-05-20 08:00:00",
                    "speed": 20.0
                }
                ships_data.append(ship)
            except (ValueError, KeyError):
                continue
        if not ships_data:
            return jsonify({"status": "error", "message": "没有找到有效的船舶数据"}), 400
        # 写入数据库
        session = Session()
        session.query(Ship).delete()
        for item in ships_data:
            session.add(Ship(**item))
        session.commit()
        session.close()
        return jsonify({"status": "success", "message": f"成功导入 {len(ships_data)} 条船舶数据"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"导入失败: {str(e)}"}), 500

@app.route('/api/import/routes', methods=['POST'])
def import_routes():
    if 'file' not in request.files:
        return jsonify({
            "status": "error",
            "message": "没有上传文件"
        }), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            "status": "error",
            "message": "未选择文件"
        }), 400
    
    # 获取文件格式
    file_format = request.form.get('format', 'txt')
    if not file.filename.endswith(f'.{file_format}'):
        return jsonify({
            "status": "error",
            "message": f"文件格式必须是 {file_format}"
        }), 400
    
    try:
        routes_data = []
        if file_format == 'txt':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            for line in lines[1:]:  # 跳过标题行
                parts = line.strip().split('\t')
                if len(parts) < 6:
                    continue
                # 只处理有有效ID的行
                if not parts[0].strip().isdigit():
                    continue
                try:
                    route = {
                        "id": int(parts[0]),
                        "number_of_ports": int(parts[1]) if parts[1].strip() else 0,
                        "ports": parts[2] if parts[2].strip() else "",
                        "number_of_calls": int(parts[3]) if parts[3].strip() else 0,
                        "ports_of_call": parts[4] if parts[4].strip() else "",
                        "times": parts[5] if parts[5].strip() else ""
                    }
                    routes_data.append(route)
                except ValueError:
                    continue
        elif file_format == 'csv':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            headers = lines[0].strip().split(',')
            for line in lines[1:]:
                values = line.strip().split(',')
                if len(values) == len(headers):
                    data = dict(zip(headers, values))
                    # 只处理有有效ID的行
                    if not data.get('ShippingRouteID') or not data['ShippingRouteID'].strip().isdigit():
                        continue
                    try:
                        route = {
                            "id": int(data['ShippingRouteID']),
                            "number_of_ports": int(data.get('NumberofPorts', '0') or '0'),
                            "ports": data.get('Ports', '') or '',
                            "number_of_calls": int(data.get('NumberofCall', '0') or '0'),
                            "ports_of_call": data.get('PortsofCall', '') or '',
                            "times": data.get('Time', '') or ''
                        }
                        routes_data.append(route)
                    except ValueError:
                        continue
        elif file_format == 'json':
            data = json.loads(file.read().decode('utf-8'))
            if not isinstance(data, list):
                data = [data]
            for item in data:
                # 只处理有有效ID的行
                if not str(item.get('ShippingRouteID', '')).strip().isdigit():
                    continue
                try:
                    route = {
                        "id": int(item.get('ShippingRouteID', 0)),
                        "number_of_ports": int(item.get('NumberofPorts', 0) or 0),
                        "ports": item.get('Ports', '') or '',
                        "number_of_calls": int(item.get('NumberofCall', 0) or 0),
                        "ports_of_call": item.get('PortsofCall', '') or '',
                        "times": item.get('Time', '') or ''
                    }
                    routes_data.append(route)
                except ValueError:
                    continue
        else:
            return jsonify({
                "status": "error",
                "message": "不支持的文件格式"
            }), 400
        
        if not routes_data:
            return jsonify({
                "status": "error",
                "message": "没有找到有效的航线数据"
            }), 400
        
        # 写入数据库
        session = Session()
        session.query(Route).delete()
        for route in routes_data:
            new_route = Route(
                id=route['id'],
                number_of_ports=route['number_of_ports'],
                ports=route['ports'],
                number_of_calls=route['number_of_calls'],
                ports_of_call=route['ports_of_call'],
                times=route['times']
            )
            session.add(new_route)
        session.commit()
        session.close()
        
        # 更新全局数据
        global ROUTES_DATA
        ROUTES_DATA = routes_data
        
        return jsonify({
            "status": "success",
            "message": f"成功导入 {len(routes_data)} 条航线数据",
            "data": routes_data
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"导入失败: {str(e)}"
        }), 500

@app.route('/api/import/ports', methods=['POST'])
def import_ports():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "没有上传文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400
    file_format = request.form.get('format', 'txt')
    if not file.filename.endswith(f'.{file_format}'):
        return jsonify({"status": "error", "message": f"文件格式必须是 {file_format}"}), 400
    try:
        # 解析文件内容
        if file_format == 'txt':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            headers = lines[0].strip().split('\t')
            data = []
            for line in lines[1:]:
                values = line.strip().split('\t')
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))
        elif file_format == 'csv':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            headers = lines[0].strip().split(',')
            data = []
            for line in lines[1:]:
                values = line.strip().split(',')
                if len(values) == len(headers):
                    data.append(dict(zip(headers, values)))
        elif file_format == 'json':
            data = json.loads(file.read().decode('utf-8'))
            if not isinstance(data, list):
                data = [data]
        else:
            return jsonify({"status": "error", "message": "不支持的文件格式"}), 400
        # 写入数据库
        session = Session()
        session.query(Port).delete()
        for item in data:
            port = Port(
                id=int(item['PortID']),
                name=item['Port'],
                whether_trans=int(item['WhetherTrans']),
                region=item['Region'],
                group=int(item['Group'])
            )
            session.add(port)
        session.commit()
        session.close()
        return jsonify({"status": "success", "message": f"成功导入 {len(data)} 条港口数据"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"导入失败: {str(e)}"}), 500

@app.route('/api/import/nodes', methods=['POST'])
def import_nodes_data():
    file = request.files.get('file')
    file_format = request.form.get('format')
    if not file:
        return jsonify({'status': 'fail', 'message': '未上传文件'}), 400
    content = file.read().decode('utf-8')
    lines = content.strip().split('\n')
    headers = lines[0].strip().split('\t' if file_format == 'txt' else ',')
    data = []
    for line in lines[1:]:
        values = line.strip().split('\t' if file_format == 'txt' else ',')
        if len(values) == len(headers):
            data.append(dict(zip(headers, values)))
    session = Session()
    session.query(Node).delete()
    for item in data:
        node = Node(
            id=int(item['ID']),
            route=int(item['Route']),
            call=int(item['Call']),
            port=item['Port'],
            round_trip=int(item['RoundTrip']),
            time=float(item['Time'])
        )
        session.add(node)
    session.commit()
    session.close()
    return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条时空节点数据'})

@app.route('/api/import/transship', methods=['POST'])
def import_transship_data():
    file = request.files.get('file')
    file_format = request.form.get('format')
    if not file:
        return jsonify({'status': 'fail', 'message': '未上传文件'}), 400
    content = file.read().decode('utf-8')
    lines = content.strip().split('\n')
    headers = lines[0].strip().split('\t' if file_format == 'txt' else ',')
    data = []
    for line in lines[1:]:
        values = line.strip().split('\t' if file_format == 'txt' else ',')
        if len(values) == len(headers):
            data.append(dict(zip(headers, values)))
    session = Session()
    session.query(TransshipArc).delete()
    for item in data:
        arc = TransshipArc(
            id=int(item['TransshipArcID']),
            port=item['Port'],
            origin_node_id=int(item['OriginNodeID']),
            origin_time=float(item['OriginTime']),
            transship_time=float(item['TransshipTime']),
            destination_node_id=int(item['DestinationNodeID']),
            destination_time=float(item['DestinationTime']),
            from_route=int(item['FromRoute']),
            to_route=int(item['ToRoute'])
        )
        session.add(arc)
    session.commit()
    session.close()
    return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条转运弧数据'})

@app.route('/api/import/traveling', methods=['POST'])
def import_traveling_data():
    file = request.files.get('file')
    file_format = request.form.get('format')
    if not file:
        return jsonify({'status': 'fail', 'message': '未上传文件'}), 400
    content = file.read().decode('utf-8')
    lines = content.strip().split('\n')
    headers = lines[0].strip().split('\t' if file_format == 'txt' else ',')
    data = []
    for line in lines[1:]:
        values = line.strip().split('\t' if file_format == 'txt' else ',')
        if len(values) == len(headers):
            data.append(dict(zip(headers, values)))
    session = Session()
    session.query(TravelingArc).delete()
    for item in data:
        arc = TravelingArc(
            id=int(item['TravelingArcID']),
            route=int(item['Route']),
            origin_node_id=int(item['OriginNodeID']),
            origin_call=int(item['OriginCall']),
            origin_port=item['OriginPort'],
            round_trip=int(item['RoundTrip']),
            origin_time=float(item['OriginTime']),
            traveling_time=float(item['TravelingTime']),
            destination_node_id=int(item['DestinationNodeID']),
            destination_call=int(item['DestinationCall']),
            destination_port=item['DestinationPort'],
            destination_time=float(item['DestinationTime'])
        )
        session.add(arc)
    session.commit()
    session.close()
    return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条航段弧数据'})

@app.route('/api/import/paths', methods=['POST'])
def import_paths_data():
    file = request.files.get('file')
    file_format = request.form.get('format')
    if not file:
        return jsonify({'status': 'fail', 'message': '未上传文件'}), 400
    
    try:
        content = file.read().decode('utf-8')
        lines = content.strip().split('\n')
        headers = lines[0].strip().split('\t' if file_format == 'txt' else ',')
        data = []
        
        for line in lines[1:]:
            values = line.strip().split('\t' if file_format == 'txt' else ',')
            if len(values) == len(headers):
                row_data = dict(zip(headers, values))
                # 处理列表字段
                for field in ['TransshipPort', 'TransshipTime', 'PortPath', 'ArcsID']:
                    if field in row_data:
                        if row_data[field] == '0':
                            row_data[field] = []
                        else:
                            if field in ['TransshipTime', 'ArcsID']:
                                row_data[field] = [int(x) for x in row_data[field].split(',')]
                            else:
                                row_data[field] = row_data[field].split(',')
                data.append(row_data)
        
        session = Session()
        session.query(Path).delete()
        
        for item in data:
            try:
                # 确保所有必要的字段都存在
                path_data = {
                    'id': int(item['ContainerPathID']),
                    'container_path_id': int(item['ContainerPathID']),
                    'origin_port': item['OriginPort'],
                    'origin_time': int(item['OriginTime']),
                    'destination_port': item['DestinationPort'],
                    'destination_time': int(item['DestinationTime']),
                    'path_time': int(item['PathTime']),
                    'transship_port': ','.join(item['TransshipPort']) if item['TransshipPort'] else '0',
                    'transship_time': ','.join(map(str, item['TransshipTime'])) if item['TransshipTime'] else '0',
                    'port_path': ','.join(item['PortPath']) if item['PortPath'] else '0',
                    'arcs_id': ','.join(map(str, item['ArcsID'])) if item['ArcsID'] else '0'
                }
                
                path = Path(**path_data)
                session.add(path)
                
            except Exception as e:
                logger.error(f"处理路径数据时出错: {str(e)}, 数据: {item}")
                continue
        
        session.commit()
        logger.info(f"成功导入 {len(data)} 条路径数据")
        return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条路径数据'})
        
    except Exception as e:
        logger.error(f"导入路径数据失败: {str(e)}")
        return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'}), 500
        
    finally:
        if 'session' in locals():
            session.close()

@app.route('/api/import/requests', methods=['POST'])
def import_requests_data():
    file = request.files.get('file')
    file_format = request.form.get('format')
    if not file:
        return jsonify({'status': 'fail', 'message': '未上传文件'}), 400
    content = file.read().decode('utf-8')
    lines = content.strip().split('\n')
    headers = lines[0].strip().split('\t' if file_format == 'txt' else ',')
    data = []
    for line in lines[1:]:
        values = line.strip().split('\t' if file_format == 'txt' else ',')
        if len(values) == len(headers):
            row_data = dict(zip(headers, values))
            # 处理列表字段
            for field in ['LadenPaths', 'EmptyPaths']:
                if field in row_data:
                    if row_data[field] == '0':
                        row_data[field] = []
                    else:
                        row_data[field] = [int(x) for x in row_data[field].split(',')]
            data.append(row_data)
    session = Session()
    session.query(Request).delete()
    for item in data:
        req = Request(
            id=int(item['RequestID']),
            origin_port=item['OriginPort'],
            destination_port=item['DestinationPort'],
            w_i_earlist=float(item['WiEarliest']),
            latest_destination_time=float(item['LatestDestinationTime']),
            laden_paths=','.join(map(str, item['LadenPaths'])) if item['LadenPaths'] else '0',
            number_of_laden_path=int(item['NumberOfLadenPath']),
            empty_paths=','.join(map(str, item['EmptyPaths'])) if item['EmptyPaths'] else '0',
            number_of_empty_path=int(item['NumberOfEmptyPath'])
        )
        session.add(req)
    session.commit()
    session.close()
    return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条需求序列数据'})

####################################################################################

@app.route('/api/schedule', methods=['POST'])
def update_schedule():
    data = request.json
    
    # 验证输入数据
    if not algorithm_interface.validate_input_data(data):
        return jsonify({
            "status": "error",
            "message": "输入数据无效"
        }), 400
    
    # 运行调度算法
    result = algorithm_interface.run_scheduling_algorithm(
        ships_data=data.get('ships', []),
        ports_data=data.get('ports', [])
    )
    
    if result['status'] == 'error':
        return jsonify(result), 500
        
    return jsonify(result)

# 数据分析API
@app.route('/api/analysis')
def get_analysis():
    analysis_type = request.args.get('type', 'performance')
    time_range = request.args.get('range', 'day')
    data_source = request.args.get('source', 'all')
    
    try:
        # 获取分析数据
        metrics = {
            'avg_response_time': '2.5h',
            'resource_utilization': '85%',
            'cost_efficiency': '92%',
            'emission_intensity': '0.8t/100km'
        }
        
        # 趋势数据
        trend = {
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'metric1': [100, 120, 110, 130, 125],
            'metric2': [80, 85, 90, 88, 92],
            'metric3': [60, 65, 70, 68, 72]
        }
        
        # 分布数据
        distribution = [
            {'name': '类别A', 'value': 40},
            {'name': '类别B', 'value': 30},
            {'name': '类别C', 'value': 20},
            {'name': '类别D', 'value': 10}
        ]
        
        # 对比数据
        comparison = {
            'categories': ['指标1', '指标2', '指标3', '指标4'],
            'actual': [80, 85, 90, 95],
            'target': [75, 80, 85, 90]
        }
        
        return jsonify({
            'status': 'success',
            'metrics': metrics,
            'trend': trend,
            'distribution': distribution,
            'comparison': comparison
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 添加统计数据的API
@app.route('/api/stats')
def get_stats():
    try:
        # 从数据库读取统计数据
        session = Session()
        port_count = session.query(Port).count()
        route_count = session.query(Route).count()
        ship_count = session.query(Ship).count()
        active_ship_count = session.query(Ship).filter(Ship.status == '在航').count()
        session.close()
        
        return jsonify({
            'status': 'success',
            'port_count': port_count,
            'route_count': route_count,
            'ship_count': ship_count,
            'active_ship_count': active_ship_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 添加网络拓扑数据的API
@app.route('/api/network')
def get_network():
    try:
        # 颜色列表
        def get_color(idx):
            color_list = [
                '#5470C6', '#91CC75', '#FAC858', '#EE6666', '#73C0DE',
                '#3BA272', '#FC8452', '#9A60B4', '#EA7CCC', '#FFB300',
                '#00BFFF', '#FF69B4', '#8A2BE2', '#20B2AA', '#FFA500'
            ]
            return color_list[idx % len(color_list)]

        nodes = []
        node_set = set()
        links = []
        legend = []
        color_map = {}

        # 为每条航线分配颜色
        for idx, route in enumerate(ROUTES_DATA):
            color = get_color(idx)
            color_map[route['id']] = color
            # 兼容 ports_of_call 可能为字符串或列表
            ports_of_call = route['ports_of_call']
            if isinstance(ports_of_call, str):
                ports_of_call = [p.strip() for p in ports_of_call.split(',') if p.strip()]
            legend.append({'name': f'航线{route["id"]}', 'color': color, 'ports': ports_of_call})

            # 添加港口节点
            for port in ports_of_call:
                if port not in node_set:
                    node_set.add(port)
                    nodes.append({'name': port, 'category': 0, 'symbolSize': 50})

            # 按顺序连接
            times = route['times']
            if isinstance(times, str):
                times = [float(t) for t in times.split(',') if t.strip()]
            ports = ports_of_call
            for i in range(len(ports) - 1):
                links.append({
                    'source': ports[i],
                    'target': ports[i + 1],
                    'value': times[i] if i < len(times) else 1,
                    'routeId': route['id'],
                    'lineStyle': {'color': color, 'width': 3, 'opacity': 0.8},
                    'legendName': f'航线{route["id"]}'
                })

        return jsonify({
            'status': 'success',
            'nodes': nodes,
            'links': links,
            'legend': legend
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# 添加状态分布数据的API
@app.route('/api/status')
def get_status():
    try:
        # 从数据库统计船舶状态
        session = Session()
        status_count = {
            '在航': session.query(Ship).filter(Ship.status == '在航').count(),
            '停泊': session.query(Ship).filter(Ship.status == '停泊').count(),
            '待航': session.query(Ship).filter(Ship.status == '待航').count(),
            '维修': session.query(Ship).filter(Ship.status == '维修').count()
        }
        session.close()
        
        # 转换为饼图数据格式
        status_data = [
            {'name': status, 'value': count}
            for status, count in status_count.items()
        ]
        
        return jsonify({
            'status': 'success',
            'data': status_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 添加吞吐量数据的API
@app.route('/api/throughput')
def get_throughput():
    try:
        # 计算每个港口的吞吐量
        port_throughput = {}
        for route in ROUTES_DATA:
            for port in route['ports']:
                if port not in port_throughput:
                    port_throughput[port] = 0
                port_throughput[port] += 1
        
        # 转换为图表数据格式
        ports = list(port_throughput.keys())
        values = list(port_throughput.values())
        
        return jsonify({
            'status': 'success',
            'ports': ports,
            'values': values
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


####################################################################################
### 优化算法
####################################################################################

@app.route('/api/optimize', methods=['POST'])
def optimize():
    try:
        # 创建日志列表用于存储所有日志
        log_messages = []
        
        def log_callback(message):
            log_messages.append(message)
            print(message)  # 同时在控制台打印
            # 将日志消息添加到队列以便通过SSE发送
            log_queue.put(message)
            
        log_callback("="*50)
        log_callback("开始处理优化请求...")
        
        data = request.get_json()
        log_callback(f"接收到的参数: {data}")
        
        # 提取参数
        model_params = {
            'time_window': int(data.get('time_window', 60)),
            'robustness': float(data.get('robustness', 1.0)),
            'demand_fluctuation': float(data.get('demand_fluctuation', 0.1)),
            'empty_rent_cost': float(data.get('empty_rent_cost', 10)),
            'penalty_coeff': float(data.get('penalty_coeff', 100)),
            'port_load_cost': float(data.get('port_load_cost', 5)),
            'port_unload_cost': float(data.get('port_unload_cost', 5)),
            'port_transship_cost': float(data.get('port_transship_cost', 8)),
            'laden_stay_cost': float(data.get('laden_stay_cost', 2)),
            'laden_stay_free_time': int(data.get('laden_stay_free_time', 3)),
            'empty_stay_cost': float(data.get('empty_stay_cost', 1)),
            'empty_stay_free_time': int(data.get('empty_stay_free_time', 3)),
        }
        log_callback(f"模型参数读取完成")
        
        algo_params = {
            'solver': data.get('solver', 'cplex'),
            'max_iter': int(data.get('max_iter', 100)),
            'max_time': int(data.get('max_time', 600)),
            'mip_gap': float(data.get('mip_gap', 0.01)),
        }
        log_callback(f"算法参数读取完成")
        
        try:
            log_callback("开始执行优化计算...")
            
            # 更新默认设置
            log_callback("更新默认设置...")
            DefaultSetting.update_setting_from_dict(model_params)
            DefaultSetting.update_setting_from_dict(algo_params)

            logger.info("开始执行算法...")
            
            # 初始化输入数据
            input_data = InputData()
            
            # 读取数据
            reader = ReadData(
                path="data/",
                input_data=input_data,
                time_horizon=data.get('time_horizon', DefaultSetting.DEFAULT_TIME_HORIZON),
                use_db=True,
                db_path="ships.db"
            )
            logger.info("数据读取完成")
            
            # param = Parameter()
            # GenerateParameter(input_data=input_data, 
            #                   param=param, 
            #                   time_horizon=data.get('time_horizon', DefaultSetting.DEFAULT_TIME_HORIZON), 
            #                   uncertain_degree=data.get('demand_fluctuation', DefaultSetting.DEFAULT_UNCERTAIN_DEGREE))
            # logger.info("参数生成完成")
            
            # # 执行算法
            result = {}
            # if data.get('algorithm', 'bd') == "bd":
            #     logger.info("使用Benders分解算法")
            #     bd = BendersDecomposition(input_data=input_data, param=param)
            #     result = bd.solve()
            # elif data.get('algorithm', 'ccg') == "ccg":
            #     logger.info("使用列生成算法")
            #     cp = CCG(input_data=input_data, param=param)
            #     result = cp.solve()
            # elif data.get('algorithm', 'bdpap') == "bdpap":
            #     logger.info("使用带PAP的Benders分解算法")
            #     bdpap = BendersDecompositionWithPAP(input_data=input_data, param=param)
            #     result = bdpap.solve()
            # elif data.get('algorithm', 'ccgpap') == "ccgpap":
            #     logger.info("使用带PAP的列生成算法")
            #     ccgpap = CCGwithPAP(input_data=input_data, param=param)
            #     result = ccgpap.solve()
            # logger.info("算法执行完成")
            # # 执行优化
            
            log_callback("优化完成！")
            
            return jsonify({
                'status': 'success',
                'result_time': f"{result.get('time', 0):.1f}s",
                'total_cost': result.get('objective', 0),
                'oc': result.get('laden_cost', 0),
                'lcec': result.get('empty_cost', 0),
                'rc': result.get('rental_cost', 0),
                'pc': result.get('penalty_cost', 0),
                'log': '\n'.join(log_messages)
            })
        except Exception as e:
            logger.error(f"算法执行失败: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f"算法执行失败: {str(e)}",
                'log': '\n'.join(log_messages)
            }), 500
            
    except Exception as e:
        error_msg = f"优化过程出错: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500




@app.route('/api/run_algorithm', methods=['POST'])
def run_algorithm():
    """
    运行算法接口
    
    请求体格式：
    {
        "algorithm_params": {
            "time_horizon": 30,
            "algorithm": "bd",
            "use_db": true,
            "db_path": "path/to/database.db",
            "other_params": {...}
        }
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()
        algorithm_params = data.get('algorithm_params', {})
        
        # 记录请求参数
        logger.info(f"收到算法参数: {json.dumps(algorithm_params, indent=2)}")
        
        # 构建运行命令
        run_script = os.path.join(os.path.dirname(__file__), '..', 'src-py', 'run.py')
        
        # 将参数转换为命令行参数
        cmd = ['python', run_script]
        
        # 处理布尔值参数
        if algorithm_params.get('use_db', False):
            cmd.append('--use_db')
        
        # 处理其他参数
        param_mapping = {
            ## 模型参数
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
            ## 算法参数
            'algorithm': '--algorithm',
            'max_iter': '--max_iter',
            'max_time': '--max_time',
            'mip_gap': '--mip_gap',

        }
        
        for param, value in algorithm_params.items():
            if param in param_mapping and value is not None:
                cmd.extend([param_mapping[param], str(value)])
        
        # 运行算法
        logger.info(f"执行命令: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 获取输出
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("算法执行成功")
            return jsonify({
                'status': 'success',
                'message': '算法执行成功',
                'output': stdout
            })
        else:
            logger.error(f"算法执行失败: {stderr}")
            return jsonify({
                'status': 'error',
                'message': '算法执行失败',
                'error': stderr
            }), 500
            
    except Exception as e:
        logger.error(f"运行算法时出错: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '服务器内部错误',
            'error': str(e)
        }), 500



####################################################################################
### 初始化数据
####################################################################################

def load_initial_data():
    """应用启动时加载初始数据"""
    try:
        session = Session()
        # 加载船舶数据
        ships = session.query(Ship).all()
        global SHIPS_DATA
        SHIPS_DATA = [s.__dict__ for s in ships]
        for ship in SHIPS_DATA:
            ship.pop('_sa_instance_state', None)
            
        # 加载航线数据
        routes = session.query(Route).all()
        global ROUTES_DATA
        ROUTES_DATA = [r.__dict__ for r in routes]
        for route in ROUTES_DATA:
            route.pop('_sa_instance_state', None)
            
        # 加载港口数据
        ports = session.query(Port).all()
        global PORTS_DATA
        PORTS_DATA = [p.__dict__ for p in ports]
        for port in PORTS_DATA:
            port.pop('_sa_instance_state', None)
            
        # 加载时空节点数据
        nodes = session.query(Node).all()
        global NODES_DATA
        NODES_DATA = [n.__dict__ for n in nodes]
        for node in NODES_DATA:
            node.pop('_sa_instance_state', None)

        # 加载转运弧数据
        transship_arcs = session.query(TransshipArc).all()
        global TRANS_DATA
        TRANS_DATA = [a.__dict__ for a in transship_arcs]
        for arc in TRANS_DATA:
            arc.pop('_sa_instance_state', None)

        # 加载航段弧数据
        traveling_arcs = session.query(TravelingArc).all()
        global TRAVEL_DATA
        TRAVEL_DATA = [a.__dict__ for a in traveling_arcs]
        for arc in TRAVEL_DATA:
            arc.pop('_sa_instance_state', None)

        # 加载候选运输路径数据
        paths = session.query(Path).all()
        global PATHS_DATA
        PATHS_DATA = [p.__dict__ for p in paths]
        for path in PATHS_DATA:
            path.pop('_sa_instance_state', None)


        # 加载需求序列数据
        requests = session.query(Request).all()
        global REQUESTS_DATA
        REQUESTS_DATA = [r.__dict__ for r in requests]
        for req in REQUESTS_DATA:
            req.pop('_sa_instance_state', None)
            
            
        session.close()
        logger.info("初始数据加载完成")
    except Exception as e:
        logger.error(f"初始数据加载失败: {str(e)}")

# 添加SSE端点用于实时日志流
@app.route('/api/log-stream')
def log_stream():
    def generate():
        # 发送初始事件保持连接
        yield "data: {\"message\": \"连接已建立，等待日志...\"}\n\n"
        
        while True:
            try:
                # 非阻塞方式获取日志消息
                message = log_queue.get(block=False)
                if message:
                    yield f"data: {json.dumps({'message': message})}\n\n"
            except queue.Empty:
                # 队列为空，发送保持连接的消息
                yield "data: {\"keepalive\": true}\n\n"
            
            time.sleep(0.1)  # 短暂休眠避免CPU过载
    
    return Response(generate(), mimetype="text/event-stream")

if __name__ == '__main__':
    # 启动时加载数据
    load_initial_data()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True) 