import numpy as np
import time
import os
import logging
from typing import List, Dict, Any, Union
from multi.entity.scenario import Scenario
from multi.model.parameter import Parameter
from multi.utils.default_setting import DefaultSetting
from multi.utils.input_data import InputData
from multi.entity.request import Request
logger = logging.getLogger(__name__)

class GenerateParameter:
    """参数生成类
    
    用于生成模型所需的各类参数:
    1. 成本参数
    2. 容量参数
    3. 时间参数
    4. 需求参数
    5. 网络参数
    """
    
    def __init__(self, 
                 input_data: InputData, 
                 param: Parameter, 
                 time_horizon: int, 
                 uncertain_degree: float):
        """初始化参数生成器
        
        Args:
            input_data: 输入数据(网络结构、需求等)
            param: 参数类
            time_horizon: 时间范围
            uncertain_degree: 不确定度
        """
        self.input_data = input_data
        self.time_horizon = time_horizon
        self.uncertain_degree = uncertain_degree
        self.param = param
        np.random.seed(DefaultSetting.RANDOM_SEED)  # 设置随机种子
        self.frame()
        
    def frame(self):
        """参数生成的主框架"""
        logger.info("========Start to Generate parameters========")
        start_time = time.time()

        self.param.time_horizon = self.time_horizon
        self.param.tau = int(np.sqrt(len(self.input_data.requests)) * DefaultSetting.BUDGET_COEFFICIENT)
        self.param.uncertain_degree = self.uncertain_degree
        self.input_data.uncertain_degree = self.uncertain_degree

        self.set_arc_set()
        self.set_time_point()
        self.set_ports()
        self.set_requests()
        self.set_ship_routes()
        self.set_vessels()
        self.set_vessel_paths()
        self.set_container_paths()
        self.set_arc_capacity()
        self.set_initial_empty_containers()

        if DefaultSetting.WHETHER_GENERATE_SAMPLES:
            self.generate_random_sample_scene_set()
        if DefaultSetting.WHETHER_LOAD_SAMPLE_TESTS:
            self.param.sample_scenes = self.input_data.sample_scenes

        end_time = time.time()
        logger.info(f"========End Generate parameters ({end_time - start_time:.2f}s)========")

    def set_arc_set(self):
        """设置弧集合"""
        # 设置航行弧ID集合
        traveling_arcs_set = [arc.traveling_arc_id for arc in self.input_data.traveling_arcs]
        self.param.traveling_arcs_set = traveling_arcs_set
        logger.info(f"traveling_arcs_set: A1={len(traveling_arcs_set)}")

        # 设置转运弧ID集合
        transshipment_arcs_set = [arc.transship_arc_id for arc in self.input_data.transship_arcs]
        self.param.transhipment_arcs_set = transshipment_arcs_set
        logger.info(f"transshipment_arcs_set: A2={len(transshipment_arcs_set)}")

    def set_time_point(self):
        """设置时间点集合"""
        # 时间点集合 = {0, 1, 2, ..., T}
        time_point_set = list(range(self.time_horizon + 1))
        self.param.time_horizon = self.time_horizon
        self.param.time_point_set = time_point_set
        logger.info(f"time_point_set: T={len(time_point_set)}")

    def set_ports(self):
        """设置港口参数"""
        # 设置租赁成本、周转时间、滞期成本等
        self.param.rental_cost = DefaultSetting.DEFAULT_UNIT_RENTAL_COST
        
        port_set = []
        turn_over_time = []
        laden_demurrage_cost = []
        empty_demurrage_cost = []
        
        for port in self.input_data.port_set.values():
            port_set.append(port.port)
            turn_over_time.append(DefaultSetting.DEFAULT_TURN_OVER_TIME)
            laden_demurrage_cost.append(DefaultSetting.DEFAULT_LADEN_DEMURRAGE_COST)
            empty_demurrage_cost.append(DefaultSetting.DEFAULT_EMPTY_DEMURRAGE_COST)
            
            port.rental_cost = DefaultSetting.DEFAULT_UNIT_RENTAL_COST
            port.turn_over_time = DefaultSetting.DEFAULT_TURN_OVER_TIME
            port.laden_demurrage_cost = DefaultSetting.DEFAULT_LADEN_DEMURRAGE_COST
            port.empty_demurrage_cost = DefaultSetting.DEFAULT_EMPTY_DEMURRAGE_COST
            port.loading_cost = DefaultSetting.DEFAULT_UNIT_LOADING_COST
            port.discharge_cost = DefaultSetting.DEFAULT_UNIT_DISCHARGE_COST
            port.transshipment_cost = DefaultSetting.DEFAULT_UNIT_TRANSSHIPMENT_COST
            
        self.param.port_set = port_set
        self.param.turn_over_time = turn_over_time
        self.param.laden_demurrage_cost = laden_demurrage_cost
        self.param.empty_demurrage_cost = empty_demurrage_cost
        logger.info(f"port_set: P={len(port_set)}")

    def set_requests(self):
        """设置请求参数"""
        # 设置需求、惩罚成本等
        demand_request = []
        origin_of_demand = []
        destination_of_demand = []
        demand = []
        demand_maximum = []
        penalty_cost_for_demand = []
        
        for request in self.input_data.requests:
            try:
                # logger.info(f"request: {request}")
                demand_request.append(request.request_id)
                origin_of_demand.append(request.origin_port)
                destination_of_demand.append(request.destination_port)
                
                group_o = self.input_data.port_set[request.origin_port].group
                group_d = self.input_data.port_set[request.destination_port].group
                group_range = self.input_data.group_range_map[f"{group_o}{group_d}"]
                
                # 生成需求
                if group_range is None:
                    demand_value = group_range.demand_lower_bound + int(
                        (group_range.demand_upper_bound - group_range.demand_lower_bound) * 
                        self.get_rand_double()
                    )
                    # 生成惩罚成本
                    penalty = group_range.freight_lower_bound + int(
                        (group_range.freight_upper_bound - group_range.freight_lower_bound) * 
                        self.get_rand_double()
                    )
                else:
                    demand_value = 0
                    penalty = 0
                
                penalty *= DefaultSetting.PENALTY_COEFFICIENT
                
                request.penalty_cost = penalty
                request.mean_demand = demand_value
                demand_maximum_value = demand_value * self.uncertain_degree
                request.variance_demand = demand_maximum_value
                
                demand.append(demand_value)
                demand_maximum.append(demand_maximum_value)
                penalty_cost_for_demand.append(penalty)

            except Exception as e:
                logger.error(f"Error in set_requests: {e}")
            
        self.param.demand_request_set = demand_request
        self.param.origin_of_demand = origin_of_demand
        self.param.destination_of_demand = destination_of_demand
        self.param.demand = demand
        self.param.maximum_demand_variation = demand_maximum
        self.param.penalty_cost_for_demand = penalty_cost_for_demand

        logger.info(f"demand_request_set: I={len(demand_request)}")

    def set_ship_routes(self):
        """设置航线参数"""
        # 设置航线ID集合和往返次数
        vessel_route = []
        round_trips = []
        
        for route in self.input_data.ship_route_set.values():
            vessel_route.append(route.ship_route_id)
            round_trips.append(route.num_round_trips)
            
        self.param.shipping_route_set = vessel_route
        self.param.num_of_round_trips = round_trips

        logger.info(f"shipping_route_set: R={len(vessel_route)}")

    def set_vessels(self):
        """设置船舶参数"""
        # 设置船舶类型、容量、运营成本等
        vessel = []
        vessel_capacity = []
        vessel_operation_cost = []
        vessel_type_and_shipping_route = np.zeros(
            (len(self.input_data.vessel_type_set), len(self.input_data.ship_route_set))
        )
        shipping_route_vessel_num = np.zeros(len(self.param.shipping_route_set))
        
        for i, vessel_type in enumerate(self.input_data.vessel_type_set.values()):
            vessel_type_and_shipping_route[i][vessel_type.route_id - 1] = 1
            shipping_route_vessel_num[vessel_type.route_id - 1] += 1
            
            vessel.append(vessel_type.id)
            vessel_capacity.append(vessel_type.capacity)
            vessel_operation_cost.append(vessel_type.cost)
            
        self.param.vessel_type_and_ship_route = vessel_type_and_shipping_route
        self.param.vessel_set = vessel
        self.param.vessel_capacity = vessel_capacity
        self.param.vessel_operation_cost = vessel_operation_cost
        self.param.shipping_route_vessel_num = shipping_route_vessel_num

        logger.info(f"vessel_set: V={len(vessel)}")

    def set_vessel_paths(self):
        """设置船舶路径参数"""
        # 设置航线与船舶路径的关系矩阵
        ship_route_and_vessel_path = np.zeros(
            (len(self.input_data.ship_route_set), len(self.input_data.vessel_paths))
        )
        vessel_path_set = []
        arc_and_vessel_path = np.zeros(
            (len(self.input_data.traveling_arcs), len(self.input_data.vessel_paths))
        )
        vessel_path_ship_route_set = []
        
        for w, vessel_path in enumerate(self.input_data.vessel_paths):
            vessel_path_id = vessel_path.vessel_path_id
            route_idx = vessel_path.route_id - 1
            
            ship_route_and_vessel_path[route_idx][w] = 1
            vessel_path_ship_route_set.append(route_idx)
            
            # 设置弧与船舶路径的关系矩阵
            for nn, arc in enumerate(self.input_data.traveling_arcs):
                if arc.traveling_arc_id in vessel_path.arc_ids:
                    arc_and_vessel_path[nn][w] = 1
                    
            vessel_path_set.append(vessel_path_id)
            
        self.param.arc_and_vessel_path = arc_and_vessel_path
        self.param.ship_route_and_vessel_path = ship_route_and_vessel_path
        self.param.vessel_path_set = vessel_path_set
        self.param.vessel_path_ship_route_index = vessel_path_ship_route_set

        logger.info(f"vessel_path_set: VP={len(vessel_path_set)}")

    def set_container_paths(self):
        """设置集装箱路径参数"""
        # 计算每条路径的总滞期成本
        path_load_and_discharge_cost = []
        laden_path_demurrage_cost = []
        empty_path_demurrage_cost = []
        laden_path_cost = []
        empty_path_cost = []
        travel_time_on_laden_path = []
        path_set = []
        arc_and_path = np.zeros(
            (len(self.input_data.traveling_arc_set), len(self.input_data.container_paths))
        )
        port_and_path = {}

        for x, container_path in enumerate(self.input_data.container_paths):
            # 计算装卸成本
            load_discharge_cost = 0
            for port in self.input_data.port_set.values():
                if port.port == container_path.origin_port:
                    load_discharge_cost += port.loading_cost
                elif port.port == container_path.destination_port:
                    load_discharge_cost += port.discharge_cost
                else:
                    if container_path.transshipment_port:
                        for trans_port in container_path.transshipment_port:
                            if port.port == trans_port:
                                load_discharge_cost += port.transshipment_cost

            container_path.path_cost = load_discharge_cost
            path_load_and_discharge_cost.append(load_discharge_cost)
            
            # 计算滞期成本
            laden_demurrage = max(0, 175 * container_path.get_total_demurrage_time())
            empty_demurrage = max(0, 100 * container_path.get_total_demurrage_time())
            
            laden_path_demurrage_cost.append(laden_demurrage)
            empty_path_demurrage_cost.append(empty_demurrage)
            
            # 计算总成本
            laden_path_cost.append(laden_demurrage + load_discharge_cost)
            empty_path_cost.append(empty_demurrage + load_discharge_cost * 0.5)

            travel_time_on_laden_path.append(container_path.path_time)
            path_set.append(container_path.container_path_id)
            
            # 设置弧与路径的关系矩阵
            for i, arc in enumerate(self.input_data.traveling_arcs):
                if arc.traveling_arc_id in container_path.arcs_id:
                    arc_and_path[i][x] = 1

            #  设置港口与路径的关系矩阵
            for port in container_path.ports_in_path:
                port_and_path[port][container_path.id] = 1
                    
        self.param.laden_path_demurrage_cost = laden_path_demurrage_cost
        self.param.empty_path_demurrage_cost = empty_path_demurrage_cost
        self.param.laden_path_cost = laden_path_cost
        self.param.empty_path_cost = empty_path_cost
        self.param.travel_time_on_path = travel_time_on_laden_path
        self.param.path_set = path_set
        self.param.arc_and_path = arc_and_path
        self.param.port_and_path = port_and_path

        logger.info(f"path_set: CP={len(path_set)}")

    def set_arc_capacity(self):
        """设置弧容量"""
        for nn in range(len(self.param.traveling_arcs_set)):
            capacity = 0
            for r in range(len(self.param.shipping_route_set)):
                for w in range(len(self.param.vessel_path_set)):
                    for h in range(len(self.param.vessel_set)):
                        capacity += (
                            self.param.arc_and_vessel_path[nn][w] *
                            self.param.vessel_capacity[h] *
                            self.param.ship_route_and_vessel_path[r][w] *
                            self.param.vessel_type_and_ship_route[h][r]
                        )
                        
            if DefaultSetting.DEBUG_ENABLE and DefaultSetting.GENERATE_PARAM_ENABLE:
                arc = self.input_data.traveling_arcs[nn]
                logger.info(
                    f"RouteID = {arc.route_id}\t"
                    f"TravelArcID = {arc.traveling_arc_id}\t"
                    f"({arc.origin_node}--{arc.destination_node})\t"
                    f"Total Capacity = {capacity}"
                )
        logger.info(f"arc_capacity: A1={len(self.param.traveling_arcs_set)}")

    def set_initial_empty_containers(self):
        """设置初始空箱量"""
        # 计算每个港口在时间0的初始空箱量
        initial_empty_container = np.zeros(len(self.input_data.port_set))
        
        alpha = 0.8 + 0.2 * self.get_rand_double()
        for x, port in enumerate(self.input_data.port_set.values()):
            for request in self.input_data.requests:
                if (port.port == request.origin_port and 
                    request.earliest_pickup_time < DefaultSetting.INITIAL_EMPTY_CONTAINERS):
                    initial_empty_container[x] += alpha * self.param.demand[request.request_id - 1]
                    
        self.param.initial_empty_container = initial_empty_container

        logger.info(f"initial_empty_container: I0={len(initial_empty_container)}")

    def get_rand_double(self) -> float:
        """生成随机数
        
        Returns:
            float: 随机数
        """
        mean = 0.5
        variance = 1.0 / 12.0
        
        if DefaultSetting.DISTRIBUTION_TYPE == "Uniform":
            return np.random.random()
        elif DefaultSetting.DISTRIBUTION_TYPE == "Normal":
            return np.random.normal()
        elif DefaultSetting.DISTRIBUTION_TYPE == "Log-Normal":
            # Log-Normal distribution:
            # mean = exp(mu + sigma^2/2)
            # variance = (exp(sigma^2) - 1) * exp(2 * mu + sigma^2)
            sigma = np.sqrt(np.log(1 + variance)) * DefaultSetting.LOG_NORMAL_SIGMA_FACTOR
            mu = np.log(mean) - 0.5 * sigma * sigma
            # 返回服从Log-normal分布的近似随机数：standard normal --> log-normal
            # z ~ N(0,1) --> X = exp(mu + sigma * z)
            return np.exp(mu + sigma * np.random.normal())
        else:
            return np.random.random()

    def generate_random_sample_scene_set(self):
        """生成随机样本场景"""
        logger.info(f"begin to generate_random_sample_scene_set: S={DefaultSetting.NUM_SAMPLE_SCENES}")

        sample_scenes = np.zeros((DefaultSetting.NUM_SAMPLE_SCENES, len(self.input_data.requests)))
        scenarios = []
        
        try:
            for i in range(DefaultSetting.NUM_SAMPLE_SCENES):
                selected_requests = set()
                while len(selected_requests) < self.param.tau:
                    selected_requests.add(np.random.randint(len(self.input_data.requests)))
                    
                scene = ""
                for j in selected_requests:
                    sample_scenes[i][j] = 1
                    scene += f"{j},"
                    
                scenarios.append(Scenario(request=sample_scenes[i], scenario_id=i))
            
        except Exception as e:
            logger.error(f"Error in generate_random_sample_scene_set: {e}")

        self.param.sample_scenes = sample_scenes
        self.input_data.scenarios = scenarios

        logger.info(f"sample_scenes: S={len(sample_scenes)}")

        if DefaultSetting.WHETHER_WRITE_SAMPLE_TESTS:
            self.write_random_sample_scene_set()

    def write_random_sample_scene_set(self):
        """写入随机样本场景"""
        sample_filename = (
            f"R{len(self.input_data.ship_routes)}-T{self.param.time_horizon}"
            f"-Tau{self.param.tau}-S{DefaultSetting.RANDOM_SEED}-SampleTestSet.txt"
        )
        file_path = os.path.join(
            DefaultSetting.ROOT_PATH,
            DefaultSetting.DATA_PATH,
            DefaultSetting.CASE_PATH,
            sample_filename
        )
        
        with open(file_path, "w") as f:
            for i in range(len(self.param.sample_scenes)):
                f.write(f"{i}\t")
                for j in range(len(self.param.sample_scenes[i])):
                    if self.param.sample_scenes[i][j] != 0:
                        f.write(f"{j},")
                f.write("\n")
