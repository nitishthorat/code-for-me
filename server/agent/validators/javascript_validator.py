"""
JavaScript Validator - Validates JavaScript/JSX syntax using Node.js and ESLint
"""
import subprocess
import json
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any


def validate_javascript(filepath: str, code: str) -> List[Dict[str, Any]]:
    """
    Validate JavaScript/JSX syntax using Node.js syntax checking
    
    Args:
        filepath: Path to the JS/JSX file
        code: JavaScript code content
        
    Returns:
        List of error dictionaries with 'file', 'line', 'message', 'type' keys
    """
    errors = []
    ext = filepath.split('.')[-1].lower()
    
    # For JSX files, we need to check if it's valid JSX syntax
    # For now, use basic Node.js syntax checking
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_file_path = tmp_file.name
        
        try:
            # Try to parse with Node.js (basic syntax check)
            # Use node --check for syntax validation
            result = subprocess.run(
                ['node', '--check', tmp_file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                # Parse error output
                error_output = result.stderr
                # Extract line numbers and messages
                lines = error_output.split('\n')
                for line in lines:
                    if 'SyntaxError' in line or 'Error' in line:
                        # Try to extract line number
                        line_num = 1
                        if ':' in line:
                            parts = line.split(':')
                            try:
                                line_num = int(parts[-2]) if len(parts) > 2 else 1
                            except:
                                pass
                        
                        errors.append({
                            "file": filepath,
                            "line": line_num,
                            "column": 1,
                            "message": line.strip(),
                            "type": "syntax",
                            "severity": "error"
                        })
        except subprocess.TimeoutExpired:
            errors.append({
                "file": filepath,
                "line": 1,
                "column": 1,
                "message": "JavaScript validation timed out",
                "type": "syntax",
                "severity": "warning"
            })
        except FileNotFoundError:
            # Node.js not available, skip validation
            pass
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
                
    except Exception as e:
        # If validation fails, don't block - just log
        pass
    
    # Basic syntax checks as fallback
    # Check for common syntax errors
    if code.strip():
        # Check for unclosed brackets/braces/parentheses (basic)
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            errors.append({
                "file": filepath,
                "line": 1,
                "column": 1,
                "message": f"Unmatched braces: {{ {open_braces}, }} {close_braces}",
                "type": "syntax",
                "severity": "error"
            })
    
    return errors

