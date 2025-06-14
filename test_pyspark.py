#!/usr/bin/env python3
import sys
import os

# 确保使用虚拟环境的Python路径
venv_path = r'C:\Users\32503\Desktop\hbaseProject\.venv'
sys.path.insert(0, os.path.join(venv_path, 'Lib', 'site-packages'))

print("Python路径:")
for path in sys.path[:5]:  # 只显示前5个路径
    print(f"  {path}")

try:
    import pyspark
    print(f"✅ PySpark导入成功! 版本: {pyspark.__version__}")
    
    from pyspark.sql import SparkSession
    print("✅ SparkSession导入成功!")
    
    from pyspark.sql.functions import *
    print("✅ PySpark函数导入成功!")
    
    print("\n🎉 所有PySpark模块导入成功!")
    
except ImportError as e:
    print(f"❌ PySpark导入失败: {e}")
except Exception as e:
    print(f"❌ 其他错误: {e}")