"""
航运网络设计系统 - 结果显示界面模块
功能：
1. 优化结果展示
2. 统计信息显示
3. 结果导出
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import json
from datetime import datetime

from src.utils.config import Config

def load_solution(file_path):
    """加载优化结果"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            solution_data = json.load(f)
            
            # 处理design_solution字典
            if 'design_solution' in solution_data and solution_data['design_solution'] is not None:
                # 将字典中的数值转换为float类型
                design_solution = solution_data['design_solution']
                if 'total_cost' in design_solution:
                    design_solution['total_cost'] = float(design_solution['total_cost'])
                if 'total_utility' in design_solution:
                    design_solution['total_utility'] = float(design_solution['total_utility'])
                if 'total_captured_demand' in design_solution:
                    design_solution['total_captured_demand'] = float(design_solution['total_captured_demand'])
                if 'cycle_times' in design_solution:
                    design_solution['cycle_times'] = [float(t) for t in design_solution['cycle_times']]
            
            return solution_data
    except Exception as e:
        st.error(f"加载结果文件失败: {str(e)}")
        return None

## 绘制航线网络图
# eg:
# solution_data:
#       'datetime': '2025-05-20 17:09:52'
#       'method': 'ALNS'
#       'total_cost': 100000.0
#       'routes': [[2, 14, 39, 49, 4, 0], [30, 13, 32, 20, 44, 22, 0], [7, 19, 42, 24, 9, 16, 0, 37], [41, 26, 5, 36, 46, 0], [25, 23, 40, 11, 15, 12, 28, 38, 35, 0], [1, 6, 31, 10, 47, 0], [33, 29, 45, 27, 0], [34, 48, 3, 43, 17, 8, 0, 21, 18]]
#       'statistics': {'total_cost': 100000.0, 'num_routes': 8, 'execution_time': 10.0, 'solve_time': 10.0}
#       'ports': [{'港口ID': 1, '港口名称': 'Shanghai', '区域': 'East Asia', '纬度': 31.2304, '经度': 121.4737, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 2, '港口名称': 'Singapore', '区域': 'East Asia', '纬度': 1.24710725, '经度': 103.6585495, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 3, '港口名称': 'Ningbo', '区域': 'East Asia', '纬度': 29.8683, '经度': 121.544, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 4, '港口名称': 'Qingdao', '区域': 'East Asia', '纬度': 36.0671, '经度': 120.3826, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 5, '港口名称': 'Xingang', '区域': 'East Asia', '纬度': 38.99242504, '经度': 117.7510677, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 6, '港口名称': 'Prince Rupert', '区域': 'North America', '纬度': 54.3142, '经度': -130.3201, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 7, '港口名称': 'Vancouver', '区域': 'North America', '纬度': 49.2827, '经度': -123.1207, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 8, '港口名称': 'Oakland', '区域': 'North America', '纬度': 37.8044, '经度': -122.2711, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 9, '港口名称': 'Los Angeles', '区域': 'North America', '纬度': 34.0522, '经度': -118.2437, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 10, '港口名称': 'Manzanillo', '区域': 'North America', '纬度': 19.0256, '经度': -104.3175, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 11, '港口名称': 'Balboa', '区域': 'South America', '纬度': 8.9614, '经度': -79.5631, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 12, '港口名称': 'Buenaventura', '区域': 'South America', '纬度': 3.886, '经度': -77.0342, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 13, '港口名称': 'Guayaquil', '区域': 'South America', '纬度': -2.278474132, '经度': -79.91263936, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 14, '港口名称': 'Posorja', '区域': 'South America', '纬度': -2.71, '经度': -80.2517, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 15, '港口名称': 'Callao', '区域': 'South America', '纬度': -12.0516, '经度': -77.1316, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 16, '港口名称': 'Melbourne', '区域': 'Oceania', '纬度': -37.8136, '经度': 144.9631, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 17, '港口名称': 'Sydney', '区域': 'Oceania', '纬度': -33.8688, '经度': 151.2093, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 18, '港口名称': 'Brisbane', '区域': 'Oceania', '纬度': -27.4698, '经度': 153.0251, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 19, '港口名称': 'Hong Kong', '区域': 'East Asia', '纬度': 22.3193, '经度': 114.1694, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 20, '港口名称': 'Xiamen', '区域': 'East Asia', '纬度': 24.4798, '经度': 118.0894, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 21, '港口名称': 'Yantian', '区域': 'East Asia', '纬度': 22.557, '经度': 114.2599, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 22, '港口名称': 'Shekou', '区域': 'East Asia', '纬度': 22.4897, '经度': 113.9177, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 23, '港口名称': 'Dalian', '区域': 'East Asia', '纬度': 38.9390876, '经度': 121.6611658, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 24, '港口名称': 'Kaohsiung', '区域': 'East Asia', '纬度': 22.613, '经度': 120.2777, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 25, '港口名称': 'Taipei', '区域': 'East Asia', '纬度': 25.033, '经度': 121.5654, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 26, '港口名称': 'Busan', '区域': 'East Asia', '纬度': 35.1796, '经度': 129.0756, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 27, '港口名称': 'Yokohama', '区域': 'East Asia', '纬度': 35.613, '经度': 139.6786, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 28, '港口名称': 'Tokyo', '区域': 'East Asia', '纬度': 35.55105839, '经度': 139.7934437, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 29, '港口名称': 'Osaka', '区域': 'East Asia', '纬度': 34.61947428, '经度': 135.4312295, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 30, '港口名称': 'Haiphong', '区域': 'East Asia', '纬度': 20.86451721, '经度': 106.6851105, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 31, '港口名称': 'Vladivostok', '区域': 'East Asia', '纬度': 43.1155, '经度': 131.8856, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 32, '港口名称': 'Vostochny', '区域': 'East Asia', '纬度': 42.8532, '经度': 133.055, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 33, '港口名称': 'Lazaro Cardenas', '区域': 'North America', '纬度': 17.9278, '经度': -102.169, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 34, '港口名称': 'Seattle', '区域': 'North America', '纬度': 47.61147423, '经度': -122.2901501, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 35, '港口名称': 'Tacoma', '区域': 'North America', '纬度': 47.26562827, '经度': -122.4118848, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 36, '港口名称': 'Long Beach', '区域': 'North America', '纬度': 33.75504041, '经度': -118.2148702, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 37, '港口名称': 'Honolulu', '区域': 'North America', '纬度': 21.3069, '经度': -157.8583, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 38, '港口名称': 'Montreal', '区域': 'North America', '纬度': 45.5017, '经度': -73.5673, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 39, '港口名称': 'Halifax', '区域': 'North America', '纬度': 44.6488, '经度': -63.5752, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 40, '港口名称': 'Ensenada', '区域': 'North America', '纬度': 31.8719, '经度': -116.5989, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 41, '港口名称': 'San Antonio', '区域': 'South America', '纬度': -33.5928, '经度': -71.6067, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 42, '港口名称': 'Lirquen', '区域': 'South America', '纬度': -36.7146, '经度': -72.9859, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 43, '港口名称': 'Rotterdam', '区域': 'Mediterranean', '纬度': 51.9202, '经度': 4.4792, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 44, '港口名称': 'Hamburg', '区域': 'Mediterranean', '纬度': 53.5511, '经度': 9.9937, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 45, '港口名称': 'Antwerp', '区域': 'Mediterranean', '纬度': 51.2194, '经度': 4.4025, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 46, '港口名称': 'Le Havre', '区域': 'Mediterranean', '纬度': 49.4939, '经度': 0.1079, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 47, '港口名称': 'Bremerhaven', '区域': 'Mediterranean', '纬度': 53.55, '经度': 8.5833, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 48, '港口名称': 'Tanger Med', '区域': 'North Europe', '纬度': 35.7879, '经度': -5.7969, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 49, '港口名称': 'Casablanca', '区域': 'North Europe', '纬度': 33.5731, '经度': -7.5898, '是否枢纽': False, '吞吐量': 0}, {'港口ID': 50, '港口名称': 'Agadir', '区域': 'North Europe', '纬度': 30.4215, '经度': -9.5981, '是否枢纽': False, '吞吐量': 0}]


