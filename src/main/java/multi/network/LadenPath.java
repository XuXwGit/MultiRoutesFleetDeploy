package multi.network;

import lombok.Getter;
import lombok.Setter;

import java.util.List;

/**
* @Author: XuXw
* @Description: Todo
* @DateTime: 2024/12/4 21:59
*/
@Getter
@Setter
public class LadenPath{
	private ContainerPath containerPath;

	private int requestID;
	private String originPort;
	private int originTime;
	private String destinationPort;
	private int roundTrip;
	private int earliestSetUpTime;
	private int arrivalTimeToDestination;
	private int pathTime;
	private String[] transshipmentPort;
	private int[] transshipmentTime;
	private String [] portPath;
	private int pathID;
	private int numberOfArcs;
	private int [] arcsID;
	private List<Arc> arcs;
	public int getTransshipmentTime() {
		int total_transship_Time = 0;
		for (int i = 0; i < transshipmentTime.length; i++) {
			total_transship_Time += transshipmentTime[i];
		}
		return total_transship_Time;
	}
}
