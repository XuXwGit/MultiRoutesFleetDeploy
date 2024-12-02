package multi;

import java.util.ArrayList;
import java.util.List;

public class CuttingPaths {
	private InputData in;
	private Parameter p;

	public CuttingPaths(InputData in, Parameter p)
	{
		super();
		this.in = in;
		this.p = p;
		frame();
	}

	private void frame()
	{
//		reduceLongEmptyPath();

		reduceTransshippingPaths();

		reduceEmptyPaths();

		cutRequests();

		reCalculatePaths();
	}

	// 有问题
	private void reduceLongEmptyPath()
	{
		for (int i = 0; i < in.getRequestSet().size(); i++)
		{
			Request request = in.getRequestSet().get(i);
			int flag = 0;

			// 0/1
			if(request.getNumberOfEmptyPath() <= 1)
				continue;

			// 仅保留用时最短的EmptyPath
			int[] newEmptyPaths = new int[1];
			int[] newEmptyPathIndexes = new int[1];
			newEmptyPaths[0] = request.getEmptyPaths()[0];
			newEmptyPathIndexes[0] = request.getEmptyPathIndexes()[0];

			int shortestPathIndex = request.getEmptyPathIndexes()[0];
			for (int j = 1; j < request.getEmptyPathIndexes().length; j++) {
				int index = request.getEmptyPathIndexes()[j];
				if (in.getContainerPathSet().get(index).getPathTime() <= in.getContainerPathSet().get(shortestPathIndex).getPathTime())
				{
					newEmptyPaths[0] = request.getEmptyPaths()[j];
					newEmptyPathIndexes[0] = index;
					flag = 1;
				}
			}

			if(flag == 1)
			{
				int[] newEmptyID = new int[1];
				int[] newEmptyIndex = new int[1];
				for (int k = 0; k < 1; k++) {
					newEmptyID[k] = newEmptyPaths[k];
					newEmptyIndex[k] = newEmptyPathIndexes[k];
					in.getRequestSet().get(i).setEmptyPaths(newEmptyID);
					in.getRequestSet().get(i).setEmptyPathIndexes(newEmptyIndex);
				}
				in.getRequestSet().get(i).setNumberOfEmptyPath(1);
			}
		}
	}

	// 仅保留直达Path
	private void reduceTransshippingPaths()
	{
		for (int i = 0; i < in.getRequestSet().size(); i++)
		{
			Request request = in.getRequestSet().get(i);

			if(request.getNumberOfLadenPath() == 0)
				continue;

			int[] newLadenPaths = new int[request.getLadenPaths().length];
			int[] newLadenPathIndexes = new int[request.getLadenPaths().length];
			int newNumLadenPaths = 0;
			int flag = 0;

			for (int j = 0; j < request.getLadenPathIndexes().length; j++) {
				int index = request.getLadenPathIndexes()[j];
				if (in.getContainerPathSet().get(index).getTransshipment_port() == null)
				{
					newLadenPaths[newNumLadenPaths] = request.getLadenPaths()[j];
					newLadenPathIndexes[newNumLadenPaths] = index;
					newNumLadenPaths++;
					flag = 1;
				}
			}

			if(flag == 1&& newNumLadenPaths < request.getNumberOfLadenPath())
			{
				int[] newLadenID = new int[newNumLadenPaths];
				int[] newLadenIndex = new int[newNumLadenPaths];
				for (int k = 0; k < newNumLadenPaths; k++) {
					newLadenID[k] = newLadenPaths[k];
					newLadenIndex[k] = newLadenPathIndexes[k];
					in.getRequestSet().get(i).setLadenPaths(newLadenID);
					in.getRequestSet().get(i).setLadenPathIndexes(newLadenIndex);
				}
				in.getRequestSet().get(i).setNumberOfLadenPath(newNumLadenPaths);
			}
		}
	}

	// 将重定向到“进口型”港口的Request的可选EmptyPath数量置为0
	private void reduceEmptyPaths()
	{
		int[] min_importContainers = new int[in.getPortSet().size()];
		int[] max_exportContainers = new int[in.getPortSet().size()];

		// 计算各个港口的总流入量与总流出量
		for (int i = 0; i < in.getRequestSet().size(); i++) {
			String origin = in.getRequestSet().get(i).getOriginPort();
			String destination = in.getRequestSet().get(i).getDestinationPort();

			for (int j = 0; j < in.getPortSet().size(); j++) {
				if (in.getPortSet().get(j).getPort().equals(origin))
				{
					max_exportContainers[j] += p.getDemand()[i] + p.getMaximumDemandVariation()[i];
				}
				if(in.getPortSet().get(j).getPort().equals(destination))
				{
					min_importContainers[j] += p.getDemand()[i];
				}
			}
		}

		for (int i = 0; i < in.getPortSet().size(); i++) {
			if(max_exportContainers[i] <= min_importContainers[i])
			{
				for (int j = 0; j < in.getRequestSet().size(); j++) {
					if (in.getRequestSet().get(j).getOriginPort().equals(in.getPortSet().get(i).getPort()))
					{
						in.getRequestSet().get(j).setEmptyPaths(null);
						in.getRequestSet().get(j).setEmptyPathIndexes(null);
						in.getRequestSet().get(j).setNumberOfEmptyPath(0);
					}
				}
			}
		}
	}

