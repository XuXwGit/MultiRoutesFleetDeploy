package multi.network;

import lombok.Getter;
import lombok.Setter;

import java.util.List;
import java.util.Map;


/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Getter
@Setter
public class ShipRoute {
	private int shipRouteID;

	private int cycleTime;

	private int numRoundTrips;
	private int numberOfPorts;
	private String [] ports;

	/**
	 *  key : port call index
	 *	value : Port
	* */
	private Map<Integer, Port> portCalls;
	private int numberOfCall;
	private String [] portsOfCall;
	private int[] timePointsOfCall;

	private int numVesselPaths;
	private List<VesselPath> vesselPaths;

	public ShipRoute() {
	}

	public int getCallIndexOfPort(String port){
		for (int p = 0; p < this.numberOfCall - 1; p++) {
			if(port.equals(this.getPortsOfCall()[p])  )
			{
				return p;
			}
		}
		return -1;
	}
}
