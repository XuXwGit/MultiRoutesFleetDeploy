package multi;

import java.util.Arrays;
import java.util.List;
import java.util.Objects;

import lombok.Getter;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
public class Scenario {
	public Scenario() {
	}

	public Scenario( double [] request) {
		this.request = request;
	}

	public Scenario( double [] request, int id) {
		this.request = request;
		this.id = id;
	}

	@Getter
	private int id;
	private double [] request;
	private List<Integer> worseRequestSet;
	public double[] getRequest() {
		return request;
	}

	public void setRequest(double[] request) {
		this.request = request;
	}

	public List<Integer> getWorseRequestSet() {
		return worseRequestSet;
	}
	public void setWorseRequestSet(List<Integer> worseRequestSet) {
		this.worseRequestSet = worseRequestSet;
	}

	// Getters and setters
	@Override
	public boolean equals(Object o) {
		if (this == o) {
			return true;
		}
		if (o == null || getClass() != o.getClass()) {
			return false;
		}
		Scenario scenario = (Scenario) o;
		return Arrays.equals(request, scenario.request) &&
				Objects.equals(worseRequestSet, scenario.worseRequestSet);
	}

	@Override
	public int hashCode() {
		return Objects.hash(Arrays.hashCode(request), worseRequestSet);
	}

}
