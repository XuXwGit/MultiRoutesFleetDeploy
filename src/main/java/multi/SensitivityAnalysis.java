package multi;

import ilog.concert.IloException;

import lombok.extern.slf4j.Slf4j;
import multi.algos.CCG.CCGwithPAP;
import multi.network.Port;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SensitivityAnalysis {
    private static int defaultTimeHorizon;
    private double[] uncertainDegreeSet = {0.005, 0.015, 0.025, 0.035,0.045, 0.055, 0.065, 0.075, 0.085, 0.095};
    private double[] containerPathCostSet = {0.80, 0.825, 0.85, 0.875, 0.90, 0.925, 0.95, 0.975,
        1.025,1.05, 1.0725, 1.10,1.125, 1.15, 1.175, 1.20};
    private double[] rentalContainerCostSet = {0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00,
            1.05, 1.10, 1.15,  1.20, 1.25, 1.30, 1.35, 1.40};
     private double[] penaltyCostSet = {1.025, 1.075, 1.125, 1.175};

    private int[] turnOverTimeSet = {0,1, 2, 3, 4,5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23,  24, 25,  26, 27, 28};
    private int[] initialContainerSet = { 0,1, 2, 3, 4,5, 6, 7,
                                                                        8, 9, 10, 11, 12, 13, 14,
                                                                        15, 16, 17, 18, 19, 20, 21,
                                                                        22, 23,  24, 25,  26, 27, 28,
                                                                        29, 30, 31, 32, 33, 34, 35,
                                                                        36, 37, 38, 39, 40, 41, 42};
    private  int[] timeHorizonSet = {60, 75, 90, 105, 120, 135, 150, 165, 180};

    private double uncertainDegree = 0.05;
    private FileWriter fileWriter;
    private String algo;
    public SensitivityAnalysis(int instance, int type, String algo)
    {
        super();
        this.algo = algo;

        try{

            if(DefaultSetting.WhetherWriteFileLog){
                File file = new File(
                DefaultSetting.RootPath +  DefaultSetting.TestResultPath
                        + "SensitivityAnalysis" + instance
                        + "-" + type
                        + "-" + this.algo
                        + "-" + DefaultSetting.randomSeed+ ".txt");
                if (!file.exists()) {
                    try {
                        file.createNewFile();
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                }
                fileWriter = new FileWriter(file, true);

            }

            String fileName = DefaultSetting.DataPath;
            if(instance == 1){
                fileName += "data1/";
                defaultTimeHorizon = 70;
            } else if (instance == 2) {
                fileName += "data2/";
                defaultTimeHorizon = 90;
                //timeHorizonSet = new int[]{60, 75, 90, 105, 120, 135};
            }
            else if (instance == 3) {
                fileName += "data3/";
                defaultTimeHorizon = 90;
            }

            InputData input = new InputData();
            new ReadData(fileName, input, defaultTimeHorizon);
            input.showStatus();

            log.info("Experiment " + type + ": ");
            if(type == 1){
                log.info("Sensitivity Analysis Varying TurnOverTime");
                VaryTurnOverTime(input);
            } else if (type == 2) {
                log.info("Sensitivity Analysis Varying Penalty Cost");
                VaryPenaltyCost(input);
            } else if (type == 3) {
                log.info("Sensitivity Analysis Varying Unit Rental Cost");
                VaryRentalCost(input);
            }
           //VaryInitialContainers(in);
           //VaryUncertainDegree(in);
           //VaryLoadAndDischargeCost(in);

        }catch (IOException e) {
            e.printStackTrace();
        } catch (IloException e) {
            throw new RuntimeException(e);
        }
    }

    private void VaryUncertainDegree(InputData in) throws IloException, IOException {
        log.info("=========Varying UncertainDegree from 0 to 0.20==========");

        if(DefaultSetting.WhetherWriteFileLog){
            fileWriter.write("=========Varying UncertainDegree from 0 to 0.20==========");
            fileWriter.write("\n");
        }

        double UD;
        for (int i = 0; i < uncertainDegreeSet.length; i++) {

            log.info("uncertainDegreeSet = "+uncertainDegreeSet[i]);

            Parameter p = new Parameter();
            UD = uncertainDegreeSet[i];
            new GenerateParameter(p, in, defaultTimeHorizon, UD);

            CCGwithPAP cp = new CCGwithPAP(in, p, (int) Math.sqrt(in.getRequestSet().size()));

            log.info("UD"
                    + '\t' + "LPC"
                    + '\t' + "EPC"
                    + '\t' + "LC+EC"
                    + '\t' + "RC"
                    + '\t' + "PC"
                    + '\t' + "OC"
                    + '\t' + "TC");
            log.info(UD
                    + "\t" + String.format("%.2f", cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getRentalCost())
                    + "\t" + String.format("%.2f", cp.getPenaltyCost())
                    + "\t" + String.format("%.2f", cp.getOperationCost())
                    + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            log.info("=================================");


            if(DefaultSetting.WhetherWriteFileLog){
                fileWriter.write("UncertainDegree"
                        + '\t' + "LadenPathCost"
                        + '\t' + "EmptyPathCost"
                        + '\t' + "LC+EC"
                        + '\t' + "RentalCost"
                        + '\t' + "PenaltyCost"
                        + '\t' + "OperationCost"
                        +'\t'+"TotalCost"+'\n');
                fileWriter.write(UD
                        + "\t" + String.format("%.2f", cp.getLadenCost())
                        + "\t" + String.format("%.2f", cp.getEmptyCost())
                        + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                        + "\t" + String.format("%.2f", cp.getRentalCost())
                        + "\t" + String.format("%.2f", cp.getPenaltyCost())
                        + "\t" + String.format("%.2f", cp.getOperationCost())
                        +"\t"+String.format("%.2f", cp.getTotalCost())+"\n");
            }
        }
    }

    private void VaryLoadAndDischargeCost(InputData in) throws IOException, IloException {
        log.info("=========Varying Unit L&D&T Cost========");

        double LDTCoeff;
        for (int i = 0; i < containerPathCostSet.length; i++) {

            log.info("Unit ContainerPath Cost = "+ containerPathCostSet[i]);

            Parameter p = new Parameter();
            new GenerateParameter(p, in, defaultTimeHorizon, uncertainDegree);
            LDTCoeff = containerPathCostSet[i];
            double[] ladenPathCost = p.getLadenPathCost();
            double[] emptyPathCost = p.getEmptyPathCost();
            for (int j = 0; j < p.getPathSet().length; j++) {
                ladenPathCost[j] = in.getContainerPaths().get(j).getPathCost() * LDTCoeff + p.getLadenPathDemurrageCost()[j];
                emptyPathCost[j] = in.getContainerPaths().get(j).getPathCost() * 0.5 * LDTCoeff + p.getEmptyPathDemurrageCost()[j];
            }
            p.setLadenPathCost(ladenPathCost);
            p.setEmptyPathCost(emptyPathCost);

            CCGwithPAP cp = new CCGwithPAP(in, p);

            log.info("DemurrageCostCoeff"
                    + '\t' + "LPC"
                    + '\t' + "EPC"
                    + '\t' + "LC+EC"
                    + '\t' + "RC"
                    + '\t' + "PC"
                    + '\t' + "OC"
                    + '\t' + "TC");
            log.info(LDTCoeff
                    + "\t" + String.format("%.2f", cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getRentalCost())
                    + "\t" + String.format("%.2f", cp.getPenaltyCost())
                    + "\t" + String.format("%.2f", cp.getOperationCost())
                    + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            log.info("=================================");

        }
    }

    private void VaryRentalCost(InputData input) throws IloException, IOException {
        log.info("=========Varying Unit Container Rental Cost (0.5~1.5)x20========");

        if(DefaultSetting.WhetherWriteFileLog){
            fileWriter.write("=========Varying Unit Container Rental Cost (0.5~1.5)x20========");
            fileWriter.write("\n");
        }


        double rentalCostCoeff;
        for (int i = 0; i < rentalContainerCostSet.length; i++) {

            log.info("RentalCost = "+rentalContainerCostSet[i]);

            Parameter para = new Parameter();
            new GenerateParameter(para, input, defaultTimeHorizon, uncertainDegree);
            new SelectPaths(input, para, 0.4);

            rentalCostCoeff = rentalContainerCostSet[i];
            para.changeRentalCost(rentalCostCoeff);

            CCGwithPAP cp = new CCGwithPAP(input, para);

            log.info("RentalCostCoeff"
                    + '\t' + "LPC"
                    + '\t' + "EPC"
                    + '\t' + "LC+EC"
                    + '\t' + "RC"
                    + '\t' + "PC"
                    + '\t' + "OC"
                    + '\t' + "TC");
            log.info(rentalCostCoeff
                    + "\t" + String.format("%.2f", cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getRentalCost())
                    + "\t" + String.format("%.2f", cp.getPenaltyCost())
                    + "\t" + String.format("%.2f", cp.getOperationCost())
                    + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            log.info("=================================");


            if(DefaultSetting.WhetherWriteFileLog){
                fileWriter.write("RentalCostCoeff"
                        + '\t' + "LPC"
                        + '\t' + "EPC"
                        + '\t' + "LC+EC"
                        + '\t' + "RC"
                        + '\t' + "PC"
                        + '\t' + "OC"
                        + '\t' + "TC");
                fileWriter.write(rentalCostCoeff
                        + "\t" + String.format("%.2f", cp.getLadenCost())
                        + "\t" + String.format("%.2f", cp.getEmptyCost())
                        + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                        + "\t" + String.format("%.2f", cp.getRentalCost())
                        + "\t" + String.format("%.2f", cp.getPenaltyCost())
                        + "\t" + String.format("%.2f", cp.getOperationCost())
                        + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            }

        }
    }

    private void VaryPenaltyCost(InputData input) throws IloException, IOException {
        log.info("=========Varying Unit Demand Penalty Cost (80%~120%)=========");

        if(DefaultSetting.WhetherWriteFileLog){
            fileWriter.write("=========Varying Unit Demand Penalty Cost (80%~120%)=========");
            fileWriter.write("\n");
        }
        
        double PenaltyCostCoeff;
        for (int i = 0; i <penaltyCostSet.length; i++) {
            log.info("PenaltyCostCoeff = " + penaltyCostSet[i]);

            Parameter para = new Parameter();
            new GenerateParameter(para, input, defaultTimeHorizon, uncertainDegree);
            new SelectPaths(input, para, 0.4);

            PenaltyCostCoeff = penaltyCostSet[i];
            para.changePenaltyCostForDemand(PenaltyCostCoeff);

            CCGwithPAP cp = new CCGwithPAP(input, para);

            log.info("PenaltyCostCoeff"
                    + '\t' + "LPC"
                    + '\t' + "EPC"
                    + '\t' + "RC"
                    + '\t' + "PC"
                    + '\t' + "OC"
                    + '\t' + "TC");
            log.info(PenaltyCostCoeff
                    + "\t" + String.format("%.2f", cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getRentalCost())
                    + "\t" + String.format("%.2f", cp.getPenaltyCost())
                    + "\t" + String.format("%.2f", cp.getOperationCost())
                    + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            log.info("=================================");
        }
    }

    private void VaryTurnOverTime(InputData input) throws IloException, IOException {
        log.info("=========Varying TurnOverTime (0~28) =========");

        int turnOverTime;
        for (int i = 0; i <turnOverTimeSet.length; i++) {
            log.info("******************** TurnOverTime = " + turnOverTimeSet[i]+"********************");

            Parameter para = new Parameter();
            new GenerateParameter(para, input, defaultTimeHorizon, uncertainDegree);
            new SelectPaths(input, para, 0.4);

            turnOverTime = turnOverTimeSet[i];
            para.setTurnOverTime(turnOverTime);

            CCGwithPAP cp = new CCGwithPAP(input, para);

            log.info("turnOverTime"
                    + '\t' + "LPC"
                    + '\t' + "EPC"
                    + '\t' + "LC+EC"
                    + '\t' + "RC"
                    + '\t' + "PC"
                    + '\t' + "OC"
                    + '\t' + "TC");
            log.info(turnOverTime
                    + "\t" + String.format("%.2f", cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getRentalCost())
                    + "\t" + String.format("%.2f", cp.getPenaltyCost())
                    + "\t" + String.format("%.2f", cp.getOperationCost())
                    + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            log.info("=================================");
        }
    }

    private void VaryInitialContainers(InputData in) throws IloException, IOException {
        log.info("=========Varying initialContainers (0~28) =========");

        int initialContainers;
        for (int i = 0; i <initialContainerSet.length; i++) {
            log.info("initialContainers = " + initialContainerSet[i]);

            Parameter p = new Parameter();
            new GenerateParameter(p, in, defaultTimeHorizon, uncertainDegree);

            // reset initial empty containers
            initialContainers = initialContainerSet[i];
            // calculate initial number of empty containers for each port at time 0
            // initial number of empty container in pp = total demands which origins in port pp * [0.8, 1.0]
            int[] initialEmptyContainer =new int [in.getPortSet().size()];
            int x=0;
            double alpha=0.8+0.2*DefaultSetting.random.nextDouble();
            int totalOwnedEmptyContainers = 0;
            for(Port pp:in.getPortSet().values())
            {
                for(int ii = 0; ii<in.getRequestSet().size(); ii++)
                {
                    if(pp.getPort().equals(in.getRequestSet().get(ii).getOriginPort())
                            &&in.getRequestSet().get(ii).getEarliestPickupTime()<initialContainers)
                    {
                        initialEmptyContainer [x]=(int) (initialEmptyContainer [x]+alpha*p.getDemand()[i]);
                        totalOwnedEmptyContainers += initialEmptyContainer [x];
                    }
                }
                x=x+1;
            }
            log.info("Total Initial Owned Empty Containers = "+totalOwnedEmptyContainers);
            p.setInitialEmptyContainer(initialEmptyContainer);

            CCGwithPAP cp = new CCGwithPAP(in, p, (int) Math.sqrt(in.getRequestSet().size()));

            log.info("initialContainers"
                    + '\t' + "LPC"
                    + '\t' + "EPC"
                    + '\t' + "RC"
                    + '\t' + "PC"
                    + '\t' + "OC"
                    + '\t' + "TC");
            log.info(initialContainers
                    + "\t" + String.format("%.2f", cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost())
                    + "\t" + String.format("%.2f", cp.getEmptyCost()+cp.getLadenCost())
                    + "\t" + String.format("%.2f", cp.getRentalCost())
                    + "\t" + String.format("%.2f", cp.getPenaltyCost())
                    + "\t" + String.format("%.2f", cp.getOperationCost())
                    + "\t" + String.format("%.2f", cp.getTotalCost())+"\n");
            log.info("=================================");
        }
    }
}
