package multi;

public class TransshipArc {
	private int transshipArc_ID;
	private String port;
	private int originNodeID;
	private int originTime;
	private int transshipTime;
	private int destination_node_ID;
	private int destinationTime;
	private int fromRoute;
	private int toRoute;
	public int getTransshipArc_ID() {
		return transshipArc_ID;
	}
	public void setTransshipArc_ID(int transshipArc_ID) {
		this.transshipArc_ID = transshipArc_ID;
	}
	public String getPort() {
		return port;
	}
	public void setPort(String port) {
		this.port = port;
	}
	public int getOriginNodeID() {
		return originNodeID;
	}
	public void setOriginNodeID(int originNodeID) {
		this.originNodeID = originNodeID;
	}
	public int getOriginTime() {
		return originTime;
	}
	public void setOriginTime(int originTime) {
		this.originTime = originTime;
	}
	public int getTransshipTime() {
		return transshipTime;
	}
	public void setTransshipTime(int transshipTime) {
		this.transshipTime = transshipTime;
	}
	public int getDestination_node_ID() {
		return destination_node_ID;
	}
	public void setDestination_node_ID(int destination_node_ID) {
		this.destination_node_ID = destination_node_ID;
	}
	public int getDestinationTime() {
		return destinationTime;
	}
	public void setDestinationTime(int destinationTime) {
		this.destinationTime = destinationTime;
	}
	public int getFromRoute() {
		return fromRoute;
	}
	public void setFromRoute(int fromRoute) {
		this.fromRoute = fromRoute;
	}
	public int getToRoute() {
		return toRoute;
	}
	public void setToRoute(int toRoute) {
		this.toRoute = toRoute;
	}

}
