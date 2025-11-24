"""
Debug utilities for agent node debugging
"""
import os
import json
import time
import traceback
from functools import wraps
from typing import Dict, Any, Callable
from datetime import datetime

# Check if debugging is enabled
DEBUG_ENABLED = os.getenv("AGENT_DEBUG", "true").lower() == "true"
DEBUG_DETAILED = os.getenv("AGENT_DEBUG_DETAILED", "false").lower() == "true"


def log_agent_execution(agent_name: str):
    """
    Decorator to log agent execution details
    
    Args:
        agent_name: Name of the agent for logging
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            if not DEBUG_ENABLED:
                return func(state)
            
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            
            # Log input state
            input_summary = summarize_state(state, agent_name, "INPUT")
            print(f"\n{'='*80}")
            print(f"[{timestamp}] 🚀 {agent_name.upper()} - START")
            print(f"{'='*80}")
            print(input_summary)
            
            try:
                # Execute the agent
                result = func(state)
                
                # Calculate execution time
                execution_time = time.time() - start_time
                
                # Log output state
                output_summary = summarize_state(result, agent_name, "OUTPUT")
                print(f"\n{'='*80}")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ✅ {agent_name.upper()} - COMPLETE ({execution_time:.2f}s)")
                print(f"{'='*80}")
                print(output_summary)
                
                # Log detailed diff if enabled
                if DEBUG_DETAILED:
                    log_state_diff(state, result, agent_name)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                error_trace = traceback.format_exc()
                
                print(f"\n{'='*80}")
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] ❌ {agent_name.upper()} - ERROR ({execution_time:.2f}s)")
                print(f"{'='*80}")
                print(f"Error: {str(e)}")
                print(f"\nTraceback:\n{error_trace}")
                print(f"{'='*80}\n")
                
                raise
        
        return wrapper
    return decorator


def summarize_state(state: Dict[str, Any], agent_name: str, direction: str) -> str:
    """
    Create a summary of the state for logging
    
    Args:
        state: The state dictionary
        agent_name: Name of the agent
        direction: "INPUT" or "OUTPUT"
    
    Returns:
        Formatted summary string
    """
    summary_lines = []
    
    # Common fields to log
    if "user_prompt" in state:
        prompt_preview = str(state["user_prompt"])[:100] + "..." if len(str(state["user_prompt"])) > 100 else str(state["user_prompt"])
        summary_lines.append(f"  User Prompt: {prompt_preview}")
    
    if "plan" in state:
        plan_preview = str(state["plan"])[:200] + "..." if len(str(state["plan"])) > 200 else str(state["plan"])
        summary_lines.append(f"  Plan: {plan_preview}")
    
    if "task_plan" in state:
        task_plan = state["task_plan"]
        if hasattr(task_plan, 'implementation_steps'):
            summary_lines.append(f"  Task Plan: {len(task_plan.implementation_steps)} implementation steps")
            if DEBUG_DETAILED and task_plan.implementation_steps:
                summary_lines.append("  Implementation Steps:")
                for i, step in enumerate(task_plan.implementation_steps[:10], 1):
                    if hasattr(step, 'filepath'):
                        summary_lines.append(f"    {i}. {step.filepath}")
                        if hasattr(step, 'file_description'):
                            desc = step.file_description[:80] + "..." if len(step.file_description) > 80 else step.file_description
                            summary_lines.append(f"       Desc: {desc}")
                        if hasattr(step, 'required_imports') and step.required_imports:
                            summary_lines.append(f"       Imports: {step.required_imports}")
                if len(task_plan.implementation_steps) > 10:
                    summary_lines.append(f"    ... and {len(task_plan.implementation_steps) - 10} more steps")
        else:
            summary_lines.append(f"  Task Plan: {str(task_plan)[:200]}")
    
    if "framework_info" in state:
        framework_info = state["framework_info"]
        if hasattr(framework_info, 'framework'):
            summary_lines.append(f"  Framework: {framework_info.framework} ({framework_info.build_tool})")
        else:
            summary_lines.append(f"  Framework Info: {str(framework_info)[:200]}")
    
    if "files" in state:
        files = state["files"]
        file_count = len(files) if isinstance(files, list) else 0
        summary_lines.append(f"  Files: {file_count} files")
        
        if DEBUG_DETAILED and files:
            summary_lines.append("  File List:")
            for i, file in enumerate(files[:10]):  # Show first 10 files
                if hasattr(file, 'filepath'):
                    file_size = len(file.code) if hasattr(file, 'code') else 0
                    summary_lines.append(f"    {i+1}. {file.filepath} ({file_size} chars)")
            if file_count > 10:
                summary_lines.append(f"    ... and {file_count - 10} more files")
    
    if "mem_zip" in state:
        zip_size = len(state["mem_zip"].getvalue()) if hasattr(state["mem_zip"], 'getvalue') else 0
        summary_lines.append(f"  Zip Size: {zip_size} bytes")
    
    if "preview_info" in state:
        preview_info = state["preview_info"]
        if hasattr(preview_info, 'preview_url'):
            summary_lines.append(f"  Preview URL: {preview_info.preview_url}")
        else:
            summary_lines.append(f"  Preview Info: {str(preview_info)[:200]}")
    
    if "debugger_iteration" in state:
        summary_lines.append(f"  Debugger Iteration: {state['debugger_iteration']}")
    
    if "coder_errors" in state:
        errors = state["coder_errors"]
        if errors:
            summary_lines.append(f"  Coder Errors: {len(errors)} errors")
            if DEBUG_DETAILED:
                for error in errors[:5]:
                    summary_lines.append(f"    - {str(error)[:100]}")
    
    if "validation" in state:
        validation = state["validation"]
        if isinstance(validation, dict):
            if validation.get("has_errors"):
                summary_lines.append(f"  Validation: Has errors")
            if validation.get("has_warnings"):
                summary_lines.append(f"  Validation: Has warnings")
    
    # Log all keys if detailed mode
    if DEBUG_DETAILED:
        all_keys = list(state.keys())
        summary_lines.append(f"\n  All State Keys ({len(all_keys)}): {', '.join(all_keys)}")
    
    return "\n".join(summary_lines) if summary_lines else "  (Empty state)"


def log_state_diff(old_state: Dict[str, Any], new_state: Dict[str, Any], agent_name: str):
    """
    Log detailed differences between old and new state
    
    Args:
        old_state: State before agent execution
        new_state: State after agent execution
        agent_name: Name of the agent
    """
    print(f"\n  📊 State Changes:")
    
    # Check for new keys
    old_keys = set(old_state.keys())
    new_keys = set(new_state.keys())
    added_keys = new_keys - old_keys
    removed_keys = old_keys - new_keys
    
    if added_keys:
        print(f"    ➕ Added keys: {', '.join(added_keys)}")
    if removed_keys:
        print(f"    ➖ Removed keys: {', '.join(removed_keys)}")
    
    # Check for changed values
    common_keys = old_keys & new_keys
    changed_keys = []
    for key in common_keys:
        old_val = old_state[key]
        new_val = new_state[key]
        
        # Compare based on type
        if isinstance(old_val, list) and isinstance(new_val, list):
            if len(old_val) != len(new_val):
                changed_keys.append(f"{key} (list length: {len(old_val)} -> {len(new_val)})")
        elif old_val != new_val:
            changed_keys.append(key)
    
    if changed_keys:
        print(f"    🔄 Changed keys: {', '.join(changed_keys[:10])}")
        if len(changed_keys) > 10:
            print(f"       ... and {len(changed_keys) - 10} more")

