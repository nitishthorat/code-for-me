"""
Validators module for code validation using real parsers and linters
"""
from .javascript_validator import validate_javascript
from .typescript_validator import validate_typescript
from .html_validator import validate_html
from .css_validator import validate_css
from .json_validator import validate_json
from .dependency_validator import validate_dependencies, build_dependency_graph

__all__ = [
    "validate_javascript",
    "validate_typescript",
    "validate_html",
    "validate_css",
    "validate_json",
    "validate_dependencies",
    "build_dependency_graph",
]

