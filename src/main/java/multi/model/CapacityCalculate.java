package multi.model;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.Parameter;
import multi.model.primal.BasePrimalModel;
import multi.network.Request;

import java.util.ArrayList;


/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class CapacityCalculate extends BasePrimalModel {
    public CapacityCalculate(InputData in, Parameter p) {
        super();
        this.in = in;
        this.p = p;
        this.modelName = "CC" + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
        try{
            cplex = new IloCplex();
            publicSetting(cplex);
            frame();

            solveModel();
        }catch (IloException e)
        {
            e.printStackTrace();
        }
    }

    public void setDecisionVars() throws IloException
    {
        String varName;

        SetVesselDecisionVars();

        vVar =new IloIntVar [p.getShippingRouteSet().length][p.getVesselPathSet().length];
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            varName = "v("+ (r+1)+")("+(w+1)+")";
            vVar[r][w] = cplex.boolVar(varName);
        }


        xVar = new ArrayList<>();
        yVar = new ArrayList<>();
        zVar = new ArrayList<>();

        gVar =new IloNumVar [p.getDemand().length];




        for(int i=0;i<p.getDemand().length;i++)
        {
            Request od = in.getRequestSet().get(i);

            IloNumVar[] xxxVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] yyyVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] zzzVar_k = new IloNumVar[od.getNumberOfEmptyPath()];

            xVar.add(xxxVar_k);
            yVar.add(yyyVar_k);
            zVar.add(zzzVar_k);

            for (int j = 0; j < od.getNumberOfLadenPath(); j++) {
                varName = "x(" + (i+1) +")";
                xVar.get(i)[j]=cplex.numVar(0,Integer.MAX_VALUE, varName);
                varName = "y(" + (i+1) +")";
                yVar.get(i)[j]=cplex.numVar(0,Integer.MAX_VALUE, varName);
            }
            for (int j = 0; j < od.getNumberOfEmptyPath(); j++) {
                varName = "z(" + (i+1) +")";
                zVar.get(i)[j]=cplex.numVar(0,Integer.MAX_VALUE, varName);
            }

            varName = "g(" + (i+1) +")";
            gVar[i]=cplex.numVar(0,Integer.MAX_VALUE, varName);
        }
    }

    public void setObjectives() throws IloException
    {
        IloLinearNumExpr Obj=cplex.linearNumExpr();

        // item1 : Operating Cost
        // r∈R
        for(int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            Obj.addTerm(p.getShipRouteAndVesselPath()[r][w]
                    , vVar[r][w]	);
        }

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
                Obj.addTerm(p.getLadenPathDemurrageCost()[j], xVar.get(i)[k]);
                Obj.addTerm(p.getLadenPathDemurrageCost()[j], yVar.get(i)[k]);
                Obj.addTerm(p.getRentalCost()*p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
            }

            // item4: Demurrage of self-owned containers for empty path
            // \theta
            for(int k=0;k<od.getNumberOfEmptyPath();k++)
            {
                int j = od.getEmptyPathIndexes()[k];
                Obj.addTerm(p.getEmptyPathDemurrageCost()[j], zVar.get(i)[k]);
            }
        }

        cplex.addMinimize(Obj);
    }

    private IloRange[] C1;

    public void setConstraints() throws IloException
    {
        setConstraint1();
        setConstraint2();
        setConstraint3();
    }

     //(21)demand equation
    private void setConstraint1() throws IloException
    {
        C1 = new IloRange[p.getDemand().length];

        //∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            IloLinearNumExpr left=cplex.linearNumExpr();

            Request od = in.getRequestSet().get(i);
            //φ
            for(int k=0;k<od.getNumberOfLadenPath();k++)
            {
                left.addTerm(1, xVar.get(i)[k]);
                left.addTerm(1, yVar.get(i)[k]);
            }

            left.addTerm(1, gVar[i]);

            String ConstrName = "C1("+(i+1)+")";
            C1[i] = cplex.addEq(left ,p.getDemand()[i], ConstrName);
        }
    }

    //(22) VesselType Capacity Constraint
    private void setConstraint2() throws IloException    {
        // ∀<n,n'>∈A'
        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
        {
            IloLinearNumExpr left=cplex.linearNumExpr();

            // i∈I
            for(int i=0;i<p.getDemand().length;i++)
            {
                Request od = in.getRequestSet().get(i);

                // φ
                for(int k=0; k<od.getNumberOfLadenPath(); k++)
                {
                    int j = od.getLadenPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                    left.addTerm(p.getArcAndPath()[nn][j], yVar.get(i)[k]);
                }

                //θ
                for(int k=0;k<od.getNumberOfEmptyPath();k++)
                {
                    int j = od.getEmptyPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                }
            }

            // vessel capacity
            // r∈R
            // ω∈Ω
            for(int w=0;w<p.getVesselPathSet().length;w++)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                left.addTerm(-p.getArcAndVesselPath()[nn][w]
                                *p.getShipRouteAndVesselPath()[r][w]
                        , vVar[r][w]	);
            }
            String ConstrName = "C3"+"("+(nn+1)+")";
            cplex.addLe(left,0, ConstrName);
        }
    }

    // (24)Containers flow conservation
    private void setConstraint3() throws IloException
    {
        // p \in P
        for(int pp = 0; pp < p.getPortSet().length; pp++)
        {
            // t \in T
            for(int t = 1; t < p.getTimePointSet().length; t++)
            {
                IloLinearNumExpr left = cplex.linearNumExpr();

                // i \in I
                for(int i = 0; i < p.getDemand().length; i++)
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
                String ConstrName = "C3("+(pp+1)+")("+(t)+")";
                cplex.addGe(left, -p.getInitialEmptyContainer()[pp], ConstrName);
            }
        }
    }

    public void solveModel()
    {
        try
        {
            if (DefaultSetting.WhetherExportModel) {
                exportModel();
            }
            if (cplex.solve())
            {
//                printDetail();
                setObjVal(cplex.getObjValue());
                setMinV();
                changeDemandVaration();
                if (cplex.solve())
                {
//                    printDetail();
                    setMaxV();
                }
                else
                {
                    log.info("Exit an error");
                }
                printSolution();
            }
            else
            {
                log.info("No Solution");
            }
        }
        catch (IloException ex)
        {
            log.info("Concert Error: " + ex);
        }
    }

    private void changeDemandVaration() throws IloException {
        for (int i = 0; i < p.getDemand().length; i++) {
            C1[i].setBounds(p.getDemand()[i]+p.getMaximumDemandVariation()[i]
                    ,p.getDemand()[i]+p.getMaximumDemandVariation()[i] );
        }
    }

    public void setMinV() throws IloException {
        minV = new  int[p.getShippingRouteSet().length][p.getVesselPathSet().length];
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            minV[r][w] =  (int) cplex.getValue(vVar[r][w]);
        }
    }
    public void setMaxV() throws IloException {
        maxV = new  int[p.getShippingRouteSet().length][p.getVesselPathSet().length];
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            maxV[r][w] =  (int) cplex.getValue(vVar[r][w]);
        }
    }
    private int[][] minV;
    private int[][] maxV;
    public void printSolution()    {
        log.info("VesselType Decision vVar : ");
        for(int r = 0; r<p.getShippingRouteSet().length; r++)
        {
            System.out.print(p.getShippingRouteSet()[r]+":\t");
            for (int w = 0; w < p.getVesselPathSet().length; w++) {
                if(p.getShipRouteAndVesselPath()[r][w] != 0)
                {
                    System.out.print(p.getVesselPathSet()[w]);
                    System.out.print("("+minV[r][w] + "~" + maxV[r][w] + ")\t");
                }
            }
        }
    }
    public void printDetail() throws IloException {
        for (int i = 0; i < p.getDemand().length; i++) {
            System.out.print("Demand"+(i+1)
                    +"("+in.getRequestSet().get(i).getOriginPort()
                    +"->"+in.getRequestSet().get(i).getDestinationPort()+")"
                    +"("+in.getRequestSet().get(i).getEarliestPickupTime()
                    +"->"+in.getRequestSet().get(i).getLatestDestinationTime()+")"
                    +":\t"
                    +p.getDemand()[i]+" \t=\t");

            double totalX = 0;
            double totalY = 0;
            Request od = in.getRequestSet().get(i);
            //φ
            for(int k=0;k<od.getNumberOfLadenPath();k++)
            {
                totalX += cplex.getValue(xVar.get(i)[k]);
                totalY += cplex.getValue(yVar.get(i)[k]);
            }

            System.out.print(totalX+"\t\t");
            System.out.print(totalY+"\t\t");

            log.info(cplex.getValue(gVar[i]) + "\t");

        }
    }
}
