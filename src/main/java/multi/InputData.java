package multi;

import java.io.FileWriter;
import java.io.IOException;
import java.util.List;
import java.util.Map;

public class InputData {
	private int timeHorizon;
	private double uncertainDegree;
	private int totalLadenPathsNum;
	private int totalEmptyPathsNum;
	private double[][] sampleScenes;
	private List<Port> portSet;
	private List<Vessel> vesselSet;
	private List<Node> nodeSet;
	private List<TravelingArc> travelingArcSet;
	private List<TransshipArc> transshipArcSet;
	private List<VesselPath> vesselPathSet;
	private List<LadenPath> ladenPathSet;
	private List<EmptyPath> emptyPathSet;
	private List<Request> requestSet;
	private List<ShipRoute> shipRouteSet;
	private List<ContainerPath> containerPathSet;
	private Map<String, int[]> historySolutionSet;

	public InputData() {
	}
	public int getTimeHorizon() {
		return timeHorizon;
	}
	public void setTimeHorizon(int timeHorizon) {
		this.timeHorizon = timeHorizon;
	}
	public double getUncertainDegree() {
		return uncertainDegree;
	}
	public void setUncertainDegree(double uncertainDegree) {
		this.uncertainDegree = uncertainDegree;
	}
	public void setGroupRangeMap(Map<String, ODRange> groupRangeMap) {
		this.groupRangeMap = groupRangeMap;
	}
	public ODRange getGroupRange(int originGroup, int destinationGroup){
		String key = Integer.toString(originGroup) + Integer.toString(destinationGroup);
		return this.groupRangeMap.get(key);
	}
	private Map<String, ODRange> groupRangeMap;

	public List<ContainerPath> getContainerPathSet() {
		return containerPathSet;
	}
	public void setContainerPathSet(List<ContainerPath> containerPath) {
		this.containerPathSet = containerPath;
	}
	public List<ShipRoute> getShipRouteSet() {
		return shipRouteSet;
	}
	public void setShipRoute(List<ShipRoute> shiproute) {
		this.shipRouteSet = shiproute;
	}
	public List<Request> getRequestSet() {
		return requestSet;
	}

	public void setRequestSet(List<Request> requestSet) {
		this.requestSet = requestSet;
	}
	public List<Node> getNodeSet() {
		return nodeSet;
	}
	public void setNodeSet(List<Node> nodeSet) {
		this.nodeSet = nodeSet;
	}
	public List<TravelingArc> getTravelingArcSet() {
		return travelingArcSet;
	}
	public void setTravelingArcSet(List<TravelingArc> travelingArcSet) {
		this.travelingArcSet = travelingArcSet;
	}
	public List<TransshipArc> getTransshipArcSet() {
		return transshipArcSet;
	}
	public void setTransshipArcSet(List<TransshipArc> transshipArcSet) {
		this.transshipArcSet = transshipArcSet;
	}
	public List<VesselPath> getVesselPathSet() {
		return vesselPathSet;
	}
	public void setVesselPathSet(List<VesselPath> vesselPathSet) {
		this.vesselPathSet = vesselPathSet;
	}
	public List<LadenPath> getLadenPathSet() {
		return ladenPathSet;
	}
	public void setLadenPathSet(List<LadenPath> ladenPathSet) {
		this.ladenPathSet = ladenPathSet;
	}
	public List<EmptyPath> getEmptyPathSet() {
		return emptyPathSet;
	}
	public void setEmptyPathSet(List<EmptyPath> emptyPathSet) {
		this.emptyPathSet = emptyPathSet;
	}
	public List<Port> getPortSet() {
		return portSet;
	}

	public void setPortSet(List<Port> port) {
		this.portSet = port;
	}
	public List<Vessel> getVesselSet() {
		return vesselSet;
	}
	public void setVesselSet(List<Vessel> vesselSet) {
		this.vesselSet = vesselSet;
	}
	public Map<String, int[]> getHistorySolutionSet() {
		return historySolutionSet;
	}

	public void setHistorySolutionSet(Map<String, int[]> historySolutionSet) {
		this.historySolutionSet = historySolutionSet;
	}
	public double[][] getSampleScenes() {
		return sampleScenes;
	}

	public void setSampleScenes(double[][] sampleScenes) {
		this.sampleScenes = sampleScenes;
	}
	public void showStatus()
	{
		System.out.print("\n" + "TimeHorizon : " + this.timeHorizon + "\n");
		System.out.print("UncertainDegree : " + this.uncertainDegree + "\n");
		System.out.println("Nodes = " + this.getNodeSet().size() + "\t"
				+ "TravelingArcs = " + this.getTravelingArcSet().size() + "\t"
				+ "TransshipArcs = " + this.getTransshipArcSet().size() + "\t" + "\n"

				+ "ShipRoute = " + this.getShipRouteSet().size() + "\t"
				+ "Ports = " + this.getPortSet().size() + "\t"
				+ "VesselPaths = " + this.getVesselPathSet().size() + "\t"
				+ "VesselTypes = " + this.getVesselSet().size() + "\t" + "\n"

				+ "Requests = " + this.getRequestSet().size() + "\t"
				+ "Paths = " + this.getContainerPathSet().size() + "\t"
		);

		showPathStatus();
	}
	public void writeStatus(FileWriter fileWriter) throws IOException {
		fileWriter.write("\n" + "TimeHorizon : " + this.timeHorizon + "\n");
		fileWriter.write("UncertainDegree : " + this.uncertainDegree + "\n");
		fileWriter.write("Nodes = " + this.getNodeSet().size() + "\t"
				+ "TravelingArcs = " + this.getTravelingArcSet().size() + "\t"
				+ "TransshipArcs = " + this.getTransshipArcSet().size() + "\t" + "\n"

				+ "ShipRoute = " + this.getShipRouteSet().size() + "\t"
				+ "Ports = " + this.getPortSet().size() + "\t"
				+ "VesselPaths = " + this.getVesselPathSet().size() + "\t"
				+ "VesselTypes = " + this.getVesselSet().size() + "\t" + "\n"

				+ "Requests = " + this.getRequestSet().size() + "\t"
				+ "Paths = " + this.getContainerPathSet().size() + "\t"

				+ "\n"
		);
		fileWriter.write("Total LadenPaths = " + totalLadenPathsNum + "\t"
				+ "Total EmptyPaths = " + totalEmptyPathsNum + "\n"
		);
	}

	public void showPathStatus(){
		int totalLadenPaths = 0;
		int totalEmptyPaths = 0;
		for(Request request : this.getRequestSet())
		{
			totalLadenPaths += request.getNumberOfLadenPath();
			totalEmptyPaths += request.getNumberOfEmptyPath();
		}
		System.out.println( "Requests = " + this.getRequestSet().size() + "\t"
				+ "Paths = " + getContainerPathSet().size() + "\t"
				+ "Total LadenPaths = " + totalLadenPaths + "\t"
				+ "Total EmptyPaths = " + totalEmptyPaths
		);
		totalLadenPathsNum = totalLadenPaths;
		totalEmptyPathsNum = totalEmptyPaths;
	}
}
