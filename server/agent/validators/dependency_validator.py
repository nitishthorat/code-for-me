"""
Dependency Validator - Validates imports/exports and builds dependency graph
"""
import re
from typing import List, Dict, Any, Set, Tuple
from pathlib import Path
from collections import defaultdict


def build_dependency_graph(files: List) -> Dict[str, Set[str]]:
    """
    Build a dependency graph from import statements
    
    Args:
        files: List of FileCode objects
        
    Returns:
        Dictionary mapping filepath -> set of imported filepaths
    """
    graph = defaultdict(set)
    file_map = {}  # module_name -> filepath
    
    # First pass: build file map (without extensions)
    for file in files:
        filepath = file.filepath
        path_obj = Path(filepath)
        # Map various forms of the module name
        module_name = str(path_obj.with_suffix(''))
        file_map[module_name] = filepath
        file_map[path_obj.stem] = filepath  # Just filename
        file_map[filepath] = filepath  # Full path
    
    # Build set of all file paths for quick lookup
    file_paths = {f.filepath for f in files}
    
    # Second pass: extract imports and build graph
    for file in files:
        filepath = file.filepath
        code = file.code
        file_dir = str(Path(filepath).parent) if Path(filepath).parent.name else '.'
        ext = Path(filepath).suffix.lower().lstrip('.')
        
        # Extract import statements based on file type
        import_patterns = []
        
        # For CSS files, check @import statements
        if ext == 'css':
            import_patterns = [
                r"@import\s+['\"]([^'\"]+)['\"]",  # CSS @import
                r"@import\s+url\(['\"]?([^'\"]+)['\"]?\)",  # CSS @import url()
            ]
        # For HTML files, check link and script tags
        elif ext in ['html', 'htm']:
            import_patterns = [
                r'<link[^>]+href=["\']([^"\']+)["\']',  # CSS links
                r'<script[^>]+src=["\']([^"\']+)["\']',  # JS scripts
            ]
        # For JavaScript files (vanilla JS doesn't use ES6 imports, skip for now)
        # We could check for script tags in HTML instead
        
        for pattern in import_patterns:
            matches = re.findall(pattern, code)
            for import_path in matches:
                # Skip external URLs and node_modules
                if import_path.startswith('http') or import_path.startswith('//') or import_path.startswith('node_modules') or import_path.startswith('@'):
                    continue
                
                # Resolve import path to actual file
                resolved_path = None
                
                # Normalize path separators
                import_path = import_path.replace('\\', '/')
                
                # Try to resolve relative imports
                if import_path.startswith('./') or import_path.startswith('../'):
                    try:
                        # For CSS/HTML, keep the extension
                        if ext in ['css', 'html', 'htm']:
                            # Try with extension first
                            resolved = str((Path(file_dir) / import_path).resolve())
                            # Check if any file matches
                            for actual_path in file_paths:
                                if str(Path(actual_path).resolve()) == resolved or actual_path.endswith(import_path):
                                    resolved_path = actual_path
                                    break
                            
                            # If not found, try without extension
                            if not resolved_path:
                                import_path_no_ext = import_path.rsplit('.', 1)[0] if '.' in import_path else import_path
                                resolved = str((Path(file_dir) / import_path_no_ext).resolve())
                                for actual_path in file_paths:
                                    if str(Path(actual_path).resolve()).startswith(resolved):
                                        resolved_path = actual_path
                                        break
                        else:
                            # For JS files, remove extension
                            import_path_no_ext = import_path.rsplit('.', 1)[0] if '.' in import_path else import_path
                            resolved = str((Path(file_dir) / import_path_no_ext).resolve())
                            for actual_path in file_paths:
                                if str(Path(actual_path).resolve()).startswith(resolved):
                                    resolved_path = actual_path
                                    break
                    except Exception as e:
                        pass
                else:
                    # Absolute/root-relative import - try to find in file_paths
                    # Remove leading slash if present
                    import_path_clean = import_path.lstrip('/')
                    # Try exact match first
                    if import_path in file_paths:
                        resolved_path = import_path
                    elif import_path_clean in file_paths:
                        resolved_path = import_path_clean
                    else:
                        # Try to find file that ends with this path
                        for actual_path in file_paths:
                            if actual_path.endswith(import_path) or actual_path.endswith(import_path_clean):
                                resolved_path = actual_path
                                break
                
                if resolved_path and resolved_path != filepath:
                    graph[filepath].add(resolved_path)
    
    return dict(graph)


def validate_dependencies(files: List) -> List[Dict[str, Any]]:
    """
    Validate that all imports resolve to existing files
    
    Args:
        files: List of FileCode objects
        
    Returns:
        List of error dictionaries
    """
    errors = []
    graph = build_dependency_graph(files)
    file_paths = {f.filepath for f in files}
    
    # Check for unresolved imports
    for filepath, imports in graph.items():
        for imported_file in imports:
            if imported_file not in file_paths:
                errors.append({
                    "file": filepath,
                    "line": 1,
                    "column": 1,
                    "message": f"Import resolves to non-existent file: {imported_file}",
                    "type": "dependency",
                    "severity": "error"
                })
    
    # Check for circular dependencies
    def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
        visited.add(node)
        rec_stack.add(node)
        
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if has_cycle(neighbor, visited, rec_stack):
                    return True
            elif neighbor in rec_stack:
                return True
        
        rec_stack.remove(node)
        return False
    
    visited = set()
    for filepath in graph:
        if filepath not in visited:
            rec_stack = set()
            if has_cycle(filepath, visited, rec_stack):
                errors.append({
                    "file": filepath,
                    "line": 1,
                    "column": 1,
                    "message": f"Circular dependency detected involving {filepath}",
                    "type": "dependency",
                    "severity": "warning"
                })
    
    return errors

