package multi;

public class EmptyPath {
	private int request_ID;
	private String origin_Port;
	private int origin_time;
	private int numberofPath;
	private int [] path_ID;
	public int getRequestID() {
		return request_ID;
	}
	public void setRequestID(int request_ID) {
		this.request_ID = request_ID;
	}
	public String getOriginPort() {
		return origin_Port;
	}
	public void setOriginPort(String origin_Port) {
		this.origin_Port = origin_Port;
	}
	public int getOriginTime() {
		return origin_time;
	}
	public void setOriginTime(int origin_time) {
		this.origin_time = origin_time;
	}
	public int getNumberofPath() {
		return numberofPath;
	}
	public void setNumberofPath(int numberofPath) {
		this.numberofPath = numberofPath;
	}
	public int[] getPathID() {
		return path_ID;
	}
	public void setPathID(int[] path_ID) {
		this.path_ID = path_ID;
	}
	


}
