package multi;

import java.util.Arrays;

/**
 * @Author: XuXw
 * @Description: Todo
 * @DateTime: 2024/12/4 21:54
 */
public class IntArray2DWrapper {
    private final int[][] array2D;

    public IntArray2DWrapper(int[][] array2D) {
        this.array2D = array2D;
    }

    public int[][] getArray2D() {
        return array2D;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        IntArray2DWrapper that = (IntArray2DWrapper) o;
        return Arrays.deepEquals(array2D, that.array2D);
    }

    @Override
    public int hashCode() {
        return Arrays.deepHashCode(array2D);
    }


    public static double[][] Int2DArrayToDouble2DArray(int[][] intArray) {
        int rows = intArray.length;
        int cols = intArray[0].length;
        double[][] doubleArray = new double[rows][cols];

        for (int i = 0; i < rows; i++) {
            for (int j = 0; j < cols; j++) {
                doubleArray[i][j] = (double) intArray[i][j];
            }
        }

        return doubleArray;
    }

}
