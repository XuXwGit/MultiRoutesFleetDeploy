from flask import Blueprint, request, jsonify
from database import Session
from models import Ship, Route, Port, Node, TransshipArc, TravelingArc, Path, VesselPath, Request, DemandRange
import json
import logging

data_bp = Blueprint('data', __name__)

# 数据查询API
@data_bp.route('/api/ships')
def get_ships():
    session = Session()
    ships = session.query(Ship).all()
    result = [s.__dict__ for s in ships]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/routes')
def get_routes():
    session = Session()
    routes = session.query(Route).all()
    result = [r.__dict__ for r in routes]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/ports')
def get_ports():
    session = Session()
    ports = session.query(Port).all()
    result = [p.__dict__ for p in ports]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/nodes')
def get_nodes():
    session = Session()
    nodes = session.query(Node).all()
    result = [n.__dict__ for n in nodes]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/transship')
def get_transship():
    session = Session()
    arcs = session.query(TransshipArc).all()
    result = [a.__dict__ for a in arcs]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/traveling')
def get_traveling():
    session = Session()
    arcs = session.query(TravelingArc).all()
    result = [a.__dict__ for a in arcs]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/paths')
def get_paths():
    session = Session()
    paths = session.query(Path).all()
    result = [p.__dict__ for p in paths]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/requests')
def get_requests():
    session = Session()
    reqs = session.query(Request).all()
    result = [r.__dict__ for r in reqs]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)

@data_bp.route('/api/demand_range')
@data_bp.route('/api/demandrange')
def get_demandrange():
    session = Session()
    ranges = session.query(DemandRange).all()
    result = [r.__dict__ for r in ranges]
    for r in result:
        r.pop('_sa_instance_state', None)
    session.close()
    return jsonify(result)




