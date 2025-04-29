package multi;

import lombok.extern.slf4j.Slf4j;
import multi.network.*;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class GenerateParameter extends DefaultSetting {
	private Parameter p;
	private InputData in;
	private int timeHorizon;
	private double uncertainDegree = defaultUncertainDegree;

	public GenerateParameter(Parameter p, InputData in, int timeHorizon, double uncertainDegree) throws IOException {
		super();
		this.p = p;
		this.in = in;
		this.timeHorizon=timeHorizon;
		this.uncertainDegree=uncertainDegree;
		random.setSeed(randomSeed);
		frame();
	}

	private void frame() throws IOException {
		log.info("========"+ "Start to Generate parameters" + "========");
		double start = System.currentTimeMillis();

		p.setTimeHorizon(timeHorizon);
		p.setTau((int) (Math.sqrt(in.getRequestSet().size()) * budgetCoefficient));
		p.setUncertainDegree(uncertainDegree);
		in.setUncertainDegree(uncertainDegree);

		SetArcSet();

		SetTimePoint();

		// set cost for ports
		SetPorts();

		// set Request (normal/variation demand and penalty cost  for each od pairs)
		SetRequests();

		SetShipRoutes();

		SetVessels();

		SetVesselPaths();

		SetContainerPaths();

		SetArcCapacity();

		SetInitialEmptyContainers();

		if(WhetherGenerateSamples){
			GenerateRandomSampleSceneSet();
		}
		if(WhetherLoadSampleTests){
			p.setSampleScenes(in.getSampleScenes());
		}

		double end = System.currentTimeMillis();
		log.info("========"+ "End Generate parameters" + "(" +String.format("%.2f", (end - start)) + "ms)"+ "========");
	}

	public static double getRandDouble()
	{
		double mean = 0.5;
		double variance = 1.0/12.0;
		if("Uniform".equals(distributionType)) {
			return random.nextDouble();
		} else if("Normal".equals(distributionType)) {
			return random.nextGaussian();
		} else if("Log-Normal".equals(distributionType)){
			// Log-Normal distribution :
			// mean = exp(mu + sigma^2/2)
			// variance = (exp(sigma^2) - 1) * exp(2 * mu + sigma^2)
			double sigma = Math.sqrt(Math.log(1 + variance)) * log_normal_sigma_factor;
			double mu = Math.log(mean) - 0.5 * sigma * sigma;
			// 返回服从Log-normal分布的近似随机数：standard normal --> log-normal
			// z ~ N(0,1) --> X = exp(mu + sigma * z)
			return Math.exp(mu + sigma * random.nextGaussian());
		}
		else {
			return random.nextDouble();
		}
	}

	private void SetArcSet(){
		// set travel arc IDs set
		int [] travellingArcsSet =new int[in.getTravelingArcSet().size()];
		int x=0;
		for(TravelingArc tt:in.getTravelingArcSet())
		{
			travellingArcsSet[x]=tt.getTravelingArcID();
			x=x+1;
		}
		p.setTravelingArcsSet(travellingArcsSet);

		// set transship arc IDs set
		int [] transhipmentArcsSet =new int [in.getTransshipArcSet().size()];
		x=0;
		for(TransshipArc tt: in.getTransshipArcSet())
		{
			transhipmentArcsSet[x]=tt.getTransshipArcID();
			x=x+1;
		}
		p.setTranshipmentArcsSet(transhipmentArcsSet);
	}
	private void SetTimePoint(){
		// set time point set = {0, 1, 2, ..., T}
		int [] timePointSet =new int [timeHorizon+1];
		for(int i=0;i<timeHorizon+1;i++)
		{
			timePointSet[i]=i;
		}
		p.setTimeHorizon(timeHorizon);
		p.setTimePointSet(timePointSet);
	}
	private void SetPorts(){
		// set rentalCost
		// set turnover time (sp)
		// and the demurrage cost of unit laden/empty cost
		// for each port
		// sp = 14
		// unit laden demurrage = 175
		// unit empty demurrage = 100
		// set rental cost of one container per unit time
		p.setRentalCost(DefaultUnitRentalCost);
		String [] portSet =new String [in.getPortSet().size()];
		int [] turnOverTime =new int [in.getPortSet().size()];
		double [] ladenDemurrageCost =new double[in.getPortSet().size()];
		double [] emptyDemurrageCost=new double[in.getPortSet().size()];
		int x=0;
		for(Port pp :in.getPortSet().values())
		{
			portSet[x]=pp.getPort();
			turnOverTime[x]=DefaultTurnOverTime;
			ladenDemurrageCost[x]=DefaultLadenDemurrageCost;
			emptyDemurrageCost[x]=DefaultEmptyDemurrageCost;
			pp.setRentalCost(DefaultUnitRentalCost);
			pp.setTurnOverTime(DefaultTurnOverTime);
			pp.setLadenDemurralCost(DefaultLadenDemurrageCost);
			pp.setEmptyDemurralCost(DefaultEmptyDemurrageCost);
			pp.setLoadingCost(DefaultUnitLoadingCost);
			pp.setDischargeCost(DefaultUnitDischargeCost);
			pp.setTransshipmentCost(DefaultUnitTransshipmentCost);
			x=x+1;
		}
		p.setPortSet(portSet);
		p.setTurnOverTime(turnOverTime);
		p.setLadenDemurrageCost(ladenDemurrageCost);
		p.setEmptyDemurrageCost(emptyDemurrageCost);
	}
	private void WriteRequests() throws IOException {
		String Instance ="S" + randomSeed + "-" +"T"+ p.getTimeHorizon() + "(" + distributionType + ")"+ log_normal_sigma_factor;
		File file = new File(RootPath + DataPath + CasePath + "Demands" + Instance + ".txt");
		if (!file.exists()) {
			try {
				file.createNewFile();
			} catch (IOException e) {
				e.printStackTrace();
			}
		}
		FileWriter filewriter = new FileWriter(file, false);

		filewriter.write("RequestID" + "\t"
				+ "OriginPort" + "\t"
				+ "DestinationPort" + "\t"
				+ "EarliestDepartureTime" + "\t"
				+ "LatestArrivalTime" + "\t"
				+ "Demand" + "\t"
				+ "PenaltyCost" + "\n");
		// write request demands
		for(int i=0;i<in.getRequestSet().size();i++)
		{
			filewriter.write(in.getRequestSet().get(i).getRequestID() + "\t"
					+ in.getRequestSet().get(i).getOriginPort() + "\t"
					+ in.getRequestSet().get(i).getDestinationPort() + "\t"
					+ in.getRequestSet().get(i).getEarliestPickupTime() + "\t"
					+ in.getRequestSet().get(i).getLatestDestinationTime() + "\t"
					+ p.getDemand()[i] + "\t"
					+ p.getPenaltyCostForDemand()[i] + "\n");
		}
		filewriter.flush();
	}
	private void SetRequests() throws IOException {
		// set request demands
		int [] demandRequest =new int [in.getRequestSet().size()];
		String []  originOfDemand =new String  [in.getRequestSet().size()];
		String []  destinationOfDemand =new String  [in.getRequestSet().size()];
		double [] demand =new double[in.getRequestSet().size()];
		double [] demandMaximum =new double[in.getRequestSet().size()];
		double [] penaltyCostForDemand= new double[in.getRequestSet().size()];
		int x=0;
		for(Request rr: in.getRequestSet())
		{
			demandRequest[x]=rr.getRequestID();
			originOfDemand[x]=rr.getOriginPort();
			destinationOfDemand[x]=rr.getDestinationPort();
			int groupO=rr.getOriginGroup();
			int groupD=rr.getDestinationGroup();

			ODRange groupRangeRange = in.getGroupRange(groupO, groupD);

			demand[x]=groupRangeRange.getDemandLowerBound()
					+(int)(
							(groupRangeRange.getDemandUpperBound()
									-groupRangeRange.getDemandLowerBound())
									*getRandDouble()
							);
			penaltyCostForDemand [x]=groupRangeRange.getFreightLowerBound()
					+(int)(
					(groupRangeRange.getFreightUpperBound()
							- groupRangeRange.getFreightLowerBound())
									*getRandDouble());
			penaltyCostForDemand [x] = penaltyCostForDemand [x] * penaltyCoefficient;
			rr.setPenaltyCost(penaltyCostForDemand[x]);
			// variable demand = 0.05 * normal demand
			demandMaximum[x]=demand[x]*uncertainDegree;
			rr.setMeanDemand(demand[x]);
			rr.setVarianceDemand(demandMaximum[x]);

			x=x+1;
		}

		p.setDemandRequestSet(demandRequest);
		p.setOriginOfDemand(originOfDemand);
		p.setDestinationOfDemand(destinationOfDemand);
		p.setDemand(demand);
		p.setMaximumDemandVariation(demandMaximum);
		p.setPenaltyCostForDemand(penaltyCostForDemand);

		WriteRequests();
	}
	private void SetShipRoutes(){
		// set ship route IDs set
		int [] vesselRoute =new int [in.getShipRouteSet().size()];
		int [] roundTrips = new int[in.getShipRouteSet().size()];
		int x=0;
		for(ShipRoute ss:in.getShipRouteSet().values())
		{
			vesselRoute[x]=ss.getShipRouteID();
			roundTrips[x] = ss.getNumRoundTrips();
			x=x+1;
		}
		p.setShippingRouteSet(vesselRoute);
		p.setNumOfRoundTrips(roundTrips);
	}
	private void SetVessels(){
		// set vessel type
		// v[x][r] == 1: vessel x is for ship route r
		// v[x][r] == 0: otherwise
		int[] vessel =new int [in.getVesselTypeSet().size()];
		int[] vesselCapacity =new int [in.getVesselTypeSet().size()];
		double [] vesselOperationCost =new double [in.getVesselTypeSet().size()];
		int [][] vesselTypeAndShippingRoute =new int[in.getVesselTypeSet().size()][in.getShipRouteSet().size()];
		int [] shippingRouteVesselNum = new int[p.getShippingRouteSet().length];
		Arrays.fill(shippingRouteVesselNum, 0);
		int x=0;
		for(VesselType v : in.getVesselTypeSet())
		{
			vesselTypeAndShippingRoute[x][v.getRouteID()-1]=1;
			shippingRouteVesselNum[v.getRouteID()-1] += 1;
			vessel[x]=v.getId();
			vesselCapacity[x]=v.getCapacity();
			vesselOperationCost[x]=v.getCost();
			x=x+1;
		}
		p.setVesselTypeAndShipRoute(vesselTypeAndShippingRoute);
		p.setVesselSet(vessel);
		p.setVesselCapacity(vesselCapacity);
		p.setVesselOperationCost(vesselOperationCost);
		p.setShippingRouteVesselNum(shippingRouteVesselNum);
	}
	private void SetVesselPaths(){
		// set shipRoute And vessel ContainerPath :
		// 			if vesselPath w is shipping for shipRoute r , then shipRouteAndVesselPath[r][w] == 1
		// set arcAndVesselPath :
		// 			if travel arc nn is in vessel ContainerPath w, then arcAndVesselPath[nn][w] == 1
		int [][] shipRouteAndVesselPath = new int [in.getShipRouteSet().size()] [in.getVesselPathSet().size()];
		int[] vesselPathSet =new int [in.getVesselPathSet().size()];
		int [][] arcAndVesselPath =new int [in.getTravelingArcSet().size()][in.getVesselPathSet().size()];
		int[] VesselPathShipRouteSet =new int [in.getVesselPathSet().size()];

		for(int w = 0; w < in.getVesselPathSet().size(); w++)
		{
			int ww = in.getVesselPathSet().get(w).getVesselPathID();

			int r = in.getVesselPathSet().get(w).getRouteID() - 1;
			shipRouteAndVesselPath[r][w] = 1;
			VesselPathShipRouteSet[w] = r;

			for (int nn = 0; nn < in.getTravelingArcSet().size(); nn++)
			{
				for (int j = 0; j < in.getVesselPathSet().get(w).getArcIDs().length; j++)
				{
					if (in.getTravelingArcSet().get(nn).getTravelingArcID() == in.getVesselPathSet().get(w).getArcIDs()[j])
					{
						arcAndVesselPath[nn][w] = 1;
					}
				}
			}
			vesselPathSet[w] = ww;
		}

		// [nn][w]
		p.setArcAndVesselPath(arcAndVesselPath);
		// [r][w]
		p.setShipRouteAndVesselPath(shipRouteAndVesselPath);
		p.setVesselPathSet(vesselPathSet);
		p.setVesselPathShipRouteIndex(VesselPathShipRouteSet);
	}
	private void SetContainerPaths(){
		// calculate total demurrage for each path
		// demurrage = sum{transshipTime * unit demurrage}
		// arcAndPath : arcs X paths
		// arcAndPath[arc][path] == 1 : the travel arc is in path arcs
		double [] PathLoadAndDischargeCost=new double [in.getContainerPaths().size()];
		double [] ladenPathDemurrageCost=new double [in.getContainerPaths().size()];
		double [] emptyPathDemurrageCost=new double [in.getContainerPaths().size()];
		double [] ladenPathCost=new double [in.getContainerPaths().size()];
		double [] emptyPathCost=new double [in.getContainerPaths().size()];
		int [] travelTimeOnLadenPath=new int [in.getContainerPaths().size()];
		int [] PathSet =new int [in.getContainerPaths().size()];
		int [][] arcAndPath  =new int [in.getTravelingArcSet().size()][in.getContainerPaths().size()];
		int x=0;
		for(ContainerPath pp :in.getContainerPaths())
		{
			for (Port port: in.getPortSet().values()) {
				if (port.getPort().equals(pp.getOriginPort())){
					PathLoadAndDischargeCost[x] += port.getLoadingCost();
				} else if (port.getPort().equals(pp.getDestinationPort())) {
					PathLoadAndDischargeCost[x] += port.getDischargeCost();
				}
				else {
					if(pp.getTransshipmentPort() != null && pp.getTransshipmentPort().length > 0){
						for (int j = 0; j < pp.getTransshipmentPort().length; j++) {
							if(port.getPort().equals(pp.getTransshipmentPort()[j])){
								PathLoadAndDischargeCost[x] += port.getTransshipmentCost();
							}
						}
					}
				}
			}
			pp.setPathCost(PathLoadAndDischargeCost[x]);

			// why - 7 ? a setting
//			ladenPathDemurrageCost[x]=Math.max(0, 175*(pp.getTotalTransshipment_Time()-7));
//			emptyPathDemurrageCost[x]=Math.max(0, 100*(pp.getTotalTransshipment_Time()-7));

			ladenPathDemurrageCost[x]=Math.max(0, 175*pp.getTotalDemurrageTime());
			emptyPathDemurrageCost[x]=Math.max(0, 100*pp.getTotalDemurrageTime());

			ladenPathCost[x]= ladenPathDemurrageCost[x] + PathLoadAndDischargeCost[x];
			emptyPathCost[x]= emptyPathDemurrageCost[x] + PathLoadAndDischargeCost[x] * 0.5;

			travelTimeOnLadenPath[x]=pp.getPathTime();

			PathSet[x]=pp.getContainerPathID();

			for (int i = 0; i < in.getTravelingArcSet().size(); i++) {
				arcAndPath[i][x] = 0;
				for (int j = 0; j < pp.getArcsID().length; j++) {
					if(in.getTravelingArcSet().get(i).getTravelingArcID() == pp.getArcsID()[j])
					{
						arcAndPath[i][x] = 1;
					}
				}
			}
			++x;
		}

		p.setLadenPathDemurrageCost(ladenPathDemurrageCost);
		p.setEmptyPathDemurrageCost(emptyPathDemurrageCost);
		p.setLadenPathCost(ladenPathCost);
		p.setEmptyPathCost(emptyPathCost);
		p.setTravelTimeOnPath(travelTimeOnLadenPath);
		p.setPathSet(PathSet);
		p.setArcAndPath(arcAndPath);
	}
	private void SetArcCapacity(){
		for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
			double capacity = 0;
			for(int r = 0; r<p.getShippingRouteSet().length; r++)
			{
				// ω∈Ω
				for(int w=0;w<p.getVesselPathSet().length;w++)
				{
					// h∈H
					for(int h=0;h<p.getVesselSet().length;h++)
					{
						capacity +=p.getArcAndVesselPath()[nn][w]
								*p.getVesselCapacity()[h]
								*p.getShipRouteAndVesselPath()[r][w]
								*p.getVesselTypeAndShipRoute()[h][r];
					}
				}
			}

			if ( DebugEnable && GenerateParamEnable)
			{
				log.info("RouteID = "+in.getTravelingArcSet().get(nn).getRouteID() +'\t'
						+"TravelArcID = " + in.getTravelingArcSet().get(nn).getTravelingArcID() +'\t'
						+"(" + in.getTravelingArcSet().get(nn).getOriginPort().toString()
						+"," + in.getTravelingArcSet().get(nn).getDestinationPort().toString() +")" +'\t'
						+"("+in.getTravelingArcSet().get(nn).getOriginTime()
						+"--"+in.getTravelingArcSet().get(nn).getDestinationTime()+")"+'\t'
						+"Total Capacity = " + capacity
				);
			}
		}
	}
	private void SetInitialEmptyContainers(){
		// calculate initial number of empty containers for each port at time 0
		// initial number of empty container in pp = total demands which origins in port pp * [0.8, 1.0]
		int[] initialEmptyContainer =new int [in.getPortSet().size()];
		int x=0;
		double alpha=0.8+0.2*getRandDouble();
		for(Port pp:in.getPortSet().values())
		{
			for(int i = 0; i<in.getRequestSet().size(); i++)
			{
				if(pp.getPort().equals(in.getRequestSet().get(i).getOriginPort())
						&&in.getRequestSet().get(i).getEarliestPickupTime()<initialEmptyContainers)
				{
					initialEmptyContainer [x]=(int) (initialEmptyContainer [x]+alpha*p.getDemand()[i]);
				}
			}
			x=x+1;
		}
		p.setInitialEmptyContainer(initialEmptyContainer);
	}

	private void WriteRandomSampleSceneSet() throws IOException {
		String samplefilename = "R"+ in.getShipRouteSet().size() + "-T"
				+ p.getTimeHorizon() + "-Tau"+ p.getTau() + "-S" + randomSeed + "-SampleTestSet"+ ".txt";
		File file = new File(RootPath + DataPath + CasePath + samplefilename);
		if (!file.exists()) {
			try {
				file.createNewFile();
			} catch (IOException e) {
				e.printStackTrace();
			}
		}

		FileWriter filewriter = new FileWriter(file, false);
		filewriter.flush();

		double[][] sampleScenes =p.getSampleScenes();
		for(int i=0;i<p.getSampleScenes().length;i++)
		{
			filewriter.write(i + "\t");
			for(int j=0;j<p.getSampleScenes()[i].length;j++)
			{
				if(sampleScenes[i][j] != 0) {
					filewriter.write(j + ",");
				}
			}
			filewriter.write("\n");
			filewriter.flush();
		}
		filewriter.close();
	}

	private void GenerateRandomSampleSceneSet() throws IOException {
		// generate random sample scenarios
		double[][] sampleScenes = new double[numSampleScenes][in.getRequestSet().size()];
		List<Scenario> scenarios = new ArrayList<>();
		for(int i=0;i<numSampleScenes;i++)
		{
			Set<Integer> set = new HashSet<>();
			while (set.size() < p.getTau()) {
				set.add(random.nextInt(in.getRequestSet().size()));
			}

			String scene = "";
			for(int j : set){
				sampleScenes[i][j] = 1;
				scene += j + ",";
			}
			scenarios.add(new Scenario(sampleScenes[i], i));
		}
		p.setSampleScenes(sampleScenes);
		in.setScenarios(scenarios);

		if(WhetherWriteSampleTests)
		{
			WriteRandomSampleSceneSet();
		}
	}
}

