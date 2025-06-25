"""
可视化服务：负责生成各种数据可视化
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Any, Optional, Tuple, Union


class VisualizationService:
    """可视化服务类：提供数据可视化相关的功能"""
    
    def __init__(self):
        """初始化可视化服务"""
        pass
    
    def create_cost_comparison_chart(self, routes: List[Dict[str, Any]]) -> go.Figure:
        """
        创建路线成本比较图表
        
        Args:
            routes: 路线列表
            
        Returns:
            Plotly图表对象
        """
        # 提取路线名称和成本数据
        route_names = [route.get('name', f'路线{i+1}') for i, route in enumerate(routes)]
        costs = [route.get('cost', 0) for route in routes]
        
        # 创建条形图
        fig = go.Figure(data=[
            go.Bar(
                x=route_names,
                y=costs,
                marker_color='rgb(55, 83, 109)'
            )
        ])
        
        # 设置图表布局
        fig.update_layout(
            title='航运路线成本比较',
            xaxis_title='路线',
            yaxis_title='成本 (元)',
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            plot_bgcolor='white'
        )
        
        return fig
    
    def create_time_comparison_chart(self, routes: List[Dict[str, Any]]) -> go.Figure:
        """
        创建路线时间比较图表
        
        Args:
            routes: 路线列表
            
        Returns:
            Plotly图表对象
        """
        # 提取路线名称和时间数据
        route_names = [route.get('name', f'路线{i+1}') for i, route in enumerate(routes)]
        durations = [route.get('duration', 0) for route in routes]
        
        # 创建条形图
        fig = go.Figure(data=[
            go.Bar(
                x=route_names,
                y=durations,
                marker_color='rgb(26, 118, 255)'
            )
        ])
        
        # 设置图表布局
        fig.update_layout(
            title='航运路线时间比较',
            xaxis_title='路线',
            yaxis_title='时间 (天)',
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            plot_bgcolor='white'
        )
        
        return fig
    
    def create_cost_breakdown_chart(self, cost_data: Dict[str, float]) -> go.Figure:
        """
        创建成本明细图表
        
        Args:
            cost_data: 成本数据字典
            
        Returns:
            Plotly图表对象
        """
        # 提取成本类别和数值
        categories = list(cost_data.keys())
        values = list(cost_data.values())
        
        # 创建饼图
        fig = go.Figure(data=[go.Pie(
            labels=categories,
            values=values,
            hole=.3,
            textinfo='percent+label'
        )])
        
        # 设置图表布局
        fig.update_layout(
            title='成本构成分析'
        )
        
        return fig
    
    def create_port_traffic_chart(self, port_data: Dict[str, int]) -> go.Figure:
        """
        创建港口流量图表
        
        Args:
            port_data: 港口流量数据，格式为 {港口名: 流量值}
            
        Returns:
            Plotly图表对象
        """
        # 提取港口名称和流量数据
        ports = list(port_data.keys())
        traffic = list(port_data.values())
        
        # 创建条形图
        fig = go.Figure(data=[
            go.Bar(
                x=ports,
                y=traffic,
                marker_color='rgb(142, 202, 230)'
            )
        ])
        
        # 设置图表布局
        fig.update_layout(
            title='港口流量统计',
            xaxis_title='港口',
            yaxis_title='流量',
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            plot_bgcolor='white'
        )
        
        return fig
    
    def create_optimization_history_chart(self, history: List[Dict[str, Any]]) -> go.Figure:
        """
        创建优化历史图表
        
        Args:
            history: 优化历史记录
            
        Returns:
            Plotly图表对象
        """
        # 提取历史数据
        iterations = list(range(1, len(history) + 1))
        costs = [h['result_summary']['cost'] for h in history]
        methods = [h['method'] for h in history]
        
        # 创建折线图
        fig = go.Figure()
        
        # 为每种方法添加一条线
        for method in set(methods):
            method_indices = [i for i, m in enumerate(methods) if m == method]
            method_iterations = [iterations[i] for i in method_indices]
            method_costs = [costs[i] for i in method_indices]
            
            fig.add_trace(go.Scatter(
                x=method_iterations,
                y=method_costs,
                mode='lines+markers',
                name=method
            ))
        
        # 设置图表布局
        fig.update_layout(
            title='优化历史记录',
            xaxis_title='迭代次数',
            yaxis_title='总成本',
            legend_title='优化方法',
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            plot_bgcolor='white'
        )
        
        return fig
    
    def create_sensitivity_analysis_chart(self, parameter: str, values: List[float], 
                                        costs: List[float]) -> go.Figure:
        """
        创建敏感性分析图表
        
        Args:
            parameter: 参数名称
            values: 参数值列表
            costs: 对应的成本列表
            
        Returns:
            Plotly图表对象
        """
        # 创建折线图
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=values,
            y=costs,
            mode='lines+markers',
            line=dict(color='rgb(67, 160, 71)', width=2)
        ))
        
        # 设置图表布局
        fig.update_layout(
            title=f'参数敏感性分析: {parameter}',
            xaxis_title=parameter,
            yaxis_title='总成本',
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray'
            ),
            plot_bgcolor='white'
        )
        
        return fig
    
    def create_route_comparison_table(self, routes: List[Dict[str, Any]], 
                                     metrics: List[str] = None) -> pd.DataFrame:
        """
        创建路线比较表格
        
        Args:
            routes: 路线列表
            metrics: 要比较的指标列表
            
        Returns:
            DataFrame表格
        """
        # 如果未指定指标，使用默认指标
        if metrics is None:
            metrics = ['cost', 'distance', 'duration', 'port_count']
        
        # 创建表格数据
        table_data = []
        
        for route in routes:
            row = {'name': route.get('name', '')}
            
            for metric in metrics:
                if metric == 'port_count' and 'ports' in route:
                    row[metric] = len(route['ports'])
                else:
                    row[metric] = route.get(metric, 0)
                    
            table_data.append(row)
        
        # 创建DataFrame
        df = pd.DataFrame(table_data)
        
        return df
    
    def create_heatmap(self, data: List[List[float]], x_labels: List[str], 
                      y_labels: List[str], title: str) -> go.Figure:
        """
        创建热力图
        
        Args:
            data: 热力图数据矩阵
            x_labels: X轴标签
            y_labels: Y轴标签
            title: 图表标题
            
        Returns:
            Plotly图表对象
        """
        # 创建热力图
        fig = go.Figure(data=go.Heatmap(
            z=data,
            x=x_labels,
            y=y_labels,
            colorscale='Viridis',
            colorbar=dict(title='数值')
        ))
        
        # 设置图表布局
        fig.update_layout(
            title=title,
            xaxis_title='',
            yaxis_title='',
            xaxis=dict(side='top')
        )
        
        return fig
    
    def create_distance_matrix_heatmap(self, distance_matrix: pd.DataFrame) -> go.Figure:
        """
        创建距离矩阵热力图
        
        Args:
            distance_matrix: 距离矩阵DataFrame
            
        Returns:
            Plotly图表对象
        """
        # 获取港口名称
        ports = distance_matrix.index.tolist()
        
        # 创建距离热力图
        return self.create_heatmap(
            data=distance_matrix.values.tolist(),
            x_labels=ports,
            y_labels=ports,
            title='港口间距离矩阵 (海里)'
        )
    
    def create_correlation_matrix(self, data: pd.DataFrame, 
                                 columns: List[str] = None) -> go.Figure:
        """
        创建相关性矩阵
        
        Args:
            data: 数据DataFrame
            columns: 要计算相关性的列名列表
            
        Returns:
            Plotly图表对象
        """
        # 如果未指定列，使用所有数值列
        if columns is None:
            numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
            columns = numeric_cols
        
        # 计算相关性矩阵
        correlation = data[columns].corr()
        
        # 创建热力图
        return self.create_heatmap(
            data=correlation.values.tolist(),
            x_labels=columns,
            y_labels=columns,
            title='变量相关性矩阵'
        ) 