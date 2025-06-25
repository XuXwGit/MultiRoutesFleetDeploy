import logging
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))
from pathlib import Path
import matplotlib.pyplot as plt
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import threading
import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.extend([str(PROJECT_ROOT), str(PROJECT_ROOT / "src"), str(PROJECT_ROOT / "src" / "lib")])

from design.core.optimizer import ShippingNetworkOptimizer
from src.utils.data_loader import DataLoader
from src.utils.config import Config
from src.test.experiment_analyzer import ExperimentAnalyzer
from src.utils.visualization import ResultVisualizer
from src.utils.data_loader import DataLoader

# 初始化项目路径
def main():
    """主运行函数"""
    Config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        instance = "2"
        # 初始化实验分析器
        analyzer = ExperimentAnalyzer(instance= instance)
        # 运行不同类型的实验
        # logging.info("A. 中转次数的影响分析...")
        # analyzer.transit_limit_analysis()
        # logging.info("B. OD数量的影响分析...")  
        # analyzer.od_pairs_analysis()
        # logging.info("C. 线路数量的影响分析...")  
        # analyzer.routes_number_analysis()

        # 加载日志数据并分析绘图
        data_loader = DataLoader()
        result_df = data_loader.load_history_results(instance=instance)
        result_visualizer = ResultVisualizer(result_df)
        result_visualizer.draw_analysis(instance=instance, lang='en')
        result_visualizer.draw_analysis(instance=instance, lang='zh')

    except Exception as e:
        logging.error(f"程序运行出错: {str(e)}", exc_info=True)
        raise
    finally:
        plt.close('all')

if __name__ == "__main__":

    main()
