package multi.algos.CCG;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.model.primal.DetermineModel;
import multi.model.dual.DualSubProblem;
import multi.model.primal.MasterProblem;
import multi.model.primal.SubProblem;

import java.io.IOException;
import java.util.List;
/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class CCGwithPAP extends CCG {
    public CCGwithPAP(InputData in, Parameter p) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = p.getTau();
        this.Algo = "CCG&PAP";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed + "-V" + VesselCapacityRange;
        frame();
    }
    public CCGwithPAP(InputData in, Parameter p, int tau) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = tau;
        this.Algo = "CCG&PAP";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed + "-V" + VesselCapacityRange;
        frame();
    }

    @Override
    protected void frame() throws IloException, IOException {
        initialize();

        double[] maxDemandVar = p.getMaximumDemandVariation();
        initializeSce(sce);

        double masterObjective;
        int flag=0;

        double time0 = System.currentTimeMillis();
        WhetherAddInitializeSce = true;
        initialModel();

        printIterTitle(fileWriter, System.currentTimeMillis() - time0);
        printIteration(fileWriter, lower[0], upper[0],
                0, 0, 0,
                "--", 0, "--", 0);

        double start0 = System.currentTimeMillis();
        while(upperBound - lowerBound > boundGapLimit
                && flag==0
                && iteration<maxIterationNum
                && (System.currentTimeMillis() - start0)/1000 < maxIterationTime
        ) {
            // build and solve master model
            // add new scene to Master Problem
            if (iteration != 0){
                mp.addScene(sce.get(sce.size()-1));
            }

            double start1 = System.currentTimeMillis();
            mp.solveModel();
            double end1 = System.currentTimeMillis();

            // get the solution
            masterObjective = mp.getObjVal();
            setOperationCost(mp.getOperationCost());
            setTotalCost(mp.getObjVal());

            // check if the mp-solution changed
            if(! addSolutionPool(mp.getSolution())){
                flag=1;
            }

            // update lower bound: LB = max {LB, Obj*}
            if(mp.getObjVal()>lowerBound
                    && mp.getSolveStatus() == IloCplex.Status.Optimal) {
                setLowerBound(mp.getObjVal());
            }

            dsp.changeObjectiveVvarsCoefficients(mp.getVVarValue());

            double start2 = System.currentTimeMillis();
            dsp.solveModel();
            double end2 = System.currentTimeMillis();

            if(addScenarioPool(dsp.getScene())){
                sce.add(dsp.getScene());
            }
            else{
                flag=2;
            }

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
                    dsp.getSolveStatusString(), dsp.getObjGap(), mp.getSolveStatusString(), mp.getObjGap());
        }

        if(flag == 1){
            log.info("MP solution duplicate");
        }
        else if(flag == 2){
            log.info("Worse case duplicate");
        }

        setTotalCost(upperBound);
        setOperationCost(mp.getObjVal() - mp.getEtaValue());

        p.setMaximumDemandVariation(maxDemandVar);

        setAlgoResult();
        end();


        if(CCG_PAP_Use_Sp){
            Long start1 = System.currentTimeMillis();
            SubProblem sp = new SubProblem(in, p);
            sp.changeConstraintCoefficients(mp.getVVarValue(), dsp.getUValue());
            sp.solveModel();
            sp.end();

            if(WhetherPrintProcess || WhetherPrintSolveTime){
                Long end1 = System.currentTimeMillis();
                log.info("SubProblem Time = "+ (end1 - start1));
            }

            setLadenCost(sp.getLadenCost());
            setEmptyCost(sp.getEmptyCost());
            setRentalCost(sp.getRentalCost());
            setPenaltyCost(sp.getPenaltyCost());
        }
    }

    @Override
protected double initialModel() throws IloException, IOException {
    dsp =new DualSubProblem(in, p, 1);
    mp=new MasterProblem(in, p);

    if(WhetherAddInitializeSce){
        mp.addScene(sce.get(0));
    }

    if(WhetherSetInitialSolution){
        DetermineModel dm = new DetermineModel(in, p);
        mp.setInitialSolution(dm.getVVarValue());
    }
    return 0;
}
    @Override
    protected void initializeSce(List<Scenario> sce)
    {
        // beta = min{k , I/k}
        double beta=(double)tau > p.getDemand().length/(double)tau ?
                p.getDemand().length/(double)tau : (double)tau;
        p.changeMaximumDemandVariation(beta);

        double[] sss  =new double [in.getRequestSet().size()];
        // v = tau/I * e  --> |e| = tau/I --> e_i = tau/I * 1/sqrt(I)
        for(int i=0;i<p.getDemand().length;i++)
        {
            sss[i]=(double)tau/ p.getDemand().length * (1.0/ (Math.sqrt(p.getDemand().length)));
        }

        sce.add(new Scenario(sss));
    }
}
