"""
@Author: XuXw
@Description: 浮点数数组包装类，对应Java版本DoubleArrayWrapper.java
@DateTime: 2024/12/4 21:54
"""
from typing import List
import numpy as np


class DoubleArrayWrapper:
    """
    浮点数数组包装类
    对应Java类: multi.DoubleArrayWrapper
    
    提供浮点数数组的转换功能
    """
    
    @staticmethod
    def double_array_to_int_array(double_array: List[float]) -> List[int]:
        """
        将浮点数数组转换为整数数组
        对应Java: public static int[] doubleArrayToIntArray(double[] array)
        
        Args:
            double_array: 浮点数数组
            
        Returns:
            List[int]: 转换后的整数数组
        """
        if double_array is None:
            return []
        
        # 使用NumPy高效转换
        return np.array(double_array, dtype=int).tolist()
    
    @staticmethod
    def round_array(double_array: List[float], precision: int = 0) -> List[float]:
        """
        对浮点数数组进行四舍五入
        对应Java: public static double[] roundArray(double[] array, int precision)
        
        Args:
            double_array: 浮点数数组
            precision: 精度（小数位数），默认为0
            
        Returns:
            List[float]: 四舍五入后的浮点数数组
        """
        if double_array is None:
            return []
        
        # 使用NumPy高效转换
        return np.round(double_array, precision).tolist() 