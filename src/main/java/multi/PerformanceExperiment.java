package multi;

import ilog.concert.IloException;
import lombok.extern.slf4j.Slf4j;
import multi.algos.BD.BD;
import multi.algos.BD.BDwithPAP;
import multi.algos.BD.BDwithPareto;
import multi.algos.BD.SOwithBD;
import multi.algos.BD.SOwithSAA;
import multi.algos.CCG.CCG;
import multi.algos.CCG.CCGwithPAP;
import multi.algos.CCG.CCGwithPAP_Reactive;
import multi.model.primal.DetermineModel;
import multi.model.primal.DetermineModelReactive;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

/**
 * 性能实验类
 *
 * 用于测试和比较不同算法的性能表现
 *
 * 主要功能:
 * 1. 运行不同算法(BD, CCG等)的性能测试
 * 2. 记录求解时间、目标值等关键指标
 * 3. 生成性能测试报告
 *
 * 测试用例:
 * 1. 小规模实例(data1): 2条航线,10个港口,10艘船
 * 2. 中规模实例(data3): 3条航线,21个港口,35艘船
 * 3. 大规模实例(data2): 8条航线,29个港口,40艘船
 *
 * @Author: XuXw
 * @DateTime: 2024/12/4 17:28
 */
@Slf4j
public class PerformanceExperiment {
    /**
     * 结果文件写入器
     */
    private static FileWriter fileWriter;
    
    /**
     * 时间范围集合(天)
     */
    private static int[] timeHorizonSet;
    
    /**
     * 不确定度系数[0,1]
     */
    private static double uncertainDegree = DefaultSetting.defaultUncertainDegree;
    
