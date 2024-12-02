package multi;

import multi.DefaultSetting;

import java.util.Arrays;

public class Parameter extends DefaultSetting {
	private int timeHorizon;
	private int tau;
	private double uncertainDegree;
	private double rentalCost;
	private int [] travelingArcsSet;
	private int [] transhipmentArcsSet;
	private int [] timePointSet;
	private int [] shippingRouteSet;

	private int[] numOfRoundTrips;
	private int [] vesselSet;
	private int [] vesselPathSet;
	private int [] NumVesselPaths;
	private int [] PathSet;
	private int [] initialEmptyContainer;
	private int [] demandRequestSet;
	private int [] turnOverTime;
	private int [] vesselCapacity;
	private int [] travelTimeOnPath;
	private int [][] arcAndVesselPath;
	private int [][] arcAndPath;
	private int [][] shipRouteAndVesselPath;
	private int[] VesselPathShipRouteIndex;
	private int[] shippingRouteVesselNum;
	private int [][] vesselTypeAndShipRoute;
	private String [] portSet;
	private String [] originOfDemand;
	private String [] destinationOfDemand;
	private double [] demand;

	private double [] vesselOperationCost;
	private double [] penaltyCostForDemand;
	private double [] ladenDemurrageCost;
	private double [] emptyDemurrageCost;
	private double [] ladenPathDemurrageCost;
	private double [] emptyPathDemurrageCost;
	private double [] ladenPathCost;
	private double [] emptyPathCost;
	private double [] maximumDemandVariation;
	private double[][] sampleScenes;

	public Parameter() {
	}
	public int getTimeHorizon() {
		return timeHorizon;
	}
	public void setTimeHorizon(int timeHorizon) {
		this.timeHorizon = timeHorizon;
	}
	public int getTau() {
		return tau;
	}
	public void setTau(int tau) {
		this.tau = tau;
	}
	public int[] getTravelTimeOnPath() {
		return travelTimeOnPath;
	}
	public void setUncertainDegree(double uncertainDegree)
	{
		this.uncertainDegree = uncertainDegree;
	}
	public double getUncertainDegree()
	{
		return uncertainDegree;
	}
	public void setTravelTimeOnPath(int[] travelTimeOnPath) {
		this.travelTimeOnPath = travelTimeOnPath;
	}
	public double[] getMaximumDemandVariation() {
		return maximumDemandVariation;
	}
	public void setMaximumDemandVariation(double[] maximumDemandVariation) {
		this.maximumDemandVariation = maximumDemandVariation;
	}
	public void changeMaximunDemandVariation(double coeff){
		double[] newMaxDemandVariation = new double[this.getDemand().length];
		for (int i = 0; i < this.demand.length; i++) {
			newMaxDemandVariation[i] = maximumDemandVariation[i] * coeff;
		}
		setMaximumDemandVariation(newMaxDemandVariation);
	}
	public int[] getPathSet() {
		return PathSet;
	}
	public void setPathSet(int[] PathSet) {
		this.PathSet = PathSet;
	}
	public int[][] getArcAndPath() {
		return arcAndPath;
	}
	public void setArcAndPath(int[][] arcAndPath) {
		this.arcAndPath = arcAndPath;
	}
	public int[] getVesselPathSet() {
		return vesselPathSet;
	}
	public void setVesselPathSet(int[] vesselPathSet) {
		this.vesselPathSet = vesselPathSet;
	}
	public int[] getTravelingArcsSet() {
		return travelingArcsSet;
	}
	public void setTravelingArcsSet(int[] travelingArcsSet) {
		this.travelingArcsSet = travelingArcsSet;
	}
	public int[] getTranshipmentArcsSet() {
		return transhipmentArcsSet;
	}
	public void setTranshipmentArcsSet(int[] transhipmentArcsSet) {
		this.transhipmentArcsSet = transhipmentArcsSet;
	}
	public int[] getTimePointSet() {
		return timePointSet;
	}
	public void setTimePointSet(int[] timePointSet) {
		this.timePointSet = timePointSet;
	}
	 
	public String[] getPortSet() {
		return portSet;
	}
	public void setPortSet(String[] portSet) {
		this.portSet = portSet;
	}
	public int[] getDemandRequestSet() {
		return demandRequestSet;
	}
	public void setDemandRequestSet(int[] demandRequestSet) {
		this.demandRequestSet = demandRequestSet;
	}
	public int[] getShippingRouteSet() {
		return shippingRouteSet;
	}
	public void setShippingRouteSet(int[] shippingRouteSet) {
		this.shippingRouteSet = shippingRouteSet;
	}

