package multi.model.dual;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.Parameter;
import multi.network.Request;
import multi.Scenario;
/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class DualSubProblemReactive extends BaseDualModel
{
    private final int tau;
    private int [][] vVarValue1;
    private int [][] vVarValue2;
    private Scenario Scene;
    private IloNumVar[] alphaVar;
    private IloNumVar[] betaVar1;
    private IloNumVar[] betaVar2;
    private IloNumVar[][] gammaVar;
    private IloIntVar[] miuVar;
    private IloNumVar[] lambdaVar;
    private IloObjective objective;
    private double subObj;
    private double mipGap;
    public DualSubProblemReactive(InputData in, Parameter p, int tau) {
        super();
        this.in = in;
        this.p = p;
        this.tau=tau;
        this.modelName = "DSPR"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
        this.vVarValue1= new int[p.getVesselSet().length] [p.getShippingRouteSet().length];
        this.vVarValue2= new int[p.getVesselSet().length] [p.getVesselPathSet().length];
        try{
            cplex = new IloCplex();
            publicSetting(cplex);
            frame();
        }catch (IloException e) {
            e.printStackTrace();
        }
    }

    public void setDecisionVars() throws IloException	{
        // create dual variable
        // α[i]
        //β[nn']
        //γ[p][t]
        alphaVar =new IloNumVar [p.getDemand().length];
        betaVar1 =new IloNumVar [p.getTravelingArcsSet().length];
        betaVar2 =new IloNumVar [p.getTravelingArcsSet().length];
        gammaVar=new IloNumVar[p.getPortSet().length][p.getTimePointSet().length];

        // u[i] ∈{0,1}
        // the uncertain request can be inferred by u
        // f[i] = nf[i] + vf[i]*u[i]
        miuVar=new IloIntVar [p.getDemand().length];

        // create auxiliary variable
        //λ[i]=α[i]*u[i]
        lambdaVar =new IloNumVar [p.getDemand().length];

        String varName;
        for(int i=0;i<p.getDemand().length;i++)
        {
            varName = "alpha(" + p.getDemand()[i] +")";
            alphaVar[i]=cplex.numVar(Integer.MIN_VALUE, Integer.MAX_VALUE, varName);

            varName = "lambda(" + p.getDemand()[i] +")";
            lambdaVar[i]=cplex.numVar(Integer.MIN_VALUE ,Integer.MAX_VALUE, varName);

            varName = "u(" + p.getDemand()[i] +")";
            miuVar[i]=cplex.boolVar(varName);
        }

        for(int i = 0; i<p.getTravelingArcsSet().length; i++)
        {
            // beta <= 0
            varName = "beta1(" + p.getTravelingArcsSet()[i] +")";
            betaVar1[i]=cplex.numVar(Integer.MIN_VALUE,0, varName);
            varName = "beta2(" + p.getTravelingArcsSet()[i] +")";
            betaVar2[i]=cplex.numVar(Integer.MIN_VALUE,0, varName);
        }

        for(int i=0;i<p.getPortSet().length;i++)
        {
            for(int t=1;t<p.getTimePointSet().length;t++)
            {
                // gamma >= 0
                varName = "gamma(" + p.getPortSet()[i] +")(" + p.getTimePointSet()[t] + ")";
                gammaVar[i][t]=cplex.numVar(0,Integer.MAX_VALUE, varName);
            }
        }
    }


    public void setObjectives() throws IloException	{
        IloLinearNumExpr Obj=cplex.linearNumExpr();
        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            Obj.addTerm(p.getDemand()[i], alphaVar[i]);
            Obj.addTerm(p.getMaximumDemandVariation()[i], lambdaVar[i]);
        }

        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
        {
            double capacity1 = 0;
            double capacity2 = 0;
            // w∈Ω
            for(int w=0; w<p.getVesselPathSet().length; w++)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                // r(w) = r
                // h \in Hr
                for(int h=0;h<p.getVesselSet().length;h++)
                {
                    // vValue[v][r] : come from solution of master problem
                    capacity1 += p.getArcAndVesselPath()[nn][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue1[h][r];

                    // vValue[v][w] : come from solution of master problem
                    capacity2 += p.getArcAndVesselPath()[nn][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue2[h][w];
                }
            }
            Obj.addTerm(capacity1, betaVar1[nn]);
            Obj.addTerm(capacity2, betaVar2[nn]);
        }

        // III. part three:
        // p∈P
        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            //t∈ T
            for(int t=1; t<p.getTimePointSet().length; t++)
            {
                Obj.addTerm(-p.getInitialEmptyContainer()[pp], gammaVar[pp][t]);
            }
        }

        objective = cplex.addMaximize(Obj);
    }

    public void changeObjectiveVCoefficients(int[][] vValue1, int[][]vValue2) throws IloException	{
        this.vVarValue1 = vValue1;
        this.vVarValue2 = vValue2;
        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        for(int n = 0; n<p.getTravelingArcsSet().length; n++) {
            double capacity1 = 0;
            double capacity2 = 0;
            // w∈Ω
            for(int w=0; w<p.getVesselPathSet().length; w++)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                // r(w) = r
                // h \in Hr
                for(int h=0;h<p.getVesselSet().length;h++)
                {
                    // vValue[v][r] : come from solution of master problem
                    capacity1 += p.getArcAndVesselPath()[n][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue1[h][r];
                    // vValue[v][w] : come from solution of master problem
                    capacity2 += p.getArcAndVesselPath()[n][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue2[h][w];
                }
            }
            cplex.setLinearCoef(objective, capacity1, betaVar1[n]);
            cplex.setLinearCoef(objective, capacity2, betaVar2[n]);
        }
    }
    public void setConstraints() throws IloException	{
        // dual constraints
        setConstraint1();
        setConstraint2();
        setConstraint3();
        setConstraint4();

        // uncertain set
        setConstraint5();

        // linearize constraints
        // λ<=α
        setConstraint6();
        //λ>= α-(1-u)M
        setConstraint7();
        // λ<= M*u
        setConstraint8();
        // λ>=- M*u
        setConstraint9();
    }


//	private IloRange[][] C1;
//	private IloRange[][] C2;
//	private IloRange[][] C3;
//	private IloRange[] C4;

    // C1------X
    private void setConstraint1() throws IloException	{
        //  ∀i∈I
        for(int i=0;i<p.getDemand().length;i++) {
            // ∀φ∈Φi
            Request OD = in.getRequestSet().get(i);
            for(int k1=0; k1< OD.getNumberOfLadenPath(); k1++) {
                int j = OD.getLadenPathIndexes()[k1];

                IloLinearNumExpr left = cplex.linearNumExpr();

                // first item :
                left.addTerm(1, alphaVar[i]);

                // second item :
                // <n,n'> ∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++) {
                    left.addTerm(p.getArcAndPath()[n][j], betaVar1[n]);
                }

                // third item :
                // t∈T
                for(int t=1;t<p.getTimePointSet().length;t++) {
                    // p ∈P
                    for(int m=0; m<p.getPortSet().length; m++)
                    {
                        // p == d(i)
                        if(p.getPortSet()[m].equals(p.getDestinationOfDemand()[i]))
                        {
                            // <n,n'>∈A'
                            for (int n = 0; n < p.getTravelingArcsSet().length; n++) {
                                // p(n') == p
                                // 1 <= t(n') <= t - sp
                                if (in.getTravelingArcSet().get(n).getDestinationPort().equals(p.getPortSet()[m])
                                        && in.getTravelingArcSet().get(n).getDestinationTime() <= t - p.getTurnOverTime()[m]
                                        && in.getTravelingArcSet().get(n).getDestinationTime() >= 1) {
                                    left.addTerm(p.getArcAndPath()[n][j], gammaVar[m][t]);
                                }
                            }
                        }
                        // p == o(i)
                        if(p.getPortSet()[m].equals(p.getOriginOfDemand()[i]))
                        {
                            // <n,n'>∈A'
                            for(int n = 0; n<p.getTravelingArcsSet().length; n++)
                            {
                                // p(n) == p
                                // 1 <= t(n) <= t
                                if(in.getTravelingArcSet().get(n).getOriginPort().equals(p.getPortSet()[m])
                                        &&in.getTravelingArcSet().get(n).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(n).getOriginTime()>=1)
                                {
                                    left.addTerm(-p.getArcAndPath()[n][j],gammaVar[m][t]);
                                }
                            }
                        }
                    }
                }

                String ConstrName = "C1_"+(j+1);
                cplex.addLe(left,p.getLadenPathCost()[j], ConstrName);
            }
        }
    }

    // C2------Y
    private void setConstraint2() throws IloException {
        // ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            for(int k1 = 0; k1<in.getRequestSet().get(i).getNumberOfLadenPath(); k1++)
            {
                int j = in.getRequestSet().get(i).getLadenPathIndexes()[k1];

                IloLinearNumExpr left=cplex.linearNumExpr();

                // item1:
                left.addTerm(1,alphaVar[i]);

                // <n,n'>∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++)
                {
                    left.addTerm(p.getArcAndPath()[n][j], betaVar1[n]);
                }

                // left <= c3 * g(φ) + c4φ
                String ConstrName = "C2_"+(i+1)+"_"+(j+1);
                cplex.addLe(left,p.getRentalCost()*p.getTravelTimeOnPath()[j]+p.getLadenPathCost()[j], ConstrName);
            }
        }
    }

    // C3------Z
    private void setConstraint3() throws IloException	{
        // i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            //  θ∈Θi
            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfEmptyPath(); k++) {
                int j = in.getRequestSet().get(i).getEmptyPathIndexes()[k];

                IloLinearNumExpr left = cplex.linearNumExpr();

                // <n,n'>∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++) {
                    // add item1:
                    left.addTerm(p.getArcAndPath()[n][j],betaVar2[n]);

                    // t∈T
                    for(int t=1;t<p.getTimePointSet().length;t++) {
                        // p∈P
                        for(int pp=0;pp<p.getPortSet().length;pp++)
                        {
                            // p == o(i)
                            if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                            {
                                // add item1:
                                //p(n') == p
                                // 1<=t(n')<= t
                                if(in.getTravelingArcSet().get(n).getDestinationPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(n).getDestinationTime()<=t
                                        &&in.getTravelingArcSet().get(n).getDestinationTime()>=1) {
                                    left.addTerm(p.getArcAndPath()[n][j],gammaVar[pp][t]);
                                }
                            }

                            // p
                            // add item4:
                            // p(n) == p
                            // 1<= t(n)<=t
                            if(in.getTravelingArcSet().get(n).getOriginPort().equals(p.getPortSet()[pp])
                                    &&in.getTravelingArcSet().get(n).getOriginTime()<=t
                                    &&in.getTravelingArcSet().get(n).getOriginTime()>=1)
                            {
                                left.addTerm(-p.getArcAndPath()[n][j],gammaVar[pp][t]);
                            }
                        }
                    }
                }

                // left <= c5θ
                String ConstraintName = "C3_"+(j+1);
                cplex.addLe(left, p.getEmptyPathCost()[j], ConstraintName);
            }
        }
    }

    // C4------G
    private void setConstraint4() throws IloException	{
        for (int i = 0; i < p.getDemand().length; i++) {
            cplex.addLe(alphaVar[i], p.getPenaltyCostForDemand()[i]);
        }
    }

    // budget uncertain set
    private void setConstraint5() throws IloException	{
        IloLinearIntExpr left = cplex.linearIntExpr();

        for(int i=0;i<p.getDemand().length;i++) {
            left.addTerm(1,miuVar[i]);
        }
        cplex.addLe(left, tau);
    }

    // λ[i] <= α[i]
    private void setConstraint6() throws IloException	{
        for(int i=0;i<p.getDemand().length;i++)
        {
            IloLinearNumExpr left=cplex.linearNumExpr();
            left.addTerm(1,lambdaVar[i]);
            left.addTerm(-1,alphaVar[i]);
            cplex.addLe(left,0);
        }
    }

    // λ[i] >= α[i] - M*(1-u[i])
    // λ[i] - M*u[i] - α[i] >= - M
    private void setConstraint7() throws IloException	{
        double M = 1E6;

        for(int i=0;i<p.getDemand().length;i++)
        {
            IloLinearNumExpr left=cplex.linearNumExpr();

            left.addTerm(1,lambdaVar[i]);
            left.addTerm(-M, miuVar[i]);
            left.addTerm(-1,alphaVar[i]);
            cplex.addGe(left, -M);
        }
    }

    // λ[i] <= u[i]*M
    private void setConstraint8() throws IloException	{
        double M = 1E6;

        for(int i=0;i<p.getDemand().length;i++)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();

            left.addTerm(1,lambdaVar[i]);
            left.addTerm(-M,miuVar[i]);

            cplex.addLe(left,0);
        }
    }

    // λ[i] >= - u[i]*M
    private void setConstraint9() throws IloException	{
        double M = 1E6;

        for(int i=0;i<p.getDemand().length;i++)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();

            left.addTerm(1,lambdaVar[i]);
            left.addTerm(M, miuVar[i]);

            cplex.addGe(left,0);
        }
    }

    public void solveModel() {
        try {
            if (DefaultSetting.WhetherExportModel)
                exportModel();
            long startTime = System.currentTimeMillis();
            if (cplex.solve()) {
                long endTime = System.currentTimeMillis();

                setObjVal(cplex.getObjValue());
                setSolveTime(endTime - startTime);
                setObjGap(cplex.getMIPRelativeGap());

                uValue = new double[p.getDemand().length];
                double[] request = new double[p.getDemand().length];
                double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
                for (int i = 0; i < p.getDemand().length; i++) {
                    if (cplex.getValue(miuVar[i]) >= 1 - tolerance) {
                        {
                            request[i] = 1;
                            uValue[i] = 1;
                        }
                    }

//                printSolution();

                    if (DefaultSetting.DebugEnable && DefaultSetting.DualSubEnable) {
                        log.info("------------------------------------------------------------------------");
                        log.info("SolveTime = " + (endTime - startTime));
                        printSolution();
                        log.info("------------------------------------------------------------------------");
                    }

                    Scene = new Scenario();
                    Scene.setRequest(request);
                }
                /*cplex.end();*/
            }
        } catch (IloCplex.UnknownObjectException e) {
            throw new RuntimeException(e);
        } catch (IloException e) {
            throw new RuntimeException(e);
        }
    }

    public void printSolution(){
        log.info("The Worst Case(DSP) : "+"(tau = "+tau+")");
        for(int i=0;i<p.getDemand().length;i++)
        {
            if (uValue[i] != 0)
            {
                System.out.print(i+"("+ uValue[i]+")\t");
            }
        }

    }

    public Scenario getScene()	{
        return Scene;
    }

    public double getConstantItem() throws IloException {
        double constantItem = 0;
        for(int n = 0; n<p.getTravelingArcsSet().length; n++)
        {
            // r ∈R
            for(int w=0; w<p.getVesselPathSet().length; w++)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                // r(w) = r
                for(int h=0;h<p.getVesselSet().length;h++)
                {
                    // vValue[v][r] : come from solution of master problem
                    constantItem += p.getArcAndVesselPath()[n][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue1[h][r]
                            * cplex.getValue(betaVar1[n]);

                    // vValue[v][r] : come from solution of master problem
                    constantItem += p.getArcAndVesselPath()[n][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue2[h][r]
                            * cplex.getValue(betaVar2[n]);
                }
            }
        }

        return this.getObjVal()-constantItem;
    }

    public double[] getBeta1Value() throws IloException {
        double[] beta_value = new double[p.getTravelingArcsSet().length];
        if(cplex.getStatus() == IloCplex.Status.Optimal)
        {
            for (int i = 0; i < p.getTravelingArcsSet().length; i++)
            {
                beta_value[i] = cplex.getValue(betaVar1[i]);
            }
        }
        return beta_value;
    }

    public double[] getBeta2Value() throws IloException {
        double[] beta_value = new double[p.getTravelingArcsSet().length];
        if(cplex.getStatus() == IloCplex.Status.Optimal)
        {
            for (int i = 0; i < p.getTravelingArcsSet().length; i++)
            {
                beta_value[i] = cplex.getValue(betaVar2[i]);
            }
        }
        return beta_value;
    }

    public double getMipGap() {
        return mipGap;
    }

}
