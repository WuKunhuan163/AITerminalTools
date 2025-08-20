"""
Simple Hello Script
"""
print("Hello from remote project!")
print("Current working directory:", __import__("os").getcwd())
import sys
print("Python version:", sys.version)
