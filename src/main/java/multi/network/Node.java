package multi.network;

import lombok.Getter;
import lombok.Setter;


/**
* @Author: XuXw
* @Description: Todo
* @DateTime: 2024/12/4 22:00
*/
@Getter
@Setter
public class Node {
	private String portString;
	private int nodeID;
	private int route;
	private int call;
	private int roundTrip;
	private int time;
	private Port port;
}
