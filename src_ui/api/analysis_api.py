from flask import Blueprint, jsonify, request
from database import Session
from models import Ship, Route, Port
import logging

analysis_bp = Blueprint('analysis', __name__)

@analysis_bp.route('/api/analysis')
def get_analysis():
    analysis_type = request.args.get('type', 'performance')
    time_range = request.args.get('range', 'day')
    data_source = request.args.get('source', 'all')
    try:
        metrics = {
            'avg_response_time': '2.5h',
            'resource_utilization': '85%',
            'cost_efficiency': '92%',
            'emission_intensity': '0.8t/100km'
        }
        trend = {
            'dates': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
            'metric1': [100, 120, 110, 130, 125],
            'metric2': [80, 85, 90, 88, 92],
            'metric3': [60, 65, 70, 68, 72]
        }
        distribution = [
            {'name': '类别A', 'value': 40},
            {'name': '类别B', 'value': 30},
            {'name': '类别C', 'value': 20},
            {'name': '类别D', 'value': 10}
        ]
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
        return jsonify({'status': 'error', 'message': str(e)}), 500

@analysis_bp.route('/api/stats')
def get_stats():
    try:
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
        return jsonify({'status': 'error', 'message': str(e)}), 500

@analysis_bp.route('/api/network')
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
        from api.data_api import ROUTES_DATA
        nodes = []
        node_set = set()
        links = []
        legend = []
        color_map = {}
        for idx, route in enumerate(ROUTES_DATA):
            color = get_color(idx)
            color_map[route['id']] = color
            ports_of_call = route['ports_of_call']
            if isinstance(ports_of_call, str):
                ports_of_call = [p.strip() for p in ports_of_call.split(',') if p.strip()]
            legend.append({'name': f'航线{route["id"]}', 'color': color, 'ports': ports_of_call})
            for port in ports_of_call:
                if port not in node_set:
                    node_set.add(port)
                    nodes.append({'name': port, 'category': 0, 'symbolSize': 50})
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

@analysis_bp.route('/api/status')
def get_status():
    try:
        session = Session()
        status_count = {
            '在航': session.query(Ship).filter(Ship.status == '在航').count(),
            '停泊': session.query(Ship).filter(Ship.status == '停泊').count(),
            '待航': session.query(Ship).filter(Ship.status == '待航').count(),
            '维修': session.query(Ship).filter(Ship.status == '维修').count()
        }
        session.close()
        status_data = [
            {'name': status, 'value': count}
            for status, count in status_count.items()
        ]
        return jsonify({'status': 'success', 'data': status_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@analysis_bp.route('/api/throughput')
def get_throughput():
    try:
        from api.data_api import ROUTES_DATA
        port_throughput = {}
        for route in ROUTES_DATA:
            for port in route['ports']:
                if port not in port_throughput:
                    port_throughput[port] = 0
                port_throughput[port] += 1
        ports = list(port_throughput.keys())
        values = list(port_throughput.values())
        return jsonify({'status': 'success', 'ports': ports, 'values': values})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500 