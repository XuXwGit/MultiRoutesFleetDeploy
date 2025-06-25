from datetime import datetime
import os
import re
import matplotlib.pyplot as plt
import logging
from matplotlib.path import Path as MplPath  # 使用别名避免冲突
from pathlib import Path
from matplotlib.patches import PathPatch, FancyArrowPatch
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point
from design.core.models.network_data import NetworkData
from src.utils.config import Config
from shapely.affinity import translate
from shapely.ops import split
import random
from matplotlib.lines import Line2D


class Visualizer:
    def __init__(self, lang: str = 'en'):
        self.lang = lang

        Config.reset_logger()

        # 设置全局样式和非交互式后端
        plt.switch_backend('Agg')  # 使用非交互式后端避免Tkinter问题
        
        self.set_lang(lang=lang)

    def set_lang(self, lang = "en"):
        self.lang = lang
        plt.rcParams.update({
            'font.family': Config.FONT_CONFIG[lang]['family'],
            'axes.titlesize': Config.PLOT_STYLE['titlesize'],
            'lines.linewidth': Config.PLOT_STYLE['linewidth']
        })

    def cleanup(self):
        """清理所有matplotlib资源"""
        plt.close('all')

    def _generate_output_path(self, chart_type: str) -> Path:
        """生成标准化的输出路径"""
        lang_dir = 'zh' if self.lang == 'zh' else 'en'
        filename = f"{chart_type}"
        full_path = Path(Config.get_output_path(f"{filename}/{lang_dir}", Config.INSTANCE))
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path


