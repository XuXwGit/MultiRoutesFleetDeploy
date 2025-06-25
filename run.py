import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入并运行main函数
from multi.main import main

if __name__ == "__main__":
    main() 