    /**
     * 默认时间范围(天)
     */
    private static int defaultTimeHorizon;
    /**
     * 性能实验构造函数
     *
     * @param instance 测试实例编号(1:小规模,2:大规模,3:中规模)
     * @param type 算法类型
     * @throws IloException CPLEX异常
     * @throws IOException 文件操作异常
     */
    public PerformanceExperiment(int instance, int type) throws IloException, IOException {

        File file = new File(DefaultSetting.RootPath +  DefaultSetting.TestResultPath
                + "Performance" + instance
                + "-" + type
                + "-" + DefaultSetting.randomSeed+ ".txt");
        if (!file.exists()) {
            try {
                file.createNewFile();
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        fileWriter = new FileWriter(file, true);

        // instance:
        // 1-> data1 : R=2,P=10,V=10 /small scale with 2 ship routes
        // 2-> data2 : R=8,P=29,V=40 /large scale with 8 ship routes
        // 3-> data3 : R=3,P=21,V=35 /middle scale with 3 ship routes
        String fileName = DefaultSetting.DataPath + DefaultSetting.CasePath;
        if(instance == 1){
            defaultTimeHorizon = 70;
            timeHorizonSet = new int[]{56, 63, 70, 77, 84, 91};
        } else if (instance == 2) {
            defaultTimeHorizon = 90;
            timeHorizonSet = new int[]{90};
            //timeHorizonSet = new int[]{60, 75, 90, 105, 120, 135};
        }
        else if (instance == 3) {
            //timeHorizonSet = new int[]{180, 165, 150, 135, 120, 105, 90};
            timeHorizonSet = new int[]{90, 105, 120, 135, 150, 165, 180};
        }

        //print_strategy_status(fileName);

        // experiment type
        // 1: compare the performance of the four algorithms (CCG/BD/CCG&PAP/BD&PAP)
        // 2: compare the empty container reposition strategy with reactive strategy
        // 3: compare different laden/empty paths select strategy
        // 4: compare different fleet composition: Homo V\S Hetero
        // 5: compare different vessel capacity range
        // 6: compare different demand distribution
        // 7: compare mean-performance and worst-case performance
        // 8: compare two-stage robust with two-stage stochastic programming
        log.info("Experiment " + type + ": ");
        if(type == 1){
            log.info("Compare the performance of the four algorithms (CCG/BD/CCG&PAP/BD&PAP)");
            experimentTest1(fileName);
        } else if (type == 2) {
            log.info("Compare the empty container reposition strategy with reactive strategy");
            experiment_test2(fileName);
        }else if (type == 3){
            log.info("Compare performance under different laden/empty paths select strategy");
            experimentTest3(fileName);
        }else if (type == 4){
            log.info("Compare performance under different fleet composition: Homo V/S Hetero");
            experiment_test4(fileName);
        }else if (type == 5){
            log.info("Compare performance under different vessel capacity range");
            experiment_test5(fileName);
        }else if (type == 6){
            log.info("Compare performance under different demand distribution");
            experiment_test6(fileName);
        }else if (type == 7){
            log.info("Compare mean-performance and worst-case performance");
            experiment_test7(fileName);
        }else if (type == 8){
            log.info("Compare two-stage robust with two-stage stochastic programming");
            experiment_test8(fileName);
        }else if (type == 9){
            log.info("Compare two-stage robust with two-stage stochastic programming");
            experiment_test9(fileName);
        }else if (type == 10){
            log.info("Consider Fold Containers and no empty container reposition");
            experimentTest10(fileName);
        }

        fileWriter.close();
    }

    static private void experimentTest1(String filename) throws IloException, IOException {
        log.info("========================== Begin Performance Test =========================");
        log.info("==============================" + "Experiment 1" + "=============================");
        for (int t : timeHorizonSet) {
            InputData inputData = new InputData();
            new ReadData(filename, inputData, t);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, t, uncertainDegree);
            inputData.showStatus();
            new SelectPaths(inputData, para, 0.4);

            // DetermineModel de = new DetermineModel(inputData, para);
            // de.solveModel();

            //DualSubProblem dsp = new DualSubProblem(inputData, para, para.getTau());
            //dsp.changeObjectiveVCoefficients(de.getVVarValue());
            //dsp.solveModel();

            CCG ccg = new CCG(inputData, para);
            CCGwithPAP ccgp = new CCGwithPAP(inputData, para);
            // BDwithPAP bdp = new BDwithPAP(inputData, para, para.getTau());
            BD bd = new BD(inputData, para);
            DetermineModel dm = new DetermineModel(inputData, para);
            // BDwithPareto bdpa = new BDwithPareto(inputData, para, para.getTau());


            log.info("=====================================================================");

            log.info("Algorithm :" + "\t"
                    //+ "BD&Pareto"+ "\t"
                    //+ "BD&PAP"+ "\t"
                    + "BD" + "\t"
                    + "CCG&PAP" + "\t"
                    + "CCG" + "\t"
            );
            log.info("SolveTime :" + "\t"
                    //+ bdpa.getSolveTime() + "\t"
                    // + bdp.getSolveTime() + "\t"
                    + bd.getSolveTime() + "\t"
                    + ccgp.getSolveTime() + "\t"
                    + ccg.getSolveTime() + "\t"
            );
            log.info("Objective  :" + "\t"
                    //+ String.format("%.2f", bdpa.getObj()) + "\t"
                    // + String.format("%.2f", bdp.getObjVal())+ "\t"
                    + String.format("%.2f", bd.getObjVal())+ "\t"
                    + String.format("%.2f", ccgp.getObjVal()) + "\t"
                    + String.format("%.2f", ccg.getObjVal()) + "\t"
            );
            log.info("Iteration    :" + "\t"
                    //+ bdpa.getIter() + "\t"
                    // + bdp.getIter()+ "\t"
                    + bd.getIter()+ "\t"
                    + ccgp.getIter() + "\t"
                    + ccg.getIter() + "\t"
            );
            log.info("=====================================================================");


            if(DefaultSetting.WhetherWriteFileLog){
                fileWriter.write("\n" + "TimeHorizon : " + t + "\n");
                fileWriter.write("UncertainDegree : " + uncertainDegree + "\n");

                inputData.writeStatus(fileWriter);

                fileWriter.write("Algorithm :" + "\t"
                        //+ "BD&Pareto"+ "\t"
                        // + "BD&PAP"+ "\t"
                        + "BD" + "\t"
                        + "CCG&PAP" + "\t"
                        + "CCG" + "\t"
                        + "\n"
                );
                fileWriter.write("SolveTime :" + "\t"
                        //+ bdpa.getSolveTime() + "\t"
                        // + bdp.getSolveTime() + "\t"
                        + bd.getSolveTime() + "\t"
                        + ccgp.getSolveTime() + "\t"
                        + ccg.getSolveTime() + "\t"
                        + "\n"
                );
                fileWriter.write("Objective  :" + "\t"
                        //+ String.format("%.2f", bdpa.getObj()) + "\t"
                        // + String.format("%.2f", bdp.getObjVal())+ "\t"
                        + String.format("%.2f", bd.getObjVal())+ "\t"
                        + String.format("%.2f", ccgp.getObjVal()) + "\t"
                        + String.format("%.2f", ccg.getObjVal()) + "\t"
                        + "\n"
                );
                fileWriter.write("Iteration    :" + "\t"
                        //+ bdpa.getIter() + "\t"
                        //+ bdp.getIter()+ "\t"
                        + bd.getIter()+ "\t"
                        + ccgp.getIter() + "\t"
                        + ccg.getIter() + "\t"
                        + "\n"
                );
                fileWriter.write("\n");
                fileWriter.flush();
            }
        }
    }

    static private void experiment_test2(String filename) throws IloException, IOException {
        log.info("========================== Begin Performance Test =========================");
        log.info("=============================" + "Experiment 2" + "=============================");

        for (int T : timeHorizonSet) {
            log.info("TimeHorizon : " + T + "\n");
            log.info("UncertainDegree : " + uncertainDegree + "\n");

            InputData inputData = new InputData();
            new ReadData(filename, inputData, T);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, T, uncertainDegree);

            DetermineModel                              de = new DetermineModel(inputData, para);
            DetermineModelReactive der = new DetermineModelReactive(inputData, para);
            CCGwithPAP                                      cp = new CCGwithPAP(inputData, para);
            CCGwithPAP_Reactive cpr = new CCGwithPAP_Reactive(inputData, para);

            log.info("==========================================");
            log.info("Algorithm :" + "\t"
                    + "Determine" + "\t"
                    + "Determine&Reactive" + "\t"
                    + "CCG&PAP"+ "\t"
                    + "CCG&PAP&Reactive" + "\t"
            );
            log.info("SolveTime :" + "\t"
                    + de.getSolveTime() + "\t"
                    +  der.getSolveTime() + "\t"
                    + cp.getSolveTime()  + "\t"
                    + cpr.getSolveTime()  + "\t"
            );
            log.info("Objective  :" + "\t"
                    + String.format("%.2f", de.getObjVal()) + "\t"
                    + String.format("%.2f", der.getObjVal()) + "\t"
                    + String.format("%.2f", cp.getObjVal())+ "\t"
                    + String.format("%.2f", cpr.getObjVal()) + "\t"
            );
            log.info("===========================================");


            if(DefaultSetting.WhetherWriteFileLog){
                fileWriter.write("\n" + "TimeHorizon : " + T + "\n");
                fileWriter.write("UncertainDegree : " + uncertainDegree + "\n");
                inputData.writeStatus(fileWriter);

                fileWriter.write("Algorithm :" + "\t"
                        + "Determine" + "\t"
                        + "Determine&Strategy" + "\t"
                        + "CCG&PAP"+ "\t"
                        + "CCG&PAP&Reactive" + "\t"
                        + "\n"
                );
                fileWriter.write("SolveTime :" + "\t"
                        + de.getSolveTime() + "\t"
                        + der.getSolveTime() + "\t"
                        + cp.getSolveTime() + "\t"
                        + cpr.getSolveTime() + "\t"
                        + "\n"
                );
                fileWriter.write("Objective  :" + "\t"
                        + String.format("%.2f", de.getObjVal()) + "\t"
                        + String.format("%.2f", der.getObjVal())+ "\t"
                        + String.format("%.2f", cp.getObjVal()) + "\t"
                        + String.format("%.2f", cpr.getObjVal())
                        + "\n"
                );
                fileWriter.write("Iteration    :" + "\t"
                        + 1 					  + "\t"
                        + 1 + "\t"
                        + cp.getIter()+ "\t"
                        + cpr.getIter()+ "\t"
                        + "\n"
                );
                fileWriter.write("\n");
                fileWriter.flush();
            }
        }
    }

