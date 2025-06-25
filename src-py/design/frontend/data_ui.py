from pathlib import Path
import sys
import streamlit as st
import pandas as pd
import logging

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.extend([str(PROJECT_ROOT), 
                 str(PROJECT_ROOT / "src"), 
                 str(PROJECT_ROOT / "src" / "frontend"), 
                 str(PROJECT_ROOT / "src" / "lib")])

# 导入统一日志系统
from src.utils.logger import get_logger, set_log_level

# 获取数据UI模块的日志记录器
data_ui_logger = get_logger('data_ui')

from ..utils.data_loader import DataLoader

# 初始化session state
if 'params' not in st.session_state:
    st.session_state.params = {
        "model_params": {
            "default_speed": 20,  # 默认航速（节）
        }
    }

def calculate_arrival_time(distance, speed):
    """计算航行时间（小时）"""
    return distance / (speed * 1.852)  # 将节转换为km/h

def show_data_management():
    """显示数据管理界面"""
    st.header("📊 数据管理")
    
    # 创建五个子标签页
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["上传数据", "添加港口", "添加航线", "数据预览", "实时日志"])
    
    with tab1:
        st.subheader("上传数据文件")
        uploaded_file = st.file_uploader("选择CSV或Excel文件", type=['csv', 'xlsx'], key="data_file_uploader")
        
        if uploaded_file is not None:
            try:
                data_ui_logger.info(f"用户上传文件: {uploaded_file.name}")
                # 尝试不同的编码方式读取文件
                encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'latin1']
                df = None
                
                for encoding in encodings:
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df = pd.read_csv(uploaded_file, encoding=encoding)
                            data_ui_logger.debug(f"成功使用{encoding}编码读取CSV文件")
                        else:
                            df = pd.read_excel(uploaded_file)
                            data_ui_logger.debug("成功读取Excel文件")
                        break
                    except UnicodeDecodeError:
                        data_ui_logger.debug(f"尝试使用{encoding}编码读取失败")
                        continue
                
                if df is None:
                    error_msg = "无法读取文件，请检查文件格式和编码"
                    st.error(error_msg)
                    data_ui_logger.error(error_msg)
                    return
                
                # 定义列名映射
                column_mappings = {
                    '港口ID': ['港口ID', '港口编号', 'ID', 'id', 'port_id', 'PortID', 'portid'],
                    '港口名称': ['港口名称', '港口名', '名称','name', 'city', 'City', 'City_en', 'port_name', 'PortName', 'portname'],
                    '经度': ['经度', 'longitude', 'lon', 'LON', 'Longitude', 'long', 'Longitude(E)'],
                    '纬度': ['纬度', 'latitude', 'lat', 'LAT', 'Latitude', 'lati', 'Latitude(N)'],
                    '吞吐量': ['吞吐量', '年吞吐量', 'throughput', 'Throughput', 'capacity', 'Capacity', 'TEU'],
                    '区域': ['区域', '地区', 'region', 'Region', 'area', 'Area'],
                    '是否枢纽': ['是否枢纽', '枢纽港口', 'hub', 'Hub', 'is_hub', 'IsHub', '枢纽']
                }
                
                # 标准化列名
                df_columns = list(df.columns)
                column_mapping = {}
                
                for standard_name, possible_names in column_mappings.items():
                    for col in df_columns:
                        if col in possible_names:
                            column_mapping[col] = standard_name
                            data_ui_logger.debug(f"列名映射: {col} -> {standard_name}")
                            break
                
                # 重命名列
                df = df.rename(columns=column_mapping)
                data_ui_logger.info(f"完成列名标准化，映射情况: {column_mapping}")
                
                # 检查必要的列是否存在
                required_columns = ['港口ID', '港口名称', '经度', '纬度']  # 移除吞吐量
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    error_msg = f"文件缺少必要的列: {', '.join(missing_columns)}"
                    st.error(error_msg)
                    data_ui_logger.error(error_msg)
                    st.write("当前文件包含的列:", df_columns)
                    st.write("支持的列名格式:")
                    for std_name, poss_names in column_mappings.items():
                        st.write(f"- {std_name}: {', '.join(poss_names)}")
                    return
                
                # 处理可选列
                if '区域' not in df.columns:
                    df['区域'] = '未分类'
                    data_ui_logger.info("添加默认区域列: '未分类'")
                if '是否枢纽' not in df.columns:
                    df['是否枢纽'] = False
                    data_ui_logger.info("添加默认枢纽列: False")
                if '吞吐量' not in df.columns:
                    df['吞吐量'] = 0  # 设置默认值为0
                    data_ui_logger.info("添加默认吞吐量列: 0")
                
                # 数据类型转换
                try:
                    df['经度'] = pd.to_numeric(df['经度'], errors='coerce')
                    df['纬度'] = pd.to_numeric(df['纬度'], errors='coerce')
                    df['吞吐量'] = pd.to_numeric(df['吞吐量'], errors='coerce').fillna(0)  # 将无效值填充为0
                    data_ui_logger.debug("完成数据类型转换")
                    
                    # 检查数值范围
                    invalid_lon = df[(df['经度'] < -180) | (df['经度'] > 180)].shape[0]
                    invalid_lat = df[(df['纬度'] < -90) | (df['纬度'] > 90)].shape[0]
                    
                    if invalid_lon > 0 or invalid_lat > 0:
                        warning_msg = f"发现 {invalid_lon} 条经度或 {invalid_lat} 条纬度数据超出有效范围，这些数据将被标记为无效"
                        st.warning(warning_msg)
                        data_ui_logger.warning(warning_msg)
                except Exception as e:
                    error_msg = f"数据类型转换失败: {str(e)}"
                    st.error(error_msg)
                    data_ui_logger.error(error_msg)
                    return
                
                # 保存到session state
                st.session_state.current_ports_data = df
                st.success("数据加载成功！")
                data_ui_logger.info(f"成功加载港口数据，共{len(df)}条记录")
                
                # 更新港口数据到标准格式
                update_port_data_for_optimization()
                    
            except Exception as e:
                error_msg = f"加载数据时出错: {str(e)}"
                st.error(error_msg)
                data_ui_logger.exception(error_msg)
    
    with tab2:
        st.subheader("添加港口信息")
        
        # 创建两列布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 港口信息输入表单
            with st.form("port_form"):
                port_id = st.text_input("港口ID", help="请输入唯一的港口标识符")
                port_name = st.text_input("港口名称", help="请输入港口名称")
                
                # 区域选择
                region = st.selectbox(
                    "所属区域",
                    ["东亚", "东南亚", "南亚", "中东", "欧洲", "北美", "南美", "非洲", "大洋洲"],
                    help="请选择港口所属区域"
                )
                
                # 枢纽港口选择
                is_hub = st.checkbox("是否为枢纽港口", help="选择是否为枢纽港口")
                
                col3, col4 = st.columns(2)
                with col3:
                    longitude = st.number_input("经度", min_value=-180.0, max_value=180.0, value=0.0, format="%.6f",
                                             help="请输入经度值（-180到180）")
                with col4:
                    latitude = st.number_input("纬度", min_value=-90.0, max_value=90.0, value=0.0, format="%.6f",
                                            help="请输入纬度值（-90到90）")
                
                throughput = st.number_input("吞吐量(TEU/年)", min_value=0, value=100000,
                                          help="请输入年吞吐量（标准箱）")
                
                # 提交按钮
                submitted = st.form_submit_button("添加港口")
                
                if submitted:
                    if not port_id or not port_name:
                        st.error("港口ID和港口名称为必填项！")
                    else:
                        # 创建新的港口数据
                        new_port = pd.DataFrame({
                            '港口ID': [port_id],
                            '港口名称': [port_name],
                            '区域': [region],
                            '是否枢纽': [is_hub],
                            '经度': [longitude],
                            '纬度': [latitude],
                            '吞吐量': [throughput]
                        })
                        
                        # 如果已有数据，则合并
                        if 'current_ports_data' in st.session_state:
                            st.session_state.current_ports_data = pd.concat([st.session_state.current_ports_data, new_port], ignore_index=True)
                        else:
                            st.session_state.current_ports_data = new_port
                        
                        st.success(f"成功添加港口：{port_name}")
                        
                        # 更新港口数据到标准格式
                        update_port_data_for_optimization()
        
        with col2:
            # 显示已添加的港口列表
            st.markdown("#### 已添加的港口")
            if 'current_ports_data' in st.session_state and not st.session_state.current_ports_data.empty:
                st.dataframe(st.session_state.current_ports_data[['港口ID', '港口名称', '区域', '是否枢纽', '吞吐量']])
            else:
                st.info("暂无港口数据")
        
    with tab3:
        st.subheader("航线管理")
        
        # 检查是否有港口数据
        if 'current_ports_data' not in st.session_state or st.session_state.current_ports_data.empty:
            st.warning("请先添加港口数据")
            return
        
        # 初始化航线数据
        if 'routes' not in st.session_state:
            st.session_state.routes = []
        
        # 创建两列布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 航线信息输入表单
            with st.form("route_form"):
                route_id = st.text_input("航线ID", help="请输入唯一的航线标识符")
                
                # 选择起始港口
                start_port = st.selectbox(
                    "起始港口",
                    options=st.session_state.current_ports_data['港口名称'].tolist(),
                    help="选择航线起始港口"
                )
                
                # 添加访问港口
                st.markdown("#### 访问港口序列")
                if 'current_route' not in st.session_state:
                    st.session_state.current_route = []
                
                # 显示当前航线
                if st.session_state.current_route:
                    st.write("当前航线:")
                    for i, port in enumerate(st.session_state.current_route):
                        st.write(f"{i+1}. {port}")
                
                # 添加港口按钮
                next_port = st.selectbox(
                    "添加下一个港口",
                    options=st.session_state.current_ports_data['港口名称'].tolist(),
                    help="选择下一个访问的港口（允许重复访问）"
                )
                
                if st.form_submit_button("添加港口到航线"):
                    if next_port:
                        st.session_state.current_route.append(next_port)
                        st.rerun()
                
                # 清除航线按钮
                if st.form_submit_button("清除当前航线"):
                    st.session_state.current_route = []
                    st.rerun()
                
                # 保存航线按钮
                if st.form_submit_button("保存航线"):
                    if not route_id:
                        st.error("请输入航线ID")
                    elif not st.session_state.current_route:
                        st.error("请添加至少一个访问港口")
                    else:
                        # 计算到港时间
                        arrival_times = []
                        current_time = 0
                        
                        for i in range(len(st.session_state.current_route)):
                            if i == 0:
                                arrival_times.append(current_time)
                            else:
                                # 获取当前港口和前一个港口的位置
                                current_port = st.session_state.current_ports_data[
                                    st.session_state.current_ports_data['港口名称'] == st.session_state.current_route[i]
                                ].iloc[0]
                                prev_port = st.session_state.current_ports_data[
                                    st.session_state.current_ports_data['港口名称'] == st.session_state.current_route[i-1]
                                ].iloc[0]
                                
                                # 计算距离（使用简单的欧氏距离）
                                distance = ((current_port['经度'] - prev_port['经度'])**2 + 
                                          (current_port['纬度'] - prev_port['纬度'])**2)**0.5 * 111  # 粗略转换为公里
                                
                                # 计算航行时间
                                speed = st.session_state.params["model_params"]["default_speed"]
                                travel_time = calculate_arrival_time(distance, speed)
                                current_time += travel_time
                                arrival_times.append(current_time)
                        
                        # 创建航线数据
                        route_data = {
                            '航线ID': route_id,
                            '港口序列': st.session_state.current_route,
                            '到港时间': arrival_times
                        }
                        
                        st.session_state.routes.append(route_data)
                        st.session_state.current_route = []
                        st.success(f"成功添加航线：{route_id}")
                        st.rerun()
        
        with col2:
            # 显示已添加的航线
            st.markdown("#### 已添加的航线")
            if st.session_state.routes:
                for route in st.session_state.routes:
                    with st.expander(f"航线 {route['航线ID']}"):
                        st.write("访问序列:")
                        for i, (port, time) in enumerate(zip(route['港口序列'], route['到港时间'])):
                            st.write(f"{i+1}. {port} (到港时间: {time:.1f}小时)")
            else:
                st.info("暂无航线数据")
            
            # 导出航线数据
            if st.session_state.routes:
                if st.button("导出航线数据", key="export_routes_btn"):
                    routes_df = pd.DataFrame([
                        {
                            '航线ID': route['航线ID'],
                            '港口序列': '->'.join(route['港口序列']),
                            '到港时间': '->'.join([f"{t:.1f}" for t in route['到港时间']])
                        }
                        for route in st.session_state.routes
                    ])
                    csv = routes_df.to_csv(index=False)
                    st.download_button(
                        label="下载航线数据",
                        data=csv,
                        file_name="routes_data.csv",
                        mime="text/csv",
                        key="download_routes_btn"
                    )
    
    with tab4:
        st.subheader("数据预览")
        
        # 预览标签页
        preview_tab1, preview_tab2 = st.tabs(["原始数据", "优化数据格式"])
        
        with preview_tab1:
            # 显示当前数据
            if 'current_ports_data' in st.session_state and not st.session_state.current_ports_data.empty:
                st.dataframe(st.session_state.current_ports_data)
                
                # 导出数据按钮
                if st.button("导出数据", key="export_data_btn"):
                    import time
                    timestr = time.strftime("%Y%m%d-%H%M%S")
                    export_path = f"exported_data_{timestr}.csv"
                    st.session_state.current_ports_data.to_csv(export_path, index=False, encoding='utf-8-sig')
                    st.success(f"数据已导出到 {export_path}")
            else:
                st.info("请先上传或添加数据")
        
        with preview_tab2:
            # 显示优化格式数据
            if 'port_data' in st.session_state and not st.session_state.port_data.empty:
                st.markdown("#### 优化器将使用的港口数据")
                st.dataframe(st.session_state.port_data)
                
                # 显示港口数量和分布信息
                st.markdown("#### 港口统计信息")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("总港口数", len(st.session_state.port_data))
                with col2:
                    hub_count = st.session_state.port_data['is_hub'].sum() if 'is_hub' in st.session_state.port_data.columns else 0
                    st.metric("枢纽港口数", hub_count)
                with col3:
                    region_count = st.session_state.port_data['region'].nunique() if 'region' in st.session_state.port_data.columns else 0
                    st.metric("覆盖区域数", region_count)
                
                # 准备优化按钮
                if st.button("准备优化", key="prepare_optimization_btn"):
                    if 'port_data' in st.session_state:
                        st.success("港口数据已准备完毕，可以进行优化！")
                        st.info("请前往参数设置页面配置优化参数，然后点击侧边栏的【开始优化】按钮开始优化")
                    else:
                        st.error("港口数据准备失败，请检查数据格式")
            else:
                st.warning("尚未准备优化数据，请先上传或添加港口数据")
    
    with tab5:
        show_log_management()

