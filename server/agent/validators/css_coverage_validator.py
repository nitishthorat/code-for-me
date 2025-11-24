"""
CSS Coverage Validator - Checks that all HTML classes and IDs have corresponding CSS styles
"""
import re
from typing import List, Dict, Any, Set, Tuple
from pathlib import Path


def extract_html_selectors(html_code: str) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Extract all class names, IDs, and semantic elements from HTML code
    
    Args:
        html_code: HTML code content
        
    Returns:
        Tuple of (set of class names, set of IDs, set of semantic elements)
    """
    classes = set()
    ids = set()
    
    # Extract classes from class="..." attributes
    class_pattern = r'class=["\']([^"\']+)["\']'
    for match in re.finditer(class_pattern, html_code, re.IGNORECASE):
        class_values = match.group(1).split()
        classes.update(class_values)
    
    # Extract IDs from id="..." attributes
    id_pattern = r'id=["\']([^"\']+)["\']'
    for match in re.finditer(id_pattern, html_code, re.IGNORECASE):
        ids.add(match.group(1))
    
    # Also extract semantic HTML elements that should be styled
    semantic_elements = {'header', 'nav', 'main', 'section', 'article', 'aside', 'footer', 
                         'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'a', 'button', 'input', 
                         'form', 'label', 'ul', 'ol', 'li', 'img', 'div', 'span'}
    
    # Check which semantic elements are present in HTML
    present_elements = set()
    for element in semantic_elements:
        if re.search(rf'<{element}[>\s]', html_code, re.IGNORECASE):
            present_elements.add(element)
    
    return classes, ids, present_elements


def extract_css_selectors(css_code: str) -> Set[str]:
    """
    Extract all CSS selectors from CSS code
    
    Args:
        css_code: CSS code content
        
    Returns:
        Set of CSS selector strings (normalized)
    """
    selectors = set()
    
    # Remove comments
    css_code = re.sub(r'/\*.*?\*/', '', css_code, flags=re.DOTALL)
    
    # Extract selectors from CSS rules
    # Pattern matches selector { ... }
    rule_pattern = r'([^{]+)\{'
    for match in re.finditer(rule_pattern, css_code):
        selector_text = match.group(1).strip()
        
        # Split by comma to handle multiple selectors
        for selector in selector_text.split(','):
            selector = selector.strip()
            if selector:
                # Normalize selector (remove extra whitespace, handle pseudo-classes)
                selector = re.sub(r'\s+', ' ', selector)
                # Extract base selector (before :hover, :focus, etc.)
                base_selector = re.split(r':', selector)[0].strip()
                if base_selector:
                    selectors.add(base_selector)
    
    return selectors


def normalize_selector(selector: str) -> str:
    """
    Normalize a CSS selector for comparison
    
    Args:
        selector: CSS selector string
        
    Returns:
        Normalized selector
    """
    # Remove extra whitespace
    selector = re.sub(r'\s+', ' ', selector.strip())
    # Remove leading/trailing spaces around combinators
    selector = re.sub(r'\s*>\s*', ' > ', selector)
    selector = re.sub(r'\s*\+\s*', ' + ', selector)
    selector = re.sub(r'\s*~\s*', ' ~ ', selector)
    return selector


def check_selector_coverage(selector: str, css_selectors: Set[str]) -> bool:
    """
    Check if a selector (class, ID, or element) is covered by CSS
    
    Args:
        selector: HTML selector (class name, ID, or element name)
        css_selectors: Set of CSS selectors found in CSS files
        
    Returns:
        True if covered, False otherwise
    """
    # Check exact match
    if selector in css_selectors:
        return True
    
    # Check class selector (.class-name)
    if f'.{selector}' in css_selectors:
        return True
    
    # Check ID selector (#id-name)
    if f'#{selector}' in css_selectors:
        return True
    
    # Check if selector is part of a compound selector
    for css_selector in css_selectors:
        # Check if selector appears in compound selector (e.g., ".card .title" contains ".title")
        if selector in css_selector or f'.{selector}' in css_selector or f'#{selector}' in css_selector:
            # More specific check: ensure it's a complete word/selector
            if re.search(rf'(^|[\s>+~])\.?{re.escape(selector)}([\s>+~\.#:]|$)', css_selector):
                return True
    
    return False


def validate_css_coverage(html_files: List[Dict[str, str]], css_files: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Validate that all HTML classes and IDs have corresponding CSS styles
    
    Args:
        html_files: List of dicts with 'filepath' and 'code' keys for HTML files
        css_files: List of dicts with 'filepath' and 'code' keys for CSS files
        
    Returns:
        List of error dictionaries for unstyled selectors
    """
    errors = []
    
    # Extract all CSS selectors from all CSS files
    all_css_selectors = set()
    for css_file in css_files:
        css_selectors = extract_css_selectors(css_file['code'])
        all_css_selectors.update(css_selectors)
    
    # Check each HTML file
    for html_file in html_files:
        html_code = html_file['code']
        filepath = html_file['filepath']
        
        # Extract classes, IDs, and semantic elements from HTML
        classes, ids, semantic_elements = extract_html_selectors(html_code)
        
        # Check classes
        for class_name in classes:
            if not check_selector_coverage(class_name, all_css_selectors):
                errors.append({
                    "file": filepath,
                    "line": 1,
                    "column": 1,
                    "message": f"Class '{class_name}' is used in HTML but has no corresponding CSS styles",
                    "type": "coverage",
                    "severity": "warning",
                    "selector": f".{class_name}",
                    "selector_type": "class"
                })
        
        # Check IDs
        for id_name in ids:
            if not check_selector_coverage(id_name, all_css_selectors):
                errors.append({
                    "file": filepath,
                    "line": 1,
                    "column": 1,
                    "message": f"ID '{id_name}' is used in HTML but has no corresponding CSS styles",
                    "type": "coverage",
                    "severity": "warning",
                    "selector": f"#{id_name}",
                    "selector_type": "id"
                })
        
        # Check semantic elements (only warn if they're likely to need styling)
        important_elements = {'header', 'nav', 'main', 'section', 'footer', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        for element in semantic_elements:
            if element in important_elements:
                if not check_selector_coverage(element, all_css_selectors):
                    errors.append({
                        "file": filepath,
                        "line": 1,
                        "column": 1,
                        "message": f"Semantic element '<{element}>' is used but may need explicit CSS styling",
                        "type": "coverage",
                        "severity": "info",
                        "selector": element,
                        "selector_type": "element"
                    })
    
    return errors