    static private void print_data_status(String filename) throws IOException {
        log.info("========================== Print Data Status =========================");

        for (int T : timeHorizonSet) {
            log.info("TimeHorizon : " + T + "\n");
            InputData inputData = new InputData();
            new ReadData(filename, inputData, T);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, T, uncertainDegree);
            log.info("UncertainDegree : " + uncertainDegree + "\n");

            inputData.showStatus();
        }
    }

    static private void experimentTest3(String filename) throws IOException, IloException {
        print_data_status(filename);

        log.info("========================== Begin Performance Test =========================");
        log.info("=============================" + "Experiment 3" + "=============================");

        for (int T : timeHorizonSet) {
            log.info("TimeHorizon : " + T + "\n");
            double[] percentSet = new double[]{0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95, 1.0};
            //double[] percentSet = new double[]{0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0};
            for (double percent : percentSet) {
                log.info("Path Percent : " + percent + "\n");
                InputData inputData = new InputData();
                new ReadData(filename, inputData, T);
                Parameter para = new Parameter();
                new GenerateParameter(para, inputData, T, uncertainDegree);
                log.info("UncertainDegree : " + uncertainDegree + "\n");
                inputData.showStatus();
                new SelectPaths(inputData, para, percent);

                CCGwithPAP ccgp = new CCGwithPAP(inputData, para);
                CCG ccg = new CCG(inputData, para);
                BD bd = new BD(inputData, para);
                BDwithPAP bdp = new BDwithPAP(inputData, para);

                log.info("=====================================================================");

                log.info("Algorithm :" + "\t"
                        + "BD&PAP" + "\t"
                        + "BD" + "\t"
                        + "CCG&PAP" + "\t"
                        + "CCG" + "\t"
                );
                log.info("SolveTime :" + "\t\t"
                        + bdp.getSolveTime() + "\t"
                        + bd.getSolveTime() + "\t"
                        + ccgp.getSolveTime() + "\t"
                        + ccg.getSolveTime() + "\t"
                );
                log.info("Objective :" + "\t\t"
                        + String.format("%.2f", bdp.getObjVal()) + "\t"
                        + String.format("%.2f", bd.getObjVal()) + "\t"
                        + String.format("%.2f", ccgp.getObjVal()) + "\t"
                        + String.format("%.2f", ccg.getObjVal()) + "\t"
                );
                log.info("Iteration    :" + "\t\t"
                        + bdp.getIter() + "\t"
                        + bd.getIter() + "\t"
                        + ccgp.getIter() + "\t"
                        + ccg.getIter() + "\t"
                        + "\n"
                );
                log.info("=====================================================================");


                if (DefaultSetting.WhetherWriteFileLog) {
                    fileWriter.write("\n");
                    fileWriter.write("=====================================================================");
                    fileWriter.write("\n");
                    fileWriter.write("Path Percent : " + (1 - percent) + "\n");
                    inputData.writeStatus(fileWriter);

                    fileWriter.write("Algorithm :" + "\t"
                            + "BD&PAP" + "\t"
                            + "BD" + "\t"
                            + "CCG&PAP" + "\t"
                            + "CCG" + "\t"
                            + "\n"
                    );
                    fileWriter.write("SolveTime :" + "\t"
                            + bdp.getSolveTime() + "\t"
                            + bd.getSolveTime() + "\t"
                            + ccgp.getSolveTime() + "\t"
                            + ccg.getSolveTime() + "\t"
                            + "\n"
                    );
                    fileWriter.write("Objective  :" + "\t"
                            + String.format("%.2f", bdp.getObjVal()) + "\t"
                            + String.format("%.2f", bd.getObjVal()) + "\t"
                            + String.format("%.2f", ccgp.getObjVal()) + "\t"
                            + String.format("%.2f", ccg.getObjVal()) + "\t"
                            + "\n"
                    );
                    fileWriter.write("Iteration    :" + "\t"
                            + bdp.getIter() + "\t"
                            + bd.getIter() + "\t"
                            + ccgp.getIter() + "\t"
                            + ccg.getIter() + "\t"
                            + "\n"
                    );
                    fileWriter.write("=====================================================================");
                    fileWriter.write("\n");
                    fileWriter.flush();
                }
            }
        }
    }

    static private void experiment_test4(String filename) throws IOException, IloException {
        DefaultSetting.CCG_PAP_Use_Sp = true;
        print_data_status(filename);
        log.info("========================== Begin Performance Test =========================");
        log.info("=============================" + "Experiment 4" + "=============================");

        fileWriter.write("\n" + "===========================================" + "\n");
        fileWriter.write("TimeHorizon" + "\t" + "Homo-Obj" + "\t" + "Hetero-Obj"  + "\t"
                + "Homo-OC" + "\t" + "Hetero-OC"  + "\t"
                + "Homo-LC" + "\t" + "Hetero-LC"  + "\t"
                + "Homo-EC" + "\t" + "Hetero-EC"  + "\t"
                + "Homo-RC" + "\t" + "Hetero-RC"  + "\t"
                + "Homo-PC" + "\t" + "Hetero-PC"  + "\t"
                + "Homo-WP" + "\t" + "Hetero-WP"  + "\t"
                + "\n");

        for (int T : timeHorizonSet) {
            log.info("TimeHorizon : " + T + "\n");
            log.info("UncertainDegree : " + uncertainDegree + "\n");
            InputData inputData = new InputData();
            new ReadData(filename, inputData, T);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, T, uncertainDegree);
            inputData.showStatus();
            new SelectPaths(inputData, para, 0.4);

            DefaultSetting.FleetType = "Homo";
            CCGwithPAP ccgp_homo = new CCGwithPAP(inputData, para);
            DefaultSetting.FleetType = "Hetero";
            CCGwithPAP ccgp_hetero = new CCGwithPAP(inputData, para);

            if(DefaultSetting.WhetherWriteFileLog) {
                fileWriter.write(T + "\t");
                fileWriter.write(ccgp_homo.getObjVal() + "\t");
                fileWriter.write(ccgp_hetero.getObjVal() + "\t");
                fileWriter.write(ccgp_homo.getOperationCost() + "\t");
                fileWriter.write(ccgp_hetero.getOperationCost() + "\t");
                fileWriter.write(ccgp_homo.getLadenCost() + "\t");
                fileWriter.write(ccgp_hetero.getLadenCost() + "\t");
                fileWriter.write(ccgp_homo.getEmptyCost() + "\t");
                fileWriter.write(ccgp_hetero.getEmptyCost() + "\t");
                fileWriter.write(ccgp_homo.getRentalCost() + "\t");
                fileWriter.write(ccgp_hetero.getRentalCost() + "\t");
                fileWriter.write(ccgp_homo.getPenaltyCost() + "\t");
                fileWriter.write(ccgp_hetero.getPenaltyCost() + "\t");
                fileWriter.write(ccgp_homo.getWorstPerformance() + "\t");
                fileWriter.write(ccgp_hetero.getWorstPerformance() + "\t");
                fileWriter.write("\n");
                fileWriter.flush();
            }
        }
    }

    static private void experiment_test5(String filename) throws IOException, IloException {
        DefaultSetting.CCG_PAP_Use_Sp = true;
        log.info("========================== Begin Performance Test =========================");
        log.info("==========================" + "Experiment 5" + "==========================");

        fileWriter.write("\n" + "===========================================" + "\n");
        fileWriter.write("TimeHorizon" + "\t" + "Obj." + "\t"
                + "OC" + "\t"
                + "LC" + "\t"
                + "C" + "\t"
                + "RC" + "\t"
                + "PC" + "\t"
                + "WP" + "\t"
                + "\n");

        for(String vessel_type: new String[]{"II", "III"}){
            DefaultSetting.writeSettings(fileWriter);
            DefaultSetting.printSettings();


            DefaultSetting.VesselCapacityRange = vessel_type;

            for (int T : timeHorizonSet) {
                log.info("TimeHorizon : " + T + "\n");

                InputData inputData = new InputData();
                new ReadData(filename, inputData, T);

                inputData.showStatus();

                Parameter para = new Parameter();
                new GenerateParameter(para, inputData, T, uncertainDegree);
                log.info("UncertainDegree : " + uncertainDegree + "\n");

                new SelectPaths(inputData, para, 0.4);

                CCGwithPAP ccgp = new CCGwithPAP(inputData, para, para.getTau());

                if(DefaultSetting.WhetherWriteFileLog) {
                    fileWriter.write(T + "\t");
                    fileWriter.write(ccgp.getObjVal() + "\t");
                    fileWriter.write(ccgp.getOperationCost() + "\t");
                    fileWriter.write(ccgp.getLadenCost() + "\t");
                    fileWriter.write(ccgp.getEmptyCost() + "\t");
                    fileWriter.write(ccgp.getRentalCost() + "\t");
                    fileWriter.write(ccgp.getPenaltyCost() + "\t");
                    fileWriter.write(ccgp.getWorstPerformance() + "\t");
                    fileWriter.write("\n");
                    fileWriter.flush();
                }

            }
        }
    }

    static private void experiment_test6(String fileName) throws IOException, IloException {
        DefaultSetting.CCG_PAP_Use_Sp = true;
        log.info("========================== Begin Performance Test =========================");
        log.info("==========================" + "Experiment 6" + "==========================");
        log.info("DistributionType : " + DefaultSetting.distributionType + "\n");
        String filename = fileName+"/";

        fileWriter.write("\n" + "===========================================" + "\n");
        fileWriter.write("TimeHorizon" + "\t" + "Obj." + "\t"
                + "OC" + "\t"
                + "LC" + "\t"
                + "C" + "\t"
                + "RC" + "\t"
                + "PC" + "\t"
                + "WP" + "\t"
                + "\n");
        int T = defaultTimeHorizon;
        log.info("TimeHorizon : " + T + "\n");
        //double[] sigma_factor_set = new double[]{0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0};
        double[] sigmaFactorSet = new double[]{1};
        for (double sigmaFactor : sigmaFactorSet) {
            log.info("UncertainDegree : " + uncertainDegree + "\n");
            DefaultSetting.log_normal_sigma_factor = sigmaFactor;
            log.info("log_normal_sigma_factor : " + DefaultSetting.log_normal_sigma_factor + "\n");

            InputData inputData = new InputData();
            new ReadData(filename, inputData, T);
            inputData.showStatus();
            Parameter para = new Parameter();

            //distributionType = "Log-Normal";
            DefaultSetting.distributionType = "Uniform";
            new GenerateParameter(para, inputData, T, uncertainDegree);
            new SelectPaths(inputData, para, 0.4);

            CCGwithPAP ccgp = new CCGwithPAP(inputData, para, para.getTau());

            if(DefaultSetting.WhetherWriteFileLog) {
                fileWriter.write(sigmaFactor + "\t");
                fileWriter.write(ccgp.getObjVal() + "\t");
                fileWriter.write(ccgp.getOperationCost() + "\t");
                fileWriter.write(ccgp.getLadenCost() + "\t");
                fileWriter.write(ccgp.getEmptyCost() + "\t");
                fileWriter.write(ccgp.getRentalCost() + "\t");
                fileWriter.write(ccgp.getPenaltyCost() + "\t");
                fileWriter.write(ccgp.getWorstPerformance() + "\t");
                fileWriter.write(ccgp.getMeanPerformance() + "\t");
                fileWriter.write("\n");
                fileWriter.flush();
            }
        }
    }

    static private void experiment_test7(String filename) throws IOException, IloException {
        DefaultSetting.WhetherGenerateSamples = true;
        DefaultSetting.WhetherCalculateMeanPerformance = true;
        DefaultSetting.UseHistorySolution = true;
        DefaultSetting.CCG_PAP_Use_Sp = true;

        log.info("========================== Begin Performance Test =========================");
        log.info("=============================" + "Experiment 7" + "=============================");

        fileWriter.write("\n");
        fileWriter.write("=====================================================================");
        fileWriter.write("\n");
        fileWriter.write("Methods" + "\t"
                + "DM-MeanPerformance" + "\t"
                + "DM-WorstPerformance" + "\t"
                + "BD-MeanPerformance" + "\t"
                + "BD-WorstPerformance" + "\t"
                + "CCG-MeanPerformance" + "\t"
                + "CCG-WorstPerformance" + "\t"
                + "CCG&PAP-MeanPerformance" + "\t"
                + "CCG&PAP-WorstPerformance" + "\t"
                + "\n");

        DefaultSetting.writeSettings(fileWriter);
        DefaultSetting.printSettings();
        int T = defaultTimeHorizon;

        DefaultSetting.UseHistorySolution = false;

        log.info("TimeHorizon : " + T + "\n");
        log.info("UncertainDegree : " + uncertainDegree + "\n");
        InputData inputData = new InputData();
        new ReadData(filename, inputData, T);
        Parameter para = new Parameter();
        new GenerateParameter(para, inputData, T, uncertainDegree);
        inputData.showStatus();
        new SelectPaths(inputData, para, 0.4);
        log.info("Tau : " + para.getTau());

        ////////////////////////////////////////
        DetermineModel dm = new DetermineModel(inputData, para);
        CCGwithPAP ccgp = new CCGwithPAP(inputData, para);
        //BD bd = new BD(inputData, para, para.getTau());
        //CCG ccg = new CCG(inputData, para, para.getTau());

        fileWriter.write("\n" + "TimeHorizon : " + T + "\n");
        fileWriter.write("UncertainDegree : " + uncertainDegree + "\n");
        fileWriter.write("Tau : " + para.getTau() + "\n");
        fileWriter.write(T + "\t"
                + dm.getMeanPerformance() + "\t"
                + dm.getWorstPerformance() + "\t"
                //+ bd.getMeanPerformance() + "\t"
                //+ bd.getWorstPerformance() + "\t"
                //+ ccg.getMeanPerformance() + "\t"
                // + ccg.getWorstPerformance() + "\t"
                + ccgp.getMeanPerformance() + "\t"
                + ccgp.getWorstPerformance() + "\t"
                + "\n");
        fileWriter.write(T + "\t"
                + dm.getMeanSecondStageCost() + "\t"
                + dm.getWorstSecondStageCost() + "\t"
                //+ bd.getMeanSecondStageCost() + "\t"
                //+ bd.getWorstSecondStageCost() + "\t"
                // + ccg.getMeanSecondStageCost() + "\t"
                //+ ccg.getWorstSecondStageCost() + "\t"
                + ccgp.getMeanSecondStageCost() + "\t"
                + ccgp.getWorstSecondStageCost() + "\t"
                + "\n");
        fileWriter.write("=====================================================================");
        fileWriter.flush();
        fileWriter.close();
    }

    static private void experiment_test8(String filename) throws IOException, IloException {
        log.info("========================== Begin Performance Test =========================");
        log.info("=============================" + "Experiment 8" + "=============================");

        DefaultSetting.writeSettings(fileWriter);
        DefaultSetting.printSettings();
        for (int T : timeHorizonSet) {

            log.info("TimeHorizon : " + T + "\n");
            log.info("UncertainDegree : " + uncertainDegree + "\n");
            InputData inputData = new InputData();
            new ReadData(filename, inputData, T);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, T, uncertainDegree);
            inputData.showStatus();
            new SelectPaths(inputData, para, 0.4);

            SOwithBD so = new SOwithBD(inputData, para);
            log.info("SOwithBD : " + so.getObjVal() + "\t" + so.getSolveTime() + "\t" + so.getIter());
        }
    }

    static private void experiment_test9(String fileName) throws IOException, IloException {
        log.info("========================== Begin Performance Test =========================");
        log.info("=============================" + "Experiment 9" + "=============================");

        String filename = fileName+"/";
        DefaultSetting.writeSettings(fileWriter);
        DefaultSetting.printSettings();
        for (int T : timeHorizonSet) {

            log.info("TimeHorizon : " + T + "\n");
            log.info("UncertainDegree : " + uncertainDegree + "\n");
            InputData inputData = new InputData();
            new ReadData(filename, inputData, T);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, T, uncertainDegree);
            inputData.showStatus();
            new SelectPaths(inputData, para, 0.4);

            BDwithPareto bdpa = new BDwithPareto(inputData, para);
            BD bd = new BD(inputData, para);

            log.info("BD with Pareto Cut: \t" + bdpa.getObjVal() + "\t" + bdpa.getSolveTime() + "\t" + bdpa.getIter());
            log.info("BD : \t" + bd.getObjVal() + "\t" + bd.getSolveTime() + "\t" + bd.getIter());
        }
    }


    static private void experimentTest10(String filename) throws IloException, IOException {
        log.info("========================== Begin Performance Test =========================");
        log.info("==============================" + "Experiment 10" + "=============================");
        for (int t : timeHorizonSet) {
            InputData inputData = new InputData();
            new ReadData(filename, inputData, t);
            Parameter para = new Parameter();
            new GenerateParameter(para, inputData, t, uncertainDegree);
            inputData.showStatus();
            new SelectPaths(inputData, para, 0.4);

            new DetermineModel(inputData, para);
            // de.solveModel();

            new SOwithBD(inputData, para);
            new SOwithSAA(inputData, para);

            log.info("=====================================================================");
        }
    }
}