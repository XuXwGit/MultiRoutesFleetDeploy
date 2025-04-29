package multi;

import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import multi.network.*;

import java.io.FileWriter;
import java.io.IOException;
import java.util.List;
import java.util.Map;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
@Getter
@Setter
public class InputData {
	private int timeHorizon;
	private double uncertainDegree;
	private int totalLadenPathsNum;
	private int totalEmptyPathsNum;
	private double[][] sampleScenes;
	private List<Scenario> scenarios;
	private Map<String, Port> portSet;
	private List<VesselType> vesselTypeSet;
	private Map<Integer, Node> nodeSet;
	private Map<Integer, Arc> arcSet;
	private List<TravelingArc> travelingArcSet;
	private List<TransshipArc> transshipArcSet;
	private List<VesselPath> vesselPathSet;
	private List<LadenPath> ladenPathSet;
	private List<EmptyPath> emptyPathSet;
	private List<Request> requestSet;
	private Map<Integer, ShipRoute> shipRouteSet;
	private List<ContainerPath> containerPaths;
	private Map<Integer, ContainerPath> containerPathSet;
	private Map<String, int[]> historySolutionSet;

	public InputData() {
	}
	public ODRange getGroupRange(int originGroup, int destinationGroup){
		String key = originGroup + Integer.toString(destinationGroup);
		return this.groupRangeMap.get(key);
	}
	private Map<String, ODRange> groupRangeMap;
	public void showStatus()
	{
		log.info("\n" + "TimeHorizon : " + this.timeHorizon + "\n");
		log.info("UncertainDegree : " + this.uncertainDegree + "\n");
		log.info("Nodes = " + this.getNodeSet().size() + "\t"
				+ "TravelingArcs = " + this.getTravelingArcSet().size() + "\t"
				+ "TransshipArcs = " + this.getTransshipArcSet().size() + "\t" + "\n"

				+ "ShipRoute = " + this.getShipRouteSet().size() + "\t"
				+ "Ports = " + this.getPortSet().size() + "\t"
				+ "VesselPaths = " + this.getVesselPathSet().size() + "\t"
				+ "VesselTypes = " + this.getVesselTypeSet().size() + "\t" + "\n"

				+ "Requests = " + this.getRequestSet().size() + "\t"
				+ "Paths = " + this.getContainerPaths().size() + "\t"
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
				+ "VesselTypes = " + this.getVesselTypeSet().size() + "\t" + "\n"

				+ "Requests = " + this.getRequestSet().size() + "\t"
				+ "Paths = " + this.getContainerPaths().size() + "\t"

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
		log.info( "Requests = " + this.getRequestSet().size() + "\t"
				+ "Paths = " + getContainerPaths().size() + "\t"
				+ "Total LadenPaths = " + totalLadenPaths + "\t"
				+ "Total EmptyPaths = " + totalEmptyPaths
		);
		totalLadenPathsNum = totalLadenPaths;
		totalEmptyPathsNum = totalEmptyPaths;
	}
}
