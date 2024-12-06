package multi.model;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.model.BaseModel;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

@Slf4j
public class BaseDualModel extends BaseModel {
    protected int tau;
    protected IloLinearNumExpr ObjExpr;

    public BaseDualModel(InputData in, int tau, Parameter p) {
        super();
        this.tau = tau;
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

    public BaseDualModel() {
    }

    private Scenario Scene;
    protected void setScene(Scenario Scene) {
        this.Scene = Scene;
    }
    public Scenario getScene()	{
        return Scene;
    }

    // cplex model/variables/objective
    protected IloNumVar[] alphaVar;
    protected IloNumVar[] betaVar;
    protected IloNumVar[][] gammaVar;
    protected IloObjective objective;
    private List<IloRange[]> C1;
    private List<IloRange[]> C2;
    private List<IloRange[]> C3;
    private IloRange[] C4;

    // create basic decision and add basic constraints
    protected void setDualDecisionVars() throws IloException {
        // create dual variable
        // α[i]
        //β[nn']
        //γ[p][t]
        alphaVar =new IloNumVar [p.getDemand().length];
        betaVar =new IloNumVar [p.getTravelingArcsSet().length];
        gammaVar=new IloNumVar[p.getPortSet().length][p.getTimePointSet().length];

        String varName;
        for(int i=0;i<p.getDemand().length;i++)
        {
            varName = "alpha(" + i +")";
            alphaVar[i]=cplex.numVar(Integer.MIN_VALUE, p.getPenaltyCostForDemand()[i], varName);
      }

        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
        {
            // beta <= 0
            varName = "beta(" + nn +")";
            betaVar[nn]=cplex.numVar(Integer.MIN_VALUE,0, varName);
        }

        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            for(int t=1;t<p.getTimePointSet().length;t++)
            {
                // gamma >= 0
                varName = "gamma(" + pp +")(" + t + ")";
                gammaVar[pp][t]=cplex.numVar(0,Integer.MAX_VALUE, varName);
            }
        }
    }
    protected IloLinearNumExpr getObjExpr(int[][] vValue, double[] uValue) throws IloException {
        ObjExpr = getDetermineObj(vValue);
        // variable objective function
        for(int i=0;i<p.getDemand().length;i++){
            ObjExpr.addTerm(p.getMaximumDemandVariation()[i] * uValue[i], alphaVar[i]);
        }

        return ObjExpr;
    }
    protected IloLinearNumExpr getObjExpr(int[][] vValue, int[] uValue) throws IloException {
        double[] uValueDouble = IntArrayWrapper.IntArrayToDoubleArray(uValue);
        return getObjExpr(vValue, uValueDouble);
    }
    protected IloLinearNumExpr getDetermineObj(int[][] vVarValue) throws IloException {
        double[][] vVarValueDouble = IntArray2DWrapper.Int2DArrayToDouble2DArray(vVarValue);
        return getDetermineObj(vVarValueDouble);
    }
    protected IloLinearNumExpr getDetermineObj(double[][] vVarValue) throws IloException {
        IloLinearNumExpr ObjExpr = cplex.linearNumExpr();

        // I.part one : sum(normal_demand * alpha) = sum(normal_demand * alpha)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            ObjExpr.addTerm(p.getDemand()[i], alphaVar[i]);
        }

        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        double[] capacitys = getCapacityOnArcs(vVarValue);
        for(int n = 0; n<p.getTravelingArcsSet().length; n++)
        {
            ObjExpr.addTerm(capacitys[n], betaVar[n]);
        }

