"""
JSON Validator - Validates JSON syntax using Python's json module
"""
import json
from typing import List, Dict, Any


def validate_json(filepath: str, code: str) -> List[Dict[str, Any]]:
    """
    Validate JSON syntax
    
    Args:
        filepath: Path to the JSON file
        code: JSON code content
        
    Returns:
        List of error dictionaries with 'file', 'line', 'message', 'type' keys
    """
    errors = []
    
    try:
        json.loads(code)
    except json.JSONDecodeError as e:
        errors.append({
            "file": filepath,
            "line": e.lineno,
            "column": e.colno,
            "message": e.msg,
            "type": "syntax",
            "severity": "error"
        })
    except Exception as e:
        errors.append({
            "file": filepath,
            "line": 1,
            "column": 1,
            "message": f"JSON validation error: {str(e)}",
            "type": "syntax",
            "severity": "error"
        })
    
    return errors