def show_log_management():
    """显示实时日志管理界面"""
    st.subheader("📝 系统日志")
    
    # 日志开关控制
    if 'log_enabled' not in st.session_state:
        st.session_state.log_enabled = False
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        log_enabled = st.toggle("启用日志记录", value=st.session_state.log_enabled, key="log_toggle")
        if log_enabled != st.session_state.log_enabled:
            st.session_state.log_enabled = log_enabled
            # 设置日志级别
            if log_enabled:
                set_log_level("DEBUG")
                st.success("日志记录已启用")
                data_ui_logger.info("日志记录功能已启用")
            else:
                set_log_level("WARNING")
                st.warning("日志记录已禁用")
                data_ui_logger.warning("日志记录功能已禁用")
    
    with col2:
        if log_enabled:
            # 日志级别选择
            log_level = st.selectbox(
                "日志级别",
                ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=1,  # 默认INFO级别
                key="log_level_select"
            )
            # 设置日志级别
            set_log_level(log_level)
            st.caption(f"当前日志级别: {log_level}")
            data_ui_logger.info(f"日志级别已设置为: {log_level}")
    
    # 日志显示区域
    st.write("### 实时日志输出")
    log_display = st.empty()
    
    # 获取日志内容
    if 'log_messages' in st.session_state and st.session_state.log_messages:
        num_logs_to_show = st.slider("显示日志条数", min_value=10, max_value=100, value=30, key="log_count_slider")
        # 显示最新的若干条日志
        logs_to_show = st.session_state.log_messages[-num_logs_to_show:]
        
        # 使用代码块展示日志
        log_text = "\n".join(logs_to_show)
        log_display.code(log_text, language="text")
        
        # 添加功能按钮
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("清除日志", key="clear_log_btn"):
                st.session_state.log_messages = []
                data_ui_logger.info("用户清除了日志记录")
                st.success("日志已清除")
                st.rerun()
        with col2:
            if st.button("导出日志", key="export_log_btn"):
                log_text = "\n".join(st.session_state.log_messages)
                data_ui_logger.info("用户导出了日志记录")
                st.download_button(
                    label="下载日志文件",
                    data=log_text,
                    file_name="application_log.txt",
                    mime="text/plain",
                    key="download_log_btn"
                )
        with col3:
            if st.button("刷新日志", key="refresh_log_btn"):
                data_ui_logger.debug("用户刷新了日志显示")
                st.rerun()
    else:
        if log_enabled:
            log_display.info("暂无日志记录。系统操作将在此显示日志信息。")
            data_ui_logger.info("日志系统已启用，但尚无日志记录")
        else:
            log_display.warning("日志记录功能未启用。请开启日志记录以查看系统运行日志。")

