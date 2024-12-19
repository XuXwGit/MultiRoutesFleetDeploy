package multi.algos.OLP;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import multi.InputData;
import multi.Parameter;

/**
 * @Author: XuXw
 * @Description: Solve the offline linear programming problem as a benchmark
 * @DateTime: 2024/12/6 1:05
 **/
public class OfflineLinearProgramming extends OnlineAlgoFrame{
    public OfflineLinearProgramming(InputData in, Parameter p) throws IloException {
        super(in, p);

        frame();
    }

    @Override
    protected void frame() throws IloException {
        // Solve the offline LP to find the optimal offline solution
        //        offlineX = solveLP(A, b, c);
    }

    protected double[] solveOfflineLp(double[][] A, double[] b, double[] c) throws IloException {
        int nConst = A.length;
        int nTime = A[0].length;

        // Solve the offline LP to find the optimal offline solution
        cplex = new IloCplex();
        xVar = cplex.numVarArray(nTime, 0, 1);
        cplex.addMaximize(cplex.scalProd(c, xVar));
        for (int i = 0; i < nConst; i++) {
            cplex.addLe(cplex.scalProd(A[i], xVar), b[i]);
        }
        cplex.solve();
        return cplex.getValues(xVar);
    }
}