class NetworkVisualizer(Visualizer):
    def __init__(self, network_data: NetworkData, base_map=None):
        super().__init__()
        self.base_map = base_map or self._create_base_map()
        # self.plot_port_distribution(ports_df= network_data.ports_df)

    @staticmethod
    def _create_base_map():
        """创建基础世界地图"""
        world_map = gpd.read_file(Config.WORLD_MAP_DIR / 'ne_110m_admin_0_countries.shp')

        # 地图整体偏移：调整为以太平洋为中心
        delta = 110
        shift = delta - 180
        moved_map = []

        # 分割并移动地图
        border = LineString([(shift, 90), (shift, -90)])
        for row in world_map["geometry"]:
            split_result = split(row, border)
            for item in split_result.geoms:
                minx, miny, maxx, maxy = item.bounds
                if minx >= shift:
                    moved_map.append(translate(item, xoff=-180 - shift))
                else:
                    moved_map.append(translate(item, xoff=180 - shift))

        return gpd.GeoDataFrame({"geometry": moved_map})

    def plot_world_background(self, ax):
        """绘制世界背景图"""
        # 绘制底图
        self.base_map.plot(ax=ax, color='#f0f0f0', edgecolor='#999999')

        # 绘制陆地和海洋
        self._plot_geographical_features(ax)

        # 设置背景颜色
        ax.set_facecolor('lightblue')

        # 设置图像边界
        ax.set_xlim(-10, 180)
        ax.set_ylim(-40, 60)

    def _plot_geographical_features(self, ax):
        """绘制陆地和海洋的公共方法"""
        land = self.base_map[self.base_map['geometry'].type == 'Polygon']
        sea = self.base_map[self.base_map['geometry'].type == 'MultiPolygon']

        # 绘制陆地
        if not land.empty:
            land.plot(ax=ax, color='#E7E9E1', edgecolor='#E7E9E1')
        else:
            logging.warning("No land features found in the map data.")

        # 绘制海洋
        if not sea.empty:
            sea.plot(ax=ax, color='#96BBD0', edgecolor='blue')
        else:
            logging.warning("No sea features found in the map data.")

    def plot_port_nodes(self, ax, ports_df):
        """绘制港口节点"""
        # 将经纬度数据转换为点对象
        geometry = [Point(xy) for xy in zip(ports_df['NewLongitude'], ports_df['Latitude'])]
        city_points = gpd.GeoDataFrame(ports_df, geometry=geometry)

        # 根据区域为每个城市设置不同颜色
        city_points['Color'] = city_points['Region'].map(Config.COLORS)

        # 绘制不同颜色的城市点
        for color in Config.COLORS.values():
            subset = city_points[city_points['Color'] == color]
            subset.plot(ax=ax, markersize=10, color=color, marker='o')

        # 添加城市标签
        for idx, row in ports_df.iterrows():
            ax.annotate(
                text=row['ID'],
                xy=(row['NewLongitude'], row['Latitude']),
                xytext=(row['NewLongitude'], row['Latitude'] + 1),
                fontsize=5,
                ha='center',
                va='bottom',
                color='black',
                alpha=0.8
            )

    def bezier_curve(self, city_points, line, color, ax, bound_direction='out'):
        """绘制贝塞尔曲线"""
        line.append(line[0])  # 确保闭合路径
        verts = []
        codes = []

        for i in range(len(line) - 1):
            start_point = (
                city_points.loc[city_points.index == line[i], 'NewLongitude'].iloc[0],
                city_points.loc[city_points.index == line[i], 'Latitude'].iloc[0]
            )
            end_point = (
                city_points.loc[city_points.index == line[i + 1], 'NewLongitude'].iloc[0],
                city_points.loc[city_points.index == line[i + 1], 'Latitude'].iloc[0]
            )

            # 计算控制点
            factor = random.uniform(0.2, 0.9)
            if bound_direction == 'out':
                control_point = (
                    (start_point[0] + end_point[0]) / 2,
                    (start_point[1] + end_point[1]) / 2 - abs(start_point[1] - end_point[1]) * factor
                )
            elif bound_direction == 'in':
                control_point = (
                    (start_point[0] + end_point[0]) / 2,
                    (start_point[1] + end_point[1]) / 2 + abs(start_point[1] - end_point[1]) * factor
                )
            else:
                logging.error(f"Invalid bound_direction: {bound_direction}")
                return

            # 添加路径顶点和绘制指令
            verts.extend([start_point, control_point, end_point])
            codes.extend([MplPath.MOVETO, MplPath.CURVE3, MplPath.CURVE3])

        # 绘制曲线和箭头
        path = MplPath(verts, codes)
        patch = FancyArrowPatch(path=path, arrowstyle='->', mutation_scale=5, color=color)
        ax.add_patch(patch)

    def plot_shipping_routes(self, ports_df, routes, ax):
        """绘制航线"""
        for i, route in routes.items():
            try:
                if isinstance(route, list) and len(route) == 2:
                    self.bezier_curve(ports_df, route[0], Config.ROUTE_COLORS[i], ax)
                    self.bezier_curve(ports_df, route[1], Config.ROUTE_COLORS[i], ax)
                else:
                    self.bezier_curve(ports_df, route, Config.ROUTE_COLORS[i], ax)
            except Exception as e:
                logging.warning(f"绘制航线{route}出错: {str(e)}", exc_info=True)

    def plot_network(self, ports_df, routes, inset_config=None):
        """主绘图方法"""
        # 设置样式
        plt.style.use(['ieee', 'no-latex'])

        # 创建画布
        fig, ax = plt.subplots(figsize=(10, 6), dpi=360)

        # 绘制背景、港口和航线
        self.plot_world_background(ax)
        self.plot_port_nodes(ax, ports_df)
        self.plot_shipping_routes(ports_df, routes, ax)

        # 添加局部放大
        if inset_config:
            self._add_inset(ax, ports_df, routes, inset_config)

        # 添加图例
        self.add_legends(ax, ports_df, routes)

        # 保存结果
        output_path = self._generate_output_path("design_result")
        filename = f"shipping_network(P{len(ports_df)},R{len(routes)})"
        self._save_figure(fig, output_path, filename)

        logging.info(f"Results saved to: {output_path}")
        plt.close()

    def _add_inset(self, main_ax, ports_df, routes, config):
        """添加局部放大区域"""
        axins = main_ax.inset_axes(config['position'])
        self.base_map.plot(ax=axins, color='#f0f0f0', edgecolor='#999999')

        # 绘制港口点
        ports_gdf = gpd.GeoDataFrame(
            geometry=[Point(xy) for xy in zip(ports_df.Longitude, ports_df.Latitude)]
        )
        ports_gdf.plot(ax=axins, markersize=5, color='#3498db')

        # 绘制局部航线
        for i, route in enumerate(routes):
            path = self._create_ship_path(ports_df, route)
            patch = PathPatch(path, color=Config.ROUTE_COLORS[i], lw=1.5, alpha=0.8)
            axins.add_patch(patch)

        axins.set_xlim(config['xlim'])
        axins.set_ylim(config['ylim'])

    def add_legends(self, ax, ports_df, routes):
        """添加图例"""
        # 区域图例
        regions = ports_df.Region.unique()
        region_legends = [
            Line2D([0], [0], marker='o', color=Config.COLORS[region], markersize=5, label=region)
            for region in regions
        ]

        # 航线图例
        route_legends = [
            Line2D([0], [0], color=Config.ROUTE_COLORS[i], lw=2, label=f'Route {i+1}')
            for i in range(len(routes))
        ]

        ax.legend(
            handles=region_legends + route_legends,
            loc='upper left',
            bbox_to_anchor=(1.05, 1)
        )

    def _create_ship_path(self, ports_df, route):
        """创建航线几何路径"""
        coords = ports_df.iloc[route][['NewLongitude', 'Latitude']].values
        return MplPath(coords)

    def plot_port_distribution(self, ports_df):
        """绘制港口在世界地图上的分布图"""
        # 设置样式
        plt.style.use(['ieee', 'no-latex'])

        # 创建画布
        fig, ax = plt.subplots(figsize=(10, 6), dpi=Config.PLOT_STYLE['dpi'])

        # 绘制自定义世界地图背景
        world_map = gpd.read_file(Config.WORLD_MAP_DIR / 'ne_110m_admin_0_countries.shp')
        
        # 计算港口坐标范围并设置地图边界
        min_lon = ports_df['NewLongitude'].min() - 5
        max_lon = ports_df['NewLongitude'].max() + 5
        min_lat = ports_df['Latitude'].min() - 5
        max_lat = ports_df['Latitude'].max() + 5
        
        # 绘制地图
        world_map.plot(
            ax=ax,
            color='#f0f0f0',  # 陆地颜色
            edgecolor='#999999' # 边界颜色
        )
        
        # 设置地图边界
        ax.set_xlim(min_lon, max_lon)
        ax.set_ylim(min_lat, max_lat)
        ax.set_facecolor('lightblue')  # 海洋颜色

        # 将经纬度数据转换为点对象
        geometry = [Point(xy) for xy in zip(ports_df['NewLongitude'], ports_df['Latitude'])]
        port_points = gpd.GeoDataFrame(ports_df, geometry=geometry)

        # 根据区域为每个港口设置颜色
        port_points['Color'] = port_points['Region'].map(Config.COLOR_MAP)

        # 绘制不同颜色的港口点
        for region, color in Config.COLOR_MAP.items():
            subset = port_points[port_points['Region'] == region]
            if not subset.empty:
                subset.plot(ax=ax, markersize=Config.PLOT_STYLE['marker_size'], color=color, marker='o', label=region)

        # 添加港口标签
        for idx, row in ports_df.iterrows():
            ax.annotate(
                text=row["City_en"],
                xy=(row['NewLongitude'], row['Latitude']),
                xytext=(row['NewLongitude'], row['Latitude'] + 1),
                fontsize=Config.PLOT_STYLE['fontsize'],
                ha='center',
                va='bottom',
                color='black',
                alpha=0.8
            )

        # 添加图例（显示在图形下方）
        ax.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, -0.15),
            title='Region',
            ncol=3,
            frameon=False
        )
        plt.tight_layout()  # 调整布局避免图例被截断

        # 保存结果
        output_path = self._generate_output_path("port_distribution")
        filename = f"port_distribution(P{len(ports_df)})"
        self._save_figure(fig, output_path, filename)

        plt.close()
        logging.info(f"Port distribution plot saved to: {output_path}")


    def _save_figure(self, fig, output_path_dir, filename):
        """保存图像到指定路径"""
        formats = ['pdf', 'jpg', 'svg']
        output_path = Path(output_path_dir)
        if not os.path.exists(output_path):
                # 创建案例结果目录
                os.makedirs(output_path)
        for fmt in formats:
            fig.savefig(f"{output_path_dir}/{filename}.{fmt}", format=fmt, dpi=Config.PLOT_STYLE['dpi'])
            plt.close(fig)  # 显式关闭图形对象


