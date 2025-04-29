package multi.algos.OLP;

import ilog.concert.IloException;
import ilog.concert.IloNumVar;
import ilog.cplex.IloCplex;
import multi.InputData;
import multi.Parameter;

import java.util.List;

/**
* @Author: XuXw
* @Description: online linear programming based dual price algorithm
* @DateTime: 2024/12/5 0:15
*/
public class OnlineAlgoFrame {
    protected InputData in;
    protected Parameter para;
    public OnlineAlgoFrame(InputData in, Parameter para) throws IloException {
        this.in = in;
        this.para = para;

        frame();
    }

    protected IloCplex cplex;
    protected IloNumVar[] xVar;

    protected IloCplex dualCplex;
    protected IloNumVar[] dualVars;
    protected IloNumVar[] betaVar;
    protected IloNumVar[][] gammaVar;

    /**
     * input parameters : A, b, c
     */
    //    List<List<Double>> A;
    //    List<Double> b;
    //    List<Double> c;
    double[][] A;
    double[] b;
    double[] c;

    /**
     * number of constraints and variables
     */
    int nConst;
    int nTime;

    /**
     *  dual price vector p
     */
    // List<Double> p;
    double[] p;

    /**
     * cumulative cost
     */
    List<Double> cumulativeCosts;

    /**
     * output parameters : online/offline solution x
     */
    //    List<Integer> onlineX;
    double[] onlineX;
    //    List<Integer> offlineX;
    double[] offlineX;

    /**
     * competitive ratio : online objective value / offline objective value
     */
    double competitiveRatio;

    protected void frame() throws IloException {

    }

}
