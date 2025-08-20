# Test script with multiple Python errors

import os, sys    # Multiple imports on one line (style violation)
import json       # Unused import (style violation)

def function_with_errors(x,y):  # Missing space after comma (style)
    # Missing docstring (style violation)
    if x>5:  # Missing spaces around operator (style)
        print("x is greater than 5")
    
    # Undefined variable (runtime error)
    result = undefined_variable + y
    
    # Unreachable code after return
    return result
    print("This will never execute")  # Unreachable code

def another_function():
    # Long line exceeding 79 characters (PEP 8 violation)
    very_long_string = "This is a very long string that exceeds the recommended 79 character limit for Python code according to PEP 8 style guide"
    
    # Unused variable (style violation)
    unused_var = 42
    
    # Missing return statement for non-void function
    pass

# Missing blank lines around function definition (style)
def bad_indentation():
        # Inconsistent indentation (4 spaces vs 8 spaces)
    print("Bad indentation example")
    
# Function call with undefined function
undefined_function()

if __name__ == "__main__":
    function_with_errors(10, 5)
    another_function()
