package multi.algos.OLP;

import multi.InputData;
import multi.Parameter;
import multi.network.Request;

import java.util.Comparator;
import java.util.List;

/**
 * @Author: xuxw
 * @Description: TODO
 * @DateTime: 2024/12/8 21:31
 **/
public class GenerateOnlineData {
    protected InputData in;
    protected Parameter para;

    public GenerateOnlineData(InputData in, Parameter para) {
        this.in = in;
        this.para = para;
    }

    protected void frame() {
        generateTimeSeries();
    }

    /**
     * @Author Xu Xw
     * @Description Generate the time series data
     * @Date  2024/12/21 0:16
     * @Param
     * @return
     **/
    private void generateTimeSeries() {
        List<Request> sortedRequestSet = in.getRequestSet();
        // Sort the list based on a specific rule, e.g., by request arrival time
        sortedRequestSet.sort(Comparator.comparing(Request::getArrivalTime));

        // set Resource Constraint : the capacity for each transship arc

    }
}
