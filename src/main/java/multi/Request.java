package multi;

public class Request {
	private int requestID;
	private String originPort;
	private String destinationPort;
	private int originGroup;
	private int destinationGroup;
	private int w_i_Earliest;
	private int latestDestinationTime;
	private int[] ladenPaths;
	private int[] ladenPathIndexes;
	private int numberOfLadenPath;
	private int [] emptyPaths;
	private int[] emptyPathIndexes;
	private int numberOfEmptyPath;

	public int getRequestID() {
		return requestID;
	}
	public void setRequestID(int requestID) {
		this.requestID = requestID;
	}
	public String getOriginPort() {
		return originPort;
	}
	public void setOriginPort(String originPort) {
		this.originPort = originPort;
	}
	public String getDestinationPort() {
		return destinationPort;
	}
	public void setDestinationPort(String destinationPort) {
		this.destinationPort = destinationPort;
	}
	
	public int getOriginGroup() {
		return originGroup;
	}
	public void setOriginGroup(int originGroup) {
		this.originGroup = originGroup;
	}
	public int getDestinationGroup() {
		return destinationGroup;
	}
	public void setDestinationGroup(int destinationGroup) {
		this.destinationGroup = destinationGroup;
	}
	
	public int getW_i_Earliest() {
		return w_i_Earliest;
	}
	public void setW_i_Earliest(int w_i_Earliest) {
		this.w_i_Earliest = w_i_Earliest;
	}
	public int getLatestDestinationTime() {
		return latestDestinationTime;
	}
	public void setLatestDestinationTime(int latestDestinationTime) {
		this.latestDestinationTime = latestDestinationTime;
	}
	public int[] getLadenPaths() {
		return ladenPaths;
	}
	public void setLadenPaths(int[] ladenPaths) {
		this.ladenPaths = ladenPaths;
	}
	public int[] getLadenPathIndexes() {
		return ladenPathIndexes;
	}
	public void setLadenPathIndexes(int[] ladenPathIndexes) {
		this.ladenPathIndexes = ladenPathIndexes;
	}
	public int getNumberOfLadenPath() {
		return numberOfLadenPath;
	}
	public void setNumberOfLadenPath(int numberOfLadenPath) {
		this.numberOfLadenPath = numberOfLadenPath;
	}
	public int[] getEmptyPaths() {
		return emptyPaths;
	}
	public void setEmptyPaths(int[] emptyPaths) {
		this.emptyPaths = emptyPaths;
	}
	public int[] getEmptyPathIndexes() {
		return emptyPathIndexes;
	}
	public void setEmptyPathIndexes(int[] emptyPathIndexes) {
		this.emptyPathIndexes = emptyPathIndexes;
	}
	public int getNumberOfEmptyPath() {
		return numberOfEmptyPath;
	}
	public void setNumberOfEmptyPath(int numberOfEmptyPath) {
		this.numberOfEmptyPath = numberOfEmptyPath;
	}
	
	


}
