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
public class EmptyPath{
	private ContainerPath containerPath;
	private int requestID;
	private String originPortString;
	private Port originPort;
	private int originTime;
	private int numberOfPath;
	private int pathID;
}
