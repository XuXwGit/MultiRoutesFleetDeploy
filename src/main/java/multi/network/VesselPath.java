package multi.network;


import lombok.Getter;
import lombok.Setter;

import java.util.List;

/**
* @Author: XuXw
* @Description: Todo
* @DateTime: 2024/12/4 21:54
*/
@Setter
@Getter
public class VesselPath {
	private int vesselPathID;
	private int routeID;

	private int numberOfArcs;
	private int [] arcIDs;
	private List<Arc> arcs;

	private int originTime;
	private int destinationTime;
	private int pathTime;
}
