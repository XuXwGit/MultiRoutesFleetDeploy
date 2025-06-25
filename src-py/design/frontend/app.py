"""
航运服务网络设计系统 - 主界面模块
功能：
1. 初始化页面布局配置
2. 管理功能选项卡（数据/参数/结果/可视化）
3. 协调各子模块交互
4. 实时状态管理
"""

from pathlib import Path
import sys
import streamlit as st
import time
from typing import Dict, Any, Callable
import threading
import logging
import os

# 添加项目根目录到Python路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

# 导入统一日志系统
from src.utils.logger import get_logger, setup_streamlit_logging, set_log_level

# 获取应用日志记录器
app_logger = get_logger('app')
# 确保有文件处理器
if not app_logger.handlers:
    fh = logging.FileHandler('app.log')
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    app_logger.addHandler(fh)

# 导入其他模块
from src.backend.optimizer_executor import OptimizerExecutor
from src.frontend.data_ui import show_data_management
from src.frontend.param_ui import show_parameter_settings
from src.frontend.result_ui import show_results
from src.frontend.visualization_ui import show_visualization
# 导入优化服务
from src.backend.services.optimization_service import OptimizationService


def initialize_session_state():
    """初始化会话状态变量"""
    if 'optimization_status' not in st.session_state:
        st.session_state.optimization_status = 'ready'  # ready, running, completed
    if 'current_iteration' not in st.session_state:
        st.session_state.current_iteration = 0
    if 'best_solution' not in st.session_state:
        st.session_state.best_solution = None
    if 'optimization_history' not in st.session_state:
        st.session_state.optimization_history = []
    
    if 'optimizer_executor' not in st.session_state:
        st.session_state.optimizer_executor = OptimizerExecutor()
        
    # 添加日志消息列表
    if 'log_messages' not in st.session_state:
        st.session_state.log_messages = []
        
    # 添加日志状态
    if 'log_enabled' not in st.session_state:
        st.session_state.log_enabled = False
        
    # 设置Streamlit日志处理器
    setup_streamlit_logging()
    
    # 记录初始化完成
    app_logger.info("会话状态初始化完成")