def update_port_data_for_optimization():
    """将港口数据处理为优化所需的标准格式并存储到session state"""
    if 'current_ports_data' in st.session_state and not st.session_state.current_ports_data.empty:
        data_ui_logger.info("开始处理港口数据为优化格式")
        # 选择需要的列并重命名
        port_data = st.session_state.current_ports_data.copy()
        
        # 确保列名符合优化器要求
        column_mapping = {
            '港口ID': 'id',
            '港口名称': 'name',
            '经度': 'longitude',
            '纬度': 'latitude',
            '吞吐量': 'throughput',
            '区域': 'region',
            '是否枢纽': 'is_hub'
        }
        
        # 重命名列
        port_data = port_data.rename(columns=column_mapping)
        data_ui_logger.debug(f"列名已重命名: {column_mapping}")
        
        # 确保所有必要的列都存在
        for col in ['id', 'name', 'longitude', 'latitude']:
            if col not in port_data.columns:
                error_msg = f"缺少必要的列: {col}"
                st.error(error_msg)
                data_ui_logger.error(error_msg)
                return
        
        # 将处理后的数据保存到session state，供优化器使用
        st.session_state.port_data = port_data
        data_ui_logger.info(f"港口数据已更新为优化所需格式，共{len(port_data)}条记录")
        st.success("港口数据已更新为优化所需格式")