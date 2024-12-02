package multi;

public class VesselPath {
	private int vesselPath_ID;
	private int routeID;
	private int numberofArcs;
	private int [] arc_ID;
	public int getVesselPathID() {
		return vesselPath_ID;
	}
	public void setVesselPathID(int vesselPath_ID) {
		this.vesselPath_ID = vesselPath_ID;
	}
	public int getRouteID() {
		return routeID;
	}
	public int getOriginTime() {
		return origin_time;
	}

	public void setOriginTime(int origin_time) {
		this.origin_time = origin_time;
	}

	public int getDestinationTime() {
		return destination_time;
	}

	public void setDestinationTime(int destination_time) {
		this.destination_time = destination_time;
	}

	private int origin_time;
	private int destination_time;
	public int getPath_time() {
		return path_time;
	}

	public void setPathTime(int path_time) {
		this.path_time = path_time;
	}

	private int path_time;
	public void setRouteID(int routeID) {
		this.routeID = routeID;
	}
	public int getNumberofArcs() {
		return numberofArcs;
	}
	public void setNumberofArcs(int numberofArcs) {
		this.numberofArcs = numberofArcs;
	}
	public int[] getPathArcIDs() {
		return arc_ID;
	}
	public void setArcID(int[] arc_ID) {
		this.arc_ID = arc_ID;
	}

}
