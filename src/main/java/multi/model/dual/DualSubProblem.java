package multi.model.dual;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import multi.InputData;
import multi.Parameter;
import multi.Scenario;
import multi.model.primal.SubProblem;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
@Getter
@Setter
public class DualSubProblem extends BaseDualModel
{
	// data : in/p/tau

	// cplex model/variables/objective
	private IloIntVar[] miuVar;
	private IloNumVar[] lambdaVar;
	private IloRange UConstr;

	// result : u / obj / gap
	private double subObj;
	public DualSubProblem(InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.tau=p.getTau();
		this.modelName = "DSP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		if("Homo".equals(FleetType)){
			// V[h][r]
			vVarValue= new int[p.getVesselSet().length] [p.getShippingRouteSet().length];
		} else if ("Hetero".equals(FleetType)) {
			// V[h][w]
			this.vVarValue= new int[p.getVesselSet().length] [p.getVesselPathSet().length];
		}
		else{
			log.info("Error in Fleet type!");
		}

		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			//cplex.setParam(IloCplex.Param.MIP.Tolerances.MIPGap, 0.1);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}
	public DualSubProblem(InputData in, Parameter p, int tau) {
		super();
		this.in = in;
		this.p = p;
		this.tau=tau;
		this.modelName = "DSP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		if("Homo".equals(FleetType)){
			// V[h][r]
			vVarValue= new int[p.getVesselSet().length] [p.getShippingRouteSet().length];
		} else if ("Hetero".equals(FleetType)) {
			// V[h][w]
			this.vVarValue= new int[p.getVesselSet().length] [p.getVesselPathSet().length];
		}
		else{
			log.info("Error in Fleet type!");
		}

		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			//cplex.setParam(IloCplex.Param.MIP.Tolerances.MIPGap, 0.1);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}

	@Override
	public void setDecisionVars() throws IloException	{
		// create dual variable
		// α[i]
		//β[nn']
		//γ[p][t]
		setDualDecisionVars();

		// u[i] ∈{0,1}
		// the uncertain request can be inferred by u
		// f[i] = nf[i] + vf[i]*u[i]
		miuVar=new IloIntVar [p.getDemand().length];

		// create auxiliary variable
		//λ[i]=α[i]*u[i]
		lambdaVar =new IloNumVar [p.getDemand().length];

		String varName;
		for(int i=0;i<p.getDemand().length;i++)
		{
			varName = "lambda(" + i +")";
			lambdaVar[i]=cplex.numVar(0 , p.getPenaltyCostForDemand()[i], varName);

			varName = "u(" +i +")";
			miuVar[i]=cplex.boolVar(varName);
			//cplex.setPriority(miuVar[i], i);
		}
	}

	protected IloLinearNumExpr setObjExpr(int[][] vValue) throws IloException {
		// determine objective function
		objExpr =getDetermineObj(vValue);
		// variable objective function
		for(int i=0;i<p.getDemand().length;i++){
			objExpr.addTerm(p.getMaximumDemandVariation()[i], lambdaVar[i]);
		}
		return objExpr;
	}

	@Override
	public void setObjectives() throws IloException{
		setObjExpr(vVarValue);
		objective = cplex.addMaximize(objExpr);
	}

	@Override
	public void setConstraints() throws IloException	{
		//long startTime = System.currentTimeMillis();
		// dual constraints
		setConstraint1();
		//log.info("		Set Dual Constraint-I Time = "+(System.currentTimeMillis() - startTime));
		//startTime = System.currentTimeMillis();
		setConstraint2();
		//log.info("		Set Dual Constraint-II Time = "+(System.currentTimeMillis() - startTime));
		//startTime = System.currentTimeMillis();
		setConstraint3();
		//log.info("		Set Dual Constraint-III Time = "+(System.currentTimeMillis() - startTime));
		//startTime = System.currentTimeMillis();
		setConstraint4();
		//log.info("		Set Dual Constraint-IV Time = "+(System.currentTimeMillis() - startTime));
		//startTime = System.currentTimeMillis();
		//log.info("	Set Dual Constraint Time = "+(System.currentTimeMillis() - startTime));
		//startTime = System.currentTimeMillis();

		// uncertain set
		setConstraint5();
		//log.info("	Set Uncertain Set Time = "+(System.currentTimeMillis() - startTime));
		//startTime = System.currentTimeMillis();

		// linearize constraints
		// λ<=α
		setConstraint6();
		//λ>= α-(1-u)M
		setConstraint7();
		// λ<= M*u
		setConstraint8();
		// λ>=- M*u
		setConstraint9();
		//log.info("	Set Linearize Constraint Time = "+(System.currentTimeMillis() - startTime));

	}

