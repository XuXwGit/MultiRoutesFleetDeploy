package multi;

import lombok.extern.slf4j.Slf4j;
import multi.network.*;

import java.io.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static java.lang.Integer.parseInt;

/**
* @Author: XuXw
* @Description: read input data from local files
* @DateTime: 2024/12/4 22:11
*/
@Slf4j
public class ReadData{
	private final InputData inputData;
	private final int timeHorizon;
	private final String filePath;
	public ReadData(String path, InputData inputdata, int timeHorizon) {
		super();
		this.filePath = DefaultSetting.RootPath + path;
		this.inputData = inputdata;
		this.timeHorizon = timeHorizon;
		frame();

		if(DefaultSetting.WhetherPrintDataStatus){
			inputdata.showStatus();
		}
	}

	private void frame()
	{
		log.info("========"+ "Start to read data" + "========");
		double start = System.currentTimeMillis();

		inputData.setTimeHorizon(timeHorizon);
		// 1. read shipping network data (include ports and ship routes)
		readPorts();
		readShipRoutes();

		// 2. read space-time data (include nodes, traveling arcs, transshipment arcs) generated based on the shipping network
		//  traveling arc, and transshipment arc are extended on arc
		readNodes();
		readTravelingArcs();
		readTransshipArcs();

		// 3. read container paths (include laden paths and empty paths) searched based on the shipping network
		// laden path and empty path both combined with container path
		readContainerPaths();
		readVesselPaths();
		readLadenPaths();
		readEmptyPaths();

		// 4. read vessel data (include vessel capacity, cost, route, max number)
		readVessels();

		// 5. read orders or requests
		readDemandRange();
		readRequests();

		// 6. read history solution and sample scenes
		if(DefaultSetting.UseHistorySolution) {
			readHistorySolution();
		}
		if(DefaultSetting.WhetherLoadSampleTests) {
			readSampleScenes();
		}

		double end = System.currentTimeMillis();
		log.info("========"+ "End read data" + "(" +String.format("%.2f", (end - start)) + "ms)"+ "========");
	}

	/**
	 * @Author Xu Xw
	 * @Description Read data from local file "filename", and return the data as a two-dimensional array
	 * @Date  2024/12/18 17:26
	 * @Param
	 * @return
	 **/
	String[][] read_to_string(String filename){
		ArrayList<String> temp = new ArrayList<>();
		int totalLine = 0;
		int columnNumber = 0;
		try {
			String encoding="GBK";
			File file=new File(filename);

			if(file.isFile() && file.exists())
			{
				log.info("Success to Read File: " + filename);

				InputStreamReader read = new InputStreamReader(new FileInputStream(file),encoding);
				BufferedReader bufferedReader = new BufferedReader(read);
				String line;
				boolean firstTime = true;
				while((line = bufferedReader.readLine()) != null)
				{
					String[] ss = line.split("\t");
					for (int j = 0; j < ss.length; j++)
					{
						temp.add(ss[j]);
					}
					if (firstTime)
					{
						columnNumber = line.split("\t").length;
						firstTime = false;
					}
					totalLine = totalLine + 1;
				}
				read.close();
			}
			else
			{
				log.info("Can not find the file: " + filename);
			}
		}
		catch (Exception e) {
			log.info("Error in read data");
			e.printStackTrace();
		}

		String[][] result = new String[totalLine][columnNumber];
		for (int i = 0; i < totalLine; i++)
		{
			for (int j = 0; j < columnNumber; j++)
			{
				result[i][j] = temp.get(i * columnNumber + j);
			}
		}

		return result;
	}

