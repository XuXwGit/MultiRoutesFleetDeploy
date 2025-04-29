package multi.model.primal;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.network.Request;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
/**
 * 子问题模型类
 *
 * 用于求解给定主问题解下的第二阶段问题
 *
 * 数学模型特点:
 * 1. 目标函数: 最小化第二阶段运营成本
 *    min Σ_a (c_x x_a + c_x1 x1_a + c_y y_a + c_z z_a) + Σ_i p_i u_i
 * 2. 约束条件:
 *    - 流量平衡约束
 *    - 容量约束(基于主问题解)
 *    - 需求满足约束(允许缺货u_i)
 *
 * 其中:
 * c_x, c_x1, c_y, c_z: 各类集装箱的单位成本
 * x_a, x1_a, y_a, z_a: 各类集装箱的运输量
 * p_i: 需求点i的缺货惩罚成本
 * u_i: 需求点i的缺货量
 *
 * @Author: XuXw
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SubProblem extends BasePrimalModel
{
	/**
	 * 总成本 = 重箱成本 + 空箱成本 + 惩罚成本 + 租赁成本
	 */
	private double totalCost;
	
	/**
	 * 重箱运输成本 Σ_a c_x x_a
	 */
	private double ladenCost;
	
	/**
	 * 空箱运输成本 Σ_a c_z z_a
	 */
	private double emptyCost;
	
	/**
	 * 需求未满足惩罚成本 Σ_i p_i u_i
	 */
	private double penaltyCost;
	
	/**
	 * 集装箱租赁成本 Σ_a c_y y_a
	 */
	private double rentalCost;

	/**
	 * 子问题构造函数
	 *
	 * @param in 输入数据(网络结构、需求等)
	 * @param p 模型参数(成本系数、容量等)
	 */
	public SubProblem(InputData in, Parameter p){
		super();
		this.in = in;
		this.p = p;
		this.modelName = "SP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		if(FleetType.equals("Homo")){
			vVarValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
		} else if (FleetType.equals("Hetero")) {
			vVarValue = new int[p.getVesselSet().length] [p.getVesselPathSet().length];
		}
		else{
			log.info("Error in Fleet type!");
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
	public SubProblem(InputData in, Parameter p, int[][] vVarValue){
		super();
		this.in = in;
		this.p = p;
		this.modelName = "SP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue= vVarValue;
		this.uValue = new double[p.getDemand().length];
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}
	public SubProblem(InputData in, Parameter p, int[][] vVarValue, double[] uValue){
		super();
		this.in = in;
		this.p = p;
		this.modelName = "SP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue= vVarValue;
		this.uValue = uValue;
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}
	public SubProblem(InputData in, Parameter p, int[][] vVarValue, int[] uValue){
		super();
		this.in = in;
		this.p = p;
		this.modelName = "SP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ FleetType + "-S" + randomSeed;
		this.vVarValue= vVarValue;
		this.uValue = IntArrayWrapper.IntArrayToDoubleArray(uValue);
		try{
			cplex = new IloCplex();
			publicSetting(cplex);
			frame();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}

	protected void setDecisionVars() throws IloException{
		SetRequestDecisionVars();
	}

	// Minimize total cost about containers
	protected void setObjectives() throws IloException	{
		IloLinearNumExpr Obj = cplex.linearNumExpr();
		Obj = GetRequestTransCostObj(Obj);
		cplex.addMinimize(Obj);
	}

	protected void setConstraints() throws IloException {
		setConstraint1();
		setConstraint2();
		setConstraint3();
	}

	// Demand equation :
	// C-5------α
	// C-5 = 0
	private void setConstraint1() throws IloException	{
		C1 = new IloRange[p.getDemand().length];

		//∀i∈I
		for (int i = 0; i < p.getDemand().length; i++) {
			IloLinearNumExpr left = cplex.linearNumExpr();

			Request od = in.getRequestSet().get(i);
			//φ
			for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
				left.addTerm(1, xVar.get(i)[k]);
				left.addTerm(1, yVar.get(i)[k]);
			}

			left.addTerm(1, gVar[i]);

			String ConstrName = "C1(" + (i + 1) + ")";
			C1[i] = cplex.addEq(left, p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValue[i], ConstrName);
		}
	}

	// VesselType Capacity Constraint :
	// C-6------β
	// C-6<= 0
	private void setConstraint2() throws IloException {
		C2 = new IloRange[p.getTravelingArcsSet().length];

		// ∀<n,n'>∈A'
		double[]  capacitys= getCapacityOnArcs(vVarValue);
		for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
			IloLinearNumExpr left=cplex.linearNumExpr();

			// i∈I
			for(int i=0;i<p.getDemand().length;i++){
				Request od = in.getRequestSet().get(i);

				// φ
				for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
					int j = od.getLadenPathIndexes()[k];
					left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
					left.addTerm(p.getArcAndPath()[nn][j], yVar.get(i)[k]);
				}

				//θ
				for (int k = 0; k < od.getNumberOfEmptyPath(); k++) {
					int j = od.getEmptyPathIndexes()[k];
					left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
				}
			}

			String ConstrName = "C6-"+"_"+(nn+1);
			C2[nn] = cplex.addLe(left, capacitys[nn], ConstrName);
		}
	}

	// Container Flow Conservation Constraint :
	// calculate the number of available empty self-owned containers at port p at time t
	// or
	// L[p][t] > 0 means all empty self-owned containers that repositioning to other ports (sumZ(out))
	// plus all laden self-owned containers that transport to other ports (sumX(out))
	// should no more than (L[p][t-1] + sumX(in) + sumZ(in))
	// C7------γ
	// C7>=0  =>  -C7 <= 0
	// ( item4 - item1 ) * Z + (item3 - item2) * X <= Lp0
	// Output-X + OutputZ - Input-X - Input-Z <= lp0
	private void setConstraint3() throws IloException	{
		setEmptyConservationConstraint();
	}

	public void solveModel()	{
		try
		{
			if (WhetherExportModel)
				exportModel();
			// solve the model
			long startTime = System.currentTimeMillis();
			if (cplex.solve())
			{
				long endTime = System.currentTimeMillis();
				setObjVal(cplex.getObjValue());
				setDetailCost();
				setSolveTime(endTime - startTime);
				setObjGap(cplex.getMIPRelativeGap());

				if(DefaultSetting.WhetherWriteFileLog){
					writePortContainers();
					writeSolution();
				}
			}
			else
			{
				log.info("SubProblem No solution");
			}

		}
		catch (IloException ex) {
			log.info("Concert Error: " + ex);
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

	public double getDualObjective() throws IloException {
		double dualObj = 0;

		// I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
		// i ∈I
		for(int i=0;i<p.getDemand().length;i++)
		{
			dualObj += p.getDemand()[i] * cplex.getDual(C1[i]);
			dualObj += p.getMaximumDemandVariation()[i] *uValue[i]* cplex.getDual(C1[i]);
		}

		// II. sum (vessel capacity * V[h][r] * beta[arc])
		// V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
		// <n,n'> ∈ A'
		for(int n = 0; n<p.getTravelingArcsSet().length; n++)
		{
			// r ∈R
			for(int r = 0; r<p.getShippingRouteSet().length; r++)
			{
				for(int w=0; w<p.getVesselPathSet().length; w++)
				{
					// r(w) = r
					for(int h=0;h<p.getVesselSet().length;h++)
					{
						// vValue[v][r] : come from solution of master problem
						dualObj += p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
								*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]* vVarValue[h][r] * cplex.getDual(C2[n]);
					}
				}
			}
		}

		// III. part three:
		// p∈P
		for(int pp=0;pp<p.getPortSet().length;pp++)
		{
			//t∈ T
			for(int t=1; t<p.getTimePointSet().length; t++)
			{
				dualObj += p.getInitialEmptyContainer()[pp] * cplex.getDual(C3[pp][t]);
			}
		}
		return dualObj;
	}

	public void printPathAllocationSolutions() throws IloException {
		for (int i = 0; i < p.getDemand().length; i++) {
			System.out.print("Request "+i+" : ");
			for (int k = 0; k < in.getRequestSet().get(i).getNumberOfLadenPath(); k++)
			{
				int j = in.getRequestSet().get(i).getLadenPathIndexes()[k];
				System.out.print("X["+i+"]["+j+"] = "+cplex.getValue(xVar.get(i)[k])+'\t'
													+"Y["+i+"]["+j+"] = "+cplex.getValue(yVar.get(i)[k]));
			}

		}
	}

	public void writeDualSolution() throws IOException, IloException {
		File file = new File(RootPath + SolutionPath + "SP-Dual-Solution"
				+"(R="+in.getShipRouteSet().size()+")"
				+"(T="+(p.getTimePointSet().length-1)+")"
				+"(U="+p.getUncertainDegree()+")"
				+".txt");
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
			fileWriter.write("alpha["+i+"] = "+cplex.getDual(C1[i])+"\n");
		}

		fileWriter.write("Beta : "+"\n");
		for (int i = 0; i < p.getTravelingArcsSet().length; i++) {
			fileWriter.write("beta["+i+"] = "+cplex.getDual(C2[i])+"\n");
		}

		fileWriter.write("Gamma : "+"\n");
		for (int pp = 0; pp < p.getPortSet().length; pp++) {
			for (int t = 1; t < p.getTimePointSet().length; t++) {
				fileWriter.write("gamma["+pp+"]["+t+ "] = "+cplex.getDual(C3[pp][t])+"\n");
			}
		}
	}

	//Change Demand Equation Constraint(Constraint2)'s Right Coefficients
	public void changeDemandConstraintCoefficients(double[] uValue) throws IloException {
		this.uValue = uValue;
		//∀i∈I
		for(int i=0;i<p.getDemand().length;i++)
		{
			C1[i].setBounds(p.getDemand()[i]+p.getMaximumDemandVariation()[i]*uValue[i],
					p.getDemand()[i]+p.getMaximumDemandVariation()[i]*uValue[i]);
		}
	}

	//Change Capacity Constraint(Constraint3)'s Right Coefficients
	public void changeCapacityConstraintCoefficients(int[][] VValue) throws IloException {
		this.vVarValue = VValue;
		// ∀<n,n'>∈A'
		double[] capacitys = getCapacityOnArcs(vVarValue);
		for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
		{
			C2[nn].setBounds(0, capacitys[nn]);
		}
	}

	public void changeConstraintCoefficients(int[][] VValue, int[] uValue) throws IloException {
		this.vVarValue = VValue;
		this.uValue = IntArrayWrapper.IntArrayToDoubleArray(uValue);

		changeConstraintCoefficients(this.vVarValue, this.uValue);
	}
	public void changeConstraintCoefficients(int[][] VValue, double[] uValue) throws IloException {
		this.vVarValue = VValue;
		this.uValue =uValue;

		//Change Demand Equation Constraint(Constraint2)'s Right Coefficients
		changeDemandConstraintCoefficients(uValue);

		//Change Capacity Constraint(Constraint3)'s Right Coefficients
		changeCapacityConstraintCoefficients(VValue);
	}
	public double getTotalCost() {
		return totalCost;
	}

	public void setTotalCost(double totalCost) {
		this.totalCost = totalCost;
	}
	public double getLadenCost() {
		return ladenCost;
	}

	public void setLadenCost(double ladenCost) {
		this.ladenCost = ladenCost;
	}

	public double getEmptyCost() {
		return emptyCost;
	}

	public void setEmptyCost(double emptyCost) {
		this.emptyCost = emptyCost;
	}

	public double getPenaltyCost() {
		return penaltyCost;
	}

	public void setPenaltyCost(double penaltyCost) {
		this.penaltyCost = penaltyCost;
	}

	public double getRentalCost() {
		return rentalCost;
	}

	public void setRentalCost(double rentalCost) {
		this.rentalCost = rentalCost;
	}

	protected void setDetailCost() throws IloException {
		double TotalLadenCost = 0;
		double TotalEmptyCost = 0;
		double TotalRentalCost = 0;
		double TotalPenaltyCost = 0;

		for(int i = 0; i < p.getDemand().length; ++i){
			// item2 : Penalty Cost of unsatisfied Demand
			TotalPenaltyCost +=(p.getPenaltyCostForDemand()[i] * cplex.getValue(gVar[i]));

			Request od = in.getRequestSet().get(i);

			// \phi \in \\Phi_i
			for(int k = 0; k < od.getNumberOfLadenPath(); ++k) {
				int j = od.getLadenPathIndexes()[k];
				// item3 : Demurrage of self-owned and leased containers and Rental cost on laden paths
				TotalLadenCost += (p.getLadenPathCost()[j] * cplex.getValue(xVar.get(i)[k]));
				TotalLadenCost += (p.getLadenPathCost()[j] * cplex.getValue(yVar.get(i)[k]));
				TotalRentalCost += (p.getRentalCost() * p.getTravelTimeOnPath()[j] * cplex.getValue(yVar.get(i)[k]));
			}

			// \theta \in \\Theta_i
			for(int k = 0; k < od.getNumberOfEmptyPath(); ++k)
			{
				int j = od.getEmptyPathIndexes()[k];
				TotalEmptyCost += (p.getEmptyPathCost()[j]* cplex.getValue(zVar.get(i)[k]));
			}
		}

		setLadenCost(TotalLadenCost);
		setEmptyCost(TotalEmptyCost);
		setRentalCost(TotalRentalCost);
		setPenaltyCost(TotalPenaltyCost);
		setTotalCost(TotalLadenCost + TotalEmptyCost + TotalRentalCost + TotalPenaltyCost);
	}
	public void writeSolution() throws IOException, IloException {
		String filename = RootPath + SolutionPath + "SP-Solution"
				+"(R="+in.getShipRouteSet().size()+")"
				+"(T="+(p.getTimePointSet().length-1)+")"
				+"(U="+p.getUncertainDegree()+")"
				+".txt";
		File file = new File(filename);
		if(!file.exists())
		{
			try {
				file.createNewFile();
			} catch (IOException e) {
				e.printStackTrace();
			}
		}

		FileWriter fileWriter2 = new FileWriter(file);

		double TotalOtherCost = 0;
		double TotalLadenCost = 0;
		double TotalEmptyCost = 0;
		double TotalRentalCost = 0;
		double TotalPenaltyCost = 0;

		int totalOwnedContainer = 0;
		int totalLeasedContainer = 0;
		int totalEmptyContainer = 0;
		int totalUnfulfilledContainer = 0;

		int noPathContainer = 0;

		fileWriter2.write("\n");

		for (int i = 0; i < in.getRequestSet().size(); i++)
		{
			Request od = in.getRequestSet().get(i);
			double totalRequestCost = 0;

			if(WhetherWriteFileLog){
				fileWriter2.write("Request"+od.getRequestID()
						+"("+od.getOriginPort()+"->"+od.getDestinationPort()+")"
						+"("+String.format("%.2f", (p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValue[i]))+")"
						+":"+"\n");
				fileWriter2.write("\t");
				fileWriter2.write("LadenContainerPath"+"("+od.getNumberOfLadenPath()+")"+":");
			}
			for (int k = 0; k < od.getNumberOfLadenPath(); k++)
			{
				if(cplex.getValue(xVar.get(i)[k]) != 0 || cplex.getValue(yVar.get(i)[k]) != 0 )
					fileWriter2.write(k+"("
							+p.getLadenPathCost()[k]
							+"x"
							+String.format("%.2f", cplex.getValue(xVar.get(i)[k]))
							+"+"
							+((p.getRentalCost()*p.getTravelTimeOnPath()[k])+p.getLadenPathCost()[k])
							+"x"
							+String.format("%.2f", cplex.getValue(yVar.get(i)[k]))
							+ ")"
					);

				totalOwnedContainer += cplex.getValue(xVar.get(i)[k]);
				totalLeasedContainer += cplex.getValue(yVar.get(i)[k]);

				totalRequestCost += p.getLadenPathCost()[k] * cplex.getValue(xVar.get(i)[k])
						+ (p.getLadenPathCost()[k] + (p.getRentalCost()*p.getTravelTimeOnPath()[k]) )* cplex.getValue(yVar.get(i)[k]);
				TotalLadenCost += p.getLadenPathCost()[k] * cplex.getValue(xVar.get(i)[k])
						+ p.getLadenPathCost()[k] * cplex.getValue(yVar.get(i)[k]);
				TotalRentalCost += (p.getRentalCost()*p.getTravelTimeOnPath()[k])* cplex.getValue(yVar.get(i)[k]);
			}
			fileWriter2.write("\t");

			fileWriter2.write("Unfulfilled : "
					+p.getPenaltyCostForDemand()[i]
					+"x"
					+ String.format("%.2f",cplex.getValue(gVar[i])) + "\t\t");
			if(od.getNumberOfLadenPath() == 0)
			{
				noPathContainer += cplex.getValue(gVar[i]);
			}

			totalRequestCost += p.getPenaltyCostForDemand()[i] * cplex.getValue(gVar[i]);
			TotalPenaltyCost += p.getPenaltyCostForDemand()[i] * cplex.getValue(gVar[i]);
			totalUnfulfilledContainer += cplex.getValue(gVar[i]);

			fileWriter2.write("EmptyContainerPath"+"("+od.getNumberOfEmptyPath()+")"+":");
			fileWriter2.write("\t");
			for (int k = 0; k < od.getNumberOfEmptyPath(); k++)
			{
				if(cplex.getValue(zVar.get(i)[k]) != 0)
					fileWriter2.write(k+"("
							+p.getEmptyPathCost()[k]
							+"x"
							+String.format("%.2f", cplex.getValue(zVar.get(i)[k]))
							+ ")"
					);
				totalRequestCost += p.getEmptyPathCost()[k] * cplex.getValue(zVar.get(i)[k]);
				TotalEmptyCost += p.getEmptyPathCost()[k] * cplex.getValue(zVar.get(i)[k]);

				totalEmptyContainer += cplex.getValue(zVar.get(i)[k]);
			}
			fileWriter2.write("\t");

			fileWriter2.write("totalRequestCost = "+ totalRequestCost);
			fileWriter2.write("\n");
			TotalOtherCost += totalRequestCost;
		}

		if(WhetherPrintRequestDecision){
			log.info("TotalLadenCost = " + "\t"
					+"TotalEmptyCost = " + "\t"
					+"TotalRentalCost = " + "\t"
					+"TotalPenaltyCost = " + "\t"
			);
			log.info(String.format("%.2f", TotalLadenCost) + "\t"
					+String.format("%.2f", TotalEmptyCost) + "\t"
					+String.format("%.2f", TotalRentalCost) + "\t"
					+String.format("%.2f", TotalPenaltyCost) + "\t"
			);
			log.info("TotalOwnedContainer "+"\t"
					+"TotalLeasedContainer " + "\t"
					+"TotalUnfulfilledContainer "+"\t"
					+"TotalEmptyContainer " + "\t"
			);
			log.info( totalOwnedContainer+"\t"
					+ totalLeasedContainer + "\t"
					+ totalUnfulfilledContainer + "\t"
					+ totalEmptyContainer + "\t"
			);
		}

		fileWriter2.write("TotalOtherCost = "+String.format("%.2f", TotalOtherCost)+"\n");
		fileWriter2.write("\n");
		fileWriter2.close();

		setLadenCost(TotalLadenCost);
		setEmptyCost(TotalEmptyCost);
		setRentalCost(TotalRentalCost);
		setPenaltyCost(TotalPenaltyCost);
	}

	public void writePortContainers() throws IOException, IloException {
		String filename = RootPath + SolutionPath
				+ "SP"+"_Port-Containers"
				+"(T="+(p.getTimePointSet().length-1)+")"
				+".txt";
		File file = new File(filename);
		if(!file.exists())
		{
			try {
				file.createNewFile();
			} catch (IOException e) {
				e.printStackTrace();
			}
		}

		FileWriter fileWriter = new FileWriter(file);

		int[][] Lpt = new int[p.getPortSet().length][p.getTimePointSet().length];

		fileWriter.write("TimePoint"+"\t");
		for (int pp = 0; pp < in.getPortSet().size(); pp++)
		{
			fileWriter.write(p.getPortSet()[pp]+"\t");
		}
		fileWriter.write("\n");

		for (int t = 0; t < p.getTimePointSet().length; t++) {
			fileWriter.write(t+"\t");
			for (int pp = 0; pp < in.getPortSet().size(); pp++) {

				if(t == 0)
				{
					Lpt[pp][t] = p.getInitialEmptyContainer()[pp];
				}
				else
				{
					Lpt[pp][t] = Lpt[pp][t-1];
					// i∈I
					for (int i = 0; i < p.getDemand().length; i++)
					{
						Request od = in.getRequestSet().get(i);

						// Input Z flow:
						// (item1)
						// o(i) == p
						if (p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
						{
							//θi
							for (int k = 0; k < od.getNumberOfEmptyPath(); k++)
							{
								int j = od.getEmptyPathIndexes()[k];
								// <n,n'> ∈A'
								for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++)
								{
									// p(n') == p
									//  t(n')== t
									if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
											&& in.getTravelingArcSet().get(nn).getDestinationTime() == t)
									{
										Lpt[pp][t] += (p.getArcAndPath()[nn][j] * cplex.getValue(zVar.get(i)[k]) );
									}
								}
							}
						}

						// Input flow X
						// item2
						// d(i) == p
						if (p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i]))
						{
							for (int k = 0; k < od.getNumberOfLadenPath(); k++)
							{
								int j = od.getLadenPathIndexes()[k];
								// <n,n'>∈A'
								for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
									// p(n‘)∈p
									// t(n')== t-sp
									if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
											&& in.getTravelingArcSet().get(nn).getDestinationTime() == t - p.getTurnOverTime()[pp])
									{
										Lpt[pp][t] += (p.getArcAndPath()[nn][j] *  cplex.getValue(xVar.get(i)[k]));
									}
								}
							}
						}

						//Output  flow X
						// item3
						// o(i) == p
						if (p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
						{
							// φi
							for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
								int j = od.getLadenPathIndexes()[k];

								// <n.n'>∈A'
								for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
									//p(n) == p
									// t(n) == t
									if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
											&& in.getTravelingArcSet().get(nn).getOriginTime() == t)
									{
										Lpt[pp][t] += (-p.getArcAndPath()[nn][j] * cplex.getValue(xVar.get(i)[k]));
									}
								}
							}
						}

						// Output Flow Z
						// item4
						// θ
						for (int k = 0; k < od.getNumberOfEmptyPath(); k++)
						{
							int jj = od.getEmptyPathIndexes()[k];

							// <n,n'>∈A'
							for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++)
							{
								// p(n) == p
								// t(n) == t
								if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
										&& in.getTravelingArcSet().get(nn).getOriginTime() == t)
								{
									Lpt[pp][t] += (-p.getArcAndPath()[nn][jj] * cplex.getValue(zVar.get(i)[k]));
								}
							}
						}
					}
				}

				fileWriter.write(Lpt[pp][t]+"\t");
			}
			fileWriter.write("\n");
		}

		fileWriter.close();
	}

}