	// C1------X
	private void setConstraint1() throws IloException	{
		setDualConstraintX();
	}

	// C2------Y
	private void setConstraint2() throws IloException	{
		setDualConstraintY();
	}

	// C3------Z
	private void setConstraint3() throws IloException	{
		setDualConstraintZ();
	}

	// C4------G
	private void setConstraint4() throws IloException	{
		setDualConstraintG();
	}

	// budget uncertain set
	private void setConstraint5() throws IloException {
		IloLinearIntExpr left = cplex.linearIntExpr();

		for(int i=0;i<p.getDemand().length;i++) {
			left.addTerm(1,miuVar[i]);
		}
		String ConstrName = "C-U";
		UConstr = cplex.addLe(left, tau, ConstrName);
	}

	public void setUncertainSetBound(int new_tau) throws IloException {
		UConstr.setUB(new_tau);
	}

	// λ[i] <= α[i]
	private void setConstraint6() throws IloException	{
		for(int i=0;i<p.getDemand().length;i++){
			IloLinearNumExpr left=cplex.linearNumExpr();
			left.addTerm(1,lambdaVar[i]);
			left.addTerm(-1,alphaVar[i]);
			cplex.addLe(left,0);
		}
	}

	// λ[i] >= α[i] - M*(1-u[i])
	// λ[i] - M*u[i] - α[i] >= - M
	private void setConstraint7() throws IloException	{
		/*int M = Integer.MAX_VALUE;*/

		for(int i=0;i<p.getDemand().length;i++)
		{
			double M = p.getPenaltyCostForDemand()[i];
			IloLinearNumExpr left=cplex.linearNumExpr();

			left.addTerm(1,lambdaVar[i]);
			left.addTerm(-M, miuVar[i]);
			left.addTerm(-1,alphaVar[i]);
			cplex.addGe(left, -M);
		}
	}