	public int[] getShippingRouteVesselNum() {
		return shippingRouteVesselNum;
	}

	public void setShippingRouteVesselNum(int[] shippingRouteVesselNum) {
		this.shippingRouteVesselNum = shippingRouteVesselNum;
	}

	public int[] getNumOfRoundTrips() {
		return numOfRoundTrips;
	}

	public void setNumOfRoundTrips(int[] numOfRoundTrips) {
		this.numOfRoundTrips = numOfRoundTrips;
	}

	public int[] getVesselSet() {
		return vesselSet;
	}
	public void setVesselSet(int[] vesselSet) {
		this.vesselSet = vesselSet;
	}
	public int[] getInitialEmptyContainer() {
		return initialEmptyContainer;
	}
	public void setInitialEmptyContainer(int[] initialEmptyContainer) {
		this.initialEmptyContainer = initialEmptyContainer;
	}
	public String[] getOriginOfDemand() {
		return originOfDemand;
	}
	public void setOriginOfDemand(String[] originOfDemand) {
		this.originOfDemand = originOfDemand;
	}
	public String[] getDestinationOfDemand() {
		return destinationOfDemand;
	}
	public void setDestinationOfDemand(String[] destinationOfDemand) {
		this.destinationOfDemand = destinationOfDemand;
	}
	public double[] getDemand() {
		return demand;
	}
	public void setDemand(double[] demand) {
		this.demand = demand;
	}
	public int[] getTurnOverTime() {
		return turnOverTime;
	}
	public void setTurnOverTime(int[] turnOverTime) {
		this.turnOverTime = turnOverTime;
	}
	public void setTurnOverTime(int turnOverTime){
		int[] turn_over_time = new int[this.portSet.length];
		Arrays.fill(turn_over_time, turnOverTime);
		setTurnOverTime(turn_over_time);
	}
	public int[] getVesselCapacity() {
		return vesselCapacity;
	}
	public void setVesselCapacity(int[] vesselCapacity) {
		this.vesselCapacity = vesselCapacity;
	}
	public double[] getVesselOperationCost() {
		return vesselOperationCost;
	}
	public void setVesselOperationCost(double[] vesselOperationCost) {
		this.vesselOperationCost = vesselOperationCost;
	}
	public double[] getPenaltyCostForDemand() {
		return penaltyCostForDemand;
	}
	public void setPenaltyCostForDemand(double[] penaltyCostForDemand) {
		this.penaltyCostForDemand = penaltyCostForDemand;
	}
	public void changePenaltyCostForDemand(double penaltyCostCoeff) {
		double[] newPenaltyCost = new double[this.demand.length];
		for (int i = 0; i < demand.length; i++) {
			newPenaltyCost[i] = penaltyCostForDemand[i] * penaltyCostCoeff;
		}
		this.penaltyCostForDemand = newPenaltyCost;
	}
	public double getRentalCost() {
		return rentalCost;
	}
	public void setRentalCost(double rentalCost) {
		this.rentalCost = rentalCost;
	}
	public void changeRentalCost(double rentalCostcoeff) {
		this.rentalCost = rentalCost * rentalCostcoeff;
	}
	public void setLadenDemurrageCost(double[] ladenDemurrageCost) {
		this.ladenDemurrageCost = ladenDemurrageCost;
	}
	public void setEmptyDemurrageCost(double[] emptyDemurrageCost) {
		this.emptyDemurrageCost = emptyDemurrageCost;
	}

	public int[][] getArcAndVesselPath() {
		return arcAndVesselPath;
	}
	public void setArcAndVesselPath(int[][] arcAndVesselPath) {
		this.arcAndVesselPath = arcAndVesselPath;
	}

	public int[][] getShipRouteAndVesselPath() {
		return shipRouteAndVesselPath;
	}
	public void setShipRouteAndVesselPath(int[][] shipRouteAndVesselPath) {
		this.shipRouteAndVesselPath = shipRouteAndVesselPath;
	}
	public int[] getVesselPathShipRouteIndex() {
		return VesselPathShipRouteIndex;
	}

	public void setVesselPathShipRouteIndex(int[] vesselPathShipRouteIndex) {
		VesselPathShipRouteIndex = vesselPathShipRouteIndex;
	}

