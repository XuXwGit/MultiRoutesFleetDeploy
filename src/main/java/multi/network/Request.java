package multi.network;


import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

import java.util.List;


/**
* @Author: XuXw
* @Description: 订单/需求 类
* @DateTime: 2024/12/4 21:31
*/
@Slf4j
@Getter
@Setter
public class Request {
	private int requestID;
	private int arrivalTime;

	private double meanDemand;
	private double varianceDemand;

	private double penaltyCost;

	private Port origin;
	private Port destination;

	private String originPort;
	private String destinationPort;
	private int originGroup;
	private int destinationGroup;
	private int earliestPickupTime;
	private int latestDestinationTime;

	private List<ContainerPath> ladenPathSet;
	private int[] ladenPaths;
	private int[] ladenPathIndexes;
	private int numberOfLadenPath;

	private List<ContainerPath> emptyPathSet;
	private int [] emptyPaths;
	private int[] emptyPathIndexes;
	private int numberOfEmptyPath;
}
