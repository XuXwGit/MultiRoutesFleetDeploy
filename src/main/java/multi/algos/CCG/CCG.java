package multi.algos.CCG;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.InputData;
import multi.Parameter;
import multi.Scenario;
import multi.algos.AlgoFrame;

import java.io.IOException;
import java.util.List;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class CCG extends AlgoFrame {
	public CCG(InputData in, Parameter p) throws IloException, IOException {
		super();
		this.in = in;
		this.p = p;
		this.tau = p.getTau();
		this.Algo = "CCG";
		this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed + "-V" + VesselCapacityRange;
		frame();
	}
	public CCG(InputData in, Parameter p, int tau) throws IloException, IOException {
		super();
		this.in = in;
		this.p = p;
		this.tau = tau;
		this.Algo = "CCG";
		this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed + "-V" + VesselCapacityRange;
		frame();
	}

	public CCG() {
	}

	@Override
	protected void frame() throws IloException, IOException {
		initialize();

		if(WhetherCalculateMeanPerformance && UseHistorySolution){
			calculateMeanPerformance();
			return;
		}

		if(WhetherAddInitializeSce) {
			initializeSce(sce);
		}

		double time0 = System.currentTimeMillis();

		initialModel();

		printIterTitle(fileWriter, System.currentTimeMillis() - time0);
		printIteration(fileWriter, lower[0], upper[0],0, 0, 0,
				"--", 0, "--", 0);

		int flag = 0;
		double start0 = System.currentTimeMillis();
		while(upperBound - lowerBound > boundGapLimit
				&& flag == 0
				&& iteration<maxIterationNum
				&& (System.currentTimeMillis() - start0)/1000 < maxIterationTime
		){
			// add new scene to Master Problem
			if (iteration != 0)
			{
				mp.addScene(sce.get(sce.size()-1));
			}

			double start1 = System.currentTimeMillis();
			mp.solveModel();
			double end1 = System.currentTimeMillis();

			if(! addSolutionPool(mp.getSolution())){
				flag=1;
			}

			// MP >> the primal problem after relax some constraints
			// So : LP = MP - Obj
			if(mp.getObjVal()>lowerBound
					&& mp.getSolveStatus() == IloCplex.Status.Optimal) {
				setLowerBound(mp.getObjVal());
			}

			// solve dual sub problem
			dsp.changeObjectiveVvarsCoefficients(mp.getVVarValue());
			double start2 = System.currentTimeMillis();
			dsp.solveModel();
			double end2 = System.currentTimeMillis();

			//  update UB : UB = min{UB, MP.OperationCost + SP.Objective}
			if(dsp.getObjVal()+mp.getOperationCost() < upperBound
					&& dsp.getSolveStatus() == IloCplex.Status.Optimal){
				setUpperBound(dsp.getObjVal()+mp.getOperationCost());
			}

			if(addScenarioPool(dsp.getScene())){
				sce.add(dsp.getScene());
			}
			else{
				flag=1;
			}

			iteration++;
			upper[iteration] = upperBound;
			lower[iteration] = lowerBound;

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

		setAlgoResult();
		end();
	}

	@Override
	protected void initializeSce(List<Scenario> sce)
	{
		double [] sss =new double [in.getRequestSet().size()];
		for(int i=0;i<tau;i++)
		{
			sss[i]=1;
		}

		sce.add(new Scenario(sss));
	}
}
