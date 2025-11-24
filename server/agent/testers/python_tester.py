"""
Python Tester - Executes Python code in isolated environment
"""
import subprocess
import tempfile
import os
from typing import Dict, Any


def test_python(filepath: str, code: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Test Python code execution in isolated environment
    
    Args:
        filepath: Path to the Python file
        code: Python code content
        timeout: Execution timeout in seconds
        
    Returns:
        Dictionary with 'success', 'errors', 'output' keys
    """
    result = {
        "success": True,
        "errors": [],
        "output": "",
        "runtime_errors": []
    }
    
    # Skip testing for certain cases
    if not code.strip() or len(code) < 10:
        return result
    
    # Don't test if it's clearly a module (has imports/exports but no execution)
    if ('def ' in code or 'class ' in code) and '__main__' not in code and not any(keyword in code for keyword in ['if __name__', 'print(']):
        return result
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp_file:
            tmp_file.write(code)
            tmp_file_path = tmp_file.name
        
        try:
            # Execute with Python
            exec_result = subprocess.run(
                ['python3', tmp_file_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if exec_result.returncode != 0:
                result["success"] = False
                error_output = exec_result.stderr
                result["runtime_errors"].append({
                    "file": filepath,
                    "message": error_output,
                    "type": "runtime",
                    "severity": "error"
                })
            else:
                result["output"] = exec_result.stdout
                
        except subprocess.TimeoutExpired:
            result["success"] = False
            result["runtime_errors"].append({
                "file": filepath,
                "message": f"Execution timed out after {timeout} seconds",
                "type": "runtime",
                "severity": "error"
            })
        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_file_path)
            except:
                pass
                
    except Exception as e:
        # If testing fails, don't block - just log
        result["errors"].append({
            "file": filepath,
            "message": f"Testing error: {str(e)}",
            "type": "testing",
            "severity": "warning"
        })
    
    return result

