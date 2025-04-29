package multi.algos.BD;

import ilog.concert.IloException;
import lombok.extern.slf4j.Slf4j;
import multi.*;
import multi.algos.AlgoFrame;
import multi.model.primal.MasterProblem;

import java.io.IOException;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
@Slf4j
public class SOwithSAA extends AlgoFrame {
    public SOwithSAA(InputData in, Parameter p) throws IloException, IOException {
        super();
        this.in = in;
        this.p = p;
        this.tau = p.getTau();
        this.Algo = "SO&SAA";
        this.AlgoID = Algo + "-R"+ in.getShipRouteSet().size() 
                                        + "-T" + p.getTimeHorizon() 
                                        + "-"+ DefaultSetting.FleetType 
                                        + "-S" + DefaultSetting.randomSeed 
                                        + "-V" + DefaultSetting.VesselCapacityRange;
        frame();
    }

    public SOwithSAA() {
    }
    @Override
    protected double initialModel() throws IloException, IOException {
        start = System.currentTimeMillis();

        mp=new MasterProblem(in, p, "Stochastic");

        for(int i=0; i<p.getSampleScenes().length; i++){
            mp.addScene(in.getScenarios().get(i));
        }

        return System.currentTimeMillis() - start;
    }
    @Override
    protected void frame() throws IOException, IloException {
        initialize();

        initialModel();

        mp.solveModel();

        setAlgoResult();
        end();
    }

    @Override
    protected void endModel() {
        mp.end();
    }
}
