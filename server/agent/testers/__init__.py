"""
Testers module for code execution testing
"""
from .javascript_tester import test_javascript
from .python_tester import test_python

__all__ = [
    "test_javascript",
    "test_python",
]

