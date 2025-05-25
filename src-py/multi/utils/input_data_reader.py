"""
@Author: XuXw
@Description: 输入数据读取类，对应Java版本InputDataReader.java
@DateTime: 2024/12/4 21:54
"""
import os
from typing import List, Union
import numpy as np


class InputDataReaderException(Exception):
    """
    输入数据读取异常
    对应Java类: multi.InputDataReader.InputDataReaderException
    """
    
    def __init__(self, file_name: str):
        """
        初始化异常
        
        Args:
            file_name: 引发异常的文件名
        """
        super().__init__(f"格式错误或读取数据出错: {file_name}")
        self.file_name = file_name


class InputDataReader:
    """
    输入数据读取类
    对应Java类: multi.InputDataReader
    
    提供从文本文件读取数值数据的功能
    """
    
    def __init__(self, file_name: str):
        """
        初始化数据读取器
        
        Args:
            file_name: 数据文件路径
        
        Raises:
            FileNotFoundError: 文件不存在时抛出
        """
        self.file_name = file_name
        # 检查文件是否存在
        if not os.path.exists(file_name):
            raise FileNotFoundError(f"文件不存在: {file_name}")
        
        # 读取文件内容
        with open(file_name, 'r') as file:
            self.content = file.read()
        
        # 清理内容（移除注释和空行）
        self._clean_content()
        
        # 将内容分割为标记
        self.tokens = self.content.split()
        self.token_index = 0
    
    def _clean_content(self):
        """清理文件内容，移除注释和空白行"""
        lines = []
        for line in self.content.split('\n'):
            # 移除注释
            comment_index = line.find('//')
            if comment_index != -1:
                line = line[:comment_index]
            
            # 移除前后空白
            line = line.strip()
            
            # 只保留非空行
            if line:
                lines.append(line)
        
        self.content = ' '.join(lines)
    
    def read_double(self) -> float:
        """
        读取单个浮点数
        对应Java: public double readDouble() throws InputDataReaderException
        
        Returns:
            float: 读取的浮点数
            
        Raises:
            InputDataReaderException: 读取失败时抛出
        """
        try:
            if self.token_index >= len(self.tokens):
                raise InputDataReaderException(self.file_name)
            
            value = float(self.tokens[self.token_index])
            self.token_index += 1
            return value
        except ValueError:
            raise InputDataReaderException(self.file_name)
    
    def read_int(self) -> int:
        """
        读取单个整数
        对应Java: public int readInt() throws InputDataReaderException
        
        Returns:
            int: 读取的整数
            
        Raises:
            InputDataReaderException: 读取失败时抛出
        """
        try:
            if self.token_index >= len(self.tokens):
                raise InputDataReaderException(self.file_name)
            
            value = int(self.tokens[self.token_index])
            self.token_index += 1
            return value
        except ValueError:
            raise InputDataReaderException(self.file_name)
    
    def read_double_array(self) -> List[float]:
        """
        读取浮点数数组
        对应Java: public double[] readDoubleArray() throws InputDataReaderException
        
        Returns:
            List[float]: 读取的浮点数数组
            
        Raises:
            InputDataReaderException: 读取失败时抛出
        """
        try:
            # 读取数组大小
            size = self.read_int()
            
            # 读取数组元素
            result = []
            for _ in range(size):
                result.append(self.read_double())
            
            return result
        except Exception:
            raise InputDataReaderException(self.file_name)
    
    def read_double_array_array(self) -> List[List[float]]:
        """
        读取二维浮点数数组
        对应Java: public double[][] readDoubleArrayArray() throws InputDataReaderException
        
        Returns:
            List[List[float]]: 读取的二维浮点数数组
            
        Raises:
            InputDataReaderException: 读取失败时抛出
        """
        try:
            # 读取数组大小
            size = self.read_int()
            
            # 读取数组元素
            result = []
            for _ in range(size):
                result.append(self.read_double_array())
            
            return result
        except Exception:
            raise InputDataReaderException(self.file_name)
    
    def read_int_array(self) -> List[int]:
        """
        读取整数数组
        对应Java: public int[] readIntArray() throws InputDataReaderException
        
        Returns:
            List[int]: 读取的整数数组
            
        Raises:
            InputDataReaderException: 读取失败时抛出
        """
        try:
            # 读取数组大小
            size = self.read_int()
            
            # 读取数组元素
            result = []
            for _ in range(size):
                result.append(self.read_int())
            
            return result
        except Exception:
            raise InputDataReaderException(self.file_name)
    
    def read_int_array_array(self) -> List[List[int]]:
        """
        读取二维整数数组
        对应Java: public int[][] readIntArrayArray() throws InputDataReaderException
        
        Returns:
            List[List[int]]: 读取的二维整数数组
            
        Raises:
            InputDataReaderException: 读取失败时抛出
        """
        try:
            # 读取数组大小
            size = self.read_int()
            
            # 读取数组元素
            result = []
            for _ in range(size):
                result.append(self.read_int_array())
            
            return result
        except Exception:
            raise InputDataReaderException(self.file_name) 