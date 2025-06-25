"""
航运网络设计系统 - 参数设置界面模块
功能：
1. 模型约束参数设置
2. 目标函数类型设置
3. 算法参数配置
"""

import streamlit as st
import json
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List

def load_default_params():
    """加载默认参数设置"""
    return {
        "model_params": {
            "max_ports_per_route": 5,
            "min_ports_per_route": 2,
            "max_routes": 10,
            "min_routes": 3,
            "max_distance": 5000,
            "min_load_factor": 0.6,
            "max_load_factor": 0.9,
            "max_transfer": 2,
            "default_speed": 20  # 默认航速（节）
        },
        "cost_params": {
            "fixed_cost": 1000,
            "distance_cost": 1.0,
            "time_cost": 10.0,
            "port_cost": 500
        },
        "algorithm_params": {
            "algorithm": "Genetic Algorithm",
            "population_size": 100,
            "generations": 100,
            "mutation_rate": 0.1,
            "crossover_rate": 0.8,
            "time_limit": 300
        }
    }

def save_params(params):
    """保存参数设置到文件"""
    params_file = Path("params.json")
    with open(params_file, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=4, ensure_ascii=False)
    st.success("参数已保存！")

def show_parameter_settings():
    """显示参数设置界面"""

    ##################################################################################
    # 模型参数设置
    st.header("模型参数设置")
    with st.expander("航运网络约束", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # 容量约束
            st.subheader("容量约束")
            max_ports_per_route = st.number_input(
                "每条路线最大港口数", 
                min_value=2, 
                max_value=20, 
                value=8, 
                step=1
            )
            
            max_route_count = st.number_input(
                "最大规划航行数量", 
                min_value=1, 
                max_value=50, 
                value=10, 
                step=1
            )
            
            num_of_ODs = st.slider(
                "服务运输OD数量", 
                min_value=0, 
                max_value=1000, 
                value=100, 
                step=50
            )
        
        with col2:
            # 时间和距离约束
            st.subheader("时间和距离约束")
            max_distance_per_route = st.number_input(
                "每条路线最大距离(海里)", 
                min_value=1000, 
                max_value=50000, 
                value=20000, 
                step=1000
            )
            
            max_route_duration = st.number_input(
                "每条路线最大持续时间(天)", 
                min_value=5, 
                max_value=60, 
                value=30, 
                step=1
            )

            default_speed = st.number_input(
                "默认航速(节)", 
                min_value=10, 
                max_value=60,
                value=20, 
                step=1
            )

            
            service_frequency = st.selectbox(
                "服务频率", 
                options=["weekly", "biweekly", "monthly"],
                format_func=lambda x: {
                    "weekly": "每周一次",
                    "biweekly": "每两周一次",
                    "monthly": "每月一次"
                }.get(x, x)
            )
    
    # 必经港口设置
    with st.expander("覆盖港口设置"):
        st.info("从下面选择必须覆盖的港口")
        
        # 港口数据应该从会话状态或数据服务中获取
        # 这里使用示例数据
        if 'port_data' in st.session_state:
            port_data = st.session_state.port_data
            port_options = port_data['name'].tolist()
            
            required_ports = st.multiselect(
                "覆盖港口",
                options=port_options,
                default=[]
            )
        else:
            st.warning("请先在数据管理页面导入港口数据")
    


    ##########################################################################################
    st.header("优化参数设置")
    
    # 创建三列布局
    col1, col2 = st.columns([1, 2])
    
    # 声明权重变量并设置默认值
    cost_weight = 0.0
    demand_weight = 0.0
    utility_weight = 0.0
    single_objective = "成本"  # 默认单目标优化指标
    
    with col1:
        # 算法选择
        st.subheader("算法基本设置")
        algorithm = st.selectbox(
            "优化算法", 
            options=["alns", "genetic", "simulated_annealing", "linear_programming"],
            format_func=lambda x: {
                "alns": "ALNS (自适应大领域搜索)",
                "genetic": "遗传算法",
                "simulated_annealing": "模拟退火",
                "linear_programming": "线性规划"
            }.get(x, x)
        )
        
        # 保存算法选择到会话状态
        st.session_state.selected_algorithm = algorithm
        
        # 通用设置
        max_time = st.number_input(
            "最大运行时间(秒)", 
            min_value=0, 
            max_value=3600, 
            value=10, 
            step=10
        )

        iterations = st.slider(
            "迭代次数", 
            min_value=0, 
            max_value=10000, 
            value=100, 
            step=100
        )

        # 随机种子设置
        use_random_seed = st.checkbox("使用固定随机种子", value=False)
        random_seed = st.number_input(
            "随机种子", 
            min_value=1, 
            max_value=100000, 
            value=42, 
            step=1,
            disabled=not use_random_seed
        )
        
        # 并行计算设置
        enable_parallel = st.checkbox("启用并行计算", value=False)
        if enable_parallel:
            num_workers = st.slider(
                "并行线程数", 
                min_value=2, 
                max_value=16, 
                value=4, 
                step=1
            )
    
    with col2:
        # 算法特定参数
        st.subheader(f"{get_algorithm_display_name(algorithm)}参数")
        
        if algorithm == "genetic":
            show_genetic_parameters()
        elif algorithm == "simulated_annealing":
            show_simulated_annealing_parameters()
        elif algorithm == "alns":
            show_alns_parameters()
        elif algorithm == "linear_programming":
            show_linear_programming_parameters()
        elif algorithm == "vns":
            show_vns_parameters()
    
    ##################################################################################
    # 目标函数权重设置
    st.header("目标函数权重设置")
    st.info("设置多目标优化的权重（总和应为1）")
    
    # 优化目标选择
    st.subheader("优化目标选择")
    # 单目标还是多目标
    single_or_multi_objective = st.selectbox(
        "优化目标",
        options=["单目标", "多目标"],
        format_func=lambda x: {
            "单目标": "单目标",
            "多目标": "多目标"
        }.get(x, x)
    )
    # 单目标优化
    if single_or_multi_objective == "单目标":
        single_objective = st.selectbox(
            "优化指标",
            options=["成本", "需求", "效用"],
        format_func=lambda x: {
            "成本": "成本",
            "需求": "需求",
            "效用": "效用"
        }.get(x, x)
        )
        
        st.subheader("优化方向")
        optimization_direction = st.selectbox(
            "优化方向",
            options=["最小化", "最大化"],
            format_func=lambda x: {
                "最小化": "最小化", 
                "最大化": "最大化"
            }.get(x, x)
        )
        
    # 多目标优化
    if single_or_multi_objective == "多目标":
        col1, col2, col3 = st.columns(3)
        
        with col1:
            cost_weight = st.slider(
                "成本权重", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.6, 
                step=0.05
            )
        
        with col2:
            demand_weight = st.slider(
                "需求权重", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.3, 
                step=0.05
            )
        
        with col3:
            utility_weight = st.slider(
                "效用权重", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.1, 
                step=0.05
            )
        
        # 检查权重总和
        total_weight = cost_weight + demand_weight + utility_weight
        if abs(total_weight - 1.0) > 0.01:
            st.warning(f"警告：权重总和为 {total_weight:.2f}，应为1.0")

        st.subheader("优化方向")
        optimization_direction = st.selectbox(
            "优化方向",
            options=["最小化", "最大化"],
            format_func=lambda x: {
                "最小化": "最小化", 
                "最大化": "最大化"
            }.get(x, x)
        )
    
    # 保存配置按钮
    if st.button("保存配置"):
        # 单目标模式下设置权重
        if single_or_multi_objective == "单目标":
            # 单目标时设置对应权重为1.0
            cost_weight = 1.0 if single_objective == "成本" else 0.0
            demand_weight = 1.0 if single_objective == "需求" else 0.0
            utility_weight = 1.0 if single_objective == "效用" else 0.0
            
        # 收集所有配置
        config = {
            "algorithm": algorithm,
            "max_time": max_time,
            "max_iterations": iterations,
            "random_seed": random_seed if use_random_seed else None,
            "parallel": {
                "enabled": enable_parallel,
                "num_workers": num_workers if enable_parallel else 1
            },
            "algorithm_params": get_algorithm_params(algorithm),
            "constraints": {
                "max_ports_per_route": max_ports_per_route,
                "max_route_count": max_route_count,
                "num_of_ODs": num_of_ODs,
                "max_distance_per_route": max_distance_per_route,
                "max_route_duration": max_route_duration,
                "service_frequency": service_frequency,
                "required_ports": required_ports if 'required_ports' in locals() else []
            },
            "objective_weights": {
                "cost": cost_weight,
                "demand": demand_weight,
                "utility": utility_weight
            },
            "default_speed": default_speed
        }
        
        # 保存到会话状态
        st.session_state.optimization_config = config
        st.success("配置已保存！可以开始优化")
        
        # 调试模式下显示配置详情
        if st.session_state.get("debug_mode", False):
            st.json(config)

def show_genetic_parameters():
    """显示遗传算法参数"""
    col1, col2 = st.columns(2)
    
    with col1:
        population_size = st.slider(
            "种群大小", 
            min_value=20, 
            max_value=500, 
            value=100, 
            step=10
        )
        
        generations = st.slider(
            "迭代次数(世代)", 
            min_value=10, 
            max_value=1000, 
            value=100, 
            step=10
        )
        
        crossover_rate = st.slider(
            "交叉概率", 
            min_value=0.1, 
            max_value=1.0, 
            value=0.8, 
            step=0.05
        )
        
        mutation_rate = st.slider(
            "变异概率", 
            min_value=0.01, 
            max_value=0.5, 
            value=0.1, 
            step=0.01
        )
    
    with col2:
        # 遗传算子设置
        crossover_operator = st.selectbox(
            "交叉算子",
            options=["single_point", "two_point", "uniform", "pmx"],
            format_func=lambda x: {
                "single_point": "单点交叉",
                "two_point": "双点交叉",
                "uniform": "均匀交叉",
                "pmx": "部分映射交叉(PMX)"
            }.get(x, x)
        )
        
        selection_operator = st.selectbox(
            "选择算子",
            options=["tournament", "roulette", "rank"],
            format_func=lambda x: {
                "tournament": "锦标赛选择",
                "roulette": "轮盘赌选择",
                "rank": "排序选择"
            }.get(x, x)
        )
        
        # 锦标赛大小（仅当选择锦标赛选择时显示）
        tournament_size = st.slider(
            "锦标赛大小", 
            min_value=2, 
            max_value=10, 
            value=3, 
            step=1,
            disabled=selection_operator != "tournament"
        )
        
        elitism = st.slider(
            "精英保留数量", 
            min_value=0, 
            max_value=20, 
            value=2, 
            step=1
        )
    
    # 保存参数到会话状态
    st.session_state.ga_params = {
        "population_size": population_size,
        "generations": generations,
        "crossover_rate": crossover_rate,
        "mutation_rate": mutation_rate,
        "crossover_operator": crossover_operator,
        "selection_operator": selection_operator,
        "tournament_size": tournament_size,
        "elitism": elitism
    }

def show_simulated_annealing_parameters():
    """显示模拟退火算法参数"""
    col1, col2 = st.columns(2)
    
    with col1:
        initial_temperature = st.slider(
            "初始温度", 
            min_value=100.0, 
            max_value=10000.0, 
            value=1000.0, 
            step=100.0
        )
        
        cooling_rate = st.slider(
            "冷却率", 
            min_value=0.5, 
            max_value=0.99, 
            value=0.95, 
            step=0.01
        )
    
    with col2:
        iterations_per_temp = st.slider(
            "每个温度的迭代次数", 
            min_value=1, 
            max_value=100, 
            value=10, 
            step=1
        )
        
        min_temperature = st.slider(
            "最低温度", 
            min_value=0.1, 
            max_value=100.0, 
            value=1.0, 
            step=0.1
        )
    
    # 邻域结构选择
    neighborhood_type = st.selectbox(
        "邻域结构类型",
        options=["swap", "insertion", "inversion", "two_opt", "all"],
        format_func=lambda x: {
            "swap": "交换 (Swap)",
            "insertion": "插入 (Insertion)",
            "inversion": "反转 (Inversion)",
            "two_opt": "2-opt",
            "all": "全部使用"
        }.get(x, x)
    )
    
    # 保存参数到会话状态
    st.session_state.sa_params = {
        "initial_temperature": initial_temperature,
        "cooling_rate": cooling_rate,
        "iterations_per_temp": iterations_per_temp,
        "min_temperature": min_temperature,
        "neighborhood_type": neighborhood_type
    }

def show_alns_parameters():
    """显示自适应大邻域搜索参数"""
    col1, col2 = st.columns(2)
    
    with col1:

        decay_parameter = st.slider(
            "衰减参数", 
            min_value=0.1, 
            max_value=1.0, 
            value=0.8, 
            step=0.05
        )

    
    # with col2:
    #     noise_parameter = st.slider(
    #         "噪声参数", 
    #         min_value=0.0, 
    #         max_value=0.5, 
    #         value=0.1, 
    #         step=0.01
    #     )
        
        # segment_size = st.slider(
        #     "分段大小", 
        #     min_value=10, 
        #     max_value=500, 
        #     value=100, 
        #     step=10
        # )
    
    # ALNS权重调整参数
    st.subheader("权重调整参数")
    col1, col2 = st.columns(2)
    
    with col1:
        omega_1 = st.slider(
            "全局最优解奖励(ω1)", 
            min_value=1.0, 
            max_value=20.0, 
            value=10.0, 
            step=0.5
        )
        
        omega_2 = st.slider(
            "当前最优解奖励(ω2)", 
            min_value=0.5, 
            max_value=15.0, 
            value=5.0, 
            step=0.5
        )
    
    # with col2:
        omega_3 = st.slider(
            "接受解奖励(ω3)", 
            min_value=0.1, 
            max_value=10.0, 
            value=2.0, 
            step=0.1
        )
        
        omega_4 = st.slider(
            "拒绝解惩罚(ω4)", 
            min_value=0.0, 
            max_value=5.0, 
            value=0.5, 
            step=0.1
        )
    
    # 破坏和修复操作的选择
    st.subheader("操作符选择")
    col1, col2 = st.columns(2)
    
    with col1:
        destroy_operators = ["random_removal", "worst_removal", "shaw_removal", "related_removal", "cluster_removal"]
        selected_destroy = st.multiselect(
            "破坏操作",
            options=destroy_operators,
            default=destroy_operators[:3],
            format_func=lambda x: {
                "random_removal": "随机移除",
                "worst_removal": "最差移除",
                "shaw_removal": "Shaw相关性移除",
                "related_removal": "相关性移除",
                "cluster_removal": "聚类移除"
            }.get(x, x)
        )
    
    with col2:
        repair_operators = ["greedy_insertion", "regret_insertion", "random_insertion", "nearest_insertion", "k_regret"]
        selected_repair = st.multiselect(
            "修复操作",
            options=repair_operators,
            default=repair_operators[:2],
            format_func=lambda x: {
                "greedy_insertion": "贪婪插入",
                "regret_insertion": "遗憾插入",
                "random_insertion": "随机插入",
                "nearest_insertion": "最近插入",
                "k_regret": "k-遗憾插入"
            }.get(x, x)
        )
    
    # 保存参数到会话状态
    st.session_state.alns_params = {
        # "max_iterations": iterations,
        # "segment_size": segment_size,
        # "noise_parameter": noise_parameter,
        "decay_parameter": decay_parameter,
        "omega_1": omega_1,
        "omega_2": omega_2,
        "omega_3": omega_3,
        "omega_4": omega_4,
        "destroy_operators": selected_destroy,
        "repair_operators": selected_repair
    }

def show_linear_programming_parameters():
    """显示线性规划参数"""
    col1, col2 = st.columns(2)
    
    with col1:
        solver = st.selectbox(
            "求解器",
            options=["cbc", "glpk", "cplex", "gurobi"],
            format_func=lambda x: {
                "cbc": "CBC",
                "glpk": "GLPK",
                "cplex": "CPLEX (商业)",
                "gurobi": "Gurobi (商业)"
            }.get(x, x)
        )
        
        time_limit = st.slider(
            "最大求解时间(秒)", 
            min_value=10, 
            max_value=7200, 
            value=3600, 
            step=10
        )
    
    with col2:
        gap_tolerance = st.slider(
            "间隙容差", 
            min_value=0.0001, 
            max_value=0.1, 
            value=0.01, 
            step=0.0001,
            format="%.4f"
        )
        
        relaxation = st.checkbox(
            "启用LP松弛", 
            value=False
        )
    
    # 其他线性规划选项
    presolve = st.checkbox("启用预解", value=True)
    
    warm_start = st.checkbox("使用热启动解", value=False)
    
    verbose = st.checkbox("详细输出", value=False)
    
    # 保存参数到会话状态
    st.session_state.lp_params = {
        "solver": solver,
        "time_limit": time_limit,
        "gap_tolerance": gap_tolerance,
        "relaxation": relaxation,
        "presolve": presolve,
        "warm_start": warm_start,
        "verbose": verbose
    }

def show_vns_parameters():
    """显示变邻域搜索参数"""
    col1, col2 = st.columns(2)
    
    with col1:
        iterations = st.slider(
            "迭代次数", 
            min_value=10, 
            max_value=1000, 
            value=100, 
            step=10
        )
        
        max_no_improvement = st.slider(
            "无改进最大次数", 
            min_value=5, 
            max_value=100, 
            value=20, 
            step=5
        )
    
    with col2:
        shaking_intensity = st.slider(
            "扰动强度", 
            min_value=1, 
            max_value=10, 
            value=3, 
            step=1
        )
        
        local_search_iterations = st.slider(
            "局部搜索迭代次数", 
            min_value=1, 
            max_value=100, 
            value=10, 
            step=1
        )
    
    # 邻域结构选择
    st.subheader("邻域结构")
    neighborhood_structures = ["swap", "insertion", "inversion", "two_opt", "or_opt", "three_opt", "relocate"]
    selected_neighborhoods = st.multiselect(
        "启用的邻域结构",
        options=neighborhood_structures,
        default=neighborhood_structures[:4],
        format_func=lambda x: {
            "swap": "交换",
            "insertion": "插入",
            "inversion": "反转",
            "two_opt": "2-opt",
            "or_opt": "OR-opt",
            "three_opt": "3-opt",
            "relocate": "重定位"
        }.get(x, x)
    )
    
    # 是否使用最佳改进
    best_improvement = st.radio(
        "局部搜索策略",
        options=["first_improvement", "best_improvement"],
        format_func=lambda x: {
            "first_improvement": "首次改进",
            "best_improvement": "最佳改进"
        }.get(x, x)
    )
    
    # 保存参数到会话状态
    st.session_state.vns_params = {
        "max_iterations": iterations,
        "max_no_improvement": max_no_improvement,
        "shaking_intensity": shaking_intensity,
        "local_search_iterations": local_search_iterations,
        "neighborhoods": selected_neighborhoods,
        "best_improvement": best_improvement == "best_improvement"
    }

def get_algorithm_display_name(algorithm: str) -> str:
    """获取算法的显示名称"""
    algorithm_names = {
        "genetic": "遗传算法",
        "simulated_annealing": "模拟退火算法",
        "alns": "自适应大邻域搜索",
        "linear_programming": "线性规划",
        "vns": "变邻域搜索"
    }
    return algorithm_names.get(algorithm, algorithm)

def get_algorithm_params(algorithm: str) -> Dict[str, Any]:
    """从会话状态获取当前算法的参数"""
    if algorithm == "genetic":
        return st.session_state.get("ga_params", {})
    elif algorithm == "simulated_annealing":
        return st.session_state.get("sa_params", {})
    elif algorithm == "alns":
        return st.session_state.get("alns_params", {})
    elif algorithm == "linear_programming":
        return st.session_state.get("lp_params", {})
    elif algorithm == "vns":
        return st.session_state.get("vns_params", {})
    return {}