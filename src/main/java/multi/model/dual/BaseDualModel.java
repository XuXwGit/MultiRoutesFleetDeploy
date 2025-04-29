package multi.model.dual;

import ilog.concert.*;
import ilog.cplex.IloCplex;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.model.BaseModel;
import multi.network.Request;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;

/**
 * @author XuXw
 * @time 2024/12/01 15:00
 * @description: 对偶问题模型实现类，对应tex中的DSP模型
 * 数学模型：
 * 目标函数: max ∑(f_i + u_i*f_i^hat)*α_i + ∑(capacity*V_hr)*β_nn' - ∑(l_p0)*γ_pt
 * 约束条件:
 * 1. α_i + ∑μ_nn'φ*β_nn' + ... ≤ c4φ (对应X_iφ约束)
 * 2. α_i + ∑μ_nn'φ*β_nn' ≤ c3*gφ + c4φ (对应Y_iφ约束)
 * 3. ∑ξ_nn'θ*β_nn' + ... ≤ c5θ (对应Z_iθ约束)
 * 4. α_i ≤ c2i (对应G_i约束)
 */
@Slf4j
@Getter
@Setter
public class BaseDualModel extends BaseModel {
    protected int tau;
    protected IloLinearNumExpr objExpr;
    public BaseDualModel(InputData in, int tau, Parameter p) {
        super();
        this.tau = tau;
        this.in = in;
        this.p = p;
        try {
            cplex = new IloCplex();
            publicSetting(cplex);
            // create basic decision and add basic constraints
            frame();
        } catch (IloException e) {
            throw new RuntimeException(e);
        }
    }

    public BaseDualModel() {
    }

    private Scenario scene;
    protected void setScene(Scenario scene) {
        this.scene = scene;
    }
    public Scenario getScene()	{
        return scene;
    }

    // cplex model/variables/objective
    protected IloNumVar[] alphaVar;
    protected IloNumVar[] betaVar;
    protected IloNumVar[][] gammaVar;
    protected IloNumVar[][] gamma2Var;

    protected IloObjective objective;
    // x - c1
    private List<IloRange[]> c1;
    // x1 - c12
    private List<IloRange[]> c12;
    // y - c2
    private List<IloRange[]> c2;
    // z - c3
    private List<IloRange[]> c3;
    // z2 - c32
    private List<IloRange[]> c32;
    // g - c4
    private IloRange[] c4;

