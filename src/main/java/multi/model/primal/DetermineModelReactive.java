package multi.model.primal;

import ilog.concert.IloException;
import ilog.concert.IloIntVar;
import ilog.concert.IloLinearIntExpr;
import ilog.concert.IloLinearNumExpr;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.InputData;
import multi.Parameter;
import multi.network.Request;
import multi.network.TravelingArc;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class DetermineModelReactive extends BasePrimalModel {
    public DetermineModelReactive(InputData in, Parameter p) {
        super();
        this.in = in;
        this.p = p;
        this.modelName = "DMR"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
        try{
            if(WhetherPrintProcess){
                log.info("=========DetermineModel (Reactive Strategy)==========");
            }
            cplex = new IloCplex();

            publicSetting(cplex);

            double start = System.currentTimeMillis();
            frame();
            double begin = System.currentTimeMillis();
            solveModel();
            double end = System.currentTimeMillis();
            setSolveTime(end - start);

            if(WhetherPrintProcess){
                log.info("BuildTime = "+ (begin - start) +"\t\t"
                        + "SolveTime = " + (end - start));
                log.info("Determine Objective = " +String.format("%.2f", getObjVal()));
            }
            if(WhetherPrintProcess){
                printSolution();
            }
            log.info("================================");
        }catch (IloException e) {
            e.printStackTrace();
        }
    }
    private IloIntVar[][] vVar2;
    public void setDecisionVars() throws IloException
    {
        String varName;

        // v[h][r/w] : binary variable ���� whether vessel type h is assigned to shipping route r/w
        SetVesselDecisionVars();

        vVar2 =new IloIntVar [p.getVesselSet().length] [p.getVesselPathSet().length];
        for(int h=0;h<p.getVesselSet().length;h++)
        {
            for (int w = 0; w < p.getVesselPathSet().length; w++) {
                varName = "v(" + (h+1) +")("+ (w+1)+")";
                vVar2[h][w]=cplex.boolVar(varName);
            }
        }

        // x[i][k]
        // y[i][k]
        // z[i][k]
        // g[i]
        SetRequestDecisionVars();
    }

    public void setObjectives() throws IloException
    {
        IloLinearNumExpr Obj=cplex.linearNumExpr();
        // r
        for(int r = 0; r<p.getShippingRouteSet().length; r++)
        {
            // h
            for(int h=0; h<p.getVesselSet().length; h++)
            {
                // ω
                for (int w = 0; w < p.getVesselPathSet().length; w++)
                {
                    // C1[h][r(w)] * V[h][r]
                    Obj.addTerm(p.getShipRouteAndVesselPath()[r][w]
                                    *p.getVesselTypeAndShipRoute()[h][r]
                                    * p.getVesselOperationCost()[h],
                            vVar[h][r]);
                }
            }
        }


        // h
        for(int h=0; h<p.getVesselSet().length; h++)
        {
            // ω
            for (int w = 0; w < p.getVesselPathSet().length; w++) {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                // C1[h][r(w)] * V[h][r]
                Obj.addTerm(p.getShipRouteAndVesselPath()[r][w]
                                *p.getVesselTypeAndShipRoute()[h][r]
                                * p.getVesselOperationCost()[h],
                        vVar2[h][w]);
            }
        }

        // i
        for(int i=0;i<p.getDemand().length;i++)
        {
            // C2[i] * G[i]
            Obj.addTerm(p.getPenaltyCostForDemand()[i], gVar[i]);

            Request od = in.getRequestSet().get(i);
            for(int k=0;k<od.getNumberOfLadenPath();k++)
            {
                // directly get ladenPath index
                int j = od.getLadenPathIndexes()[k];

                // C3 * g[k] * Y[i][k]
                // C4[k] * Y[i][k]
                // C4[k] * X[i][k]
                Obj.addTerm(p.getRentalCost()*p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
                Obj.addTerm(p.getLadenPathCost()[j], yVar.get(i)[k]);
                Obj.addTerm(p.getLadenPathCost()[j], xVar.get(i)[k]);
            }

            for(int k=0;k<od.getNumberOfEmptyPath();k++)
            {
                int j = od.getEmptyPathIndexes()[k];
                // C5[k] * Z[i][k]
                Obj.addTerm(p.getEmptyPathCost()[j], zVar.get(i)[k]);
            }

        }
        cplex.addMinimize(Obj);
    }

    public void setConstraints() throws IloException
    {
        // each ship route assigned to one vessel
        setConstraint1();

        // Demand Equation Constraints
        setConstraint2();

        // Transport Capacity Constraints
        setConstraint3_1();
        setConstraint3_2();

        // Containers Flow Conservation Constraints
        setConstraint4();
    }

    // (2)
    // Each Route should be assigned only one VesselType
    private void setConstraint1() throws IloException
    {
        // r \in R
        for(int r = 0; r<p.getShippingRouteSet().length; r++)
        {
            IloLinearIntExpr left=cplex.linearIntExpr();

            // h
            for(int h=0;h<p.getVesselSet().length;h++)
            {
                left.addTerm(p.getVesselTypeAndShipRoute()[h][r], vVar[h][r]);
                // or
            }
            cplex.addEq(left,1);
        }
    }

    // (3)
    // Demand Equation Constraints
    private void setConstraint2() throws IloException
    {
        // i
        for(int i=0;i<p.getDemand().length;i++)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();

            Request OD = in.getRequestSet().get(i);
            // phi
            for(int k=0;k<OD.getNumberOfLadenPath();k++)
            {
                left.addTerm(1, xVar.get(i)[k]);
                left.addTerm(1, yVar.get(i)[k]);
            }

            left.addTerm(1, gVar[i]);
            cplex.addEq(left,p.getDemand()[i]);
        }
    }

    // (4)
    // Capacity Constraint on each travel arc
    private void setConstraint3_1() throws IloException
    {
        for(int l = 0; l<p.getTravelingArcsSet().length; l++)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();

            // i
            for(int i=0;i<p.getDemand().length;i++)
            {
                Request od = in.getRequestSet().get(i);
                // phi
                for(int k=0;k<od.getNumberOfLadenPath();k++)
                {
                    int j = od.getLadenPathIndexes()[k];
                    left.addTerm(p.getArcAndPath()[l][j], xVar.get(i)[k]);
                    left.addTerm(p.getArcAndPath()[l][j], yVar.get(i)[k]);
                }
            }

            // r
            for(int r = 0; r<p.getShippingRouteSet().length; r++)
            {
                // w
                for(int w=0;w<p.getVesselPathSet().length;w++)
                {
                    for(int h=0;h<p.getVesselSet().length;h++)
                    {
                        left.addTerm(-p.getArcAndVesselPath()[l][w]
                                        *p.getVesselCapacity()[h]
                                        *p.getShipRouteAndVesselPath()[r][w]
                                        *p.getVesselTypeAndShipRoute()[h][r]
                                , vVar[h][r]);
                    }
                }
            }
            cplex.addLe(left,0);
        }
    }
    private void setConstraint3_2() throws IloException
    {

        for(int l = 0; l<p.getTravelingArcsSet().length; l++)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();

            // i
            for(int i=0;i<p.getDemand().length;i++)
            {
                Request od = in.getRequestSet().get(i);
                // theta
                for(int k=0;k<od.getNumberOfEmptyPath();k++)
                {
                    int j = od.getEmptyPathIndexes()[k];
                    left.addTerm(p.getArcAndPath()[l][j], zVar.get(i)[k]);
                }
            }

            // w
            for(int w=0;w<p.getVesselPathSet().length;w++)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                for(int h=0;h<p.getVesselSet().length;h++)
                {
                    left.addTerm(-p.getArcAndVesselPath()[l][w]
                                    *p.getVesselCapacity()[h]
                                    *p.getShipRouteAndVesselPath()[r][w]
                                    *p.getVesselTypeAndShipRoute()[h][r]
                            , vVar2[h][w]);
                }
            }
            cplex.addLe(left,0);
        }
    }

    // (29)
    // Containers flow conservation
    // Containers of each port p at each time t
    private void setConstraint4() throws IloException
    {
        TravelingArc arc;
        // p \in P
        for(int pp = 0; pp < p.getPortSet().length; pp++) {
            String port = p.getPortSet()[pp];
            // t \in T
            for(int t = 1; t < p.getTimePointSet().length; t++) {
                IloLinearNumExpr left = cplex.linearNumExpr();
                // i \in I
                for(int i = 0; i < p.getDemand().length; i++) {
                    Request od = in.getRequestSet().get(i);

                    // nn' \in A'
                    for(int nn = 0; nn < p.getTravelingArcsSet().length; nn++)
                    {
                        arc = in.getTravelingArcSet().get(nn);

                        // o(i)=p
                        if(od.getOriginPort().equals(port))
                        {
                            // In-Z
                            // \theta \in Theta_i
                            for(int k = 0; k < od.getNumberOfEmptyPath(); k++)
                            {
                                // p(n') = p
                                // 1 <= t(n') <= t
                                if(arc.getDestinationPort().equals(port)
                                        && arc.getDestinationTime() <= t
                                        && arc.getDestinationTime() >= 1)
                                {
                                    int j = od.getEmptyPathIndexes()[k];
                                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                }
                            }

                            // Out-X
                            // \phi \in Phi_i
                            for(int k = 0; k < od.getNumberOfLadenPath(); k++)
                            {
                                // p(n) = p
                                // 1 <= t(n) <= t
                                if(arc.getOriginPort().equals(port)
                                        && arc.getOriginTime() <= t
                                        && arc.getOriginTime() >= 1)
                                {
                                    int j = od.getLadenPathIndexes()[k];
                                    left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                }
                            }
                        }

                        // d(i)=p
                        else if(od.getDestinationPort().equals(port))
                        {
                            // In-X
                            // \phi \in Theta_i
                            for(int k = 0; k < od.getNumberOfLadenPath(); k++)
                            {
                                // p(n') = p
                                // 1 <= t(n') <= t-s_p
                                if(arc.getDestinationPort().equals(port)
                                        && arc.getDestinationTime() <= t - p.getTurnOverTime()[pp]
                                        && arc.getDestinationTime() >= 1)
                                {
                                    int j = od.getLadenPathIndexes()[k];
                                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                }
                            }

                            // Out-Z
                            // \phi \in Theta_i
                            for(int k = 0; k < od.getNumberOfEmptyPath(); k++)
                            {
                                // p(n) = p
                                // 1 <= t(n) <= t
                                if(arc.getOriginPort().equals(port)
                                        && arc.getOriginTime() <= t
                                        && arc.getOriginTime() >= 1)
                                {
                                    int j = od.getEmptyPathIndexes()[k];
                                    left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                }
                            }
                        }
                    }
                }
                cplex.addGe(left, -p.getInitialEmptyContainer()[pp]);
            }
        }
    }

    private void solveModel()
    {
        try
        {
            if (WhetherExportModel)
                exportModel();
            long startTime = System.currentTimeMillis();
            if (cplex.solve())
            {
                long endTime = System.currentTimeMillis();

                int[][]  vvv =new int [p.getVesselSet().length][p.getShippingRouteSet().length];
                for (int i = 0; i < p.getShippingRouteSet().length; i++) {
                    for (int j = 0; j < p.getVesselSet().length; j++) {
                        vvv[j][i] = (int)(cplex.getValue(vVar[j][i]) + 0.5);
                    }
                }

                int[][]  vvv2 =new int [p.getVesselSet().length][p.getVesselPathSet().length];
                for (int w = 0; w < p.getVesselPathSet().length; w++) {
                    for (int j = 0; j < p.getVesselSet().length; j++) {
                        vvv2[j][w] = (int)(cplex.getValue(vVar2[j][w]) + 0.5);
                    }
                }
                setVVarValue(vvv);
                setvVarValue2(vvv2);


                setObjVal(cplex.getObjValue());
                setSolveTime(endTime - startTime);
                setObjGap(cplex.getMIPRelativeGap());

                if(WhetherPrintProcess){
                    printSolution();
                }
            }
            else
            {
                log.info("No solution");
            }
            cplex.end();
        }
        catch (IloException ex) {
            log.info("Concert Error: " + ex);
        }
    }
    private int[][] vVarValue2;

    public void setvVarValue2(int[][] vVarValue2) {
        this.vVarValue2 = vVarValue2;
    }
    public void printSolution(){
        log.info("Master Objective ="+String.format("%.2f", getObjVal()));
        System.out.print("VesselType Decision vVar (MP) : ");
        for(int r = 0; r<p.getShippingRouteSet().length; r++)
        {
            System.out.print(p.getShippingRouteSet()[r]+"(");
            for(int h=0;h<p.getVesselSet().length;h++)
            {
                if(vVarValue[h][r] != 0)
                {
                    System.out.print(p.getVesselSet()[h]+")\t");
                }
            }
        }

        System.out.print("Reactive Decision vVar2 (MP) : ");
        for(int w=0;w<p.getVesselPathSet().length;w++)
        {
            for(int h=0;h<p.getVesselSet().length;h++)
            {
                if(vVarValue2[h][w] != 0)
                {
                    System.out.print(p.getVesselPathSet()[w]+"("+p.getVesselSet()[h]+")\t");
                }
            }
        }
    }

}
