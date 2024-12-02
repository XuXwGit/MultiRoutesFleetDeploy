package multi;

import java.util.Arrays;
import java.util.Comparator;
import java.util.List;

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
        System.out.println("After Selecting Paths : ");

        reRankContainerPaths();

        // reduce: total path cost > penalty cost
        if( WhetherCuttingOverCostPaths )
            reduceOverCostPaths();


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

            int num_laden = request.getNumberOfLadenPath();
            int num_empty = request.getNumberOfEmptyPath();

            int[] laden_paths = request.getLadenPaths();
            int[] empty_paths = request.getEmptyPaths();
            int[] laden_indexes = request.getLadenPathIndexes();
            int[] empty_indexes = request.getEmptyPathIndexes();

            int new_num_laden = (int) Math.ceil(num_laden * (1 - percent));
            int new_num_empty = (int) Math.ceil(num_empty * (1 - percent));

            request.setNumberOfLadenPath(new_num_laden);
            request.setNumberOfEmptyPath(new_num_empty);

            if(new_num_laden > 0 ){
                request.setLadenPaths(Arrays.copyOfRange(laden_paths, 0, new_num_laden));
                request.setLadenPathIndexes(Arrays.copyOfRange(laden_indexes, 0, new_num_laden));
            }

            if(new_num_empty > 0){
                request.setEmptyPaths(Arrays.copyOfRange(empty_paths, 0, new_num_empty));
                request.setEmptyPathIndexes(Arrays.copyOfRange(empty_indexes, 0, new_num_empty));
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

            double penalty_cost = p.getPenaltyCostForDemand()[i];

            // cut laden paths
            int longest_trans_time = 0;
            int num_laden = request.getNumberOfLadenPath();
            int[] laden_paths = request.getLadenPaths();
            int[] laden_indexes = request.getLadenPathIndexes();
            for (int path_index = 0; path_index < num_laden; path_index++) {
                int j = laden_indexes[path_index];
                if(p.getLadenPathCost()[j] >= penalty_cost){

                    laden_paths[path_index] = laden_paths[num_laden - 1];
                    laden_indexes[path_index] = laden_indexes[num_laden - 1];
                    num_laden --;
                    path_index --;
                }
                else {
                    if(p.getTravelTimeOnPath()[j] > longest_trans_time){
                        longest_trans_time = p.getTravelTimeOnPath()[j];
                    }
                }
            }
            if(num_laden != request.getNumberOfLadenPath()){
                request.setNumberOfLadenPath(num_laden);
                request.setLadenPaths(Arrays.copyOfRange(laden_paths, 0, num_laden));
                request.setLadenPathIndexes(Arrays.copyOfRange(laden_indexes, 0, num_laden));
            }


            // cut empty paths
            int num_empty = request.getNumberOfEmptyPath();
            int[] empty_paths = request.getEmptyPaths();
            int[] empty_indexes = request.getEmptyPathIndexes();
            for (int path_index = 0; path_index < num_empty; path_index++) {
                int j = empty_indexes[path_index];
                if(p.getEmptyPathCost()[j] >= penalty_cost || p.getEmptyPathCost()[j] > p.getRentalCost() * longest_trans_time){
                    empty_paths[path_index] = empty_paths[num_empty - 1];
                    empty_indexes[path_index] = empty_indexes[num_empty - 1];
                    num_empty --;
                    path_index --;
                }
            }
            if(num_empty != request.getNumberOfEmptyPath()){
                        request.setNumberOfEmptyPath(num_empty);
                        request.setEmptyPaths(Arrays.copyOfRange(empty_paths, 0, num_empty));
                        request.setEmptyPathIndexes(Arrays.copyOfRange(empty_indexes, 0, num_empty));
            }

            /*System.out.println("Request :" + i+ ": " + request.getNumberOfLadenPath() + " " + request.getNumberOfEmptyPath());
            System.out.print(penalty_cost + ">");
            for (int j = 0; j < request.getLadenPathIndexes().length; j++) {
                System.out.print(p.getLadenPathCost()[request.getLadenPathIndexes()[j]] + "\t");
            }
            System.out.println();*/

            requestSet.set(i, request);
        }

        in.setRequestSet(requestSet);
        in.showPathStatus();
    }
}
