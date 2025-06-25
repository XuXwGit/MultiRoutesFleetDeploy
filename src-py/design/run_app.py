"""
航运网络设计系统启动脚本
"""

import os
import sys
import logging
from pathlib import Path

# 获取项目根目录
project_root = Path(__file__).resolve().parent.parent

# 添加项目根目录到Python路径
sys.path.append(str(project_root))

# 导入统一日志系统
from src.utils.logger import get_logger, log_manager

def main():
    """主函数"""
    # 获取主日志记录器
    logger = get_logger('main')
    logger.info("="*50)
    logger.info("航运服务网络设计系统启动")
    logger.info("="*50)
    
    # 检查环境
    try:
        import streamlit
        import pandas
        import plotly
        import folium
    except ImportError as e:
        logger.error(f"错误: 缺少必要的依赖包。请先运行: pip install -r requirements.txt")
        logger.error(f"具体错误: {str(e)}")
        sys.exit(1)
    
    # 直接导入并运行应用
    try:
        from src.frontend.app import app
        app()
    except Exception as e:
        logger.error(f"启动应用失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()