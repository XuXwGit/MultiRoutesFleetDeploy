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
 * @Author: XuXw
 * @Description: Todo
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

    protected void frame() throws IOException, IloException {
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
