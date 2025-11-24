from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langgraph.graph import StateGraph

from agent.prompts import *
from agent.states import *
from agent.validators.unified_validator import validate_all_files
from agent.testers.javascript_tester import test_javascript
from agent.testers.python_tester import test_python
from agent.debug_utils import log_agent_execution

import io, zipfile
import os
import ast
from pathlib import Path

load_dotenv()

# Debugging can be enabled via environment variables in langchain 1.0+
# Set LANGCHAIN_VERBOSE=true and LANGCHAIN_DEBUG=true in your .env file if needed
os.environ.setdefault("LANGCHAIN_VERBOSE", "true")
os.environ.setdefault("LANGCHAIN_DEBUG", "true")

# Get model from environment variable, with fallback to alternative models
# Available Groq models (as of 2024):
# - llama-3.3-70b-versatile (recommended, latest 70B model)
# - llama-3.1-8b-instant (faster, smaller, good for quick responses)
# - mixtral-8x7b-32768 (good for longer context)
# - gemma2-9b-it (smaller, faster)
# - openai/gpt-oss-120b (has rate limits)
# Note: llama-3.1-70b-versatile has been decommissioned
model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
llm = ChatGroq(model=model_name)
print(f"Using Groq model: {model_name}")

@log_agent_execution("planner")
def planner_agent(state: dict) -> dict:
    user_prompt = state["user_prompt"]
    import json
    import re
    
    # Use regular invoke instead of with_structured_output to avoid tool calling issues
    prompt = planner_prompt(user_prompt)
    raw_response = llm.invoke(prompt)
    content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
    
    # Extract JSON from response
    parsed_data = None
    
    # Method 1: Try to parse JSON directly if content is already JSON
    try:
        parsed_data = json.loads(content.strip())
        print("✓ Successfully parsed JSON directly from response")
    except:
        pass
    
    # Method 2: Extract JSON from markdown code blocks if present
    if not parsed_data:
        json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
        match = re.search(json_block_pattern, content, re.DOTALL)
        if match:
            try:
                parsed_data = json.loads(match.group(1))
                print("✓ Successfully parsed JSON from code block")
            except:
                pass
    
    # Method 3: Find JSON object in content (starts with {)
    if not parsed_data:
        json_start = content.find('{')
        if json_start != -1:
            # Find matching closing brace
            brace_count = 0
            json_end = -1
            for i in range(json_start, len(content)):
                if content[i] == '{':
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end != -1:
                try:
                    json_str = content[json_start:json_end]
                    parsed_data = json.loads(json_str)
                    print("✓ Successfully parsed JSON by finding braces")
                except:
                    pass
    
    # Create Plan object from parsed data
    if parsed_data:
        try:
            response = Plan(**parsed_data)
            return {"plan": response}
        except Exception as validation_err:
            print(f"Failed to create Plan from parsed data: {validation_err}")
            print(f"Parsed data keys: {list(parsed_data.keys()) if isinstance(parsed_data, dict) else 'not a dict'}")
            raise ValueError(f"Invalid Plan structure: {validation_err}")
    
    # If no JSON found, raise error
    raise ValueError(f"Could not extract valid JSON from planner response. Content: {content[:500]}")

def parse_markdown_tasks(content: str) -> list:
    """Parse markdown/text content and extract implementation tasks"""
    import re
    
    tasks = []
    filepaths_found = {}
    
    # Pattern 1: Extract file paths from directory structure diagrams
    # Matches lines like: │ ├─ App.tsx or │ ├─ components/App.tsx or ├─ src/main.tsx
    dir_structure_pattern = r'[│├└─\s]+([a-zA-Z0-9_/\\-]+\.(?:js|jsx|ts|tsx|json|html|css|md|py|yml|yaml|config\.js|config\.ts|test\.tsx?))'
    dir_matches = re.finditer(dir_structure_pattern, content)
    for match in dir_matches:
        filepath = match.group(1).strip()
        # Clean up common prefixes
        filepath = re.sub(r'^src[/\\]', 'src/', filepath)
        filepath = re.sub(r'^components[/\\]', 'src/components/', filepath)
        if not filepath.startswith('src/') and not filepath.startswith('./') and '/' in filepath:
            filepath = 'src/' + filepath
        if filepath not in filepaths_found:
            filepaths_found[filepath] = match.start()
    
    # Pattern 2: Extract from code blocks with file paths
    code_block_pattern = r'```[^\n]*\n(.*?)```'
    code_blocks = re.finditer(code_block_pattern, content, re.DOTALL)
    for block_match in code_blocks:
        block_content = block_match.group(1)
        # Look for file paths in code blocks
        file_paths_in_block = re.findall(r'([a-zA-Z0-9_/\\-]+\.(?:js|jsx|ts|tsx|json|html|css|md|py|yml|yaml|config\.js|config\.ts))', block_content)
        for fp in file_paths_in_block:
            fp = fp.strip()
            if not fp.startswith('src/') and not fp.startswith('./') and '/' in fp:
                fp = 'src/' + fp
            if fp not in filepaths_found:
                filepaths_found[fp] = block_match.start()
    
    # Pattern 3: Split content by section headers (## with numbers/emojis)
    # Pattern to match section headers: ## 1️⃣ `filepath` or ## 1 `filepath`
    section_pattern = r'##\s*\d+[️⃣1-9]?\s*`([^`]+)`'
    
    # Find all section headers and their positions
    section_matches = list(re.finditer(section_pattern, content, re.IGNORECASE))
    
    # Pattern 4: Find file paths in backticks or bold
    if not section_matches:
        filepath_patterns = [
            r'`([^`/]+\.(?:js|jsx|ts|tsx|json|html|css|md|py|yml|yaml|config\.js|config\.ts))`',
            r'\*\*([^*]+\.(?:js|jsx|ts|tsx|json|html|css|md|py|yml|yaml|config\.js|config\.ts))\*\*',
            r'([a-zA-Z0-9_/\\-]+\.(?:js|jsx|ts|tsx|json|html|css|md|py|yml|yaml|config\.js|config\.ts))',  # Plain file paths
        ]
        
        for pattern in filepath_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                filepath = match.group(1).strip()
                # Skip if it's part of a URL or other context
                if 'http' in match.group(0) or '@' in match.group(0):
                    continue
                if not filepath.startswith('src/') and not filepath.startswith('./') and '/' in filepath and not filepath.startswith('http'):
                    filepath = 'src/' + filepath
                if filepath not in filepaths_found:
                    filepaths_found[filepath] = match.start()
    
    # Add section matches to filepaths
    for section_match in section_matches:
        filepath = section_match.group(1)
        if filepath not in filepaths_found:
            filepaths_found[filepath] = section_match.start()
    
    # Sort filepaths by their position in the document
    sorted_filepaths = sorted(filepaths_found.items(), key=lambda x: x[1])
    
    # Create SimpleMatch objects for processing
    class SimpleMatch:
        def __init__(self, pos, filepath):
            self._pos = pos
            self._filepath = filepath
        def group(self, n):
            return self._filepath if n == 1 else None
        def start(self):
            return self._pos
    
    section_matches = [SimpleMatch(pos, fp) for fp, pos in sorted_filepaths]
    
    # Process each filepath found
    for i, section_match in enumerate(section_matches):
        filepath = section_match.group(1)
        start_pos = section_match.start()
        end_pos = section_matches[i + 1].start() if i + 1 < len(section_matches) else len(content)
        
        # Get context around this filepath
        context_start = max(0, start_pos - 500)  # Look 500 chars before
        context_end = min(len(content), end_pos + 500)  # Look 500 chars after
        section_content = content[context_start:context_end]
        
        # Generate task description based on filepath and context
        task_desc = None
        
        # Pattern 1: Extract from markdown table format
        # | **T‑01** | **Create the project manifest** – define `name`, ...
        table_row_pattern = r'\|\s*\*\*T[-\u2013]?\d+\*\*\s*\|\s*\*\*([^*]+)\*\*\s*[–-]\s*(.+?)(?=\n\||\n\n|$)'
        table_match = re.search(table_row_pattern, section_content, re.DOTALL)
        
        if table_match:
            # Extract task description from table
            task_desc = table_match.group(2).strip()
        else:
            # Pattern 2: Look for content after the filepath in the section
            # Extract text after filepath mention until next section
            desc_pattern = rf'(?:{re.escape(filepath)}|`{re.escape(filepath)}`)[^`]*?[–-]\s*(.+?)(?=\n`|\n\*\*|\n##|\n---|$)'
            desc_match = re.search(desc_pattern, section_content, re.DOTALL | re.IGNORECASE)
            
            if desc_match:
                task_desc = desc_match.group(1).strip()
            else:
                # Pattern 3: Generate description based on filepath and context
                # Extract filename and extension
                filename = filepath.split('/')[-1] if '/' in filepath else filepath
                file_ext = filename.split('.')[-1] if '.' in filename else ''
                file_base = filename.replace('.' + file_ext, '') if file_ext else filename
                
                # Generate description based on file type and name
                if filepath == 'package.json':
                    task_desc = f"Create package.json with project metadata, dependencies, and npm scripts for the React TypeScript application"
                elif filepath.endswith('.config.ts') or filepath.endswith('.config.js'):
                    task_desc = f"Create {filename} configuration file for build tools and project setup"
                elif filepath == 'src/main.tsx' or filepath == 'src/main.jsx':
                    task_desc = f"Create main entry point that imports ReactDOM, renders the App component into the root element"
                elif filepath == 'src/App.tsx' or filepath == 'src/App.jsx':
                    task_desc = f"Create App component as the root component that sets up context providers and renders main UI structure"
                elif 'components' in filepath:
                    component_name = file_base.replace('.tsx', '').replace('.jsx', '')
                    task_desc = f"Create {component_name} component in {filepath} with proper TypeScript types, props interface, and React functional component structure"
                elif 'context' in filepath:
                    task_desc = f"Create React Context and provider for state management in {filepath}"
                elif 'hooks' in filepath:
                    hook_name = file_base.replace('.ts', '').replace('.tsx', '')
                    task_desc = f"Create custom React hook {hook_name} in {filepath}"
                elif filepath.endswith('.test.tsx') or filepath.endswith('.test.ts'):
                    task_desc = f"Create unit tests for the corresponding component using Jest and React Testing Library"
                elif filepath.endswith('.css'):
                    task_desc = f"Create CSS stylesheet with Tailwind CSS utilities and custom styles for the application"
                elif filepath == 'index.html':
                    task_desc = f"Create HTML entry point with root div element and script tag to load the React application"
                elif filepath == 'README.md':
                    task_desc = f"Create README.md with project description, setup instructions, and usage documentation"
                else:
                    # Generic description
                    task_desc = f"Create {filename} file with appropriate code structure and functionality"
        
        # Clean up markdown formatting
        if task_desc:
            # Remove markdown table formatting but preserve content
            # First, extract content from table cells if present
            if '|' in task_desc:
                # Extract text between pipes, skip header rows
                cells = [cell.strip() for cell in task_desc.split('|') if cell.strip()]
                if len(cells) >= 2:
                    # Usually the description is in the last cell or second cell
                    task_desc = cells[-1] if len(cells) > 2 else ' '.join(cells[1:])
            
            # Remove markdown formatting
            task_desc = re.sub(r'\*\*([^*]+)\*\*', r'\1', task_desc)  # Remove bold
            task_desc = re.sub(r'\*([^*]+)\*', r'\1', task_desc)  # Remove italic
            task_desc = re.sub(r'`([^`]+)`', r'\1', task_desc)  # Remove inline code (but keep content)
            task_desc = re.sub(r'```[\s\S]*?```', '', task_desc)  # Remove code blocks
            task_desc = re.sub(r'\|', '', task_desc)  # Remove remaining pipe characters
            task_desc = re.sub(r'#{1,6}\s+', '', task_desc)  # Remove headers
            task_desc = re.sub(r'[–—-]+', '-', task_desc)  # Normalize dashes
            task_desc = re.sub(r'\n\s*\n+', ' ', task_desc)  # Replace multiple newlines with space
            task_desc = re.sub(r'\s+', ' ', task_desc)  # Normalize whitespace
            task_desc = task_desc.strip()
            
            # Remove common markdown artifacts
            task_desc = re.sub(r'^\*\*.*?:\*\*\s*', '', task_desc)  # Remove bold labels
            task_desc = re.sub(r'^\d+[️⃣1-9]?\s*', '', task_desc)  # Remove numbered list markers
            task_desc = re.sub(r'^T[-\u2013]?\d+\s*[–-]?\s*', '', task_desc, flags=re.IGNORECASE)  # Remove task IDs
            
            if task_desc and len(task_desc) > 10:  # Valid description
                tasks.append(ImplementationTask(
                    filepath=filepath,
                    task_description=task_desc
                ))
    
    return tasks

