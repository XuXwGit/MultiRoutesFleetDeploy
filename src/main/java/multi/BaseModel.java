package multi;

import ilog.concert.IloException;
import ilog.cplex.IloCplex;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.IntArray2DWrapper;
import multi.Parameter;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Slf4j
public class BaseModel  extends DefaultSetting {
    protected InputData in;
    protected Parameter p;
    protected IloCplex cplex;
    protected String Model;
    protected String ModelName;

    public BaseModel(InputData in, Parameter p) {
        super();
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

    protected void publicSetting(IloCplex cplex) throws IloException {
        if(DefaultSetting.WhetherCloseOutputLog)
        {
            cplex.setOut(null);
            cplex.setWarning(null);
        }

        cplex.setParam(IloCplex.Param.WorkMem, MaxWorkMem);
        cplex.setParam(IloCplex.Param.TimeLimit, MIPTimeLimit);
        cplex.setParam(IloCplex.Param.MIP.Tolerances.MIPGap, MIPGapLimit);
        cplex.setParam(IloCplex.Param.Threads, MaxThreads);
    }

    public BaseModel() {
    }

    public void frame() throws IloException{
        //long start = System.currentTimeMillis();
        setDecisionVars();
        //log.info("Set <" + ModelName + "> DecisionVars Time = "+ (System.currentTimeMillis() - start));
        //start = System.currentTimeMillis();
        setObjectives();
        //log.info("Set <" + ModelName + "> Objectives Time = "+ (System.currentTimeMillis() - start));
        //start = System.currentTimeMillis();
        setConstraints();
        //log.info("Set <" + ModelName + "> Constraints Time = "+ (System.currentTimeMillis() - start));
    }

    protected  void setDecisionVars() throws IloException {
    }
    protected  void setConstraints() throws IloException{
    }
    protected  void setObjectives() throws IloException{
    }
    public IloCplex getCplex() {
        return cplex;
    }

    protected double objVal;
    public double getObjVal() {
        return objVal;
    }
    public void setObjVal(double objVal) {
        this.objVal = objVal;
    }

    protected double objGap;
    public double getObjGap() {
        return objGap;
    }
    protected void setObjGap(double objGap) {
        this.objGap = objGap;
    }

    protected double operationCost;
    public double getOperationCost() {
        return operationCost;
    }

    public void setOperationCost(double operationCost) {
        this.operationCost = operationCost;
    }

    protected double solveTime;
    public double getSolveTime() {
        return solveTime;
    }
    protected void setSolveTime(double solveTime) {
        this.solveTime = solveTime;
    }
    public void end()
    {
        cplex.end();
    }
    protected int[][] vVarValue;
    protected double[][] vVarValueDouble;
    public int[][] getVVarValue() {
        return vVarValue;
    }
    public void setVVarValue(int[][] vVarValue) {
        this.vVarValue = vVarValue;
    }
    protected double[] uValue;
    public double[] getUValue() {
        return uValue;
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
    protected double[] getCapacityOnArcs(double[][] vValue){
        double capacitys [] = new double[p.getTravelingArcsSet().length];
        for(int n = 0; n<p.getTravelingArcsSet().length; n++)
        {
            capacitys[n] = 0;
            // r ∈R
            // w∈Ω
            for(int w=0; w<p.getVesselPathSet().length; w++)
            {
                int r = in.getVesselPathSet().get(w).getRouteID() - 1;
                // r(w) = r
                // h \in Hr
                for(int h=0;h<p.getVesselSet().length;h++)
                {
                    if(FleetType.equals("Homo")){
                        // vValue[v][r] : come from solution of master problem
                        capacitys[n] += p.getArcAndVesselPath()[n][w]
                                *p.getShipRouteAndVesselPath()[r][w]
                                *p.getVesselTypeAndShipRoute()[h][r]
                                *p.getVesselCapacity()[h]
                                * vValue[h][r];
                    } else if (FleetType.equals("Hetero")) {
                        // vValue[v][r] : come from solution of master problem
                        capacitys[n] += p.getArcAndVesselPath()[n][w]
                                *p.getVesselCapacity()[h]
                                * vValue[h][w];
                    }
                    else{
                        log.info("Error in Fleet type!");
                    }
                }
            }
        }
        return capacitys;
    }

    protected double[] getCapacityOnArcs(int[][] vValue){
        double[][] vValueDouble = IntArray2DWrapper.Int2DArrayToDouble2DArray(vValue);
        return getCapacityOnArcs(vValueDouble);
    }

    protected void exportModel() throws IloException {
        String modelFilePath = RootPath + ExportModelPath;
        try {
            // 使用Paths.get()方法创建Path对象
            Path path = Paths.get(modelFilePath);

            // 检查路径是否存在，如果不存在则创建文件夹
            if (!Files.exists(path)) {
                // 使用Files.createDirectories()方法创建文件夹，包括所有必需但不存在的父目录
                Files.createDirectories(path);
            }
        } catch (IOException e) {
            // 处理可能的IOException
            e.printStackTrace();
        }
        String filename = ModelName + ".lp";
        cplex.exportModel(modelFilePath+ filename);
    }
}