def plot_route_network(solution_data):
    """绘制航线网络图"""
    if not solution_data:
        return None
    
    try:
        # 创建网络图
        fig = go.Figure()
        
        # 添加海图背景
        fig.add_trace(go.Scattergeo(
            lon=[-180, 180],
            lat=[-90, 90],
            mode='markers',
            marker=dict(
                size=0,
                color='lightblue'
            ),
            showlegend=False
        ))
        
        # 添加港口节点
        for port in solution_data.get('ports', []):
            fig.add_trace(go.Scattergeo(
                lon=[port.get('经度', port.get('longitude', port.get('Longitude', 0)))],
                lat=[port.get('纬度', port.get('latitude', port.get('Latitude', 0)))],
                mode='markers+text',
                name=port.get('港口名称', port.get('name', 'Unknown')),
                text=port.get('港口名称', port.get('name', 'Unknown')),
                textposition="top center",
                marker=dict(
                    size=8,
                    color='red',
                    symbol='circle'
                ),
                hoverinfo='text',
                legendgroup='ports',
                showlegend=True,
                legendgrouptitle_text="港口节点"  # 添加港口图例组标题
            ))

        ports_df = pd.DataFrame(solution_data.get('ports', []))
        
        # 添加航线连接（使用贝塞尔曲线）
        for i, route in enumerate(solution_data.get('routes', [])):
            points = route
            lons = [ports_df.iloc[p]['经度'] for p in points]
            lons.append(lons[0])  # 闭合航线
            lats = [ports_df.iloc[p]['纬度'] for p in points]
            lats.append(lats[0])  # 闭合航线
            
            # 计算贝塞尔曲线控制点
            curve_lons = []
            curve_lats = []
            for j in range(len(lons)-1):
                # 添加起点
                curve_lons.append(lons[j])
                curve_lats.append(lats[j])
                
                # 计算控制点
                mid_lon = (lons[j] + lons[j+1]) / 2
                mid_lat = (lats[j] + lats[j+1]) / 2
                
                # 添加控制点（在中间点的基础上向上或向下偏移）
                offset = 5  # 控制曲线的弯曲程度
                if abs(lons[j] - lons[j+1]) > 180:  # 处理跨越180度经线的情况
                    offset = -offset
                curve_lons.append(mid_lon)
                curve_lats.append(mid_lat + offset)
                
                # 添加终点
                curve_lons.append(lons[j+1])
                curve_lats.append(lats[j+1])

            # 获取航线信息
            design_solution = solution_data.get('design_solution')
            if design_solution and hasattr(design_solution, 'route_solutions') and i < len(design_solution.route_solutions):
                route_solution = design_solution.route_solutions[i]
                route_distance = getattr(route_solution, 'travel_distance', 0)
                route_time = getattr(route_solution, 'round_trip_time', 0)
            else:
                route_distance = 0
                route_time = 0
            
            # 构建悬停文本
            hover_text = f"航线 {i+1}<br>"
            hover_text += f"往返里程: {route_distance:.1f}km<br>"
            hover_text += f"往返时间: {route_time:.1f}h<br>"
            hover_text += "停靠港口: "
            for p in points:
                port_name = ports_df.iloc[p]['港口名称']
                hover_text += f"{port_name} → "
            hover_text = hover_text[:-3]  # 移除最后的箭头

            fig.add_trace(go.Scattergeo(
                lon=curve_lons,
                lat=curve_lats,
                mode='lines',
                name=f'Route {i+1}',
                line=dict(
                    width=2,
                    color=Config.ROUTE_COLORS[i]
                ),
                hoverinfo='text',
                hovertext=hover_text,
                legendgroup='routes',
                showlegend=True,
                legendgrouptitle_text="航线"  # 添加航线图例组标题
            ))
        
        # 更新布局
        fig.update_layout(
            title=dict(
                text='航线网络设计结果',
                x=0.5,
                y=0.95,
                xanchor='center',
                yanchor='top'
            ),
            showlegend=True,
            width=1000,
            height=700,
            geo=dict(
                scope='world',
                showland=True,
                showcoastlines=True,
                showocean=True,
                landcolor='rgb(243, 243, 243)',
                oceancolor='rgb(204, 229, 255)',
                coastlinecolor='rgb(128, 128, 128)',
                projection_type='equirectangular',
                center=dict(lon=120, lat=30),  # 以中国为中心
                lonaxis=dict(range=[-180, 180]),
                lataxis=dict(range=[-60, 80]),
                bgcolor='rgba(255, 255, 255, 0.8)'
            ),
            margin=dict(l=0, r=150, t=50, b=0),  # 增加右侧边距以容纳两个图例
            legend=dict(
                orientation="v",  # 垂直排列
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.02,  # 放置在图表右侧
                groupclick="toggleitem",  # 允许单独切换图例项
                bordercolor="rgba(0,0,0,0.2)",
                borderwidth=1,
                bgcolor="rgba(255,255,255,0.8)",
                tracegroupgap=5,  # 增加图例项之间的间距
                font=dict(size=10),  # 调整字体大小
                title=dict(
                    text="图例",
                    font=dict(size=12, color="black")
                ),
                grouptitlefont=dict(size=11, color="black")  # 设置图例组标题的字体
            ),
            # 添加缩放和平移控件
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    x=0.1,
                    y=1.1,
                    showactive=True,
                    buttons=list([
                        dict(
                            args=[{"geo.zoom": 1}],
                            label="重置视图",
                            method="relayout"
                        ),
                        dict(
                            args=[{"geo.zoom": 2}],
                            label="放大",
                            method="relayout"
                        ),
                        dict(
                            args=[{"geo.zoom": 0.5}],
                            label="缩小",
                            method="relayout"
                        )
                    ])
                )
            ]
        )
        
        # 配置交互模式
        fig.update_layout(
            dragmode='pan',  # 默认启用平移模式
            modebar=dict(
                orientation='v',
                bgcolor='rgba(255,255,255,0.7)'
            )
        )
        
        return fig
    except Exception as e:
        st.error(f"绘制网络图失败: {str(e)}")
        return None

