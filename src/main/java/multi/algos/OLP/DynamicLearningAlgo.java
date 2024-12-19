package multi.algos.OLP;

import ilog.concert.IloException;
import ilog.concert.IloNumVar;
import ilog.cplex.IloCplex;
import multi.InputData;
import multi.Parameter;

import java.util.Arrays;

/**
 * @Author: xuxw
 * @Description: TODO
 * @DateTime: 2024/12/6 1:02
 **/
public class DynamicLearningAlgo extends OnlineAlgoFrame{
    public DynamicLearningAlgo(InputData in, Parameter p) throws IloException {
        super(in, p);
    }

    /**
     * # Algorithm 2 Dynamic Learning Algorithm
     * # 1: Input: A, b, c, delta
     * # 2: Initialize: Find δ ∈(1, 2] and L > 0 s.t. δ^L=n
     * # 3:Let tk =δ^k, k = 1, 2, ..., L − 1 and tL = n + 1
     * # 4: Initialize decision variable, and Set x1 = ... = xt1 = 0
     * # 5: for k = 1, 2, :::, L − 1 do
     * # 6:     Update dual value p_hat
     * # 7:     for t = tk + 1, ..., tk+1 do
     * # 8:         if the constraints are not violated
     * # 9:             Set xt = 1
     * # 10:         else
     * # 11:             Set xt = 0
     * # 12:     end for
     * # 13: end for
     * # 14: Output: x = (x1, ..., xn)
     */
    @Override
    protected void frame() throws IloException {
        // Solve the offline LP to find the optimal offline solution
        double[] offlineX = new OfflineLinearProgramming(in, para).solveOfflineLp(A, b, c);
    }

    /**
     * Check the input parameters and solve the offline LP to find the optimal offline solution.
     *
     * @param delta the delta parameter
     * @param A     the constraint matrix
     * @param b     the constraint bounds
     * @param c     the objective coefficients
     * @return the competitive ratio, online solution, and offline solution
     * @throws IloException if an error occurs during optimization
     */
    public double checkInputParametersAndSolve(double delta, double[][] A, double[] b, double[] c) throws IloException {
        if (!(1 < delta && delta <= 2)) {
            throw new IllegalArgumentException("delta must be between 1 and 2");
        }
        if (A.length != b.length || A[0].length != c.length) {
            throw new IllegalArgumentException("Dimension mismatch in input matrices");
        }

        nConst = A.length;
        nTime = A[0].length;

        // Initialize: Find δ ∈(1, 2] and L > 0 s.t. δ^L=n
        int L = (int) Math.ceil(Math.log(nTime) / Math.log(delta));

        // Let tk =δ^k, k = 1, 2, ..., L − 1 and tL = n + 1
        int[] timeSteps = new int[L];
        for (int k = 1; k < L; k++) {
            timeSteps[k - 1] = (int) Math.floor(Math.pow(delta, k));
        }
        timeSteps[L - 1] = nTime;

        // Initialize decision variable, and Set x1 = ... = xt1 = 0
        double[] onlineX = new double[nTime];
        Arrays.fill(onlineX, 0, timeSteps[0], 0);

        // for k = 1, 2, ..., L − 1 do
        for (int k = 1; k < L - 1; k++) {
            int tK = timeSteps[k - 1];

            // Update dual value p_hat
            double[] cc = new double[nConst + tK];
            for (int i = 0; i < nConst; i++) {
                cc[i] = b[i] / nTime;
            }
            Arrays.fill(cc, nConst, cc.length, 1.0 / tK);

            double[][] AA = new double[tK][nConst + tK];
            for (int i = 0; i < tK; i++) {
                System.arraycopy(A[i], 0, AA[i], 0, nConst);
                AA[i][nConst + i] = 1;
            }

            double[] bb = Arrays.copyOf(c, tK);

            dualCplex = new IloCplex();
            dualVars = dualCplex.numVarArray(nConst + tK, 0, Double.MAX_VALUE);
            dualCplex.addMinimize(dualCplex.scalProd(cc, dualVars));
            for (int i = 0; i < tK; i++) {
                dualCplex.addGe(dualCplex.scalProd(AA[i], dualVars), bb[i]);
            }
            dualCplex.solve();
            double[] dualValue = dualCplex.getValues(dualVars);
            double[] pHat = Arrays.copyOf(dualValue, nConst);

            // Decide whether to allocate resources at time t
            for (int t = tK + 1; t < timeSteps[k]; t++) {
                double xTide = c[t] > dotProduct(pHat, A[t]) ? 1 : 0;

                // Check Stopping Time and update decision
                if (anyGreaterThan(addVectors(dotProduct(A, onlineX, t), multiplyVector(A[t], xTide)), b)) {
                    onlineX[t] = 0;
                } else {
                    onlineX[t] = xTide;
                }

                if (t == nTime - 1) {
                    break;
                }
            }
        }

        // Compute the competitive ratio : online objective value / offline objective value
        competitiveRatio = dotProduct(c, onlineX) / dotProduct(c, offlineX);

        return competitiveRatio;
    }

    private double dotProduct(double[] a, double[] b) {
        double result = 0;
        for (int i = 0; i < a.length; i++) {
            result += a[i] * b[i];
        }
        return result;
    }

    private double[] dotProduct(double[][] A, double[] x, int t) {
        double result = 0;
        for (int i = 0; i < A.length; i++) {
            result += A[i][t] * x[i];
        }
        return new double[]{result};
    }

    private double[] multiplyVector(double[] a, double b) {
        double[] result = new double[a.length];
        for (int i = 0; i < a.length; i++) {
            result[i] = a[i] * b;
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
    private boolean anyGreaterThan(double[] a, double[] b) {
        for (int i = 0; i < a.length; i++) {
            if (a[i] > b[i]) {
                return true;
            }
        }
        return false;
    }
}