    // create basic decision and add basic constraints
    protected void setDualDecisionVars() throws IloException {
        // 创建对偶变量
        // α[i] ∈ (-∞, c2i] 对应tex中的α_i ≤ c2i
        // β[nn'] ∈ (-∞, 0] 对应tex中的β_nn' ≤ 0
        // γ[p][t] ∈ [0, +∞) 对应tex中的γ_pt ≥ 0
        alphaVar =new IloNumVar [p.getDemand().length];
        betaVar =new IloNumVar [p.getTravelingArcsSet().length];
        gammaVar=new IloNumVar[p.getPortSet().length][p.getTimePointSet().length];
        gamma2Var=new IloNumVar[p.getPortSet().length][p.getTimePointSet().length];

        String varName;
        for(int i=0;i<p.getDemand().length;i++)
        {
            varName = "alpha(" + i +")";
            alphaVar[i]=cplex.numVar(Integer.MIN_VALUE, p.getPenaltyCostForDemand()[i], varName);
      }

        for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++)
        {
            // beta <= 0
            varName = "beta(" + nn +")";
            betaVar[nn]=cplex.numVar(Integer.MIN_VALUE,0, varName);
        }

        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            for(int t=1;t<p.getTimePointSet().length;t++)
            {
                // gamma >= 0
                varName = "gamma(" + pp +")(" + t + ")";
                gammaVar[pp][t]=cplex.numVar(0,Integer.MAX_VALUE, varName);
                if(DefaultSetting.AllowFoldableContainer){
                    varName = "gamma2(" + pp +")(" + t + ")";
                    gamma2Var[pp][t]=cplex.numVar(0,Integer.MAX_VALUE, varName);
                }
            }
        }
    }

    protected IloLinearNumExpr getObjExpr(int[][] vValue, double[] uValue) throws IloException {
        objExpr = getDetermineObj(vValue);
        // variable objective function
        for(int i=0;i<p.getDemand().length;i++){
            objExpr.addTerm(p.getMaximumDemandVariation()[i] * uValue[i], alphaVar[i]);
        }

        return objExpr;
    }
    protected IloLinearNumExpr getObjExpr(int[][] vValue, int[] uValue) throws IloException {
        double[] uValueDouble = IntArrayWrapper.IntArrayToDoubleArray(uValue);
        return getObjExpr(vValue, uValueDouble);
    }
    protected IloLinearNumExpr getDetermineObj(int[][] vVarValue) throws IloException {
        double[][] vVarValueDouble = IntArray2DWrapper.Int2DArrayToDouble2DArray(vVarValue);
        return getDetermineObj(vVarValueDouble);
    }
    protected IloLinearNumExpr getDetermineObj(double[][] vVarValue) throws IloException {
        IloLinearNumExpr objExpr = cplex.linearNumExpr();

        // I.part one : sum(normal_demand * alpha) = sum(normal_demand * alpha)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            objExpr.addTerm(p.getDemand()[i], alphaVar[i]);
        }

        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        double[] capacitys = getCapacityOnArcs(vVarValue);
        for(int n = 0; n<p.getTravelingArcsSet().length; n++)
        {
            objExpr.addTerm(capacitys[n], betaVar[n]);
        }

        // III. part three:
        // p∈P
        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            //t∈ T
            for(int t=1; t<p.getTimePointSet().length; t++)
            {
                objExpr.addTerm(-p.getInitialEmptyContainer()[pp], gammaVar[pp][t]);
                if(DefaultSetting.AllowFoldableContainer){
                    objExpr.addTerm(-p.getInitialEmptyContainer()[pp] * 0.5, gamma2Var[pp][t]);
                }
            }
        }
        return objExpr;
    }
    /**
     * 设置自有集装箱运输路径的对偶约束(对应数学模型中的X_iφ约束)
     *
     * 数学表达式:
     * α_i + ∑_{<n,n'>∈A'} μ_{nn'φ} β_{nn'}
     * + ∑_{t∈T} [∑_{p=d(i)} γ_{pt} ∑_{<n,n'>∈A':p(n')=p,1≤t(n')≤t-s_p} μ_{nn'φ}
     * - ∑_{p=o(i)} γ_{pt} ∑_{<n,n'>∈A':p(n)=p,1≤t(n)≤t} μ_{nn'φ}] ≤ c_{4φ}
     *
     * 其中:
     * α_i: 需求i的对偶变量
     * β_{nn'}: 弧<n,n'>的对偶变量
     * γ_{pt}: 港口p在时间t的对偶变量
     * μ_{nn'φ}: 路径φ是否包含弧<n,n'>的指示变量
     * c_{4φ}: 路径φ的运营成本
     *
     * 代码变量对应:
     * alphaVar[i] ↔ α_i
     * betaVar[nn] ↔ β_{nn'}
     * gammaVar[pp][t] ↔ γ_{pt}
     * p.getArcAndPath()[nn][j] ↔ μ_{nn'φ}
     * p.getLadenPathCost()[j] ↔ c_{4φ}
     *
     * @throws IloException
     */
    protected void setDualConstraintX() throws IloException {
        c1 = new ArrayList<>();
        c12 = new ArrayList<>();
        //  ∀i∈I (遍历所有需求)
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            Request od = in.getRequestSet().get(i);
            IloRange[] c1K = new IloRange[od.getNumberOfLadenPath()];
            c1.add(c1K);
            if(DefaultSetting.AllowFoldableContainer){
                IloRange[] c12K = new IloRange[od.getNumberOfLadenPath()];
                c12.add(c12K);
            }

            for(int k=0; k< od.getNumberOfLadenPath(); k++){
                int j = od.getLadenPathIndexes()[k];

                IloLinearNumExpr left = cplex.linearNumExpr();
                IloLinearNumExpr left2 = cplex.linearNumExpr();

                // first item :
                left.addTerm(1, alphaVar[i]);
                left2.addTerm(1, alphaVar[i]);

                // second item :
                // <n,n'> ∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                    left.addTerm(p.getArcAndPath()[nn][j], betaVar[nn]);
                    left2.addTerm(p.getArcAndPath()[nn][j], betaVar[nn]);
                }

                IloLinearNumExpr third = cplex.linearNumExpr();
                // third item :
                // t∈T
                for(int t=1;t<p.getTimePointSet().length;t++) {
                    // p ∈P
                    for(int pp=0; pp<p.getPortSet().length; pp++) {
                        // p == d(i)
                        if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i])){
                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
                                // p(n') == p
                                // 1 <= t(n') <= t - sp
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() <= t - p.getTurnOverTime()[pp]
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() >= 1) {
                                    third.addTerm(p.getArcAndPath()[nn][j], gammaVar[pp][t]);
                                }
                            }
                        }

                        // p == o(i)
                        else if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                        {
                            // <n,n'>∈A'
                            for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
                                // p(n) == p
                                // 1 <= t(n) <= t
                                if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                                {
                                    third.addTerm(-p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                }
                            }
                        }
                    }
                }
                left.add(third);
                left2.add(third);

                String constrName = "C-X_"+(i) + "_" + (k); // 约束名称格式:C-X_需求索引_路径索引
                // 添加约束: α_i + ∑β + ∑γ ≤ c_{4φ}
                c1.get(i)[k] = cplex.addLe(left,p.getLadenPathCost()[j], constrName);
                if(DefaultSetting.AllowFoldableContainer){
                    c12.get(i)[k] = cplex.addLe(left2,p.getLadenPathCost()[j], constrName);
                }
            }
        }
    }

    protected void setDualConstraintY() throws IloException {
        c2 = new ArrayList<>();
        // ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            Request od = in.getRequestSet().get(i);
            IloRange[] c2K = new IloRange[od.getNumberOfLadenPath()];
            c2.add(c2K);

            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfLadenPath(); k++){
                int j = in.getRequestSet().get(i).getLadenPathIndexes()[k];

                IloLinearNumExpr left=cplex.linearNumExpr();

                // item1:
                left.addTerm(1,alphaVar[i]);

                // <n,n'>∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
                    // item2:
                    left.addTerm(p.getArcAndPath()[nn][j], betaVar[nn]);
                }

                // left <= c3 * g(φ) + c4φ
                String constrName = "C-Y_"+(i)+"_"+(k);
                //log.info("Add Constraint : "+constrName);
                c2.get(i)[k] = cplex.addLe(left,p.getRentalCost()*p.getTravelTimeOnPath()[j]+p.getLadenPathCost()[j]
                        , constrName);
            }
        }
    }

    protected void setDualConstraintZ() throws IloException {
        // 添加Z_iθ约束: ∑ξ_nn'θ*β_nn' + ∑(γ_pt相关项) ≤ c5θ
        // 对应tex中的Z_iθ约束
        if(WhetherUseMultiThreads){
           // long start = System.currentTimeMillis();
            setDualConstraintZwithMultiThreads();
            //log.info("            Set DualConstraintZ Time(Multi Threads) = "+ (System.currentTimeMillis() - start));
        } else {
            //long start = System.currentTimeMillis();
            setDualConstraintZwithSingleThread();
            //log.info("            Set DualConstraintZ Time = "+ (System.currentTimeMillis() - start));
        }
    }
    protected void setDualConstraintZwithSingleThread() throws IloException {
        c3 = new ArrayList<>();
        c32 = new ArrayList<>();
        // i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            Request od = in.getRequestSet().get(i);

            if(!DefaultSetting.IsEmptyReposition){
                IloRange[] c3K = new IloRange[od.getNumberOfLadenPath()];
                c3.add(c3K);
                IloRange[] c32K = new IloRange[od.getNumberOfLadenPath()];
                c32.add(c32K);

                //  θ∈Θi
                for(int k = 0; k<od.getNumberOfLadenPath(); k++) {
                    int j = od.getLadenPathIndexes()[k];

                    IloLinearNumExpr left = cplex.linearNumExpr();
                    IloLinearNumExpr left2 = cplex.linearNumExpr();

                    // <n,n'>∈A'
                    for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                        // add item1:
                        left.addTerm(p.getArcAndPath()[nn][j],betaVar[nn]);
                        left2.addTerm(p.getArcAndPath()[nn][j] * 0.25,betaVar[nn]);

                        // t∈T
                        for(int t=1;t<p.getTimePointSet().length;t++) {
                            // p∈P
                            for(int pp=0;pp<p.getPortSet().length;pp++)
                            {
                                // p == d(i)
                                if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i]))
                                {
                                    // add item2:
                                    //p(n') == p
                                    // 1<=t(n')<= t
                                    if(in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            &&in.getTravelingArcSet().get(nn).getDestinationTime()<=t
                                            &&in.getTravelingArcSet().get(nn).getDestinationTime()>=1)
                                    {
                                        left.addTerm(p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                        left2.addTerm(p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                    }
                                }

                                // p == o(i)
                                if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                                {
                                    // add item3:
                                    // p(n) == p
                                    // 1<= t(n)<=t
                                    if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                            &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                            &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                                    {
                                        left.addTerm(-p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                        left2.addTerm(-p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                    }
                                }
                            }
                        }
                    }

                    // left <= c5θ
                    String constrName = "C-Z_" + (i) +"-"+(k);
                    c3.get(i)[k] = cplex.addLe(left, p.getLadenPathCost()[j], constrName);
                    c32.get(i)[k] = cplex.addLe(left2, p.getLadenPathCost()[j], constrName);
                }
            }
            else{
                IloRange[] c3K = new IloRange[od.getNumberOfEmptyPath()];
                c3.add(c3K);

                //  θ∈Θi
                for(int k = 0; k<od.getNumberOfEmptyPath(); k++) {
                    int j = od.getEmptyPathIndexes()[k];

                    IloLinearNumExpr left = cplex.linearNumExpr();

                    // <n,n'>∈A'
                    for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                        // add item1:
                        left.addTerm(p.getArcAndPath()[nn][j],betaVar[nn]);

                        // t∈T
                        for(int t=1;t<p.getTimePointSet().length;t++) {
                            // p∈P
                            for(int pp=0;pp<p.getPortSet().length;pp++)
                            {
                                // p == o(i)
                                if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                                {
                                    // add item2:
                                    //p(n') == p
                                    // 1<=t(n')<= t
                                    if(in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                            &&in.getTravelingArcSet().get(nn).getDestinationTime()<=t
                                            &&in.getTravelingArcSet().get(nn).getDestinationTime()>=1)
                                    {
                                        left.addTerm(p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                    }
                                }

                                // p
                                // add item3:
                                // p(n) == p
                                // 1<= t(n)<=t
                                if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                                {
                                    left.addTerm(-p.getArcAndPath()[nn][j],gammaVar[pp][t]);
                                }
                            }
                        }

                    }

                    // left <= c5θ
                    String constrName = "C-Z_" + (i) +"-"+(k);
                    c3.get(i)[k] = cplex.addLe(left, p.getEmptyPathCost()[j], constrName);
                }
            }
        }
    }
    protected void setDualConstraintZwithMultiThreads() throws IloException {
        c3 = new ArrayList<>();
        // i∈I
        for(int i=0;i<p.getDemand().length;i++) {
            Request od = in.getRequestSet().get(i);
            IloRange[] c3K = new IloRange[od.getNumberOfEmptyPath()];
            c3.add(c3K);
        }

        Map<Integer, IloNumExpr[]> leftIterms = new HashMap<>();

        //创建工作队列，用于存放提交的等待执行任务
        BlockingQueue<Runnable> workQueue = new LinkedBlockingQueue<>();
        //创建线程池，线程池中线程的数量为3，允许的最大线程数量为5
        //核心线程数
        int corePoolSize = 3;
        //最大线程数
        int maximumPoolSize = 6;
        //超过 corePoolSize 线程数量的线程最大空闲时间
        long keepAliveTime = 2;
        //以秒为时间单位
        TimeUnit unit = TimeUnit.SECONDS;
        ThreadPoolExecutor threadPoolExecutor = null;
        try{
            //创建线程池
            threadPoolExecutor = new ThreadPoolExecutor(corePoolSize,
                    maximumPoolSize,
                    keepAliveTime,
                    unit,
                    workQueue,
                    new ThreadPoolExecutor.AbortPolicy());

            // i∈I
            for(int index=0;index<p.getDemand().length;index++)
            {
                int i = index;
                //// parallel
                threadPoolExecutor.submit(() -> {
                    Request od = in.getRequestSet().get(i);
                    IloNumExpr[] lefts = new IloNumExpr[od.getNumberOfEmptyPath()];
                    //  θ∈Θi
                    for (int k1 = 0; k1 < od.getNumberOfEmptyPath(); k1++) {
                        int j = od.getEmptyPathIndexes()[k1];

                        IloLinearNumExpr left;
                        try {
                            left = cplex.linearNumExpr();
                        } catch (IloException e) {
                            throw new RuntimeException(e);
                        }

                        // <n,n'>∈A'
                        for (int n = 0; n < p.getTravelingArcsSet().length; n++) {
                            // add item1:
                            try {
                                left.addTerm(p.getArcAndPath()[n][j], betaVar[n]);
                            } catch (IloException e) {
                                throw new RuntimeException(e);
                            }

                            // t∈T
                            for(int t=1;t<p.getTimePointSet().length;t++) {
                                // p∈P
                                for(int pp=0;pp<p.getPortSet().length;pp++)
                                {
                                    // p == o(i)
                                    if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                                    {
                                        // add item2:
                                        //p(n') == p
                                        // 1<=t(n')<= t
                                        if(in.getTravelingArcSet().get(n).getDestinationPort().equals(p.getPortSet()[pp])
                                                &&in.getTravelingArcSet().get(n).getDestinationTime()<=t
                                                &&in.getTravelingArcSet().get(n).getDestinationTime()>=1)
                                        {
                                            try {
                                                left.addTerm(p.getArcAndPath()[n][j],gammaVar[pp][t]);
                                            } catch (IloException e) {
                                                throw new RuntimeException(e);
                                            }
                                        }
                                    }

                                    // p
                                    // add item3:
                                    // p(n) == p
                                    // 1<= t(n)<=t
                                    if(in.getTravelingArcSet().get(n).getOriginPort().equals(p.getPortSet()[pp])
                                            &&in.getTravelingArcSet().get(n).getOriginTime()<=t
                                            &&in.getTravelingArcSet().get(n).getOriginTime()>=1)
                                    {
                                        try {
                                            left.addTerm(-p.getArcAndPath()[n][j],gammaVar[pp][t]);
                                        } catch (IloException e) {
                                            throw new RuntimeException(e);
                                        }
                                    }
                                }
                            }
                        }

                        lefts[k1] = left;
                    }
                    leftIterms.put(i, lefts);
                });
            }
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            threadPoolExecutor.shutdown();
        }

        for(int i=0;i<p.getDemand().length;i++)
        {
            Request od = in.getRequestSet().get(i);
            for(int k = 0; k<od.getNumberOfEmptyPath(); k++)
            {
                int j = od.getEmptyPathIndexes()[k];
                // left <= c5θ
                String constrName = "C-Z_" + (i) +"-"+(k);

                c3.get(i)[k] = cplex.addLe(leftIterms.get(i)[k], p.getEmptyPathCost()[j], constrName);
            }
        }
    }




    protected void setDualConstraintG() throws IloException {
        // 添加G_i约束: α_i ≤ c2i (对偶变量α_i的上界约束)
        // 对应tex中的G_i约束
        c4 = new IloRange[p.getDemand().length];
        for (int i = 0; i < p.getDemand().length; i++) {
            // alpha <= c2 (α_i ≤ c2i)
            String constrName = "C-Z_" + (i) ;
            c4[i] = cplex.addLe(alphaVar[i], p.getPenaltyCostForDemand()[i], constrName);
        }
    }
    public void changeObjectiveVvarsCoefficients(double[][] vValue) throws IloException	{
        this.vVarValueDouble = vValue;
        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        double[] capacitys = getCapacityOnArcs(vValue);
        for(int n = 0; n<p.getTravelingArcsSet().length; n++)
        {
            cplex.setLinearCoef(objective, capacitys[n], betaVar[n]);
        }
    }
    public void changeObjectiveVvarsCoefficients(int[][] vValue) throws IloException	{
        this.vVarValue = vValue;
        this.vVarValueDouble = IntArray2DWrapper.Int2DArrayToDouble2DArray(vValue);
        double[][] vValueDouble2D = IntArray2DWrapper.Int2DArrayToDouble2DArray(vValue);
        changeObjectiveVvarsCoefficients(vValueDouble2D);
    }
    public void changeObjectiveUvarsCoefficients(double[] uValue) throws IloException {
        this.uValue = uValue;
        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++){
            cplex.setLinearCoef(objective
                    ,p.getDemand()[i] + p.getMaximumDemandVariation()[i] * this.uValue[i]
                    , alphaVar[i]);
        }
    }
    public void changeObjectiveUvarsCoefficients(int[] uValue) throws IloException {
        this.uValue = IntArrayWrapper.IntArrayToDoubleArray(uValue);
        changeObjectiveUvarsCoefficients(this.uValue);
    }
    public void changeObjectiveCoefficients(int[][] vValue, double[] uValue) throws IloException {
        this.vVarValue = vValue;
        this.uValue = uValue;

        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        changeObjectiveUvarsCoefficients(uValue);

        // II. sum (vessel capacity * V[h][r] * beta[arc])
        // V[h][r] : the solution come from the master problem (the only changeable input param in dual sub model)
        // <n,n'> ∈ A'
        changeObjectiveVvarsCoefficients(vValue);
    }
    protected double getConstantItem() throws IloException {
        double constantItem = 0;

        // I.part one : sum(normal_demand * alpha + max_var_demand*u*alpha) = sum(normal_demand * alpha + max_var_demand * lambda)
        // i ∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            constantItem  += ((p.getDemand()[i] + p.getMaximumDemandVariation()[i] * uValue[i])*cplex.getValue( alphaVar[i]));
        }

        // III. part three:
        // p∈P
        for(int pp=0;pp<p.getPortSet().length;pp++)
        {
            //t∈ T
            for(int t=1; t<p.getTimePointSet().length; t++)
            {
                constantItem  += (-p.getInitialEmptyContainer()[pp] * cplex.getValue(gammaVar[pp][t]));
                if(DefaultSetting.AllowFoldableContainer){
                    constantItem  += (-p.getInitialEmptyContainer()[pp] * cplex.getValue(gamma2Var[pp][t]));
                }
            }
        }
        return constantItem;
    }

    // here constant item is (sub objective - second item)
    // the second item contains the first stage decision V[h][r]
    public IloRange constructOptimalCut(IloCplex cplex, IloIntVar[][] vVars, IloNumVar etaVar) throws IloException {
        IloRange cut = null;

        if (this.cplex.getStatus().equals(IloCplex.Status.Optimal)){
            double constantItem = getConstantItem();
            double[] betaValue = getBetaValue();
            IloLinearNumExpr left = this.cplex.linearNumExpr();
            for(int n = 0; n<p.getTravelingArcsSet().length; n++){
                if(betaValue[n]==0){
                    continue;
                }
                // r ∈R
                for(int w=0; w<p.getVesselPathSet().length; ++w)
                {
                    int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                    // r(w) = r
                    for(int h=0;h<p.getVesselSet().length;++h)
                    {
                        if("Homo".equals(FleetType)){
                            if(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
                                    *p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h] > 0){
                                // vValue[h][r] : come from solution of master problem
                                left.addTerm(p.getArcAndVesselPath()[n][w]*p.getShipRouteAndVesselPath()[r][w]
                                                *p.getVesselTypeAndShipRoute()[h][r]*p.getVesselCapacity()[h]*betaValue[n]
                                        , vVars[h][r]);
                            }
                        } else if ("Hetero".equals(FleetType)) {
                            // vValue[h][w] : come from solution of master problem
                            left.addTerm(p.getArcAndVesselPath()[n][w]
                                            *p.getVesselCapacity()[h]*betaValue[n]
                                    , vVars[h][w]);
                        }
                        else{
                            log.info("Error in Fleet type!");
                        }
                    }
                }
            }
            left.addTerm(-1, etaVar);

            cut = cplex.le(left, -constantItem);
        }

        return cut;
    }

    public double[] getAlphaValue(){
        double[] alphaValue = new double[p.getDemand().length];
        try {
            if(cplex.getStatus() == IloCplex.Status.Optimal){
                for (int i = 0; i < p.getDemand().length; i++){
                    alphaValue[i] = cplex.getValue(alphaVar[i]);
                }
            }
        } catch (IloException e) {
            e.printStackTrace();
        }
        return alphaValue;
    }
    public double[] getBetaValue() throws IloException {
        double[] betaValue = new double[p.getTravelingArcsSet().length];
        if(cplex.getStatus() == IloCplex.Status.Optimal){
            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++){
                betaValue[nn] = cplex.getValue(betaVar[nn]);
            }
        }
        return betaValue;
    }
    public double[][] getGammaValue() {
        double[][] gammaValue = new double[p.getPortSet().length][p.getTimePointSet().length];
        for (int pp = 0; pp < p.getPortSet().length; pp++) {
            for (int t = 1; t < p.getTimePointSet().length; t++) {
                try {
                    gammaValue[pp][t] = cplex.getValue(gammaVar[pp][t]);
                } catch (IloException e) {
                    e.printStackTrace();
                }
            }
        }
        return gammaValue;
    }

