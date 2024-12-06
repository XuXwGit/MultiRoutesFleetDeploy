package multi;

public class ShipRoute {
	private int shippingRouteID;

	private int cycleTime;

	public int getNumVesselPaths() {
		return numVesselPaths;
	}

	public void setNumVesselPaths(int numVesselPaths) {
		this.numVesselPaths = numVesselPaths;
	}

	private int numVesselPaths;
	private int numRoundTrips;
	private int numberofPorts;
	private String [] Ports;
	private int numberofCall;
	private String [] portsofCall;
	private int[] TimePointsOfCall;

	public ShipRoute() {
	}

	public int getShippingRouteID() {
		return shippingRouteID;
	}
	public void setShippingRouteID(int shippingRouteID) {
		this.shippingRouteID = shippingRouteID;
	}

	public int getCycleTime() {
		return cycleTime;
	}

	public void setCycleTime(int cycleTime) {
		this.cycleTime = cycleTime;
	}

	public int getNumberofPorts() {
		return numberofPorts;
	}

	public int getNumRoundTrips() {
		return numRoundTrips;
	}

	public void setNumRoundTrips(int numRoundTrips) {
		this.numRoundTrips = numRoundTrips;
	}

	public void setNumberofPorts(int numberofPorts) {
		this.numberofPorts = numberofPorts;
	}
	public String[] getPorts() {
		return Ports;
	}
	public void setPorts(String[] ports) {
		Ports = ports;
	}
	public int getNumberofCall() {
		return numberofCall;
	}
	public void setNumberofCall(int numberofCall) {
		this.numberofCall = numberofCall;
	}
	public String[] getPortsofCall() {
		return portsofCall;
	}
	public void setPortsofCall(String[] portsofCall) {
		this.portsofCall = portsofCall;
	}
	public int[] getTimePointsOfCall(){
		return	TimePointsOfCall;
	}
	public void setTimePointsOfCall(int[] TimePointsOfCall){
		this.TimePointsOfCall = TimePointsOfCall;
	}
	
	public int getCallIndexOfPort(String port){
		for (int p = 0; p < this.numberofCall - 1; p++) {
			if(port.equals(this.getPortsofCall()[p])  )
			{
				return p;
			}
		}
		return -1;
	}
}