@log_agent_execution("architect")
def architect_agent(state: dict) -> dict:
    plan = state['plan']
    import json
    import re
    
    # Extract and validate tech_stack
    tech_stack = None
    if hasattr(plan, 'tech_stack'):
        tech_stack = plan.tech_stack
        print(f"📋 Architect: Detected tech_stack: {tech_stack}")
        
        # Validate tech_stack is vanilla HTML/CSS/JS
        if tech_stack and "vanilla" not in tech_stack.lower() and "html" not in tech_stack.lower():
            print(f"⚠️  WARNING: Tech stack is '{tech_stack}' but should be 'Vanilla HTML/CSS/JS'. Enforcing vanilla HTML/CSS/JS.")
    
    # Extract design system from plan if available
    design_system = None
    if hasattr(plan, 'design_system') and plan.design_system:
        design_system = {
            'colors': plan.design_system.colors if hasattr(plan.design_system, 'colors') else {},
            'typography': plan.design_system.typography if hasattr(plan.design_system, 'typography') else {},
            'spacing': plan.design_system.spacing if hasattr(plan.design_system, 'spacing') else {},
            'breakpoints': plan.design_system.breakpoints if hasattr(plan.design_system, 'breakpoints') else {},
            'components': plan.design_system.components if hasattr(plan.design_system, 'components') else []
        }
    
    plan_str = str(plan) if not isinstance(plan, str) else plan
    
    response = None
    original_error_str = None
    
    try:
        # Try without json_schema method first to avoid list wrapping issues
        response = llm.with_structured_output(TaskPlan).invoke(architect_prompt(plan_str, design_system, tech_stack))
    except Exception as e:
        # Handle case where LLM returns markdown or text instead of JSON
        error_str = str(e)
        original_error_str = error_str  # Store for use in nested exception handlers
        
        # Check if error contains failed_generation with markdown/text
        if 'failed_generation' in error_str:
            try:
                # Try to parse the error as a Python dict representation
                content = None
                
                # Method 1: Try to use ast.literal_eval to parse the entire error string as a dict
                try:
                    # Extract the dict part from the error string
                    dict_match = re.search(r"\{'error':\s*\{[^}]+\}\}", error_str, re.DOTALL)
                    if dict_match:
                        error_dict_str = dict_match.group(0)
                        error_dict = ast.literal_eval(error_dict_str)
                        if 'error' in error_dict and 'failed_generation' in error_dict['error']:
                            content = error_dict['error']['failed_generation']
                except:
                    pass
                
                # Method 2: Try regex extraction if ast.literal_eval failed
                if not content:
                    # Look for failed_generation with single quotes (handles escaped quotes)
                    # This pattern matches: 'failed_generation': '...' where ... can contain escaped quotes
                    pattern = r"'failed_generation':\s*'((?:[^'\\]|\\.|'')*)'"
                    failed_gen_match = re.search(pattern, error_str, re.DOTALL)
                    if not failed_gen_match:
                        # Try with double quotes
                        pattern = r'"failed_generation":\s*"((?:[^"\\]|\\.|"")*)"'
                        failed_gen_match = re.search(pattern, error_str, re.DOTALL)
                    
                    if failed_gen_match:
                        content = failed_gen_match.group(1)
                        # Unescape the content
                        try:
                            content = content.encode('latin1').decode('unicode_escape')
                        except:
                            pass  # If unescaping fails, use as-is
                
                if content:
                    # Try to parse markdown/text and extract tasks
                    tasks = parse_markdown_tasks(content)
                    if tasks:
                        response = TaskPlan(implementation_steps=tasks)
                        print(f"Successfully parsed {len(tasks)} tasks from markdown content")
            except Exception as parse_err:
                print(f"Error parsing markdown: {parse_err}")
                import traceback
                traceback.print_exc()
        
        # Handle case where LLM returns a list instead of object
        if response is None:
            if 'Input should be a valid dictionary' in error_str or 'input_type=list' in error_str:
                # Try to extract from error message or raw response
                try:
                    # Try with json_schema as fallback
                    response = llm.with_structured_output(TaskPlan, method='json_schema').invoke(architect_prompt(plan_str, design_system, tech_stack))
                except Exception as e2:
                    # Last resort: try to extract from raw response
                    try:
                        raw_response = llm.invoke(architect_prompt(plan_str, design_system, tech_stack))
                        content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
                        
                        # First try to parse markdown if JSON not found
                        tasks = parse_markdown_tasks(content)
                        if tasks:
                            response = TaskPlan(implementation_steps=tasks)
                        else:
                            # Try to find JSON object in response
                            json_match = re.search(r'(\{.*"implementation_steps".*\})', content, re.DOTALL)
                            if json_match:
                                parsed = json.loads(json_match.group(1))
                                response = TaskPlan(**parsed)
                            else:
                                # Try to find array and extract first element
                                array_match = re.search(r'(\[.*"implementation_steps".*\])', content, re.DOTALL)
                                if array_match:
                                    parsed_list = json.loads(array_match.group(1))
                                    if parsed_list and isinstance(parsed_list, list) and len(parsed_list) > 0:
                                        # Extract the TaskPlan object from the list
                                        if isinstance(parsed_list[0], dict) and 'implementation_steps' in parsed_list[0]:
                                            response = TaskPlan(**parsed_list[0])
                                        else:
                                            raise ValueError(f"Invalid structure in list: {parsed_list[0]}")
                                    else:
                                        raise ValueError(f"Failed to parse TaskPlan from list: {e2}")
                                else:
                                    raise ValueError(f"Failed to parse TaskPlan: {e2}")
                    except Exception as e3:
                        raise ValueError(f"Failed to parse TaskPlan from LLM response. Original error: {original_error_str or 'Unknown error'}, Fallback error: {e3}")
            else:
                # If we haven't handled it yet, try one more time with raw response
                if response is None:
                    try:
                        raw_response = llm.invoke(architect_prompt(plan_str, design_system, tech_stack))
                        content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
                        tasks = parse_markdown_tasks(content)
                        if tasks:
                            response = TaskPlan(implementation_steps=tasks)
                        else:
                            raise ValueError(f"Failed to parse TaskPlan: {original_error_str or 'Unknown error'}")
                    except Exception as e4:
                        raise ValueError(f"Failed to parse TaskPlan from LLM response. Original error: {original_error_str or 'Unknown error'}, Final error: {e4}")

    if response is None:
        raise ValueError("Architect did not return a valid response")

    response.plan = plan
    
    # Validate and filter out any framework files
    forbidden_extensions = ['.tsx', '.jsx', '.ts', '.vue']
    forbidden_paths = ['src/', 'node_modules/', 'package.json', 'vite.config', 'webpack.config']
    forbidden_imports = ['react', 'vue', 'angular', '@angular', '@vue', 'react-dom']
    
    original_count = len(response.implementation_steps)
    filtered_steps = []
    removed_files = []
    
    for step in response.implementation_steps:
        filepath = step.filepath.lower()
        should_remove = False
        
        # Check for forbidden extensions
        if any(filepath.endswith(ext) for ext in forbidden_extensions):
            should_remove = True
            removed_files.append(f"{step.filepath} (forbidden extension)")
        
        # Check for forbidden paths
        if any(forbidden in filepath for forbidden in forbidden_paths):
            should_remove = True
            removed_files.append(f"{step.filepath} (forbidden path)")
        
        # Check for forbidden imports
        if step.required_imports:
            for imp in step.required_imports:
                if any(forbidden in imp.lower() for forbidden in forbidden_imports):
                    should_remove = True
                    removed_files.append(f"{step.filepath} (contains framework import: {imp})")
                    break
        
        if not should_remove:
            filtered_steps.append(step)
    
    if removed_files:
        print(f"\n⚠️  ARCHITECT VALIDATION: Removed {len(removed_files)} framework files:")
        for removed in removed_files:
            print(f"   - {removed}")
        response.implementation_steps = filtered_steps
        print(f"   Kept {len(filtered_steps)} vanilla HTML/CSS/JS files")
    
    # LAYER 1: PREVENTION - Calculate correct import paths
    print("\n🔗 LAYER 1: Calculating correct import paths...")
    file_path_map = {step.filepath: step for step in response.implementation_steps}
    
    for step in response.implementation_steps:
        if not step.required_imports:
            continue
        
        current_filepath = step.filepath
        current_ext = Path(current_filepath).suffix.lower()
        current_dir = str(Path(current_filepath).parent) if Path(current_filepath).parent.name else '.'
        
        fixed_imports = []
        for import_path in step.required_imports:
            # Skip external URLs and node_modules
            if import_path.startswith('http') or import_path.startswith('//') or import_path.startswith('node_modules') or import_path.startswith('@'):
                fixed_imports.append(import_path)
                continue
            
            # Normalize path
            import_path_clean = import_path.replace('\\', '/').lstrip('/')
            
            # Find the target file
            target_file = None
            
            # Try exact match first
            if import_path_clean in file_path_map:
                target_file = import_path_clean
            else:
                # Try to find file that matches
                for filepath in file_path_map.keys():
                    # Check if import path matches filepath (with or without extension)
                    if filepath == import_path_clean or filepath.endswith(import_path_clean):
                        target_file = filepath
                        break
                    # Check if import path matches filename
                    if Path(filepath).name == import_path_clean or Path(filepath).stem == import_path_clean.split('.')[0]:
                        target_file = filepath
                        break
            
            if target_file:
                # Calculate relative path from current file to target file
                current_path = Path(current_filepath)
                target_path = Path(target_file)
                
                # Get directory parts
                current_parts = list(current_path.parent.parts) if current_path.parent.name else []
                target_parts = list(target_path.parent.parts) if target_path.parent.name else []
                
                # Normalize (remove empty parts)
                current_parts = [p for p in current_parts if p and p != '.']
                target_parts = [p for p in target_parts if p and p != '.']
                
                # Find common prefix
                common_len = 0
                for i in range(min(len(current_parts), len(target_parts))):
                    if current_parts[i] == target_parts[i]:
                        common_len = i + 1
                    else:
                        break
                
                # Calculate relative path
                up_levels = len(current_parts) - common_len
                down_parts = target_parts[common_len:]
                
                # Build relative import path
                if current_ext == '.css':
                    # CSS @import: include .css extension
                    target_filename = target_path.name  # Include extension
                    if up_levels == 0 and not down_parts:
                        relative_path = f"./{target_filename}"
                    else:
                        up_path = '../' * up_levels
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_path = f"{up_path}{down_path}{target_filename}"
                elif current_ext in ['.html', '.htm']:
                    # HTML link/script: relative to HTML file location
                    target_filename = target_path.name  # Include extension
                    if up_levels == 0 and not down_parts:
                        relative_path = target_filename
                    else:
                        up_path = '../' * up_levels if up_levels > 0 else ''
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_path = f"{up_path}{down_path}{target_filename}"
                else:
                    # JS files: no imports in vanilla JS, but keep original if provided
                    relative_path = import_path
                
                fixed_imports.append(relative_path)
                if relative_path != import_path:
                    print(f"   ✓ Fixed import in {current_filepath}: '{import_path}' → '{relative_path}'")
            else:
                # Keep original if we can't find target
                fixed_imports.append(import_path)
                print(f"   ⚠️  Could not resolve import '{import_path}' in {current_filepath}")
        
        # Update required_imports with fixed paths
        step.required_imports = fixed_imports
    
    # Auto-populate required_imports for HTML files that are missing CSS/JS paths
    print("\n🔗 LAYER 1: Auto-populating HTML file imports...")
    all_css_files = [step.filepath for step in response.implementation_steps if step.filepath.endswith('.css')]
    all_js_files = [step.filepath for step in response.implementation_steps if step.filepath.endswith('.js')]
    
    for step in response.implementation_steps:
        current_ext = Path(step.filepath).suffix.lower()
        if current_ext in ['.html', '.htm']:
            # If HTML file has empty required_imports, populate with CSS and JS files
            if not step.required_imports:
                html_imports = []
                # Add all CSS files (relative to HTML file location)
                for css_file in all_css_files:
                    html_path = Path(step.filepath)
                    css_path = Path(css_file)
                    
                    # Calculate relative path from HTML to CSS
                    html_parts = list(html_path.parent.parts) if html_path.parent.name else []
                    css_parts = list(css_path.parent.parts) if css_path.parent.name else []
                    
                    html_parts = [p for p in html_parts if p and p != '.']
                    css_parts = [p for p in css_parts if p and p != '.']
                    
                    common_len = 0
                    for i in range(min(len(html_parts), len(css_parts))):
                        if html_parts[i] == css_parts[i]:
                            common_len = i + 1
                        else:
                            break
                    
                    up_levels = len(html_parts) - common_len
                    down_parts = css_parts[common_len:]
                    
                    css_filename = css_path.name
                    if up_levels == 0 and not down_parts:
                        relative_css = css_filename
                    else:
                        up_path = '../' * up_levels if up_levels > 0 else ''
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_css = f"{up_path}{down_path}{css_filename}"
                    
                    html_imports.append(relative_css)
                
                # Add all JS files (relative to HTML file location)
                for js_file in all_js_files:
                    html_path = Path(step.filepath)
                    js_path = Path(js_file)
                    
                    # Calculate relative path from HTML to JS
                    html_parts = list(html_path.parent.parts) if html_path.parent.name else []
                    js_parts = list(js_path.parent.parts) if js_path.parent.name else []
                    
                    html_parts = [p for p in html_parts if p and p != '.']
                    js_parts = [p for p in js_parts if p and p != '.']
                    
                    common_len = 0
                    for i in range(min(len(html_parts), len(js_parts))):
                        if html_parts[i] == js_parts[i]:
                            common_len = i + 1
                        else:
                            break
                    
                    up_levels = len(html_parts) - common_len
                    down_parts = js_parts[common_len:]
                    
                    js_filename = js_path.name
                    if up_levels == 0 and not down_parts:
                        relative_js = js_filename
                    else:
                        up_path = '../' * up_levels if up_levels > 0 else ''
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_js = f"{up_path}{down_path}{js_filename}"
                    
                    html_imports.append(relative_js)
                
                if html_imports:
                    step.required_imports = html_imports
                    print(f"   ✓ Auto-populated imports for {step.filepath}: {html_imports}")
    
    print("✅ LAYER 1: Path calculation complete\n")
    
    # DEBUG: Print full architect output
    print("\n" + "="*80)
    print("🏗️  ARCHITECT AGENT - FULL OUTPUT")
    print("="*80)
    print(f"\n📋 Task Plan Summary:")
    print(f"  Total Implementation Steps: {len(response.implementation_steps)}")
    
    print(f"\n📝 Detailed Implementation Steps:")
    for i, step in enumerate(response.implementation_steps, 1):
        print(f"\n  Step {i}:")
        print(f"    Filepath: {step.filepath}")
        print(f"    Description: {step.file_description}")
        print(f"    Required Imports: {step.required_imports}")
        print(f"    Task Description: {step.task_description[:200]}..." if len(step.task_description) > 200 else f"    Task Description: {step.task_description}")
    
    print(f"\n📦 Full TaskPlan Object:")
    try:
        import json
        # Convert to dict for pretty printing
        task_plan_dict = {
            "implementation_steps": [
                {
                    "filepath": step.filepath,
                    "file_description": step.file_description,
                    "required_imports": step.required_imports,
                    "task_description": step.task_description
                }
                for step in response.implementation_steps
            ]
        }
        print(json.dumps(task_plan_dict, indent=2))
    except Exception as e:
        print(f"  (Could not serialize to JSON: {e})")
        print(f"  Raw response: {response}")
    
    print("="*80 + "\n")
    
    # Validate that index.html exists for web projects
    # Check if any file paths suggest this is a web project
    filepaths = [step.filepath for step in response.implementation_steps]
    is_web_project = any(
        'package.json' in fp or 
        'vite.config' in fp or 
        'src/main' in fp or 
        'src/App' in fp or
        '.html' in fp or
        'react' in str(plan).lower() or
        'vue' in str(plan).lower() or
        'angular' in str(plan).lower()
        for fp in filepaths
    )
    
    # Extract components and features from plan for cross-referencing
    components = []
    features = []
    if hasattr(plan, 'design_system') and plan.design_system and hasattr(plan.design_system, 'components'):
        components = plan.design_system.components if plan.design_system.components else []
    if hasattr(plan, 'features'):
        features = plan.features if plan.features else []
    
    # Build list of expected HTML elements/classes/IDs based on components and features
    expected_selectors = []
    if 'navigation' in components or any('nav' in f.lower() for f in features):
        expected_selectors.extend(['#navigation', '.nav-menu', '.nav-toggle', '.nav-link'])
    if 'hero' in components or any('hero' in f.lower() for f in features):
        expected_selectors.extend(['#hero', '.hero-section', '.hero-content'])
    if 'button' in components or any('button' in f.lower() for f in features):
        expected_selectors.extend(['.button', '.btn', 'button'])
    if 'card' in components or any('card' in f.lower() for f in features):
        expected_selectors.extend(['.card', '.card-container'])
    if 'form' in components or any('form' in f.lower() or 'contact' in f.lower() for f in features):
        expected_selectors.extend(['#contact-form', '.form', '.form-input', '.form-button'])
    if 'footer' in components:
        expected_selectors.extend(['footer', '#footer'])
    
    # For vanilla HTML/CSS/JS, ensure all three mandatory files exist
    has_index_html = any('index.html' in fp.lower() for fp in filepaths)
    has_main_css = any('styles/main.css' in fp.lower() for fp in filepaths)
    has_main_js = any('scripts/main.js' in fp.lower() for fp in filepaths)
    
    # Find all CSS and JS files
    css_files = [step.filepath for step in response.implementation_steps if step.filepath.endswith('.css')]
    js_files = [step.filepath for step in response.implementation_steps if step.filepath.endswith('.js')]
    
    # Ensure index.html exists
    if not has_index_html:
        print("🔧 Adding index.html task for vanilla HTML/CSS/JS project...")
        
        # Calculate relative paths from index.html (which is in root)
        html_imports = []
        for css_file in css_files:
            html_imports.append(css_file)  # e.g., "styles/main.css"
        for js_file in js_files:
            html_imports.append(js_file)  # e.g., "scripts/main.js"
        
        # If no CSS/JS files exist yet, add default paths
        if not html_imports:
            html_imports = ["styles/main.css", "scripts/main.js"]
        
        index_desc = f"Create index.html with <!DOCTYPE html>, <html lang='en'>, <head> with meta charset='UTF-8' and viewport for responsive design, <title> tag, link to CSS files ({', '.join(html_imports) if html_imports else 'styles/main.css'}), and <body> with semantic HTML structure. Include semantic elements (header, nav, main, section, footer) with appropriate classes and IDs based on components: {', '.join(components) if components else 'navigation, hero, cards, forms, footer'}. Link to JS files ({', '.join(html_imports) if html_imports else 'scripts/main.js'}) with defer attribute at end of body. Use EXACT paths from required_imports for all <link> and <script> tags."
        
        # Insert index.html as the first task
        index_task = ImplementationTask(
            filepath="index.html",
            file_description="Main HTML entry point for the vanilla HTML/CSS/JS website",
            required_imports=html_imports,
            task_description=index_desc
        )
        response.implementation_steps.insert(0, index_task)
        print(f"   ✓ Added index.html task with required_imports: {html_imports}")
    
    # Ensure styles/main.css exists
    if not has_main_css:
        print("🔧 Adding styles/main.css task for vanilla HTML/CSS/JS project...")
        
        # Build CSS task description with explicit references to HTML selectors
        css_selectors_text = ", ".join(expected_selectors[:10]) if expected_selectors else "header, nav, main, section, footer, .button, .card, .form"
        css_desc = f"Define :root CSS variables for the full design system (colors, typography, spacing, breakpoints). Add a basic CSS reset, base typography styles, layout utilities (flex/grid helpers). Style ALL HTML elements, classes, and IDs that will be used in index.html - including semantic elements (header, nav, main, section, footer), component classes and IDs: {css_selectors_text}. Reference the components list from the plan ({', '.join(components) if components else 'navigation, hero, buttons, cards, forms, footer'}) to ensure every component has corresponding CSS. Implement a mobile-first approach with media queries using the provided breakpoints and ensure focus/hover/active states are clearly visible for all interactive elements."
        
        css_task = ImplementationTask(
            filepath="styles/main.css",
            file_description="Main stylesheet with CSS variables, base styles, layout, component styles, and responsive design",
            required_imports=[],
            task_description=css_desc
        )
        
        # Insert CSS task after index.html (position 1)
        insert_pos = 1 if has_index_html else 1
        response.implementation_steps.insert(insert_pos, css_task)
        print(f"   ✓ Added styles/main.css task with references to HTML selectors")
    
    # Ensure scripts/main.js exists
    if not has_main_js:
        print("🔧 Adding scripts/main.js task for vanilla HTML/CSS/JS project...")
        
        # Build JS task description with explicit references to HTML elements
        js_elements_text = ", ".join(expected_selectors[:10]) if expected_selectors else "#navigation, .nav-toggle, .button, #contact-form"
        js_desc = f"Attach a DOMContentLoaded listener, then implement all interactive behavior described in the plan. Use querySelector/querySelectorAll to select elements by their IDs and classes from index.html (e.g., {js_elements_text}). Implement functionality for: mobile navigation toggle (if nav exists), form validation/handling (if forms exist), smooth scrolling (if navigation links exist), interactive toggles/accordions (if applicable), and any other interactivity mentioned in the plan ({', '.join(features[:5]) if features else 'interactive elements'}). Use addEventListener for events and small, focused functions. Add null checks before using DOM elements to avoid runtime errors. Reference specific IDs and classes that will be present in the HTML."
        
        js_task = ImplementationTask(
            filepath="scripts/main.js",
            file_description="Main JavaScript file for all interactivity and DOM manipulation using vanilla ES6+",
            required_imports=[],
            task_description=js_desc
        )
        
        # Insert JS task after CSS (position 2)
        insert_pos = 2 if (has_index_html and has_main_css) else (1 if has_index_html else 0)
        response.implementation_steps.insert(insert_pos, js_task)
        print(f"   ✓ Added scripts/main.js task with references to HTML elements")
    
    # Update index.html's required_imports to include the CSS/JS files we just added
    for step in response.implementation_steps:
        if step.filepath.lower() == 'index.html':
            # Ensure required_imports includes styles/main.css and scripts/main.js
            if 'styles/main.css' not in step.required_imports:
                step.required_imports.append('styles/main.css')
            if 'scripts/main.js' not in step.required_imports:
                step.required_imports.append('scripts/main.js')
            print(f"   ✓ Updated index.html required_imports: {step.required_imports}")
            break
    
    return {"task_plan": response}

