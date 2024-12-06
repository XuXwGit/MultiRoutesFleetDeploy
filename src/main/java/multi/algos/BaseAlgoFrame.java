package multi;

import ilog.concert.IloException;
import lombok.extern.slf4j.Slf4j;

import java.io.FileWriter;
import java.io.IOException;

@Slf4j

public class BaseAlgoFrame extends DefaultSetting {
    protected InputData in;
    protected Parameter p;
    public BaseAlgoFrame() {
    }

    protected double upperBound = Long.MAX_VALUE;
    protected double lowerBound = Long.MIN_VALUE;

    public double getUpperBound() {
        return upperBound;
    }
    public void setUpperBound(double upperBound) {
        this.upperBound = upperBound;
    }
    public double getLowerBound() {
        return lowerBound;
    }
    public void setLowerBound(double lowerBound) {
        this.lowerBound = lowerBound;
    }

    protected double [] upper =new double [maxIterationNum+1];
    protected double [] lower =new double [maxIterationNum+1];

    protected int iteration=0;

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

    protected void printIteration(FileWriter fileWriter, double LB, double UB, double total_time) throws IOException {
        if(WhetherPrintProcess || WhetherPrintIteration){
            log.info(iteration+"\t\t"
                    +String.format("%.2f", LB)+"\t\t"
                    +String.format("%.2f", UB)+"\t\t"
                    +String.format("%.2f", total_time)+"\t\t"
            );
        }
        if(WhetherWriteFileLog){
            fileWriter.write(iteration+"\t\t"
                    +String.format("%.2f", LB) +"\t\t"
                    +String.format("%.2f", UB)+"\t\t"
                    +String.format("%.2f", total_time)+"\t\t"
            );
            fileWriter.write("\n");
            fileWriter.flush();
        }
    }

    protected void printIteration(FileWriter fileWriter, double LB, double UB, double mp_time, double sp_time, double total_time) throws IOException {
        if(WhetherPrintProcess || WhetherPrintIteration){
            log.info(iteration+"\t\t"
                    +String.format("%.2f", LB)+"\t\t"
                    +String.format("%.2f", UB)+"\t\t"
                    +String.format("%.2f", mp_time)+"\t\t"
                    +String.format("%.2f", sp_time)+"\t\t"
                    +String.format("%.2f", total_time)+"\t\t"
            );
        }
        if(WhetherWriteFileLog){
            fileWriter.write(iteration+"\t\t"
                    +String.format("%.2f", LB) +"\t\t"
                    +String.format("%.2f", UB)+"\t\t"
                    +String.format("%.2f", mp_time)+"\t\t"
                    +String.format("%.2f", sp_time)+"\t\t"
                    +String.format("%.2f", total_time)+"\t\t"
            );
            fileWriter.write("\n");
            fileWriter.flush();
        }
    }

    private double Gap;
    public double getGap() {
        return Gap;
    }
    protected void setGap(double Gap) {
        this.Gap = Gap;
    }
    private double obj;
    public double getObjVal() {
        return obj;
    }
    protected void setObj(double obj) {
        this.obj = obj;
    }

    private double solveTime;
    public double getSolveTime() {
        return solveTime;
    }
    protected void setSolveTime(double solveTime) {
        this.solveTime = solveTime;
    }

    private int iter;
    public int getIter() {
        return iter;
    }
    protected void setIter(int iter) {
        this.iter = iter;
    }

}
