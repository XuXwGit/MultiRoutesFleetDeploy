package multi.network;

import lombok.Getter;
import lombok.Setter;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Setter
@Getter
public class TravelingArc extends Arc{
	private int travelingArcID;
	private int routeID;

	private int roundTrip;
	private int travelingTime;
}
