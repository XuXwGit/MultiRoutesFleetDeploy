package multi;

import lombok.extern.slf4j.Slf4j;
import multi.network.Request;

import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SelectPaths extends DefaultSetting {
    private InputData in;
    private Parameter p;
    private double reducePathPercentage;
    private int maxLadenPathsNum = DefaultSetting.MaxLadenPathsNum;
    private int maxEmptyPathsNum = DefaultSetting.MaxEmptyPathsNum;


    public SelectPaths(InputData in, Parameter p)
    {
        super();
        this.in = in;
        this.p = p;
        this.reducePathPercentage = DefaultSetting.reducePathPercentage;
        frame();
    }

    public SelectPaths(InputData in, Parameter p, double reducePathPercentage)
    {
        super();
        this.in = in;
        this.p = p;
        this.reducePathPercentage = reducePathPercentage;
        frame();
    }

    public SelectPaths(InputData in, Parameter p, int maxLadenPathsNum, int maxEmptyPathsNum)
    {
        super();
        this.in = in;
        this.p = p;
        this.maxLadenPathsNum = maxLadenPathsNum;
        this.maxEmptyPathsNum = maxEmptyPathsNum;
        frame();
    }

    private void frame() {
        log.info("After Selecting Paths : ");

        reRankContainerPaths();

        // reduce: total path cost > penalty cost
        if( WhetherCuttingOverCostPaths ) {
            reduceOverCostPaths();
        }


        reduceContainerPaths(reducePathPercentage);
        // randomSelectPaths(maxLadenPathsNum, maxEmptyPathsNum);
    }

    private void reRankContainerPaths(){
        List<Request> requestSet = in.getRequestSet();
        for (int i = 0; i < requestSet.size(); i++) {
            Request request = requestSet.get(i);

            // For laden paths
            int[] laden_paths = request.getLadenPaths();
            int[] laden_indexes = request.getLadenPathIndexes();
            if(laden_paths != null){
                double[] laden_costs = new double[laden_paths.length];
                for (int j = 0; j < laden_paths.length; j++) {
                    laden_costs[j] = p.getLadenPathCost()[laden_indexes[j]];
                }

                Integer[] new_laden_indexes = new Integer[laden_paths.length];
                for (int j = 0; j < laden_paths.length; j++) {
                    new_laden_indexes[j] = j;
                }
                Arrays.sort(new_laden_indexes, Comparator.comparingDouble(index -> laden_costs[index]));

                // 根据排序结果重新排列laden_paths和laden_indexes
                int[] sorted_laden_paths = new int[laden_paths.length];
                int[] sorted_laden_indexes = new int[laden_paths.length];
                for (int j = 0; j < new_laden_indexes.length; j++) {
                    sorted_laden_paths[j] = laden_paths[new_laden_indexes[j]];
                    sorted_laden_indexes[j] = laden_indexes[new_laden_indexes[j]];
                }
                request.setLadenPaths(sorted_laden_paths);
                request.setLadenPathIndexes(sorted_laden_indexes);
            }

            // For empty paths
            int[] empty_paths = request.getEmptyPaths();
            int[] empty_indexes = request.getEmptyPathIndexes();
            if(empty_paths != null){
                double[] empty_costs = new double[empty_paths.length];
                for (int j = 0; j < empty_paths.length; j++) {
                    empty_costs[j] = p.getEmptyPathCost()[empty_indexes[j]];
                }

                Integer[] new_empty_indexes = new Integer[empty_paths.length];
                for (int j = 0; j < empty_paths.length; j++) {
                    new_empty_indexes[j] = j;
                }
                Arrays.sort(new_empty_indexes, Comparator.comparingDouble(index -> empty_costs[index]));

                // 根据排序结果重新排列empty_paths和empty_indexes
                int[] sorted_empty_paths = new int[empty_paths.length];
                int[] sorted_empty_indexes = new int[empty_paths.length];
                for (int j = 0; j < new_empty_indexes.length; j++) {
                    sorted_empty_paths[j] = empty_paths[new_empty_indexes[j]];
                    sorted_empty_indexes[j] = empty_indexes[new_empty_indexes[j]];
                }
                request.setEmptyPaths(sorted_empty_paths);
                request.setEmptyPathIndexes(sorted_empty_indexes);
            }

            requestSet.set(i, request);
        }

        in.setRequestSet(requestSet);
        // in.showPathStatus();
    }

    private void reduceContainerPaths(double percent){
        List<Request> requestSet = in.getRequestSet();
        for (int i = 0; i < requestSet.size(); i++) {
            Request request = requestSet.get(i);

            int numberOfLadenPath = request.getNumberOfLadenPath();
            int numberOfEmptyPath = request.getNumberOfEmptyPath();

            int[] ladenPaths = request.getLadenPaths();
            int[] emptyPaths = request.getEmptyPaths();
            int[] ladenPathIndexes = request.getLadenPathIndexes();
            int[] emptyPathIndexes = request.getEmptyPathIndexes();

            int newNumLaden = (int) Math.ceil(numberOfLadenPath * (1 - percent));
            int newNumEmpty = (int) Math.ceil(numberOfEmptyPath * (1 - percent));

            request.setNumberOfLadenPath(newNumLaden);
            request.setNumberOfEmptyPath(newNumEmpty);

            if(newNumLaden > 0 ){
                request.setLadenPaths(Arrays.copyOfRange(ladenPaths, 0, newNumLaden));
                request.setLadenPathIndexes(Arrays.copyOfRange(ladenPathIndexes, 0, newNumLaden));
            }

            if(newNumEmpty > 0){
                request.setEmptyPaths(Arrays.copyOfRange(emptyPaths, 0, newNumEmpty));
                request.setEmptyPathIndexes(Arrays.copyOfRange(emptyPathIndexes, 0, newNumEmpty));
            }

            requestSet.set(i, request);
        }

        in.setRequestSet(requestSet);
        in.showPathStatus();
    }
    private void reduceOverCostPaths(){
        List<Request> requestSet = in.getRequestSet();
        for (int i = 0; i < requestSet.size(); i++) {
            Request request = requestSet.get(i);

            double penaltyCost = p.getPenaltyCostForDemand()[i];

            // cut laden paths
            int longestTransTime = 0;
            int numberOfLadenPath = request.getNumberOfLadenPath();
            int[] ladenPaths = request.getLadenPaths();
            int[] ladenPathIndexes = request.getLadenPathIndexes();
            for (int pathIndex = 0; pathIndex < numberOfLadenPath; pathIndex++) {
                int j = ladenPathIndexes[pathIndex];
                if(p.getLadenPathCost()[j] >= penaltyCost){

                    ladenPaths[pathIndex] = ladenPaths[numberOfLadenPath - 1];
                    ladenPathIndexes[pathIndex] = ladenPathIndexes[numberOfLadenPath - 1];
                    numberOfLadenPath --;
                    pathIndex --;
                }
                else {
                    if(p.getTravelTimeOnPath()[j] > longestTransTime){
                        longestTransTime = p.getTravelTimeOnPath()[j];
                    }
                }
            }
            if(numberOfLadenPath != request.getNumberOfLadenPath()){
                request.setNumberOfLadenPath(numberOfLadenPath);
                request.setLadenPaths(Arrays.copyOfRange(ladenPaths, 0, numberOfLadenPath));
                request.setLadenPathIndexes(Arrays.copyOfRange(ladenPathIndexes, 0, numberOfLadenPath));
            }


            // cut empty paths
            int numberOfEmptyPath = request.getNumberOfEmptyPath();
            int[] emptyPaths = request.getEmptyPaths();
            int[] emptyPathIndexes = request.getEmptyPathIndexes();
            for (int pathIndex = 0; pathIndex < numberOfEmptyPath; pathIndex++) {
                int j = emptyPathIndexes[pathIndex];
                if(p.getEmptyPathCost()[j] >= penaltyCost || p.getEmptyPathCost()[j] > p.getRentalCost() * longestTransTime){
                    emptyPaths[pathIndex] = emptyPaths[numberOfEmptyPath - 1];
                    emptyPathIndexes[pathIndex] = emptyPathIndexes[numberOfEmptyPath - 1];
                    numberOfEmptyPath --;
                    pathIndex --;
                }
            }
            if(numberOfEmptyPath != request.getNumberOfEmptyPath()){
                        request.setNumberOfEmptyPath(numberOfEmptyPath);
                        request.setEmptyPaths(Arrays.copyOfRange(emptyPaths, 0, numberOfEmptyPath));
                        request.setEmptyPathIndexes(Arrays.copyOfRange(emptyPathIndexes, 0, numberOfEmptyPath));
            }

            requestSet.set(i, request);
        }

        in.setRequestSet(requestSet);
        in.showPathStatus();
    }
}
