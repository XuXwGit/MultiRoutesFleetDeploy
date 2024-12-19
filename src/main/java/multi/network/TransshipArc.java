package multi.network;

import lombok.Getter;
import lombok.Setter;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Getter
@Setter
public class TransshipArc extends Arc{
	private int transshipArcID;

	private String port;

	private int transshipTime;

	private int fromRoute;
	private int toRoute;
}
