package multi.model.primal;

import lombok.Builder.Default;
import lombok.extern.slf4j.Slf4j;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import multi.DefaultSetting;
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
	private IloIntVar[][] vVar2;  // 决策变量 V_hw: 船舶类型h分配到路径w的二元变量
	private IloNumVar EtaVar;     // 辅助变量 η: 第二阶段的期望成本上界
	private IloNumVar[] etaVars;  // 辅助变量 η_k: 场景k下的第二阶段成本
	private int[][] vVarValue2;
	private double etaValue;
	private String type;
	public MasterProblem(IloCplex _cplex, InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.modelName = "MP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
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
		this.modelName = "MP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
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

					this.type = type;
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

	/**
	 * 设置第一阶段决策变量
	 *
	 * 数学模型中的变量:
	 * V_hr ∈ {0,1}: 船舶类型h分配到航线r的二元决策变量 (式3)
	 *   对应代码中的vesselVar[h][r]
	 *
	 * η ≥ 0: 第二阶段期望成本的上界变量 (式4)
	 *   对应代码中的EtaVar
	 *
	 * 约束条件:
	 * ∑_r V_hr ≤ 1, ∀h∈H (每艘船最多分配一条航线)
	 *   对应SetVesselDecisionVars()方法中的约束
	 *
	 * @throws IloException
	 */
	protected void setDecisionVars() throws IloException
	{
		/**
		 * 初始化船舶分配决策变量V_hr
		 * 数学模型: V_hr ∈ {0,1}, ∀h∈H, ∀r∈R
		 */
		SetVesselDecisionVars();
		
		/**
		 * 初始化第二阶段成本上界变量η
		 * 数学模型: η ≥ 0
		 */
		EtaVar = cplex.numVar(0,Integer.MAX_VALUE, "Eta");
	}

	/**
	 * 设置随机场景下的辅助决策变量
	 *
	 * 数学模型中的变量:
	 * η_k ≥ 0: 第k个场景下的第二阶段成本上界变量
	 *   对应代码中的etaVars[k]
	 *
	 * 约束条件:
	 * η = (1/K)∑_{k=1}^K η_k (所有场景的平均成本上界)
	 *   对应代码中的cplex.addEq(EtaVar, left)
	 *
	 * 其中:
	 * K: 场景数量(对应p.getSampleScenes().length)
	 *
	 * @throws IloException
	 */
	protected void setStochasticAuxiliaryDecisionVars() throws IloException {
		// 初始化每个场景的成本上界变量η_k
		etaVars = new IloNumVar[p.getSampleScenes().length];
		for(int k=0;k<p.getSampleScenes().length;++k)
		{
			etaVars[k]=cplex.numVar(0,Integer.MAX_VALUE, "Eta"+k);
		}
		// 添加场景平均成本约束: η = (1/K)∑η_k
		IloLinearNumExpr left = cplex.linearNumExpr();
		for(int k=0;k<p.getSampleScenes().length;++k)
		{
			left.addTerm(1.0/p.getSampleScenes().length, etaVars[k]);
		}
		cplex.addEq(EtaVar, left);
	}





	/**
	 * 设置随机规划模型的决策变量
	 *
	 * 包含:
	 * 1. 基本决策变量(V_hr, η)
	 * 2. 随机场景辅助变量(η_k)
	 *
	 * 调用顺序:
	 * 1. setDecisionVars(): 设置V_hr和η
	 * 2. setStochasticAuxiliaryDecisionVars(): 设置η_k
	 *
	 * @throws IloException
	 */
	private void setStochasticDecisionVars() throws IloException
	{
		setDecisionVars();  // 设置基本决策变量
		setStochasticAuxiliaryDecisionVars();  // 设置场景相关变量
	}


	/**
	 * 设置响应式模型的决策变量
	 *
	 * 数学模型中的变量:
	 * V_hr ∈ {0,1}: 船舶类型h分配到航线r的二元决策变量
	 *   对应代码中的vVar[h][r] (通过SetVesselDecisionVars()初始化)
	 *
	 * V_hw ∈ {0,1}: 船舶类型h分配到路径w的二元决策变量
	 *   对应代码中的vVar2[h][w]
	 *
	 * η ≥ 0: 第二阶段成本上界变量
	 *   对应代码中的EtaVar
	 *
	 * 约束条件:
	 * ∑_r V_hr + ∑_w V_hw ≤ 1, ∀h∈H (每艘船最多分配一条航线或路径)
	 *
	 * @throws IloException
	 */
	private void setReactiveDecisionVars() throws IloException
	{
		String varName;
		// 初始化船舶航线分配变量V_hr
		SetVesselDecisionVars();

		// 初始化船舶路径分配变量V_hw
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

		// 初始化第二阶段成本上界变量η
		EtaVar = cplex.numVar(0, Integer.MAX_VALUE, "Yita");
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

	/**
	 * 设置主问题目标函数
	 * 最小化: Σ_h Σ_r c_hr V_hr + η (式2)
	 * 其中:
	 * c_hr: 船舶类型h在航线r上的运营成本
	 * V_hr: 船舶分配决策变量
	 * η: 第二阶段期望成本上界
	 */
	protected void setObjectives() throws IloException
	{
		IloLinearNumExpr Obj = cplex.linearNumExpr();
		Obj = GetVesselOperationCostObj(Obj);  // 添加船舶运营成本项 Σ_h Σ_r c_hr V_hr
		Obj.addTerm(1, EtaVar);  // 添加η项
		cplex.addMinimize(Obj);  // 设置最小化目标
	}
	/**
	 * 设置响应式模型的目标函数
	 *
	 * 最小化: Σ_h Σ_r c_hr V_hr + Σ_h Σ_w c_hw V_hw + η (式2扩展)
	 * 其中:
	 * c_hr: 船舶类型h在航线r上的运营成本
	 * V_hr: 船舶航线分配决策变量
	 * c_hw: 船舶类型h在路径w上的运营成本
	 * V_hw: 船舶路径分配决策变量
	 * η: 第二阶段期望成本上界
	 *
	 * 代码实现:
	 * 1. GetVesselOperationCostObj: 计算Σ_h Σ_r c_hr V_hr
	 * 2. 循环添加路径成本项Σ_h Σ_w c_hw V_hw
	 * 3. 添加η项
	 *
	 * @throws IloException
	 */
	private void setReactiveObjectives() throws IloException
	{
		IloLinearNumExpr Obj = cplex.linearNumExpr();

		// 添加船舶航线运营成本 Σ_h Σ_r c_hr V_hr
		Obj = GetVesselOperationCostObj(Obj);

		// 添加船舶路径固定运营成本 Σ_h Σ_w c_hw V_hw
		for (int w = 0; w < p.getVesselPathSet().length; ++w)
		{
			int r = in.getVesselPathSet().get(w).getRouteID() - 1;
			// 路径w所属航线r
			// 船舶类型h属于集合H
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
	/**
	 * 设置主问题约束条件
	 * 包括:
	 * 1. 船舶分配约束 Σ_h V_hr = 1, ∀r ∈ R (式5)
	 */
	protected void setConstraints() throws IloException{
		setConstraint1();  // 设置船舶分配约束
	}

	/**
	 * 设置船舶分配约束
	 *
	 * 数学模型:
	 * 1. 标准模型约束: Σ_h V_hr = 1, ∀r ∈ R (式5)
	 *    每条航线r必须恰好分配一艘船
	 *
	 * 2. 响应式模型约束: Σ_h V_hw = 1, ∀w ∈ W
	 *    每条路径w必须恰好分配一艘船
	 *
	 * 其中:
	 * H: 船舶类型集合
	 * R: 航线集合
	 * W: 路径集合
	 *
	 * @throws IloException
	 */

	private void setConstraint1() throws IloException
	{
		/**
		 * 调用setVesselConstraint()设置船舶分配约束
		 *
		 * 实现:
		 * 1. 对于每条航线r: Σ_h V_hr = 1
		 * 2. 对于每条路径w: Σ_h V_hw = 1 (响应式模型)
		 */
		/**
		 * 设置船舶分配约束
		 *
		 * 数学模型:
		 * 1. 标准模型: Σ_h V_hr = 1, ∀r ∈ R
		 *    每条航线r必须恰好分配一艘船
		 * 2. 响应式模型: Σ_h V_hw = 1, ∀w ∈ W
		 *    每条路径w必须恰好分配一艘船
		 *
		 * 其中:
		 * V_hr: 船舶类型h分配到航线r的决策变量
		 * V_hw: 船舶类型h分配到路径w的决策变量
		 * R: 航线集合
		 * W: 路径集合
		 */
		setVesselConstraint();
	}

	private void setConstraint0(Map<String, List<IloNumVar[]>> xs, IloNumVar[] gVar, int k) throws IloException
	{
		IloLinearNumExpr left = cplex.linearNumExpr();
		left = GetRequestTransCostObj(left, xs, gVar);
		
		left.addTerm(-1, etaVars[k]);
		cplex.addLe(left, 0);
	}

		/*
	cutting plane for scene k
	 */
	private void setConstraint0(Map<String, List<IloNumVar[]>> xs, IloNumVar[] gVar) throws IloException
	{
		IloLinearNumExpr left = cplex.linearNumExpr();

		/**
		 * 计算二阶段运输成本目标函数部分
		 *
		 * 数学模型:
		 * Σ_h Σ_r c_hr V_hr (标准模型)
		 * 或
		 * Σ_h Σ_w c_hw V_hw (响应式模型)
		 *
		 * 其中:
		 * c_hr: 船舶类型h在航线r上的运营成本
		 * c_hw: 船舶类型h在路径w上的运营成本
		 * V_hr/V_hw: 船舶分配决策变量
		 *
		 * @param left 线性表达式构建器
		 * @return 添加了船舶运营成本项的表达式
		 */
		// left = GetVesselOperationCostObj(left);

		left = GetRequestTransCostObj(left, xs, gVar);
		
		left.addTerm(-1, EtaVar);
		cplex.addLe(left, 0);
	}



	/*
	cutting plane for scene k
	 */
	private void setConstraint0(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar, List<IloNumVar[]> zVar, IloNumVar[] gVar) throws IloException
	{
		IloLinearNumExpr left = cplex.linearNumExpr();

		/**
		 * 计算船舶运营成本目标函数部分
		 *
		 * 数学模型:
		 * Σ_h Σ_r c_hr V_hr (标准模型)
		 * 或
		 * Σ_h Σ_w c_hw V_hw (响应式模型)
		 *
		 * 其中:
		 * c_hr: 船舶类型h在航线r上的运营成本
		 * c_hw: 船舶类型h在路径w上的运营成本
		 * V_hr/V_hw: 船舶分配决策变量
		 *
		 * @param left 线性表达式构建器
		 * @return 添加了船舶运营成本项的表达式
		 */
		// left = GetVesselOperationCostObj(left);

		left = GetRequestTransCostObj(left, xVar, yVar, zVar, gVar);

		left.addTerm(-1, EtaVar);

		cplex.addLe(left, 0);
	}

	/*
	demand equation
	/sum{X+Y} + G = f
	 */
	/**
	 * 设置需求约束(对应数学模型中式7)
	 * Σ_p (x_ip + y_ip) + g_i = f_i, ∀i ∈ I
	 * 其中:
	 * x_ip: 自有集装箱在路径p上的运输量
	 * y_ip: 租赁集装箱在路径p上的运输量
	 * g_i: 未满足的需求量
	 * f_i: 总需求量
	 */
	private void setConstraint4(Map<String, List<IloNumVar[]>> xs, IloNumVar[] gVar, double[] uValue) throws IloException {
		setDemandConstraint(xs, gVar, uValue);
	}
	private void setConstraint4(List<IloNumVar[]> xVar, List<IloNumVar[]> yVar, IloNumVar[] gVar, double[] uValue) throws IloException {
		setDemandConstraint(xVar, yVar, gVar, uValue);
	}

	/*
	vessel capacity constraint
	/sum{X+Y+Z} <= V
	 */
	/**
	 * 设置船舶容量约束(对应数学模型中式8)
	 * Σ_i Σ_p (x_ip + y_ip + z_ip) a_np ≤ Σ_h Σ_r V_hr C_h a_nr, ∀n ∈ N
	 * 其中:
	 * a_np: 路径p是否使用弧n
	 * C_h: 船舶类型h的容量
	 */
	private void setConstraint5(Map<String, List<IloNumVar[]>> xs) throws IloException
	{
		setCapacityConstraint(xs);
	}
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
	/**
	 * 设置空集装箱平衡约束(对应数学模型中式9)
	 * l_pt + Σ_i Σ_q z_iq b_qt - Σ_i Σ_p x_ip b_pt ≥ 0, ∀p ∈ P, t ∈ T
	 * 其中:
	 * l_pt: 港口p在时间t的空箱库存
	 * b_qt: 空箱路径q是否在时间t到达港口p
	 */
	private void setConstraint6(Map<String, List<IloNumVar[]>> xs) throws IloException	{
		if(DefaultSetting.IsEmptyReposition){
            setEmptyConservationConstraint(xs.get("x"), xs.get("z"), 1);
        }else{
            setEmptyConservationConstraint(xs.get("x"), xs.get("z1"), 1);
            if(DefaultSetting.AllowFoldableContainer){
                setEmptyConservationConstraint(xs.get("x1"), xs.get("z2"), 0.5);
            }            
        }
	}
	private void setConstraint6(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar) throws IloException	{
		setEmptyConservationConstraint(xVar, zVar, 1);
	}

	public void setEtaValue(double etaValue) {
		this.etaValue = etaValue;
	}

	/**
	 * 为场景k添加第二阶段决策变量和约束
	 * 数学模型中的变量:
	 * x_ipk: 场景k下需求i在路径p上的自有集装箱运输量
	 * y_ipk: 场景k下需求i在路径p上的租赁集装箱运输量
	 * z_iqk: 场景k下需求i在空箱路径q上的调运量
	 * g_ik: 场景k下需求i的未满足量
	 * 约束包括:
	 * 最优性割约束(式10)
	 * 需求约束(式7)
	 * 容量约束(式8)
	 * 空箱平衡约束(式9)
	 */
	public void addScene(Scenario scene_k) throws IloException	{
		// second-stage variable :
		// by adding
		// x[i][p][k] : continue variable ���� number of self-owned containers shipped on path p for demand i in scene k
		// y[i][p][k] : continue variable ���� number of leased containers shipped on path p for demand i in scene k
		// z[i][q][k] : continue variable ���� number of self-owned containers repositioned on path q for demand i in scene k
		// g[i][k] : continue variable ���� number of unfulfilled containers for demand i on path p in scene k
		// l[p][t][k] : continue variable ���� number of self-owned containers shipped at port p at time t in scene k
		// create decision for scenery k
		Map<String, List<IloNumVar[]>> scene_k_xs = new HashMap<>(); 

		List<IloNumVar[]> xxVar_k = new ArrayList<>();
		scene_k_xs.put("x", xxVar_k);
		if(DefaultSetting.AllowFoldableContainer){
			List<IloNumVar[]> xx1Var_k = new ArrayList<>();
			scene_k_xs.put("x1", xx1Var_k);
		}
		List<IloNumVar[]> yyVar_k = new ArrayList<>();
		scene_k_xs.put("y", yyVar_k);

		List<IloNumVar[]> zzVar_k = new ArrayList<>();
		if(DefaultSetting.IsEmptyReposition){
			zzVar_k = new ArrayList<>();
			scene_k_xs.put("z", zzVar_k);
		}else{
			if(DefaultSetting.AllowFoldableContainer){
				List<IloNumVar[]> zz1Var_k = new ArrayList<>();
				scene_k_xs.put("z1", zz1Var_k);
			}
			if(DefaultSetting.AllowFoldableContainer){
				List<IloNumVar[]> zz2Var_k = new ArrayList<>();
				scene_k_xs.put("z2", zz2Var_k);
			}
		}

		IloNumVar[] gVar_k = new IloNumVar[p.getDemand().length];


		this.SetRequestDecisionVars(scene_k_xs, gVar_k);

		double[] request = scene_k.getRequest();

		if(this.type.equals("Stochastic")){
			setConstraint0(scene_k_xs, gVar_k, scene_k.getId());
		}else{
			setConstraint0(scene_k_xs, gVar_k);
		}
		// setConstraint4(xxVar_k, yyVar_k, gVar_k, request);
		setConstraint4(scene_k_xs, gVar_k, request);
		// setConstraint5(xxVar_k, yyVar_k, zzVar_k); 
		setConstraint5(scene_k_xs);  	// 对应约束条件(6): 船舶容量约束
		// setConstraint6(xxVar_k, zzVar_k);   // 对应约束条件(5): 空集装箱平衡约束
		setConstraint6(scene_k_xs);
	}
	
	/**
		* 添加反应式场景(对应两阶段随机规划的第二阶段问题)
		* @param scene_k 场景k
		* @throws IloException
		*
		* 数学模型变量对应关系:
		* xxVar_k ↔ X_{iφ}^k (自有集装箱运输决策)
		* yyVar_k ↔ Y_{iφ}^k (租赁集装箱运输决策)
		* zzVar_k ↔ Z_{iθ}^k (空集装箱调运决策)
		* gVar_k ↔ G_i^k (未满足需求决策)
		*
		* 约束条件:
		* setConstraint0 ↔ 初始条件约束
		* setConstraint4 ↔ 需求满足约束(式2)
		* setConstraint5_Reactive1 ↔ 自有集装箱运输平衡约束
		* setConstraint5_Reactive2 ↔ 空集装箱调运平衡约束
		* setConstraint6 ↔ 船舶容量约束(式3)
		*/
	public void addReactiveScene(Scenario scene_k) throws IloException {
		// 第二阶段决策变量:
		// x[i][p][k] : 场景k下需求i在路径p上运输的自有集装箱数量 (X_{iφ}^k)
		// y[i][p][k] : 场景k下需求i在路径p上运输的租赁集装箱数量 (Y_{iφ}^k)
		// z[i][q][k] : 场景k下需求i在路径q上调运的空集装箱数量 (Z_{iθ}^k)
		// g[i][k] : 场景k下需求i未满足的数量 (G_i^k)
		// l[p][t][k] : 场景k下港口p在时间t的空集装箱数量 (L_{pt}^k)
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

	/**
	 * 添加最优性割平面(对应数学模型中式10)
	 * Σ_n Σ_r Σ_h β_n V_hr C_h a_nr - η ≤ -π
	 *
	 * 数学表达式:
	 * ∑_{n∈A'} ∑_{r∈R} ∑_{h∈H_r} β_n V_hr q_h a_nr - η ≤ -π
	 *
	 * 其中:
	 * β_n: 对偶变量(弧n的容量约束乘子)
	 * V_hr: 主问题船舶分配决策变量
	 * q_h: 船舶h的容量(TEU)
	 * a_nr: 弧n是否属于航线r的指示变量
	 * η: 期望成本上界变量
	 * π: 常数项(子问题的目标值)
	 *
	 * 代码实现说明:
	 * - p.getArcAndVesselPath()[n][w]: a_nr (弧n与航线w的关系)
	 * - p.getShipRouteAndVesselPath()[r][w]: 航线r与路径w的关系
	 * - p.getVesselTypeAndShipRoute()[h][r]: 船舶类型h与航线r的关系
	 * - p.getVesselCapacity()[h]: q_h (船舶容量)
	 * - vVar[h][r]: V_hr (船舶分配决策变量)
	 * - EtaVar: η (期望成本上界变量)
	 */
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
					if(DefaultSetting.FleetType.equals("Homo")){
						// vValue[h][r] : come from solution of master problem
						left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta_value[n]
								, vVar[h][r]);
					} else if (DefaultSetting.FleetType.equals("Hetero")) {
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
	/**
	 * 添加可行性割平面(对应数学模型中的可行性割)
	 * Σ_n Σ_r Σ_h β_n V_hr C_h a_nr ≤ -π
	 *
	 * 数学表达式:
	 * ∑_{n∈A'} ∑_{r∈R} ∑_{h∈H_r} β_n V_hr q_h a_nr ≤ -π
	 *
	 * 与最优性割的区别:
	 * 1. 不包含η变量
	 * 2. 当子问题不可行时添加此约束
	 *
	 * 参数说明:
	 * @param constantItem -π (子问题不可行时的对偶目标值)
	 * @param beta_value β_n (对偶变量值数组)
	 */
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
						if(DefaultSetting.FleetType.equals("Homo")){
							// vValue[h][r] : come from solution of master problem
							left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
											*p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*beta_value[n]
									, vVar[h][r]);
						} else if (DefaultSetting.FleetType.equals("Hetero")) {
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


	/**
	 * 求解主问题模型(对应数学模型中的主问题MP)
	 *
	 * 输出:
	 * - 船舶分配决策V_hr (vVar变量值)
	 * - 期望成本上界η (EtaVar变量值)
	 * - 总运营成本 = 目标值 - η
	 *
	 * 数学模型对应:
	 * min ∑_{r∈R} ∑_{h∈H_r} c_{1hr} V_hr + η
	 * s.t. (1) 船舶分配约束
	 *      (10) 最优性割约束
	 *      (其他相关约束)
	 *
	 * 其中:
	 * c_{1hr}: 船舶h在航线r上的运营成本
	 * V_hr: 船舶分配决策变量
	 * η: 期望成本上界
	 */
	public void solveModel()
	{
		try
		{
			if (DefaultSetting.WhetherExportModel)
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

				if(DefaultSetting.WhetherPrintVesselDecision){
					printMPSolution();
				}

				// print master problem solution
				if (DefaultSetting.DebugEnable && DefaultSetting.MasterEnable )
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
			if (DefaultSetting.WhetherExportModel)
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
				if (DefaultSetting.DebugEnable && DefaultSetting.MasterEnable )
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