def run_backend_optimization():
    """使用OptimizerExecutor执行后端优化"""
    try:
        # 创建一个调试容器，直接在页面上显示信息
        debug_container = st.empty()
        debug_container.info("开始优化过程...")
        
        # 添加日志记录
        app_logger.info("开始执行后端优化")
        
        # 检查是否有配置
        if 'optimization_config' not in st.session_state:
            st.error("未找到优化配置，请先在参数设置页面保存配置")
            app_logger.error("未找到优化配置，优化任务中止")
            return False
            
        # 获取优化配置
        config = st.session_state.optimization_config
        app_logger.info(f"读取优化配置成功: 算法={config.get('algorithm', '未指定')}")
        debug_container.info(f"优化配置: 算法={config.get('algorithm', '未指定')}, 最大迭代={config.get('max_iterations', '未指定')}")
        
        # 获取执行器
        executor = st.session_state.optimizer_executor
        
        # 准备数据
        if 'current_ports_data' in st.session_state:
            config['ports_data'] = st.session_state.current_ports_data.to_dict('records')
            app_logger.info(f"港口数据准备完成，共 {len(config['ports_data'])} 个港口")
            debug_container.info(f"港口数据准备完成，共 {len(config['ports_data'])} 个港口")
        else:
            st.error("未找到港口数据，请先在数据管理页面导入数据")
            app_logger.error("未找到港口数据，优化任务中止")
            return False
            
        # 打印算法和数据信息到优化结果界面
        st.write("准备启动优化...")
        st.write(f"优化算法: {config.get('algorithm', '未指定')}")
        st.write(f"港口数据: {len(config.get('ports_data', []))}个港口")
        
        # 创建一个状态指示器
        status_indicator = st.empty()
        
        # 重要: 创建OptimizationService实例，而不是传递类
        optimization_service = OptimizationService()
        app_logger.info("已创建OptimizationService实例")
        debug_container.info("已创建OptimizationService实例")
        
        # 启动优化 - 传递实例而非类
        app_logger.info("开始启动优化执行器...")
        debug_container.warning("正在执行优化，这可能需要一些时间...")
        status_indicator.info("⏳ 优化进行中...")
        
        # 直接在这里执行优化，而不是使用线程，便于调试
        try:
            # 直接调用优化服务
            debug_container.info("直接调用优化服务...")
            result = optimization_service(config)
            debug_container.success("优化服务调用完成")
            
            # 保存结果
            st.session_state.optimization_result = result
            st.session_state.optimization_status = 'completed'
            
            # 显示结果摘要
            if result:
                debug_container.success(f"优化完成! 结果键: {list(result.keys())}")
                if 'routes' in result:
                    debug_container.info(f"生成了 {len(result['routes'])} 条航线")
                if 'total_cost' in result:
                    debug_container.info(f"总成本: {result['total_cost']}")
                
                # 保存结果到文件
                # import json
                # with open("optimization_result.json", "w", encoding="utf-8") as f:
                #     json.dump(result, f, ensure_ascii=False, indent=4)
                # debug_container.info("结果已保存到文件")
            else:
                debug_container.error("优化结果为空")
            
            status_indicator.success("✅ 优化完成!")
            return True
            
        except Exception as e:
            import traceback
            error_msg = f"直接优化调用出错: {str(e)}"
            debug_container.error(error_msg)
            debug_container.error(traceback.format_exc())
            app_logger.error(error_msg)
            app_logger.error(traceback.format_exc())
            status_indicator.error("❌ 优化失败!")
            
            # 创建错误结果
            st.session_state.optimization_result = {
                'error': str(e),
                'traceback': traceback.format_exc(),
                'ports': config.get('ports_data', []),
                'routes': [],
                'total_cost': 0
            }
            st.session_state.optimization_status = 'completed'
            return False
            
    except Exception as e:
        import traceback
        error_msg = f"优化过程异常: {str(e)}"
        app_logger.error(error_msg)
        app_logger.error(traceback.format_exc())
        st.error(error_msg)
        
        # 确保有结果
        st.session_state.optimization_result = {
            'error': str(e),
            'traceback': traceback.format_exc(),
            'ports': config.get('ports_data', []) if 'config' in locals() else [],
            'routes': [],
            'total_cost': 0
        }
        st.session_state.optimization_status = 'completed'
        return False



def show_sidebar():
    """显示侧边栏控制面板"""
    with st.sidebar:
        st.header("系统控制")
        
        # 系统状态显示
        status_color = {
            'ready': '🟢',
            'running': '🟡',
            'completed': '🔵'
        }
        st.write(f"{status_color[st.session_state.optimization_status]} 系统状态: {st.session_state.optimization_status.upper()}")
        
        # 控制按钮
        if st.session_state.optimization_status != 'running':
            if st.button("🚀 开始优化", key='start_btn'):
                st.session_state.optimization_status = 'running'
                st.session_state.run_optimization = True
        else:
            if st.button("⏹️ 停止优化", key='stop_btn'):
                st.session_state.optimization_status = 'ready'
                
        # 系统信息
        st.divider()
        st.caption("系统信息")
        st.caption(f"当前迭代次数: {st.session_state.current_iteration}")
        if st.session_state.best_solution:
            st.caption(f"最优解成本: {st.session_state.best_solution:.2f}")
            
        # 添加日志控制选项
        st.divider()
        log_enabled = st.checkbox("启用详细日志", value=st.session_state.get('log_enabled', False), key="sidebar_log_toggle")
        if log_enabled != st.session_state.get('log_enabled', False):
            st.session_state.log_enabled = log_enabled
            # 设置日志级别
            if log_enabled:
                set_log_level("DEBUG")
                app_logger.info("详细日志已启用")
            else:
                set_log_level("WARNING")
                app_logger.warning("详细日志已禁用")
            st.rerun()
            
        # 显示日志统计
        if 'log_messages' in st.session_state:
            st.caption(f"日志记录: {len(st.session_state.log_messages)}条")
            
        # 添加日志显示区域
        st.divider()
        st.subheader("实时日志")
        
        # 创建一个空容器用于显示日志
        log_container = st.container()
        
        # 如果有日志消息，显示最新的几条
        with log_container:
            if 'log_messages' in st.session_state and st.session_state.log_messages:
                # 只显示最新的10条日志
                logs_to_show = st.session_state.log_messages[-10:]
                for log in logs_to_show:
                    if "ERROR" in log or "error" in log.lower():
                        st.error(log)
                    elif "WARNING" in log or "warning" in log.lower():
                        st.warning(log)
                    elif "INFO" in log or "info" in log.lower():
                        st.info(log)
                    else:
                        st.text(log)
                
                # 添加查看更多日志链接
                if len(st.session_state.log_messages) > 10:
                    st.caption("在【数据管理】->【实时日志】页面查看完整日志")


