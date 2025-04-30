package multi.model.primal;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.Parameter;
import multi.network.Request;
import multi.model.BaseModel;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

/**
 * 原始问题基础模型类
 *
 * 定义原始问题(Primal Problem)的通用变量和方法框架
 *
 * 主要变量:
 * vVar[h][r]: 船舶类型h分配到航线r的二元决策变量 V_hr ∈ {0,1}
 * xVar[k][a]: 场景k下普通箱运输量决策变量 x_ka ≥ 0
 * x1Var[k][a]: 场景k下折叠箱运输量决策变量 x1_ka ≥ 0
 * yVar[k][a]: 场景k下租赁箱运输量决策变量 y_ka ≥ 0
 * zVar[k][a]: 场景k下空箱重定向决策变量 z_ka ≥ 0
 *
 * 其中:
 * h ∈ H: 船舶类型集合
 * r ∈ R: 航线集合
 * k ∈ K: 场景集合
 * a ∈ A: 运输弧集合
 *
 * @Author: XuXw
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class BasePrimalModel extends BaseModel {
    public BasePrimalModel(InputData in, Parameter p) {
        super();
        this.in = in;
        this.p = p;
        try {
            cplex = new IloCplex();
            publicSetting(cplex);
            // 初始化决策变量和约束条件
            frame();  // 框架方法，由子类实现具体内容
        } catch (IloException e) {
            throw new RuntimeException(e);
        }
    }
    public BasePrimalModel() {
    }

    /**
     * 船舶分配决策变量
     * V_hr ∈ {0,1}: 船舶类型h分配到航线r的二元变量
     */
    protected IloIntVar[][] vVar;
    
    /**
     * 普通箱运输量决策变量
     * x_ka ≥ 0: 场景k下弧a的普通箱运输量
     */
    protected List<IloNumVar[]> xVar;
    
    /**
     * 折叠箱运输量决策变量
     * x1_ka ≥ 0: 场景k下弧a的折叠箱运输量
     */
    protected List<IloNumVar[]> x1Var;
    
    /**
     * 租赁箱运输量决策变量
     * y_ka ≥ 0: 场景k下弧a的租赁箱运输量
     */
    protected List<IloNumVar[]> yVar;
    
    /**
     * 空箱重定向决策变量
     * z_ka ≥ 0: 场景k下弧a的空箱重定向量
     */
    protected List<IloNumVar[]> zVar;
    protected List<IloNumVar[]> z1Var;  // 调度空普通箱
    protected List<IloNumVar[]> z2Var;  // 调度空折叠箱

    protected Map<String, List<IloNumVar[]>> xs;
 
    protected IloNumVar[] gVar;

    protected IloRange[] C1;
    protected IloRange[] C2;
    protected IloRange[][] C3;
    private double worstPerformance;
    private double meanPerformance;
    private double worstSecondStageCost;
    private double meanSecondStageCost;


    protected void setVesselConstraint() throws IloException {
        if(DefaultSetting.FleetType.equals("Homo")){
            setVesselConstraint11_1();
        }
        else if (DefaultSetting.FleetType.equals("Hetero")) {
            setVesselConstraint11_2();
            // two additional constraint
            setVesselConstraint12();
            setVesselConstraint13();
        }
        else{
            log.info("Error in Fleet type!");
        }
    }


    protected void setVesselConstraint11_1() throws IloException {

        // r \in R
        for (int r = 0; r < p.getShippingRouteSet().length; ++r)
        {
            IloLinearNumExpr left = cplex.linearNumExpr ();

            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h)
            {
                // r(h) == r
                left.addTerm(p.getVesselTypeAndShipRoute()[h][r], vVar[h][r]);
            }
            cplex.addEq(left, 1);
        }
    }

    // 异质船型约束1：Sum_h V[h][w] == 1
    protected void setVesselConstraint11_2() throws IloException {
        // w
        for (int w = 0; w < p.getVesselPathSet().length; ++w) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h) {
                // r(h) == r
                left.addTerm(1, vVar[h][w]);
            }
            cplex.addEq(left, 1);
        }
    }

    /*
     * Each vessel only assignment once at the same time : Sum_w V[h][w] <= 1
     * */
    protected void setVesselConstraint12() throws IloException {
        for (int h = 0; h < p.getVesselSet().length; h++) {
            IloLinearNumExpr left = cplex.linearNumExpr ();

            for (int r = 0; r < p.getShippingRouteSet().length; r++) {
                int n_r = p.getNumOfRoundTrips()[r];
                for (int w = 0; w < p.getVesselPathSet().length; w++) {
                    if(p.getShipRouteAndVesselPath()[r][w] == 1){
                        for (int i = 0; i < n_r; i++) {
                            if(w + i >= p.getVesselPathSet().length )
                            {
                                break;
                            }
                            if (p.getShipRouteAndVesselPath()[r][w+i] == 1) {
                                left.addTerm(1, vVar[h][w + i]);
                            }
                        }
                        break;
                    }
                }
            }

            cplex.addLe(left, 1);
        }
    }

     /** rotation cycle: V[h][w+n_r(w)] = V[h][w]* */
    protected void setVesselConstraint13() throws IloException {
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            int n_r = p.getNumOfRoundTrips()[r];
            if (w + n_r > p.getVesselPathSet().length - 1) {
                continue;
            }
            for (int h = 0; h < p.getVesselSet().length; h++) {
                if(p.getShipRouteAndVesselPath()[r][w] == 1 && p.getShipRouteAndVesselPath()[r][w+n_r] == 1){
                    IloLinearNumExpr left = cplex.linearNumExpr ();
                    left.addTerm(1, vVar[h][w]);
                    left.addTerm(-1, vVar[h][w+n_r]);
                    cplex.addEq(left, 0);
                }
            }
        }
    }

    public boolean checkVesselConstraint(double[][] vValueDouble) {
        if("Homo".equals(DefaultSetting.FleetType)){
            if(!checkVesselConstraint11_1(vValueDouble)){
                log.info("Error in VesselType Constraint 1");
                return false;
            }
        }
        else if ("Hetero".equals(DefaultSetting.FleetType)) {
            if(!checkVesselConstraint11_2(vValueDouble)){
                log.info("Error in VesselType Constraint 1");
                return false;
            }
            // two additional constraint
            if(!checkVesselConstraint12(vValueDouble)){
                log.info("Error in VesselType Constraint 2");
                return false;
            }
            if(!checkVesselConstraint13(vValueDouble)){
                log.info("Error in VesselType Constraint 3");
                return false;
            }
        }
        else{
            log.info("Error in Fleet type!");
        }
        return true;
    }


    protected boolean checkVesselConstraint11_1(double[][] vValueDouble)  {
        // r \in R
        for (int r = 0; r < p.getShippingRouteSet().length; ++r)
        {
            double left = 0;
            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h)
            {
                // r(h) == r
                left += (p.getVesselTypeAndShipRoute()[h][r] * vValueDouble[h][r]);
            }
            if (left - 1 > DefaultSetting.MIPGapLimit || left - 1 < -DefaultSetting.MIPGapLimit)
                return false;
        }
        return true;
    }


    protected boolean checkVesselConstraint11_2(double[][] vValueDouble)  {
        // w
        for (int w = 0; w < p.getVesselPathSet().length; ++w) {
            double left = 0;
            // h \in H
            for (int h = 0; h < p.getVesselSet().length; ++h) {
                // r(h) == r
                left += (1 * vValueDouble[h][w]);
            }
            if (left - 1 > DefaultSetting.MIPGapLimit || left - 1 < -DefaultSetting.MIPGapLimit)
                return false;
        }
        return true;
    }


    /* * Each vessel only assignment once at the same time : Sum_w V[h][w] <= 1* */
    protected boolean checkVesselConstraint12(double[][] vValueDouble) {
        for (int h = 0; h < p.getVesselSet().length; h++) {
            double left = 0;
            for (int r = 0; r < p.getShippingRouteSet().length; r++) {
                int n_r = p.getNumOfRoundTrips()[r];
                for (int w = 0; w < p.getVesselPathSet().length; w++) {
                    if(p.getShipRouteAndVesselPath()[r][w] == 1){
                        for (int i = 0; i < n_r; i++) {
                            if(w + i >= p.getVesselPathSet().length )
                            {
                                break;
                            }
                            if (p.getShipRouteAndVesselPath()[r][w+i] == 1) {
                                left += (1 * vValueDouble[h][w + i]);
                            }
                        }
                        break;
                    }
                }
            }

            if (left  > 1 )
                return false;
        }
        return true;
    }


    /* * rotation cycle: V[h][w+n_r(w)] = V[h][w] * */
    protected boolean checkVesselConstraint13(double[][] vValueDouble) {
        for (int w = 0; w < p.getVesselPathSet().length; w++) {
            int r = in.getVesselPathSet().get(w).getRouteID() - 1;
            int n_r = p.getNumOfRoundTrips()[r];
            if (w + n_r > p.getVesselPathSet().length - 1) {
                continue;
            }
            for (int h = 0; h < p.getVesselSet().length; h++) {
                if(p.getShipRouteAndVesselPath()[r][w] == 1 && p.getShipRouteAndVesselPath()[r][w+n_r] == 1){
                    double left = 0;
                    left += (1 * vValueDouble[h][w]);
                    left += (-1 * vValueDouble[h][w+n_r]);
                    if (left > DefaultSetting.MIPGapLimit || left < -DefaultSetting.MIPGapLimit)
                        return false;
                }
            }
        }
        return true;
    }


    protected void setDemandConstraint(Map<String, List<IloNumVar[]>> xs, 
                                                                IloNumVar[] gVar, 
                                                                double[] uValue)
                            throws IloException {
        //∀i∈I
        for (int i = 0; i < p.getDemand().length; ++i) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            Request od = in.getRequestSet().get(i);
            //φ
            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                if(xs.containsKey("x")){
                    left.addTerm(1, xs.get("x").get(i)[k]);
                }
                if(xs.containsKey("x1")){
                    left.addTerm(1,  xs.get("x1").get(i)[k]);
                }
                if(xs.containsKey("y")){
                    left.addTerm(1,  xs.get("y").get(i)[k]);
                }
            }

            left.addTerm(1, gVar[i]);

            String ConstrName = "C1(" + (i + 1) + ")";
            cplex.addEq(left, p.getDemand()[i] +
                    p.getMaximumDemandVariation()[i] * uValue[i], ConstrName);
        }
    }

    protected void setDemandConstraint(List<IloNumVar[]> xVar, 
                                                                List<IloNumVar[]> yVar, 
                                                                IloNumVar[] gVar, 
                                                                double[] uValue) 
                            throws IloException {
        //∀i∈I
        for (int i = 0; i < p.getDemand().length; ++i) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            Request od = in.getRequestSet().get(i);
            //φ
            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                left.addTerm(1, xVar.get(i)[k]);
                left.addTerm(1, yVar.get(i)[k]);
            }

            left.addTerm(1, gVar[i]);

            String ConstrName = "C1(" + (i + 1) + ")";
            cplex.addEq(left, p.getDemand()[i] +
                    p.getMaximumDemandVariation()[i] * uValue[i], ConstrName);
        }
    }

    protected void setCapacityConstraint() throws IloException  {
        // setCapacityConstraint(xVar, yVar, zVar);
        setCapacityConstraint(xs);
    }

    protected void setCapacityConstraint(Map<String, List<IloNumVar[]>> xs) throws IloException  {
        C2 = new IloRange[p.getTravelingArcsSet().length];

        // ∀<n,n'>∈A'
        for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
            IloLinearNumExpr left = cplex.linearNumExpr();

            // i∈I
            for (int i = 0; i < p.getDemand().length; ++i) {
                Request od = in.getRequestSet().get(i);

                // φ
                for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                    int j = od.getLadenPathIndexes()[k];
                    if(xs.containsKey("x")){
                            left.addTerm(p.getArcAndPath()[nn][j], xs.get("x").get(i)[k]);
                    }

                    if(xs.containsKey("x1")){
                            left.addTerm(p.getArcAndPath()[nn][j], xs.get("x1").get(i)[k]);
                    }

                    if(xs.containsKey("y")){
                            left.addTerm(p.getArcAndPath()[nn][j], xs.get("y").get(i)[k]);
                    }

                    if(xs.containsKey("z1")){
                            left.addTerm(p.getArcAndPath()[nn][j], xs.get("z1").get(i)[k]);
                    }

                    if(xs.containsKey("z2")){
                            left.addTerm(p.getArcAndPath()[nn][j] * 0.25, xs.get("z2").get(i)[k]);
                    }
                }

                //θ
                for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                    int j = od.getEmptyPathIndexes()[k];
                    
                    if(xs.containsKey("z")){
                            left.addTerm(p.getArcAndPath()[nn][j], xs.get("z").get(i)[k]);
                    }
                }
            }

            // r \in R
            // w \in \Omega
            // r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
            for(int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(DefaultSetting.FleetType.equals("Homo")){
                    // h \in H_r
                    // r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
                    for(int h = 0; h < p.getVesselSet().length; ++h){
                        left.addTerm(-p.getVesselTypeAndShipRoute()[h][r]
                                        * p.getShipRouteAndVesselPath()[r][w]
                                        * p.getArcAndVesselPath()[nn][w]
                                        * p.getVesselCapacity()[h],
                                vVar[h][r]
                        );
                    }
                } else if (DefaultSetting.FleetType.equals("Hetero")) {
                    // h \in H
                    for(int h = 0; h < p.getVesselSet().length; ++h)
                    {
                        left.addTerm(- p.getArcAndVesselPath()[nn][w]
                                        * p.getVesselCapacity()[h],
                                vVar[h][w]
                        );
                    }
                }
                else{
                    log.info("Error in Fleet type!");
                }
            }
            String ConstrName = "C3" + "(" + (nn + 1) + ")";
            C2[nn] = cplex.addLe(left, 0, ConstrName);
        }
    }

    protected void setCapacityConstraint(List<IloNumVar[]> xVar, 
                                                                List<IloNumVar[]> yVar, 
                                                                List<IloNumVar[]> zVar) throws IloException  {
        C2 = new IloRange[p.getTravelingArcsSet().length];

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

                //θ
                for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                    int j = od.getEmptyPathIndexes()[k];

                    left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                }
            }

            // r \in R
            // w \in \Omega
            // r(w) = r : p.getShipRouteAndVesselPath()[r][w] == 1
            for(int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(DefaultSetting.FleetType.equals("Homo")){
                    // h \in H_r
                    // r(h) = r : p.getVesselTypeAndShippingRoute()[h][r] == 1
                    for(int h = 0; h < p.getVesselSet().length; ++h){
                        left.addTerm(-p.getVesselTypeAndShipRoute()[h][r]
                                        * p.getShipRouteAndVesselPath()[r][w]
                                        * p.getArcAndVesselPath()[nn][w]
                                        * p.getVesselCapacity()[h],
                                vVar[h][r]
                        );
                    }
                } else if (DefaultSetting.FleetType.equals("Hetero")) {
                    // h \in H
                    for(int h = 0; h < p.getVesselSet().length; ++h)
                    {
                        left.addTerm(- p.getArcAndVesselPath()[nn][w]
                                        * p.getVesselCapacity()[h],
                                vVar[h][w]
                        );
                    }
                }
                else{
                    log.info("Error in Fleet type!");
                }
            }
            String ConstrName = "C3" + "(" + (nn + 1) + ")";
            C2[nn] = cplex.addLe(left, 0, ConstrName);
        }
    }
    protected void setEmptyConservationConstraint() throws IloException {
        if(DefaultSetting.IsEmptyReposition){
            setEmptyConservationConstraint(xVar, zVar, 1);
        }else{
            setEmptyConservationConstraint(xVar, z1Var, 1 - DefaultSetting.DefaultFoldContainerPercent);
            if(DefaultSetting.AllowFoldableContainer){
                setEmptyConservationConstraint(x1Var, z2Var, DefaultSetting.DefaultFoldContainerPercent);
            }
        }
    }

    protected void setEmptyConservationConstraint(Map<String, List<IloNumVar[]>> xsMap) throws IloException {
        if(DefaultSetting.IsEmptyReposition){
            setEmptyConservationConstraint(xsMap.get("x"), xs.get("z"), 1);
        }else{
            setEmptyConservationConstraint(xsMap.get("x"), xsMap.get("z1"), 1 - DefaultSetting.DefaultFoldContainerPercent);
            if(DefaultSetting.AllowFoldableContainer){
                setEmptyConservationConstraint(xsMap.get("x1"), xsMap.get("z2"), DefaultSetting.DefaultFoldContainerPercent);
            }
        }
    }

    protected void setEmptyConservationConstraint(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar, double initial_port_container_coeff) throws IloException {
        if(DefaultSetting.WhetherUseMultiThreads){
            //long start = System.currentTimeMillis();
            setEmptyConservationConstraintWithMultiThread(xVar, zVar);
            //log.info("Set Empty Conservation Constraint Time(Multi Threads) = "+ (System.currentTimeMillis() - start));
        } else {
            //long start = System.currentTimeMillis();
            setEmptyConservationConstraintSingleThread(xVar, zVar, initial_port_container_coeff);
            //log.info("Set Empty Conservation Constraint Time = "+ (System.currentTimeMillis() - start));
        }
    }

    protected void setEmptyConservationConstraintSingleThread(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar, double initial_port_container_coeff) throws IloException{
        C3 = new IloRange[p.getPortSet().length][p.getTimePointSet().length];
        // p \in P
        for (int pp = 0; pp < p.getPortSet().length; ++pp)
        {
            IloLinearNumExpr left = cplex.linearNumExpr();
            // t \in T
            for (int t = 1; t < p.getTimePointSet().length; ++t)
            {
                // i \in I
                for (int i = 0; i < p.getDemand().length; ++i) {
                    Request od = in.getRequestSet().get(i);

                    // Input Z flow:
                    // (item1)
                    // o(i) == p
                    if(DefaultSetting.IsEmptyReposition){
                        if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                            //θi
                            for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                                int j = od.getEmptyPathIndexes()[k];

                                // <n,n'> ∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    // p(n') == p
                                    // 1<= t(n')<= t
                                    if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getDestinationTime() == t
                                            ) {
                                        left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                    }
                                }
                            }
                        }                        
                    }


                    // Input flow X
                    // item2
                    // d(i) == p
                    if (p.getDestinationOfDemand()[i].equals(p.getPortSet()[pp])) {
                        for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                            int j = od.getLadenPathIndexes()[k];

                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                // p(n‘)∈p
                                // 1 <= t(n')<= t-sp
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() == t - p.getTurnOverTime()[pp]) {
                                    left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                    if(!DefaultSetting.IsEmptyReposition && DefaultSetting.AllowFoldableContainer){
                                        left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                    }
                                }
                            }
                        }
                    }

                    //Output  flow X
                    // item3
                    // o(i) == p
                    if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                        // φi
                        for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                            int j = od.getLadenPathIndexes()[k];

                            // <n.n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                //p(n) == p
                                // t(n) <= t
                                if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                    left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                    if(!DefaultSetting.IsEmptyReposition && DefaultSetting.AllowFoldableContainer){
                                        left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                    }
                                }
                            }
                        }
                    }


                    // Output Flow Z
                    // item4
                    // θ
                    if(DefaultSetting.IsEmptyReposition){
                        for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                            int j = od.getEmptyPathIndexes()[k];

                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                // p(n) == p
                                // t(n) <= t
                                if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                    left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                }
                            }
                        }
                    }
                }

                String ConstrName = "C3(" + (pp + 1) + ")(" + (t) + ")";
                double initial_port_containers = p.getInitialEmptyContainer()[pp] * initial_port_container_coeff;
                C3[pp][t] = cplex.addGe(left, -initial_port_containers, ConstrName);
            }
        }
    }

    protected void setEmptyConservationConstraintWithMultiThread(List<IloNumVar[]> xVar, List<IloNumVar[]> zVar) throws IloException	{

        ExecutorService executor = Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());

        C3 = new IloRange[p.getPortSet().length][p.getTimePointSet().length];

        IloLinearNumExpr[][] leftItems = new IloLinearNumExpr[p.getPortSet().length][p.getTimePointSet().length];
        // p \in P
        for (int portIndex = 0; portIndex < p.getPortSet().length; ++portIndex)
        {
            final int pp = portIndex;
            // t \in T
            for (int tt = 1; tt < p.getTimePointSet().length; ++tt)
            {
                final int t = tt;

                //// parallel
                executor.submit(() -> {

                    IloLinearNumExpr left;
                    try {
                        left = cplex.linearNumExpr();
                    } catch (IloException e) {
                        throw new RuntimeException(e);
                    }
                    // i \in I
                    for (int i = 0; i < p.getDemand().length; ++i) {
                        Request od = in.getRequestSet().get(i);

                        // Input Z flow:
                        // (item1)
                        // o(i) == p
                        if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                            //θi
                            for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                                int j = od.getEmptyPathIndexes()[k];

                                // <n,n'> ∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    // p(n') == p
                                    // 1<= t(n')<= t
                                    if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getDestinationTime() == t) {
                                        try {
                                            left.addTerm(p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }

                        // Input flow X
                        // item2
                        // d(i) == p
                        if (p.getDestinationOfDemand()[i].equals(p.getPortSet()[pp])) {
                            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                                int j = od.getLadenPathIndexes()[k];

                                // <n,n'>∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    // p(n‘)∈p
                                    // 1 <= t(n')<= t-sp
                                    if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getDestinationTime() == t - p.getTurnOverTime()[pp]) {
                                        try {
                                            left.addTerm(p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }

                        //Output  flow X
                        // item3
                        // o(i) == p
                        if (p.getOriginOfDemand()[i].equals(p.getPortSet()[pp])) {
                            // φi
                            for (int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                                int j = od.getLadenPathIndexes()[k];

                                // <n.n'>∈A'
                                for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                    //p(n) == p
                                    // t(n) == t
                                    if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                            && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                        try {
                                            left.addTerm(-p.getArcAndPath()[nn][j], xVar.get(i)[k]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }


                        // Output Flow Z
                        // item4
                        // θ
                        for (int k = 0; k < od.getNumberOfEmptyPath(); ++k) {
                            int j = od.getEmptyPathIndexes()[k];

                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; ++nn) {
                                // p(n) == p
                                // t(n) == t
                                if (in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getOriginTime() == t) {
                                    try {
                                        left.addTerm(-p.getArcAndPath()[nn][j], zVar.get(i)[k]);
                                    } catch (IloException e) {
                                        throw new RuntimeException(e);
                                    }
                                }
                            }
                        }
                    }

                    leftItems[pp][t] = left;
                });
            }
        }

        executor.shutdown();

        try {
            executor.awaitTermination(Long.MAX_VALUE, TimeUnit.NANOSECONDS);
        } catch (InterruptedException e) {
            // 处理中断异常
            throw new RuntimeException(e);
        }

        for (int pp = 0; pp < p.getPortSet().length; pp++) {
            IloLinearNumExpr left = cplex.linearNumExpr();
            for (int t = 1; t < p.getTimePointSet().length; ++t){
                left.add(leftItems[pp][t]);
                String ConstrName = "C3(" + (pp + 1) + ")(" + (t) + ")";
                C3[pp][t] = cplex.addGe(left, -p.getInitialEmptyContainer()[pp], ConstrName);
            }
        }
    }
    protected double operationCost;
    public double getOperationCost() {
        return operationCost;
    }

    public void setOperationCost(double operationCost) {
        this.operationCost = operationCost;
    }
    protected double getOperationCost(int[][] vValue){
        double operation_cost = 0;
        for (int h = 0; h < p.getVesselSet().length; ++h)
        {
            for (int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                // r(��) == r
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(DefaultSetting.FleetType.equals("Homo")) {
                    // vesselTypeAndShipRoute == 1 : r(h) = r
                    operation_cost += (p.getVesselTypeAndShipRoute()[h][r]
                            * p.getShipRouteAndVesselPath()[r][w]
                            * p.getVesselOperationCost()[h]
                            * vValue[h][r]);
                }
                else if (DefaultSetting.FleetType.equals("Hetero")) {
                    operation_cost += (p.getVesselOperationCost()[h]
                            * vValue[h][w]);
                }
            }
        }
        return operation_cost;
    }

    protected int[][] vVarValue;
    public int[][] getVVarValue() {
        return vVarValue;
    }
    public void setVVarValue(int[][] vVarValue) {
        this.vVarValue = vVarValue;
    }
    private int[] solution;
    public int[] getSolution(){
        return solution;
    }
    protected void setSolution(int[] solution){
        this.solution = solution;
    }
    public double getWorstPerformance() {
        return worstPerformance;
    }
    protected void setWorstPerformance(double worstPerformance) {
        this.worstPerformance = worstPerformance;
    }
    public double getMeanPerformance() {
        return meanPerformance;
    }

    public void setMeanPerformance(double meanPerformance) {
        this.meanPerformance = meanPerformance;
    }
    public double getWorstSecondStageCost() {
        return worstSecondStageCost;
    }

    protected void setWorstSecondStageCost(double worstSecondStageCost) {
        this.worstSecondStageCost = worstSecondStageCost;
    }
    public double getMeanSecondStageCost() {
        return meanSecondStageCost;
    }

    protected void setMeanSecondStageCost(double meanSecondStageCost) {
        this.meanSecondStageCost = meanSecondStageCost;
    }

    public IloCplex.Status getSolveStatus() throws IloException {
        return cplex.getStatus();
    }
    public String getSolveStatusString() throws IloException {
        if (cplex.getStatus() == IloCplex.Status.Optimal)
            return "Optimal";
        else if (cplex.getStatus() == IloCplex.Status.Feasible) {
            return "Feasible";
        }
        else if (cplex.getStatus() == IloCplex.Status.Infeasible) {
            return "Infeasible";
        }
        else if (cplex.getStatus() == IloCplex.Status.Bounded) {
            return "Bounded";
        }
        return "Others";
    }
    protected void SetVesselDecisionVars() throws IloException {
        // first-stage variable :
        // v[h][r] : binary variable ���� whether vessel type h is assigned to shipping route r
        // eta : auxiliary decision variable ���� the upper bound of second-stage objective under all scene
        if(DefaultSetting.FleetType.equals("Homo")){
            vVar =new IloIntVar [p.getVesselSet().length] [p.getShippingRouteSet().length];
            vVarValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
        } else if (DefaultSetting.FleetType.equals("Hetero")) {
            vVar =new IloIntVar [p.getVesselSet().length] [p.getVesselPathSet().length];
            vVarValue = new int[p.getVesselSet().length] [p.getVesselPathSet().length];
        }
        else{
            log.info("Error in Fleet type!");
        }

        // V[h][r]
        String varName;
        for(int h=0;h<p.getVesselSet().length;++h)
        {
            if(DefaultSetting.FleetType.equals("Homo")){
                for(int r = 0; r<p.getShippingRouteSet().length; r++)
                {
                    varName = "V("+(p.getVesselSet()[h])+")("+(p.getShippingRouteSet()[r])+")";
                    vVar[h][r]=cplex.boolVar(varName);
                }
            } else if (DefaultSetting.FleetType.equals("Hetero")) {
                for(int w = 0; w < p.getVesselPathSet().length; ++w)
                {
                    varName = "V("+(p.getVesselSet()[h])+")("+(p.getVesselPathSet()[w])+")";
                    vVar[h][w]=cplex.boolVar(varName);
                }
            }
        }
    }

    // set container path variables
    protected void SetRequestDecisionVars(List<IloNumVar[]> xVar,  
                                                                    List<IloNumVar[]> yVar, 
                                                                    List<IloNumVar[]> zVar, 
                                                                    IloNumVar[] gVar) throws IloException {
        String varName;

        for (int i = 0; i < p.getDemand().length; i++) {
            Request od = in.getRequestSet().get(i);

            IloNumVar[] xxxVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] yyyVar_k = new IloNumVar[od.getNumberOfLadenPath()];

            IloNumVar[] zzzVar_k = new IloNumVar[od.getNumberOfEmptyPath()];

            xVar.add(xxxVar_k);
            yVar.add(yyyVar_k);
            zVar.add(zzzVar_k);

            for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
                varName = "x(" + (i + 1) + ")";
                xVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
                varName = "y(" + (i + 1) + ")";
                yVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
            }
            for (int k = 0; k < od.getNumberOfEmptyPath(); k++) {
                varName = "z(" + (i + 1) + ")";
                zVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
            }

            varName = "g(" + (i + 1) + ")";
            gVar[i] = cplex.numVar(0, Integer.MAX_VALUE, varName);
        }
    }

    // set container path variables
    protected void SetRequestDecisionVars(Map<String, List<IloNumVar[]>> xs,  IloNumVar[] gVar) throws IloException {
        String varName;
        
        List<IloNumVar[]> xVar = xs.get("x");
        List<IloNumVar[]> x1Var = xs.get("x1");
        List<IloNumVar[]> yVar = xs.get("y");
        List<IloNumVar[]> zVar = xs.get("z");
        List<IloNumVar[]> z1Var = xs.get("z1");
        List<IloNumVar[]> z2Var = xs.get("z2");

        for (int i = 0; i < p.getDemand().length; i++) {
            Request od = in.getRequestSet().get(i);

            IloNumVar[] xxxVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] xxx1Var_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] yyyVar_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] zzz1Var_k = new IloNumVar[od.getNumberOfLadenPath()];
            IloNumVar[] zzz2Var_k = new IloNumVar[od.getNumberOfLadenPath()];

            IloNumVar[] zzzVar_k = new IloNumVar[od.getNumberOfEmptyPath()];

            xVar.add(xxxVar_k);
            x1Var.add(xxx1Var_k);
            yVar.add(yyyVar_k);

            z1Var.add(zzz1Var_k);
            z2Var.add(zzz2Var_k);

            for (int k = 0; k < od.getNumberOfLadenPath(); k++) {
                if(xs.containsKey("x")){
                    varName = "x(" + (i + 1) + ")";
                    xVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);                    
                }
                if(xs.containsKey("x1")){
                    varName = "x1(" + (i + 1) + ")";
                    x1Var.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);            
                }
                if(xs.containsKey("y")){
                    varName = "y(" + (i + 1) + ")";
                    yVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);                    
                }
                if(xs.containsKey("z1")){
                    varName = "z1(" + (i + 1) + ")";
                    z1Var.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
                }
                if(xs.containsKey("z2")){
                    varName = "z2(" + (i + 1) + ")";
                    z2Var.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
                }
            }

            if(DefaultSetting.IsEmptyReposition){
                zVar.add(zzzVar_k);
                for (int k = 0; k < od.getNumberOfEmptyPath(); k++) {
                    varName = "z(" + (i + 1) + ")";
                    zVar.get(i)[k] = cplex.numVar(0, Integer.MAX_VALUE, varName);
                }
            }

            varName = "g(" + (i + 1) + ")";
            gVar[i] = cplex.numVar(0, Integer.MAX_VALUE, varName);
        }
    }

    protected void SetRequestDecisionVars() throws IloException {
        xs = new HashMap<>();
        xVar = new ArrayList<>();
        xs.put("x", xVar);
        
        if(DefaultSetting.AllowFoldableContainer){
            x1Var = new ArrayList<>();
            xs.put("x1", x1Var);
        }

        yVar = new ArrayList<>();
        xs.put("y", yVar);

        if(DefaultSetting.IsEmptyReposition){
            zVar = new ArrayList<>();
        }{
            z1Var = new ArrayList<>();
            xs.put("z1", z1Var);
            z2Var = new ArrayList<>();
            xs.put("z2", z2Var);            
        }
        
        gVar = new IloNumVar[p.getDemand().length];
        // SetRequestDecisionVars(xVar, yVar, zVar, gVar);
        SetRequestDecisionVars(xs, gVar);
    }

    protected IloLinearNumExpr GetVesselOperationCostObj(IloLinearNumExpr Obj) throws IloException {
        // add fixed operating cost to maintain shipping route
        // w
        // h�ʦ�
        for (int h = 0; h < p.getVesselSet().length; ++h)
        {
            for (int w = 0; w < p.getVesselPathSet().length; ++w)
            {
                // r(��) == r
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;

                if(DefaultSetting.FleetType.equals("Homo")) {
                    // vesselTypeAndShipRoute == 1 : r(h) = r
                    Obj.addTerm(p.getVesselTypeAndShipRoute()[h][r]
                                    * p.getShipRouteAndVesselPath()[r][w]
                                    * p.getVesselOperationCost()[h]
                            , vVar[h][r]);
                }
                else if (DefaultSetting.FleetType.equals("Hetero")) {
                    Obj.addTerm(p.getVesselOperationCost()[h]
                            , vVar[h][w]);
                }
            }
        }

        return Obj;
    }


    protected IloLinearNumExpr GetRequestTransCostObj(IloLinearNumExpr Obj, Map<String, List<IloNumVar[]>> xs,  IloNumVar[] gVar)
            throws IloException{

        List<IloNumVar[]> xVar = xs.get("x");
        List<IloNumVar[]> x1Var = xs.get("x1");
        List<IloNumVar[]> yVar = xs.get("y");
        List<IloNumVar[]> zVar = xs.get("z");
        List<IloNumVar[]> z1Var = xs.get("z1");
        List<IloNumVar[]> z2Var = xs.get("z2");
        
        // i \in I
        for(int i = 0; i < p.getDemand().length; ++i){
            // item2 : Penalty Cost of unsatisfied Demand
            Obj.addTerm(p.getPenaltyCostForDemand()[i], gVar[i]);

            Request od = in.getRequestSet().get(i);

            // \phi \in \\Phi_i
            for(int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                int j = od.getLadenPathIndexes()[k];
                // item3 : Demurrage of self-owned and leased containers and Rental cost on laden paths
                // x：标准
                if(xs.containsKey("x")){
                    Obj.addTerm(p.getLadenPathCost()[j], xVar.get(i)[k]);
                }
                // x1：折叠
                if(xs.containsKey("x1")){
                    Obj.addTerm(p.getLadenPathCost()[j], x1Var.get(i)[k]);
                }
                // y：租赁
                if(xs.containsKey("y")){
                    Obj.addTerm(p.getLadenPathCost()[j], yVar.get(i)[k]);
                    Obj.addTerm(p.getRentalCost() * p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
                }
                // z1：重调度空箱
                if(xs.containsKey("x1")){
                    Obj.addTerm(p.getLadenPathCost()[j] * 0.5, z1Var.get(i)[k]);
                }
                // z2：重调度折叠箱
                if(xs.containsKey("x2")){
                    Obj.addTerm(p.getLadenPathCost()[j] * 0.5 + DefaultSetting.DefaultFoldEmptyCostBias, z2Var.get(i)[k]);
                }
            }

            // \theta \in \\Theta_i
            if(DefaultSetting.IsEmptyReposition){
                for(int k = 0; k < od.getNumberOfEmptyPath(); ++k)
                {
                    int j = od.getEmptyPathIndexes()[k];
                     // z：重定向普通空箱
                    if(xs.containsKey("z")){
                        Obj.addTerm(p.getEmptyPathCost()[j], zVar.get(i)[k]);
                    }
                }                
            }
        }

        return Obj;
    }


    protected IloLinearNumExpr GetRequestTransCostObj(
                                                        IloLinearNumExpr Obj,
                                                        List<IloNumVar[]> xVar, 
                                                        List<IloNumVar[]> yVar,
                                                        List<IloNumVar[]> zVar, 
                                                        IloNumVar[] gVar)
            throws IloException{
        // i \in I
        for(int i = 0; i < p.getDemand().length; ++i){
            // item2 : Penalty Cost of unsatisfied Demand
            Obj.addTerm(p.getPenaltyCostForDemand()[i], gVar[i]);

            Request od = in.getRequestSet().get(i);

            // \phi \in \\Phi_i
            for(int k = 0; k < od.getNumberOfLadenPath(); ++k) {
                int j = od.getLadenPathIndexes()[k];
                // item3 : Demurrage of self-owned and leased containers and Rental cost on laden paths
                Obj.addTerm(p.getLadenPathCost()[j], xVar.get(i)[k]);
                Obj.addTerm(p.getLadenPathCost()[j], yVar.get(i)[k]);
                Obj.addTerm(p.getRentalCost() * p.getTravelTimeOnPath()[j], yVar.get(i)[k]);
            }

            // \theta \in \\Theta_i
            for(int k = 0; k < od.getNumberOfEmptyPath(); ++k)
            {
                int j = od.getEmptyPathIndexes()[k];
                Obj.addTerm(p.getEmptyPathCost()[j], zVar.get(i)[k]);
            }
        }

        return Obj;
    }
    protected IloLinearNumExpr GetRequestTransCostObj(IloLinearNumExpr Obj) throws IloException{
        // return GetRequestTransCostObj(Obj, xVar, yVar, zVar, gVar);
        return GetRequestTransCostObj(Obj, xs, gVar);
    }


    public void setInitialSolution(int[][] vVarValue) throws IloException {
        int m = vVar.length;
        int n = vVar[0].length;
        IloNumVar[] startVar = new IloNumVar[m * n];
        double[] startVal = new double[m * n];
        for (int i = 0, idx = 0; i < m; ++i)
            for (int j = 0; j < n; ++j) {
                startVar[idx] = vVar[i][j];
                startVal[idx] = vVarValue[i][j];
                ++idx;
            }
        cplex.addMIPStart(startVar, startVal);
    }
    protected void writeSolution(FileWriter fileWriter){
        try {
            fileWriter.write("VesselType Solution:\t");
            for (int r = 0; r < getSolution().length; r++) {
                if(r!=0){
                    fileWriter.write(",");
                }
                fileWriter.write(getSolution()[r]);
            }
            fileWriter.write("\n");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
    private void setHomoVesselSolution() throws IloException {
        int[][]  vvv =new int [p.getVesselSet().length][p.getShippingRouteSet().length];
        int[] solution = new int[p.getShippingRouteSet().length];
        for (int r = 0; r < p.getShippingRouteSet().length; ++r) {
            for (int h = 0; h < p.getVesselSet().length; h++) {
                double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
                if(cplex.getValue(vVar[h][r]) >= 1 - tolerance){
                    vvv[h][r]= 1;
                    solution[r] = h + 1;
                }
            }
        }
        setVVarValue(vvv);
        setSolution(solution);
    }
    private void setHeteroVesselSolution() throws IloException {
        int[][] vvv =new int [p.getVesselSet().length][p.getVesselPathSet().length];
        int[] solution = new int[p.getVesselPathSet().length];
        for(int w=0; w<p.getVesselPathSet().length; ++w) {
            for (int h = 0; h < p.getVesselSet().length; h++) {
                double tolerance = cplex.getParam(IloCplex.Param.MIP.Tolerances.Integrality);
                if(cplex.getValue(vVar[h][w]) >= 1 - tolerance){
                    vvv[h][w]= 1;
                    solution[w] = h + 1;
                }
            }
        }
        setVVarValue(vvv);
        setSolution(solution);
    }
    protected void setVVarsSolution() throws IloException {
        if(DefaultSetting.FleetType.equals("Homo")){
            setHomoVesselSolution();
        } else if (DefaultSetting.FleetType.equals("Hetero")) {
            setHeteroVesselSolution();
        }
        else{
            log.info("Error in Fleet type!");
        }
    }
    protected double calculateSampleMeanPerformance(int[][] vValue) throws IOException, IloException {
        String filename = model + "-R"+ in.getShipRouteSet().size()
                + "-T" + p.getTimeHorizon() + "-"+ DefaultSetting.FleetType
                + "-Tau" + p.getTau()
                + "-U" + p.getUncertainDegree()
                + "-S" + DefaultSetting.randomSeed
                + "-SampleTestResult"+ ".txt";
        File file = new File(DefaultSetting.RootPath + DefaultSetting.AlgoLogPath + filename);
        if (!file.exists()) {
            try {
                file.createNewFile();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }

        FileWriter filewriter = new FileWriter(file, false);
        filewriter.write("Sample\tOperationCost\t " +
                "TotalTransCost\t LadenCost\t " +
                "EmptyCost\t RentalCost\t " +
                "PenaltyCost\tTotalCost\n");
        filewriter.flush();

        double mp_operation_cost = getOperationCost(vValue);


        double[] sample_sub_opera_costs = new double[DefaultSetting.numSampleScenes];
        double[] sample_laden_costs = new double[DefaultSetting.numSampleScenes];
        double[] sample_empty_costs = new double[DefaultSetting.numSampleScenes];
        double[] sample_rental_costs = new double[DefaultSetting.numSampleScenes];
        double[] sample_penalty_costs = new double[DefaultSetting.numSampleScenes];

        double sum_sub_opera_costs = 0;
        double worst_total_cost = 0;
        double worst_second_cost = 0;
        SubProblem sp = new SubProblem(in, p, vValue);
        for (int sce = 0; sce < DefaultSetting.numSampleScenes; sce++) {
            sp.changeDemandConstraintCoefficients(p.getSampleScenes()[sce]);
            sp.solveModel();

            sample_sub_opera_costs[sce] = sp.getTotalCost();
            sample_laden_costs[sce] = sp.getLadenCost();
            sample_empty_costs[sce] = sp.getEmptyCost();
            sample_rental_costs[sce] = sp.getRentalCost();
            sample_penalty_costs[sce] = sp.getPenaltyCost();

            sum_sub_opera_costs += sp.getTotalCost();
            if((mp_operation_cost + sample_sub_opera_costs[sce]) > worst_total_cost){
                worst_total_cost = mp_operation_cost + sample_sub_opera_costs[sce];
                worst_second_cost = sample_sub_opera_costs[sce];
            }

            DefaultSetting.drawProgressBar((sce) * 100 / DefaultSetting.numSampleScenes);

            filewriter.write(sce + "\t" + mp_operation_cost + "\t"
                    + sample_sub_opera_costs[sce] + "\t"
                    + sample_laden_costs[sce] + "\t"
                    + sample_empty_costs[sce] + "\t"
                    + sample_rental_costs[sce] + "\t"
                    + sample_penalty_costs[sce] + "\t"
                    + (mp_operation_cost + sample_sub_opera_costs[sce])
                    + "\n");
            filewriter.flush();
        }
        this.setWorstPerformance(worst_total_cost);
        this.setWorstSecondStageCost(worst_second_cost);
        this.setMeanPerformance(mp_operation_cost + sum_sub_opera_costs / DefaultSetting.numSampleScenes);
        this.setMeanSecondStageCost(sum_sub_opera_costs / DefaultSetting.numSampleScenes);

        filewriter.close();

        return mp_operation_cost + sum_sub_opera_costs/ DefaultSetting.numSampleScenes;
    }
    protected double calculateMeanPerformance() throws IOException, IloException {
        log.info("Calculating Mean Performance ...");
        if(DefaultSetting.UseHistorySolution)
        {
            if((in.getHistorySolutionSet().get(modelName) != (null))) {
                calculateSampleMeanPerformance(solutionToVValue(in.getHistorySolutionSet().get(modelName)));
            }
        }else {
            calculateSampleMeanPerformance(this.getVVarValue());
        }
        log.info("MeanPerformance = " + getMeanPerformance());
        log.info("WorstPerformance = "+ getWorstPerformance());
        log.info("WorstSecondStageCost = " + getWorstSecondStageCost());
        log.info("MeanSecondStageCost = " + getMeanSecondStageCost());
        log.info("AlgoObjVal = "+ getObjVal());
        return meanPerformance;
    }
    public int[][] solutionToVValue(int[] solution){
        int[][] vValue = new int[0][];
        if(DefaultSetting.FleetType.equals("Homo")){
            vValue = new int[p.getVesselSet().length][p.getShippingRouteSet().length];
            for(int r = 0; r<p.getShippingRouteSet().length; r++) {
                vValue[solution[r] - 1][r] = 1;
            }
        } else if (DefaultSetting.FleetType.equals("Hetero")) {
            vValue = new int[p.getVesselSet().length][p.getVesselPathSet().length];
            for(int w=0;w<p.getVesselPathSet().length;++w) {
                vValue[solution[w]-1][w] = 1;
            }
        }
        else{
            log.info("Error in Fleet type!");
        }

        return vValue;
    }
    protected  void printSolution(){
        log.info("Objective ="+String.format("%.2f", getObjVal()));
        System.out.print("Objective ="+String.format("%.2f", getObjVal()));
        System.out.print("VesselType Decision vVar : ");
        for(int r = 0; r<p.getShippingRouteSet().length; r++) {
            System.out.print(p.getShippingRouteSet()[r]);
            System.out.print(":");

            if(DefaultSetting.FleetType.equals("Homo")){
                for(int h=0;h<p.getVesselSet().length;++h)
                {
                    if(vVarValue[h][r] != 0)
                    {
                        System.out.print(p.getVesselSet()[h]+"\t");
                    }
                }
            } else if (DefaultSetting.FleetType.equals("Hetero")) {
                for(int w=0;w<p.getVesselPathSet().length;++w){
                    if (p.getShipRouteAndVesselPath()[r][w] != 1)
                    {
                        continue;
                    }
                    for(int h=0;h<p.getVesselSet().length;++h)
                    {
                        if(vVarValue[h][w] != 0 && p.getShipRouteAndVesselPath()[r][w] == 1)
                        {
                            System.out.print(p.getVesselPathSet()[w]+"(" + p.getVesselSet()[h]+")\t");
                        }
                    }
                }
            }
            else{
                log.info("Error in Fleet type!");
            }
        }
    }
}

