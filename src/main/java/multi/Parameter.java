package multi;

import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

import java.util.Arrays;
import java.util.Map;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
@Getter
@Setter
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
	private Map<Integer, Integer> arcCapacity;

	public Parameter() {
	}

	public void changeMaximumDemandVariation(double coeff){
		double[] newMaxDemandVariation = new double[this.getDemand().length];
		for (int i = 0; i < this.demand.length; i++) {
			newMaxDemandVariation[i] = maximumDemandVariation[i] * coeff;
		}
		setMaximumDemandVariation(newMaxDemandVariation);
	}
	public void setTurnOverTime(int[] turnOverTime) {
		this.turnOverTime = turnOverTime;
	}
	public void setTurnOverTime(int turnOverTime){
		int[] turn_over_time = new int[this.portSet.length];
		Arrays.fill(turn_over_time, turnOverTime);
		setTurnOverTime(turn_over_time);
	}
	public void changePenaltyCostForDemand(double penaltyCostCoeff) {
		double[] newPenaltyCost = new double[this.demand.length];
		for (int i = 0; i < demand.length; i++) {
			newPenaltyCost[i] = penaltyCostForDemand[i] * penaltyCostCoeff;
		}
		this.penaltyCostForDemand = newPenaltyCost;
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

				if("Homo".equals(FleetType)) {
					// vesselTypeAndShipRoute == 1 : r(h) = r
					operation_cost += (this.getVesselTypeAndShipRoute()[h][r]
							* this.getShipRouteAndVesselPath()[r][w]
							* this.getVesselOperationCost()[h]
							* vValue[h][r]);
				}
				else if ("Hetero".equals(FleetType)) {
					operation_cost += (this.getVesselOperationCost()[h]
							* vValue[h][w]);
				}
			}
		}
		return operation_cost;
	}
	public int[][] solutionToVValue(int[] solution){
		int[][] vValue = new int[0][];
		if("Homo".equals(FleetType)){
			vValue = new int[this.getVesselSet().length][this.getShippingRouteSet().length];
			for(int r = 0; r<this.getShippingRouteSet().length; r++) {
				vValue[solution[r] - 1][r] = 1;
			}
		} else if ("Hetero".equals(FleetType)) {
			vValue = new int[this.getVesselSet().length][this.getVesselPathSet().length];
			for(int w=0;w<this.getVesselPathSet().length;++w)
			{
				vValue[solution[w]-1][w] = 1;
			}
		}
		else{
			log.info("Error in Fleet type!");
		}

		return vValue;
	}
}
