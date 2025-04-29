package multi.algos;

import ilog.concert.IloException;
import lombok.Getter;
import lombok.Setter;
import lombok.extern.slf4j.Slf4j;
import multi.DefaultSetting;
import multi.InputData;
import multi.Parameter;

import java.io.FileWriter;
import java.io.IOException;

/**
 * 算法框架基类
 *
 * 定义算法执行的通用框架和流程
 *
 * 主要功能:
 * 1. 维护上下界(upperBound/lowerBound)
 * 2. 记录迭代过程(upper/lower数组)
 * 3. 提供算法执行的基本框架(frame方法)
 * 4. 记录算法性能指标(gap/obj/solveTime等)
 *
 * 子类需要实现具体的算法逻辑
 *
 * @Author: XuXw
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
@Getter
@Setter

public class BaseAlgoFrame extends DefaultSetting {
    protected InputData in;
    protected Parameter p;
    private double gap;
    private double obj;
    private double solveTime;
    private int iter;
    protected int iteration=0;

    public BaseAlgoFrame() {
    }
    protected double [] upper =new double [maxIterationNum+1];
    protected double [] lower =new double [maxIterationNum+1];

    protected double upperBound = Long.MAX_VALUE;
    protected double lowerBound = Long.MIN_VALUE;

    /**
     * 算法框架主方法
     *
     * 定义算法的基本执行流程:
     * 1. 初始化算法参数
     * 2. 主循环迭代直到收敛:
     *    a. 求解主问题(获取上界)
     *    b. 求解子问题(获取下界)
     *    c. 检查收敛条件
     *    d. 更新割平面(如Benders分解)
     * 3. 输出最终结果
     *
     * 子类需要实现具体的算法逻辑
     *
     * @throws IOException
     * @throws IloException
     */
    protected void frame() throws IOException, IloException {
        // 由子类实现具体算法逻辑
    }

    protected void printIterTitle(FileWriter fileWriter, double bulidModelTime) throws IOException {
        if(WhetherPrintProcess || WhetherPrintIteration){
            log.info("BuildModelTime = "+String.format("%.2f", bulidModelTime));
            log.info("k"+"\t\t"
                    +"LB"+"\t\t"
                    +"UB"+"\t\t"
                    +"Total Time"+"\t\t"
            );
        }

        if(WhetherWriteFileLog){
            fileWriter.write("k"+"\t\t"
                    +"LB"+"\t\t"
                    +"UB"+"\t\t"
                    +"Total Time(s)"+"\t\t"
            );
            fileWriter.write("\n");
            fileWriter.flush();
        }
    }

    protected void printIteration(FileWriter fileWriter, double lb, double ub, double totalTime) throws IOException {
        if(WhetherPrintProcess || WhetherPrintIteration){
            log.info(iteration+"\t\t"
                    +String.format("%.2f", lb)+"\t\t"
                    +String.format("%.2f", ub)+"\t\t"
                    +String.format("%.2f", totalTime)+"\t\t"
            );
        }
        if(WhetherWriteFileLog){
            fileWriter.write(iteration+"\t\t"
                    +String.format("%.2f", lb) +"\t\t"
                    +String.format("%.2f", ub)+"\t\t"
                    +String.format("%.2f", totalTime)+"\t\t"
            );
            fileWriter.write("\n");
            fileWriter.flush();
        }
    }

    protected void printIteration(FileWriter fileWriter, double lb, double ub, double mpTime, double spTime, double totalTime) throws IOException {
        if(WhetherPrintProcess || WhetherPrintIteration){
            log.info(iteration+"\t\t"
                    +String.format("%.2f", lb)+"\t\t"
                    +String.format("%.2f", ub)+"\t\t"
                    +String.format("%.2f", mpTime)+"\t\t"
                    +String.format("%.2f", spTime)+"\t\t"
                    +String.format("%.2f", totalTime)+"\t\t"
            );
        }
        if(WhetherWriteFileLog){
            fileWriter.write(iteration+"\t\t"
                    +String.format("%.2f", lb) +"\t\t"
                    +String.format("%.2f", ub)+"\t\t"
                    +String.format("%.2f", mpTime)+"\t\t"
                    +String.format("%.2f", spTime)+"\t\t"
                    +String.format("%.2f", totalTime)+"\t\t"
            );
            fileWriter.write("\n");
            fileWriter.flush();
        }
    }

    public double getObjVal() {
        return obj;
    }
}
