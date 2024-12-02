package multi;

import lombok.extern.slf4j.Slf4j;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import ilog.concert.*;
import ilog.cplex.IloCplex;

@Slf4j
public class DualProblem extends BaseDualModel {

	private IloRange CObj;
	// data : in/p
	// variable parameter
	public DualProblem(InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.ModelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
		this.uValue = new double[p.getDemand().length];
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}
	public DualProblem(InputData in, Parameter p, int[][] vValue) {
		super();
		this.in = in;
		this.p = p;
		this.ModelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue = vValue;
		this.uValue = new double[p.getDemand().length];
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}
	public DualProblem(InputData in, Parameter p, int[][] vValue, double[] uValue) {
		super();
		this.in = in;
		this.p = p;
		this.ModelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue = vValue;
		this.uValue = uValue;
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}

	public DualProblem(InputData in, Parameter p, int[][] vValue, int[] uValue) {
		super();
		this.in = in;
		this.p = p;
		this.ModelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue = vValue;
		this.uValue = IntArrayWrapper.IntArrayToDoubleArray(uValue);
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}


	@Override
	protected void setDecisionVars() throws IloException{
		setDualDecisionVars();
	}

	@Override
	public void setObjectives() throws IloException{
		ObjExpr = getObjExpr(vVarValue, uValue);
		objective = cplex.addMaximize(ObjExpr);
	}

	@Override
	public void setConstraints() throws IloException	{
		// dual constraints
		setConstraint1();
		setConstraint2();
		setConstraint3();
		setConstraint4();

		if (UseParetoOptimalCut){
			setParetoConstraint();
		}
	}

	// pareto optimal cut constraint:
	// DSP-obj == Obj -> objLB <= DSP-obj <= objUB
	private void setParetoConstraint() throws IloException{
		CObj = cplex.addRange(Double.MIN_VALUE, ObjExpr, Double.MAX_VALUE, "ParetoObj");
	}
	public void changeParetoConstr(int[][] vValue, double[] uValue, double dspObjVal) throws IloException {
		ObjExpr = getObjExpr(vValue, uValue);
		CObj.setExpr(ObjExpr);
		CObj.setBounds(dspObjVal - boundGapLimit, dspObjVal + boundGapLimit);
	}
	// C1------X
	private void setConstraint1() throws IloException {
		//  ∀i∈I
		setDualConstraintX();
	}

	// C2------Y
	private void setConstraint2() throws IloException {
		//  ∀i∈I
		setDualConstraintY();
	}
 	private void setConstraint3() throws IloException {
		setDualConstraintZ();
	}

	// C4------G
	private void setConstraint4() throws IloException {
		setDualConstraintG();
	}

	public void solveModel() {
		try
		{
			if (WhetherExportModel)
				exportModel();
			long startTime = System.currentTimeMillis();
			if (cplex.solve())
			{
				long endTime = System.currentTimeMillis();

				setObjVal(cplex.getObjValue());
				setSolveTime(endTime - startTime);
				setObjGap(cplex.getMIPRelativeGap());
			}
			else
			{
				log.info("DualProblem No Solution");
			}
		}
		catch (IloException ex) {
			log.info("Concert Error: " + ex);
		}
	}
	public double[] getAlphaValue(){
		double[] alpha_value = new double[p.getDemand().length];
		try {
			if(cplex.getStatus() == IloCplex.Status.Optimal){
				for (int i = 0; i < p.getDemand().length; i++){
					alpha_value[i] = cplex.getValue(alphaVar[i]);
				}
			}
		} catch (IloException e) {
			e.printStackTrace();
		}
		return alpha_value;
	}
	// here beta is used for cutting
	// second item (which contains the first stage decision ) in the cut = sum{λ * q * β * V}
	public double[] getBetaValue() throws IloException {
		double[] beta_value = new double[p.getTravelingArcsSet().length];
		if(cplex.getStatus() == IloCplex.Status.Optimal)
		{
			for (int i = 0; i < p.getTravelingArcsSet().length; i++) {
				beta_value[i] = cplex.getValue(betaVar[i]);
			}
		}
		return beta_value;
	}

	public void writeSolution() throws IOException, IloException {
		File file = new File("DSP.txt");
		if(!file.exists())
		{
			try {
				file.createNewFile();
			} catch (IOException e) {
				e.printStackTrace();
			}
		}
		FileWriter fileWriter = new FileWriter(file);

		fileWriter.write("Alpha : "+"\n");
		for (int i = 0; i < p.getDemand().length; i++) {
			fileWriter.write("alpha["+i+"] = "+cplex.getValue(alphaVar[i])+"\n");
		}

		fileWriter.write("Beta : "+"\n");
		for (int i = 0; i < p.getTravelingArcsSet().length; i++) {
			fileWriter.write("beta["+i+"] = "+cplex.getValue(betaVar[i])+"\n");
		}

		fileWriter.write("Gamma : "+"\n");
		for (int pp = 0; pp < p.getPortSet().length; pp++) {
			for (int t = 1; t < p.getTimePointSet().length; t++) {
				fileWriter.write("gamma["+pp+"]["+t+ "] = "+cplex.getValue(gammaVar[pp][t])+"\n");
			}
		}
	}
	public double calculateDetermineCost() throws IloException {
		double cost = 0;
		// I.part one : sum(normal_demand * alpha) = sum(normal_demand * alpha)
		// i ∈I
		for(int i=0;i<p.getDemand().length;i++)
		{
			cost += p.getDemand()[i] * cplex.getValue(alphaVar[i]);
		}

		// II. sum (vessel capacity * V[h][r] * beta[arc])
		// V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
		// <n,n'> ∈ A'
		double[] capacitys = getCapacityOnArcs(vVarValue);
		for(int n = 0; n<p.getTravelingArcsSet().length; n++)
		{
			cost += capacitys[n] *  cplex.getValue(betaVar[n]);
		}

		// III. part three:
		// p∈P
		for(int pp=0;pp<p.getPortSet().length;pp++)
		{
			//t∈ T
			for(int t=1; t<p.getTimePointSet().length; t++)
			{
				cost += -p.getInitialEmptyContainer()[pp] *  cplex.getValue(gammaVar[pp][t]);
			}
		}
		return cost;
	}
	public double calculateUncertainCost() throws IloException {
		double cost = 0;
		for(int i=0;i<p.getDemand().length;i++){
			cost += p.getMaximumDemandVariation()[i] * uValue[i] * cplex.getValue(alphaVar[i]);
		}
		return cost;
	}
}