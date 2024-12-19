package multi.algos.OLP;

import ilog.concert.IloException;
import ilog.concert.IloNumVar;
import ilog.cplex.IloCplex;
import multi.InputData;
import multi.Parameter;

/**
 * @Author: xuxw
 * @Description: TODO
 * @DateTime: 2024/12/6 1:00
 **/
public class SimpleOnlineAlgo extends OnlineAlgoFrame{


    public SimpleOnlineAlgo(InputData in, Parameter p) throws IloException {
        super(in, p);
    }


    /**
     * # Algorithm 1 Simple Online Algorithm
     * # 1: Input: d = b/n
     * # 2: Initialize p1 = 0
     * # 3: for t = 1, ..., n do
     * # 4:        Set xt = {1, rt > at>pt ; 0, rt ≤ at>pt }
     * # 5:        Update dual price with sub gradient method: Compute p[t+1] = p[t]+ γt (a[t] * x[t] − d) ; p[t+1] = p[t+1] ∨ 0
     * # 6: end for
     * # 7: Output: x = (x1, ..., xn)
     */
    @Override
    protected void frame(){
    }


    /**
     * Simple Online Algorithm for online resource allocation.
     *
     * @param A     the constraint matrix
     * @param b     the constraint bounds
     * @param c     the objective coefficients
     * @param gamma the step size for the sub-gradient method
     * @return the competitive ratio, online solution, and offline solution
     * @throws IloException if an error occurs during optimization
     */
    public double SO(double[][] A, double[] b, double[] c, double gamma) throws IloException {
        int nConst = A.length;
        int nTime = A[0].length;

        // Solve the offline LP to find the optimal offline solution
        cplex = new IloCplex();
        IloNumVar[] x = cplex.numVarArray(nTime, 0, 1);
        cplex.addMaximize(cplex.scalProd(c, x));
        for (int i = 0; i < nConst; i++) {
            cplex.addLe(cplex.scalProd(A[i], x), b[i]);
        }
        cplex.solve();
        double[] offlineX = cplex.getValues(x);

        // Input: A, b, c, gamma
        double[] d = new double[nConst];
        for (int i = 0; i < nConst; i++) {
            d[i] = b[i] / nTime;
        }

        // Initialize p1 = 0
        double[] pHat = new double[nConst];
        double[] onlineX = new double[nTime];

        // for t = 1, ..., n do
        for (int t = 0; t < nTime; t++) {
            // Set xt = {1, rt > at>pt ; 0, rt ≤ at>pt }
            double xTide = c[t] > dotProduct(pHat, A, t) ? 1 : 0;

            // Check Stopping Time and update decision
            if (anyGreaterThan(addVectors(dotProduct(A, onlineX, t), multiplyVector(A[t], xTide)), b)) {
                onlineX[t] = 0;
            } else {
                onlineX[t] = xTide;
            }

            // Update dual price with sub gradient method
            pHat = addVectors(pHat, multiplyVector(subtractVectors(multiplyVector(A[t], onlineX[t]), d), gamma));
            pHat = maxVector(pHat, 0);
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

    private double[] maxVector(double[] a, double b) {
        double[] result = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            result[i] = Math.max(a[i], b);
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
}