	/**
	 * @Author Xu Xw
	 * @Description Read OD range from the local  file
	 * 		The file format is as follows:
	 * 				OriginRegion	DestinationRegion	DemandLowerBound	DemandUpperBound	FreightLowerBound	FreightUpperBound
	 * 				1	2	20	40	2000	2500
	 * 				2	1	40	60	2000	2500
	 * 				...
	 * @Date  2024/12/18 17:25
	 * @Param
	 * @return
	 **/
	private void readDemandRange() {
		String[][] result = read_to_string(filePath + "DemandRange.txt");

		Map<String, ODRange> rangeMap = new HashMap<>();
		for (int i=1; i<result.length; i++)
		{
			ODRange ff=new ODRange(Integer.parseInt(result[i][0]),
					Integer.parseInt(result[i][1]),
					Integer.parseInt(result[i][2]),
					Integer.parseInt(result[i][3]),
					Integer.parseInt(result[i][4]),
					Integer.parseInt(result[i][5])
					);
			String key = result[i][0] + result[i][1];
			rangeMap.put(key, ff);
		}
		inputData.setGroupRangeMap(rangeMap);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the container paths from the local  file
	 * 		The file format is as follows:
	 * 					ContainerPath ID	OriginPort	OriginTime	DestinationPort	DestinationTime	PathTime	TransshipPort	TransshipTime	PortPath_length	PortPath	Arcs_length	Arcs_ID
	 * 					1	A	2	B	3	1	0	0	2	A,B	1	1
	 * 					2	A	9	B	10	1	0	0	2	A,B	1	9
	 * 					3	A	16	B	17	1	0	0	2	A,B	1	17
	 * 					...
	 * @Date  2024/12/18 17:24
	 * @Param
	 * @return
	 **/
	private void readContainerPaths()
	{
		String[][] result = read_to_string(filePath + "P-aths.txt");

		List<ContainerPath> containerPathList = new ArrayList<>();
		Map<Integer, ContainerPath> containerPaths =new HashMap<>();

		for (int i=1;i<result.length;i++)
		{
			ContainerPath ff=new ContainerPath();

			// output reference path

			// set the ContainerPath ID
			ff.setContainerPathID(Integer.parseInt(result[i][0]));

			// set origin port
			ff.setOriginPort((result[i][1]));

			// set origin time
			ff.setOriginTime(Integer.parseInt(result[i][2]));

			// set destination port
			ff.setDestinationPort(result[i][3]);

			// set destination time
			ff.setDestinationTime(Integer.parseInt(result[i][4]));

			// set path travel time
			ff.setPathTime(Integer.parseInt(result[i][5]));

			//set the transshipment port and transhipment time
			if("0".equals(result[i][6])&& "0".equals(result[i][7]))
			{
				ff.setTransshipmentPort(null);
				ff.setTransshipmentTime(null);
			}
			else
			{
				// transshipment port
				String[] trans_port = result[i][6].split(",");
				ff.setTransshipmentPort(trans_port);

				List<Port> transshipmentPorts = new ArrayList<>();
				for (int j = 0; j < trans_port.length; j++) {
					transshipmentPorts.add(inputData.getPortSet().get(trans_port[j]));
				}
				ff.setTransshipmentPorts(transshipmentPorts);

				//transshipment time
				String[] s_trans_time = result[i][7].split(",");
				int[] trans_time = new int[s_trans_time.length];
				for (int j = 0; j < s_trans_time.length; j++) {
					trans_time[j] = Integer.parseInt(s_trans_time[j]);
				}
				ff.setTransshipmentTime(trans_time);
			}

			// set the number of Ports in ContainerPath
			ff.setNumberOfPath(Integer.parseInt(result[i][8]));

			// set the Port ContainerPath sequence
			String[] port_path = result[i][9].split(",");
			ff.setPortPath(port_path);

			// set the Port Sequence in ContainerPath
			List<Port> portsInPath = new ArrayList<>();
			for (int j = 0; j < port_path.length; j++) {
				portsInPath.add(inputData.getPortSet().get(port_path[j]));
			}
			ff.setPortsInPath(portsInPath);

			//set the number of arcs
			int num_of_arcs = Integer.parseInt(result[i][10]);
			ff.setNumberOfArcs(num_of_arcs);

			// set the arcs sequence
			int[] arcIDs  =new int [num_of_arcs];
			String[] s_arcIDs = result[i][11].split(",");
			for (int j = 0; j < s_arcIDs.length; j++) {
				arcIDs[j] = Integer.parseInt(s_arcIDs[j]);
			}
			ff.setArcsID(arcIDs);

			// set the arcs sequence
			List<Arc> arcs = new ArrayList<>();
			for (int j = 0; j < arcIDs.length; j++) {
				arcs.add(inputData.getArcSet().get(arcIDs[j]));
			}
			ff.setArcs(arcs);

			// add the path to ContainerPath set
			if(ff.getDestinationTime()<=timeHorizon)
			{
				containerPathList.add(ff);
				containerPaths.put(ff.getContainerPathID(), ff);
			}
		}

		// set the ContainerPath set
		inputData.setContainerPaths(containerPathList);
		inputData.setContainerPathSet(containerPaths);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the ship routes from the local  file
	 * 		The file format is as follows:
	 * 				ShippingRouteID	NumberofPorts	Ports	NumberofCall	PortsofCall	Time
	 * 				1	7	A,B,C,D,E,F,G	8	A,B,C,D,E,F,G,A	2,3,4,10,12,14,17,23
	 * 				2	5	H,D,F,I,J	6	H,D,F,I,J,H	4,5,6,16,22,32
	 * 				...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readShipRoutes()
	{
		String[][] result = read_to_string(filePath + "Shipingroute.txt");

		Map<Integer, ShipRoute> shipRoutes = new HashMap<>();

		for (int i=1;i<result.length;i++)
		{
			ShipRoute ff=new ShipRoute();

			ff.setShipRouteID( Integer.parseInt(result[i][0]));
			ff.setNumberOfPorts( Integer.parseInt(result[i][1]));
			ff.setNumberOfCall( Integer.parseInt(result[i][3]));

			String[] route_ports = result[i][2].split(",");
			String[] port_calls = result[i][4].split(",");
			String[] S_time_calls = result[i][5].split(",");

			Map<Integer, Port> port_calls_map = new HashMap<>();

			int[] time_calls = new int[S_time_calls.length];
			for (int t = 0; t < S_time_calls.length; t++) {
				time_calls[t] = Integer.parseInt(S_time_calls[t]);
				port_calls_map.put(time_calls[t], inputData.getPortSet().get(port_calls[t]));
			}

			ff.setPorts(route_ports);
			ff.setPortsOfCall(port_calls);
			ff.setPortCalls(port_calls_map);
			ff.setTimePointsOfCall(time_calls);

			ff.setCycleTime(time_calls[S_time_calls.length-1] - time_calls[0]);
			ff.setNumRoundTrips((int) Math.ceil(ff.getCycleTime() / 7));

			// set after initialization vessel paths
			ff.setNumVesselPaths(0);

			shipRoutes.put(ff.getShipRouteID(), ff);
		}
		inputData.setShipRouteSet(shipRoutes);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the requests from the local  file
	 * 		The file format is as follows:
	 * 				RequestID	OriginPort	DestinationPort	W_i_Earlist	LatestDestinationTime	LadenPaths	NumberOfLadenPath	EmptyPaths	NumberOfEmptyPath
	 * 				1	BALBOA	BUSAN(KOREA)	1	58	0	0	0	0
	 *					2	BALBOA	BUSAN(KOREA)	8	65	0	0	0	0
	 * 				3	BALBOA	BUSAN(KOREA)	15	72	0	0	0	0
	 * 				4	BALBOA	BUSAN(KOREA)	22	79	0	0	0	0
	 *					5	BALBOA	BUSAN(KOREA)	29	86	16	1	0	0
	 * 				6	BALBOA	BUSAN(KOREA)	36	93	16,17,18,23	4	0	0
	 *					7	BALBOA	BUSAN(KOREA)	43	100	23,24,25,31	4	3709,3710,3721,3722,10965,15794,16874,21134,23390,23391,32217	11
	 *					...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readRequests()
	{
		String[][] result = read_to_string(filePath + "Requests.txt");

		List<Request> request=new ArrayList<>();

		for (int i=1;i<result.length;i++)
		{
			Request ff=new Request();

			// get Request ID...
			ff.setRequestID(Integer.parseInt(result[i][0]));
			ff.setOriginPort( (result[i][1]));
			ff.setDestinationPort( (result[i][2]));
			ff.setEarliestPickupTime(Integer.parseInt(result[i][3]));
			ff.setLatestDestinationTime(Integer.parseInt(result[i][4]));
			ff.setNumberOfLadenPath(Integer.parseInt(result[i][6]));
			ff.setNumberOfEmptyPath(Integer.parseInt(result[i][8]));

			// >=
			// >
			if(ff.getLatestDestinationTime() >= timeHorizon) {
				continue;
			}

			// get laden path IDs
			String[] s_laden_paths = result[i][5].split(",");
			int[] laden_paths = new int[s_laden_paths.length];
			int[] laden_path_indexes = new int[s_laden_paths.length];
			List<ContainerPath> ladenPathSet = new ArrayList<>();
			for (int j = 0; j < ff.getNumberOfLadenPath(); j++) {
				laden_paths[j] = Integer.parseInt(s_laden_paths[j]);
				ladenPathSet.add(inputData.getContainerPathSet().get(laden_paths[j]));

				if(ff.getNumberOfLadenPath() != 0)
				{
					int flag = 0;

					// get the path index according to path ID
					for (int k = 0; k < inputData.getContainerPaths().size(); k++) {
						if(laden_paths[j] == inputData.getContainerPaths().get(k).getContainerPathID())
						{
							laden_path_indexes[j] = k;
							flag = 1;
							break;
						}
					}

					if(flag == 0)
					{
						log.info("Error in finding laden path");
					}
				}
			}
			if(ff.getNumberOfLadenPath() != 0)
			{
				ff.setLadenPaths(laden_paths);
				ff.setLadenPathIndexes(laden_path_indexes);
				ff.setLadenPathSet(ladenPathSet);
			}
			else
			{
				ff.setLadenPaths(null);
				ff.setLadenPathIndexes(null);
				ff.setLadenPathSet(null);
			}

			// get empty path IDs
			String[] s_empty_paths = result[i][7].split(",");
			int[] empty_paths = new int[ff.getNumberOfEmptyPath()];
			int[] empty_path_indexes = new int[ff.getNumberOfEmptyPath()];
			List<ContainerPath> emptyPathSet = new ArrayList<>();
			for (int j = 0; j < ff.getNumberOfEmptyPath(); j++) {
				empty_paths[j] = Integer.parseInt(s_empty_paths[j]);
				emptyPathSet.add(inputData.getContainerPathSet().get(empty_paths[j]));
				if(empty_paths[0] != 0)
				{
					int flag = 0;
					// get the path index according to path ID
					for (int k = 0; k < inputData.getContainerPaths().size(); k++) {
						if(empty_paths[j] == inputData.getContainerPaths().get(k).getContainerPathID())
						{
							empty_path_indexes[j] = k;
							flag = 1;
							break;
						}
					}

					if(flag == 0)
					{
						log.info("Error in finding laden path");
					}
				}

			}
			ff.setEmptyPaths(empty_paths);
			ff.setEmptyPathIndexes(empty_path_indexes);
			ff.setEmptyPathSet(emptyPathSet);

			// set originGroup and destinationGroup
			int groupO = 0;
			int groupD = 0;
			for(Port pp:inputData.getPortSet().values())
			{
				if(pp.getPort().equals(ff.getOriginPort()))
				{
					groupO=pp.getGroup();
				}

				if(pp.getPort().equals(ff.getDestinationPort()))
				{
					groupD=pp.getGroup();
				}
			}
			ff.setOriginGroup(groupO);
			ff.setDestinationGroup(groupD);

			// add Request
			//! 2024/03/06 Note:
			//! Whether import request that origin and destination not within same region ?
			//! solution : not import
			if(ff.getLatestDestinationTime()<=timeHorizon
					&& ff.getNumberOfLadenPath() != 0){
				if(DefaultSetting.WhetherAllowSameRegionTrans || ff.getOriginGroup() != ff.getDestinationGroup()) {
					request.add(ff);
				}
			}
		}
		inputData.setRequestSet(request);
	}


	/**
	 * @Author Xu Xw
	 * @Description Read the vessels  from the local  file
	 * 		The file format is as follows:
	 * 				VesselID	Capacity	OperationCost	RouteID	MaxNum
	 * 				1	10642	14.69	1	1
	 * 				2	11388	14.877	1	1
	 *					3	15072	15.798	1	1
	 *					...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readVessels()
	{
		String filename = filePath;
		if("I".equals(DefaultSetting.VesselCapacityRange)){
			filename += "Vessels.txt";
		}else if("II".equals(DefaultSetting.VesselCapacityRange)) {
			filename += "Vessels-II.txt";
		}else if("III".equals(DefaultSetting.VesselCapacityRange)) {
			filename += "Vessels-III.txt";
		}

		String[][] result = read_to_string(filename);

		List <VesselType> vesselTypeSet =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			VesselType ff=new VesselType();

			ff.setId(Integer.parseInt(result[i][0]));
			ff.setCapacity(Integer.parseInt(result[i][1]));
			ff.setCost(Double.parseDouble(result[i][2]) * 1000000);
			ff.setRouteID(Integer.parseInt(result[i][3]));
			ff.setMaxNum(Integer.parseInt(result[i][4]));

			vesselTypeSet.add(ff);

			if (inputData.getShipRouteSet().get(ff.getRouteID()).getAvailableVessels() == null) {
				inputData.getShipRouteSet().get(ff.getRouteID()).setAvailableVessels(new HashMap<>());
			}
			inputData.getShipRouteSet().get(ff.getRouteID()).getAvailableVessels().put(ff.getId(), ff);
		}
		inputData.setVesselTypeSet(vesselTypeSet);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the ports from the local  file
	 * The Ports example:
	 * 	PortID	Port	WhetherTrans	Region	Group
	 * 	1				SINGAPORE	0				ASIA		1
	 * 	...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:55
	 * @Param
	 * @return
	 **/
	private void readPorts()
	{
		String[][] result = read_to_string(filePath + "Ports.txt");

		Map <String, Port> portSet = new HashMap<>();
		for (int i=1;i<result.length;i++)
		{
			Port ff=new Port();

			// set port
			ff.setId(Integer.parseInt(result[i][0]));
			ff.setPort(result[i][1]);
			ff.setWhetherTrans(Integer.parseInt(result[i][2]));
			ff.setRegion(result[i][3]);
			ff.setGroup(Integer.parseInt(result[i][4]));

			portSet.put(ff.getPort(), ff);
		}
		inputData.setPortSet(portSet);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the empty paths from the local  file
	 * 	The file format is as follows:
	 * 			RequestID	OriginPort	OriginTime	NumOfEmptyPath	PathIDs
	 * 			1	A	1	0	0
	 * 			2	A	8	0	0
	 *				3	A	15	0	0
	 * 			4	A	22	0	0
	 * 			5	A	29	13	425,426,911,912,1452,1453,1454,1898,2144,2354,2714,2715,2716
	 * 			...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readEmptyPaths()
	{
		String[][] result = read_to_string(filePath + "EmptyP-aths.txt");

		List<EmptyPath> emptyPaths=new ArrayList<>();

		for (int i=1;i<result.length;i++)
		{
			// set Request ID, 	Origin Port, 	Earliest Setup Time
			int requestID = Integer.parseInt(result[i][0]);
			String originPortString = result[i][1];
			Port originPort = inputData.getPortSet().get(originPortString);
			int originTime = Integer.parseInt(result[i][2]);
			int numOfEmptyPath = Integer.parseInt(result[i][3]);
			if(numOfEmptyPath == 0)
			{
				continue;
			}

			// get all Empty ContainerPath IDs
			String[] s_empty_paths = result[i][3].split(",");
			for (String s_empty_path : s_empty_paths) {
				EmptyPath ff = new EmptyPath();
				ff.setRequestID(requestID);
				ff.setOriginPortString(originPortString);
				ff.setOriginTime(originTime);
				ff.setOriginPort(originPort);
				ff.setPathID(Integer.parseInt(s_empty_path));

				// if the Request ID has laden path : add corresponding empty paths
				// otherwise : no need for empty path
				int index = 0;
				for (LadenPath ll : inputData.getLadenPathSet()) {
					if (ll.getRequestID() == ff.getRequestID()) {
						index = index + 1;
					}
				}

				if (index > 0) {
					emptyPaths.add(ff);
				}
			}
		}
		inputData.setEmptyPathSet(emptyPaths);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the laden paths from the local  file
	 * 		The file format is as follows:
	 * 				RequestID	OriginPort	OriginTime	DestinationPort	RoundTrip	W_i_Earlist	ArrivalTime_to_Destination	PathTime	TransshipPort	TransshipTime	Port_Path	PathID	ArcIDs
	 * 						1	A	2	B	1	1	3	1	0	0	1	A,B	1
	 * 						1	A	9	B	1	1	10	1	0	0	2	A,B	9
	 *							2	A	9	B	2	8	10	1	0	0	2	A,B	9
	 *							2	A	16	B	2	8	17	1	0	0	3	A,B	17
	 * 						3	A	16	B	3	15	17	1	0	0	3	A,B	17
	 * 						...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readLadenPaths()
	{
		String[][] result = read_to_string(filePath+"LadenP-aths.txt");

		List<LadenPath> ladenPaths=new ArrayList<>();

		for (int i=1;i<result.length;i++)
		{
			LadenPath ff=new LadenPath();

			ff.setRequestID(Integer.parseInt(result[i][0]));
			ff.setOriginPort((result[i][1]));
			ff.setOriginTime(Integer.parseInt(result[i][2]));
			ff.setDestinationPort(result[i][3]);
			ff.setRoundTrip(Integer.parseInt(result[i][4]));
			ff.setEarliestSetUpTime(Integer.parseInt(result[i][5]));
			ff.setArrivalTimeToDestination(Integer.parseInt(result[i][6]));
			ff.setPathTime(Integer.parseInt(result[i][7]));

			// get transship ports and transship time in path i
			// there is no transshipment in path i
			// default : no data format error
			if(result[i][8].equals("0") && result[i][9].equals("0"))
			{
				ff.setTransshipmentPort(null);
				ff.setTransshipmentPort(null);
			}
			// otherwise
			else
			{
				String[] transship_port = result[i][8].split(",");
				String[] s_transship_time = result[i][9].split(",");
				int[] transship_time = new int[s_transship_time.length];
				for (int j = 0; j < transship_port.length; j++) {
					transship_time[j] = Integer.parseInt(s_transship_time[j]);
				}
				ff.setTransshipmentPort(transship_port);
				ff.setTransshipmentTime(transship_time);
			}

			// get ContainerPath ID
			ff.setPathID(Integer.parseInt(result[i][10]));
			ff.setContainerPath(inputData.getContainerPathSet().get(ff.getPathID()));

			// get port path sequence
			String [] portPath = result[i][11].split(",");
			ff.setPortPath(portPath);

			// get port arcIDs sequence
			String[] s_arcIDs = result[i][12].split(",");
			int[] arcIDs = new int[s_arcIDs.length];
			List<Arc> arcs = new ArrayList<>();
			for (int j = 0; j < arcIDs.length; j++) {
				arcIDs[j] = Integer.parseInt(s_arcIDs[j]);
				arcs.add(inputData.getArcSet().get(arcIDs[j]));
			}
			ff.setArcsID(arcIDs);
			ff.setArcs(arcs);

			if(ff.getArrivalTimeToDestination()<timeHorizon)
			{
				ladenPaths.add(ff);
			}
		}
		inputData.setLadenPathSet(ladenPaths);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read the vessel paths from the local file: "VesselPaths.txt"
	 * 	Note: The String "path" in the file name is not available in the Linux system
	 * 	The file format is as follows:
	 * 		VesselPathID	VesselRouteID	NumOfArcs	ArcIDs	originTime	destinationTime
	 * 		1	1	14	1,2,3,4,5,6,7,8,9,10,11,12,13,14	3	87
	 * 		2	1	14	16,17,18,19,20,21,22,23,24,25,26,27,28,29	10	94
	 * 		...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readVesselPaths()
	{
		String[][] result = read_to_string(filePath+ "VesselP-aths.txt");

		List<VesselPath> vesselPath=new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			VesselPath ff=new VesselPath();

			// set vessel ContainerPath ID, Routes ID, Number of Arcs
			ff.setVesselPathID( Integer.parseInt(result[i][0]));
			ff.setRouteID(Integer.parseInt(result[i][1]));


			ff.setOriginTime(Integer.parseInt(result[i][4]));
			ff.setDestinationTime(Integer.parseInt(result[i][5]));
			ff.setPathTime(ff.getDestinationTime() - ff.getOriginTime());


			// set vesselPath ArcIDs and Arcs
			ff.setNumberOfArcs(Integer.parseInt(result[i][2]));
			int[] arcIDs =new int [ff.getNumberOfArcs()];
			String[] s_arcIDs = result[i][3].split(",");
			List<Arc> arcs = new ArrayList<>();
			for (int j = 0; j < s_arcIDs.length; j++) {
				arcIDs[j] = Integer.parseInt(s_arcIDs[j]);
				arcs.add(inputData.getArcSet().get(arcIDs[j]));
			}
			ff.setArcIDs(arcIDs);
			ff.setArcs(arcs);

			int index=0;
			for(TravelingArc tt:inputData.getTravelingArcSet())
			{
				if(tt.getTravelingArcID()==ff.getArcIDs()[ff.getNumberOfArcs()-1])
				{
					index=index+1;
				}
			}
			if(index>0)
			{
				vesselPath.add(ff);

				// update vessel paths in the route
				if(inputData.getShipRouteSet().get(ff.getRouteID()).getVesselPaths() == null)
				{
					inputData.getShipRouteSet().get(ff.getRouteID()).setVesselPaths(new ArrayList<>());
				}
				inputData.getShipRouteSet().get(ff.getRouteID()).setNumVesselPaths(inputData.getShipRouteSet().get(ff.getRouteID()).getNumVesselPaths()+1);
				inputData.getShipRouteSet().get(ff.getRouteID()).getVesselPaths().add(ff);
			}
		}
		inputData.setVesselPathSet(vesselPath);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read  transship arcs from the local  file: "TransshipArcs.txt"
	 * 	The file format is as follows:
	 * 		TransshipArc ID	Port	origin_node_ID	OriginTime	TransshipTime	Destination_node_ID	DestinationTime	FromRoute	ToRoute
	 * 		557	SHEKOU	2	7	3	225	10	1	2
	 * 		558	SHEKOU	2	7	10	241	17	1	2
	 * 		...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readTransshipArcs()
	{
		String[][] result = read_to_string(filePath +"TransshipArcs.txt");

		List<TransshipArc> transshipArcs =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			TransshipArc ff=new TransshipArc();
			ff.setArcID(Integer.parseInt(result[i][0]));
			ff.setTransshipArcID(Integer.parseInt(result[i][0]));

			ff.setPort((result[i][1]));

			ff.setOriginNodeID(Integer.parseInt(result[i][2]));
			ff.setOriginTime(Integer.parseInt(result[i][3]));
			ff.setOriginNode(inputData.getNodeSet().get(ff.getOriginNodeID()));

			ff.setTransshipTime(Integer.parseInt(result[i][4]));

			ff.setDestinationNodeID(Integer.parseInt(result[i][5]));
			ff.setDestinationTime(Integer.parseInt(result[i][6]));
			ff.setDestinationNode(inputData.getNodeSet().get(ff.getDestinationNodeID()));

			ff.setFromRoute(Integer.parseInt(result[i][7]));
			ff.setToRoute(Integer.parseInt(result[i][8]));

			if(ff.getDestinationTime()<timeHorizon)
			{
				transshipArcs.add(ff);

				if(inputData.getArcSet() == null){
					inputData.setArcSet(new HashMap<>());
				}
				inputData.getArcSet().putIfAbsent(ff.getArcID(), ff);
			}

		}
		inputData.setTransshipArcSet(transshipArcs);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read  traveling arcs from the local file: "TravelingArcs.txt"
	 * 	The file format is as follows:
	 * 			TravelingArc_ID	Route	Origin_node_ID	Origin_Call	Origin_Port	Round_Trip	OriginTime	TravelingTime	Destination_node_ID	Destination_Call	Destination_Port	DestinationTime
	 * 			1	1	1	1	A	1	2	1	2	2	B	3
	 *				2	1	2	2	B	1	3	1	3	3	C	4
	 * 			3	1	3	3	C	1	4	6	4	4	D	10
	 * 			...
	 * @version: v0.1.0
	 * @Date  2024/12/18 15:16
	 * @Param None
	 * @return None
	 **/
	private void readTravelingArcs()
	{
		String[][] result = read_to_string(filePath +"TravelingArcs.txt");

		List<TravelingArc> travelingArcs =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			TravelingArc ff=new TravelingArc();

			ff.setArcID(Integer.parseInt(result[i][0]));
			ff.setTravelingArcID(Integer.parseInt(result[i][0]));

			ff.setRouteID(Integer.parseInt(result[i][1]));

			// origin node
			ff.setOriginNodeID(Integer.parseInt(result[i][2]));
			ff.setOriginCall(Integer.parseInt(result[i][3]));
			ff.setOriginPort((result[i][4]));
			ff.setOriginTime(Integer.parseInt(result[i][6]));
			ff.setOriginNode(inputData.getNodeSet().get(ff.getOriginNodeID()));

			ff.setTravelingTime(Integer.parseInt(result[i][7]));

			// destination node
			ff.setDestinationNodeID(Integer.parseInt(result[i][8]));
			ff.setDestinationCall(Integer.parseInt(result[i][9]));
			ff.setDestinationPort((result[i][10]));
			ff.setDestinationTime(Integer.parseInt(result[i][11]));
			ff.setDestinationNode(inputData.getNodeSet().get(ff.getDestinationNodeID()));

			//The front input data about round_trip is error
			ShipRoute r = inputData.getShipRouteSet().get(ff.getRouteID());
			int index = r.getCallIndexOfPort(ff.getOriginPort());
			int round_trip = (ff.getOriginTime() - r.getTimePointsOfCall()[index])/7 + 1;
			ff.setRoundTrip(round_trip);

			if(r.getTimePointsOfCall()[r.getNumberOfCall() - 1] + 7 * ( ff.getRoundTrip() - 1)
					<= timeHorizon)
			{
				travelingArcs.add(ff);
				if(inputData.getArcSet() == null){
					inputData.setArcSet(new HashMap<>());
				}
				inputData.getArcSet().putIfAbsent(ff.getArcID(), ff);
			}
		}
		inputData.setTravelingArcSet(travelingArcs);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read Nodes from the local file : "Nodes.txt"
	 * 			The file format is as follows:
	 * 					ID	Route	Call	Port	Round_trip	Time
	 * 					1	1	1	A	1	2
	 * 					2	1	2	B	1	3
	 * 					3	1	3	C	1	4
	 *						4	1	4	D	1	10
	 *						...
	 * @Date  2024/12/18 17:27
	 * @Param
	 * @return
	 **/
	private void readNodes()
	{
		String[][] result = read_to_string(filePath +"Nodes.txt");

		Map<Integer, Node> nodeMap =new HashMap<>();

		/**	example:
		 * 		ID	Route	Call	Port	Round_trip	Time
		 * 		1		1			1		D5		1						4
		 */
		Map<String, Integer> mapToIndex = new HashMap<>();
		for (int i = 0; i < result[0].length; i++) {
			mapToIndex.put(result[0][i], i);
		}
		for (int i=1;i<result.length;i++)
		{
			Node ff=new Node();
			ff.setNodeID(parseInt(result[i][mapToIndex.get("ID")].trim()));
			ff.setRoute(parseInt(result[i][mapToIndex.get("Route")].trim()));
			ff.setCall(parseInt(result[i][mapToIndex.get("Call")].trim()));
			ff.setPortString(result[i][mapToIndex.get("Port")].trim());
			ff.setPort(inputData.getPortSet().get(ff.getPortString()));
			ff.setRoundTrip(parseInt(result[i][mapToIndex.get("Round_trip")].trim()));
			ff.setTime(parseInt(result[i][mapToIndex.get("Time")].trim()));
			if(ff.getTime()<timeHorizon){
				nodeMap.put(ff.getNodeID(), ff);
			}
		}
		inputData.setNodeSet(nodeMap);
	}
	private void readHistorySolution()
	{
		String[][] result = read_to_string(DefaultSetting.RootPath + DefaultSetting.SolutionPath +"AlgoSolutions"
				+ "-R" + inputData.getShipRouteSet().size() + ".txt");

		// get the history solution
		/* eg:
			Algo	Route	T	Fleet	Seed	Solution
			BD	8	90	Homo	100	1,10,13,18,23,28,31,40*/
		Map<String, int[]> historySolution = new HashMap<>();
		for (int i=1;i<result.length;i++)
		{
			// Algo + "-R"+ in.getShipRouteSet().size()
			// + "-T" + p.getTimeHorizon()
			// + "-"+ FleetType
			// + "-S" + randomSeed
			// + "-V" + VesselCapacityRange;
			String key = result[i][0]
					+ "-R" + result[i][1]
					+ "-T" + result[i][2]
					+ "-" + result[i][3]
					+ "-S" + result[i][4]
					+ "-V" + result[i][5]
					;
			String[] s_solution = result[i][6].split(",");
			int[] solution = new int[s_solution.length];
			for (int j = 0; j < s_solution.length; j++) {
				solution[j] = Integer.parseInt(s_solution[j]);
			}
			historySolution.put(key, solution);
		}

		inputData.setHistorySolutionSet(historySolution);
	}

	/**
	 * @Author Xu Xw
	 * @Description Read Sample Data from local backup
	 * 		The file format is as follows:
	 * 				0	18,29,32,37,38,53,102,130,160,171,204,211,218,227,296,301,319,320,
	 * 				1	56,59,67,71,144,177,183,187,225,227,246,248,250,269,287,322,336,343,
	 * @Date  2024/12/18 17:36
	 * @Param
	 * @return
	 **/
	private void readSampleScenes(){
		int tau = (int) Math.sqrt(inputData.getRequestSet().size());
		String samplefilename = "R"+ inputData.getShipRouteSet().size() + "-T"
				+ inputData.getTimeHorizon() + "-Tau"+ tau + "-S" + DefaultSetting.randomSeed + "-SampleTestSet"+ ".txt";
		String[][] result = read_to_string(filePath +samplefilename);
		double[][] sampleScenes = new double[DefaultSetting.numSampleScenes][inputData.getRequestSet().size()];

		for(int i=0;i<DefaultSetting.numSampleScenes;i++) {
			String[] s_solution = result[i][1].split(",");
			int[] solution = new int[s_solution.length];
			for (int j = 0; j < s_solution.length; j++) {
				solution[j] = Integer.parseInt(s_solution[j]);
				sampleScenes[i][solution[j]] = 1;
			}
		}
		inputData.setSampleScenes(sampleScenes);
	}
}