def app():
    """应用主入口函数"""
    # 初始化页面配置
    st.set_page_config(
        page_title="航运服务网络设计系统",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your_repo',
            'Report a bug': 'mailto:xuxw@bit.edu.cn',
            'About': "# 航线优化系统V1.0\n开发者：[Xu Xw]"
        }
    )
    
    # 初始化会话状态
    initialize_session_state()
    
    # 添加日志记录
    app_logger.info("应用启动")
    
    # 添加一个自动刷新机制，以更新日志显示
    auto_refresh = st.sidebar.checkbox("自动刷新界面", value=True, key="auto_refresh_toggle")
    if auto_refresh:
        # 添加一个小间隔的自动刷新，确保日志能实时展示
        auto_refresh_interval = st.sidebar.number_input("刷新间隔(秒)", 
                                                        min_value=1, 
                                                        max_value=10,
                                                        value=2,
                                                        key="refresh_interval")
        if st.session_state.get('optimization_status') == 'running':
            # 如果正在优化，使用更短的刷新间隔
            auto_refresh_interval = min(auto_refresh_interval, 1)
            st.sidebar.info(f"优化运行中: 使用{auto_refresh_interval}秒刷新间隔")
        else:
            st.sidebar.write(f"每{auto_refresh_interval}秒自动刷新页面")
    
    # 显示侧边栏
    show_sidebar()
    
    # 主页面标题
    st.title("航运服务网络优化设计系统")
    
    # 如果设置了自动刷新，添加自动刷新代码
    if auto_refresh:
        # 添加一个隐藏的元素，其值每次刷新都会变化，这会触发重新渲染
        st.empty().text(f"上次刷新时间: {time.strftime('%H:%M:%S')}")
        st.sidebar.text(f"下次刷新: {auto_refresh_interval}秒后")
        
        # 使用进度条显示刷新倒计时
        if 'refresh_counter' not in st.session_state:
            st.session_state.refresh_counter = 0
        
        # 最小进度显示
        min_progress = 0.05
        
        # 根据当前计数器状态显示进度
        progress_val = min(st.session_state.refresh_counter / auto_refresh_interval, 1.0)
        if progress_val < min_progress:
            progress_val = min_progress
            
        refresh_progress = st.sidebar.progress(progress_val, "刷新进度")
        
        # 增加计数器
        st.session_state.refresh_counter += 0.1
        
        # 如果到达刷新时间，重置计数器并刷新
        if st.session_state.refresh_counter >= auto_refresh_interval:
            st.session_state.refresh_counter = 0
            time.sleep(0.1)  # 短暂等待，确保UI更新
            st.rerun()
        
        # 添加一个小延迟，让计数器平滑增加
        time.sleep(0.1)
    
    # 主要功能选项卡
    tab1, tab2, tab3, tab4 = st.tabs([
                                      "📊 数据管理", 
                                      "⚙️ 参数设置", 
                                      "📈 优化结果", 
                                      "🌍 可视化"])
    
    with tab1:
        show_data_management()
        
    with tab2:
        show_parameter_settings()
        
    with tab3:
        if st.session_state.optimization_status in ['running', 'completed']:
            show_results()
        else:
            st.info("请点击侧边栏的【开始优化】按钮开始优化过程")
            
    with tab4:
        show_visualization()

    # 检查是否需要执行优化
    if st.session_state.get('run_optimization', False):
        with st.spinner("正在优化..."):
            # 记录开始优化
            app_logger.info("开始执行优化任务")
            
            # 这里调用后端优化逻辑
            run_backend_optimization()
            
            # 完成后更新状态
            st.session_state.optimization_status = 'completed'
            st.session_state.run_optimization = False
            
            # 记录优化完成
            app_logger.info("优化任务已完成")
            
            # 重新加载页面显示结果
            st.rerun()


if __name__ == "__main__":
    app()