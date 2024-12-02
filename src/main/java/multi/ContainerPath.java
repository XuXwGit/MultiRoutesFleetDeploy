package multi;

public class ContainerPath {
	private int ContainerPathID;
	private String originPort;
	private int originTime;
	private String destinationPort;
	private int destinationTime;
	private int pathTime;
	private String[] transshipment_port;
	private int[] transshipment_Time;
	private int totalTransshipTime;
	
	private int numberOfPath;
	private String [] port_Path;

	private int numberOfArcs;
	private int [] arcs_ID;
	private double path_cost;


	public double getPathCost() {
		return path_cost;
	}

	public void setPathCost(double path_cost) {
		this.path_cost = path_cost;
	}
	public int getContainerPathID() {
		return ContainerPathID;
	}
	public void setContainerPathID(int containerPathID) {
		this.ContainerPathID = containerPathID;
	}
	public String getOriginPort() {
		return originPort;
	}
	public void setOriginPort(String originPort) {
		this.originPort = originPort;
	}
	public int getOriginTime() {
		return originTime;
	}
	public void setOriginTime(int originTime) {
		this.originTime = originTime;
	}
	public String getDestinationPort() {
		return destinationPort;
	}
	public void setDestinationPort(String destinationPort) {
		this.destinationPort = destinationPort;
	}
	public int getDestinationTime() {
		return destinationTime;
	}
	public void setDestinationTime(int destinationTime) {
		this.destinationTime = destinationTime;
	}
	public int getPathTime() {
		return pathTime;
	}
	public void setPathTime(int pathTime) {
		this.pathTime = pathTime;
	}
	public String[] getTransshipment_port() {
		return transshipment_port;
	}
	public void setTransshipment_port(String[] transshipment_port) {
		this.transshipment_port = transshipment_port;
	}
	public int[] getTransshipment_Time() {
		return transshipment_Time;
	}
	private void setTotalTransshipTime(int totalTransshipTime)
	{
		this.totalTransshipTime = totalTransshipTime;
	}
	public int getTotalTransshipment_Time()
	{
		int total_transshipment_Time = 0;
		if(transshipment_port == null)
		{
			setTotalTransshipTime(0);
		}
		else
		{
			for (int i = 0; i < transshipment_port.length; i++)
			{
				total_transshipment_Time += transshipment_Time[i];
			}
			setTotalTransshipTime(total_transshipment_Time);
		}
		return totalTransshipTime;
	}
	public int getTotalDemurrageTime()
	{
		int total_transshipment_Time = 0;
		int total_demurrage_Time = 0;
		if(transshipment_port == null)
		{
			setTotalTransshipTime(0);
			return 0;
		}
		else
		{
			if(transshipment_port.length != transshipment_Time.length){
				System.out.println("Error in transshipment port num!");
			}
			for (int i = 0; i < transshipment_port.length; i++)
			{
				total_transshipment_Time += transshipment_Time[i];
				if (transshipment_Time[i] > 7){
					total_demurrage_Time += (transshipment_Time[i] - 7);
				}
			}
			setTotalTransshipTime(total_transshipment_Time);
		}
		return total_demurrage_Time;
	}
	public void setTransshipment_Time(int[] transshipment_Time) {
		this.transshipment_Time = transshipment_Time;
	}
	public int getNumberofPath() {
		return numberOfPath;
	}
	public void setNumberofPath(int numberofPath) {
		this.numberOfPath = numberofPath;
	}
	public String[] getPort_Path() {
		return port_Path;
	}
	public void setPortPath(String[] port_Path) {
		this.port_Path = port_Path;
	}
	public int getNumberOfArcs() {
		return numberOfArcs;
	}
	public void setNumberOfArcs(int numberOfArcs) {
		this.numberOfArcs = numberOfArcs;
	}
	public int[] getArcsID() {
		return arcs_ID;
	}
	public void setArcsID(int[] arcs_ID) {
		this.arcs_ID = arcs_ID;
	}
}
