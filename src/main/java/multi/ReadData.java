package multi;

import java.io.*;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static java.lang.Integer.parseInt;

public class ReadData extends DefaultSetting {
	private final InputData inputdata;
	private final int timeHorizon;
	private final String filePath;
	public ReadData(String path, InputData inputdata, int timeHorizon) {
		super();
		this.filePath = RootPath + path;
		this.inputdata = inputdata;
		this.timeHorizon = timeHorizon;
		frame();

		if(WhetherPrintDataStatus){
			inputdata.showStatus();
		}
	}

	private void frame()
	{
		System.out.println("========"+ "Start to read data" + "========");
		double start = System.currentTimeMillis();

		inputdata.setTimeHorizon(timeHorizon);
		readShipRoutes();
		readNodes();
		readTravelingArcs();
		readTransshipArcs();
		readPaths();
		readVesselPaths();
//		readLadenPaths();
//		readEmptyPaths();
		readPorts();
		readVessels();
		readRequests();
		readDemandRange();
		if(UseHistorySolution)
			readHistorySolution();
		if(WhetherLoadSampleTests)
			readSampleScenes();

		double end = System.currentTimeMillis();
		System.out.println("========"+ "End read data" + "(" +String.format("%.2f", (end - start)) + "ms)"+ "========");
	}

