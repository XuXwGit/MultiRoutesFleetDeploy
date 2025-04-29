package multi.algos.BD;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.model.primal.DetermineModel;
import multi.model.dual.DualSubProblemReactive;
import multi.model.primal.MasterProblem;

import java.io.IOException;
import java.util.List;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class BDwithPapReactive extends BD {

    private DualSubProblemReactive dsp;
    public BDwithPapReactive(InputData in, Parameter p) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = p.getTau();
        this.Algo = "BD&PAP-Reactive";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() 
                                        + "-T" + p.getTimeHorizon() 
                                        + "-"+ DefaultSetting.FleetType 
                                        + "-S"+ DefaultSetting.randomSeed 
                                        + "-V" + DefaultSetting.VesselCapacityRange;
        frame();
    }
    public BDwithPapReactive(InputData in, Parameter p, int tau) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = tau;
        this.Algo = "BD&PAP-Reactive";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size()
                + "-T" + p.getTimeHorizon()
                + "-"+ DefaultSetting.FleetType
                + "-S" + DefaultSetting.randomSeed
                + "-V" + DefaultSetting.VesselCapacityRange;
        frame();
    }
    @Override
    protected double initialModel() throws IloException, IOException {
        double start = System.currentTimeMillis();

        dsp =new DualSubProblemReactive(in, p, tau);
        mp=new MasterProblem(in, p, "Reactive");

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
    protected void frame() throws IloException, IOException {
        initialize();

        if(DefaultSetting.WhetherAddInitializeSce) {
            initializeSce(sce);
        }

        // change  MaxVarDemand
        // beta = min(k, m/k)=tau

        double[] maxDemandVar = p.getMaximumDemandVariation();
        p.changeMaximumDemandVariation(tau);

        double time0 = System.currentTimeMillis();
        initialModel();

        printIterTitle(fileWriter, System.currentTimeMillis() - time0);
        printIteration(fileWriter, lower[iteration], upper[iteration],0, 0, 0,
                "--", 0, "--", 0 );

        // add the initial scene to make the MP feasible
        /*initializeSce(sce);*/
        int flag = 0;
        mp.addScene(sce.get(iteration));
        double start0 = System.currentTimeMillis();
        while(upperBound - lowerBound > DefaultSetting.boundGapLimit
                && flag == 0
                && iteration<DefaultSetting.maxIterationNum
                && (System.currentTimeMillis() - start0)/1000 < DefaultSetting.maxIterationTime
        )
        {
            double start1 = System.currentTimeMillis();
            mp.solveReactiveModel();
            double end1 = System.currentTimeMillis();

            // check if the mp-solution changed
            if(! addSolutionPool(mp.getSolution())){
                log.info("MP solution duplicate");
                flag=1;
            }

            // LB = max{LB , MP.Objective}
            // LB = MP.Objective = MP.OperationCost + Eta
            if(mp.getObjVal()>lowerBound
                    && mp.getSolveStatus() == IloCplex.Status.Optimal) {
                setLowerBound(mp.getObjVal());
            }

            dsp.changeObjectiveVCoefficients(mp.getVVarValue(), mp.getVVarValue2());
            double start2 = System.currentTimeMillis();
            dsp.solveModel();
            double end2 = System.currentTimeMillis();

            //  the SP is optimal :  add optimality cut
            if(dsp.getSolveStatus() == IloCplex.Status.Optimal )
            {
                //  update UB : UB = min{UB, MP.OperationCost + SP.Objective}
                if(dsp.getObjVal()+mp.getOperationCost()<upperBound)
                {
                    setUpperBound(dsp.getObjVal()+mp.getOperationCost());
                }

                // add optimality cut
                mp.addReactiveOptimalityCut(dsp.getConstantItem(), dsp.getBeta1Value(), dsp.getBeta2Value());

                // add worse case to scene set
                if(! addScenarioPool(dsp.getScene())){
                    sce.add(dsp.getScene());
                }
            }
            // the SP is unbounded : add feasibility cut
            else if(dsp.getSolveStatus() == IloCplex.Status.Unbounded)
            {
                // ! here beta is extreme ray !
                mp.addReactiveFeasibilityCut(dsp.getConstantItem(), dsp.getBeta1Value(), dsp.getBeta2Value());
            }

            iteration++;
            upper[iteration]=upperBound;
            lower[iteration]=lowerBound;

            if(DefaultSetting.WhetherPrintProcess || DefaultSetting.WhetherPrintIteration){
                log.info(iteration+"\t\t"
                        +String.format("%.2f", upper[iteration])+"\t\t"
                        +String.format("%.2f", lower[iteration])+"\t\t"
                        +String.format("%.2f", end2 - start2)+"\t\t"
                        +String.format("%.2f", end1 - start1)+"\t\t"
                        +String.format("%.2f",System.currentTimeMillis() - start0)+"\t\t"
                        +dsp.getSolveStatusString()+"("+String.format("%.4f", dsp.getMipGap())+")"+"\t\t"
                        +mp.getSolveStatusString()+"("+String.format("%.4f", mp.getObjGap())+")"
                );
            }
            if(DefaultSetting.WhetherWriteFileLog){
                fileWriter.write(iteration+"\t\t"
                        +String.format("%.2f", upper[iteration]) +"\t\t"
                        +String.format("%.2f", lower[iteration])+"\t\t"
                        +String.format("%.2f", end2 - start2)+"\t\t"
                        +String.format("%.2f", end1 - start1)+"\t\t"
                        +String.format("%.2f",System.currentTimeMillis() - start0)+"\t\t"
                        +dsp.getSolveStatusString()+"("+String.format("%.4f", dsp.getMipGap())+")"+"\t\t"
                        +mp.getSolveStatusString()+"("+String.format("%.4f", mp.getObjGap())+")"
                );
                fileWriter.write("\n");
            }
        }

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
}
