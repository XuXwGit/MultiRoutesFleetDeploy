package multi.algos.OLP;

import multi.InputData;
import multi.Parameter;

import java.util.List;

/**
* @Author: XuXw
* @Description: online linear programming based dual price algorithm
* @DateTime: 2024/12/5 0:15
*/
public class OnlineAlgo {
    protected InputData in;
    protected Parameter p;
    public OnlineAlgo(InputData in, Parameter p) {
        this.in = in;
        this.p = p;
    }


    /**
     * input parameters : A, b, c
     */
    List<List<Integer>> A;
    List<Double> b;
    List<Double> c;

    private void frame(){

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
    private void SimpleOnlineAlgo(){

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
    private void DynamicLearningAlgo(){

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
    private void ActionHistoryDependentLearningAlgo(){

    }
}
