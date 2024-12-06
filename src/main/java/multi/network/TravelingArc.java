package multi;

public class TravelingArc {
	private int travelingArc_ID;
	private int route;
	private int origin_node_ID;
	private int origin_Call;
	private String origin_Port;
	private int round_Trip;
	private int originTime;	
	private int travelingTime;
	private int destination_node_ID;
	private int Destination_Call;
	private String destination_Port;
	private int destinationTime;
	public int getTravelingArc_ID() {
		return travelingArc_ID;
	}
	public void setTravelingArc_ID(int travelingArc_ID) {
		this.travelingArc_ID = travelingArc_ID;
	}
	public int getRoute() {
		return route;
	}
	public void setRoute(int route) {
		this.route = route;
	}
	public int getRouteIndex(){
		return getRoute() - 1;
	}
	public int getOrigin_node_ID() {
		return origin_node_ID;
	}
	public void setOrigin_node_ID(int origin_node_ID) {
		this.origin_node_ID = origin_node_ID;
	}
	public int getOrigin_Call() {
		return origin_Call;
	}
	public void setOrigin_Call(int origin_Call) {
		this.origin_Call = origin_Call;
	}
	public String getOriginPort() {
		return origin_Port;
	}
	public void setOrigin_Port(String origin_Port) {
		this.origin_Port = origin_Port;
	}
	public int getRound_Trip() {
		return round_Trip;
	}
	public void setRound_Trip(int round_Trip) {
		this.round_Trip = round_Trip;
	}
	public int getOriginTime() {
		return originTime;
	}
	public void setOriginTime(int originTime) {
		this.originTime = originTime;
	}
	public int getTravelingTime() {
		return travelingTime;
	}
	public void setTravelingTime(int travelingTime) {
		this.travelingTime = travelingTime;
	}
	public int getDestination_node_ID() {
		return destination_node_ID;
	}
	public void setDestination_node_ID(int destination_node_ID) {
		this.destination_node_ID = destination_node_ID;
	}
	public int getDestination_Call() {
		return Destination_Call;
	}
	public void setDestination_Call(int destination_Call) {
		Destination_Call = destination_Call;
	}
	public String getDestinationPort() {
		return destination_Port;
	}
	public void setDestination_Port(String destination_Port) {
		this.destination_Port = destination_Port;
	}
	public int getDestinationTime() {
		return destinationTime;
	}
	public void setDestinationTime(int destinationTime) {
		this.destinationTime = destinationTime;
	}
	


}
