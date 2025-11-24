"""
HTML Validator - Validates HTML syntax using html5lib
"""
from typing import List, Dict, Any

# Try to import html5lib, but make it optional
try:
    import html5lib
    from html5lib import HTMLParser
    HTML5LIB_AVAILABLE = True
except ImportError:
    HTML5LIB_AVAILABLE = False


def validate_html(filepath: str, code: str) -> List[Dict[str, Any]]:
    """
    Validate HTML syntax using html5lib
    
    Args:
        filepath: Path to the HTML file
        code: HTML code content
        
    Returns:
        List of error dictionaries with 'file', 'line', 'message', 'type' keys
    """
    errors = []
    
    if HTML5LIB_AVAILABLE:
        try:
            parser = HTMLParser(strict=False)
            # Parse the HTML - this will catch syntax errors
            parser.parse(code)
        except Exception as e:
            # html5lib is lenient, so we check for well-formedness differently
            # Try to parse and check for errors
            try:
                from html5lib.html5parser import parse
                tree = parse(code, treebuilder="etree")
                # If parsing succeeds, check for common issues
                if not code.strip():
                    errors.append({
                        "file": filepath,
                        "line": 1,
                        "column": 1,
                        "message": "HTML file is empty",
                        "type": "syntax",
                        "severity": "warning"
                    })
            except Exception as parse_error:
                errors.append({
                    "file": filepath,
                    "line": 1,
                    "column": 1,
                    "message": f"HTML parsing error: {str(parse_error)}",
                    "type": "syntax",
                    "severity": "error"
                })
    
    # Basic validation checks
    if code.strip():
        # Check for basic HTML structure
        if "<html" not in code.lower() and "<!doctype" not in code.lower():
            # This is okay for fragments, but warn
            pass
        
        # Check for unclosed tags (basic check)
        open_tags = code.count("<") - code.count("</") - code.count("<!")
        if open_tags < 0:
            errors.append({
                "file": filepath,
                "line": 1,
                "column": 1,
                "message": "Possible unclosed HTML tags detected",
                "type": "syntax",
                "severity": "warning"
            })
    
    return errors