	public double[] getLadenPathDemurrageCost() {
		return ladenPathDemurrageCost;
	}
	public void setLadenPathDemurrageCost(double[] ladenPathDemurrageCost) {
		this.ladenPathDemurrageCost = ladenPathDemurrageCost;
	}
	public double[] getEmptyPathDemurrageCost() {
		return emptyPathDemurrageCost;
	}
	public void setEmptyPathDemurrageCost(double[] emptyPathDemurrageCost) {
		this.emptyPathDemurrageCost = emptyPathDemurrageCost;
	}
	public double[] getLadenPathCost() {
		return ladenPathCost;
	}

	public void setLadenPathCost(double[] ladenPathCost) {
		this.ladenPathCost = ladenPathCost;
	}
	public double[] getEmptyPathCost() {
		return emptyPathCost;
	}
	public void setEmptyPathCost(double[] emptyPathCost) {
		this.emptyPathCost = emptyPathCost;
	}
	public int[][] getVesselTypeAndShipRoute() {
		return vesselTypeAndShipRoute;
	}
	public void setVesselTypeAndShipRoute(int[][] vesselTypeAndShipRoute) {
		this.vesselTypeAndShipRoute = vesselTypeAndShipRoute;
	}

	public int getTotalCapacityMax(){
		int total_capacity = 0;
		// r \in R
		for(int r = 0; r < getShippingRouteSet().length; r++)
		{
			// w \in \Omega
			// r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
			for(int w = 0; w < getVesselPathSet().length; w++)
			{
				double max_capacity = 0;
				// h \in H_r
				// r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
				for(int h = 0; h < getVesselSet().length; h++)
				{
					if(getVesselTypeAndShipRoute()[h][r] * getShipRouteAndVesselPath()[r][w] != 0){
						if(getVesselCapacity()[h]>max_capacity){
							max_capacity = getVesselCapacity()[h];
						}
					}
				}
				total_capacity += max_capacity;
			}
		}

		return total_capacity;
	}
	public int getTotalCapacityMin(){
		int total_capacity = 0;
		// r \in R
		for(int r = 0; r < getShippingRouteSet().length; r++)
		{
			// w \in \Omega
			// r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
			for(int w = 0; w < getVesselPathSet().length; w++)
			{
				double min_capacity = Integer.MAX_VALUE;
				// h \in H_r
				// r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
				for(int h = 0; h < getVesselSet().length; h++)
				{
					if(getVesselTypeAndShipRoute()[h][r] * getShipRouteAndVesselPath()[r][w] != 0){
						if(getVesselCapacity()[h] < min_capacity){
							min_capacity = getVesselCapacity()[h];
						}
					}
				}
				total_capacity += min_capacity;
			}
		}

		return total_capacity;
	}

	public int getTotalDemand(){
		int total_demand = 0;
		for (int i = 0; i < getDemand().length; i++) {
			total_demand += getDemand()[i] + getMaximumDemandVariation()[i];
		}
		return total_demand;
	}

	public double getOperationCost(int[][] vValue){
		double operation_cost = 0;
		for (int h = 0; h < this.getVesselSet().length; ++h)
		{
			for (int w = 0; w < this.getVesselPathSet().length; ++w)
			{
				// r(��) == r
				int r = this.getVesselPathShipRouteIndex()[w];

				if(FleetType.equals("Homo")) {
					// vesselTypeAndShipRoute == 1 : r(h) = r
					operation_cost += (this.getVesselTypeAndShipRoute()[h][r]
							* this.getShipRouteAndVesselPath()[r][w]
							* this.getVesselOperationCost()[h]
							* vValue[h][r]);
				}
				else if (FleetType.equals("Hetero")) {
					operation_cost += (this.getVesselOperationCost()[h]
							* vValue[h][w]);
				}
			}
		}
		return operation_cost;
	}
	public int[][] solutionToVValue(int[] solution){
		int[][] vValue = new int[0][];
		if(FleetType.equals("Homo")){
			vValue = new int[this.getVesselSet().length][this.getShippingRouteSet().length];
			for(int r = 0; r<this.getShippingRouteSet().length; r++) {
				vValue[solution[r] - 1][r] = 1;
			}
		} else if (FleetType.equals("Hetero")) {
			vValue = new int[this.getVesselSet().length][this.getVesselPathSet().length];
			for(int w=0;w<this.getVesselPathSet().length;++w)
			{
				vValue[solution[w]-1][w] = 1;
			}
		}
		else{
			System.out.println("Error in Fleet type!");
		}

		return vValue;
	}

	public double[][] getSampleScenes() {
		return sampleScenes;
	}

	public void setSampleScenes(double[][] sampleScenes) {
		this.sampleScenes = sampleScenes;
	}

}
