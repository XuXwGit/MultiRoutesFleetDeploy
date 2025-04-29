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
public class Port {
	private int id;
	private String port;
	private String region;
	private int whetherTrans;
	private int group;
	private int turnOverTime;
	private double ladenDemurralCost;
	private double emptyDemurralCost;
	private double loadingCost;
	private double dischargeCost;
	private double transshipmentCost;
	private double rentalCost;
}
