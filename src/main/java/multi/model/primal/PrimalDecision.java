package multi.model.primal;

import java.util.List;

import ilog.concert.IloNumVar;

public class PrimalDecision {
    protected List<IloNumVar[]> xVar;
    protected List<IloNumVar[]> yVar;
    protected List<IloNumVar[]> zVar;
    protected IloNumVar[] gVar;
}