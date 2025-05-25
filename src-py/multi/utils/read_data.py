import logging
import time
from typing import List, Dict, Any
import pandas as pd
from multi.entity.vessel_type import VesselType
from multi.utils.input_data import InputData
from multi.network import Port, Node, Arc, TravelingArc, TransshipArc, VesselPath, LadenPath, EmptyPath, Request, ShipRoute, ContainerPath, ODRange
from multi.utils.default_setting import DefaultSetting

logger = logging.getLogger(__name__)

class ReadData:
    """
    数据读取类，用于从本地文件读取输入数据。
    
    该类负责读取所有必要的数据文件，包括：
    - 航运网络数据（港口和航线）
    - 时空网络数据（节点、航行弧、转运弧）
    - 集装箱路径数据（重箱路径和空箱路径）
    - 船舶数据
    - 订单/请求数据
    - 历史解决方案和样本场景
    
    Attributes:
        input_data: 输入数据对象
        time_horizon: 时间范围
        file_path: 数据文件路径
    """
    
    def __init__(self, path: str, input_data: InputData, time_horizon: int):
        """
        初始化数据读取器
        
        Args:
            path: 数据文件相对路径
            input_data: 输入数据对象
            time_horizon: 时间范围
        """
        self.input_data = input_data
        self.time_horizon = time_horizon
        self.file_path = DefaultSetting.ROOT_PATH + "/" + path
        self._frame()
        
        if DefaultSetting.WHETHER_PRINT_DATA_STATUS:
            input_data.show_status()

    def _frame(self):
        """
        数据读取的主框架，按顺序读取所有必要的数据
        """
        logger.info("========Start to read data========")
        start_time = time.time()

        self.input_data.time_horizon = self.time_horizon
        
        # 1. 读取航运网络数据（包括港口和航线）
        self._read_ports()
        self._read_ship_routes()

        # 2. 读取时空网络数据（包括节点、航行弧、转运弧）
        self._read_nodes()
        self._read_traveling_arcs()
        self._read_transship_arcs()

        # 3. 读取集装箱路径数据（包括重箱路径和空箱路径）
        self._read_container_paths()
        self._read_vessel_paths()
        self._read_laden_paths()
        self._read_empty_paths()

        # 4. 读取船舶数据
        self._read_vessels()

        # 5. 读取订单/请求数据
        self._read_demand_range()
        self._read_requests()

        # 6. 读取历史解决方案和样本场景
        if DefaultSetting.USE_HISTORY_SOLUTION:
            self._read_history_solution()
        if DefaultSetting.WHETHER_LOAD_SAMPLE_TESTS:
            self._read_sample_scenes()

        end_time = time.time()
        logger.info(f"========End read data ({end_time - start_time:.2f}s)========")

    def _read_to_dataframe(self, filename: str) -> pd.DataFrame:
        """
        从本地文件读取数据到DataFrame
        
        Args:
            filename: 文件名
            
        Returns:
            pd.DataFrame: 包含文件数据的DataFrame
        """
        try:
            file_path = self.file_path + filename
            logger.info(f"Reading file: {file_path}")
            return pd.read_csv(file_path, sep='\t', encoding='GBK')
        except Exception as e:
            logger.error(f"Error reading file {filename}: {str(e)}")
            raise

    def _read_demand_range(self):
        """
        读取需求范围数据
        
        文件格式：
        OriginRegion DestinationRegion DemandLowerBound DemandUpperBound FreightLowerBound FreightUpperBound
        1 2 20 40 2000 2500
        2 1 40 60 2000 2500
        ...
        """
        df = self._read_to_dataframe("DemandRange.txt")
        range_map = {}
        
        for _, row in df.iterrows():
            od_range = ODRange(
                origin_group=int(row["OriginRegion"]),
                destination_group=int(row["DestinationRegion"]),
                demand_lower_bound=int(row["DemandLowerBound"]),
                demand_upper_bound=int(row["DemandUpperBound"]),
                freight_lower_bound=int(row["FreightLowerBound"]),
                freight_upper_bound=int(row["FreightUpperBound"])
            )
            key = f"{row[0]}{row[1]}"
            range_map[key] = od_range
            
        self.input_data.group_range_map = range_map

    def _read_container_paths(self):
        """
        读取集装箱路径数据
        
        文件格式：
        ContainerPathID OriginPort OriginTime DestinationPort DestinationTime PathTime TransshipPort TransshipTime PortPath_length PortPath Arcs_length Arcs_ID
        1 A 2 B 3 1 0 0 2 A,B 1 1
        2 A 9 B 10 1 0 0 2 A,B 1 9
        ...
        """
        df = self._read_to_dataframe("Paths.txt")
        container_path_list = []
        container_paths = {}
        
        for _, row in df.iterrows():
            container_path = ContainerPath(
                container_path_id=int(row["ContainerPathID"]),
                origin_port=row["OriginPort"],
                origin_time=int(row["OriginTime"]),
                destination_port=row["DestinationPort"],
                destination_time=int(row["DestinationTime"]),
                path_time=int(row["PathTime"]),
            )
            
            # 设置转运信息
            if row[6] != '0':  # 如果有转运港口
                transship_ports = row[6].split(',')
                transship_times = [int(t) for t in row[7].split(',')]
                for port, time in zip(transship_ports, transship_times):
                    container_path.add_transshipment(
                        self.input_data.port_set[port],
                        time
                    )
            
            # 设置港口路径
            port_path = row[9].split(',')
            for port in port_path:
                container_path.add_port_in_path(self.input_data.port_set[port])
            
            # 设置弧
            arc_ids = [int(aid) for aid in row[11].split(',')]
            for arc_id in arc_ids:
                container_path.add_arc(self.input_data.arc_set[arc_id])
            
            container_path_list.append(container_path)
            container_paths[container_path.container_path_id] = container_path
        
        self.input_data.container_paths = container_path_list
        self.input_data.container_path_set = container_paths

    def _read_ports(self):
        """
        读取港口数据
        
        文件格式：
        PortID PortName RegionID WhetherTransshipment Group
        1 A 1 1 1
        2 B 2 0 1
        ...
        """
        df = self._read_to_dataframe("Ports.txt")
        port_list = []
        ports = {}
        
        # 设置默认值
        default_turn_over_time = DefaultSetting.DEFAULT_TURN_OVER_TIME
        default_laden_demurrage_cost = DefaultSetting.DEFAULT_LADEN_DEMURRAGE_COST
        default_empty_demurrage_cost = DefaultSetting.DEFAULT_EMPTY_DEMURRAGE_COST
        default_unit_loading_cost = DefaultSetting.DEFAULT_UNIT_LOADING_COST
        default_unit_discharge_cost = DefaultSetting.DEFAULT_UNIT_DISCHARGE_COST
        default_unit_transshipment_cost = DefaultSetting.DEFAULT_UNIT_TRANSSHIPMENT_COST
        default_unit_rental_cost = DefaultSetting.DEFAULT_UNIT_RENTAL_COST
        
        for _, row in df.iterrows():
            port = Port(
                id=int(row[0]),
                port=row[1],
                whether_trans=int(row[2]),
                region=row[3],
                group=int(row[4]),
                turn_over_time=default_turn_over_time,
                laden_demurrage_cost=default_laden_demurrage_cost,
                empty_demurrage_cost=default_empty_demurrage_cost,
                loading_cost=default_unit_loading_cost,
                discharge_cost=default_unit_discharge_cost,
                transshipment_cost=default_unit_transshipment_cost,
                rental_cost=default_unit_rental_cost
            )
            port_list.append(port)
            ports[port.port] = port
            
        self.input_data.ports = port_list
        self.input_data.port_set = ports

    def _read_ship_routes(self):
        """
        读取航线数据
        
        文件格式：
        ShipRouteID CycleTime NumRoundTrips NumberOfPorts PortCallSequence
        1 10 2 3 A,B,C
        2 15 1 4 A,C,D,B
        ...
        """
        df = self._read_to_dataframe("Shipingroute.txt")
        route_list = []
        routes = {}
        
        for _, row in df.iterrows():
            route = ShipRoute(
                ship_route_id=int(row["ShippingRouteID"]),
                time_points_of_call=[int(t) for t in row["Time"].split(',')],
                ports_of_call=list(row["Ports"].split(',')),
            )
            
            # 设置港口调用序列
            port_sequence = row["Ports"].split(',')
            for port in port_sequence:
                route.add_port_call(self.input_data.port_set[port])
            
            route_list.append(route)
            routes[route.ship_route_id] = route
            
        self.input_data.ship_routes = route_list
        self.input_data.ship_route_set = routes

    def _read_nodes(self):
        """
        读取节点数据
        
        文件格式：
        NodeID PortID Time
        1 A 0
        2 A 1
        ...
        """
        df = self._read_to_dataframe("Nodes.txt")
        node_list = []
        nodes = {}
        
        for _, row in df.iterrows():
            node = Node(
                id=int(row[0]),
                port_string=row[1],
                node_id=int(row[0]),
                route=0,  # 默认值
                call=0,   # 默认值
                round_trip=0,  # 默认值
                time=int(row[2]),
                port=self.input_data.port_set[row["Port"]]
            )
            node_list.append(node)
            nodes[node.node_id] = node
            
        self.input_data.nodes = node_list
        self.input_data.node_set = nodes

    def _read_traveling_arcs(self):
        """
        读取航行弧数据
        
        文件格式：
        ArcID OriginNodeID DestinationNodeID TravelTime Cost
        1 1 2 1 100
        2 2 3 1 150
        ...
        """
        df = self._read_to_dataframe("TravelingArcs.txt")
        arc_list = []
        arcs = {}
        
        for _, row in df.iterrows():
            arc = TravelingArc(
                arc_id=int(row["TravelingArc_ID"]),
                route_id=int(row["Route"]),
                round_trip=int(row["Round_Trip"]),
                origin_node=self.input_data.node_set[int(row["Origin_node_ID"])],
                destination_node=self.input_data.node_set[int(row["Destination_node_ID"])],
                travel_time=int(row["TravelingTime"]),
            )
            arc_list.append(arc)
            arcs[arc.id] = arc
            
        self.input_data.traveling_arcs = arc_list
        self.input_data.traveling_arc_set = arcs

    def _read_transship_arcs(self):
        """
        读取转运弧数据
        
        文件格式：
        TransshipArcID	Port	Origin_node_ID	OriginTime	TransshipTime	Destination_node_ID	DestinationTime	FromRoute	ToRoute
        272	D	4	10	2	172	12	1	2
        273	D	4	10	9	178	19	1	2
        274	F	6	14	6	179	20	1	2
        ...
        """
        df = self._read_to_dataframe("TransshipArcs.txt")
        arc_list = []
        arcs = {}
        
        for _, row in df.iterrows():
            arc = TransshipArc(
                id=int(row["TransshipArcID"]),
                port=self.input_data.port_set[row["Port"]],
                origin_node=self.input_data.node_set[int(row["Origin_node_ID"])],
                destination_node=self.input_data.node_set[int(row["Destination_node_ID"])],
                from_route=int(row["FromRoute"]),
                to_route=int(row["ToRoute"]),
                transship_time=int(row["TransshipTime"]),
            )
            arc_list.append(arc)
            arcs[arc.id] = arc
            
        self.input_data.transship_arcs = arc_list
        self.input_data.transship_arc_set = arcs
        
        # 合并所有弧
        self.input_data.arcs = self.input_data.traveling_arcs + self.input_data.transship_arcs
        self.input_data.arc_set = {**self.input_data.traveling_arc_set, **self.input_data.transship_arc_set}

    def _read_vessel_paths(self):
        """
        读取船舶路径数据
        
        文件格式：
        VesselPathID RouteID NumberOfArcs ArcIDs OriginTime DestinationTime PathTime
        1 1 2 1,2 0 2 2
        2 1 2 3,4 2 4 2
        ...
        """
        df = self._read_to_dataframe("VesselPaths.txt")
        vessel_path_list = []
        vessel_paths = {}
        
        for _, row in df.iterrows():
            vessel_path = VesselPath(
                vessel_path_id=int(row["VesselPathID"]),
                route_id=int(row["VesselRouteID"]),
                number_of_arcs=int(row["NumOfArcs"]),
                origin_time=int(row["originTime"]),
                destination_time=int(row["destinationTime"]),
                path_time=int(row["destinationTime"]) - int(row["originTime"])
            )
            
            # 设置弧ID和弧对象
            arc_ids = [int(aid) for aid in row[3].split(',')]
            vessel_path.arc_ids = arc_ids
            vessel_path.arcs = [self.input_data.arc_set[aid] for aid in arc_ids]
            
            vessel_path_list.append(vessel_path)
            vessel_paths[vessel_path.vessel_path_id] = vessel_path
            
        self.input_data.vessel_paths = vessel_path_list
        self.input_data.vessel_path_set = vessel_paths

    def _read_laden_paths(self):
        """
        读取重箱路径数据
        
        文件格式：
        RequestID	OriginPort	OriginTime	DestinationPort	RoundTrip	W_i_Earlist	ArrivalTime_to_Destination	PathTime	TransshipPort	TransshipTime	PathID	Port_Path	ArcIDs
        1	A	2	B	1	1	3	1	0	0	1	A,B	1
        1	A	9	B	1	1	10	1	0	0	2	A,B	9
        2	A	9	B	2	8	10	1	0	0	2	A,B	9
        ...
        """
        df = self._read_to_dataframe("LadenPaths.txt")
        laden_path_list = []
        laden_paths = {}
        
        for _, row in df.iterrows():
            laden_path = LadenPath(
                request_id=int(row["RequestID"]),
            )
            
            # 设置船舶路径
            container_path = self.input_data.container_path_set[int(row["PathID"])]
            laden_path.number_of_arcs = container_path.number_of_arcs
            laden_path.arc_ids = container_path.arcs_id
            laden_path.arcs = container_path.arcs
            laden_path.origin_time = container_path.origin_time
            laden_path.arrival_time_to_destination = container_path.destination_time
            laden_path.path_time = container_path.path_time
            laden_path.path_id = container_path.container_path_id
            laden_path_list.append(laden_path)
            
            laden_paths[laden_path.path_id] = laden_path
            
        self.input_data.laden_paths = laden_path_list
        self.input_data.laden_path_set = laden_paths

    def _read_empty_paths(self):
        """
        读取空箱路径数据
        
        文件格式：
        EmptyPathID ContainerType Volume VesselPathID
        1 1 20 1
        2 1 20 2
        ...
        """
        df = self._read_to_dataframe("EmptyPaths.txt")
        empty_path_list = []
        empty_paths = {}
        
        for _, row in df.iterrows():
            if int(row["NumOfEmptyPath"]) <= 0:
                continue
            for path_id_str in row["PathIDs"].split(','):
                container_path = self.input_data.container_path_set[int(path_id_str)]
                empty_path = EmptyPath(
                    path_id=int(path_id_str),
                    request_id=int(row["RequestID"]),
                    origin_port_string=row["OriginPort"],
                    origin_time=int(row["OriginTime"]),
                    container_path=container_path,
                    origin_port=self.input_data.port_set[row["OriginPort"]]
                )
        
                empty_path_list.append(empty_path)
                empty_paths[empty_path.path_id] = empty_path
            
        self.input_data.empty_paths = empty_path_list
        self.input_data.empty_path_set = empty_paths

    def _read_requests(self):
        """
        读取请求数据
        
        文件格式：
        RequestID	OriginPort	DestinationPort	W_i_Earlist	LatestDestinationTime	LadenPaths	NumberOfLadenPath	EmptyPaths	NumberOfEmptyPath
        1	A3	A1	1	15	2442,2443	2	0	0
        2	A4	A9	1	15	3938,3939	2	0	0
        ...
        """
        df = self._read_to_dataframe("Requests.txt")
        request_list = []
        requests = {}
        
        for _, row in df.iterrows():
            request = Request(
                request_id=int(row["RequestID"]),
                earliest_pickup_time=int(row["W_i_Earlist"]),
                latest_destination_time=int(row["LatestDestinationTime"]),
                origin_port=row["OriginPort"],
                destination_port=row["DestinationPort"]
            )
            
            # 设置重箱路径和空箱路径
            request.number_of_laden_path = int(row["NumberOfLadenPath"])
            request.number_of_empty_path = int(row["NumberOfEmptyPath"])
            # 设置重箱路径
            if request.number_of_laden_path > 0:
                request.laden_paths = [
                    self.input_data.laden_path_set[int(path_id)] for path_id in row["LadenPaths"].split(',')
                    if int(path_id) in self.input_data.laden_path_set
                ]
                request.laden_path_set = {
                    laden_path.path_id: laden_path
                    for laden_path in request.laden_paths
                }
                request.laden_path_indexes = [
                    laden_path.path_id - 1
                    for laden_path in request.laden_paths
                ]
            else:
                request.laden_paths = []
            # 设置空箱路径
            if request.number_of_empty_path > 0:
                request.empty_paths = [
                    self.input_data.empty_path_set[int(path_id)] for path_id in row["EmptyPaths"].split(',')
                    if int(path_id) in self.input_data.empty_path_set
                ]
                request.empty_path_set = {
                    empty_path.path_id: empty_path
                    for empty_path in request.empty_paths
                }
                request.empty_path_indexes = [
                    empty_path.path_id - 1
                    for empty_path in request.empty_paths
                ]
            else:
                request.empty_paths = []
            
            request_list.append(request)
            requests[request.request_id] = request
            
        self.input_data.requests = request_list
        self.input_data.request_set = requests

    def _read_vessels(self):
        """
        读取船舶数据
        
        文件格式：
        VesselID  Capacity  OperatingCost  RouteID  maxNum
        0          1      5500          5.375        1       1
        1          2      5750          5.438        1       1
        2          3      6000          5.500        1       1
        ...
        """
        df = self._read_to_dataframe("Vessels.txt")
        vessel_list = []
        vessels = {}
        
        for _, row in df.iterrows():
            vessel = VesselType(
                id = int(row["VesselID"]),
                capacity = int(row["Capacity"]),
                cost = float(row["OperatingCost"]),
                route_id = int(row["RouteID"]),
                max_num = int(row["maxNum"])
            )
            vessel_list.append(vessel)
            vessels[vessel.id] = vessel
            
        self.input_data.vessels = vessel_list
        self.input_data.vessel_type_set = vessels

    def _read_history_solution(self):
        """
        读取历史解决方案数据
        
        文件格式：
        RequestID VesselPathID Volume
        1 1 20
        1 2 10
        ...
        """
        if not DefaultSetting.USE_HISTORY_SOLUTION:
            return
            
        df = self._read_to_dataframe("HistorySolution.txt")
        history_solution = {}
        
        for _, row in df.iterrows():
            request_id = int(row[0])
            vessel_path_id = int(row[1])
            volume = int(row[2])
            
            if request_id not in history_solution:
                history_solution[request_id] = {}
            history_solution[request_id][vessel_path_id] = volume
            
        self.input_data.history_solution = history_solution

    def _read_sample_scenes(self):
        """
        读取样本场景数据
        
        文件格式：
        SceneID RequestID Demand
        1 1 25
        1 2 35
        ...
        """
        if not DefaultSetting.WHETHER_LOAD_SAMPLE_TESTS:
            return
            
        df = self._read_to_dataframe("SampleScenes.txt")
        sample_scenes = {}
        
        for _, row in df.iterrows():
            scene_id = int(row[0])
            request_id = int(row[1])
            demand = int(row[2])
            
            if scene_id not in sample_scenes:
                sample_scenes[scene_id] = {}
            sample_scenes[scene_id][request_id] = demand
            
        self.input_data.sample_scenes = sample_scenes 