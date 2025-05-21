from flask import Flask, render_template, jsonify, request
import json
import pandas as pd
from algorithm_interface import AlgorithmInterface
from flask_cors import CORS
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker
import logging

app = Flask(__name__)
CORS(app)
algorithm_interface = AlgorithmInterface()

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

engine = create_engine('sqlite:///ships.db')
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

@app.route('/api/ships')
def get_ships():
    session = Session()
    ships = session.query(Ship).all()
    result = [s.__dict__ for s in ships]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

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

@app.route('/api/optimize', methods=['POST'])
def optimize():
    try:
        data = request.get_json()
        result = algorithm_interface.run_scheduling_algorithm(data, data.get('algorithm_type', 'genetic'))
        return jsonify(result)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/api/routes')
def get_routes():
    return jsonify(ROUTES_DATA)

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
        required_fields = ['VesselID', 'Capacity', 'OperatingCost', 'RouteID', 'maxNum']
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
                    "max_num": int(float(item['maxNum'])),
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

@app.route('/api/ports')
def get_ports():
    session = Session()
    ports = session.query(Port).all()
    result = [p.__dict__ for p in ports]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

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
            
        session.close()
        logger.info("初始数据加载完成")
    except Exception as e:
        logger.error(f"初始数据加载失败: {str(e)}")

if __name__ == '__main__':
    # 启动时加载数据
    load_initial_data()
    app.run(host='0.0.0.0', port=5000, debug=True) 