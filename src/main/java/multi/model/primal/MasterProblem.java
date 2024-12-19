package multi.model.primal;

import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.List;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import multi.InputData;
import multi.Parameter;
import multi.network.Request;
import multi.Scenario;
/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class MasterProblem extends BasePrimalModel
{
	private IloIntVar[][] vVar2;
	private IloNumVar EtaVar;
	private IloNumVar[] etaVars;
	private int[][] vVarValue2;
	private double etaValue;
	public MasterProblem(IloCplex _cplex, InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.modelName = "MP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		try{
			cplex = _cplex;
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}

	public MasterProblem(InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.modelName = "MP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}
	public MasterProblem(InputData in, Parameter p, String type) {
		super();
		this.in = in;
		this.p = p;
		try {
				if(type == "Reactive") {
					cplex = new IloCplex();

					publicSetting(cplex);

					// create basic decision and add basic constraints
					// V[h][r]
					//V[h][w]
					setReactiveDecisionVars();
					setReactiveObjectives();
					setConstraints();
				} else if (type == "Stochastic") {
					cplex = new IloCplex();

					publicSetting(cplex);

					// create basic decision and add basic constraints
					// V[h][r]
					//V[h][w]
					setStochasticDecisionVars();
					setObjectives();
					setConstraints();
				}
			}catch (IloException e) {
				e.printStackTrace();
		}
	}

	// set V[h][r]
	protected void setDecisionVars() throws IloException
	{
		// first-stage variable :
		// v[h][r] : binary variable ���� whether vessel type h is assigned to shipping route r
		SetVesselDecisionVars();

		// eta : auxiliary decision variable ���� the upper bound of second-stage objective under all scene
		EtaVar =cplex.numVar(0,Integer.MAX_VALUE, "Eta");
	}
	protected void setStochasticAuxiliaryDecisionVars() throws IloException {
		etaVars = new IloNumVar[p.getSampleScenes().length];
		for(int k=0;k<p.getSampleScenes().length;++k)
		{
			etaVars[k]=cplex.numVar(0,Integer.MAX_VALUE, "Eta"+k);
		}
		// eta : auxiliary decision variable ���� the upper bound of second-stage objective under all scene
		// add connect constraint
		// Eta = 1/numSamples * sum(eta[k])
		IloLinearNumExpr left = cplex.linearNumExpr();
		for(int k=0;k<p.getSampleScenes().length;++k)
		{
			left.addTerm(1.0/p.getSampleScenes().length, etaVars[k]);
		}
		cplex.addEq(EtaVar, left);
	}
	private void setStochasticDecisionVars() throws IloException
	{
		setDecisionVars();
		setStochasticAuxiliaryDecisionVars();
	}
	private void setReactiveDecisionVars() throws IloException
	{
		String varName;
		// first-stage variable :
		// v[h][r] : binary variable ���� whether vessel type h is assigned to shipping route r
		SetVesselDecisionVars();

		// first-stage variable :
		// v[h][w] : binary variable ���� whether vessel type h is assigned to shipping route r
		// eta : auxiliary decision variable ���� the upper bound of second-stage objective under all scene
		vVar2 =new IloIntVar [p.getVesselSet().length] [p.getVesselPathSet().length];
		// V[h][w]
		for(int h=0;h<p.getVesselSet().length;++h)
		{
			for(int w=0;w<p.getVesselPathSet().length;++w)
			{
				varName = "V("+(p.getVesselSet()[h])+")("+(p.getVesselPathSet()[w])+")";
				vVar2[h][w]=cplex.boolVar(varName);
			}
		}

		// eta : auxiliary decision variable ���� the upper bound of second-stage objective under all scene
		EtaVar =cplex.numVar(0,Integer.MAX_VALUE, "Yita");
	}

	public IloIntVar[][] getVVars(){
		return vVar;
	}

	public IloNumVar getEtaVar(){
		return EtaVar;
	}
	public IloNumVar[] getEtaVars(){
		return etaVars;
	}

	protected void setObjectives() throws IloException
	{
		IloLinearNumExpr Obj=cplex.linearNumExpr();

		// add fixed operating cost to maintain shipping route
		Obj = GetVesselOperationCostObj(Obj);

		Obj.addTerm(1, EtaVar);

		cplex.addMinimize(Obj);
	}
	private void setReactiveObjectives() throws IloException
	{
		IloLinearNumExpr Obj=cplex.linearNumExpr();

		Obj = GetVesselOperationCostObj(Obj);

		// add fixed operating cost to maintain shipping route
		// r��R
		// w
		for (int w = 0; w < p.getVesselPathSet().length; ++w)
		{
			int r = in.getVesselPathSet().get(w).getRouteID() - 1;
			// r(��) == r
			// h�ʦ�
			for (int h = 0; h < p.getVesselSet().length; ++h)
			{
				// vesselTypeAndShipRoute == 1 : r(h) = r
				Obj.addTerm(p.getVesselTypeAndShipRoute()[h][r]
								*p.getShipRouteAndVesselPath()[r][w]
								* p.getVesselOperationCost()[h]
						, vVar2[h][w]);
			}
		}

		Obj.addTerm(1, EtaVar);

		cplex.addMinimize(Obj);
	}

	//		"set basic Constraint for MasterProblem start!"
	protected void setConstraints() throws IloException{
		// each vessel route assigns one type of vessel
		setConstraint1();
	}

	/*
	 * vessel assignment constraint: Sum_h V[h][r] = 1  /  Sum_h V[h][w] = 1
	 *
	 * */

	private void setConstraint1() throws IloException
	{
		setVesselConstraint();
	}

	/*
	cutting plane for scene k
	 */
	private void setConstraint0(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar, List<IloNumVar[]> zVar, IloNumVar[] gVar) throws IloException
	{
		IloLinearNumExpr left = cplex.linearNumExpr();

		left = GetRequestTransCostObj(left, xVar, yVar, zVar, gVar);

		left.addTerm(-1, EtaVar);

		cplex.addLe(left, 0);
	}

	/*
	demand equation
	/sum{X+Y} + G = f
	 */
	private void setConstraint4(List<IloNumVar[]> xVar,	List<IloNumVar[]> yVar, IloNumVar[] gVar,	double[] uValue) throws IloException {
		setDemandConstraint(xVar, yVar, gVar, uValue);
	}

	/*
	vessel capacity constraint
	/sum{X+Y+Z} <= V
	 */
	private void setConstraint5(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar, List<IloNumVar[]> zVar) throws IloException
	{
		setCapacityConstraint(xVar, yVar, zVar);
	}
	private void setConstraint5_Reactive1(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar) throws IloException {
		// ∀<n,n'>∈A'
		for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
			IloLinearNumExpr left = cplex.linearNumExpr();

			// i∈I
			for (int i = 0; i < p.getDemand().length; ++i) {
				Request od = in.getRequestSet().get(i);

				// φ
				for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
					int j = od.getLadenPathIndexes()[k];

					left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
					left.addTerm(p.getArcAndPath()[nn][j], yVar.get(i)[k]);
				}
			}

			// w \in \Omega
			// r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
			for(int w = 0; w < p.getVesselPathSet().length; ++w) {
				int r = in.getVesselPathSet().get(w).getRouteID() - 1;
				// h \in H_r
				// r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
				for(int h = 0; h < p.getVesselSet().length; ++h)
				{
					left.addTerm(-p.getVesselTypeAndShipRoute()[h][r]
									* p.getShipRouteAndVesselPath()[r][w]
									* p.getArcAndVesselPath()[nn][w]
									* p.getVesselCapacity()[h]
							, vVar[h][r]
					);
				}
			}

			String ConstrName = "C3" + "(" + (nn + 1) + ")";
			cplex.addLe(left, 0, ConstrName);
		}
	}
	private void setConstraint5_Reactive2(List<IloNumVar[]> zVar) throws IloException	{
		// ∀<n,n'>∈A'
		for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
			IloLinearNumExpr left = cplex.linearNumExpr();

			// i∈I
			for (int i = 0; i < p.getDemand().length; ++i) {
				Request od = in.getRequestSet().get(i);

				//θ
				for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
					int j = od.getEmptyPathIndexes()[k];

					left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
				}
			}

			// w \in \Omega
			// r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
			for(int w = 0; w < p.getVesselPathSet().length; ++w)
			{
				int r = in.getVesselPathSet().get(w).getRouteID() - 1;
				// h \in H_r
				// r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
				for(int h = 0; h < p.getVesselSet().length; ++h)
				{
					left.addTerm(-p.getVesselTypeAndShipRoute()[h][r]
									* p.getShipRouteAndVesselPath()[r][w]
									* p.getArcAndVesselPath()[nn][w]
									* p.getVesselCapacity()[h]
							, vVar2[h][w]
					);
				}
			}
			String ConstrName = "C3" + "(" + (nn + 1) + ")";
			cplex.addLe(left, 0, ConstrName);
		}
	}


	/*
	empty containers flow balance
	l_{pt} + /sum{ Z + X - Z - X} >= 0
	 */
	private void setConstraint6(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar) throws IloException	{
		setEmptyConservationConstraint(xVar, zVar);
	}

	public void setEtaValue(double etaValue) {
		this.etaValue = etaValue;
	}

	public void addScene(Scenario scene_k) throws IloException	{
		// second-stage variable :
		// by adding
		// x[i][p][k] : continue variable ���� number of self-owned containers shipped on path p for demand i in scene k
		// y[i][p][k] : continue variable ���� number of leased containers shipped on path p for demand i in scene k
		// z[i][q][k] : continue variable ���� number of self-owned containers repositioned on path q for demand i in scene k
		// g[i][k] : continue variable ���� number of unfulfilled containers for demand i on path p in scene k
		// l[p][t][k] : continue variable ���� number of self-owned containers shipped at port p at time t in scene k
		// create decision for scenery k
		List<IloNumVar[]> xxVar_k = new ArrayList<>();
		List<IloNumVar[]> yyVar_k = new ArrayList<>();
		List<IloNumVar[]> zzVar_k = new ArrayList<>();
		IloNumVar[] gVar_k = new IloNumVar[p.getDemand().length];

		SetRequestDecisionVars(xxVar_k, yyVar_k, zzVar_k, gVar_k);

		double[] request = scene_k.getRequest();

		setConstraint0(xxVar_k, yyVar_k, zzVar_k, gVar_k);
		setConstraint4(xxVar_k, yyVar_k, gVar_k, request);
		setConstraint5(xxVar_k, yyVar_k, zzVar_k);
		setConstraint6(xxVar_k, zzVar_k);
	}
	public void addReactiveScene(Scenario scene_k) throws IloException {
		// second-stage variable :
		// by adding
		// x[i][p][k] : continue variable ���� number of self-owned containers shipped on path p for demand i in scene k
		// y[i][p][k] : continue variable ���� number of leased containers shipped on path p for demand i in scene k
		// z[i][q][k] : continue variable ���� number of self-owned containers repositioned on path q for demand i in scene k
		// g[i][k] : continue variable ���� number of unfulfilled containers for demand i on path p in scene k
		// l[p][t][k] : continue variable ���� number of self-owned containers shipped at port p at time t in scene k
		// create decision for scenery k
		List<IloNumVar[]> xxVar_k = new ArrayList<>();
		List<IloNumVar[]> yyVar_k = new ArrayList<>();
		List<IloNumVar[]> zzVar_k = new ArrayList<>();
		IloNumVar[] gVar_k = new IloNumVar[p.getDemand().length];

		SetRequestDecisionVars(xxVar_k, yyVar_k, zzVar_k, gVar_k);

		double[] request = scene_k.getRequest();

		setConstraint0(xxVar_k, yyVar_k, zzVar_k, gVar_k);
		setConstraint4(xxVar_k, yyVar_k, gVar_k, request);
		setConstraint5_Reactive1(xxVar_k, yyVar_k);
		setConstraint5_Reactive2(zzVar_k);
		setConstraint6(xxVar_k, zzVar_k);
	}

	public void addOptimalityCut(double constantItem, double[] beta_value) throws IloException {
		IloLinearNumExpr left = cplex.linearNumExpr();
		for(int n = 0; n<p.getTravelingArcsSet().length; n++)
		{
			// r ∈R
			for(int w=0; w<p.getVesselPathSet().length; ++w)
			{
				int r = in.getVesselPathSet().get(w).getRouteID() - 1;
				// r(w) = r
				for(int h=0;h<p.getVesselSet().length;++h)
				{
					if(FleetType.equals("Homo")){
						// vValue[h][r] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta_value[n]
								, vVar[h][r]);
					} else if (FleetType.equals("Hetero")) {
						// vValue[h][w] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]
										*p.getVesselCapacity()[h]*beta_value[n]
								, vVar[h][w]);
					}
					else{
						log.info("Error in Fleet type!");
					}
				}
			}
		}
		left.addTerm(-1, EtaVar);
		cplex.addLe(left, -constantItem);
	}
	public void addFeasibilityCut(double constantItem, double[] beta_value) throws IloException {
		IloLinearNumExpr left = cplex.linearNumExpr();
		for(int n = 0; n<p.getTravelingArcsSet().length; n++)
		{
			// r ∈R
			/*for(int r=0; r<p.getVesselRouteSet().length; r++)*/
			{
				for(int w=0; w<p.getVesselPathSet().length; ++w)
				{
					int r = in.getVesselPathSet().get(w).getRouteID() - 1;
					// r(w) = r
					for(int h=0;h<p.getVesselSet().length;++h)
					{
						if(FleetType.equals("Homo")){
							// vValue[h][r] : come from solution of master problem
							left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
											*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta_value[n]
									, vVar[h][r]);
						} else if (FleetType.equals("Hetero")) {
							// vValue[h][w] : come from solution of master problem
							left.addTerm(p.getArcAndVesselPath()[n][w]
											*p.getVesselCapacity()[h]*beta_value[n]
									, vVar[h][w]);
						}
						else{
							log.info("Error in Fleet type!");
						}
					}
				}
			}
		}
		cplex.addLe(left, -constantItem);
	}

	public void addReactiveOptimalityCut(double constantItem, double[] beta1_value, double[] beta2_value) throws IloException {
		IloLinearNumExpr left = cplex.linearNumExpr();
		for(int n = 0; n<p.getTravelingArcsSet().length; n++)
		{
			// r ∈R
			for(int r = 0; r<p.getShippingRouteSet().length; r++)
			{
				for(int w=0; w<p.getVesselPathSet().length; ++w)
				{
					// r(w) = r
					for(int h=0;h<p.getVesselSet().length;++h)
					{
						// vValue[v][r] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta1_value[n]
								, vVar[h][r]);

						// vValue[v][r] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta2_value[n]
								, vVar2[h][r]);
					}
				}
			}
		}
		left.addTerm(-1, EtaVar);
		cplex.addLe(left, -constantItem);
	}
	public void addReactiveFeasibilityCut(double constantItem, double[] beta1_value, double[] beta2_value) throws IloException {
		IloLinearNumExpr left = cplex.linearNumExpr();
		for(int n = 0; n<p.getTravelingArcsSet().length; n++)
		{
			// r ∈R
			for(int r = 0; r<p.getShippingRouteSet().length; r++)
			{
				for(int w=0; w<p.getVesselPathSet().length; ++w)
				{
					// r(w) = r
					for(int h=0;h<p.getVesselSet().length;++h)
					{
						// vValue[v][r] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta1_value[n]
								, vVar[h][r]);

						// vValue[v][r] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta2_value[n]
								, vVar2[h][r]);
					}
				}
			}
		}
		cplex.addLe(left, -constantItem);
	}


	public void solveModel()
	{
		try
		{
			if (WhetherExportModel)
				exportModel();
			long startTime = System.currentTimeMillis();
			if (cplex.solve())
			{
				long endTime = System.currentTimeMillis();

				setVVarsSolution();
				setEtaValue(cplex.getValue(EtaVar));
				setOperationCost(cplex.getObjValue()-cplex.getValue(EtaVar));

				setObjVal(cplex.getObjValue());
				setSolveTime(endTime - startTime);
				setObjGap(cplex.getMIPRelativeGap());

				if(WhetherPrintVesselDecision){
					printMPSolution();
				}

				// print master problem solution
				if (DebugEnable && MasterEnable )
				{
					log.info("------------------------------------------------------------------------");
					log.info("SolveTime = "+getSolveTime());
					printMPSolution();
					log.info("------------------------------------------------------------------------");
				}
			}
			else
			{
				log.info("MasterProblem No solution");
			}
		}
		catch (IloException ex) {
			log.info("Concert Error: " + ex);
		}
	}

	public void solveReactiveModel()
	{
		try
		{
			if (WhetherExportModel)
				exportModel();
			long startTime = System.currentTimeMillis();
			if (cplex.solve())
			{
//				log.info("MP Solution Status : "+getSolveStatus());

				long endTime = System.currentTimeMillis();
				setVVarsSolution();

				int[][]  vvv2 =new int [p.getVesselSet().length][p.getVesselPathSet().length];
				for (int w = 0; w < p.getVesselPathSet().length; ++w) {
					for (int h = 0; h < p.getVesselSet().length; ++h) {
						double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
						if(cplex.getValue(vVar2[h][w]) >= 1 - tolerance) {
							vvv2[h][w] = 1;
						}
					}
				}
				setvVarValue2(vvv2);

				setEtaValue(cplex.getValue(EtaVar));
				setObjVal(cplex.getObjValue());
				setOperationCost(cplex.getObjValue()-cplex.getValue(EtaVar));
				setObjGap(cplex.getMIPRelativeGap());
				setSolveTime(endTime - startTime);

				// print master problem solution
				if (DebugEnable && MasterEnable )
				{
					log.info("------------------------------------------------------------------------");
					log.info("SolveTime = "+getSolveTime());
					printMPSolution();
					log.info("------------------------------------------------------------------------");
				}
			}
			else
			{
				log.info("MasterProblem No solution");
			}
		}
		catch (IloException ex) {
			log.info("Concert Error: " + ex);
		}
	}

	public int[][] getVVarValue2() {
		return vVarValue2;
	}
	public void setvVarValue2(int[][] vVarValue2) {
		this.vVarValue2 = vVarValue2;
	}
	public double getEtaValue() {
		return etaValue;
	}

	public void printMPSolution(){
		log.info("Master Objective ="+String.format("%.2f", getObjVal()));
		log.info ("Mp-OperationCost = "+String.format("%.2f",getOperationCost()));
		log.info ("Mp-OtherCost = "+String.format("%.2f",getEtaValue()));
		printSolution();
	}
	public void printReactiveSolution(){
		System.out.print("V[h][w] : ");
		for(int w=0;w<p.getVesselPathSet().length;++w)
		{
			for(int h=0;h<p.getVesselSet().length;++h)
			{
				if(vVarValue2[h][w] != 0)
				{
					System.out.print(p.getVesselPathSet()[w]+"(" + p.getVesselSet()[h]+")\t");
				}
			}
		}

	}
}
