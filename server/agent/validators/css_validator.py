"""
CSS Validator - Validates CSS syntax using cssutils
"""
from typing import List, Dict, Any

# Try to import cssutils, but make it optional
try:
    import cssutils
    # Suppress cssutils warnings
    cssutils.log.setLevel('ERROR')
    CSSUTILS_AVAILABLE = True
except ImportError:
    CSSUTILS_AVAILABLE = False


def validate_css(filepath: str, code: str) -> List[Dict[str, Any]]:
    """
    Validate CSS syntax using cssutils
    
    Args:
        filepath: Path to the CSS file
        code: CSS code content
        
    Returns:
        List of error dictionaries with 'file', 'line', 'message', 'type' keys
    """
    errors = []
    
    if CSSUTILS_AVAILABLE:
        try:
            # Parse CSS - cssutils will catch syntax errors
            sheet = cssutils.parseString(code)
            
            # Check for parsing errors
            # cssutils stores errors in sheet.errors list
            if hasattr(sheet, 'errors') and sheet.errors:
                for error in sheet.errors:
                    # Error objects may have different attributes depending on cssutils version
                    error_line = getattr(error, 'line', None) or getattr(error, 'lineno', None) or 1
                    error_col = getattr(error, 'col', None) or getattr(error, 'colno', None) or 1
                    errors.append({
                        "file": filepath,
                        "line": error_line,
                        "column": error_col,
                        "message": str(error),
                        "type": "syntax",
                        "severity": "error"
                    })
        except Exception as e:
            # Catch any parsing exceptions (like UnicodeDecodeError mentioned in docs)
            errors.append({
                "file": filepath,
                "line": 1,
                "column": 1,
                "message": f"CSS validation error: {str(e)}",
                "type": "syntax",
                "severity": "error"
            })
    
    return errors

