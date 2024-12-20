package multi.network;

import lombok.Getter;
import lombok.Setter;

/**
 * @Author: xuxw
 * @Description: TODO
 * @DateTime: 2024/12/18 16:30
 **/
@Getter
@Setter
public class Arc {
    private int arcID;
    private int originNodeID;
    private int destinationNodeID;
    private String originPort;
    private String destinationPort;
    private Node originNode;
    private Node destinationNode;
    private int originCall;
    private int destinationCall;
    private int originTime;
    private int destinationTime;

    // "Traveling Arc" or "Transship Arc"
    private String arcType;
}
