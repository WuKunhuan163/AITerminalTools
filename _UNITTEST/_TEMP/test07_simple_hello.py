"""
Simple Hello Script
"""
print(f"Hello from remote project")
print(f"Current working directory:", __import__("os").getcwd())
import sys
print(f"Python version:", sys.version)
