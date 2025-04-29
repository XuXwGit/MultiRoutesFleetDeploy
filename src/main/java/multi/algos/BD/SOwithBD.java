package multi.algos.BD;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.algos.AlgoFrame;
import multi.model.primal.DetermineModel;
import multi.model.dual.DualProblem;
import multi.model.primal.MasterProblem;

import java.io.IOException;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SOwithBD extends AlgoFrame {
    private DualProblem dp;

    public SOwithBD(InputData in, Parameter p) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = p.getTau();
        this.Algo = "SO&BD";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() 
                                + "-T" + p.getTimeHorizon() 
                                + "-"+ DefaultSetting.FleetType 
                                + "-S" + DefaultSetting.randomSeed 
                                + "-V" + DefaultSetting.VesselCapacityRange;
        frame();
    }

    public SOwithBD() {
    }
    @Override
    protected double initialModel() throws IloException, IOException {
        start = System.currentTimeMillis();

        dp = new DualProblem(in, p);
        mp=new MasterProblem(in, p, "Stochastic");

        if(DefaultSetting.WhetherAddInitializeSce){
            mp.addScene(sce.get(0));
        }

        if(DefaultSetting.WhetherSetInitialSolution){
            DetermineModel dm = new DetermineModel(in, p);
            mp.setInitialSolution(dm.getVVarValue());
        }

        return System.currentTimeMillis() - start;
    }
    @Override
    protected void frame() throws IOException, IloException {
        initialize();

        if(DefaultSetting.WhetherAddInitializeSce) {
            initializeSce(sce);
        }

        double time0 = System.currentTimeMillis();
        initialModel();

        printIterTitle(fileWriter, System.currentTimeMillis() - time0);
        printIteration(fileWriter, lower[iteration], upper[iteration],0, 0, 0 );

        int flag = 0;
        double start0 = System.currentTimeMillis();
        while(upperBound - lowerBound > DefaultSetting.boundGapLimit
                && flag == 0
                && iteration<DefaultSetting.maxIterationNum
                && (System.currentTimeMillis() - start0)/1000 < DefaultSetting.maxIterationTime
        )
        {
            double start1 = System.currentTimeMillis();
            mp.solveModel();
            double end1 = System.currentTimeMillis();

            // check if the mp-solution changed
            if(! addSolutionPool(mp.getSolution())){
                flag=1;
            }

            // LB = max{LB , MP.Objective}
            // LB = MP.Objective = MP.OperationCost + Eta
            if(mp.getObjVal()>lowerBound
                    && mp.getSolveStatus() == IloCplex.Status.Optimal) {
                setLowerBound(mp.getObjVal());
            }

            double total_sp_cost = 0;
            dp.changeObjectiveVvarsCoefficients(mp.getVVarValue());
            double start2 = System.currentTimeMillis();
            for(int i=0; i<p.getSampleScenes().length; i++){
                dp.changeObjectiveUvarsCoefficients(p.getSampleScenes()[i]);
                dp.solveModel();
                total_sp_cost += dp.getObjVal();
                mp.getCplex().add(dp.constructOptimalCut(mp.getCplex(), mp.getVVars(), mp.getEtaVars()[i]));
            }
            double end2 = System.currentTimeMillis();

            if(total_sp_cost/p.getSampleScenes().length+mp.getOperationCost()<upperBound)
            {
                setUpperBound(total_sp_cost/p.getSampleScenes().length+mp.getOperationCost());
            }

            iteration++;
            upper[iteration]=upperBound;
            lower[iteration]=lowerBound;

            printIteration(fileWriter, lower[iteration], upper[iteration],
                    end2 - start2, end1 - start1, System.currentTimeMillis() - start0);
        }

        // end the loop
        if(flag == 1){
            log.info("MP solution duplicate");
        }
        else if(flag == 2){
            log.info("Worse case duplicate");
        }

        setAlgoResult();
        end();
    }

    @Override
    protected void endModel() {
        mp.end();
        dp.end();
    }
}
