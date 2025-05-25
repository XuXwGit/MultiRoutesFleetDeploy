"""
@Author: XuXw
@Description: 二维整数数组包装类，对应Java版本IntArray2DWrapper.java
@DateTime: 2024/12/4 21:54
"""
from typing import List
import numpy as np


class IntArray2DWrapper:
    """
    二维整数数组包装类
    对应Java类: multi.IntArray2DWrapper
    
    提供二维整数数组的转换功能
    """
    
    @staticmethod
    def int_2d_array_to_double_2d_array(int_array_2d: List[List[int]]) -> List[List[float]]:
        """
        将二维整数数组转换为二维浮点数数组
        对应Java: public static double[][] int2DArrayToDouble2DArray(int[][] array)
        
        Args:
            int_array_2d: 二维整数数组
            
        Returns:
            List[List[float]]: 转换后的二维浮点数数组
        """
        if int_array_2d is None:
            return []
        
        # 使用NumPy高效转换
        return np.array(int_array_2d, dtype=float).tolist()
    
    @staticmethod
    def int_2d_array_to_boolean_2d_array(int_array_2d: List[List[int]]) -> List[List[bool]]:
        """
        将二维整数数组转换为二维布尔数组
        对应Java: public static boolean[][] int2DArrayToBoolean2DArray(int[][] array)
        
        Args:
            int_array_2d: 二维整数数组
            
        Returns:
            List[List[bool]]: 转换后的二维布尔数组
        """
        if int_array_2d is None:
            return []
        
        # 使用列表推导式转换
        return [[val != 0 for val in row] for row in int_array_2d] 