package multi;

public class LadenPath {
	private int request_ID;
	private String origin_Port;
	private int origin_Time;
	private String destination_Port;
	private int round_trip;
	private int w_i_Earlist;
	private int arrival_Time_to_destination;
	private int pathtime;	
	private String[] transshipment_port;
	private int[] transshipment_Time;
	private String [] port_Path;
	private int path_ID;
	private int numberOfArcs;
	private int [] arcs_ID;
	public String getDestination_Port() {
		return destination_Port;
	}
	public void setDestination_Port(String destination_Port) {
		this.destination_Port = destination_Port;
	}
	public int getRound_trip() {
		return round_trip;
	}
	public void setRound_trip(int round_trip) {
		this.round_trip = round_trip;
	}
	public int getW_i_Earlist() {
		return w_i_Earlist;
	}
	public void setW_i_Earlist(int w_i_Earlist) {
		this.w_i_Earlist = w_i_Earlist;
	}
	public int getArrival_Time_to_destination() {
		return arrival_Time_to_destination;
	}
	public void setArrival_Time_to_destination(int arrival_Time_to_destination) {
		this.arrival_Time_to_destination = arrival_Time_to_destination;
	}
	public int getPathtime() {
		return pathtime;
	}
	public void setPathtime(int pathtime) {
		this.pathtime = pathtime;
	}
	public String[] getTransshipment_port() {
		return transshipment_port;
	}
	public void setTransshipment_port(String[] transshipment_port) {
		this.transshipment_port = transshipment_port;
	}
	public int getTransshipment_Time() {
		int total_transship_Time = 0;
		for (int i = 0; i < transshipment_Time.length; i++) {
			total_transship_Time += transshipment_Time[i];
		}
		return total_transship_Time;
	}
	public void setTransshipment_Time(int[] transshipment_Time) {
		this.transshipment_Time = transshipment_Time;
	}
	public String[] getPort_Path() {
		return port_Path;
	}
	public void setPort_Path(String[] port_Path) {
		this.port_Path = port_Path;
	}
	public int getPath_ID() {
		return path_ID;
	}
	public void setPath_ID(int path_ID) {
		this.path_ID = path_ID;
	}
	public int getNumberOfArcs() {
		return numberOfArcs;
	}
	public void setNumberOfArcs(int numberOfArcs) {
		this.numberOfArcs = numberOfArcs;
	}
	public int[] getArcs_ID() {
		return arcs_ID;
	}
	public void setArcs_ID(int[] arcs_ID) {
		this.arcs_ID = arcs_ID;
	}
	public int getRequest_ID() {
		return request_ID;
	}
	public void setRequest_ID(int request_ID) {
		this.request_ID = request_ID;
	}
	public String getOrigin_Port() {
		return origin_Port;
	}
	public void setOrigin_Port(String origin_Port) {
		this.origin_Port = origin_Port;
	}
	public int getOrigin_Time() {
		return origin_Time;
	}
	public void setOrigin_Time(int origin_Time) {
		this.origin_Time = origin_Time;
	}
	


}