@data_bp.route('/api/import', methods=['POST'])
def import_data():
    try:
        data = request.get_json()
        # 处理导入数据
        return jsonify({'status': 'success', 'message': '数据导入成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@data_bp.route('/api/export')
def export_data():
    try:
        data_type = request.args.get('type')
        format = request.args.get('format', 'json')
        # 处理导出数据
        return jsonify({'status': 'success', 'message': '数据导出成功'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400

@data_bp.route('/api/import/ships', methods=['POST'])
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
                    "id": int(float(item['VesselID'])),
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

@data_bp.route('/api/import/routes', methods=['POST'])
def import_routes():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "没有上传文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400
    file_format = request.form.get('format', 'txt')
    if not file.filename.endswith(f'.{file_format}'):
        return jsonify({"status": "error", "message": f"文件格式必须是 {file_format}"}), 400
    try:
        routes_data = []
        if file_format == 'txt':
            content = file.read().decode('utf-8')
            lines = content.strip().split('\n')
            for line in lines[1:]:
                parts = line.strip().split('\t')
                if len(parts) < 6:
                    continue
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
            return jsonify({"status": "error", "message": "不支持的文件格式"}), 400
        if not routes_data:
            return jsonify({"status": "error", "message": "没有找到有效的航线数据"}), 400
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
        return jsonify({"status": "success", "message": f"成功导入 {len(routes_data)} 条航线数据"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"导入失败: {str(e)}"}), 500

@data_bp.route('/api/import/ports', methods=['POST'])
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

@data_bp.route('/api/import/nodes', methods=['POST'])
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

@data_bp.route('/api/import/transship', methods=['POST'])
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

@data_bp.route('/api/import/traveling', methods=['POST'])
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

@data_bp.route('/api/import/vesselpaths', methods=['POST'])
def import_vesselpaths_data():
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
                data.append(dict(zip(headers, values)))
        session = Session()
        session.query(VesselPath).delete()
        for item in data:
            vessel_path = VesselPath(
                id=int(item['VesselPathID']),
                vessel_route_id=int(item['ShippingRouteID']),
                number_of_arcs=int(item['NumberOfArcs']),
                arcs_id=item['ArcIDs'],
                origin_time=int(item['OriginTime']),
                destination_time=int(item['DestinationTime'])
            )
            session.add(vessel_path)
        session.commit()
        session.close()
        return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条航行轮回路径数据'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'}), 500  
    finally:
        if 'session' in locals():
            session.close()

@data_bp.route('/api/import/paths', methods=['POST'])
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
                    'port_path_length': int(item.get('PortPathLength', len(item['PortPath']))),
                    'port_path': ','.join(item['PortPath']) if item['PortPath'] else '0',
                    'arcs_id': ','.join(map(str, item['ArcsID'])) if item['ArcsID'] else '0',
                    'arcs_length': len(item['ArcsID'])
                }
                path = Path(**path_data)
                session.add(path)
            except Exception as e:
                logging.error(f"处理路径数据时出错: {str(e)}, 数据: {item}")
                continue
        session.commit()
        logging.info(f"成功导入 {len(data)} 条路径数据")
        return jsonify({'status': 'success', 'message': f'成功导入 {len(data)} 条路径数据'})
    except Exception as e:
        logging.error(f"导入路径数据失败: {str(e)}")
        return jsonify({'status': 'error', 'message': f'导入失败: {str(e)}'}), 500
    finally:
        if 'session' in locals():
            session.close()

@data_bp.route('/api/import/requests', methods=['POST'])
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
            earliest_pickup_time=float(item['EarliestPickupTime']),
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

@data_bp.route('/api/import/demand_range', methods=['POST'])
@data_bp.route('/api/import/demandrange', methods=['POST'])
def import_demandrange():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "没有上传文件"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "未选择文件"}), 400
    file_format = request.form.get('format', 'txt')
    if not file.filename.endswith(f'.{file_format}'):
        return jsonify({"status": "error", "message": f"文件格式必须是 {file_format}"}), 400
    try:
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
        session = Session()
        session.query(DemandRange).delete()
        for item in data:
            dr = DemandRange(
                origin_region=int(item['OriginRegion']),
                destination_region=int(item['DestinationRegion']),
                demand_lower_bound=int(item['DemandLowerBound']),
                demand_upper_bound=int(item['DemandUpperBound']),
                freight_lower_bound=int(item['FreightLowerBound']),
                freight_upper_bound=int(item['FreightUpperBound'])
            )
            session.add(dr)
        session.commit()
        session.close()
        logging.info(f"success to import demand range")
        return jsonify({"status": "success", "message": f"成功导入 {len(data)} 条需求区间数据"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"导入失败: {str(e)}"}), 500

@data_bp.route('/api/query_paths', methods=['POST'])
def query_paths():
    data = request.get_json()
    origin_port = data.get('origin_port')
    destination_port = data.get('destination_port')
    time_type = data.get('time_type')  # 'depart' or 'arrive'
    time_point = int(data.get('time_point', 0))
    time_window = int(data.get('time_window', 0))

    session = Session()
    query = session.query(Path).filter(
        Path.origin_port == origin_port,
        Path.destination_port == destination_port
    )

    if time_type == 'depart':
        query = query.filter(
            Path.origin_time >= time_point,
            Path.origin_time <= time_point + time_window
        )
    elif time_type == 'arrive':
        query = query.filter(
            Path.destination_time >= time_point - time_window,
            Path.destination_time <= time_point
        )

    paths = query.order_by(Path.path_time.asc()).all()
    result = []
    for p in paths:
        result.append({
            'container_path_id': p.container_path_id,
            'origin_port': p.origin_port,
            'origin_time': p.origin_time,
            'destination_port': p.destination_port,
            'destination_time': p.destination_time,
            'path_time': p.path_time,
            'port_path': p.port_path,
            # 可根据需要补充更多字段
        })
    session.close()
    return jsonify({'status': 'success', 'paths': result})

# 这里继续迁移所有导入导出API（/api/import/*, /api/export等）
# ... 