        // III. part three:
        // p∈P
        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            //t∈ T
            for(int t=1; t<p.getTimePointSet().length; t++)
            {
                ObjExpr.addTerm(-p.getInitialEmptyContainer()[pp], gammaVar[pp][t]);
            }
        }
        return ObjExpr;
    }
    protected void setDualConstraintX() throws IloException {
        C1 = new ArrayList<>();
        //  ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            Request od = in.getRequestSet().get(i);
            IloRange[] C1_k = new IloRange[od.getNumberOfLadenPath()];
            C1.add(C1_k);

            for(int k=0; k< od.getNumberOfLadenPath(); k++){
                int j = od.getLadenPathIndexes()[k];

                IloLinearNumExpr left = cplex.linearNumExpr();

                // first item :
                left.addTerm(1, alphaVar[i]);

                // second item :
                // <n,n'> ∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                    left.addTerm(p.getArcAndPath()[nn][j], betaVar[nn]);
                }

                // third item :
                // t∈T
                for(int t=1;t<p.getTimePointSet().length;t++) {
                    // p ∈P
                    for(int pp=0; pp<p.getPortSet().length; pp++) {
                        // p == d(i)
                        if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i])){
                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
                                // p(n') == p
                                // 1 <= t(n') <= t - sp
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() <= t - p.getTurnOverTime()[pp]
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() >= 1) {
                                    left.addTerm(p.getArcAndPath()[nn][j], gammaVar[pp][t]);
                                }
                            }
                        }

                        // p == o(i)
                        else if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                        {
                            // <n,n'>∈A'
                            for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
                                // p(n) == p
                                // 1 <= t(n) <= t
                                if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                                {
                                    left.addTerm(-p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                }
                            }
                        }
                    }
                }

                String ConstrName = "C-X_"+(i) + "_" + (k);
                //log.info("Add Constraint : "+ConstrName);
                C1.get(i)[k] = cplex.addLe(left,p.getLadenPathCost()[j], ConstrName);
            }
        }
    }
    protected void setDualConstraintY() throws IloException {
        C2 = new ArrayList<>();
        // ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            Request od = in.getRequestSet().get(i);
            IloRange[] C2_k = new IloRange[od.getNumberOfLadenPath()];
            C2.add(C2_k);

            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfLadenPath(); k++){
                int j = in.getRequestSet().get(i).getLadenPathIndexes()[k];

                IloLinearNumExpr left=cplex.linearNumExpr();

                // item1:
                left.addTerm(1,alphaVar[i]);

                // <n,n'>∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
                    // item2:
                    left.addTerm(p.getArcAndPath()[nn][j], betaVar[nn]);
                }

                // left <= c3 * g(φ) + c4φ
                String ConstrName = "C-Y_"+(i)+"_"+(k);
                //log.info("Add Constraint : "+ConstrName);
                C2.get(i)[k] = cplex.addLe(left,p.getRentalCost()*p.getTravelTimeOnPath()[j]+p.getLadenPathCost()[j]
                        , ConstrName);
            }
        }
    }
    protected void setDualConstraintZ() throws IloException {
        if(WhetherUseMultiThreads){
           // long start = System.currentTimeMillis();
            setDualConstraintZwithMultiThreads();
            //log.info("            Set DualConstraintZ Time(Multi Threads) = "+ (System.currentTimeMillis() - start));
        } else {
            //long start = System.currentTimeMillis();
            setDualConstraintZwithSingleThread();
            //log.info("            Set DualConstraintZ Time = "+ (System.currentTimeMillis() - start));
        }
    }
    protected void setDualConstraintZwithSingleThread() throws IloException {
        C3 = new ArrayList<>();
        // i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            Request od = in.getRequestSet().get(i);
            IloRange[] C3_k = new IloRange[od.getNumberOfEmptyPath()];
            C3.add(C3_k);

            //  θ∈Θi
            for(int k = 0; k<od.getNumberOfEmptyPath(); k++) {
                int j = od.getEmptyPathIndexes()[k];

                IloLinearNumExpr left = cplex.linearNumExpr();

                // <n,n'>∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                    // add item1:
                    left.addTerm(p.getArcAndPath()[nn][j],betaVar[nn]);

                    // t∈T
                    for(int t=1;t<p.getTimePointSet().length;t++) {
                        // p∈P
                        for(int pp=0;pp<p.getPortSet().length;pp++)
                        {
                            // p == o(i)
                            if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                            {
                                // add item2:
                                //p(n') == p
                                // 1<=t(n')<= t
                                if(in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getDestinationTime()<=t
                                        &&in.getTravelingArcSet().get(nn).getDestinationTime()>=1)
                                {
                                    left.addTerm(p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                }
                            }

                            // p
                            // add item3:
                            // p(n) == p
                            // 1<= t(n)<=t
                            if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                    &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                    &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                            {
                                left.addTerm(-p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                            }
                        }
                    }

                }

                // left <= c5θ
                String ConstrName = "C-Z_" + (i) +"-"+(k);
                C3.get(i)[k] = cplex.addLe(left, p.getEmptyPathCost()[j], ConstrName);
            }
        }
    }
    protected void setDualConstraintZwithMultiThreads() throws IloException {
        C3 = new ArrayList<>();
        // i∈I
        for(int i=0;i<p.getDemand().length;i++) {
            Request od = in.getRequestSet().get(i);
            IloRange[] C3_k = new IloRange[od.getNumberOfEmptyPath()];
            C3.add(C3_k);
        }
        ExecutorService executor = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
        Map<Integer, IloNumExpr[]> leftIterms = new HashMap<>();;
        // i∈I
        for(int index=0;index<p.getDemand().length;index++)
        {
            int i = index;
            //// parallel
            executor.submit(() -> {
                Request od = in.getRequestSet().get(i);
                IloNumExpr[] lefts = new IloNumExpr[od.getNumberOfEmptyPath()];
                //  θ∈Θi
                for (int k1 = 0; k1 < od.getNumberOfEmptyPath(); k1++) {
                    int j = od.getEmptyPathIndexes()[k1];

                    IloLinearNumExpr left;
                    try {
                        left = cplex.linearNumExpr();
                    } catch (IloException e) {
                        throw new RuntimeException(e);
                    }

                    // <n,n'>∈A'
                    for (int n = 0; n < p.getTravelingArcsSet().length; n++) {
                        // add item1:
                        try {
                            left.addTerm(p.getArcAndPath()[n][j], betaVar[n]);
                        } catch (IloException e) {
                            throw new RuntimeException(e);
                        }

                        // t∈T
                        for(int t=1;t<p.getTimePointSet().length;t++) {
                            // p∈P
                            for(int pp=0;pp<p.getPortSet().length;pp++)
                            {
                                // p == o(i)
                                if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                                {
                                    // add item2:
                                    //p(n') == p
                                    // 1<=t(n')<= t
                                    if(in.getTravelingArcSet().get(n).getDestinationPort().equals(p.getPortSet()[pp])
                                            &&in.getTravelingArcSet().get(n).getDestinationTime()<=t
                                            &&in.getTravelingArcSet().get(n).getDestinationTime()>=1)
                                    {
                                        try {
                                            left.addTerm(p.getArcAndPath()[n][j],gammaVar[pp][t]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }

                                // p
                                // add item3:
                                // p(n) == p
                                // 1<= t(n)<=t
                                if(in.getTravelingArcSet().get(n).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(n).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(n).getOriginTime()>=1)
                                {
                                    try {
                                        left.addTerm(-p.getArcAndPath()[n][j],gammaVar[pp][t]);
                                    } catch (IloException e) {
                                        throw new RuntimeException(e);
                                    }
                                }
                            }
                        }
                    }

                    lefts[k1] = left;
                }
                leftIterms.put(i, lefts);
            });
        }

        executor.shutdown();

        try {
            executor.awaitTermination(Long.MAX_VALUE, TimeUnit.NANOSECONDS);
        } catch (InterruptedException e) {
            // 处理中断异常
            throw new RuntimeException(e);
        }

        for(int i=0;i<p.getDemand().length;i++)
        {
            Request od = in.getRequestSet().get(i);
            for(int k = 0; k<od.getNumberOfEmptyPath(); k++)
            {
                int j = od.getEmptyPathIndexes()[k];
                // left <= c5θ
                String ConstrName = "C-Z_" + (i) +"-"+(k);
                C3.get(i)[k] = cplex.addLe(leftIterms.get(i)[k], p.getEmptyPathCost()[j], ConstrName);
            }
        }
    }
    protected void setDualConstraintG() throws IloException {
        C4 = new IloRange[p.getDemand().length];
        for (int i = 0; i < p.getDemand().length; i++) {
            // alpha <= c2
            String ConstrName = "C-Z_" + (i) ;
            C4[i] = cplex.addLe(alphaVar[i], p.getPenaltyCostForDemand()[i], ConstrName);
        }
    }
    public void changeObjectiveVCoefficients(double[][] vValue) throws IloException	{
        this.vVarValueDouble = vValue;
        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        double[] capacitys = getCapacityOnArcs(vValue);
        for(int n = 0; n<p.getTravelingArcsSet().length; n++)
        {
            cplex.setLinearCoef(objective, capacitys[n], betaVar[n]);
        }
    }
    public void changeObjectiveVCoefficients(int[][] vValue) throws IloException	{
        this.vVarValue = vValue;
        this.vVarValueDouble = IntArray2DWrapper.Int2DArrayToDouble2DArray(vValue);
        double[][] vValueDouble2D = IntArray2DWrapper.Int2DArrayToDouble2DArray(vValue);
        changeObjectiveVCoefficients(vValueDouble2D);
    }
    public void changeObjectiveUCoefficients(double[] uValue) throws IloException {
        this.uValue = uValue;
        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++){
            cplex.setLinearCoef(objective
                    ,p.getDemand()[i] + p.getMaximumDemandVariation()[i] * this.uValue[i]
                    , alphaVar[i]);
        }
    }
    public void changeObjectiveUCoefficients(int[] uValue) throws IloException {
        this.uValue = IntArrayWrapper.IntArrayToDoubleArray(uValue);
        changeObjectiveUCoefficients(this.uValue);
    }
    public void changeObjectiveCoefficients(int[][] vValue, double[] uValue) throws IloException {
        this.vVarValue = vValue;
        this.uValue = uValue;

        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        changeObjectiveUCoefficients(uValue);

        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        changeObjectiveVCoefficients(vValue);
    }
    protected double getConstantItem() throws IloException {
        double constantItem = 0;

        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            constantItem  += ((p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValue[i])*cplex.getValue( alphaVar[i]));
        }

        // III. part three:
        // p∈P
        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            //t∈ T
            for(int t=1; t<p.getTimePointSet().length; t++)
            {
                constantItem  += (-p.getInitialEmptyContainer()[pp] * cplex.getValue(gammaVar[pp][t]));
            }
        }
        return constantItem;
    }

    // here constant item is (sub objective - second item)
    // the second item contains the first stage decision V[h][r]
    public IloRange constructOptimalCut(IloCplex _cplex, IloIntVar[][] vVars, IloNumVar etaVar) throws IloException {
        IloRange cut = null;

        if (cplex.getStatus().equals(IloCplex.Status.Optimal)){
            double constantItem = getConstantItem();
            double[] beta_value = getBetaValue();
            IloLinearNumExpr left = cplex.linearNumExpr();
            for(int n = 0; n<p.getTravelingArcsSet().length; n++){
                if(beta_value[n]==0){
                    continue;
                }
                // r ∈R
                for(int w=0; w<p.getVesselPathSet().length; ++w)
                {
                    int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                    // r(w) = r
                    for(int h=0;h<p.getVesselSet().length;++h)
                    {
                        if(FleetType.equals("Homo")){
                            if(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
                                    *p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h] > 0){
                                // vValue[h][r] : come from solution of master problem
                                left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
                                                *p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta_value[n]
                                        , vVars[h][r]);
                            }
                        } else if (FleetType.equals("Hetero")) {
                            // vValue[h][w] : come from solution of master problem
                            left.addTerm(p.getArcAndVesselPath()[n][w]
                                            *p.getVesselCapacity()[h]*beta_value[n]
                                    , vVars[h][w]);
                        }
                        else{
                            log.info("Error in Fleet type!");
                        }
                    }
                }
            }
            left.addTerm(-1, etaVar);

            cut = _cplex.le(left, -constantItem);
        }

        return cut;
    }

    public double[] getAlphaValue(){
        double[] alpha_value = new double[p.getDemand().length];
        try {
            if(cplex.getStatus() == IloCplex.Status.Optimal){
                for (int i = 0; i < p.getDemand().length; i++){
                    alpha_value[i] = cplex.getValue(alphaVar[i]);
                }
            }
        } catch (IloException e) {
            e.printStackTrace();
        }
        return alpha_value;
    }
    public double[] getBetaValue() throws IloException {
        double[] beta_value = new double[p.getTravelingArcsSet().length];
        if(cplex.getStatus() == IloCplex.Status.Optimal){
            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++){
                beta_value[nn] = cplex.getValue(betaVar[nn]);
            }
        }
        return beta_value;
    }
    public double[][] getGammaValue() {
        double[][] gamma_value = new double[p.getPortSet().length][p.getTimePointSet().length];
        for (int pp = 0; pp < p.getPortSet().length; pp++) {
            for (int t = 1; t < p.getTimePointSet().length; t++) {
                try {
                    gamma_value[pp][t] = cplex.getValue(gammaVar[pp][t]);
                } catch (IloException e) {
                    e.printStackTrace();
                }
            }
        }
        return gamma_value;
    }