	String[][] read_to_string(String filename){
		ArrayList<String> temp = new ArrayList<>();
		int totalLine = 0;
		int columnNumber = 0;
		try {
			String encoding="GBK";
			File file=new File(filename);

			if(file.isFile() && file.exists())
			{
				if(WhetherPrintFileLog){
					System.out.println("Success to Read File: " + filename);
				}

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
				System.out.println("Can not find the file: " + filename);
			}
		}
		catch (Exception e) {
			System.out.println("Error in read data");
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
		inputdata.setGroupRangeMap(rangeMap);
	}
	private void readPaths()
	{
		String[][] result = read_to_string(filePath + "P-aths.txt");

		List<ContainerPath> ContainerPath =new ArrayList<>();

		//for (int j = 0; j < result[0].length; j++) {
		//System.out.print(result[0][j]+"\t");
		//}
		//System.out.println();

		for (int i=1;i<result.length;i++)
		{
			ContainerPath ff=new ContainerPath();

			// output reference path
			//for (int j = 0; j < result[i].length; j++) {
			// System.out.print(result[i][j]+"\t");
			//}
			//System.out.println();

			// set the ContainerPath ID
			//System.out.print(result[i][0] + "\t");
			ff.setContainerPathID(Integer.parseInt(result[i][0]));

			// set origin port
			//System.out.print(result[i][1] + "\t");
			ff.setOriginPort((result[i][1]));

			// set origin time
			//System.out.print(result[i][2] + "\t");
			ff.setOriginTime(Integer.parseInt(result[i][2]));

			// set destination port
			//System.out.print(result[i][3] + "\t");
			ff.setDestinationPort(result[i][3]);

			// set destination time
			//System.out.print(result[i][4] + "\t");
			ff.setDestinationTime(Integer.parseInt(result[i][4]));

			// set path travel time
			//System.out.print(result[i][5] + "\t");
			ff.setPathTime(Integer.parseInt(result[i][5]));

			//set the transshipment port and transhipment time
			if(result[i][6].equals("0")&& result[i][7].equals("0"))
			{
				ff.setTransshipment_port(null);
				ff.setTransshipment_Time(null);
			}
			else
			{
				// transshipment port
				String[] trans_port = result[i][6].split(",");
				ff.setTransshipment_port(trans_port);

				//transshipment time
				String[] s_trans_time = result[i][7].split(",");
				int[] trans_time = new int[s_trans_time.length];
				for (int j = 0; j < s_trans_time.length; j++) {
					trans_time[j] = Integer.parseInt(s_trans_time[j]);
				}
				ff.setTransshipment_Time(trans_time);
			}

			// set the number of Ports in ContainerPath
			ff.setNumberofPath( Integer.parseInt(result[i][8]));
			//System.out.print(ff.getNumberofPath() + "\t");

			// set the Port ContainerPath sequence
			String[] port_path = result[i][9].split(",");
			ff.setPortPath(port_path);

			//set the number of arcs
			int num_of_arcs = Integer.parseInt(result[i][10]);
			ff.setNumberOfArcs(num_of_arcs);
			//System.out.print(ff.getNumberOfArcs() + "\t");

			// set the arcs sequence
			int[] arcIDs  =new int [num_of_arcs];
			String[] s_arcIDs = result[i][11].split(",");
			for (int j = 0; j < s_arcIDs.length; j++) {
				arcIDs[j] = Integer.parseInt(s_arcIDs[j]);
			}
			ff.setArcsID(arcIDs);

			// add the path to ContainerPath set
			if(ff.getDestinationTime()<=timeHorizon)
			{
				ContainerPath.add(ff);
			}
		}

		// set the ContainerPath set
		inputdata.setContainerPathSet(ContainerPath);
	}
	private void readShipRoutes()
	{
		String[][] result = read_to_string(filePath + "Shipingroute.txt");

		List<ShipRoute> request=new ArrayList<>();

		for (int i=1;i<result.length;i++)
		{
			ShipRoute ff=new ShipRoute();

			ff.setShippingRouteID( Integer.parseInt(result[i][0]));
			ff.setNumberofPorts( Integer.parseInt(result[i][1]));
			ff.setNumberofCall( Integer.parseInt(result[i][3]));

			String[] route_ports = result[i][2].split(",");
			String[] port_calls = result[i][4].split(",");
			String[] S_time_calls = result[i][5].split(",");

			int[] time_calls = new int[S_time_calls.length];
			for (int t = 0; t < S_time_calls.length; t++) {
				time_calls[t] = Integer.parseInt(S_time_calls[t]);
			}

			ff.setPorts(route_ports);
			ff.setPortsofCall(port_calls);
			ff.setTimePointsOfCall(time_calls);

			ff.setCycleTime(time_calls[S_time_calls.length-1] - time_calls[0]);
			ff.setNumRoundTrips((int) Math.ceil(ff.getCycleTime() / 7));

			ff.setNumVesselPaths(0);

			request.add(ff);
		}
		inputdata.setShipRoute(request);
	}
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
			ff.setW_i_Earliest(Integer.parseInt(result[i][3]));
			ff.setLatestDestinationTime(Integer.parseInt(result[i][4]));
			ff.setNumberOfLadenPath(Integer.parseInt(result[i][6]));
			ff.setNumberOfEmptyPath(Integer.parseInt(result[i][8]));

			// >=
			// >
			if(ff.getLatestDestinationTime() >= timeHorizon)
				continue;

			// get laden path IDs
			String[] s_laden_paths = result[i][5].split(",");
			int[] laden_paths = new int[s_laden_paths.length];
			int[] laden_path_indexes = new int[s_laden_paths.length];
			for (int j = 0; j < ff.getNumberOfLadenPath(); j++) {
				laden_paths[j] = Integer.parseInt(s_laden_paths[j]);

				if(ff.getNumberOfLadenPath() != 0)
				{
					int flag = 0;
					// get the path index according to path ID
					for (int k = 0; k < inputdata.getContainerPathSet().size(); k++) {
						if(laden_paths[j] == inputdata.getContainerPathSet().get(k).getContainerPathID())
						{
							laden_path_indexes[j] = k;
							flag = 1;
							break;
						}
					}

					if(flag == 0)
					{
						System.out.println("Error in finding laden path");
					}
				}
			}
			if(ff.getNumberOfLadenPath() != 0)
			{
				ff.setLadenPaths(laden_paths);
				ff.setLadenPathIndexes(laden_path_indexes);
			}
			else
			{
				ff.setLadenPaths(null);
				ff.setLadenPathIndexes(null);
			}


			// get empty path IDs
			String[] s_empty_paths = result[i][7].split(",");
			int[] empty_paths = new int[ff.getNumberOfEmptyPath()];
			int[] empty_path_indexes = new int[ff.getNumberOfEmptyPath()];
			for (int j = 0; j < ff.getNumberOfEmptyPath(); j++) {
				empty_paths[j] = Integer.parseInt(s_empty_paths[j]);

				if(empty_paths[0] != 0)
				{
					int flag = 0;
					// get the path index according to path ID
					for (int k = 0; k < inputdata.getContainerPathSet().size(); k++) {
						if(empty_paths[j] == inputdata.getContainerPathSet().get(k).getContainerPathID())
						{
							empty_path_indexes[j] = k;
							flag = 1;
							break;
						}
					}

					if(flag == 0)
					{
						System.out.println("Error in finding laden path");
					}
				}

			}
			ff.setEmptyPaths(empty_paths);
			ff.setEmptyPathIndexes(empty_path_indexes);

			// set originGroup and destinationGroup
			int groupO = 0;
			int groupD = 0;
			for(Port pp:inputdata.getPortSet())
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
				if(WhetherAllowSameRegionTrans || ff.getOriginGroup() != ff.getDestinationGroup())
					request.add(ff);
			}

		}
		inputdata.setRequestSet(request);
	}
	private void readVessels()
	{
		String filename = filePath;
		if(VesselCapacityRange.equals("I")){
			filename += "Vessels.txt";
		}else if(VesselCapacityRange.equals("II")) {
			filename += "Vessels-II.txt";
		}else if(VesselCapacityRange.equals("III")) {
			filename += "Vessels-III.txt";
		}

		String[][] result = read_to_string(filename);

		List <Vessel> VesselSet =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			Vessel ff=new Vessel();

			ff.setId(Integer.parseInt(result[i][0]));
			ff.setCapacity(Integer.parseInt(result[i][1]));
			ff.setCost(Double.parseDouble(result[i][2]) * 1000000);
			ff.setRoute(Integer.parseInt(result[i][3]));
			ff.setMax_num(Integer.parseInt(result[i][4]));
			VesselSet.add(ff);
		}
		inputdata.setVesselSet(VesselSet);
	}

	/*
	PortID	Port	WhetherTrans	Region	Group
	1	SINGAPORE	0	ASIA	1
	...
	* */
	private void readPorts()
	{
		String[][] result = read_to_string(filePath + "Ports.txt");

		List <Port> port =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			Port ff=new Port();

			// set port
			ff.setId(Integer.parseInt(result[i][0]));
			ff.setPort(result[i][1]);
			ff.setWhetherTrans(Integer.parseInt(result[i][2]));
			ff.setRegion(result[i][3]);
			ff.setGroup(Integer.parseInt(result[i][4]));

			port.add(ff);
		}
		inputdata.setPortSet(port);
	}

	private void readEmptyPaths()
	{
		String[][] result = read_to_string(filePath + "EmptyP-aths.txt");

		List<EmptyPath> emptyPaths=new ArrayList<>();

		for (int i=1;i<result.length;i++)
		{
			EmptyPath ff=new EmptyPath();

			// set Request ID, 	Origin Port, 	Earliest Setup Time
			ff.setRequestID(Integer.parseInt(result[i][0]));
			ff.setOriginPort((result[i][1]));
			ff.setOriginTime(Integer.parseInt(result[i][2]));
//        	System.out.print(ff.getRequest_ID()+"\t");
//        	System.out.print(ff.getOrigin_Port()+"\t");
//        	System.out.print(ff.getOrigin_time()+"\t");

			// get all Empty ContainerPath IDs
			String[] s_empty_paths = result[i][3].split(",");
			int[] empty_paths  =new int [s_empty_paths.length];
			for(int k=0;k<s_empty_paths.length;k++)
			{
				empty_paths[k] = Integer.parseInt(s_empty_paths[k]);
			}
			ff.setPathID(empty_paths);

			// if the Request ID has laden path : add corresponding empty paths
			// otherwise : no need for empty path
			int index=0;
			for(LadenPath ll :inputdata.getLadenPathSet())
			{
				if(ll.getRequest_ID()==ff.getRequestID())
				{
					index=index+1;
				}
			}
//        	 System.out.print(index + "\t");

			if(index>0)
			{
				emptyPaths.add(ff);

//        		 System.out.print("Y");
			}
//        	 System.out.println();

		}
		inputdata.setEmptyPathSet(emptyPaths);

	}

	private void readLadenPaths()
	{
		String[][] result = read_to_string(filePath+"LadenP-aths.txt");

		List<LadenPath> ladenPath=new ArrayList<>();

		for (int i=1;i<result.length;i++)
		{
			LadenPath ff=new LadenPath();

			//get Request ID, origin Port, Origin Time, Rotation, W_i_Earliest, Destination Time , travel Time
			ff.setRequest_ID(Integer.parseInt(result[i][0]));
			ff.setOrigin_Port((result[i][1]));
			ff.setOrigin_Time(Integer.parseInt(result[i][2]));
			ff.setDestination_Port(result[i][3]);
			ff.setRound_trip(Integer.parseInt(result[i][4]));
			ff.setW_i_Earlist(Integer.parseInt(result[i][5]));
			ff.setArrival_Time_to_destination(Integer.parseInt(result[i][6]));
			ff.setPathtime(Integer.parseInt(result[i][7]));

			// get transship ports and transship time in path i
			// there is no transshipment in path i
			// default : no data format error
			if(result[i][8].equals("0") && result[i][9].equals("0"))
			{
				ff.setTransshipment_port(null);
				ff.setTransshipment_port(null);
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
				ff.setTransshipment_port(transship_port);
				ff.setTransshipment_Time(transship_time);
			}

			// get ContainerPath ID
			ff.setPath_ID(Integer.parseInt(result[i][10]));

			// get port path sequence
			String [] portPath = result[i][11].split(",");
			ff.setPort_Path(portPath);

			// get port arcIDs sequence
			String[] s_arcIDs = result[i][12].split(",");
			int[] arcIDs = new int[s_arcIDs.length];
			for (int j = 0; j < arcIDs.length; j++) {
				arcIDs[j] = Integer.parseInt(s_arcIDs[j]);
			}
			ff.setArcs_ID(arcIDs);

			if(ff.getArrival_Time_to_destination()<timeHorizon)
			{
				ladenPath.add(ff);
			}
		}
		inputdata.setLadenPathSet(ladenPath);
	}
	private void readVesselPaths()
	{
		String[][] result = read_to_string(filePath+ "VesselP-aths.txt");

		List<VesselPath> vesselPath=new ArrayList<>();
		List<ShipRoute> shipRouteSet = inputdata.getShipRouteSet();
		for (int i=1;i<result.length;i++)
		{
			VesselPath ff=new VesselPath();

			// set vessel ContainerPath ID, Routes ID, Number of Arcs
			ff.setVesselPathID( Integer.parseInt(result[i][0]));
			ff.setRouteID(Integer.parseInt(result[i][1]));
			ff.setNumberofArcs(Integer.parseInt(result[i][2]));
			ff.setOriginTime(Integer.parseInt(result[i][4]));
			ff.setDestinationTime(Integer.parseInt(result[i][5]));
			ff.setPathTime(ff.getDestinationTime() - ff.getOriginTime());

			// set vesselPath ArcIDs
			int[] arcIDs =new int [ff.getNumberofArcs()];
			String[] s_arcIDs = result[i][3].split(",");
			for (int j = 0; j < s_arcIDs.length; j++) {
				arcIDs[j] = Integer.parseInt(s_arcIDs[j]);
			}
			ff.setArcID(arcIDs);

			int index=0;
			for(TravelingArc tt:inputdata.getTravelingArcSet())
			{
				if(tt.getTravelingArc_ID()==ff.getPathArcIDs()[ff.getNumberofArcs()-1])
				{
					index=index+1;
				}
			}
			if(index>0)
			{
				vesselPath.add(ff);
				shipRouteSet.get(ff.getRouteID()-1).setNumVesselPaths(shipRouteSet.get(ff.getRouteID()-1).getNumVesselPaths()+1);
			}
		}
		inputdata.setVesselPathSet(vesselPath);
		inputdata.setShipRoute(shipRouteSet);
	}
	private void readTransshipArcs()
	{
		String[][] result = read_to_string(filePath +"TransshipArcs.txt");

		List<TransshipArc> transshipArcs =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			TransshipArc ff=new TransshipArc();
			ff.setTransshipArc_ID(Integer.parseInt(result[i][0]));
			ff.setPort((result[i][1]));
			ff.setOriginNodeID(Integer.parseInt(result[i][2]));
			ff.setOriginTime(Integer.parseInt(result[i][3]));
			ff.setTransshipTime(Integer.parseInt(result[i][4]));
			ff.setDestination_node_ID(Integer.parseInt(result[i][5]));
			ff.setDestinationTime(Integer.parseInt(result[i][6]));
			ff.setFromRoute(Integer.parseInt(result[i][7]));
			ff.setToRoute(Integer.parseInt(result[i][8]));

			if(ff.getDestinationTime()<timeHorizon)
			{
				transshipArcs.add(ff);
			}

		}
		inputdata.setTransshipArcSet(transshipArcs);
	}
	private void readTravelingArcs()
	{
		String[][] result = read_to_string(filePath +"TravelingArcs.txt");

		List<TravelingArc> travelingArcs =new ArrayList<>();
		for (int i=1;i<result.length;i++)
		{
			TravelingArc ff=new TravelingArc();

			ff.setTravelingArc_ID(Integer.parseInt(result[i][0]));
			ff.setRoute(Integer.parseInt(result[i][1]));
			ff.setOrigin_node_ID(Integer.parseInt(result[i][2]));
			ff.setOrigin_Call(Integer.parseInt(result[i][3]));
			ff.setOrigin_Port((result[i][4]));
			ff.setOriginTime(Integer.parseInt(result[i][6]));
			ff.setTravelingTime(Integer.parseInt(result[i][7]));
			ff.setDestination_node_ID(Integer.parseInt(result[i][8]));
			ff.setDestination_Call(Integer.parseInt(result[i][9]));
			ff.setDestination_Port((result[i][10]));
			ff.setDestinationTime(Integer.parseInt(result[i][11]));
			//        	ff.setRound_Trip(Integer.parseInt(result[i][5]));
			//The front input data about round_trip is error
			ShipRoute r = inputdata.getShipRouteSet().get(ff.getRouteIndex());
			int index = r.getCallIndexOfPort(ff.getOriginPort());
			int round_trip = (ff.getOriginTime() - r.getTimePointsOfCall()[index])/7 + 1;
			ff.setRound_Trip(round_trip);

			if(r.getTimePointsOfCall()[r.getNumberofCall() - 1] + 7 * ( ff.getRound_Trip() - 1)
					<= timeHorizon)
			{
				travelingArcs.add(ff);
			}
		}
		inputdata.setTravelingArcSet(travelingArcs);
	}
	private void readNodes()
	{
		String[][] result = read_to_string(filePath +"Nodes.txt");

		List<Node> node =new ArrayList<>();

		/*System.out.println(result[0]);*/
		for (int i=1;i<result.length;i++)
		{
			Node ff=new Node();
			ff.setNodeID(parseInt(result[i][0].trim()));
			ff.setRoute(parseInt(result[i][1].trim()));
			ff.setCall(parseInt(result[i][2].trim()));
			ff.setRound_trip(parseInt(result[i][4].trim()));
			ff.setTime(parseInt(result[i][5].trim()));
			ff.setPort(result[i][3].trim());
			if(ff.getTime()<timeHorizon){
				node.add(ff);
			}
		}
		inputdata.setNodeSet(node);
	}
	private void readHistorySolution()
	{
		String[][] result = read_to_string(RootPath + SolutionPath +"AlgoSolutions"
				+ "-R" + inputdata.getShipRouteSet().size() + ".txt");

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

		inputdata.setHistorySolutionSet(historySolution);
	}
	private void readSampleScenes(){
		int tau = (int) Math.sqrt(inputdata.getRequestSet().size());
		String samplefilename = "R"+ inputdata.getShipRouteSet().size() + "-T"
				+ inputdata.getTimeHorizon() + "-Tau"+ tau + "-S" + randomSeed + "-SampleTestSet"+ ".txt";
		String[][] result = read_to_string(filePath +samplefilename);
		double[][] sampleScenes = new double[numSampleScenes][inputdata.getRequestSet().size()];

		for(int i=0;i<numSampleScenes;i++) {
			String[] s_solution = result[i][1].split(",");
			int[] solution = new int[s_solution.length];
			for (int j = 0; j < s_solution.length; j++) {
				solution[j] = Integer.parseInt(s_solution[j]);
				sampleScenes[i][solution[j]] = 1;
			}
		}
		inputdata.setSampleScenes(sampleScenes);
	}
}
