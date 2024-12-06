package multi.model;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.InputData;
import multi.Parameter;
import multi.Request;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Slf4j
public class BasePrimalModel extends BaseModel {
    public BasePrimalModel(InputData in, Parameter p) {
        super();
        this.in = in;
        this.p = p;
        try {
            cplex = new IloCplex();
            publicSetting(cplex);
            // create basic decision and add basic constraints
            frame();
        } catch (IloException e) {
            throw new RuntimeException(e);
        }
    }
    public BasePrimalModel() {
    }

    protected IloIntVar[][] vVar;
    protected List<IloNumVar[]> xVar;
    protected List<IloNumVar[]> yVar;
    protected List<IloNumVar[]> zVar;
    protected IloNumVar[] gVar;

    protected IloRange[] C1;
    protected IloRange[] C2;
    protected IloRange[][] C3;
    private double worstPerformance;
    private double meanPerformance;
    private double worstSecondStageCost;
    private double meanSecondStageCost;
    protected void setVesselConstraint() throws IloException {
        if(FleetType.equals("Homo")){
            setVesselConstraint11_1();
        }
        else if (FleetType.equals("Hetero")) {
            setVesselConstraint11_2();
            // two additional constraint
            setVesselConstraint12();
            setVesselConstraint13();
        }
        else{
            log.info("Error in Fleet type!");
        }
    }
    protected void setVesselConstraint11_1() throws IloException {

        // r \in R
        for (int r = 0; r < p.getShippingRouteSet().length; ++r)
        {
            IloLinearNumExpr left = cplex.linearNumExpr ();

            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h)
            {
                // r(h) == r
                left.addTerm(p.getVesselTypeAndShipRoute()[h][r], vVar[h][r]);
            }
            cplex.addEq(left, 1);
        }
    }
    protected void setVesselConstraint11_2() throws IloException {
        // w
        for (int w = 0; w < p.getVesselPathSet().length; ++w) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h) {
                // r(h) == r
                left.addTerm(1, vVar[h][w]);
            }
            cplex.addEq(left, 1);
        }
    }
    /*
     * Each vessel only assignment once at the same time : Sum_w V[h][w] <= 1
     * */
    protected void setVesselConstraint12() throws IloException {
        for (int h = 0; h < p.getVesselSet().length; h++) {
            IloLinearNumExpr left = cplex.linearNumExpr ();

            for (int r = 0; r < p.getShippingRouteSet().length; r++) {
                int n_r = p.getNumOfRoundTrips()[r];
                for (int w = 0; w < p.getVesselPathSet().length; w++) {
                    if(p.getShipRouteAndVesselPath()[r][w] == 1){
                        for (int i = 0; i < n_r; i++) {
                            if(w + i >= p.getVesselPathSet().length )
                            {
                                break;
                            }
                            if (p.getShipRouteAndVesselPath()[r][w+i] == 1) {
                                left.addTerm(1, vVar[h][w + i]);
                            }
                        }
                        break;
                    }
                }
            }

            cplex.addLe(left, 1);
        }
    }

     /** rotation cycle: V[h][w+n_r(w)] = V[h][w]* */
    protected void setVesselConstraint13() throws IloException {
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            int n_r = p.getNumOfRoundTrips()[r];
            if (w + n_r > p.getVesselPathSet().length - 1) {
                continue;
            }
            for (int h = 0; h < p.getVesselSet().length; h++) {
                if(p.getShipRouteAndVesselPath()[r][w] == 1 && p.getShipRouteAndVesselPath()[r][w+n_r] == 1){
                    IloLinearNumExpr left = cplex.linearNumExpr ();
                    left.addTerm(1, vVar[h][w]);
                    left.addTerm(-1, vVar[h][w+n_r]);
                    cplex.addEq(left, 0);
                }
            }
        }
    }
    public boolean checkVesselConstraint(double[][] vValueDouble) {
        if(FleetType.equals("Homo")){
            if(!checkVesselConstraint11_1(vValueDouble)){
                log.info("Error in Vessel Constraint 1");
                return false;
            }
        }
        else if (FleetType.equals("Hetero")) {
            if(!checkVesselConstraint11_2(vValueDouble)){
                log.info("Error in Vessel Constraint 1");
                return false;
            }
            // two additional constraint
            if(!checkVesselConstraint12(vValueDouble)){
                log.info("Error in Vessel Constraint 2");
                return false;
            }
            if(!checkVesselConstraint13(vValueDouble)){
                log.info("Error in Vessel Constraint 3");
                return false;
            }
        }
        else{
            log.info("Error in Fleet type!");
        }
        return true;
    }
    protected boolean checkVesselConstraint11_1(double[][] vValueDouble)  {
        // r \in R
        for (int r = 0; r < p.getShippingRouteSet().length; ++r)
        {
            double left = 0;
            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h)
            {
                // r(h) == r
                left += (p.getVesselTypeAndShipRoute()[h][r] * vValueDouble[h][r]);
            }
            if (left - 1 > MIPGapLimit || left - 1 < -MIPGapLimit)
                return false;
        }
        return true;
    }
    protected boolean checkVesselConstraint11_2(double[][] vValueDouble)  {
        // w
        for (int w = 0; w < p.getVesselPathSet().length; ++w) {
            double left = 0;
            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h) {
                // r(h) == r
                left += (1 * vValueDouble[h][w]);
            }
            if (left - 1 > MIPGapLimit || left - 1 < -MIPGapLimit)
                return false;
        }
        return true;
    }

    /* * Each vessel only assignment once at the same time : Sum_w V[h][w] <= 1* */
    protected boolean checkVesselConstraint12(double[][] vValueDouble) {
        for (int h = 0; h < p.getVesselSet().length; h++) {
            double left = 0;
            for (int r = 0; r < p.getShippingRouteSet().length; r++) {
                int n_r = p.getNumOfRoundTrips()[r];
                for (int w = 0; w < p.getVesselPathSet().length; w++) {
                    if(p.getShipRouteAndVesselPath()[r][w] == 1){
                        for (int i = 0; i < n_r; i++) {
                            if(w + i >= p.getVesselPathSet().length )
                            {
                                break;
                            }
                            if (p.getShipRouteAndVesselPath()[r][w+i] == 1) {
                                left += (1 * vValueDouble[h][w + i]);
                            }
                        }
                        break;
                    }
                }
            }

            if (left  > 1 )
                return false;
        }
        return true;
    }

    /* * rotation cycle: V[h][w+n_r(w)] = V[h][w] * */
    protected boolean checkVesselConstraint13(double[][] vValueDouble) {
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            int n_r = p.getNumOfRoundTrips()[r];
            if (w + n_r > p.getVesselPathSet().length - 1) {
                continue;
            }
            for (int h = 0; h < p.getVesselSet().length; h++) {
                if(p.getShipRouteAndVesselPath()[r][w] == 1 && p.getShipRouteAndVesselPath()[r][w+n_r] == 1){
                    double left = 0;
                    left += (1 * vValueDouble[h][w]);
                    left += (-1 * vValueDouble[h][w+n_r]);
                    if (left > MIPGapLimit || left < -MIPGapLimit)
                        return false;
                }
            }
        }
        return true;
    }
    protected void setDemandConstraint(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar, IloNumVar[] gVar, double[] uValue) throws IloException {
        //∀i∈I
        for (int i = 0; i < p.getDemand().length; ++i) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            Request od = in.getRequestSet().get(i);
            //φ
            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                left.addTerm(1, xVar.get(i)[k]);
                left.addTerm(1, yVar.get(i)[k]);
            }

            left.addTerm(1, gVar[i]);

            String ConstrName = "C1(" + (i + 1) + ")";
            cplex.addEq(left, p.getDemand()[i] +
                    p.getMaximumDemandVariation()[i] * uValue[i], ConstrName);
        }
    }
    protected void setCapacityConstraint() throws IloException  {
        setCapacityConstraint(xVar, yVar, zVar);
    }
    protected void setCapacityConstraint(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar, List<IloNumVar[]> zVar) throws IloException  {
        C2 = new IloRange[p.getTravelingArcsSet().length];

        // ∀<n,n'>∈A'
        for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            // i∈I
            for (int i = 0; i < p.getDemand().length; ++i) {
                Request od = in.getRequestSet().get(i);

                // φ
                for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                    int j = od.getLadenPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                    left.addTerm(p.getArcAndPath()[nn][j], yVar.get(i)[k]);
                }

                //θ
                for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                    int j = od.getEmptyPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                }
            }

            // r \in R
            // w \in \Omega
            // r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
            for(int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(FleetType.equals("Homo")){
                    // h \in H_r
                    // r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
                    for(int h = 0; h < p.getVesselSet().length; ++h){
                        left.addTerm(-p.getVesselTypeAndShipRoute()[h][r]
                                        * p.getShipRouteAndVesselPath()[r][w]
                                        * p.getArcAndVesselPath()[nn][w]
                                        * p.getVesselCapacity()[h],
                                vVar[h][r]
                        );
                    }
                } else if (FleetType.equals("Hetero")) {
                    // h \in H
                    for(int h = 0; h < p.getVesselSet().length; ++h)
                    {
                        left.addTerm(- p.getArcAndVesselPath()[nn][w]
                                        * p.getVesselCapacity()[h],
                                vVar[h][w]
                        );
                    }
                }
                else{
                    log.info("Error in Fleet type!");
                }
            }
            String ConstrName = "C3" + "(" + (nn + 1) + ")";
            C2[nn] = cplex.addLe(left, 0, ConstrName);
        }
    }
    protected void setEmptyConservationConstraint() throws IloException {
        setEmptyConservationConstraint(xVar, zVar);
    }
    protected void setEmptyConservationConstraint(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar) throws IloException {
        if(WhetherUseMultiThreads){
            //long start = System.currentTimeMillis();
            setEmptyConservationConstraintWithMultiThread(xVar, zVar);
            //log.info("Set Empty Conservation Constraint Time(Multi Threads) = "+ (System.currentTimeMillis() - start));
        } else {
            //long start = System.currentTimeMillis();
            setEmptyConservationConstraintSingleThread(xVar, zVar);
            //log.info("Set Empty Conservation Constraint Time = "+ (System.currentTimeMillis() - start));
        }
    }
    protected void setEmptyConservationConstraintSingleThread(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar) throws IloException{
        C3 = new IloRange[p.getPortSet().length][p.getTimePointSet().length];
        // p \in P
        for (int pp = 0; pp < p.getPortSet().length; ++pp)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();
            // t \in T
            for (int t = 1; t < p.getTimePointSet().length; ++t)
            {
                // i \in I
                for (int i = 0; i < p.getDemand().length; ++i) {
                    Request od = in.getRequestSet().get(i);

                    // Input Z flow:
                    // (item1)
                    // o(i) == p
                    if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                        //θi
                        for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                            int j = od.getEmptyPathIndexes()[k];

                            // <n,n'> ∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                // p(n') == p
                                // 1<= t(n')<= t
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() == t) {
                                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                }
                            }
                        }
                    }

                    // Input flow X
                    // item2
                    // d(i) == p
                    if (p.getDestinationOfDemand()[i].equals(p.getPortSet()[pp])) {
                        for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                            int j = od.getLadenPathIndexes()[k];

                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                // p(n‘)∈p
                                // 1 <= t(n')<= t-sp
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() == t - p.getTurnOverTime()[pp]) {
                                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                }
                            }
                        }
                    }

                    //Output  flow X
                    // item3
                    // o(i) == p
                    if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                        // φi
                        for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                            int j = od.getLadenPathIndexes()[k];

                            // <n.n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                //p(n) == p
                                // t(n) <= t
                                if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                    left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                }
                            }
                        }
                    }


                    // Output Flow Z
                    // item4
                    // θ
                    for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                        int j = od.getEmptyPathIndexes()[k];

                        // <n,n'>∈A'
                        for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                            // p(n) == p
                            // t(n) <= t
                            if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                    && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                            }
                        }
                    }
                }
                String ConstrName = "C3(" + (pp + 1) + ")(" + (t) + ")";
                C3[pp][t] = cplex.addGe(left, -p.getInitialEmptyContainer()[pp], ConstrName);
            }
        }
    }
    protected void setEmptyConservationConstraintWithMultiThread(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar) throws IloException	{

        ExecutorService executor = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());

        C3 = new IloRange[p.getPortSet().length][p.getTimePointSet().length];

        IloLinearNumExpr[][] leftItems = new IloLinearNumExpr[p.getPortSet().length][p.getTimePointSet().length];
        // p \in P
        for (int portIndex = 0; portIndex < p.getPortSet().length; ++portIndex)
        {
            final int pp = portIndex;
            // t \in T
            for (int tt = 1; tt < p.getTimePointSet().length; ++tt)
            {
                final int t = tt;

                //// parallel
                executor.submit(() -> {

                    IloLinearNumExpr left;
                    try {
                        left = cplex.linearNumExpr();
                    } catch (IloException e) {
                        throw new RuntimeException(e);
                    }
                    // i \in I
                    for (int i = 0; i < p.getDemand().length; ++i) {
                        Request od = in.getRequestSet().get(i);

                        // Input Z flow:
                        // (item1)
                        // o(i) == p
                        if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                            //θi
                            for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                                int j = od.getEmptyPathIndexes()[k];

                                // <n,n'> ∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    // p(n') == p
                                    // 1<= t(n')<= t
                                    if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getDestinationTime() == t) {
                                        try {
                                            left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }

                        // Input flow X
                        // item2
                        // d(i) == p
                        if (p.getDestinationOfDemand()[i].equals(p.getPortSet()[pp])) {
                            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                                int j = od.getLadenPathIndexes()[k];

                                // <n,n'>∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    // p(n‘)∈p
                                    // 1 <= t(n')<= t-sp
                                    if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getDestinationTime() == t - p.getTurnOverTime()[pp]) {
                                        try {
                                            left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }

                        //Output  flow X
                        // item3
                        // o(i) == p
                        if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                            // φi
                            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                                int j = od.getLadenPathIndexes()[k];

                                // <n.n'>∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    //p(n) == p
                                    // t(n) == t
                                    if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                        try {
                                            left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }


                        // Output Flow Z
                        // item4
                        // θ
                        for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                            int j = od.getEmptyPathIndexes()[k];

                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                // p(n) == p
                                // t(n) == t
                                if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                    try {
                                        left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                    } catch (IloException e) {
                                        throw new RuntimeException(e);
                                    }
                                }
                            }
                        }
                    }

                    leftItems[pp][t] = left;
                });
            }
        }

        executor.shutdown();

        try {
            executor.awaitTermination(Long.MAX_VALUE, TimeUnit.NANOSECONDS);
        } catch (InterruptedException e) {
            // 处理中断异常
            throw new RuntimeException(e);
        }

        for (int pp = 0; pp < p.getPortSet().length; pp++) {
            IloLinearNumExpr left = cplex.linearNumExpr();
            for (int t = 1; t < p.getTimePointSet().length; ++t){
                left.add(leftItems[pp][t]);
                String ConstrName = "C3(" + (pp + 1) + ")(" + (t) + ")";
                C3[pp][t] = cplex.addGe(left, -p.getInitialEmptyContainer()[pp], ConstrName);
            }
        }
    }
    protected double operationCost;
    public double getOperationCost() {
        return operationCost;
    }

    public void setOperationCost(double operationCost) {
        this.operationCost = operationCost;
    }
    protected double getOperationCost(int[][] vValue){
        double operation_cost = 0;
        for (int h = 0; h < p.getVesselSet().length; ++h)
        {
            for (int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                // r(��) == r
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(FleetType.equals("Homo")) {
                    // vesselTypeAndShipRoute == 1 : r(h) = r
                    operation_cost += (p.getVesselTypeAndShipRoute()[h][r]
                            * p.getShipRouteAndVesselPath()[r][w]
                            * p.getVesselOperationCost()[h]
                            * vValue[h][r]);
                }
                else if (FleetType.equals("Hetero")) {
                    operation_cost += (p.getVesselOperationCost()[h]
                            * vValue[h][w]);
                }
            }
        }
        return operation_cost;
    }

    protected int[][] vVarValue;
    public int[][] getVVarValue() {
        return vVarValue;
    }
    public void setVVarValue(int[][] vVarValue) {
        this.vVarValue = vVarValue;
    }
    private int[] solution;
    public int[] getSolution(){
        return solution;
    }
    protected void setSolution(int[] solution){
        this.solution = solution;
    }
    public double getWorstPerformance() {
        return worstPerformance;
    }
    protected void setWorstPerformance(double worstPerformance) {
        this.worstPerformance = worstPerformance;
    }
    public double getMeanPerformance() {
        return meanPerformance;
    }

    public void setMeanPerformance(double meanPerformance) {
        this.meanPerformance = meanPerformance;
    }
    public double getWorstSecondStageCost() {
        return worstSecondStageCost;
    }

    protected void setWorstSecondStageCost(double worstSecondStageCost) {
        this.worstSecondStageCost = worstSecondStageCost;
    }
    public double getMeanSecondStageCost() {
        return meanSecondStageCost;
    }

    protected void setMeanSecondStageCost(double meanSecondStageCost) {
        this.meanSecondStageCost = meanSecondStageCost;
    }

    public IloCplex.Status getSolveStatus() throws IloException {
        return cplex.getStatus();
    }
    public String getSolveStatusString() throws IloException {
        if (cplex.getStatus() == IloCplex.Status.Optimal)
            return "Optimal";
        else if (cplex.getStatus() == IloCplex.Status.Feasible) {
            return "Feasible";
        }
        else if (cplex.getStatus() == IloCplex.Status.Infeasible) {
            return "Infeasible";
        }
        else if (cplex.getStatus() == IloCplex.Status.Bounded) {
            return "Bounded";
        }
        return "Others";
    }
    protected void SetVesselDecisionVars() throws IloException {
        // first-stage variable :
        // v[h][r] : binary variable ���� whether vessel type h is assigned to shipping route r
        // eta : auxiliary decision variable ���� the upper bound of second-stage objective under all scene
        if(FleetType.equals("Homo")){
            vVar =new IloIntVar [p.getVesselSet().length] [p.getShippingRouteSet().length];
            vVarValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
        } else if (FleetType.equals("Hetero")) {
            vVar =new IloIntVar [p.getVesselSet().length] [p.getVesselPathSet().length];
            vVarValue = new int[p.getVesselSet().length] [p.getVesselPathSet().length];
        }
        else{
            log.info("Error in Fleet type!");
        }

        // V[h][r]
        String varName;
        for(int h=0;h<p.getVesselSet().length;++h)
        {
            if(FleetType.equals("Homo")){
                for(int r = 0; r<p.getShippingRouteSet().length; r++)
                {
                    varName = "V("+(p.getVesselSet()[h])+")("+(p.getShippingRouteSet()[r])+")";
                    vVar[h][r]=cplex.boolVar(varName);
                }
            } else if (FleetType.equals("Hetero")) {
                for(int w = 0; w < p.getVesselPathSet().length; ++w)
                {
                    varName = "V("+(p.getVesselSet()[h])+")("+(p.getVesselPathSet()[w])+")";
                    vVar[h][w]=cplex.boolVar(varName);
                }
            }
        }
    }
    protected void SetRequestDecisionVars(List<IloNumVar[]> xVar,  List<IloNumVar[]> yVar, List<IloNumVar[]> zVar, IloNumVar[] gVar) throws IloException {
        String varName;

        for (int i = 0; i < p.getDemand().length; i++) {
            Request od = in.getRequestSet().get(i);

            IloNumVar[] xxxVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] yyyVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] zzzVar_k = new IloNumVar[od.getNumberOfEmptyPath()];

            xVar.add(xxxVar_k);
            yVar.add(yyyVar_k);
            zVar.add(zzzVar_k);

            for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
                varName = "x(" + (i + 1) + ")";
                xVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
                varName = "y(" + (i + 1) + ")";
                yVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
            }
            for (int k = 0; k < od.getNumberOfEmptyPath(); k++) {
                varName = "z(" + (i + 1) + ")";
                zVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
            }

            varName = "g(" + (i + 1) + ")";
            gVar[i] = cplex.numVar(0, Integer.MAX_VALUE, varName);
        }
    }
    protected void SetRequestDecisionVars() throws IloException {
        xVar = new ArrayList<>();
        yVar = new ArrayList<>();
        zVar = new ArrayList<>();
        gVar = new IloNumVar[p.getDemand().length];
        SetRequestDecisionVars(xVar, yVar, zVar, gVar);
    }
    protected IloLinearNumExpr GetVesselOperationCostObj(IloLinearNumExpr Obj) throws IloException {
        // add fixed operating cost to maintain shipping route
        // w
        // h�ʦ�
        for (int h = 0; h < p.getVesselSet().length; ++h)
        {
            for (int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                // r(��) == r
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(FleetType.equals("Homo")) {
                    // vesselTypeAndShipRoute == 1 : r(h) = r
                    Obj.addTerm(p.getVesselTypeAndShipRoute()[h][r]
                                    * p.getShipRouteAndVesselPath()[r][w]
                                    * p.getVesselOperationCost()[h]
                            , vVar[h][r]);
                }
                else if (FleetType.equals("Hetero")) {
                    Obj.addTerm(p.getVesselOperationCost()[h]
                            , vVar[h][w]);
                }
            }
        }

        return Obj;
    }
    protected IloLinearNumExpr GetRequestTransCostObj(
                                                        IloLinearNumExpr Obj,
                                                        List<IloNumVar[]> xVar,  List<IloNumVar[]> yVar,
                                                        List<IloNumVar[]> zVar, IloNumVar[] gVar)
            throws IloException{
        // i \in I
        for(int i = 0; i < p.getDemand().length; ++i){
            // item2 : Penalty Cost of unsatisfied Demand
            Obj.addTerm(p.getPenaltyCostForDemand()[i], gVar[i]);

            Request od = in.getRequestSet().get(i);

            // \phi \in \\Phi_i
            for(int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                int j = od.getLadenPathIndexes()[k];
                // item3 : Demurrage of self-owned and leased containers and Rental cost on laden paths
                Obj.addTerm(p.getLadenPathCost()[j], xVar.get(i)[k]);
                Obj.addTerm(p.getLadenPathCost()[j], yVar.get(i)[k]);
                Obj.addTerm(p.getRentalCost() * p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
            }

            // \theta \in \\Theta_i
            for(int k = 0; k < od.getNumberOfEmptyPath(); ++k)
            {
                int j = od.getEmptyPathIndexes()[k];
                Obj.addTerm(p.getEmptyPathCost()[j], zVar.get(i)[k]);
            }
        }

        return Obj;
    }
    protected IloLinearNumExpr GetRequestTransCostObj(IloLinearNumExpr Obj) throws IloException{
        return GetRequestTransCostObj(Obj, xVar, yVar, zVar, gVar);
    }
    public void setInitialSolution(int[][] vVarValue) throws IloException {
        int m = vVar.length;
        int n = vVar[0].length;
        IloNumVar[] startVar = new IloNumVar[m * n];
        double[] startVal = new double[m * n];
        for (int i = 0, idx = 0; i < m; ++i)
            for (int j = 0; j < n; ++j) {
                startVar[idx] = vVar[i][j];
                startVal[idx] = vVarValue[i][j];
                ++idx;
            }
        cplex.addMIPStart(startVar, startVal);
    }
    protected void writeSolution(FileWriter fileWriter){
        try {
            fileWriter.write("Vessel Solution:\t");
            for (int r = 0; r < getSolution().length; r++) {
                if(r!=0){
                    fileWriter.write(",");
                }
                fileWriter.write(getSolution()[r]);
            }
            fileWriter.write("\n");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    private void setHomoVesselSolution() throws IloException {
        int[][]  vvv =new int [p.getVesselSet().length][p.getShippingRouteSet().length];
        int[] solution = new int[p.getShippingRouteSet().length];
        for (int r = 0; r < p.getShippingRouteSet().length; ++r) {
            for (int h = 0; h < p.getVesselSet().length; h++) {
                double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
                if(cplex.getValue(vVar[h][r]) >= 1 - tolerance){
                    vvv[h][r]= 1;
                    solution[r] = h + 1;
                }
            }
        }
        setVVarValue(vvv);
        setSolution(solution);
    }
    private void setHeteroVesselSolution() throws IloException {
        int[][] vvv =new int [p.getVesselSet().length][p.getVesselPathSet().length];
        int[] solution = new int[p.getVesselPathSet().length];
        for(int w=0; w<p.getVesselPathSet().length; ++w) {
            for (int h = 0; h < p.getVesselSet().length; h++) {
                double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
                if(cplex.getValue(vVar[h][w]) >= 1 - tolerance){
                    vvv[h][w]= 1;
                    solution[w] = h + 1;
                }
            }
        }
        setVVarValue(vvv);
        setSolution(solution);
    }
    protected void setVVarsSolution() throws IloException {
        if(FleetType.equals("Homo")){
            setHomoVesselSolution();
        } else if (FleetType.equals("Hetero")) {
            setHeteroVesselSolution();
        }
        else{
            log.info("Error in Fleet type!");
        }
    }
    protected double calculateSampleMeanPerformance(int[][] vValue) throws IOException, IloException {
        String filename = Model + "-R"+ in.getShipRouteSet().size()
                + "-T" + p.getTimeHorizon() + "-"+ FleetType
                + "-Tau" + p.getTau()
                + "-U" + p.getUncertainDegree()
                + "-S" + randomSeed
                + "-SampleTestResult"+ ".txt";
        File file = new File(RootPath + AlgoLogPath + filename);
        if (!file.exists()) {
            try {
                file.createNewFile();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }

        FileWriter filewriter = new FileWriter(file, false);
        filewriter.write("Sample\tOperationCost\t " +
                "TotalTransCost\t LadenCost\t " +
                "EmptyCost\t RentalCost\t " +
                "PenaltyCost\tTotalCost\n");
        filewriter.flush();

        double mp_operation_cost = getOperationCost(vValue);


        double[] sample_sub_opera_costs = new double[numSampleScenes];
        double[] sample_laden_costs = new double[numSampleScenes];
        double[] sample_empty_costs = new double[numSampleScenes];
        double[] sample_rental_costs = new double[numSampleScenes];
        double[] sample_penalty_costs = new double[numSampleScenes];

        double sum_sub_opera_costs = 0;
        double worst_total_cost = 0;
        double worst_second_cost = 0;
        SubProblem sp = new SubProblem(in, p, vValue);
        for (int sce = 0; sce < numSampleScenes; sce++) {
            sp.changeDemandConstraintCoefficients(p.getSampleScenes()[sce]);
            sp.solveModel();

            sample_sub_opera_costs[sce] = sp.getTotalCost();
            sample_laden_costs[sce] = sp.getLadenCost();
            sample_empty_costs[sce] = sp.getEmptyCost();
            sample_rental_costs[sce] = sp.getRentalCost();
            sample_penalty_costs[sce] = sp.getPenaltyCost();

            sum_sub_opera_costs += sp.getTotalCost();
            if((mp_operation_cost + sample_sub_opera_costs[sce]) > worst_total_cost){
                worst_total_cost = mp_operation_cost + sample_sub_opera_costs[sce];
                worst_second_cost = sample_sub_opera_costs[sce];
            }

            drawProgressBar((sce) * 100 / numSampleScenes);

            filewriter.write(sce + "\t" + mp_operation_cost + "\t"
                    + sample_sub_opera_costs[sce] + "\t"
                    + sample_laden_costs[sce] + "\t"
                    + sample_empty_costs[sce] + "\t"
                    + sample_rental_costs[sce] + "\t"
                    + sample_penalty_costs[sce] + "\t"
                    + (mp_operation_cost + sample_sub_opera_costs[sce])
                    + "\n");
            filewriter.flush();
        }
        this.setWorstPerformance(worst_total_cost);
        this.setWorstSecondStageCost(worst_second_cost);
        this.setMeanPerformance(mp_operation_cost + sum_sub_opera_costs / numSampleScenes);
        this.setMeanSecondStageCost(sum_sub_opera_costs / numSampleScenes);

        filewriter.close();

        return mp_operation_cost + sum_sub_opera_costs/ numSampleScenes;
    }
    protected double calculateMeanPerformance() throws IOException, IloException {
        log.info("Calculating Mean Performance ...");
        if(UseHistorySolution)
        {
            if((in.getHistorySolutionSet().get(ModelName) != (null))) {
                calculateSampleMeanPerformance(solutionToVValue(in.getHistorySolutionSet().get(ModelName)));
            }
        }else {
            calculateSampleMeanPerformance(this.getVVarValue());
        }
        log.info("MeanPerformance = " + getMeanPerformance());
        log.info("WorstPerformance = "+ getWorstPerformance());
        log.info("WorstSecondStageCost = " + getWorstSecondStageCost());
        log.info("MeanSecondStageCost = " + getMeanSecondStageCost());
        log.info("AlgoObjVal = "+ getObjVal());
        return meanPerformance;
    }
    public int[][] solutionToVValue(int[] solution){
        int[][] vValue = new int[0][];
        if(FleetType.equals("Homo")){
            vValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
            for(int r = 0; r<p.getShippingRouteSet().length; r++) {
                vValue[solution[r] - 1][r] = 1;
            }
        } else if (FleetType.equals("Hetero")) {
            vValue = new int[p.getVesselSet().length][p.getVesselPathSet().length];
            for(int w=0;w<p.getVesselPathSet().length;++w) {
                vValue[solution[w]-1][w] = 1;
            }
        }
        else{
            log.info("Error in Fleet type!");
        }

        return vValue;
    }
    protected  void printSolution(){
        log.info("Objective ="+String.format("%.2f", getObjVal()));
        System.out.print("Vessel Decision vVar : ");
        for(int r = 0; r<p.getShippingRouteSet().length; r++) {
            System.out.print(p.getShippingRouteSet()[r]);
            System.out.print(":");

            if(FleetType.equals("Homo")){
                for(int h=0;h<p.getVesselSet().length;++h)
                {
                    if(vVarValue[h][r] != 0)
                    {
                        System.out.print(p.getVesselSet()[h]+"\t");
                    }
                }
            } else if (FleetType.equals("Hetero")) {
                for(int w=0;w<p.getVesselPathSet().length;++w){
                    if (p.getShipRouteAndVesselPath()[r][w] != 1)
                    {
                        continue;
                    }
                    for(int h=0;h<p.getVesselSet().length;++h)
                    {
                        if(vVarValue[h][w] != 0 && p.getShipRouteAndVesselPath()[r][w] == 1)
                        {
                            System.out.print(p.getVesselPathSet()[w]+"(" + p.getVesselSet()[h]+")\t");
                        }
                    }
                }
            }
            else{
                log.info("Error in Fleet type!");
            }
        }
    }
}

