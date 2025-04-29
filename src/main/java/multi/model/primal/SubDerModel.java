package multi.model.primal;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.Parameter;
import multi.network.Request;
/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SubDerModel extends BasePrimalModel {
	private double[] uValueDouble;
	public SubDerModel(InputData in, Parameter p) {
		super();
		this.in = in;
		this.p = p;
		this.modelName = "SDP"+ "-R"+ in.getShipRouteSet().size() + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType + "-S" + DefaultSetting.randomSeed;
		this.uValueDouble = new double [p.getDemand().length];
		try{
			cplex = new IloCplex();

			publicSetting(cplex);
			frame();
		}catch (IloException e)
		{
			e.printStackTrace();
		}
	}


	protected void setDecisionVars() throws IloException
	{
		SetVesselDecisionVars();
		SetRequestDecisionVars();
	}

	protected void setObjectives() throws IloException
	{
		IloLinearNumExpr Obj=cplex.linearNumExpr();

		// item1 : Operating Cost
		// r∈R
		for(int r = 0; r<p.getShippingRouteSet().length; r++)
		{
			// h∈H
			for(int w = 0; w < p.getVesselPathSet().length; w++)
			{
				for (int h=0;h<p.getVesselSet().length;h++)
				{
					Obj.addTerm(p.getVesselTypeAndShipRoute()[h][r]
							*p.getShipRouteAndVesselPath()[r][w]
							*p.getVesselOperationCost()[h]
							, vVar[h][r]);
				}
			}
		}

		// i
		for(int i=0;i<p.getDemand().length;i++)
		{
			// item2 : Penalty Cost of unsatisfied Demand : c2i*Gi
			Obj.addTerm(p.getPenaltyCostForDemand()[i], gVar[i]);

			Request od = in.getRequestSet().get(i);
			// \phi_i
			for(int k=0;k<od.getNumberOfLadenPath();k++)
			{
				int j = od.getLadenPathIndexes()[k];
				// item3 : Demurrage of self-owned and leased containers and Rental cost on laden paths
				Obj.addTerm(p.getLadenPathCost()[j], xVar.get(i)[k]);
				Obj.addTerm(p.getLadenPathCost()[j], yVar.get(i)[k]);
				Obj.addTerm(p.getRentalCost()*p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
			}

			// item4: Demurrage of self-owned containers for empty path
			// \theta
			for(int k=0;k<od.getNumberOfEmptyPath();k++)
			{
				int j = od.getEmptyPathIndexes()[k];

				Obj.addTerm(p.getEmptyPathCost()[j], zVar.get(i)[k]);
			}
		}

		cplex.addMinimize(Obj);
	}

	private IloRange[] C1;

	protected void setConstraints() throws IloException
	{
		setConstraint0();
		
		setConstraint1();
		setConstraint2();
		setConstraint3();
	}

	//(15)each ship route selected one vessel type
	private void setConstraint0() throws IloException
	{
		// r∈R
		for(int r = 0; r<p.getShippingRouteSet().length; r++)
		{
			IloLinearIntExpr left=cplex.linearIntExpr();

			// h∈H
			for(int h=0;h<p.getVesselSet().length;h++)
			{
				// r(h) == r
				left.addTerm(p.getVesselTypeAndShipRoute()[h][r], vVar[h][r]);
			}
			String ConstrName = "C0("+(r+1)+")";
			cplex.addEq(left,1, ConstrName);
		}
	}

	//(21)demand equation
	private void setConstraint1() throws IloException 
	{
		C1 = new IloRange[p.getDemand().length];

		//∀i∈I
		for(int i=0;i<p.getDemand().length;i++)
		{
			IloLinearNumExpr left=cplex.linearNumExpr();

			Request od = in.getRequestSet().get(i);
			//φ
			for(int k=0;k<od.getNumberOfLadenPath();k++)
			{
				left.addTerm(1, xVar.get(i)[k]);
				left.addTerm(1, yVar.get(i)[k]);
			}

			left.addTerm(1, gVar[i]);

			String ConstrName = "C1("+(i+1)+")";
			C1[i] = cplex.addEq(left ,p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValueDouble[i], ConstrName);
		}
	}

	//(22) VesselType Capacity Constraint
	private void setConstraint2() throws IloException
	{
		// ∀<n,n'>∈A'
		for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
		{
			IloLinearNumExpr left=cplex.linearNumExpr();

			// i∈I
			for(int i=0;i<p.getDemand().length;i++)
			{
				Request od = in.getRequestSet().get(i);

				// φ
				for(int k=0; k<od.getNumberOfLadenPath(); k++)
				{
					int j = od.getLadenPathIndexes()[k];

					left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
					left.addTerm(p.getArcAndPath()[nn][j], yVar.get(i)[k]);
				}

				//θ
				for(int k=0;k<od.getNumberOfEmptyPath();k++)
				{
					int j = od.getEmptyPathIndexes()[k];

					left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
				}
			}

			// vessel capacity
			// r∈R
			for(int r = 0; r<p.getShippingRouteSet().length; r++)
			{
				// ω∈Ω
				for(int w=0;w<p.getVesselPathSet().length;w++)
				{
					// h∈H
					for(int h=0;h<p.getVesselSet().length;h++)
					{
						left.addTerm(-p.getArcAndVesselPath()[nn][w]
										*p.getShipRouteAndVesselPath()[r][w]
										*p.getVesselTypeAndShipRoute()[h][r]
										*p.getVesselCapacity()[h]
								, vVar[h][r]);
					}
				}
			}
			String ConstrName = "C3"+"("+(nn+1)+")";
			cplex.addLe(left,0, ConstrName);
		}
	}

	// (24)Containers flow conservation
	private void setConstraint3() throws IloException
	{
		// p \in P
		for(int pp = 0; pp < p.getPortSet().length; pp++)
		{
			// t \in T
			for(int t = 1; t < p.getTimePointSet().length; t++)
			{
				IloLinearNumExpr left = cplex.linearNumExpr();

				// i \in I
				for(int i = 0; i < p.getDemand().length; i++)
				{
					Request od = in.getRequestSet().get(i);

					// Input Z flow:
					// (item1)
					// o(i) == p
					if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
					{
						//θi
						for (int k = 0; k < od.getNumberOfEmptyPath(); k++)
						{
							int j = od.getEmptyPathIndexes()[k];

							// <n,n'> ∈A'
							for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
								// p(n') == p
								// 1<= t(n')<= t
								if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
										&& in.getTravelingArcSet().get(nn).getDestinationTime() <= t
										&& in.getTravelingArcSet().get(nn).getDestinationTime() >= 1)
								{
									left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
								}
							}
						}
					}


					// Input flow X
					// item2
					// d(i) == p
					if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i]))
					{
						for(int k=0;k<od.getNumberOfLadenPath();k++)
						{
							int j = od.getLadenPathIndexes()[k];

							// <n,n'>∈A'
							for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
							{
								// p(n‘)∈p
								// 1 <= t(n')<= t-sp
								if(in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
										&&in.getTravelingArcSet().get(nn).getDestinationTime()<=t-p.getTurnOverTime()[pp]
										&&in.getTravelingArcSet().get(nn).getDestinationTime()>=1)
								{
									left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
								}
							}
						}
					}


					//Output  flow X
					// item3
					// o(i) == p
					if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
					{
						// φi
						for(int k=0;k<od.getNumberOfLadenPath();k++)
						{
							int j = od.getLadenPathIndexes()[k];

							// <n.n'>∈A'
							for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
							{
								//p(n) == p
								// t(n) <= t
								if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
										&&in.getTravelingArcSet().get(nn).getOriginTime() <=t
										&&in.getTravelingArcSet().get(nn).getOriginTime() >=1)
								{
									left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
								}
							}
						}
					}


					// Output Flow Z
					// item4
					// θ
					for(int k=0;k<od.getNumberOfEmptyPath();k++)
					{
						int j = od.getEmptyPathIndexes()[k];

						// <n,n'>∈A'
						for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
						{
							// p(n) == p
							// t(n) <= t
							if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
									&& in.getTravelingArcSet().get(nn).getOriginTime()<=t
									&& in.getTravelingArcSet().get(nn).getOriginTime()>=1)
							{
								left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
							}
						}
					}
				}
				String ConstrName = "C3("+(pp+1)+")("+(t)+")";
				cplex.addGe(left, -p.getInitialEmptyContainer()[pp], ConstrName);
			}
		}
	}

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
				setObjVal(cplex.getObjValue());
				setSolveTime(endTime - startTime);
				setObjGap(cplex.getMIPRelativeGap());

				setvVarValue();
				setOperationCost();
			}
			else
			{
				log.info("No Solution");
			}
		}
		catch (IloException ex)
		{
			log.info("Concert Error: " + ex);
		}
	}
	private void setOperationCost() throws IloException {
		double operCost = 0;
		// r∈R
		for(int r = 0; r<p.getShippingRouteSet().length; r++)
		{
			// h∈H
			for(int h=0;h<p.getVesselSet().length;h++)
			{
				for (int w = 0; w < p.getVesselPathSet().length; w++) {
					operCost += p.getVesselOperationCost()[h]
							*p.getShipRouteAndVesselPath()[r][w]
							*p.getVesselTypeAndShipRoute()[h][r]
							*(int)(cplex.getValue(vVar[h][r]) + 0.5);
				}
			}
		}
		this.operationCost = operCost;
	}

	public void changeConstraints(double[] uValue) throws IloException {
		this.uValueDouble = uValue;
		/*
		Change Demand Equation Constraint(Constraint2)'s Right Coefficients
		 */
		//∀i∈I
		for(int i=0;i<p.getDemand().length;i++)
		{
		   C1[i].setBounds(p.getDemand()[i]+p.getMaximumDemandVariation()[i]* this.uValueDouble[i],
				   p.getDemand()[i]+p.getMaximumDemandVariation()[i]* this.uValueDouble[i]);
		}
	}

	public void setvVarValue() throws IloException {
		int[][] VValue = new	int[p.getVesselSet().length][p.getShippingRouteSet().length];
		for (int h = 0; h < p.getVesselSet().length; h++) {
			for (int r = 0; r < p.getShippingRouteSet().length; r++) {
				VValue[h][r] = (int)(cplex.getValue(vVar[h][r])+0.5);
			}
		}
		this.vVarValue = VValue;
	}

//	// An Unknown Error whiling get X
//	double[][] XValue;
//	private void setX() throws IloException {
//		this.XValue = new	double[p.getDemand().length][p.getPathSet().length];
//		for (int i = 0; i < p.getDemand().length; i++)
//		{
//			for (int j = 0; j < p.getPathSet().length; j++)
//			{
//				XValue[i][j] = cplex.getValue(xVar.get(i)[k]);
//			}
//		}
//	}
//	public double[][] getX()
//	{
//		return XValue;
//	}
}
