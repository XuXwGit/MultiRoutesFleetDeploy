package multi.model.primal;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.IntArrayWrapper;
import multi.Parameter;
import multi.network.Request;
/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SubProblemReactive extends BasePrimalModel
{
    private int [][] vVarValue1;
    private int [][] vVarValue2;
    private double [] uu;
    private double ladenCost;
    private double emptyCost;
    private double penaltyCost;
    private double rentalCost;

    public SubProblemReactive(InputData in, Parameter p){
        super();
        this.in = in;
        this.p = p;
        this.modelName = "SPR"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
        this.vVarValue1= new int[p.getVesselSet().length] [p.getShippingRouteSet().length];
        this.vVarValue2= new int[p.getVesselSet().length] [p.getVesselPathSet().length];
        this.uValue = new double[p.getDemand().length];
        try{
            cplex = new IloCplex();
            publicSetting(cplex);
            frame();
        }catch (IloException e) {
            e.printStackTrace();
        }
    }

    protected void setDecisionVars() throws IloException{
        SetRequestDecisionVars();
    }

    // Minimize total cost about containers
    protected void setObjectives() throws IloException	{
        IloLinearNumExpr Obj=cplex.linearNumExpr();

        // i
        for(int i=0;i<p.getDemand().length;i++)
        {
            // item2 : Penalty Cost of unsatisfied Demand : c2i*Gi
            Obj.addTerm(p.getPenaltyCostForDemand()[i], gVar[i]);

            Request od = in.getRequestSet().get(i);
            // \phi_i
            for(int k=0;k<od.getNumberOfLadenPath();k++)
            {
                int j = od.getLadenPathIndexes()[k];
                // item3 : Demurrage of self-owned and leased containers and Rental cost on laden paths
                Obj.addTerm(p.getLadenPathCost()[j], xVar.get(i)[k]);
                Obj.addTerm(p.getLadenPathCost()[j], yVar.get(i)[k]);
                Obj.addTerm(p.getRentalCost()*p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
            }

            // item4: Demurrage of self-owned containers for empty path
            // \theta
            for(int k=0;k<od.getNumberOfEmptyPath();k++)
            {
                int j = od.getEmptyPathIndexes()[k];

                Obj.addTerm(p.getEmptyPathCost()[j], zVar.get(i)[k]);
            }
        }

        cplex.addMinimize(Obj);
    }

    private IloRange[] C1;
    private IloRange[] C2_1;
    private IloRange[] C2_2;
    private IloRange[][] C3;

    protected void setConstraints() throws IloException {
        setConstraint1();
        setConstraint2_1();
        setConstraint2_2();
        setConstraint3();
    }

    // Demand equation :
    // C-5------α
    // C-5 = 0
    private void setConstraint1() throws IloException	{
        C1 = new IloRange[p.getDemand().length];

        //∀i∈I
        for (int i = 0; i < p.getDemand().length; i++) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            Request od = in.getRequestSet().get(i);
            //φ
            for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
                left.addTerm(1, xVar.get(i)[k]);
                left.addTerm(1, yVar.get(i)[k]);
            }

            left.addTerm(1, gVar[i]);

            String ConstrName = "C1(" + (i + 1) + ")";
            C1[i] = cplex.addEq(left, p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValue[i], ConstrName);
        }
    }

    // VesselType Capacity Constraint :
    // C-6------β
    // C-6<= 0
    private void setConstraint2_1() throws IloException	{
        C2_1 = new IloRange[p.getTravelingArcsSet().length];

        // ∀<n,n'>∈A'
        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
        {
            IloLinearNumExpr left=cplex.linearNumExpr();

            // i∈I
            for(int i=0;i<p.getDemand().length;i++)
            {
                Request od = in.getRequestSet().get(i);

                // φ
                for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
                    int j = od.getLadenPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                    left.addTerm(p.getArcAndPath()[nn][j], yVar.get(i)[k]);
                }
            }

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
                }
            }
            String ConstrName = "C6-"+"_"+(nn+1);
            C2_1[nn] = cplex.addLe(left, capacity1, ConstrName);
        }
    }
    private void setConstraint2_2() throws IloException	{
        C2_2 = new IloRange[p.getTravelingArcsSet().length];

        // ∀<n,n'>∈A'
        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
        {
            IloLinearNumExpr left=cplex.linearNumExpr();

            // i∈I
            for(int i=0;i<p.getDemand().length;i++)
            {
                Request od = in.getRequestSet().get(i);

                //θ
                for (int k = 0; k < od.getNumberOfEmptyPath(); k++) {
                    int j = od.getEmptyPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                }
            }

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
                    capacity2 += p.getArcAndVesselPath()[nn][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue2[h][w];
                }
            }
            String ConstrName = "C6-"+"_"+(nn+1);
            C2_2[nn] = cplex.addLe(left, capacity2, ConstrName);
        }
    }


    // Container Flow Conservation Constraint :
    // calculate the number of available empty self-owned containers at port p at time t
    // or
    // L[p][t] > 0 means all empty self-owned containers that repositioning to other ports (sumZ(out))
    // plus all laden self-owned containers that transport to other ports (sumX(out))
    // should no more than (L[p][t-1] + sumX(in) + sumZ(in))
    // C7------γ
    // C7>=0  =>  -C7 <= 0
    // ( item4 - item1 ) * Z + (item3 - item2) * X <= Lp0
    // Output-X + OutputZ - Input-X - Input-Z <= lp0
    private void setConstraint3() throws IloException	{
        C3 = new IloRange[p.getPortSet().length][p.getTimePointSet().length];

        // ∀p∈P
        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            // ∀t∈T
            for(int t = 1; t<p.getTimePointSet().length; t++)
            {
                IloLinearNumExpr left=cplex.linearNumExpr();

                // i∈I
                for(int i=0;i<p.getDemand().length;i++)
                {
                    Request od = in.getRequestSet().get(i);

                    // Input Z flow:
                    // (item1)
                    // o(i) == p
                    if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                    {
                        //θi
                        for (int k = 0; k < od.getNumberOfEmptyPath(); k++)
                        {
                            int j = od.getEmptyPathIndexes()[k];

                            // <n,n'> ∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
                                // p(n') == p
                                // 1<= t(n')<= t
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() <= t
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() >= 1)
                                {
                                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                }
                            }
                        }
                    }

                    // Input flow X
                    // item2
                    // d(i) == p
                    if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i]))
                    {
                        for(int k=0;k<od.getNumberOfLadenPath();k++)
                        {
                            int j = od.getLadenPathIndexes()[k];

                            // <n,n'>∈A'
                            for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
                            {
                                // p(n‘)∈p
                                // 1 <= t(n')<= t-sp
                                if(in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getDestinationTime()<=t-p.getTurnOverTime()[pp]
                                        &&in.getTravelingArcSet().get(nn).getDestinationTime()>=1)
                                {
                                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                }
                            }
                        }
                    }


                    //Output  flow X
                    // item3
                    // o(i) == p
                    if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                    {
                        // φi
                        for(int k=0;k<od.getNumberOfLadenPath();k++)
                        {
                            int j = od.getLadenPathIndexes()[k];

                            // <n.n'>∈A'
                            for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
                            {
                                //p(n) == p
                                // t(n) <= t
                                if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getOriginTime() <=t
                                        &&in.getTravelingArcSet().get(nn).getOriginTime() >=1)
                                {
                                    left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                }
                            }
                        }
                    }


                    // Output Flow Z
                    // item4
                    // θ
                    for(int k=0;k<od.getNumberOfEmptyPath();k++)
                    {
                        int j = od.getEmptyPathIndexes()[k];

                        // <n,n'>∈A'
                        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
                        {
                            // p(n) == p
                            // t(n) <= t
                            if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                    && in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                    && in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                            {
                                left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                            }
                        }
                    }
                }

                String ConstrName = "C7_"+(pp+1)+"_"+(t);
                C3[pp][t] = cplex.addGe(left, -p.getInitialEmptyContainer()[pp], ConstrName);
            }
        }
    }

    public void solveModel()	{
        try
        {
            if (DefaultSetting.WhetherExportModel) {
                exportModel();
            }
            long startTime = System.currentTimeMillis();
            if (cplex.solve())
            {
                long endTime = System.currentTimeMillis();
                setObjVal(cplex.getObjValue());
                setSolveTime(endTime - startTime);
                setObjGap(cplex.getMIPRelativeGap());
            }
            else
            {
                log.info("SubProblem No solution");
            }

        }
        catch (IloException ex) {
            log.info("Concert Error: " + ex);
        }
    }

    // change the coefficients of capacity constraints
    public void changeConstraintCoefficients(int[][] vVarValue1, int[][] vVarValue2, int[] uValue) throws IloException {
        this.vVarValue1 = vVarValue1;
        this.vVarValue2 = vVarValue2;
        this.uValue = IntArrayWrapper.IntArrayToDoubleArray(uValue);

        for(int i=0;i<p.getDemand().length;i++)
        {
            C1[i].setBounds(p.getDemand()[i]+p.getMaximumDemandVariation()[i]*uValue[i],
                    p.getDemand()[i]+p.getMaximumDemandVariation()[i]*uValue[i]);
        }

        // ∀<n,n'>∈A'
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
                    // vValue[v][r] : come from solution of master problem
                    capacity2 += p.getArcAndVesselPath()[nn][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue2[h][w];
                }
            }
            C2_1[nn].setBounds(0, capacity1);
            C2_2[nn].setBounds(0, capacity2);
        }
    }
    public void changeConstraintCoefficients(int[][] vVarValue1, int[][] vVarValue2, double[] uValue) throws IloException {
        this.vVarValue1 = vVarValue1;
        this.vVarValue2 = vVarValue2;
        this.uu = uValue;

        for(int i=0;i<p.getDemand().length;i++)        {
            C1[i].setBounds(p.getDemand()[i]+p.getMaximumDemandVariation()[i]*uValue[i],
                    p.getDemand()[i]+p.getMaximumDemandVariation()[i]*uValue[i]);
        }

        // ∀<n,n'>∈A'
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
                    // vValue[v][r] : come from solution of master problem
                    capacity2 += p.getArcAndVesselPath()[nn][w]
                            *p.getShipRouteAndVesselPath()[r][w]
                            *p.getVesselTypeAndShipRoute()[h][r]
                            *p.getVesselCapacity()[h]
                            * vVarValue2[h][w];
                }
            }
            C2_1[nn].setBounds(0, capacity1);
            C2_2[nn].setBounds(0, capacity2);
        }
    }

    public double getLadenCost() {
        return ladenCost;
    }

    public void setLadenCost(double ladenCost) {
        this.ladenCost = ladenCost;
    }

    public double getEmptyCost() {
        return emptyCost;
    }

    public void setEmptyCost(double emptyCost) {
        this.emptyCost = emptyCost;
    }

    public double getPenaltyCost() {
        return penaltyCost;
    }

    public void setPenaltyCost(double penaltyCost) {
        this.penaltyCost = penaltyCost;
    }

    public double getRentalCost() {
        return rentalCost;
    }

    public void setRentalCost(double rentalCost) {
        this.rentalCost = rentalCost;
    }

}