	// λ[i] <= u[i]*M
	private void setConstraint8() throws IloException	{
	/*int M = Integer.MAX_VALUE;*/

	for(int i=0;i<p.getDemand().length;i++)
	{
		double M = p.getPenaltyCostForDemand()[i];
		IloLinearNumExpr left = cplex.linearNumExpr();

		left.addTerm(1,lambdaVar[i]);
		left.addTerm(-M,miuVar[i]);

		cplex.addLe(left,0);
	}
}
	// λ[i] >= - u[i]*M
	private void setConstraint9() throws IloException	{
		/*int M = Integer.MAX_VALUE;*/

		for(int i=0;i<p.getDemand().length;i++)
		{
			double M = p.getPenaltyCostForDemand()[i];
			IloLinearNumExpr left = cplex.linearNumExpr();

			left.addTerm(1,lambdaVar[i]);
			left.addTerm(M, miuVar[i]);

			cplex.addGe(left,0);
		}
	}
	public void solveModel()	{
		try
		{
			if (WhetherExportModel) {
				exportModel();
			}
			long startTime = System.currentTimeMillis();
			if (cplex.solve())
			{
				long endTime = System.currentTimeMillis();

				setObjVal(cplex.getObjValue());
				setSolveTime(endTime - startTime);
				setObjGap(cplex.getMIPRelativeGap());

				uValue = new double[p.getDemand().length];
				double [] request =new double [p.getDemand().length];
				List<Integer> requestList = new ArrayList<>();
				for(int i=0;i<p.getDemand().length;i++)
				{
					request[i] = cplex.getValue(miuVar[i]);
					if (cplex.getValue(miuVar[i]) != 0)
					{
						double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
						if(cplex.getValue(miuVar[i]) >= 1 - tolerance){
							//request[i] = 1;
							uValue[i] = 1;
							requestList.add(i);
						}
					}
				}

				Scenario Scene = new Scenario();
				Scene.setRequest(request);
				Scene.setWorseRequestSet(requestList);
				setScene(Scene);

				if (DebugEnable && DualSubEnable)
				{
					log.info("------------------------------------------------------------------------");
					log.info("SolveTime = "+(endTime - startTime) + "ms");
					log.info("DSP-Obj = "+ String.format("%.2f",getObjVal()));
					printSolution();
					log.info("------------------------------------------------------------------------");

					SubProblem sp = new SubProblem(in, p, vVarValue, request);
					sp.solveModel();

					DualProblem dp = new DualProblem(in, p, vVarValue, request);
					dp.solveModel();

					log.info("SP-Obj = \t"+ String.format("%.2f", sp.getObjVal()));
					log.info("DP-Obj = \t"+ String.format("%.2f", dp.getObjVal()));
					log.info("DSP-Obj = \t"+ String.format("%.2f",this.getObjVal()));
					log.info("Dual-Obj = \t"+ String.format("%.2f",calculateDualObjVal(vVarValue)));

					log.info("Determine Cost(DSP) = \t" + String.format("%.2f",calculateDetermineCost()));
					log.info("Determine Cost(DP) = \t" + String.format("%.2f",dp.calculateDetermineCost()));

					log.info("Uncertain Cost(DSP) = \t" + String.format("%.2f",calculateUncertainCost()));
					log.info("Uncertain Cost(DP) = \t" + String.format("%.2f",dp.calculateUncertainCost()));

					/*checkLambdaValue();
					checkAlphaValue(dp.getAlphaValue(), getAlphaValue());
					checkBetaValue(dp.getBetaValue(), getBetaValue());

					if(checkConstraints(getAlphaValue(), getBetaValue(), getGammaValue())){
							log.info("No Constraints in DualSubProblem is Violated");
					}else{
						log.info("DualSubProblem: Constraints is Violated");
					}

					if(checkConstraints(dp.getAlphaValue(), dp.getBetaValue(), dp.getGammaValue())){
						log.info("No Constraints in DualSubProblem is Violated (with DP solution)");
					}else{
						log.info("DualSubProblem: Constraints is Violated (with DP solution)");
					}*/

					log.info("------------------------------------------------------------------------");
				}
			}
			else
			{
				log.info("DualSubProblem No Solution");
			}
			/*cplex.end();*/
		}
		catch (IloException ex) {
			log.info("Concert Error: " + ex);
		}
	}
	public void setStartScene(double[] startCase) throws IloException {
		cplex.addMIPStart(miuVar, startCase);
	}
	public double[] getUValueDouble() throws IloException {
		double[] U = new double[p.getDemand().length];
		for (int i = 0; i < p.getDemand().length; i++) {
			U[i] = (double) uValue[i];
		}
		return U;
	}
	// here constant item is calculated to be (sub objective - second item)
	// the second item contains the first stage decision V[h][r]
	@Override
	public double getConstantItem() throws IloException {
		double constantItem = 0;

		// I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
		// i ∈I
		for(int i=0;i<p.getDemand().length;i++)
		{
			constantItem  += (p.getDemand()[i] *cplex.getValue( alphaVar[i]));
			constantItem  += (p.getMaximumDemandVariation()[i] *cplex.getValue( lambdaVar[i]));
		}

		// III. part three:
		// p∈P
		for(int pp=0;pp<p.getPortSet().length;pp++)
		{
			//t∈ T
			for(int t=1; t<p.getTimePointSet().length; t++)
			{
				constantItem  += (-p.getInitialEmptyContainer()[pp] * cplex.getValue(gammaVar[pp][t]));
			}
		}
		return constantItem;
	}
	public double[] getLambdaValue(){
		double[] lambda_value = new double[p.getDemand().length];
		try {
			if(cplex.getStatus() == IloCplex.Status.Optimal){
				for (int i = 0; i < p.getDemand().length; i++){
					lambda_value[i] = cplex.getValue(lambdaVar[i]);
				}
			}
		} catch (IloException e) {
			e.printStackTrace();
		}
		return lambda_value;
	}
	// here beta is used for cutting
	// second item (which contains the first stage decision ) in the cut = sum{λ * q * β * V}
	public double calculateDualObjVal(int[][] vValue) throws IloException {
		double objVal = getConstantItem();

		// II. sum (vessel capacity * V[h][r] * beta[arc])
		// V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
		// <n,n'> ∈ A'
		double[] capacitys = getCapacityOnArcs(vValue);
		double[] beta_value = getBetaValue();
		for(int n = 0; n<p.getTravelingArcsSet().length; n++){
			objVal  += (capacitys[n] * beta_value[n]);
		}

		return objVal;
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
			cost += p.getMaximumDemandVariation()[i] *cplex.getValue(lambdaVar[i]);
		}
		return cost;
	}
	public void checkAlphaValue(double[] alpha_value, double[] alpha_value2){
		double[] lambda_value = getLambdaValue();
			for(int i=0;i<p.getDemand().length;i++){
				if(Math.abs(alpha_value[i] - alpha_value2[i]) > 0.1){
					System.out.print("α["+i+"] = "+alpha_value[i] + "\t\t" + "α2["+i+"] = "+alpha_value2[i] + "\t\t");
					System.out.print("λ["+i+"] = "+lambda_value[i] + "\t\t" + "u["+i+"] = "+ uValue[i] + "\t\t");
					System.out.print("Cost-I = " + (p.getDemand()[i] * alpha_value[i]) + "\t\t");
					System.out.print("Cost-II = " + ((p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValue[i])  * alpha_value2[i]) + "\t\t");

				}
			}
	}
	public void checkBetaValue(double[] beta_value, double[] beta_value2){
		for(int i=0;i<p.getTravelingArcsSet().length;i++){
			if(Math.abs(beta_value[i] - beta_value2[i]) > 0.1){
				log.info("β["+i+"] = "+beta_value[i] + "\t\t" + "β2["+i+"] = "+beta_value2[i]);
			}
		}
	}
	public void checkLambdaValue() throws IloException {
		for(int i=0;i<p.getDemand().length;i++){
			if(Math.abs(cplex.getValue(lambdaVar[i]) - cplex.getValue(alphaVar[i]) * cplex.getValue(miuVar[i])) > 0.1){
				log.info("λ["+i+"] = "+cplex.getValue(lambdaVar[i]) + "\t" + "α["+i+"] = "+cplex.getValue(alphaVar[i]) + "\t" + "u["+i+"] = "+cplex.getValue(miuVar[i]));
				log.info("Difference = " + Math.abs(cplex.getValue(miuVar[i]) - cplex.getValue(alphaVar[i]) * cplex.getValue(miuVar[i])));
				log.info("Error Cost = " + cplex.getValue(lambdaVar[i]) * p.getMaximumDemandVariation()[i]);
				log.info("Error Cost = " + cplex.getValue(alphaVar[i]) * cplex.getValue(miuVar[i]) * p.getMaximumDemandVariation()[i]);
			}
		}
	}

	public IloRange separate(double[][] vValue, IloCplex cplex, IloIntVar[][] vVars, IloNumVar etaVar) throws IloException {
		changeObjectiveVvarsCoefficients(vValue);
		solveModel();
		return constructOptimalCut(cplex, vVars, etaVar);
	}

	protected void writeSolution(FileWriter fileWriter){
		try {
			fileWriter.write("Worse Solution:\t");
			for(int i=0;i<p.getDemand().length;i++) {
				if (uValue[i] != 0)
				{
					fileWriter.write(i + ",");
				}
			}
			fileWriter.write("\n");
		} catch (IOException e) {
			e.printStackTrace();
		}
	}
	public void printSolution(){
		System.out.print("The Worst Case(DSP)"+"(tau = "+tau+") : ");
		for(int i=0;i<p.getDemand().length;i++)
		{
			if (uValue[i] != 0)
			{
				System.out.print(i+",");
			}
		}

	}
}