	// 仅保留不同区域间的Request
	private void cutRequests()
	{
		List<Request> newRequestSet = new ArrayList<>();
		double[] tempDemands = new double[p.getDemand().length];
		double[] tempMaxVarDemands = new double[p.getDemand().length];
		int newNumOfRequests = 0;
		for (int i = 0; i < in.getRequestSet().size(); i++) {
			Request request = in.getRequestSet().get(i);
			if(request.getOriginGroup() != request.getDestinationGroup())
			{
				newRequestSet.add(request);
				tempDemands[newNumOfRequests] = p.getDemand()[i];
				tempMaxVarDemands[newNumOfRequests] = p.getMaximumDemandVariation()[i];
				newNumOfRequests++;
			}
		}

		double[] newDemands = new double[newNumOfRequests];
		double[] newMaxVarDemands = new double[newNumOfRequests];
		for (int i = 0; i < newNumOfRequests; i++) {
			newDemands[i] = tempDemands[i];
			newMaxVarDemands[i] = tempMaxVarDemands[i];
		}

		// update Request Set
		in.setRequestSet(newRequestSet);
		p.setDemand(newDemands);
		p.setMaximumDemandVariation(newMaxVarDemands);
		//System.out.println("The number of Requests after Cutting Requests between same group: "+ in.getRequestSet().size());
	}

	private void reCalculatePaths()
	{
		int numOfPaths = 0;
		List<ContainerPath> newPaths = new ArrayList<>();

		// 由于减少Request而导致减少的Path
		for (int i = 0; i < in.getRequestSet().size(); i++)
		{
			int[] newLadenIndexes = new int[in.getRequestSet().get(i).getNumberOfLadenPath()];

			for (int j = 0; j < in.getRequestSet().get(i).getNumberOfLadenPath(); j++) {
				int index = in.getRequestSet().get(i).getLadenPathIndexes()[j];
				ContainerPath tempPath = in.getContainerPathSet().get(index);
				newPaths.add(tempPath);
				newLadenIndexes[j] = numOfPaths;
				numOfPaths++;
			}

			in.getRequestSet().get(i).setLadenPathIndexes(newLadenIndexes);
		}

		in.setContainerPathSet(newPaths);

		// update empty paths
		for (int i = 0; i < in.getRequestSet().size(); i++) {
			Request request = in.getRequestSet().get(i);

			if(request.getNumberOfEmptyPath() == 0)
				continue;

			int newNumOfEmptyPaths = 0;

			for (int j = 0; j < request.getNumberOfEmptyPath(); j++) {
				int tempPathID = request.getEmptyPaths()[j];
				for (int k = 0; k < in.getContainerPathSet().size(); k++) {
					if (in.getContainerPathSet().get(k).getContainerPathID() == tempPathID)
					{
						in.getRequestSet().get(i).getEmptyPaths()[newNumOfEmptyPaths] = tempPathID;
						in.getRequestSet().get(i).getEmptyPathIndexes()[newNumOfEmptyPaths] = k;
						newNumOfEmptyPaths++;
						break;
					}
				}
			}

			int[] newEmptyPaths = new int[newNumOfEmptyPaths];
			int[] newEmptyPathIndexes = new int[newNumOfEmptyPaths];

			for (int j = 0; j < newNumOfEmptyPaths; j++) {
				newEmptyPaths[j] = in.getRequestSet().get(i).getEmptyPaths()[j];
				newEmptyPathIndexes[j] = in.getRequestSet().get(i).getEmptyPathIndexes()[j];
			}

			in.getRequestSet().get(i).setNumberOfEmptyPath(newNumOfEmptyPaths);
			in.getRequestSet().get(i).setEmptyPaths(newEmptyPaths);
			in.getRequestSet().get(i).setEmptyPathIndexes(newEmptyPathIndexes);
		}

		// update cost
		// calculate total demurrage for each path
		// demurrage = sum{transshipTime * unit demurrage}
		// arcAndPath : arcs X paths
		// arcAndPath[arc][path] == 1 : the travel arc is in path arcs
		double [] ladenPathDemurrageCost=new double [in.getContainerPathSet().size()];
		double [] emptyPathDemurrageCost=new double [in.getContainerPathSet().size()];
		int [] travelTimeOnPath=new int [in.getContainerPathSet().size()];
		int [] pathSet =new int [in.getContainerPathSet().size()];
		int [][] arcAndPath  =new int [in.getTravelingArcSet().size()][in.getContainerPathSet().size()];
		int x=0;
		for(ContainerPath pp :in.getContainerPathSet())
		{
/*			ladenPathDemurrageCost[x]=175*pp.getTotalTransshipment_Time();
			emptyPathDemurrageCost[x]=100*pp.getTotalTransshipment_Time();*/
			// why - 7 ?
			ladenPathDemurrageCost[x]=Math.max(0, 175*(pp.getTotalTransshipment_Time()-7));
			emptyPathDemurrageCost[x]=Math.max(0, 100*(pp.getTotalTransshipment_Time()-7));

			travelTimeOnPath[x]=pp.getPathTime();
			pathSet[x]=pp.getContainerPathID();

			for (int i = 0; i < in.getTravelingArcSet().size(); i++) {
				arcAndPath[i][x] = 0;
				for (int j = 0; j < pp.getArcsID().length; j++) {
					if(in.getTravelingArcSet().get(i).getTravelingArc_ID() == pp.getArcsID()[j])
					{
						arcAndPath[i][x] = 1;
					}
				}
			}
			++x;
		}

		p.setLadenPathDemurrageCost(ladenPathDemurrageCost);
		p.setEmptyPathDemurrageCost(emptyPathDemurrageCost);
		p.setTravelTimeOnPath(travelTimeOnPath);
		p.setPathSet(pathSet);
		p.setArcAndPath(arcAndPath);
	}

}