class ResultVisualizer(Visualizer):
    def __init__(self,
                 result_df: pd.DataFrame,
                 lang: str = 'en'
                 ):
        super(ResultVisualizer, self).__init__(lang=lang)
        self.result_df = result_df


    def _generate_output_path(self, section: str = '', chart_type: str = '', chart_name: str = '') -> Path:
        """生成标准化的输出路径"""
        lang_dir = 'zh' if self.lang == 'zh' else 'en'
        
        filename = f"{chart_type}"
        full_path = (
            Path(Config.get_output_path(lang_dir + "/" + filename, section))
        )
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def draw_analysis(self, instance="-1",lang='en'):
        self.set_lang(lang=lang)
        
        # 分析K的影响
        self.plot_k_impact(instance=instance, seed=999, plot_type='line')
        self.plot_k_impact(instance=instance, seed=999, plot_type='bar')
        
        # 分析T的影响
        self.plot_t_impact(instance=instance, seed=66, plot_type='line')
        self.plot_t_impact(instance=instance, seed=66, plot_type='bar')
        
        # 分析R的影响
        self.plot_r_impact(instance=instance, seed=44, plot_type='line')
        self.plot_r_impact(instance=instance, seed=44, plot_type='bar')

    def plot_k_impact(self, instance, seed=999, plot_type='line'):
        """绘制K(OD对数量)对结果的影响"""
        metrics = ['Cost', 'Utility', 'Demand']
        fig, axs = plt.subplots(1, 3, figsize=(18, 5), dpi=Config.PLOT_STYLE['dpi'])
        
        # 获取数据
        data = self._filter_methods_data(instance=instance, seed=seed, param='K')
        if data is not None:
            Config.NUM_PORTS = data['data'][0]["P"]
        
        for i, metric in enumerate(metrics):
            self._plot_impact(
                ax=axs[i],
                data=data,
                param_values=data['K_values'],
                metric=metric,
                plot_type=plot_type,
                param_name='K'
            )
            
        self._save_impact_plot(fig, instance, f'K_impact-{plot_type}')

    def plot_t_impact(self, instance, seed=66, plot_type='line'):
        """绘制T(时间周期)对结果的影响"""
        metrics = ['Cost', 'Utility', 'Demand']
        fig, axs = plt.subplots(1, 3, figsize=(18, 5), dpi=Config.PLOT_STYLE['dpi'])
        
        # 获取数据
        data = self._filter_methods_data(instance=instance, seed=seed, param='T')
        if data is not None:
            Config.NUM_PORTS = data['data'][0]["P"]
        
        for i, metric in enumerate(metrics):
            self._plot_impact(
                ax=axs[i],
                data=data,
                param_values=data['T_values'],
                metric=metric,
                plot_type=plot_type,
                param_name='T'
            )
            
        self._save_impact_plot(fig, instance, f'T_impact-{plot_type}')

    def plot_r_impact(self, instance, seed=44, plot_type='line'):
        """绘制R(线路数量)对结果的影响"""
        metrics = ['Cost', 'Utility', 'Demand']
        fig, axs = plt.subplots(1, 3, figsize=(18, 5), dpi=Config.PLOT_STYLE['dpi'])
        
        # 获取数据
        data = self._filter_methods_data(instance, seed, param='R')
        if data is not None:
            Config.NUM_PORTS = data['data'][0]["P"]
        
        for i, metric in enumerate(metrics):
            self._plot_impact(
                ax=axs[i],
                data=data,
                param_values=data['R_values'],
                metric=metric,
                plot_type=plot_type,
                param_name='R'
            )
            
        self._save_impact_plot(fig, instance, f'R_impact-{plot_type}')

    def _filter_methods_data(self, instance: str, seed: int, param: str = None):
        """获取参数变化的数据"""
        filtered_data = []
        param_values = []
        
        for _, row in self.result_df.iterrows():
            row_instance = row.get("Instance", row.get("Instance_Instance", -1))
            row_seed = row.get("S", row.get("S_S", -1))
            row_P = row.get("P", row.get("P_P", -1))
            row_R = row.get("R", row.get("R_R", -1))
            row_K = row.get("K", row.get("K_K", -1))
            row_T = row.get("T", row.get("T_T", -1))
            params = {'Instance': row_instance, 'K': row_K, 'R': row_R,  'T': row_T, 'S': row_seed}

            if isinstance(row_instance, float):
                row_instance = int(row_instance)
            if isinstance(row_instance, int):
                row_instance = str(row_instance)
            if row_instance != instance or row_seed != seed:
                continue
                
            methods_data = {
                "Cost": {
                    "Cost": row.get("Cost_Cost"),
                    "Utility": row.get("Cost_Utility"),
                    "Demand": row.get("Cost_Demand")
                },
                "Utility": {
                    "Cost": row.get("Utility_Cost"),
                    "Utility": row.get("Utility_Utility"),
                    "Demand": row.get("Utility_Demand")
                },
                "Demand": {
                    "Cost": row.get("Demand_Cost"),
                    "Utility": row.get("Demand_Utility"),
                    "Demand": row.get("Demand_Demand")
                },
                "P": row_P,
                "R": row_R,
                "K": row_K,
                "T": row_T,
                param: params[param]
            }
            
            param_values.append(params[param])
            filtered_data.append(methods_data)
            
        return {
            "data": filtered_data,
            f"{param}_values": sorted(list(set(param_values)))
        }

    def _plot_impact(self, ax, data, param_values, metric, plot_type, param_name):
        """绘制参数影响图"""
        bar_width = Config.PLOT_STYLE["bar_width"]
        num_methods = len(Config.METHODS)
        for method_idx, method in enumerate(Config.METHODS):
            metric_values = []
            for val in param_values:
                # 查找对应参数值的数据
                for d in data['data']:
                    if d[param_name] == val:
                        metric_values.append(d[method][metric])
                        break
            
            if plot_type == 'line':
                ax.plot(param_values, metric_values,
                       linewidth = Config.PLOT_STYLE["linewidth"],
                       linestyle = Config.PLOT_ALGO_STYLE_MAP[method]["linestyle"],
                       color=Config.PLOT_ALGO_STYLE_MAP[method]["color"], 
                       marker=Config.PLOT_ALGO_STYLE_MAP[method]["marker"], 
                       label=Config.OBJ_TO_MODEL_MAP[method],
                       )
            elif plot_type == 'bar':
                # 设置柱状图位置（避免重叠）               
                # 计算横坐标相邻值的最小间距
                min_spacing = np.min(np.array(param_values)[1:] - np.array(param_values)[:-1]) if len(param_values) > 1 else 1

                # 根据最小间距和柱状图宽度调整实际宽度（确保柱状图不会过窄）
                adjusted_bar_width = bar_width if min_spacing > bar_width * 3 else bar_width * min_spacing / (bar_width * 0.5)

                # 计算偏移量
                offset = (method_idx - num_methods / 2) * adjusted_bar_width

                # 绘制柱状图
                ax.bar(
                    [x + offset for x in param_values],
                    metric_values,
                    width=adjusted_bar_width,
                    color=Config.PLOT_ALGO_STYLE_MAP[method]["color"], 
                    label=Config.OBJ_TO_MODEL_MAP[method])
        
        font_config = Config.FONT_CONFIG[self.lang]
        ax.set_xlabel(Config.LANGUAGE_LABEL_MAP[param_name]["xlabel"][self.lang],
                                fontsize=font_config['size'],
                                fontfamily=font_config['family'])
        ax.set_ylabel(metric,
                                fontsize=font_config['size'],
                                fontfamily=font_config['family'])
        ax.set_title(f"{metric}",
                                fontsize=font_config['size'],
                                fontfamily=font_config['family'])
        ax.legend(loc = Config.DEFAULT_LEGEND_LOC)

    def _save_impact_plot(self, fig, instance, plot_name):
        """保存影响图"""
        plt.tight_layout()
        output_path = self._generate_output_path(
            section="impact_analysis",
            chart_type=f"{instance}/{plot_name}"
        )
        plt.savefig(f"{output_path}-{self.lang}.pdf", format='pdf', dpi=Config.PLOT_STYLE['dpi'])
        plt.savefig(f"{output_path}-{self.lang}.jpg", format='jpg', dpi=Config.PLOT_STYLE['dpi'])
        plt.savefig(f"{output_path}-{self.lang}.svg", format='svg', dpi=Config.PLOT_STYLE['dpi'])
        plt.close()
        logging.info(f"{instance}:{plot_name}结果已保存到{output_path}")