/*
    public boolean checkConstraints(double[] alphaValue, double[] betaValue, double[][] gamaValue) throws IloException {
        boolean flag = true;
        if(!checkDualConstraintX(alphaValue, betaValue, gamaValue))
            flag = false;
        if(!checkDualConstraintY(alphaValue, betaValue))
            flag = false;
        if(!checkDualConstraintZ(alphaValue, gamaValue))
            flag = false;
        return flag;
    }
*/

    public boolean checkDualConstraintX(double[] alphaValue, double[] betaValue, double[][] gammaValue) throws IloException {
        boolean flag = true;
        //  ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            Request od = in.getRequestSet().get(i);
            for(int k=0; k< od.getNumberOfLadenPath(); k++){
                int j = od.getLadenPathIndexes()[k];

                double left = 0;

                // first item :
                left += (1 *  alphaValue[i]);

                // second item :
                // <n,n'> ∈A'
                for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++) {
                    left += (p.getArcAndPath()[nn][j] * betaValue[nn]);
                }

                // third item :
                // t∈T
                for(int t=1;t<p.getTimePointSet().length;t++) {
                    // p ∈P
                    for(int pp=0; pp<p.getPortSet().length; pp++) {
                        // p == d(i)
                        if(p.getPortSet()[pp].equals(p.getDestinationOfDemand()[i])){
                            // <n,n'>∈A'
                            for (int nn = 0; nn < p.getTravelingArcsSet().length; nn++) {
                                // p(n') == p
                                // 1 <= t(n') <= t - sp
                                if (in.getTravelingArcSet().get(nn).getDestinationPort().equals(p.getPortSet()[pp])
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() <= t - p.getTurnOverTime()[pp]
                                        && in.getTravelingArcSet().get(nn).getDestinationTime() >= 1) {
                                    left += (p.getArcAndPath()[nn][j] * gammaValue[pp][t]);
                                }
                            }
                        }

                        // p == o(i)
                        if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                        {
                            // <n,n'>∈A'
                            for(int nn = 0; nn<p.getTravelingArcsSet().length; nn++){
                                // p(n) == p
                                // 1 <= t(n) <= t
                                if(in.getTravelingArcSet().get(nn).getOriginPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()<=t
                                        &&in.getTravelingArcSet().get(nn).getOriginTime()>=1)
                                {
                                    left += (-p.getArcAndPath()[nn][j]* gammaValue[pp][t]);
                                }
                            }
                        }
                    }
                }

                String constrName = "C-X_"+(i) + "_" + (k);

                double constraintSlack = cplex.getSlack(c1.get(i)[k]);
                if(constraintSlack < 0){
                    log.info("Cplex: "+constrName+" is violated with " + constraintSlack);
                }

                //log.info("Add Constraint : "+constrName);
                if (left > p.getLadenPathCost()[j]){
                    log.info("Dual Constraint X "+constrName+" is violated!" + "\t\t" + left + "\t\t" + p.getLadenPathCost()[j]);
                    flag = false;
                }
            }
        }

        return flag;
    }
    public boolean checkDualConstraintY(double[] alphaValue, double[] betaValue) throws IloException {
        boolean flag = true;
        // ∀i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            // ∀φ∈Φi
            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfLadenPath(); k++)
            {
                int j = in.getRequestSet().get(i).getLadenPathIndexes()[k];

                double left=0;

                // item1:
                left += (1 * alphaValue[i]);

                // <n,n'>∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++)
                {
                    // item2:
                    left += (p.getArcAndPath()[n][j] * betaValue[n]);
                }

                // left <= c3 * g(φ) + c4φ
                String constrName = "C-Y_"+(i)+"_"+(k);

                double constraintSlack = cplex.getSlack(c2.get(i)[k]);
                if(constraintSlack < 0){
                    log.info("Cplex: "+constrName+" is violated with " + constraintSlack);
                }

                //log.info("Add Constraint : "+constrName);
                if (left  >p.getRentalCost()*p.getTravelTimeOnPath()[j]+
                        p.getLadenPathCost()[j]){
                    log.info("Dual Constraint Y "+constrName+" is violated!" + "\t\t" + left + "\t\t" + p.getRentalCost()*p.getTravelTimeOnPath()[j]+
                            p.getLadenPathCost()[j]);
                    flag = false;
                }
            }
        }

        return flag;
    }
    public boolean checkDualConstraintZ(double[] betaValue, double[][] gamaValue) throws IloException {
        boolean flag = true;
        // i∈I
        for(int i=0;i<p.getDemand().length;i++)
        {
            //  θ∈Θi
            for(int k = 0; k<in.getRequestSet().get(i).getNumberOfEmptyPath(); k++)
            {
                int j = in.getRequestSet().get(i).getEmptyPathIndexes()[k];

                double left = 0;

                // <n,n'>∈A'
                for(int n = 0; n<p.getTravelingArcsSet().length; n++)
                {
                    // add item1:
                    left += (p.getArcAndPath()[n][j] * betaValue[n]);

                    // t∈T
                    for(int t=1;t<p.getTimePointSet().length;t++) {
                        // p∈P
                        for(int pp=0;pp<p.getPortSet().length;pp++)
                        {
                            // p == o(i)
                            if(p.getPortSet()[pp].equals(p.getOriginOfDemand()[i]))
                            {
                                // add item2:
                                //p(n') == p
                                // 1<=t(n')<= t
                                if(in.getTravelingArcSet().get(n).getDestinationPort().equals(p.getPortSet()[pp])
                                        &&in.getTravelingArcSet().get(n).getDestinationTime()<=t
                                        &&in.getTravelingArcSet().get(n).getDestinationTime()>=1)
                                {
                                    left += (p.getArcAndPath()[n][j] * gamaValue[pp][t]);
                                }
                            }

                            // p
                            // add item3:
                            // p(n) == p
                            // 1<= t(n)<=t
                            if(in.getTravelingArcSet().get(n).getOriginPort().equals(p.getPortSet()[pp])
                                    &&in.getTravelingArcSet().get(n).getOriginTime()<=t
                                    &&in.getTravelingArcSet().get(n).getOriginTime()>=1)
                            {
                                left += (-p.getArcAndPath()[n][j] * gamaValue[pp][t]);
                            }
                        }
                    }

                }

                // left <= c5θ
                String constrName = "C-Z_" + (i) +"-"+(k);
                double constraintSlack = cplex.getSlack(c3.get(i)[k]);
                if(constraintSlack < 0){
                    log.info("Cplex: "+constrName+" is violated with " + constraintSlack);
                }

                if(left  > p.getEmptyPathCost()[j]){
                    log.info("Dual Constraint Z "+constrName+" is violated!" + "\t\t" + left + "\t\t" + p.getEmptyPathCost()[j]);
                    flag = false;
                }
            }
        }
        return flag;
    }

}

