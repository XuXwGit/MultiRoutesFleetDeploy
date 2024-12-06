package multi;

public class Port {
	private int id;
	private String port;
	private String region;
	private int whetherTrans;
	private int group;
	public int getId() {
		return id;
	}
	public void setId(int id) {
		this.id = id;
	}
	public String getPort() {
		return port;
	}
	public void setPort(String port) {
		this.port = port;
	}
	public int getWhetherTrans() {
		return whetherTrans;
	}
	public void setWhetherTrans(int whetherTrans) {
		this.whetherTrans = whetherTrans;
	}
	public String getRegion() {
		return region;
	}

	public void setRegion(String region) {
		this.region = region;
	}
	public int getGroup() {
		return group;
	}
	public void setGroup(int group) {
		this.group = group;
	}

	public double getLadenDemurrageCost() {
		return ladenDemurrageCost;
	}

	public void setLadenDemurrageCost(double ladenDemurrageCost) {
		this.ladenDemurrageCost = ladenDemurrageCost;
	}

	public double getEmptyDemurrageCost() {
		return emptyDemurrageCost;
	}

	public void setEmptyDemurrageCost(double emptyDemurrageCost) {
		this.emptyDemurrageCost = emptyDemurrageCost;
	}

	public double getLoadingCost() {
		return loadingCost;
	}

	public void setLoadingCost(double loadingCost) {
		this.loadingCost = loadingCost;
	}

	public double getDischargeCost() {
		return dischargeCost;
	}

	public void setDischargeCost(double dischargeCost) {
		this.dischargeCost = dischargeCost;
	}

	public double getTransshipmentCost() {
		return transshipmentCost;
	}

	public void setTransshipmentCost(double transshipmentCost) {
		this.transshipmentCost = transshipmentCost;
	}

	private double ladenDemurrageCost;
	private double emptyDemurrageCost;
	private double loadingCost;
	private double dischargeCost;
	private double transshipmentCost;
	private int turnOverTime;

	public int getTurnOverTime() {
		return turnOverTime;
	}

	public void setTurnOverTime(int turnOverTime) {
		this.turnOverTime = turnOverTime;
	}

	public double getRentalCost() {
		return rentalCost;
	}

	public void setRentalCost(double rentalCost) {
		this.rentalCost = rentalCost;
	}

	private double rentalCost;
}