/*
    public boolean checkConstraints(double[] alpha_value, double[] beta_value, double[][] gama_value) throws IloException {
        boolean flag = true;
        if(!checkDualConstraintX(alpha_value, beta_value, gama_value))
            flag = false;
        if(!checkDualConstraintY(alpha_value, beta_value))
            flag = false;
        if(!checkDualConstraintZ(alpha_value, gama_value))
            flag = false;
        return flag;
    }
*/

    public boolean checkDualConstraintX(double[] alpha_value, double[] beta_value, double[][] gamma_value) throws IloException {
        boolean flag = true;
        //  ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            Request od = in.getRequestSet().get(i);
            for(int k=0; k< od.getNumberOfLadenPath(); k++){
                int j = od.getLadenPathIndexes()[k];

                double left = 0;

                // first item :
                left += (1 *  alpha_value[i]);

                // second item :
                // <n,n'> ∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                    left += (p.getArcAndPath()[nn][j] * beta_value[nn]);
                }

                // third item :
                // t∈T
                for(int t=1;t<p.getTimePointSet().length;t++) {
                    // p ∈P
                    for(int pp=0; pp<p.getPortSet().length; pp++) {
                        // p == d(i)
                        if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i])){
                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
                                // p(n') == p
                                // 1 <= t(n') <= t - sp
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() <= t - p.getTurnOverTime()[pp]
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() >= 1) {
                                    left += (p.getArcAndPath()[nn][j] * gamma_value[pp][t]);
                                }
                            }
                        }

                        // p == o(i)
                        if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                        {
                            // <n,n'>∈A'
                            for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
                                // p(n) == p
                                // 1 <= t(n) <= t
                                if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                                {
                                    left += (-p.getArcAndPath()[nn][j]* gamma_value[pp][t]);
                                }
                            }
                        }
                    }
                }

                String ConstrName = "C-X_"+(i) + "_" + (k);

                double constraintSlack = cplex.getSlack(C1.get(i)[k]);
                if(constraintSlack < 0){
                    log.info("Cplex: "+ConstrName+" is violated with " + constraintSlack);
                }

                //log.info("Add Constraint : "+ConstrName);
                if (left > p.getLadenPathCost()[j]){
                    log.info("Dual Constraint X "+ConstrName+" is violated!" + "\t\t" + left + "\t\t" + p.getLadenPathCost()[j]);
                    flag = false;
                }
            }
        }

        return flag;
    }
    public boolean checkDualConstraintY(double[] alpha_value, double[] beta_value) throws IloException {
        boolean flag = true;
        // ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfLadenPath(); k++)
            {
                int j = in.getRequestSet().get(i).getLadenPathIndexes()[k];

                double left=0;

                // item1:
                left += (1 * alpha_value[i]);

                // <n,n'>∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++)
                {
                    // item2:
                    left += (p.getArcAndPath()[n][j] * beta_value[n]);
                }

                // left <= c3 * g(φ) + c4φ
                String ConstrName = "C-Y_"+(i)+"_"+(k);

                double constraintSlack = cplex.getSlack(C2.get(i)[k]);
                if(constraintSlack < 0){
                    log.info("Cplex: "+ConstrName+" is violated with " + constraintSlack);
                }

                //log.info("Add Constraint : "+ConstrName);
                if (left  >p.getRentalCost()*p.getTravelTimeOnPath()[j]+
                        p.getLadenPathCost()[j]){
                    log.info("Dual Constraint Y "+ConstrName+" is violated!" + "\t\t" + left + "\t\t" + p.getRentalCost()*p.getTravelTimeOnPath()[j]+
                            p.getLadenPathCost()[j]);
                    flag = false;
                }
            }
        }

        return flag;
    }
    public boolean checkDualConstraintZ(double[] beta_value, double[][] gama_value) throws IloException {
        boolean flag = true;
        // i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            //  θ∈Θi
            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfEmptyPath(); k++)
            {
                int j = in.getRequestSet().get(i).getEmptyPathIndexes()[k];

                double left = 0;

                // <n,n'>∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++)
                {
                    // add item1:
                    left += (p.getArcAndPath()[n][j] * beta_value[n]);

                    // t∈T
                    for(int t=1;t<p.getTimePointSet().length;t++) {
                        // p∈P
                        for(int pp=0;pp<p.getPortSet().length;pp++)
                        {
                            // p == o(i)
                            if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                            {
                                // add item2:
                                //p(n') == p
                                // 1<=t(n')<= t
                                if(in.getTravelingArcSet().get(n).getDestinationPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(n).getDestinationTime()<=t
                                        &&in.getTravelingArcSet().get(n).getDestinationTime()>=1)
                                {
                                    left += (p.getArcAndPath()[n][j] * gama_value[pp][t]);
                                }
                            }

                            // p
                            // add item3:
                            // p(n) == p
                            // 1<= t(n)<=t
                            if(in.getTravelingArcSet().get(n).getOriginPort().equals(p.getPortSet()[pp])
                                    &&in.getTravelingArcSet().get(n).getOriginTime()<=t
                                    &&in.getTravelingArcSet().get(n).getOriginTime()>=1)
                            {
                                left += (-p.getArcAndPath()[n][j] * gama_value[pp][t]);
                            }
                        }
                    }

                }

                // left <= c5θ
                String ConstrName = "C-Z_" + (i) +"-"+(k);
                double constraintSlack = cplex.getSlack(C3.get(i)[k]);
                if(constraintSlack < 0){
                    log.info("Cplex: "+ConstrName+" is violated with " + constraintSlack);
                }

                if(left  > p.getEmptyPathCost()[j]){
                    log.info("Dual Constraint Z "+ConstrName+" is violated!" + "\t\t" + left + "\t\t" + p.getEmptyPathCost()[j]);
                    flag = false;
                }
            }
        }
        return flag;
    }

}
