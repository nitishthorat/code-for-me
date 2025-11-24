"""
Unified Validator - Routes files to appropriate validators based on file type
"""
from typing import List, Dict, Any
from ..states import FileCode
from .javascript_validator import validate_javascript
from .typescript_validator import validate_typescript
from .html_validator import validate_html
from .css_validator import validate_css
from .json_validator import validate_json
from .dependency_validator import validate_dependencies


def validate_file(file: FileCode) -> List[Dict[str, Any]]:
    """
    Validate a single file using the appropriate validator
    
    Args:
        file: FileCode object to validate
        
    Returns:
        List of error dictionaries
    """
    filepath = file.filepath
    code = file.code
    ext = filepath.split('.')[-1].lower() if '.' in filepath else ''
    
    errors = []
    
    # Route to appropriate validator
    if ext == 'json':
        errors.extend(validate_json(filepath, code))
    elif ext == 'html' or ext == 'htm':
        errors.extend(validate_html(filepath, code))
    elif ext == 'css':
        errors.extend(validate_css(filepath, code))
    elif ext in ['js', 'jsx']:
        errors.extend(validate_javascript(filepath, code))
    elif ext in ['ts', 'tsx']:
        errors.extend(validate_typescript(filepath, code))
    # For other file types, skip validation for now
    
    return errors


def validate_all_files(files: List[FileCode]) -> Dict[str, Any]:
    """
    Validate all files and return comprehensive error report
    
    Args:
        files: List of FileCode objects
        
    Returns:
        Dictionary with 'syntax_errors', 'dependency_errors', 'total_errors', etc.
    """
    syntax_errors = []
    dependency_errors = []
    
    # Validate each file
    for file in files:
        file_errors = validate_file(file)
        syntax_errors.extend(file_errors)
    
    # Validate dependencies
    dependency_errors = validate_dependencies(files)
    
    # Categorize errors
    errors_by_type = {
        "syntax": [e for e in syntax_errors if e.get("type") == "syntax"],
        "dependency": dependency_errors,
        "runtime": [e for e in syntax_errors if e.get("type") == "runtime"],
    }
    
    return {
        "syntax_errors": syntax_errors,
        "dependency_errors": dependency_errors,
        "all_errors": syntax_errors + dependency_errors,
        "errors_by_type": errors_by_type,
        "total_errors": len(syntax_errors) + len(dependency_errors),
        "error_count_by_file": {}
    }