def show_statistics(solution_data):
    """显示统计信息"""
    if not solution_data:
        return
    
    try:
        stats = solution_data.get('statistics', {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总成本", f"¥{stats.get('total_cost', 0):,.2f}")
        with col2:
            st.metric("航线数量", stats.get('num_routes', 0))
        with col3:
            st.metric("覆盖港口数", stats.get('num_ports_served', 0))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("平均航线长度", f"{stats.get('avg_route_length', 0):.1f}km")
        with col2:
            st.metric("总运营距离", f"{stats.get('total_distance', 0):,.0f}km")
        with col3:
            st.metric("中转港口数量", f"{stats.get('num_transit_ports', 0)}")
    except Exception as e:
        st.error(f"显示统计信息失败: {str(e)}")

def show_route_details(solution_data):
    """显示航线详细信息"""
    if not solution_data:
        return
    
    try:
        st.subheader("航线详细信息")
        
        for i, route in enumerate(solution_data.get('design_solution', {}).route_solutions):
            with st.expander(f"航线 {i+1}"):
                # 显示航线基本信息
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("往返时间", f"{route.get('round_trip_time', 0):.2f}h")
                with col2:
                    st.metric("往返里程", f"{route.get('travel_distance', 0):,.2f}km")
                
                # 显示港口访问顺序
                st.write("访问顺序：")
                port_call_sequence = route.get('port_call_sequence', [])
                if port_call_sequence:
                    port_call_sequence_df = pd.DataFrame(port_call_sequence)
                    stand_ports_data = st.session_state.port_data
                    # 添加港口名称列
                    port_call_sequence_df['id'] = port_call_sequence_df['port_id'].apply(
                        lambda x: stand_ports_data.iloc[x]['id'] if 0 <= x < len(stand_ports_data) else 'Unknown'
                    )
                    port_call_sequence_df['name'] = port_call_sequence_df['port_id'].apply(
                        lambda x: stand_ports_data.iloc[x]['name'] if 0 <= x < len(stand_ports_data) else 'Unknown'
                    )
                    port_call_sequence_df['region'] = port_call_sequence_df['port_id'].apply(
                        lambda x: stand_ports_data.iloc[x]['region'] if 0 <= x < len(stand_ports_data) else 'Unknown'
                    )
                    display_columns = ['id', 'name', 'port_call', 'arrival_time', 'region']
                    # 确保所有列都存在
                    for col in display_columns:
                        if col not in port_call_sequence_df.columns:
                            port_call_sequence_df[col] = 'N/A'
                    st.dataframe(port_call_sequence_df[display_columns])
                else:
                    st.info("该航线暂无港口信息")
    except Exception as e:
        st.error(f"显示航线详细信息失败: {str(e)}")

def export_results(solution_data):
    """导出优化结果"""
    if not solution_data:
        return
    
    try:
        # 创建带时间戳的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"optimization_results_{timestamp}.xlsx"
        
        with pd.ExcelWriter(output_file) as writer:
            # 导出统计信息
            stats_df = pd.DataFrame([solution_data.get('statistics', {})])
            stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            # 导出航线信息
            routes_data = []
            for route in solution_data.get('routes', []):
                route_info = {
                    'route_id': route.get('id', 'Unknown'),
                    'distance': route.get('distance', 0),
                    'cost': route.get('cost', 0),
                    'load_factor': route.get('load_factor', 0),
                    'ports_sequence': ' -> '.join([p.get('name', 'Unknown') for p in route.get('ports', [])])
                }
                routes_data.append(route_info)
            
            if routes_data:
                routes_df = pd.DataFrame(routes_data)
                routes_df.to_excel(writer, sheet_name='Routes', index=False)
            
            # 导出港口信息
            ports_data = []
            for route in solution_data.get('routes', []):
                for port in route.get('ports', []):
                    port_info = {
                        'route_id': route.get('id', 'Unknown'),
                        'port_name': port.get('name', 'Unknown'),
                        'arrival_time': port.get('arrival_time', 'N/A'),
                        'departure_time': port.get('departure_time', 'N/A'),
                        'load_quantity': port.get('load_quantity', 0)
                    }
                    ports_data.append(port_info)
            
            if ports_data:
                ports_df = pd.DataFrame(ports_data)
                ports_df.to_excel(writer, sheet_name='Ports', index=False)
        
        st.success(f"结果已导出到 {output_file}")
    except Exception as e:
        st.error(f"导出结果失败: {str(e)}")

def show_results():
    """显示优化结果界面"""
    st.header("📈 优化结果")
    
    try:
        # 如果优化正在进行中
        if st.session_state.get('optimization_status') == 'running':
            st.info("优化计算正在进行中...")
            progress_bar = st.progress(0)
            progress = st.session_state.get('current_iteration', 0) / 100  # 假设总迭代次数为100
            progress_bar.progress(progress)
            
            # 显示当前最优解
            if st.session_state.get('best_solution'):
                st.metric("当前最优解", f"¥{st.session_state.best_solution:,.2f}")
            return
        
        # 如果优化已完成
        if st.session_state.get('optimization_status') == 'completed':
            # 首先检查会话状态中是否有优化结果
            if 'optimization_result' in st.session_state and st.session_state.optimization_result:
                solution_data = st.session_state.optimization_result
                
                # 检查是否有错误信息
                if 'error' in solution_data:
                    st.error(f"优化过程中出现错误: {solution_data['error']}")
                    if 'traceback' in solution_data:
                        with st.expander("查看错误详情"):
                            st.code(solution_data['traceback'])
                    
                    # 即使有错误，也尝试显示可能存在的部分结果
                    st.warning("以下为可能不完整的优化结果")
                
                # 如果routes为空，提示用户
                if not solution_data.get('routes'):
                    st.warning("未找到有效的航线数据，请检查优化配置或重新运行")
                    
                    # 如果有日志消息，显示最近的日志
                    if 'log_messages' in st.session_state and st.session_state.log_messages:
                        with st.expander("查看最近日志"):
                            for log in st.session_state.log_messages[-20:]:
                                st.text(log)
                    
                    # 尝试提供一些建议
                    st.info("可能的解决方案:\n"
                           "1. 检查网络数据和配置是否正确\n"
                           "2. 增加最大迭代次数\n"
                           "3. 尝试不同的优化算法\n"
                           "4. 查看日志了解更多详情")
                    
                    # 添加重新运行按钮
                    if st.button("🔄 重新运行优化"):
                        st.session_state.run_optimization = True
                        st.rerun()
                    
                    return
                
                # 显示优化结果
                tab1, tab2, tab3 = st.tabs(["网络图", "统计信息", "详细信息"])
                
                with tab1:
                    network_fig = plot_route_network(solution_data)
                    if network_fig:
                        st.plotly_chart(network_fig, use_container_width=True)
                
                with tab2:
                    show_statistics(solution_data)
                
                with tab3:
                    show_route_details(solution_data)
                
                # 导出结果按钮
                if st.button("📥 导出结果"):
                    export_results(solution_data)
                return
                
            # 如果会话状态中没有结果，尝试从文件加载
            solution_file = Path("optimization_result.json")
            if solution_file.exists():
                solution_data = load_solution(solution_file)
                if solution_data:
                    # 显示优化结果
                    tab1, tab2, tab3 = st.tabs(["网络图", "统计信息", "详细信息"])
                    
                    with tab1:
                        network_fig = plot_route_network(solution_data)
                        if network_fig:
                            st.plotly_chart(network_fig, use_container_width=True)
                    
                    with tab2:
                        show_statistics(solution_data)
                    
                    with tab3:
                        show_route_details(solution_data)
                    
                    # 导出结果按钮
                    if st.button("📥 导出结果"):
                        export_results(solution_data)
                    return
            
        # 如果既没有会话状态结果也没有文件结果
        st.info("暂无优化结果，请点击侧边栏的【开始优化】按钮开始优化过程")
        
    except Exception as e:
        import traceback
        st.error(f"显示结果时出错: {str(e)}")
        with st.expander("错误详情"):
            st.code(traceback.format_exc())