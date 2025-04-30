package multi;

import lombok.extern.slf4j.Slf4j;

import java.io.FileWriter;
import java.io.IOException;
import java.security.PublicKey;
import java.util.Random;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class DefaultSetting {
	//////////////////////////////////
	/* Numerical Experiment Test */
	// VesselType Capacity / Nums
	public static String VesselCapacityRange = "I";

	/**
	 * use heterogeneous / homogeneous fleet
	 * Homo / Hetero
	 */
	public static String FleetType = "Hetero";
	//////////////////////////////////

	// 是否允许折叠箱
	public static boolean AllowFoldableContainer = true;

	// 空箱调度方式：是否重定向
	public static boolean IsEmptyReposition = false;

	//////////////////////////////////

	/**
	 * Strategy DefaultSetting
	 */
	public static double reducePathPercentage = 0;
	public static int MaxLadenPathsNum = 5;
	public static int MaxEmptyPathsNum = 5;
	/* Algo enhancement strategy */
	public static boolean UseParetoOptimalCut = true;
	public static boolean UseLocalSearch = true;
	//////////////////////////////////


	//////////////////////////////////
	/* Default Data Parameter Setting */
	// default unit rental cost : 50
	public static int DefaultUnitRentalCost = 50;
	// default unit demurrage cost : 175 / 100
	public static int DefaultLadenDemurrageCost = 175;
	public static int DefaultEmptyDemurrageCost = 100;
	// default unit loading/discharge/transshipment cost : 20/20/30
	public static int DefaultUnitLoadingCost = 20;
	public static int DefaultUnitDischargeCost = 20;
	public static int DefaultUnitTransshipmentCost = 30;
	public static int DefaultTurnOverTime = 14;
	public static double DefaultFoldContainerPercent = 0.15;
	public static double DefaultFoldEmptyCostBias = 15;
	//////////////////////////////////


	//////////////////////////////////
	// whether show DefaultSetting information
	public static boolean DebugEnable = false;
	// whether show DefaultSetting information in GenerateParameter
	public static boolean GenerateParamEnable = false;
	// whether show DefaultSetting information in subProblem
	public static boolean SubEnable = true;
	// whether show DefaultSetting information in DualProblem
	public static boolean DualEnable = false;
	// whether show DefaultSetting information in DualProblem
	public static boolean DualSubEnable = true;
	// whether show DefaultSetting information in MasterProblem
	public static boolean MasterEnable = false;
	//////////////////////////////////


	//////////////////////////////////
	/* Input Data Settings */
	public static double RequestIncludeRange = 0;
	public static boolean WhetherAllowSameRegionTrans = true;
	public static boolean WhetherCuttingOverCostPaths = true;
	//////////////////////////////////


	//////////////////////////////////
	/* Random Setting */
	// Log-Normal / Uniform / Normal
	public static String distributionType = "Uniform";
	public static Random random;
	public static int randomSeed = 0;
	public static boolean WhetherGenerateSamples = true;
	public static boolean WhetherCalculateMeanPerformance = false;
	public static boolean WhetherWriteSampleTests = true;
	public static boolean WhetherLoadSampleTests = false;
	public static int numSampleScenes = 10;
	public static double log_normal_sigma_factor = 1.0;
	public static double budgetCoefficient = 1.0;
	public static double defaultUncertainDegree = 0.15;
	public static double penaltyCoefficient = 1.0;
	public static int initialEmptyContainers = 28  ;
	//////////////////////////////////


	//////////////////////////////////
	public static boolean WhetherWriteFileLog = false;
	public static boolean WhetherPrintFileLog = false;
	public static boolean WhetherPrintDataStatus = false;
	public static boolean WhetherPrintVesselDecision = false;
	public static boolean WhetherPrintRequestDecision = false;
	public static boolean WhetherPrintIteration = true;
	public static boolean WhetherPrintSolveTime = false;
	public static boolean WhetherPrintProcess = true;
	//////////////////////////////////


	//////////////////////////////////
	/* Cplex Solver Settings */
	// whether export model
	public static boolean WhetherExportModel = false;
	// whether print output log
	public static boolean WhetherCloseOutputLog = true;
	/**
	 * MIP solve Gap limit
	 */
	public static double MIPGapLimit = 1e-3;
	// MIP solve Time limit
	public static double MIPTimeLimit = 36000; //s
	public static int MaxThreads = Runtime.getRuntime().availableProcessors();
	public static long MaxWorkMem = (Runtime.getRuntime().maxMemory() >> 20);
	//////////////////////////////////


	//////////////////////////////////
	/* Algo DefaultSetting*/
	public static int maxIterationNum = 100;
	public static int maxIterationTime = 3600;
	public static double boundGapLimit = 1.0;
	public static boolean WhetherSetInitialSolution = false;
	public static boolean WhetherAddInitializeSce = false;
	public static boolean CCG_PAP_Use_Sp = true;
	public static boolean UseHistorySolution = false;
	//////////////////////////////////


	//////////////////////////////////
	/* Java Programming DefaultSetting */
	public static boolean WhetherUseMultiThreads = false;
	public static int ProgressBarWidth = 50;
	//////////////////////////////////


	//////////////////////////////////
	/* Root path*/
	public static String RootPath = System.getProperty("user.dir") + "/";
	public static String DataPath = "data/";
	public static String CasePath = "1/";
	public static String ExportModelPath = "model/";
	public static String AlgoLogPath = "log/";
	public static String SolutionPath = "solution/";
	public static String TestResultPath = "result/";
	//////////////////////////////////


	//////////////////////////////////

	/**
	 *  print progress bar with percentage in console
	 * @Param : progress length
	 */
	public static void drawProgressBar(int progress) {
		int completedBars = progress * ProgressBarWidth / 100;
		StringBuilder progressBar = new StringBuilder();
		progressBar.append("\r[");

		for (int i = 0; i < ProgressBarWidth; i++) {
			if (i < completedBars) {
				progressBar.append("=");
			} else if (i == completedBars) {
				progressBar.append(">");
			} else {
				progressBar.append("   ");
			}
		}
		progressBar.append("] ").append(progress).append("%");
		// 先清除整行再打印进度条
		progressBar.append("\r");
		System.out.print(progressBar);
		System.out.flush();
	}

	/**
	 * Prints the basic  settings to the experiment
	 */
	public static void printSettings(){
		log.info("======================"+ "Settings" + "======================");
		log.info("FleetType = " + FleetType);
		log.info("VesselType Set = " + VesselCapacityRange);
		log.info("Random Distribution = " + distributionType);
		log.info("MIPGapLimit = " + MIPGapLimit);
		log.info("MIPTimeLimit = " + MIPTimeLimit + "s");
		log.info("MaxThreads = " + MaxThreads);
		log.info("MaxWorkMem = " + MaxWorkMem +"M");
		log.info("NumSampleScenes = " + numSampleScenes);
		log.info("maxIterationNum = " + maxIterationNum);
		log.info("maxIterationTime = " + maxIterationTime +"s");
		log.info("boundGapLimit = " + boundGapLimit);
		log.info("RandomSeed = "+randomSeed);
		log.info("WhetherLoadHistorySolution = " + UseHistorySolution);
		log.info("WhetherAddInitializeSce = " + WhetherAddInitializeSce);
	}

	/**
	 * Writes the basic settings to the experiment
	 * @Params:  fileWriter
	 */
	public static void writeSettings(FileWriter fileWriter) {
		try {
			fileWriter.write("======================"+ "Settings" + "======================\n");
			fileWriter.write("FleetType = " + FleetType + "\n");
			fileWriter.write("VesselType Set = " + VesselCapacityRange + "\n");
			fileWriter.write("Random Distribution = " + distributionType + "\n");
			fileWriter.write("MIPGapLimit = " + MIPGapLimit + "\n");
			fileWriter.write("MIPTimeLimit = " + MIPTimeLimit  + "s" + "\n");
			fileWriter.write("MaxThreads = " + MaxThreads + "\n");
			fileWriter.write("MaxWorkMem = " + MaxWorkMem + "M" + "\n");
			fileWriter.write("NumSampleScenes = " + numSampleScenes + "\n");
			fileWriter.write("maxIterationNum = " + maxIterationNum + "\n");
			fileWriter.write("maxIterationTime = " + maxIterationTime  + "s" + "\n");
			fileWriter.write("boundGapLimit = " + boundGapLimit + "\n");
			fileWriter.write("RandomSeed = "+randomSeed + "\n");
			fileWriter.write("WhetherLoadHistorySolution = " + UseHistorySolution + "\n");
			fileWriter.write("WhetherAddInitializeSce = " + WhetherAddInitializeSce + "\n");
			fileWriter.flush();
		} catch (IOException e) {
			throw new RuntimeException(e);
		}
	}
}
