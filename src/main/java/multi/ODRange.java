package multi;
/*
this class include the lower and upper bound
of demand and freight (unit penalty cost)
for a group pairs (origin group and destination group)
 */

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

    public int getOriginGroup() {
        return originGroup;
    }

    public int getDestinationGroup() {
        return destinationGroup;
    }

    public int getDemandLowerBound() {
        return demandLowerBound;
    }

    public int getDemandUpperBound() {
        return demandUpperBound;
    }

    public int getFreightLowerBound() {
        return freightLowerBound;
    }

    public int getFreightUpperBound() {
        return freightUpperBound;
    }

    private final int originGroup;
    private final int destinationGroup;
    private final int demandLowerBound;
    private final int demandUpperBound;
    private final int freightLowerBound;
    private final int freightUpperBound;
}
