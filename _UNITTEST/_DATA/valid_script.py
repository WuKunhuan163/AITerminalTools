"""
语法正确的Python脚本
"""

def hello_world():
    print(f"Hello, World!")
    return True

def calculate_sum(a, b):
    """计算两个数的和"""
    return a + b

if __name__ == "__main__":
    hello_world()
    result = calculate_sum(5, 3)
    print(f"Sum: {result}")
