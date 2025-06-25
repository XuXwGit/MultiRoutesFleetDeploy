import logging
import re
import numpy as np
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
from src.utils.data_processing import parse_coordinate
from src.utils.config import Config
from src.utils.logger import get_logger


class DataLoader:
    """数据加载器类，负责加载和处理数据"""

    def __init__(self):
        """初始化数据加载器"""
        self.logger = get_logger('data_loader')
        self.logger.info("数据加载器初始化")

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
            loader_logger = get_logger('data_loader')
            loader_logger.error(f"坐标解析错误: {coord_str} | 错误: {str(e)}")
            raise ValueError(f"无效的坐标格式: {coord_str}")

    def load_port_data(self, file_path: str = None, instance: str = None):
        """
        加载并预处理港口数据
        返回：包含标准化坐标的DataFrame
        """
        try:
            self.logger.info(f"开始加载港口数据: file_path={file_path}, instance={instance}")
            
            if file_path == None:
                file_path = Config.DATA_DIR / instance / "ports.csv"
                self.logger.debug(f"使用默认文件路径: {file_path}")
            else:
                file_path = file_path
                self.logger.debug(f"使用指定文件路径: {file_path}")
            
            self.logger.info(f"尝试读取CSV文件: {file_path}")
            df = pd.read_csv(file_path, encoding='GBK')
            self.logger.info(f"成功加载CSV文件，包含 {len(df)} 条港口数据")
            
            # 坐标转换
            self.logger.debug("开始处理坐标数据...")
            df['Longitude'] = df['Longitude'].apply(parse_coordinate)
            df['Latitude'] = df['Latitude'].apply(parse_coordinate)
            self.logger.debug("坐标数据处理完成")

            self.logger.debug("生成随机固定成本和运营成本...")
            df['FixedCost'] = np.random.randint(500, 1001, size=len(df))  # 包含1000
            df['Operation'] = np.random.randint(10000, 100001, size=len(df)) * 10
            self.logger.debug("成本数据生成完成")
                
            # 调整经度以太平洋为中心
            self.logger.info("调整经度以太平洋为中心...")
            delta = 110
            shift = delta
            shift -= 180
            df['NewLongitude'] = df['Longitude'].apply(lambda x : x - delta if x > shift else x + 360 - delta)
            self.logger.info("经度调整完成")
            
            self.logger.info(f"港口数据加载完成，共 {len(df)} 个港口")
            return df.reset_index(drop=True)
            
        except Exception as e:
            self.logger.error(f"加载港口数据失败: {str(e)}", exc_info=True)
            raise
    
    def load_history_results(self, instance: str):
        """
        加载历史优化结果数据
        :param instance: 实例名称，用于确定工作表名称
        :return: 包含历史结果的DataFrame（带合并后的表头）
        """
        try:
            self.logger.info(f"开始加载历史优化结果: instance={instance}")
            
            excel_path = Path("results/results.xlsx")
            if not excel_path.exists():
                self.logger.warning(f"结果文件不存在: {excel_path}")
                return pd.DataFrame()

            sheet_name = f"Instance{instance}"
            self.logger.debug(f"使用工作表: {sheet_name}")
            
            # 读取Excel数据，使用前两行作为多级表头
            self.logger.debug(f"尝试读取Excel文件: {excel_path}")
            df = pd.read_excel(
                excel_path,
                sheet_name=sheet_name,
                header=[0, 1]  # 使用前两行作为多级表头
            )
            self.logger.info(f"成功加载Excel文件，包含 {len(df)} 条历史结果")
            
            # 合并多级表头为单级（用下划线连接）
            self.logger.debug("合并多级表头...")
            df.columns = ['_'.join(map(str, col)).strip() for col in df.columns.values]
            df.rename(columns={
                                'Instance_Instance': 'Instance', 
                                'P_P':'P', 
                                'K_K': 'K',
                                'R_R': 'R',
                                'T_T': 'T',
                                'S_S': 'S'
                                })
            self.logger.debug("表头合并完成")
            
            self.logger.info(f"历史结果加载完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            self.logger.error(f"加载历史结果时出错: {str(e)}", exc_info=True)
            return pd.DataFrame()