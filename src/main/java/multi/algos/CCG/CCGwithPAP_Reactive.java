package multi.algos.CCG;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.model.primal.DetermineModel;
import multi.model.dual.DualSubProblemReactive;
import multi.model.primal.MasterProblem;
import multi.model.primal.SubProblemReactive;

import java.io.IOException;
import java.util.List;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class CCGwithPAP_Reactive  extends CCG {
    private DualSubProblemReactive dsp;
    public CCGwithPAP_Reactive(InputData in, Parameter p) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = p.getTau();
        this.Algo = "CCG&PAP-Reactive";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed + "-V" + VesselCapacityRange;
        frame();
    }
    public CCGwithPAP_Reactive(InputData in, Parameter p, int tau) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = tau;
        this.Algo = "CCG&PAP-Reactive";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed + "-V" + VesselCapacityRange;
        frame();
    }
    @Override
    protected double initialModel() throws IloException, IOException {
        double start = System.currentTimeMillis();

        dsp =new DualSubProblemReactive(in, p, tau);
        mp=new MasterProblem(in, p, "Reactive");

        if(WhetherAddInitializeSce){
            mp.addScene(sce.get(0));
        }

        if(WhetherSetInitialSolution){
            DetermineModel dm = new DetermineModel(in, p);
            mp.setInitialSolution(dm.getVVarValue());
        }

        return System.currentTimeMillis() - start;
    }

    @Override
    protected void frame() throws IloException, IOException {
        initialize();

        if(WhetherCalculateMeanPerformance && UseHistorySolution){
            calculateMeanPerformance();
            return;
        }

        double[] maxDemandVar = p.getMaximumDemandVariation();
        // change  MaxVarDemand
        // beta = min(k, m/k)
        double beta=(double)tau > p.getDemand().length/(double)tau ?
                p.getDemand().length/(double)tau : (double)tau;
        p.changeMaximumDemandVariation(beta);

        if(WhetherAddInitializeSce) {
            initializeSce(sce);
        }

        double masterObjective;

        double time0 = System.currentTimeMillis();
        initialModel();

        printIterTitle(fileWriter, System.currentTimeMillis() - time0);
        printIteration(fileWriter, lower[0], upper[0],
                0, 0, 0,
                "--", 0, "--", 0);

        /*initializeSce(sce);*/
        int flag=0;
        double start0 = System.currentTimeMillis();
        while(upperBound - lowerBound > boundGapLimit
                && flag==0
                && iteration<maxIterationNum
                && (System.currentTimeMillis() - start0)/1000 < maxIterationTime
        ){
            // build and solve master model
            // add new scene to Master Problem
            if (iteration != 0)
            {
                mp.addScene(sce.get(sce.size()-1));
            }

            double start1 = System.currentTimeMillis();
            mp.solveReactiveModel();
            double end1 = System.currentTimeMillis();

            // get the solution
            masterObjective = mp.getObjVal();
            this.setOperationCost(mp.getOperationCost());
            this.setTotalCost(mp.getObjVal());

            // check if the mp-solution changed
            if(! addSolutionPool(mp.getSolution())){
                log.info("MP solution duplicate");
                flag=1;
            }

            // update lower bound: LB = max {LB, Obj*}
            if(mp.getObjVal()>lowerBound
                    && mp.getSolveStatus() == IloCplex.Status.Optimal) {
                setLowerBound(mp.getObjVal());
            }

            dsp.changeObjectiveVCoefficients(mp.getVVarValue(), mp.getVVarValue2());
            double start2 = System.currentTimeMillis();
            dsp.solveModel();
            double end2 = System.currentTimeMillis();

            if(addScenarioPool(dsp.getScene())){
                sce.add(dsp.getScene());
            }
            else{
                flag=1;
            }

            SubProblemReactive sp = new SubProblemReactive(in, p);
            sp.changeConstraintCoefficients(mp.getVVarValue(), mp.getVVarValue2(), dsp.getScene().getRequest());
            sp.solveModel();
            sp.end();
//            log.info("SP-Obj = "+sp.getObjective());

            if(dsp.getObjVal()+mp.getOperationCost() < upperBound
                    && dsp.getSolveStatus() == IloCplex.Status.Optimal)
            {
                setUpperBound(dsp.getObjVal()+mp.getOperationCost());
            }

            iteration++;
            upper[iteration]=upperBound;
            lower[iteration]=lowerBound;
            masterObj[iteration] = masterObjective;
            subObj[iteration] = dsp.getObjVal();

            printIteration(fileWriter, lower[iteration], upper[iteration],
                    end2 - start2, end1 - start1, System.currentTimeMillis() - start0,
                    dsp.getSolveStatusString(), dsp.getMipGap(), mp.getSolveStatusString(), mp.getObjGap());
        }

        setTotalCost(upperBound);
        setOperationCost(mp.getObjVal() - mp.getEtaValue());
        setvValue2(mp.getVVarValue2());

        setAlgoResult();

        end();

        p.setMaximumDemandVariation(maxDemandVar);
    }

    @Override
    protected void initializeSce(List<Scenario> sce)
    {
        double[] sss  =new double [in.getRequestSet().size()];

        // |v| = tau/I |e| = tau/I
        double v=(double)tau/(double)p.getDemand().length * 1/ (Math.sqrt(p.getDemand().length));
        for(int i=0;i<p.getDemand().length;i++)
        {
            sss[i]=v ;
        }

        sce.add(new Scenario(sss));
    }
    public void setvValue2(int[][] vValue2) {
        this.vValue2 = vValue2;
    }
    private int[][] vValue2;

    public void printSolution(){
        log.info("Master Objective ="+String.format("%.2f", getObjVal()));

        System.out.print("VesselType Decision vVar (MP) : ");
        for(int r = 0; r<p.getShippingRouteSet().length; r++)
        {
            System.out.print(p.getShippingRouteSet()[r]+"(");
            for(int h=0;h<p.getVesselSet().length;h++)
            {
                if(vValue[h][r] != 0)
                {
                    System.out.print(p.getVesselSet()[h]+")\t");
                }
            }
        }
        log.info("Reactive Decision vVar2 (MP) : ");
        for(int w=0;w<p.getVesselPathSet().length;w++)
        {
            for(int h=0;h<p.getVesselSet().length;h++)
            {
                if(vValue2[h][w] != 0)
                {
                    log.info(p.getVesselPathSet()[w]+"("+p.getVesselSet()[h]+")\t");
                }
            }
        }
    }
}