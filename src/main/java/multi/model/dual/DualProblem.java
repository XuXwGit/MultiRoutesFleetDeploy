package multi.model.dual;

import lombok.extern.slf4j.Slf4j;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import ilog.concert.*;
import ilog.cplex.IloCplex;
import multi.DefaultSetting;
import multi.InputData;
import multi.IntArrayWrapper;
import multi.Parameter;
/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class DualProblem extends BaseDualModel {

	private IloRange CObj;
	// data : in/p
	// variable parameter
	public DualProblem(InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.modelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
		if(DefaultSetting.FleetType == "Hetero"){
			this.vVarValue = new int[p.getVesselSet().length][p.getVesselPathSet().length];
		}else{
			this.vVarValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
		}
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
		this.modelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
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
		this.modelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
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
		this.modelName = "DP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
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

	/**
	 * 设置对偶问题的目标函数(对应数学模型中的对偶问题目标)
	 *
	 * 数学表达式:
	 * max ∑_{i∈I} π_i f_i +   ∑_{nn'∈A}∑_{r∈R} Vnn' β_p... + ∑_{t∈T}∑_{p∈P} γ_pt l_p
	 *
	 * 其中:
	 * π_i: 需求i的对偶变量(对应代码中的alphaVar[i])
	 * β_nn': 航段nn'运力约束的对偶变量 (对应代码中的betaVar[i])
	 * γ_pt: 时刻t港口p空箱量的对偶变量(对应代码中的gammaVar[p])
	 * f_i: 需求i的大小(对应代码中的vVarValue[i])
	 * l_p: 港口p初始空箱量(对应代码中的uValue[p])
	 *
	 * @throws IloException
	 */
	@Override
	public void setObjectives() throws IloException{
		objExpr = getObjExpr(vVarValue, uValue); // 构建目标函数表达式
		objective = cplex.addMaximize(objExpr);  // 设置为最大化问题
	}

	/**
	 * 设置对偶问题的约束条件(对应数学模型中的对偶约束)
	 *
	 * 包含三类约束:
	 * 1. 自有集装箱运输路径约束(X_iφ)
	 * 2. 租赁集装箱运输路径约束(Y_iφ)
	 * 3. 空箱调运路径约束(Z_θ)
	 *
	 * 具体约束条件参见BaseDualModel中的详细说明
	 *
	 * @throws IloException
	 */
	@Override
	public void setConstraints() throws IloException	{
		// 添加所有对偶约束
		setConstraint1();
		setConstraint2();
		setConstraint3();
		setConstraint4();

		if (DefaultSetting.UseParetoOptimalCut){
			setParetoConstraint();
		}
	}

	/**
	* @Author: XuXw
	* @Description: add pareto optimal cut constraint: objLB <= DSP-obj <= objUB
	* @DateTime: 2024/12/5 16:21
	* @Params: []
	* @Return void
	*/
	private void setParetoConstraint() throws IloException{
		CObj = cplex.addRange(Double.MIN_VALUE, objExpr, Double.MAX_VALUE, "ParetoObj");
	}
	public void changeParetoConstr(int[][] vValue, double[] uValue, double dspObjVal) throws IloException {
		objExpr = getObjExpr(vValue, uValue);
		CObj.setExpr(objExpr);
		CObj.setBounds(dspObjVal - DefaultSetting.boundGapLimit, dspObjVal + DefaultSetting.boundGapLimit);
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
			if (DefaultSetting.WhetherExportModel) {
				exportModel();
			}
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
	/**
	 * 计算确定性成本(对应数学模型中的确定性成本计算)
	 *
	 * 数学表达式:
	 * cost = ∑_{i∈I} f_i π_i
	 *      + ∑_{<n,n'>∈A'} q_{nn'} β_{nn'}
	 *      - ∑_{p∈P} ∑_{t∈T} l_p γ_{pt}
	 *
	 * 其中:
	 * f_i: 需求i的大小(对应p.getDemand()[i])
	 * π_i: 需求i的对偶变量(对应alphaVar[i])
	 * q_{nn'}: 弧<n,n'>的运力(对应capacitys[n])
	 * β_{nn'}: 弧<n,n'>的对偶变量(对应betaVar[n])
	 * l_p: 港口p初始空箱量(对应p.getInitialEmptyContainer()[pp])
	 * γ_{pt}: 港口p在时间t的对偶变量(对应gammaVar[pp][t])
	 *
	 * @return 确定性成本值
	 * @throws IloException
	 */
	public double calculateDetermineCost() throws IloException {
		double cost = 0;
		// 第一部分: ∑f_iπ_i (需求i的对偶成本)
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
	/**
	 * 计算不确定性成本(对应数学模型中的鲁棒成本计算)
	 *
	 * 数学表达式:
	 * cost = ∑_{i∈I} Δf_i u_i π_i
	 *
	 * 其中:
	 * Δf_i: 需求i的最大变化量(对应p.getMaximumDemandVariation()[i])
	 * u_i: 需求i的不确定性系数(对应uValue[i])
	 * π_i: 需求i的对偶变量(对应alphaVar[i])
	 *
	 * 用途:
	 * 用于鲁棒优化模型中评估最坏情况下的成本
	 *
	 * @return 不确定性成本值
	 * @throws IloException
	 */
	public double calculateUncertainCost() throws IloException {
		double cost = 0;
		// 计算所有需求的不确定性成本总和
		for(int i=0;i<p.getDemand().length;i++){
			cost += p.getMaximumDemandVariation()[i] * uValue[i] * cplex.getValue(alphaVar[i]);
		}
		return cost;
	}
}