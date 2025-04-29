package multi.algos.OLP;

import ilog.concert.IloException;
import ilog.concert.IloNumVar;
import ilog.cplex.IloCplex;
import multi.InputData;
import multi.Parameter;

import java.util.Arrays;

/**
 * @Author: xuxw
 * @Description: 在线学习算法
 * @DateTime: 2024/12/6 1:04
 **/
public class ActionHistoryDependentLearningAlgo extends OnlineAlgoFrame{
    public ActionHistoryDependentLearningAlgo(InputData in, Parameter p) throws IloException {
        super(in, p);
    }

    /**
     * # Algorithm 3 Action-History-Dependent Learning Algorithm
     * # 1: Input: A, b, c, delta
     * # 2: Initialize the constraint/remaining resources
     * # 3: Initialize the dual price
     * # 4: for t = 1, ..., n do
     * # 5:     if t < n, solve its dual problem and obtain the dual price
     * # 6:     Observe (rt, at) and set xt
     * # 7:     Update the constraint vector
     * # 8: end for
     * # 9: Output: x = (x1, ..., xn)
     */
    @Override
    protected void frame(){

    }

    /**
     * Action-History-Dependent Learning Algorithm for online resource allocation.
     *
     * @param A     the constraint matrix
     * @param b     the constraint bounds
     * @param c     the objective coefficients
     * @param delta the learning rate parameter
     * @return the competitive ratio, online solution, and offline solution
     * @throws IloException if an error occurs during optimization
     */
    public double AHDL(double[][] A, double[] b, double[] c, double delta) throws IloException {
        int nConst = A.length;
        int nTime = A[0].length;

        // Initialize the constraint/remaining resources
        double[] bRem = Arrays.copyOf(b, b.length);

        // Solve the offline LP to find the optimal offline solution
        IloCplex cplex = new IloCplex();
        IloNumVar[] x = cplex.numVarArray(nTime, 0, 1);
        cplex.addMaximize(cplex.scalProd(c, x));
        for (int i = 0; i < nConst; i++) {
            cplex.addLe(cplex.scalProd(A[i], x), b[i]);
        }
        cplex.solve();
        double[] offlineX = cplex.getValues(x);

        // Initialize decision variables
        double[] onlineX = new double[nTime];
        onlineX[0] = c[0] > 0 ? 1 : 0;

        // Check feasibility for the first decision
        if (anyGreaterThan(multiplyVector(A[0], onlineX[0]), b)) {
            onlineX[0] = 0;
        }

        // Update remaining resources
        bRem = subtractVectors(bRem, multiplyVector(A[0], onlineX[0]));

        // Initialize the dual price
        double[] pHat = new double[nConst];

        // Iterate through the remaining time steps
        for (int t = 1; t < nTime; t++) {
            if (t < nTime - 1) {
                // Solve its dual problem and obtain the dual price
                double[] cc = new double[nConst + t];
                for (int i = 0; i < nConst; i++) {
                    cc[i] = bRem[i] / (nTime - t);
                }
                Arrays.fill(cc, nConst, cc.length, 1.0 / t);

                double[][] AA = new double[t][nConst + t];
                for (int i = 0; i < t; i++) {
                    System.arraycopy(A[i], 0, AA[i], 0, nConst);
                    AA[i][nConst + i] = 1;
                }

                double[] bb = Arrays.copyOf(c, t);

                IloCplex dualCplex = new IloCplex();
                IloNumVar[] dualVars = dualCplex.numVarArray(nConst + t, 0, Double.MAX_VALUE);
                dualCplex.addMinimize(dualCplex.scalProd(cc, dualVars));
                for (int i = 0; i < t; i++) {
                    dualCplex.addGe(dualCplex.scalProd(AA[i], dualVars), bb[i]);
                }
                dualCplex.solve();
                double[] dualValue = dualCplex.getValues(dualVars);
                pHat = Arrays.copyOf(dualValue, nConst);
            }

            // Observe (rt, at) and set xt
            double xTide = c[t] > dotProduct(pHat, A, t) ? 1 : 0;

            // Check feasibility and update decision
            if (anyGreaterThan(addVectors(dotProduct(A, onlineX, t), multiplyVector(A[t], xTide)), b)) {
                onlineX[t] = 0;
            } else {
                onlineX[t] = xTide;
            }

            // Update the constraint vector
            bRem = subtractVectors(bRem, multiplyVector(A[t], onlineX[t]));

            if (anyLessThan(bRem, 0)) {
                break;
            }
        }

        // Compute the competitive ratio : online objective value / offline objective value
        double cr = dotProduct(c, onlineX) / dotProduct(c, offlineX);

        return cr;
    }

    private double dotProduct(double[] a, double[][] A, int t) {
        double result = 0;
        for (int i = 0; i < a.length; i++) {
            result += a[i] * A[i][t];
        }
        return result;
    }

    private double dotProduct(double[] a, double[] b) {
        double result = 0;
        for (int i = 0; i < a.length; i++) {
            result += a[i] * b[i];
        }
        return result;
    }

    private double[] dotProduct(double[][] A, double[] x, int t) {
        double[] result = new double[A.length];
        for (int i = 0; i < A.length; i++) {
            result[i] = A[i][t] * x[i];
        }
        return result;
    }

    private double[] addVectors(double[] a, double[] b) {
        double[] result = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            result[i] = a[i] + b[i];
        }
        return result;
    }

    private double[] subtractVectors(double[] a, double[] b) {
        double[] result = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            result[i] = a[i] - b[i];
        }
        return result;
    }

    private double[] multiplyVector(double[] a, double b) {
        double[] result = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            result[i] = a[i] * b;
        }
        return result;
    }

    private boolean anyGreaterThan(double[] a, double[] b) {
        for (int i = 0; i < a.length; i++) {
            if (a[i] > b[i]) {
                return true;
            }
        }
        return false;
    }

    private boolean anyLessThan(double[] a, double b) {
        for (int i = 0; i < a.length; i++) {
            if (a[i] < b) {
                return true;
            }
        }
        return false;
    }
}
