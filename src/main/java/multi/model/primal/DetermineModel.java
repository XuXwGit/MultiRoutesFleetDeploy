package multi.model.primal;

import ilog.concert.IloException;
import ilog.concert.IloLinearNumExpr;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.Parameter;

import java.io.IOException;
import java.util.Arrays;

/**
 * 确定性模型类
 *
 * 基于均值需求的确定性优化模型
 *
 * 数学模型特点:
 * 1. 使用需求均值E[ξ]代替随机变量ξ
 * 2. 目标函数: 最小化总运营成本
 *    min Σ_h Σ_r c_hr V_hr + Σ_a (c_x x_a + c_x1 x1_a + c_y y_a + c_z z_a)
 * 3. 约束条件:
 *    - 船舶分配约束 Σ_h V_hr = 1
 *    - 流量平衡约束
 *    - 容量约束
 *    - 需求满足约束
 *
 * 其中:
 * c_hr: 船舶类型h在航线r上的运营成本
 * V_hr: 船舶分配决策变量
 * c_x, c_x1, c_y, c_z: 各类集装箱的单位成本
 * x_a, x1_a, y_a, z_a: 各类集装箱的运输量
 *
 * @Author: XuXw
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class DetermineModel extends BasePrimalModel {
	private final String modelType;

	/**
	 * 确定性模型构造函数
	 *
	 * 初始化模型参数并构建确定性优化问题
	 *
	 * @param in 输入数据(网络结构、需求等)
	 * @param p 模型参数(成本系数、容量等)
	 */
	public DetermineModel(InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.model = "DM";
		this.modelName = model + "-R"+ in.getShipRouteSet().size()
				+ "-T" + p.getTimeHorizon()
				+ "-"+ DefaultSetting.FleetType
				+ "-S" + DefaultSetting.randomSeed
				+ "-V" + DefaultSetting.VesselCapacityRange;
		this.modelType = "UseMeanValue";
		try{
			if(DefaultSetting.WhetherPrintProcess || DefaultSetting.WhetherPrintIteration){
				log.info("=========DetermineModel==========");
			}

			cplex = new IloCplex();
			publicSetting(cplex);

			double start = System.currentTimeMillis();
			// 构建模型框架(变量定义、约束设置)
			frame();  // 继承自BasePrimalModel
			double end = System.currentTimeMillis();
			log.info("BuildTime = "+ ( end - start));
			start = System.currentTimeMillis();
			solveModel();
			end = System.currentTimeMillis();
			log.info("SolveTime = "+ ( end - start));

			if(DefaultSetting.WhetherCalculateMeanPerformance){
				calculateMeanPerformance();
			}
		}catch (IloException e) {
			e.printStackTrace();
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}

	public DetermineModel(InputData in, Parameter p, String modelType) {
		super();
		this.in = in;
		this.p = p;
		this.model = "DM";
		this.modelName = model + "-R"
				+ in.getShipRouteSet().size()
				+ "-T" + p.getTimeHorizon()
				+ "-"+ DefaultSetting.FleetType
				+ "-S" + DefaultSetting.randomSeed
				+ "-V" + DefaultSetting.VesselCapacityRange + "-" + modelType;
		this.modelType = modelType;
		try{
			if(DefaultSetting.WhetherPrintProcess || DefaultSetting.WhetherPrintIteration){
				log.info("=========DetermineModel==========");
			}
			cplex = new IloCplex();
			publicSetting(cplex);

			frame();

			solveModel();
		}catch (IloException e) {
			e.printStackTrace();
		}
	}

	@Override
	protected void setDecisionVars() throws IloException {
		// v[h][r/w] : binary variable ���� whether vessel type h is assigned to shipping route r/w
		SetVesselDecisionVars();

		// x[i][k]
		// y[i][k]
		// z[i][k]
		// g[i]
		SetRequestDecisionVars();
	}

	@Override
	protected void setObjectives() throws IloException {
		IloLinearNumExpr obj = cplex.linearNumExpr();
		obj = GetVesselOperationCostObj(obj);
		obj = GetRequestTransCostObj(obj);

		cplex.addMinimize(obj);
	}

	@Override
	protected void setConstraints() throws IloException
	{
		// each ship route assigned to one vessel
		long start = System.currentTimeMillis();
		setConstraint1();
		log.debug("Set Constraint1 Time = "+ (System.currentTimeMillis() - start));
		start = System.currentTimeMillis();

		// Demand Equation Constraints
		setConstraint2();
		log.debug("Set Constraint2 Time = "+ (System.currentTimeMillis() - start));
		start = System.currentTimeMillis();

		// Transport Capacity Constraints
		setConstraint3();
		log.debug("Set Constraint3 Time = "+ (System.currentTimeMillis() - start));
		start = System.currentTimeMillis();

		// Containers Flow Conservation Constraints
		setConstraint4();
		log.debug("Set Constraint4 Time = "+ (System.currentTimeMillis() - start));
	}

	/**
	 * (2) Each Route should be assigned only one VesselType
	 */
	private void setConstraint1() throws IloException
	{
		setVesselConstraint();
	}

	/**
	 *  (3) Set the demand equation constraints
	 */
	private void setConstraint2() throws IloException
	{
		double [] uValueDouble = new double[p.getDemand().length];

		if("UseMaxValue".equals(modelType)) {
			Arrays.fill(uValueDouble, 1.0);
		}

		// setDemandConstraint(xVar, yVar, gVar, uValueDouble);
		setDemandConstraint(xs, gVar, uValueDouble);
	}

	/**
	 * (4) Capacity Constraint on each travel arc
	 */
	private void setConstraint3() throws IloException
	{
		setCapacityConstraint();
	}

	/**
	 *  (29)
	 *   Containers flow conservation
	 *   Containers of each port p at each time t
	 */
	private void setConstraint4() throws IloException
	{
		setEmptyConservationConstraint();
	}

	public void solveModel()
	{
		try
		{
			if (DefaultSetting.WhetherExportModel) {
				exportModel();
			}
			long startTime = System.currentTimeMillis();
			if (cplex.solve())
			{
				long endTime = System.currentTimeMillis();

				setVVarsSolution();

				setObjVal(cplex.getObjValue());
				setSolveTime(endTime - startTime);
				setObjGap(cplex.getMIPRelativeGap());

				log.info("SolveTime = " + getSolveTime());

				if(DefaultSetting.WhetherPrintProcess){
					printSolution();
				}

			}
			else
			{
				log.info("No solution");
			}
			cplex.end();
		}
		catch (IloException ex) {
			log.info("Concert Error: " + ex);
		}
	}
}