@log_agent_execution("framework_detector")
def framework_detector_agent(state: dict) -> dict:
    """Detect and validate framework choice"""
    plan = state.get('plan')
    task_plan = state.get('task_plan')
    
    # Use plan if available, otherwise use task_plan
    plan_str = str(plan) if plan else str(task_plan)
    
    try:
        response = llm.with_structured_output(FrameworkInfo).invoke(framework_detector_prompt(plan_str))
        return {"framework_info": response}
    except Exception as e:
        # Default to vanilla if detection fails
        print(f"Framework detection failed: {e}, defaulting to vanilla")
        default_framework = FrameworkInfo(
            framework="vanilla",
            version="latest",
            build_tool="none",
            requires_build=False,
            config_files=[]
        )
        return {"framework_info": default_framework}

@log_agent_execution("coder")
def coder_agent(state: dict) -> dict:
    implementation_steps = state["task_plan"].implementation_steps
    system_prompt = coder_system_prompt()
    files: list[FileCode] = []
    errors: list[str] = []
    import json
    import re

    for current_task in implementation_steps:
        user_prompt = current_task.task_description
        filepath = current_task.filepath
        file_description = getattr(current_task, 'file_description', '')
        required_imports = getattr(current_task, 'required_imports', [])
        
        # Create explicit prompt with filepath, task, and imports
        imports_section = ""
        if required_imports:
            imports_list = ", ".join(required_imports)
            file_ext = Path(filepath).suffix.lower()
            
            if file_ext in ['.html', '.htm']:
                imports_section = f"\nIMPORTANT: Use these exact paths in <link> and <script> tags: {imports_list}\n"
            elif file_ext == '.css':
                imports_section = "\nIMPORTANT: Define CSS custom properties in :root selector at the top.\n"
        
        explicit_prompt = f"""FILEPATH: {filepath}
TASK: {user_prompt}{imports_section}
Write complete code for this file. Return JSON: {{"filepath": "{filepath}", "code": "complete code here"}}"""
        
        try:
            # Use default method (not json_schema) to avoid schema format issues
            response = llm.with_structured_output(FileCode).invoke(system_prompt + explicit_prompt)
            files.append(response)
        except Exception as e:
            # Try to extract JSON from error message's failed_generation field
            error_str = str(e)
            parsed_data = None
            
            # Check if error contains failed_generation
            failed_gen_content = None
            if 'failed_generation' in error_str:
                try:
                    # Try to parse the error as a Python dict using ast.literal_eval
                    dict_start = error_str.find("{'error':")
                    if dict_start == -1:
                        dict_start = error_str.find('{"error":')
                    
                    if dict_start != -1:
                        # Find the matching closing brace for the outer dict
                        brace_count = 0
                        i = dict_start
                        dict_end = -1
                        while i < len(error_str):
                            if error_str[i] == '{':
                                brace_count += 1
                            elif error_str[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    dict_end = i + 1
                                    break
                            i += 1
                        
                        if dict_end != -1:
                            try:
                                error_dict_str = error_str[dict_start:dict_end]
                                error_dict = ast.literal_eval(error_dict_str)
                                if isinstance(error_dict, dict):
                                    error_obj = error_dict.get('error', {})
                                    if isinstance(error_obj, dict):
                                        failed_gen_content = error_obj.get('failed_generation', '')
                            except:
                                pass
                    
                    # If ast.literal_eval didn't work, try regex extraction
                    if not failed_gen_content:
                        pattern = r"'failed_generation':\s*'((?:[^'\\]|\\.|'')*)'"
                        match = re.search(pattern, error_str, re.DOTALL)
                        if match:
                            failed_gen_content = match.group(1)
                            # Unescape the string
                            try:
                                failed_gen_content = failed_gen_content.encode('latin1').decode('unicode_escape')
                            except:
                                pass
                        else:
                            # Try with double quotes
                            pattern = r'"failed_generation":\s*"((?:[^"\\]|\\.|"")*)"'
                            match = re.search(pattern, error_str, re.DOTALL)
                            if match:
                                failed_gen_content = match.group(1)
                                try:
                                    failed_gen_content = failed_gen_content.encode('latin1').decode('unicode_escape')
                                except:
                                    pass
                    
                    # Try to parse as JSON if it looks like JSON
                    if failed_gen_content:
                        try:
                            parsed_data = json.loads(failed_gen_content)
                        except:
                            # If not JSON, check if it's conversational text asking for more info
                            conversational_indicators = [
                                "could you please provide",
                                "please provide",
                                "i need more information",
                                "task description appears to be missing",
                                "could you provide the full details",
                                "i'm ready to write",
                                "once i have"
                            ]
                            is_conversational = any(indicator in failed_gen_content.lower() for indicator in conversational_indicators)
                            
                            if is_conversational:
                                # LLM is asking for more info, but we already have the task description
                                # Skip parsing and let the retry logic handle it
                                failed_gen_content = None
                            else:
                                # Try to find JSON in the content
                                json_match = re.search(r'(\{"filepath"[^}]*"code"[^}]*\})', failed_gen_content, re.DOTALL)
                                if json_match:
                                    json_str = json_match.group(1)
                                    parsed_data = json.loads(json_str)
                except Exception as parse_err:
                    pass
            
            # Check if LLM returned conversational text asking for more info
            conversational_indicators = [
                "could you please provide",
                "please provide",
                "i need more information",
                "task description appears to be missing",
                "could you provide the full details",
                "i'm ready to write",
                "once i have"
            ]
            
            is_conversational = any(indicator in error_str.lower() for indicator in conversational_indicators)
            
            # If we didn't get it from error, try raw LLM invocation with more explicit prompt
            if not parsed_data:
                try:
                    # Use even more explicit prompt if LLM was conversational
                    if is_conversational:
                        retry_prompt = f"""
CRITICAL: You already have ALL the information needed. Write the code NOW.

TASK DESCRIPTION: {user_prompt}
FILEPATH: {filepath}

Return ONLY this JSON format (no explanations, no questions):
{{"filepath": "{filepath}", "code": "write complete code here based on task description"}}

Write the code immediately. Do not ask for more information.
"""
                    else:
                        retry_prompt = system_prompt + explicit_prompt + "\n\nIMPORTANT: Return ONLY valid JSON in this exact format: {\"filepath\": \"" + filepath + "\", \"code\": \"your code here\"}"
                    
                    raw_response = llm.invoke(retry_prompt)
                    content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
                    
                    # Extract JSON from response - try multiple patterns
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
                    if not json_match:
                        # Try simpler pattern
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    
                    if json_match:
                        json_str = json_match.group()
                        # Handle escaped characters
                        json_str = json_str.replace('\\n', '\n').replace('\\"', '"')
                        parsed_data = json.loads(json_str)
                except Exception as raw_err:
                    # If still failing, try one more time with filepath explicitly set
                    if not parsed_data and filepath:
                        try:
                            # Generate a basic code structure based on filepath
                            # This is a last resort fallback
                            file_ext = filepath.split('.')[-1] if '.' in filepath else ''
                            if file_ext in ['js', 'jsx']:
                                basic_code = f"// {filepath}\n// {user_prompt}\n\n// TODO: Implement based on task description"
                            elif file_ext == 'tsx':
                                basic_code = f"// {filepath}\n// {user_prompt}\n\n// TODO: Implement based on task description"
                            elif file_ext == 'json':
                                basic_code = "{}"
                            elif file_ext == 'html':
                                basic_code = f"<!DOCTYPE html>\n<html>\n<head><title>{filepath}</title></head>\n<body>\n<!-- {user_prompt} -->\n</body>\n</html>"
                            elif file_ext == 'css':
                                basic_code = f"/* {filepath} */\n/* {user_prompt} */"
                            else:
                                basic_code = f"# {filepath}\n# {user_prompt}\n\n# TODO: Implement based on task description"
                            
                            parsed_data = {
                                'filepath': filepath,
                                'code': basic_code
                            }
                        except:
                            pass
            
            # Process parsed data
            if parsed_data:
                try:
                    # Handle case where LLM returns tool call format: {'name': '...', 'arguments': {...}}
                    if 'arguments' in parsed_data and isinstance(parsed_data['arguments'], dict):
                        parsed_data = parsed_data['arguments']
                    
                    # Handle case where LLM returns schema format with nested properties
                    if 'properties' in parsed_data and isinstance(parsed_data['properties'], dict):
                        # Extract actual values from properties
                        filepath_val = parsed_data['properties'].get('filepath', '')
                        code_val = parsed_data['properties'].get('code', '')
                        
                        # If values are still dicts (schema format), try to get default or example
                        if isinstance(filepath_val, dict):
                            filepath_val = filepath_val.get('default') or filepath_val.get('example') or filepath_val.get('const') or ''
                        if isinstance(code_val, dict):
                            code_val = code_val.get('default') or code_val.get('example') or code_val.get('const') or ''
                        
                        parsed_data = {
                            'filepath': str(filepath_val) if filepath_val else '',
                            'code': str(code_val) if code_val else ''
                        }
                    
                    # Check if parsed_data looks like file content (e.g., package.json structure) instead of FileCode structure
                    # If it has fields like 'name', 'version', 'scripts', 'dependencies', etc., it's likely package.json content
                    # Or if it doesn't have 'filepath' and 'code', it might be the actual file content
                    if 'filepath' not in parsed_data or 'code' not in parsed_data:
                        # Check if this looks like package.json content
                        package_json_fields = {'name', 'version', 'scripts', 'dependencies', 'devDependencies', 'private', 'type', 'main', 'module'}
                        if package_json_fields.intersection(set(parsed_data.keys())):
                            # This is package.json content, convert to JSON string
                            import json
                            code_content = json.dumps(parsed_data, indent=2)
                            parsed_data = {
                                'filepath': filepath,
                                'code': code_content
                            }
                        elif 'filepath' not in parsed_data:
                            # If no filepath, use the one from the task
                            # Check if parsed_data might be the code content itself (string or dict)
                            if isinstance(parsed_data, dict) and len(parsed_data) > 0:
                                # Try to convert dict to JSON string if it looks like structured data
                                import json
                                try:
                                    code_content = json.dumps(parsed_data, indent=2)
                                    parsed_data = {
                                        'filepath': filepath,
                                        'code': code_content
                                    }
                                except:
                                    # If JSON conversion fails, convert to string representation
                                    parsed_data = {
                                        'filepath': filepath,
                                        'code': str(parsed_data)
                                    }
                            else:
                                # If it's a string or other type, use it as code
                                parsed_data = {
                                    'filepath': filepath,
                                    'code': str(parsed_data)
                                }
                    
                    # Ensure we have the required fields now
                    if 'filepath' not in parsed_data or 'code' not in parsed_data:
                        raise ValueError(f"Missing required fields in parsed response: {list(parsed_data.keys())}")
                    
                    response = FileCode(**parsed_data)
                    files.append(response)
                except Exception as parse_err:
                    # If parsing fails, try to create FileCode with the parsed_data as code content
                    try:
                        import json
                        if isinstance(parsed_data, dict):
                            code_content = json.dumps(parsed_data, indent=2)
                        else:
                            code_content = str(parsed_data)
                        response = FileCode(filepath=filepath, code=code_content)
                        files.append(response)
                        print(f"Created FileCode from fallback parsing for {filepath}")
                    except Exception as fallback_err:
                        raise ValueError(f"Failed to create FileCode from parsed data: {parse_err}. Fallback also failed: {fallback_err}. Data: {str(parsed_data)[:200]}")
            else:
                error_msg = f"Failed to parse FileCode from LLM response for {filepath}. Error: {e}"
                errors.append(error_msg)
                print(error_msg)
                # Try to create a placeholder file to continue
                try:
                    placeholder_code = f"// Error generating code for {filepath}\n// Task: {user_prompt}\n// Please review and implement manually\n"
                    files.append(FileCode(filepath=filepath, code=placeholder_code))
                    print(f"Created placeholder file for {filepath}")
                except:
                    pass
    
    if errors:
        print(f"Coder agent encountered {len(errors)} errors:")
        for error in errors[:5]:  # Print first 5
            print(f"  - {error}")
    
    return {"files": files, "coder_errors": errors}

def validate_syntax(files: list[FileCode]) -> list[str]:
    """Validate syntax of code files and return list of errors"""
    import re
    syntax_errors = []
    
    for file in files:
        filepath = file.filepath
        code = file.code
        ext = filepath.split('.')[-1].lower() if '.' in filepath else ''
        
        # Basic syntax checks
        errors = []
        
        # Check for unclosed brackets/braces/parentheses
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            errors.append(f"{filepath}: Unmatched braces ({{: {open_braces}, }}: {close_braces})")
        
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            errors.append(f"{filepath}: Unmatched brackets ([{open_brackets}, ]: {close_brackets})")
        
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            errors.append(f"{filepath}: Unmatched parentheses ((: {open_parens}, ): {close_parens})")
        
        # Check for unclosed strings (basic check)
        # Count quotes, but ignore escaped quotes
        single_quotes = len(re.findall(r"(?<!\\)'", code))
        double_quotes = len(re.findall(r'(?<!\\)"', code))
        backticks = code.count('`')
        
        if single_quotes % 2 != 0:
            errors.append(f"{filepath}: Unclosed single-quoted string")
        if double_quotes % 2 != 0:
            errors.append(f"{filepath}: Unclosed double-quoted string")
        if backticks % 2 != 0:
            errors.append(f"{filepath}: Unclosed template literal (backticks)")
        
        # JSX/TSX specific checks
        if ext in ['jsx', 'tsx']:
            # Check for unclosed JSX tags (basic)
            jsx_open_tags = len(re.findall(r'<[^/!][^>]*>', code))
            jsx_close_tags = len(re.findall(r'</[^>]+>', code))
            jsx_self_closing = len(re.findall(r'<[^>]+/>', code))
            # Self-closing tags count as both open and close
            if jsx_open_tags - jsx_self_closing != jsx_close_tags:
                errors.append(f"{filepath}: Possible unclosed JSX tags")
        
        # Check for common syntax errors
        # Missing return statement in functions (basic check)
        if ext in ['js', 'jsx', 'ts', 'tsx']:
            # Check for function declarations without return (warning, not error)
            function_pattern = r'function\s+\w+\s*\([^)]*\)\s*\{[^}]*\}'
            functions = re.findall(function_pattern, code, re.DOTALL)
            for func in functions:
                if 'return' not in func and 'void' not in func and '=>' not in func:
                    # This is just a warning, not necessarily an error
                    pass
        
        syntax_errors.extend(errors)
    
    return syntax_errors

def detect_runtime_issues(files: list[FileCode]) -> list[str]:
    """Detect potential runtime issues in code"""
    import re
    runtime_issues = []
    
    for file in files:
        filepath = file.filepath
        code = file.code
        ext = filepath.split('.')[-1].lower() if '.' in filepath else ''
        
        issues = []
        
        if ext in ['js', 'jsx', 'ts', 'tsx']:
            # Check for potential null/undefined access
            # Pattern: variable.property or variable[index] without null check
            unsafe_access = re.findall(r'(\w+)\.[\w]+(?!\s*\?)', code)
            # This is a basic check - could be improved
            
            # Check for array access without bounds checking
            array_access = re.findall(r'(\w+)\[(\w+|\d+)\]', code)
            
            # Check for React hooks issues
            if ext in ['jsx', 'tsx']:
                # Hooks called conditionally
                hook_pattern = r'(use\w+)\s*\('
                hook_calls = re.findall(hook_pattern, code)
                if hook_calls:
                    # Check if hooks are inside conditionals (basic check)
                    lines = code.split('\n')
                    hook_search_pattern = r'use\w+\s*\('
                    hook_name_pattern = r'(use\w+)'
                    for i, line in enumerate(lines):
                        if re.search(hook_search_pattern, line):
                            # Extract hook name
                            hook_match = re.search(hook_name_pattern, line)
                            hook_name = hook_match.group(1) if hook_match else 'hook'
                            # Check if previous non-empty line is a conditional
                            for j in range(i-1, max(0, i-5), -1):
                                prev_line = lines[j].strip()
                                if prev_line and not prev_line.startswith('//'):
                                    if any(keyword in prev_line for keyword in ['if', 'else', 'for', 'while', 'switch']):
                                        issues.append(f"{filepath}: Hook '{hook_name}' may be called conditionally (line {i+1})")
                                    break
            
            # Check for missing error handling in async functions
            async_functions = re.findall(r'async\s+function\s+\w+', code)
            for async_func in async_functions:
                func_start = code.find(async_func)
                # Find the function body
                brace_start = code.find('{', func_start)
                if brace_start != -1:
                    # Count braces to find function end
                    brace_count = 1
                    func_end = brace_start + 1
                    while func_end < len(code) and brace_count > 0:
                        if code[func_end] == '{':
                            brace_count += 1
                        elif code[func_end] == '}':
                            brace_count -= 1
                        func_end += 1
                    
                    func_body = code[brace_start:func_end]
                    # Check for try-catch
                    if 'await' in func_body and 'try' not in func_body and 'catch' not in func_body:
                        issues.append(f"{filepath}: Async function may need error handling")
        
        runtime_issues.extend(issues)
    
    return runtime_issues

def verify_and_fix_import_paths(files: list[FileCode]) -> list[FileCode]:
    """
    LAYER 2: VERIFICATION - Verify and fix import paths in generated files.
    Handles CSS @import, HTML <link> and <script> tags.
    
    Args:
        files: List of FileCode objects
        
    Returns:
        List of FileCode objects with fixed import paths
    """
    import re
    
    # Build file path map
    file_path_map = {f.filepath: f for f in files}
    file_paths = set(file_path_map.keys())
    
    fixed_files = []
    fixes_made = []
    
    for file in files:
        code = file.code
        filepath = file.filepath
        file_ext = Path(filepath).suffix.lower()
        file_dir = str(Path(filepath).parent) if Path(filepath).parent.name else '.'
        modified = False
        
        if file_ext == '.css':
            # Handle CSS @import statements
            pattern = r"@import\s+(?:url\()?['\"]([^'\"]+)['\"]\)?;?"
            
            def replace_css_import(match):
                nonlocal modified
                full_match = match.group(0)
                import_path = match.group(1)
                
                # Skip external URLs
                if import_path.startswith('http') or import_path.startswith('//'):
                    return full_match
                
                # Normalize path
                import_path_clean = import_path.replace('\\', '/').lstrip('/')
                
                # Find target file
                target_file = None
                if import_path_clean in file_paths:
                    target_file = import_path_clean
                else:
                    # Try to find matching file
                    for fp in file_paths:
                        if fp.endswith(import_path_clean) or Path(fp).name == import_path_clean:
                            target_file = fp
                            break
                
                if target_file:
                    # Calculate relative path
                    current_path = Path(filepath)
                    target_path = Path(target_file)
                    
                    current_parts = list(current_path.parent.parts) if current_path.parent.name else []
                    target_parts = list(target_path.parent.parts) if target_path.parent.name else []
                    
                    current_parts = [p for p in current_parts if p and p != '.']
                    target_parts = [p for p in target_parts if p and p != '.']
                    
                    common_len = 0
                    for i in range(min(len(current_parts), len(target_parts))):
                        if current_parts[i] == target_parts[i]:
                            common_len = i + 1
                        else:
                            break
                    
                    up_levels = len(current_parts) - common_len
                    down_parts = target_parts[common_len:]
                    
                    target_filename = target_path.name  # Include .css extension
                    if up_levels == 0 and not down_parts:
                        relative_path = f"./{target_filename}"
                    else:
                        up_path = '../' * up_levels
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_path = f"{up_path}{down_path}{target_filename}"
                    
                    if relative_path != import_path:
                        modified = True
                        fixes_made.append(f"{filepath}: CSS @import '{import_path}' → '{relative_path}'")
                        return full_match.replace(import_path, relative_path)
                
                return full_match
            
            code = re.sub(pattern, replace_css_import, code)
        
        elif file_ext in ['.html', '.htm']:
            # Handle HTML <link> tags
            link_pattern = r'(<link[^>]+href=["\'])([^"\']+)(["\'][^>]*>)'
            
            def replace_link(match):
                nonlocal modified
                prefix = match.group(1)
                href_path = match.group(2)
                suffix = match.group(3)
                
                # Skip external URLs
                if href_path.startswith('http') or href_path.startswith('//'):
                    return match.group(0)
                
                # Normalize path
                href_clean = href_path.replace('\\', '/').lstrip('/')
                
                # Find target file
                target_file = None
                if href_clean in file_paths:
                    target_file = href_clean
                else:
                    for fp in file_paths:
                        if fp.endswith(href_clean) or Path(fp).name == href_clean:
                            target_file = fp
                            break
                
                if target_file:
                    # Calculate relative path from HTML file
                    current_path = Path(filepath)
                    target_path = Path(target_file)
                    
                    current_parts = list(current_path.parent.parts) if current_path.parent.name else []
                    target_parts = list(target_path.parent.parts) if target_path.parent.name else []
                    
                    current_parts = [p for p in current_parts if p and p != '.']
                    target_parts = [p for p in target_parts if p and p != '.']
                    
                    common_len = 0
                    for i in range(min(len(current_parts), len(target_parts))):
                        if current_parts[i] == target_parts[i]:
                            common_len = i + 1
                        else:
                            break
                    
                    up_levels = len(current_parts) - common_len
                    down_parts = target_parts[common_len:]
                    
                    target_filename = target_path.name
                    if up_levels == 0 and not down_parts:
                        relative_path = target_filename
                    else:
                        up_path = '../' * up_levels if up_levels > 0 else ''
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_path = f"{up_path}{down_path}{target_filename}"
                    
                    if relative_path != href_path:
                        modified = True
                        fixes_made.append(f"{filepath}: HTML <link> '{href_path}' → '{relative_path}'")
                        return f"{prefix}{relative_path}{suffix}"
                
                return match.group(0)
            
            code = re.sub(link_pattern, replace_link, code)
            
            # Handle HTML <script> tags
            script_pattern = r'(<script[^>]+src=["\'])([^"\']+)(["\'][^>]*>)'
            
            def replace_script(match):
                nonlocal modified
                prefix = match.group(1)
                src_path = match.group(2)
                suffix = match.group(3)
                
                # Skip external URLs
                if src_path.startswith('http') or src_path.startswith('//'):
                    return match.group(0)
                
                # Normalize path
                src_clean = src_path.replace('\\', '/').lstrip('/')
                
                # Find target file
                target_file = None
                if src_clean in file_paths:
                    target_file = src_clean
                else:
                    for fp in file_paths:
                        if fp.endswith(src_clean) or Path(fp).name == src_clean:
                            target_file = fp
                            break
                
                if target_file:
                    # Calculate relative path from HTML file
                    current_path = Path(filepath)
                    target_path = Path(target_file)
                    
                    current_parts = list(current_path.parent.parts) if current_path.parent.name else []
                    target_parts = list(target_path.parent.parts) if target_path.parent.name else []
                    
                    current_parts = [p for p in current_parts if p and p != '.']
                    target_parts = [p for p in target_parts if p and p != '.']
                    
                    common_len = 0
                    for i in range(min(len(current_parts), len(target_parts))):
                        if current_parts[i] == target_parts[i]:
                            common_len = i + 1
                        else:
                            break
                    
                    up_levels = len(current_parts) - common_len
                    down_parts = target_parts[common_len:]
                    
                    target_filename = target_path.name
                    if up_levels == 0 and not down_parts:
                        relative_path = target_filename
                    else:
                        up_path = '../' * up_levels if up_levels > 0 else ''
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_path = f"{up_path}{down_path}{target_filename}"
                    
                    if relative_path != src_path:
                        modified = True
                        fixes_made.append(f"{filepath}: HTML <script> '{src_path}' → '{relative_path}'")
                        return f"{prefix}{relative_path}{suffix}"
                
                return match.group(0)
            
            code = re.sub(script_pattern, replace_script, code)
        
        if modified:
            fixed_files.append(FileCode(filepath=filepath, code=code))
        else:
            fixed_files.append(file)
    
    if fixes_made:
        print(f"\n🔍 LAYER 2: VERIFICATION - Fixed {len(fixes_made)} import paths:")
        for fix in fixes_made:
            print(f"   ✓ {fix}")
    else:
        print(f"\n✅ LAYER 2: VERIFICATION - All import paths are correct")
    
    return fixed_files

def extract_unstyled_selectors(files: list[FileCode]) -> list[dict]:
    """
    Extract HTML selectors (classes, IDs) that don't have corresponding CSS styles
    
    Args:
        files: List of FileCode objects
        
    Returns:
        List of dictionaries with selector information
    """
    html_files = [{"filepath": f.filepath, "code": f.code} for f in files if f.filepath.endswith(('.html', '.htm'))]
    css_files = [{"filepath": f.filepath, "code": f.code} for f in files if f.filepath.endswith('.css')]
    
    if not html_files or not css_files:
        return []
    
    from agent.validators.css_coverage_validator import validate_css_coverage
    coverage_errors = validate_css_coverage(html_files, css_files)
    
    # Return only warnings (missing styles), not info messages
    return [e for e in coverage_errors if e.get('severity') == 'warning']


def generate_css_enhancement_prompt(missing_selectors: list[dict], css_code: str) -> str:
    """
    Generate a prompt enhancement for adding missing CSS styles
    
    Args:
        missing_selectors: List of unstyled selectors
        css_code: Current CSS code
        
    Returns:
        Enhancement text to add to prompt
    """
    if not missing_selectors:
        return ""
    
    selectors_by_type = {"class": [], "id": [], "element": []}
    for selector in missing_selectors[:20]:  # Limit to first 20
        selector_type = selector.get('selector_type', 'class')
        selector_name = selector.get('selector', '')
        if selector_type in selectors_by_type:
            selectors_by_type[selector_type].append(selector_name)
    
    enhancement = "\n\nCRITICAL: MISSING CSS STYLES DETECTED:\n"
    enhancement += "The following HTML selectors are used but have NO corresponding CSS styles:\n\n"
    
    if selectors_by_type["class"]:
        enhancement += f"Classes: {', '.join(selectors_by_type['class'][:10])}\n"
    if selectors_by_type["id"]:
        enhancement += f"IDs: {', '.join(selectors_by_type['id'][:10])}\n"
    if selectors_by_type["element"]:
        enhancement += f"Elements: {', '.join(selectors_by_type['element'][:10])}\n"
    
    enhancement += "\nYOU MUST:\n"
    enhancement += "1. Add complete CSS rules for ALL unstyled selectors listed above\n"
    enhancement += "2. Use modern design patterns:\n"
    enhancement += "   - Proper spacing (padding, margin) using CSS variables\n"
    enhancement += "   - Colors from design system (background-color, color, border-color)\n"
    enhancement += "   - Typography (font-family, font-size, font-weight, line-height)\n"
    enhancement += "   - Layout (display, flex/grid, width, height, max-width)\n"
    enhancement += "   - Visual effects (border-radius, box-shadow, transitions)\n"
    enhancement += "   - Interactive states (:hover, :focus, :active)\n"
    enhancement += "   - Responsive design (media queries)\n"
    enhancement += "3. Ensure styles are visually appealing and modern\n"
    enhancement += "4. Don't leave any selector unstyled\n"
    
    return enhancement


@log_agent_execution("validator_fixer")
def validator_fixer_agent(state: dict) -> dict:
    """
    Consolidated Validator and Fixer agent that validates and fixes errors iteratively.
    Combines validation and debugging into a single focused node.
    
    Args:
        state: Current agent state
    """
    files = state["files"]
    max_iterations = 3  # Maximum iterations for fixing
    iteration = state.get("validator_iteration", 0)
    
    print(f"Validator/Fixer iteration {iteration + 1}/{max_iterations}")
    
    # LAYER 2: VERIFICATION - Verify and fix import paths first
    print("\n🔍 LAYER 2: Verifying and fixing import paths...")
    files = verify_and_fix_import_paths(files)
    
    # Check CSS coverage - ensure all HTML classes/IDs are styled
    print("\n🎨 Checking CSS coverage...")
    html_files = [{"filepath": f.filepath, "code": f.code} for f in files if f.filepath.endswith(('.html', '.htm'))]
    css_files = [{"filepath": f.filepath, "code": f.code} for f in files if f.filepath.endswith('.css')]
    
    css_coverage_errors = []
    if html_files and css_files:
        from agent.validators.css_coverage_validator import validate_css_coverage
        css_coverage_errors = validate_css_coverage(html_files, css_files)
        
        if css_coverage_errors:
            # Filter to only warnings (classes/IDs without styles)
            missing_styles = [e for e in css_coverage_errors if e.get('severity') == 'warning']
            if missing_styles:
                print(f"⚠️  Found {len(missing_styles)} unstyled HTML selectors:")
                for error in missing_styles[:10]:  # Show first 10
                    print(f"   - {error['selector']} ({error['message']})")
    
    # Use unified validator for comprehensive validation
    print("Running comprehensive validation...")
    validation_result = validate_all_files(files)
    
    # Convert validation errors to string format for prompt
    syntax_errors = []
    for error in validation_result["syntax_errors"]:
        syntax_errors.append(f"{error['file']}:{error.get('line', 1)} - {error['message']}")
    
    dependency_errors = []
    for error in validation_result["dependency_errors"]:
        dependency_errors.append(f"{error['file']}:{error.get('line', 1)} - {error['message']}")
    
    # Add CSS coverage errors to syntax errors for fixing
    missing_styles = [e for e in css_coverage_errors if e.get('severity') == 'warning']
    for error in missing_styles:
        syntax_errors.append(f"{error['file']}:{error.get('line', 1)} - {error['message']}")
    
    # Run code execution tests for JavaScript/Python files
    runtime_errors = []
    for file in files:
        ext = file.filepath.split('.')[-1].lower() if '.' in file.filepath else ''
        if ext in ['js', 'jsx']:
            test_result = test_javascript(file.filepath, file.code)
            if not test_result["success"]:
                for err in test_result.get("runtime_errors", []):
                    runtime_errors.append(f"{err['file']} - {err['message']}")
        elif ext == 'py':
            test_result = test_python(file.filepath, file.code)
            if not test_result["success"]:
                for err in test_result.get("runtime_errors", []):
                    runtime_errors.append(f"{err['file']} - {err['message']}")
    
    # Combine all errors
    all_errors = syntax_errors + dependency_errors + runtime_errors
    
    if all_errors:
        print(f"Found {len(all_errors)} errors:")
        for error in all_errors[:10]:  # Print first 10
            print(f"  - {error}")
    
    # Create a comprehensive view of all files for the debugger
    files_context = "\n\n".join([
        f"=== FILE: {f.filepath} ===\n{f.code}"
        for f in files
    ])
    
    # Generate CSS enhancement prompt if there are missing styles
    css_enhancement = ""
    if missing_styles:
        css_files_list = [f for f in files if f.filepath.endswith('.css')]
        if css_files_list:
            css_enhancement = generate_css_enhancement_prompt(missing_styles, css_files_list[0].code)
    
    # Use enhanced prompt with detected errors
    debugger_prompt_text = debugger_prompt(files, syntax_errors, runtime_errors + dependency_errors) + css_enhancement + f"\n\nFull codebase:\n{files_context}"
    
    try:
        # Get debugger's response with fixes
        response = llm.with_structured_output(DebuggerResponse).invoke(debugger_prompt_text)
        
        if response and response.fixed_files:
            # Create a dictionary of filepath -> FileCode for easy lookup
            files_dict = {f.filepath: f for f in files}
            
            # Update files with fixes
            fixed_count = 0
            for fixed_file in response.fixed_files:
                if fixed_file.filepath in files_dict:
                    # Replace the file with the fixed version
                    files_dict[fixed_file.filepath] = fixed_file
                    fixed_count += 1
                    print(f"Fixed file: {fixed_file.filepath}")
                else:
                    # Add new file if debugger created one
                    files_dict[fixed_file.filepath] = fixed_file
                    fixed_count += 1
                    print(f"Added new file: {fixed_file.filepath}")
            
            # Convert back to list
            files = list(files_dict.values())
            print(f"Debugger fixed {fixed_count} files")
            
            # Re-validate after fixes
            if fixed_count > 0:
                print("Re-validating after fixes...")
                new_validation = validate_all_files(files)
                new_error_count = new_validation["total_errors"]
                
                # Check if we should iterate again
                if new_error_count > 0 and iteration < max_iterations - 1:
                    # Check if errors were reduced
                    if new_error_count < validation_result["total_errors"]:
                        print(f"Errors reduced from {validation_result['total_errors']} to {new_error_count}. Iterating again...")
                        # Recursively call validator_fixer again
                        new_state = state.copy()
                        new_state["files"] = files
                        new_state["validator_iteration"] = iteration + 1
                        return validator_fixer_agent(new_state)
                    else:
                        print(f"Errors not reduced. Stopping after {iteration + 1} iterations.")
                elif new_error_count > 0:
                    print(f"Warning: {new_error_count} errors remain after {max_iterations} iterations")
        else:
            if all_errors:
                print("Warning: Validator/Fixer did not return fixes for detected issues")
    except Exception as e:
        # If validator_fixer fails, log but continue with original files
        print(f"Validator/Fixer agent encountered an error: {e}")
        import traceback
        traceback.print_exc()
        # Continue with original files
    
    return {"files": files, "validator_iteration": iteration + 1}

def validate_code_quality(files: list[FileCode]) -> dict:
    """Final validation of code quality - returns errors and warnings using unified validator"""
    validation_result = validate_all_files(files)
    
    # Check for empty or placeholder files
    placeholder_files = []
    for file in files:
        code_lower = file.code.lower()
        if 'todo' in code_lower and len(file.code) < 200:
            placeholder_files.append(file.filepath)
    
    # Convert CodeError objects to strings for backward compatibility
    syntax_errors = [f"{e['file']}:{e.get('line', 1)} - {e['message']}" for e in validation_result["syntax_errors"]]
    runtime_issues = [f"{e['file']}:{e.get('line', 1)} - {e['message']}" for e in validation_result.get("runtime_errors", [])]
    
    return {
        "syntax_errors": syntax_errors,
        "runtime_issues": runtime_issues,
        "dependency_errors": [f"{e['file']}:{e.get('line', 1)} - {e['message']}" for e in validation_result["dependency_errors"]],
        "placeholder_files": placeholder_files,
        "has_errors": validation_result["total_errors"] > 0 or len(placeholder_files) > 0,
        "has_warnings": len(runtime_issues) > 0,
        "validation_result": validation_result
    }

def fix_import_paths(files: list[FileCode]) -> list[FileCode]:
    """Fix import paths in all files based on actual file structure"""
    import re
    from pathlib import Path
    
    # Build a map of module names (without extension) to actual file paths
    # Key: module name without extension (e.g., "App" or "src/components/App")
    # Value: actual file path (e.g., "src/App.jsx" or "src/components/App.jsx")
    module_map = {}
    for file in files:
        filepath = file.filepath
        # Remove extension
        path_obj = Path(filepath)
        module_name = str(path_obj.with_suffix(''))
        # Also add just the filename without extension
        module_name_no_path = path_obj.stem
        # Add both full path and filename to map
        module_map[module_name] = filepath
        module_map[module_name_no_path] = filepath
        # Add with src/ prefix if not present
        if not module_name.startswith('src/'):
            module_map[f'src/{module_name}'] = filepath
    
    fixed_files = []
    
    for file in files:
        code = file.code
        filepath = file.filepath
        file_dir = str(Path(filepath).parent)
        
        # Patterns for different import styles
        # ES6 imports: import X from './Y' or import X from '../Y'
        # CommonJS: const X = require('./Y')
        import_patterns = [
            # ES6: import ... from '...'
            (r"(import\s+(?:(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)(?:\s*,\s*(?:\{[^}]*\}|\*\s+as\s+\w+|\w+))*\s+from\s+)?['\"]([^'\"]+)['\"])", "es6"),
            # CommonJS: require('...')
            (r"(require\(['\"]([^'\"]+)['\"]\))", "commonjs"),
            # Dynamic import: import('...')
            (r"(import\(['\"]([^'\"]+)['\"]\))", "dynamic"),
        ]
        
        modified = False
        for pattern, import_type in import_patterns:
            def replace_import(match):
                nonlocal modified
                full_match = match.group(0)
                import_path = match.group(2) if len(match.groups()) > 1 else match.group(1)
                
                # Skip node_modules and absolute paths
                if import_path.startswith('http') or import_path.startswith('node_modules') or '/' not in import_path or import_path.startswith('@'):
                    return full_match
                
                # Skip if it's already a correct relative path
                if import_path.startswith('./') or import_path.startswith('../'):
                    # Check if the path is correct
                    try:
                        # Resolve the import path relative to current file
                        import_path_resolved = str((Path(file_dir) / import_path).resolve())
                        # Remove extension from resolved path
                        import_path_no_ext = str(Path(import_path_resolved).with_suffix(''))
                        
                        # Check if this matches any file
                        for mod_name, actual_path in module_map.items():
                            actual_path_no_ext = str(Path(actual_path).with_suffix(''))
                            if import_path_no_ext.endswith(actual_path_no_ext) or actual_path_no_ext.endswith(import_path_no_ext):
                                # Path is correct
                                return full_match
                    except:
                        pass
                
                # Try to find the correct path
                # Remove extension if present
                import_path_clean = import_path
                if '.' in import_path_clean and not import_path_clean.startswith('.'):
                    import_path_clean = import_path_clean.rsplit('.', 1)[0]
                
                # Try different variations
                candidates = [
                    import_path_clean,
                    import_path_clean.replace('\\', '/'),
                    import_path_clean.split('/')[-1],  # Just filename
                ]
                
                # If it's a relative path, try resolving it
                if import_path.startswith('./') or import_path.startswith('../'):
                    try:
                        resolved = str((Path(file_dir) / import_path).resolve())
                        candidates.append(str(Path(resolved).with_suffix('')))
                        candidates.append(Path(resolved).stem)
                    except:
                        pass
                
                # Find matching file
                best_match = None
                best_match_path = None
                
                for candidate in candidates:
                    # Try exact match
                    if candidate in module_map:
                        best_match = candidate
                        best_match_path = module_map[candidate]
                        break
                    
                    # Try partial match (filename)
                    candidate_name = Path(candidate).stem if '/' in candidate else candidate
                    for mod_name, actual_path in module_map.items():
                        mod_name_stem = Path(mod_name).stem if '/' in mod_name else mod_name
                        if mod_name_stem == candidate_name:
                            best_match = mod_name
                            best_match_path = actual_path
                            break
                    
                    if best_match:
                        break
                
                if best_match_path:
                    # Calculate relative path from current file to target file
                    # Use string manipulation since these are virtual paths
                    current_file_path = Path(filepath)
                    target_file_path = Path(best_match_path)
                    
                    current_dir_parts = list(current_file_path.parent.parts)
                    target_dir_parts = list(target_file_path.parent.parts)
                    target_filename = target_file_path.stem
                    
                    # Normalize paths (remove empty parts, handle . and ..)
                    current_dir_parts = [p for p in current_dir_parts if p and p != '.']
                    target_dir_parts = [p for p in target_dir_parts if p and p != '.']
                    
                    # Find common prefix
                    common_len = 0
                    for i in range(min(len(current_dir_parts), len(target_dir_parts))):
                        if current_dir_parts[i] == target_dir_parts[i]:
                            common_len = i + 1
                        else:
                            break
                    
                    # Calculate up levels (how many directories to go up from current)
                    up_levels = len(current_dir_parts) - common_len
                    
                    # Calculate down path (directories to go into from common ancestor)
                    down_parts = target_dir_parts[common_len:]
                    
                    # Build relative import
                    if up_levels == 0 and not down_parts:
                        # Same directory
                        relative_import = f"./{target_filename}"
                    else:
                        # Build path: ../ (up) + down_path/ + filename
                        up_path = '../' * up_levels
                        down_path = '/'.join(down_parts) + '/' if down_parts else ''
                        relative_import = f"{up_path}{down_path}{target_filename}"
                    
                    # Replace in the import statement
                    modified = True
                    if import_type == "es6":
                        return full_match.replace(import_path, relative_import)
                    elif import_type == "commonjs":
                        return full_match.replace(import_path, relative_import)
                    elif import_type == "dynamic":
                        return full_match.replace(import_path, relative_import)
                
                return full_match
            
            code = re.sub(pattern, replace_import, code)
        
        if modified:
            fixed_files.append(FileCode(filepath=filepath, code=code))
            print(f"Fixed import paths in {filepath}")
        else:
            fixed_files.append(file)
    
    return fixed_files

@log_agent_execution("import_path_fixer")
def import_path_fixer_agent(state: dict) -> dict:
    """Agent that fixes import paths in generated files"""
    files = state["files"]
    
    try:
        fixed_files = fix_import_paths(files)
        
        # Validate after fixing imports
        validation = validate_code_quality(fixed_files)
        if validation["has_errors"]:
            print(f"Warning: {len(validation['syntax_errors'])} syntax errors remain after import fixing")
            if validation["placeholder_files"]:
                print(f"Warning: {len(validation['placeholder_files'])} placeholder files detected")
        
        return {"files": fixed_files, "validation": validation}
    except Exception as e:
        print(f"Import path fixer encountered an error: {e}")
        import traceback
        traceback.print_exc()
        # Return original files if fixer fails
        return {"files": files, "validation": {"has_errors": True, "has_warnings": False}}

@log_agent_execution("downloader")
def downloader_agent(state: dict) -> dict:
    files = state["files"]
    mem_zip = io.BytesIO()
    
    # Check if index.html exists for vanilla HTML/CSS/JS projects
    filepaths = [f.filepath.lower() for f in files]
    has_index_html = any('index.html' in fp for fp in filepaths)
    
    # Generate index.html if missing (vanilla HTML/CSS/JS fallback)
    if not has_index_html:
        print("Warning: index.html missing. Generating fallback index.html for vanilla HTML/CSS/JS...")
        
        # Find main JS file
        main_js = None
        for f in files:
            fp_lower = f.filepath.lower()
            if 'main.js' in fp_lower and 'scripts' in fp_lower:
                main_js = f.filepath
                break
        
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Website</title>
    <link rel="stylesheet" href="styles/main.css">
</head>
<body>
    <header>
        <nav>
            <h1>Welcome</h1>
        </nav>
    </header>
    <main>
        <section>
            <h2>Content</h2>
            <p>Your content here</p>
        </section>
    </main>
    <footer>
        <p>&copy; 2024</p>
    </footer>
    <script src="scripts/main.js" defer></script>
</body>
</html>"""
        
        # Add index.html to files
        files.append(FileCode(filepath="index.html", code=index_html))
        print("Added fallback index.html to zip")

    with zipfile.ZipFile(mem_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            # Optional: normalize leading slashes
            arcname = f.filepath.lstrip("/")
            zf.writestr(arcname, f.code)
    mem_zip.seek(0)

    return {"mem_zip": mem_zip}

@log_agent_execution("preview_server")
def preview_server_agent(state: dict) -> dict:
    """Create preview server for generated codebase"""
    from preview_server import create_preview
    
    mem_zip = state.get("mem_zip")
    if not mem_zip:
        return {"preview_info": None}
    
    # Get zip data
    zip_data = mem_zip.getvalue()
    
    # Create preview - use relative URL for FastAPI proxy endpoint
    # The frontend will construct the full URL
    base_url = os.getenv("PREVIEW_BASE_URL", "http://localhost:8000")
    preview_info = create_preview(zip_data, base_url)
    
    return {"preview_info": preview_info}

graph = StateGraph(dict)

# Graph: planner -> architect -> coder -> validator_fixer -> downloader -> preview_server
graph.add_node("planner", planner_agent)
graph.add_node("architect", architect_agent)
graph.add_node("coder", coder_agent)
graph.add_node("validator_fixer", validator_fixer_agent)
graph.add_node("downloader", downloader_agent)
graph.add_node("preview_server", preview_server_agent)

graph.add_edge("planner", "architect")
graph.add_edge("architect", "coder")
graph.add_edge("coder", "validator_fixer")
graph.add_edge("validator_fixer", "downloader")
graph.add_edge("downloader", "preview_server")
graph.set_entry_point("planner")

agent = graph.compile()

def build_code(user_prompt: str):
    result = agent.invoke({"user_prompt": user_prompt})
    return result