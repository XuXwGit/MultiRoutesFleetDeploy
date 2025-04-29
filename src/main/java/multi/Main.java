package multi;

import ilog.concert.IloException;
import lombok.extern.slf4j.Slf4j;

import java.io.IOException;
import java.util.Objects;
import java.util.Random;


/**
 * @Author: XuXw
 * @Description: Main Function
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class Main {
	public static void main(String[] args) throws IloException, IOException {
		log.info("Instance：" + args[0]);
		DefaultSetting.CasePath = args[0] + "/";
		log.info("Experiment：" + args[1]);

		int instance = Integer.parseInt(args[0]);
		int experiment = Integer.parseInt(args[1]);

		if (args.length >= 3) {
			if(!"-".equals(args[2])){
				// set the root path
				DefaultSetting.RootPath = args[2];
			}
			log.info("RootPath：" + DefaultSetting.RootPath);
		}
		if(args.length >= 4){
			if(!"-".equals(args[3])) {
				DefaultSetting.MIPGapLimit = Double.parseDouble(args[3]);
				log.info("MIPGapLimit：" + args[3]);
			}
		}
		if(args.length >= 5){
			DefaultSetting.randomSeed = Integer.parseInt(args[4]);
			log.info("Random Seed：" + args[4]);
		}
		if(args.length >= 6){
			DefaultSetting.budgetCoefficient = Double.parseDouble(args[5]);
			log.info("Budget Coefficient：" + args[5]);
		}
		if(args.length >= 7){
			DefaultSetting.defaultUncertainDegree = Double.parseDouble(args[6]);
			log.info("Uncertain Degree：" + args[6]);
		}
		int flag = 1;
		if(args.length >= 8){
			if(Objects.equals(args[7], "P")){
				flag = 1;
				log.info("Numerical ：" + "Performance Test");
			}
			else if("S".equals(args[7])){
				flag = 2;
				log.info("Numerical ：" + "Sensitivity Analysis");
			}
		}

		// print the heap memory setting of JVM
		log.info("Free Memory = " + (Runtime.getRuntime().freeMemory() >> 20) + "M");
		log.info("Max heap Memory = " + (Runtime.getRuntime().maxMemory() >> 20) + "M");
		log.info("Total heap Memory = " + (Runtime.getRuntime().totalMemory() >> 20) + "M");
		log.info("Max Available Cores = "+ Runtime.getRuntime().availableProcessors());

		DefaultSetting.random = new Random(DefaultSetting.randomSeed);
		log.info("=============== Seed = "+DefaultSetting.randomSeed+"===============");
		log.info("Fleet Type DefaultSetting: " + DefaultSetting.FleetType);

		if(flag == 1){
			// input parameters :
			// instance	experiment
			new PerformanceExperiment(instance, experiment);
		}else if(flag == 2){
			// input parameters :
			// Instance	Experiment	 Algo
			new SensitivityAnalysis(instance, experiment, "CCG&PAP");
		}else{
			log.error("Error in Get Flag");
		}
	}
}

