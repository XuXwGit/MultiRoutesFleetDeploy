package multi.network;


import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;

import java.util.List;


/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
@Getter
@Setter
public class ContainerPath {
	private int containerPathID;
	private String originPort;
	private int originTime;
	private String destinationPort;
	private int destinationTime;
	private int pathTime;

	private String[] transshipmentPort;
	private int[] transshipmentTime;
	private int totalTransshipTime;
	private List<Port> transshipmentPorts;

	
	private int numberOfPath;
	private String [] portPath;
	private List<Port> portsInPath;

	private int numberOfArcs;
	private int [] arcsID;
	private List<Arc> arcs;

	private double pathCost;

	public int getTotalTransshipmentTime()
	{
		int totalTransshipmentTime = 0;
		if(transshipmentPort == null)
		{
			setTotalTransshipTime(0);
		}
		else
		{
			for (int i = 0; i < transshipmentPort.length; i++)
			{
				totalTransshipmentTime += transshipmentTime[i];
			}
			setTotalTransshipTime(totalTransshipmentTime);
		}
		return totalTransshipTime;
	}
	public int getTotalDemurrageTime()
	{
		int totalTransshipmentTime = 0;
		int totalDemurrageTime = 0;
		if(transshipmentPort == null)
		{
			setTotalTransshipTime(0);
			return 0;
		}
		else
		{
			if(transshipmentPort.length != transshipmentTime.length){
				log.info("Error in transshipment port num!");
			}
			for (int i = 0; i < transshipmentPort.length; i++)
			{
				totalTransshipmentTime += transshipmentTime[i];
				if (transshipmentTime[i] > 7){
					totalDemurrageTime += (transshipmentTime[i] - 7);
				}
			}
			setTotalTransshipTime(totalTransshipmentTime);
		}
		return totalDemurrageTime;
	}
}
