package multi.network;
/*
this class include the lower and upper bound
of demand and freight (unit penalty cost)
for a group pairs (origin group and destination group)
 */


import lombok.Getter;
import lombok.Setter;


/**
* @Author: XuXw
* @Description: TODO
* @DateTime: 2024/12/4 22:06
*/
@Getter
@Setter
public class ODRange {
    public ODRange(int originGroup,
                   int destinationGroup,
                   int demandLowerBound,
                   int demandUpperBound,
                   int freightLowerBound,
                   int freightUpperBound) {
        this.originGroup = originGroup;
        this.destinationGroup = destinationGroup;
        this.demandLowerBound = demandLowerBound;
        this.demandUpperBound = demandUpperBound;
        this.freightLowerBound = freightLowerBound;
        this.freightUpperBound = freightUpperBound;
    }

    private final int originGroup;
    private final int destinationGroup;
    private final int demandLowerBound;
    private final int demandUpperBound;
    private final int freightLowerBound;
    private final int freightUpperBound;
}
