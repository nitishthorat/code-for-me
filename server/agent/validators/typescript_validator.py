"""
TypeScript Validator - Validates TypeScript/TSX syntax using TypeScript compiler
"""
import subprocess
import tempfile
import os
from typing import List, Dict, Any


def validate_typescript(filepath: str, code: str) -> List[Dict[str, Any]]:
    """
    Validate TypeScript/TSX syntax using TypeScript compiler
    
    Args:
        filepath: Path to the TS/TSX file
        code: TypeScript code content
        
    Returns:
        List of error dictionaries with 'file', 'line', 'message', 'type' keys
    """
    errors = []
    ext = filepath.split('.')[-1].lower()
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{ext}', delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_file_path = tmp_file.name
        
        try:
            # Try to compile with TypeScript compiler (tsc)
            # Use --noEmit to just check without generating files
            result = subprocess.run(
                ['tsc', '--noEmit', '--skipLibCheck', tmp_file_path],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                # Parse error output
                error_output = result.stderr + result.stdout
                lines = error_output.split('\n')
                for line in lines:
                    if 'error TS' in line or 'error' in line.lower():
                        # Try to extract file, line, and message
                        # Format: file.ts(line,col): error TS####: message
                        parts = line.split(':')
                        if len(parts) >= 3:
                            try:
                                # Extract line number
                                line_info = parts[1] if len(parts) > 1 else '1'
                                line_num = int(line_info.split('(')[1].split(',')[0]) if '(' in line_info else 1
                                
                                # Extract message
                                message = ':'.join(parts[2:]).strip()
                                
                                errors.append({
                                    "file": filepath,
                                    "line": line_num,
                                    "column": 1,
                                    "message": message,
                                    "type": "syntax",
                                    "severity": "error"
                                })
                            except:
                                errors.append({
                                    "file": filepath,
                                    "line": 1,
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
                "message": "TypeScript validation timed out",
                "type": "syntax",
                "severity": "warning"
            })
        except FileNotFoundError:
            # TypeScript compiler not available, fall back to basic checks
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
    if code.strip():
        # Check for unclosed brackets/braces/parentheses
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

