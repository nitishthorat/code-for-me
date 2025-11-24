from pydantic import BaseModel, Field, ConfigDict
from typing import Union


class File(BaseModel):
    path: str = Field(description="The path to the file to be created or modified")
    purpose: str = Field(description="The purpose of the file to be created")

class DesignSystem(BaseModel):
    """Design system for modern web design"""
    colors: dict[str, Union[str, dict[str, str]]] = Field(description="Color palette with keys like 'primary', 'secondary', 'accent', 'background' (can be string or object like {'base': '#color', 'surface': '#color'}), 'text' (can be string or object like {'primary': '#color', 'muted': '#color'}), 'success', 'error', etc.")
    typography: dict[str, str] = Field(description="Typography settings: 'font_family', 'heading_font', 'body_font', 'base_size', etc.")
    spacing: dict[str, str] = Field(description="Spacing scale: 'xs', 'sm', 'md', 'lg', 'xl', 'xxl' with pixel/rem values")
    breakpoints: dict[str, str] = Field(description="Responsive breakpoints: 'mobile', 'tablet', 'desktop' with pixel values")
    components: list[str] = Field(default_factory=list, description="List of UI components to create (e.g., 'button', 'card', 'form', 'navigation')")

class Plan(BaseModel):
    name: str = Field(description="The name of the app to be built")
    description: str = Field(description="A one line description of the app to be built. eg. A web application for managing notes")
    tech_stack: str = Field(description="The tech stack - MUST be 'Vanilla HTML/CSS/JS' for this agent")
    features: list[str] = Field(description="A list of features that the app should have. eg. User Authentication, Data Visualization, etc")
    files: list[str] = Field(description="A list of files to be created, each with a 'path' and purpose")
    design_system: DesignSystem = Field(description="Design system with colors, typography, spacing, and components")

class ImplementationTask(BaseModel):
    filepath: str = Field(description="The path to the file to be created or modified")
    task_description: str = Field(description="A detailed description of the task to be performed on the file")
    required_imports: list[str] = Field(default_factory=list, description="List of imports this file will need (e.g., ['react', './components/Header', '../utils/helper'])")
    file_description: str = Field(default="", description="Brief description of what this file does and its purpose in the project")

class TaskPlan(BaseModel):
    implementation_steps: list[ImplementationTask] = Field(description="A list of implementations to run")
    model_config = ConfigDict(extra="allow")

class FileCode(BaseModel):
    filepath: str = Field(description="The path to the file to be created or modified")
    code: str = Field(description="The code to be added to the file")

class CodeBase(BaseModel):
    files: list[FileCode] = Field(description="A list of files to be created, each with the path and the code.")

class DebuggerResponse(BaseModel):
    fixed_files: list[FileCode] = Field(description="List of files that were fixed or need updates", default_factory=list)

class FrameworkInfo(BaseModel):
    framework: str = Field(description="The chosen framework name (e.g., React, Vue, Angular, vanilla)")
    version: str = Field(description="Recommended version (e.g., 18.2, 3.3, 17)")
    build_tool: str = Field(description="Build tool to use (e.g., Vite, Create React App, Angular CLI)")
    requires_build: bool = Field(description="Whether the project needs a build step")
    config_files: list[str] = Field(description="List of config files needed (e.g., package.json, vite.config.js)")

class PreviewInfo(BaseModel):
    preview_url: str = Field(description="URL to access the preview")
    preview_token: str = Field(description="Unique token for preview access")
    expires_at: float = Field(description="Unix timestamp when preview expires")
    port: int = Field(description="Port number where preview is served")

class CodeError(BaseModel):
    """Represents a single code error"""
    file: str = Field(description="File path where error occurs")
    line: int = Field(description="Line number (1-indexed)")
    column: int = Field(description="Column number (1-indexed)")
    message: str = Field(description="Error message")
    type: str = Field(description="Error type: syntax, dependency, runtime, etc.")
    severity: str = Field(description="Error severity: error, warning")

class ErrorReport(BaseModel):
    """Comprehensive error report for the codebase"""
    syntax_errors: list[CodeError] = Field(default_factory=list, description="Syntax errors found")
    dependency_errors: list[CodeError] = Field(default_factory=list, description="Dependency/import errors")
    runtime_errors: list[CodeError] = Field(default_factory=list, description="Runtime errors found")
    total_errors: int = Field(description="Total number of errors")
    errors_by_file: dict[str, list[CodeError]] = Field(default_factory=dict, description="Errors grouped by file")
    validation_passed: bool = Field(description="Whether validation passed")