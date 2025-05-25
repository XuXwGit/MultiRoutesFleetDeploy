"""
@Author: XuXw
@Description: 整数数组包装类，对应Java版本IntArrayWrapper.java
@DateTime: 2024/12/4 21:54
"""
from typing import List
import numpy as np


class IntArrayWrapper:
    """
    整数数组包装类
    对应Java类: multi.IntArrayWrapper
    
    提供整数数组的转换功能
    """
    
    @staticmethod
    def int_array_to_double_array(int_array: List[int]) -> List[float]:
        """
        将整数数组转换为浮点数数组
        对应Java: public static double[] intArrayToDoubleArray(int[] array)
        
        Args:
            int_array: 整数数组
            
        Returns:
            List[float]: 转换后的浮点数数组
        """
        if int_array is None:
            return []
        
        # 使用NumPy高效转换
        return np.array(int_array, dtype=float).tolist()
    
    @staticmethod
    def int_array_to_boolean_array(int_array: List[int]) -> List[bool]:
        """
        将整数数组转换为布尔数组
        对应Java: public static boolean[] intArrayToBooleanArray(int[] array)
        
        Args:
            int_array: 整数数组
            
        Returns:
            List[bool]: 转换后的布尔数组
        """
        if int_array is None:
            return []
        
        # 使用列表推导式转换
        return [val != 0 for val in int_array] 