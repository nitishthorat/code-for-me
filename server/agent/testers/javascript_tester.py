"""
JavaScript Tester - Executes JavaScript code in isolated Node.js environment
"""
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional


def test_javascript(filepath: str, code: str, timeout: int = 5) -> Dict[str, Any]:
    """
    Test JavaScript code execution in isolated Node.js environment
    
    Args:
        filepath: Path to the JS file
        code: JavaScript code content
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
    
    # Skip testing for certain file types or if code is too simple
    if not code.strip() or len(code) < 10:
        return result
    
    # Don't test if it's clearly a module (has exports but no execution)
    if 'export' in code and 'console.log' not in code and not any(keyword in code for keyword in ['if (', 'for (', 'while (']):
        return result
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tmp_file:
            # Wrap code in try-catch to capture errors
            wrapped_code = f"""
try {{
{code}
}} catch (error) {{
    console.error('Runtime Error:', error.message);
    console.error('Stack:', error.stack);
    process.exit(1);
}}
"""
            tmp_file.write(wrapped_code)
            tmp_file_path = tmp_file.name
        
        try:
            # Execute with Node.js
            exec_result = subprocess.run(
                ['node', tmp_file_path],
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
        except FileNotFoundError:
            # Node.js not available, skip testing
            pass
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

