package multi.algos.BD;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.model.dual.DualSubProblem;
import multi.model.primal.MasterProblem;

import java.io.IOException;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class BranchAndBenders extends BD {
    public BranchAndBenders(InputData in, Parameter p, int tau) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = tau;
        this.Algo = "Branch&Benders";
        frame();
    }

    @Override
    protected void frame() throws IloException, IOException {
        initialize();

        double time0 = System.currentTimeMillis();
        DualSubProblem dsp =new DualSubProblem(in, p, tau);
        IloCplex cplex = new IloCplex();
        MasterProblem mp=new MasterProblem(cplex, in, p);

        printIterTitle(fileWriter, System.currentTimeMillis() - time0);
        printIteration(fileWriter, lower[iteration], upper[iteration],0, 0, 0,
                "--", 0, "--", 0 );

        cplex.setParam(IloCplex.Param.MIP.Strategy.Search, IloCplex.MIPSearch.Traditional);
        cplex.use(new BendersLazyConsCallback(cplex, mp.getVVars(), mp.getEtaVar(), dsp, SolutionPool));

        // add the initial scene to make the MP feasible
        /*initializeSce(sce);
        mp.addScene(sce.get(iteration));*/
        int flag = 0;
        double start0 = System.currentTimeMillis();
        while(upperBound - lowerBound > DefaultSetting.boundGapLimit
                && flag == 0
                && iteration< DefaultSetting.maxIterationNum
                && (System.currentTimeMillis() - start0) / 1000 < DefaultSetting.maxIterationTime
        )
        {
            double start1 = System.currentTimeMillis();
            mp.solveModel();
            double end1 = System.currentTimeMillis();

            // LB = max{LB , MP.Objective}
            // LB = MP.Objective = MP.OperationCost + Eta
            if(mp.getObjVal()>lowerBound
                    && mp.getSolveStatus() == IloCplex.Status.Optimal) {
                setLowerBound(mp.getObjVal());
            }

            dsp.changeObjectiveVvarsCoefficients(mp.getVVarValue());
            double start2 = System.currentTimeMillis();
            dsp.solveModel();
            double end2 = System.currentTimeMillis();

            //  the SP is optimal :  add optimality cut
            if(dsp.getSolveStatus() == IloCplex.Status.Optimal
                    || dsp.getSolveStatus() == IloCplex.Status.Feasible)
            {

                //  update UB : UB = min{UB, MP.OperationCost + SP.Objective}
                if(dsp.getObjVal()+mp.getOperationCost()<upperBound)
                {
                    setUpperBound(dsp.getObjVal()+mp.getOperationCost());
                }

                // add optimality cut
                mp.addOptimalityCut(dsp.getConstantItem(), dsp.getBetaValue());

                // add the worst scene (extreme point) to scene set
                if(! addScenarioPool(dsp.getScene())){
                    sce.add(dsp.getScene());
                }
            }
            // the SP is unbounded : add feasibility cut
            else if(dsp.getSolveStatus() == IloCplex.Status.Unbounded)
            {
                log.info("DSP is Unbounded");
                // ! here beta is extreme ray !
                mp.addFeasibilityCut(dsp.getConstantItem(), dsp.getBetaValue());
            }

            else if(dsp.getSolveStatus() == IloCplex.Status.Infeasible)
            {
                log.info("DSP is InFeasible");
            }

            else if(dsp.getSolveStatus() == IloCplex.Status.Bounded)
            {
                log.info("DSP is Bounded");
            }

            else {
                log.info("DSP is error");
            }

            iteration=iteration+1;
            upper[iteration]=upperBound;
            lower[iteration]=lowerBound;

            printIteration(fileWriter, lower[iteration], upper[iteration],
                    end2 - start2, end1 - start1, System.currentTimeMillis() - start0,
                    dsp.getSolveStatusString(), dsp.getObjGap(), mp.getSolveStatusString(), mp.getObjGap());
        }

        setAlgoResult();
        end();
    }
}
