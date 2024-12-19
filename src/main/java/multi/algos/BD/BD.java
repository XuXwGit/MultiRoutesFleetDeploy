package multi.algos.BD;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.InputData;
import multi.Parameter;
import multi.algos.AlgoFrame;

import java.io.IOException;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class BD extends AlgoFrame {
	public BD(InputData in, Parameter p) throws IloException, IOException {
		super();
		this.in = in;
		this.p = p;
		this.tau = p.getTau();
		this.Algo = "BD";
		this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size()
				+ "-T" + p.getTimeHorizon()
				+ "-"+ FleetType
				+ "-S" + randomSeed
				+ "-V" + VesselCapacityRange;
		frame();
	}
	public BD(InputData in, Parameter p, int tau) throws IloException, IOException {
		super();
		this.in = in;
		this.p = p;
		this.tau = tau;
		this.Algo = "BD";
		this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size()
				+ "-T" + p.getTimeHorizon()
				+ "-"+ FleetType
				+ "-S" + randomSeed
				+ "-V" + VesselCapacityRange;
		frame();
	}
	public BD() {
	}

	@Override
	protected void frame() throws IOException, IloException {
		initialize();

		if(WhetherAddInitializeSce){
			initializeSce(sce);
		}

		double time0 = System.currentTimeMillis();
		initialModel();

		printIterTitle(fileWriter, System.currentTimeMillis() - time0);
		printIteration(fileWriter, lower[iteration], upper[iteration],0, 0, 0,
				"--", 0, "--", 0 );

		int flag = 0;
		double start0 = System.currentTimeMillis();
		while(upperBound - lowerBound > boundGapLimit
				&& flag == 0
				&& iteration<maxIterationNum
				&& (System.currentTimeMillis() - start0)/1000 < maxIterationTime
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

			dsp.changeObjectiveVvarsCoefficients(mp.getVVarValue());
			double start2 = System.currentTimeMillis();
			dsp.solveModel();
			double end2 = System.currentTimeMillis();

			if(!updateBoundAndMP()){
				flag = 3;
			}

			iteration++;
			upper[iteration]=upperBound;
			lower[iteration]=lowerBound;

			printIteration(fileWriter, lower[iteration], upper[iteration],
					end2 - start2, end1 - start1, System.currentTimeMillis() - start0,
					dsp.getSolveStatusString(), dsp.getObjGap(),
					mp.getSolveStatusString(), mp.getObjGap());
		}

		// end the loop
		if(flag == 1){
			log.info("MP solution duplicate");
		}
		else if(flag == 2){
			log.info("Worse case duplicate");
		}
		else if(flag == 3){
			log.info("DSP solution infeasible");
		}

		setAlgoResult();
		end();
	}

	@Override
	public boolean updateBoundAndMP() throws IloException {
		//  the SP is optimal :  add optimality cut
		if(dsp.getSolveStatus() == IloCplex.Status.Optimal)
		{
			//log.info("DSP is Optimal");
			//  update UB : UB = min{UB, MP.OperationCost + SP.Objective}
			if(dsp.getObjVal()+mp.getOperationCost()<upperBound)
			{
				setUpperBound(dsp.getObjVal()+mp.getOperationCost());
			}
			// add optimality cut
			//mp.addOptimalityCut(dsp.getConstantItem(), dsp.getBetaValue());
			mp.getCplex().add(dsp.constructOptimalCut(mp.getCplex(), mp.getVVars(), mp.getEtaVar()));
			// add the worst scene (extreme point) to scene set
			if(! addScenarioPool(dsp.getScene())){
				sce.add(dsp.getScene());
			}
		}
		else if(dsp.getSolveStatus() == IloCplex.Status.Feasible){
			log.info("DSP is Feasible");
			return false;
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
		return true;
	}
}
