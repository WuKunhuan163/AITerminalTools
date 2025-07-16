"""
LEARN Project Package

A comprehensive learning system that can generate tutorials, questions, and example code
for various topics, with special support for academic paper learning.
"""

from .utils import parse_learn_command, create_project_structure

# Conditional imports to avoid dependency issues
try:
    from .learn_core import LearnSystem
    from .paper_processor import PaperProcessor
    __all__ = ["LearnSystem", "PaperProcessor", "parse_learn_command", "create_project_structure"]
except ImportError:
    # If dependencies are not available, only export utilities
    __all__ = ["parse_learn_command", "create_project_structure"]

__version__ = "1.0.0" 