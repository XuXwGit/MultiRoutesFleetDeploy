"""
航运网络设计系统 - 可视化界面模块
功能：
1. 港口数据地图可视化
2. 优化过程实时监控
3. 结果网络可视化
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from pathlib import Path

def create_port_map(port_data=None):
    """创建港口分布地图"""
    # 创建地图
    m = folium.Map(location=[30, 120], zoom_start=4)
    
    if port_data is not None and not port_data.empty:
        # 定义可能的列名映射
        column_mappings = {
            '港口ID': ['港口ID', 'ID', 'id', 'port_id', 'PortID'],
            '港口名称': ['港口名称', 'City', 'city', 'City_en', 'port_name', 'PortName', '名称'],
            '经度': ['经度', 'Longitude', "Latitude(N)", 'longitude', 'lon', 'LON'],
            '纬度': ['纬度', 'Latitude', "Longitude(E)", 'latitude', 'lat', 'LAT'],
            '吞吐量': ['吞吐量', 'Capacity', 'capacity', 'throughput', 'Throughput']
        }
        
        # 获取实际的列名
        actual_columns = list(port_data.columns)
        
        # 创建列名映射字典
        column_map = {}
        for standard_name, possible_names in column_mappings.items():
            for name in possible_names:
                if name in actual_columns:
                    column_map[standard_name] = name
                    break
        
        # 检查必要的列是否存在
        required_columns = ['经度', '纬度']
        missing_columns = [col for col in required_columns if col not in column_map]
        
        if missing_columns:
            st.error(f"缺少必要的列: {', '.join(missing_columns)}")
            st.write("当前数据列名:", actual_columns)
            return m
        
        # 添加港口标记
        for idx, row in port_data.iterrows():
            try:
                # 获取位置信息
                lat = float(row[column_map['纬度']])
                lon = float(row[column_map['经度']])
                
                # 构建弹出信息
                popup_text = []
                if '港口名称' in column_map:
                    popup_text.append(f"港口: {row[column_map['港口名称']]}")
                if '吞吐量' in column_map:
                    popup_text.append(f"吞吐量: {row[column_map['吞吐量']]}")
                
                folium.Marker(
                    location=[lat, lon],
                    popup="<br>".join(popup_text) if popup_text else f"位置: {lat}, {lon}",
                    icon=folium.Icon(color='red', icon='info-sign')
                ).add_to(m)
            except (KeyError, ValueError) as e:
                st.error(f"处理第 {idx+1} 行数据时出错: {str(e)}")
                continue
    
    return m

def plot_optimization_progress():
    """绘制优化进度图表"""
    if 'optimization_history' in st.session_state:
        history = st.session_state.optimization_history
        
        # 创建迭代曲线
        fig = go.Figure()
        
        # 添加目标函数值曲线
        fig.add_trace(go.Scatter(
            x=list(range(len(history))),
            y=[h.get('objective_value', 0) for h in history],
            mode='lines+markers',
            name='目标函数值'
        ))
        
        # 更新布局
        fig.update_layout(
            title='优化进度',
            xaxis_title='迭代次数',
            yaxis_title='目标函数值',
            template='plotly_white'
        )
        
        return fig
    return None

def plot_network_result(solution_data=None):
    """绘制最终网络结果"""
    if solution_data is not None:
        # 创建网络图
        m = folium.Map(location=[30, 120], zoom_start=4)
        
        # 添加港口节点
        for port in solution_data.get('ports', []):
            folium.CircleMarker(
                location=[port['lat'], port['lon']],
                radius=8,
                popup=port['name'],
                color='red',
                fill=True
            ).add_to(m)
        
        # 添加航线连接
        for route in solution_data.get('routes', []):
            points = [(p['lat'], p['lon']) for p in route['ports']]
            folium.PolyLine(
                points,
                weight=2,
                color='blue',
                opacity=0.8,
                popup=f"航线 {route['id']}"
            ).add_to(m)
        
        return m
    return None

def show_visualization():
    """显示可视化界面"""
    st.header("🌍 数据分析")
    
    # 创建三个子标签页
    tab1, tab2, tab3, tab4 = st.tabs(["港口分布", "优化进度", "网络结果", "历史结果 "])
    
    with tab1:
        st.subheader("港口分布图")
        if 'current_ports_data' in st.session_state:
            port_map = create_port_map(st.session_state.current_ports_data)
            st_folium(port_map, width=800, height=500)
        else:
            st.info("请先在数据管理页面加载港口数据")
    
    with tab2:
        st.subheader("优化进度监控")
        progress_fig = plot_optimization_progress()
        if progress_fig:
            st.plotly_chart(progress_fig, use_container_width=True)
            
            # 添加优化指标
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("当前迭代次数", st.session_state.current_iteration)
            with col2:
                if st.session_state.best_solution:
                    st.metric("最优解成本", f"{st.session_state.best_solution:.2f}")
            with col3:
                if len(st.session_state.optimization_history) > 1:
                    improvement = ((st.session_state.optimization_history[0].get('objective_value', 0) -
                                 st.session_state.optimization_history[-1].get('objective_value', 0)) /
                                st.session_state.optimization_history[0].get('objective_value', 0) * 100)
                    st.metric("优化改进率", f"{improvement:.1f}%")
        else:
            st.info("优化过程尚未开始")
    
    with tab3:
        st.subheader("网络设计结果")
        if st.session_state.optimization_status == 'completed':
            # 这里应该从某处获取实际的解决方案数据
            solution_map = plot_network_result(None)  # 暂时传入None
            if solution_map:
                st_folium(solution_map, width=800, height=500)
                
                # 添加结果统计
                st.subheader("结果统计")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("航线数量", "0")  # 替换为实际值
                with col2:
                    st.metric("覆盖港口数", "0")  # 替换为实际值
                with col3:
                    st.metric("总运营成本", "0")  # 替换为实际值
        else:
            st.info("等待优化完成后显示结果") 


    with tab4:
        st.subheader("历史结果")
        if 'history_results' in st.session_state:
            for result in st.session_state.history_results:
                st.write(result)
                