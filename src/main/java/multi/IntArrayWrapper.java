package multi;

import java.util.Arrays;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
public class IntArrayWrapper {
    private final int[] array;

    public IntArrayWrapper(int[] array) {
        this.array = array;
    }

    public int[] getArray() {
        return array;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        IntArrayWrapper that = (IntArrayWrapper) o;
        return Arrays.equals(array, that.array);
    }

    @Override
    public int hashCode() {
        return Arrays.hashCode(array);
    }

    public static double[] IntArrayToDoubleArray(int[] intArray) {
        double[] doubleArray = new double[intArray.length];

        for (int i = 0; i < intArray.length; i++) {
            doubleArray[i] = intArray[i];
        }
        return doubleArray;
    }
}
