"""
Preview Server - Handles building and serving previews
"""
import os
import subprocess
import uuid
import zipfile
import io
import time
from pathlib import Path
from typing import Optional
from preview_manager import preview_manager
from agent.states import PreviewInfo

def extract_zip_to_directory(zip_data: bytes, target_dir: Path) -> None:
    """Extract zip file data to target directory"""
    target_dir.mkdir(parents=True, exist_ok=True)
    zip_file = zipfile.ZipFile(io.BytesIO(zip_data))
    zip_file.extractall(target_dir)

def install_dependencies(preview_dir: Path) -> bool:
    """Install npm dependencies if package.json exists"""
    package_json = preview_dir / "package.json"
    if not package_json.exists():
        return True  # No dependencies needed
    
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=preview_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes max
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"Error installing dependencies: {e}")
        return False

def build_project(preview_dir: Path, build_command: str = "npm run build") -> bool:
    """Build the project if needed"""
    package_json = preview_dir / "package.json"
    if not package_json.exists():
        return True  # No build needed
    
    try:
        # Check if build script exists
        import json
        with open(package_json) as f:
            package_data = json.load(f)
            scripts = package_data.get("scripts", {})
            if "build" not in scripts:
                return True  # No build script
        
        print(f"Building project in {preview_dir}...")
        result = subprocess.run(
            build_command.split(),
            cwd=preview_dir,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes max
        )
        
        if result.returncode != 0:
            print(f"Build failed with return code {result.returncode}")
            print(f"Build stdout: {result.stdout}")
            print(f"Build stderr: {result.stderr}")
            return False
        
        print(f"Build completed successfully")
        # Verify that dist directory was created (for Vite/React projects)
        dist_dir = preview_dir / "dist"
        if dist_dir.exists():
            print(f"Build output found in: {dist_dir}")
            # Check if index.html exists in dist
            if (dist_dir / "index.html").exists():
                print("index.html found in dist directory")
            else:
                print("Warning: index.html not found in dist directory")
                # Check if index.html exists in root (Vite might not move it)
                if (preview_dir / "index.html").exists():
                    print("index.html found in root, copying to dist...")
                    import shutil
                    shutil.copy(preview_dir / "index.html", dist_dir / "index.html")
        
        return True
    except subprocess.TimeoutExpired:
        print("Build timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"Error building project: {e}")
        import traceback
        traceback.print_exc()
        return False

def find_static_files(preview_dir: Path) -> Path:
    """Find the directory containing static files to serve"""
    # Common build output directories
    build_dirs = ["dist", "build", "out", "public"]
    
    for build_dir in build_dirs:
        potential_dir = preview_dir / build_dir
        if potential_dir.exists() and potential_dir.is_dir():
            return potential_dir
    
    # If no build directory, serve root (for vanilla HTML/CSS/JS)
    return preview_dir

def start_preview_server(preview_dir: Path, port: int) -> Optional[subprocess.Popen]:
    """Start a simple HTTP server to serve the preview"""
    static_dir = find_static_files(preview_dir)
    
    try:
        # Use Python's http.server for simplicity
        process = subprocess.Popen(
            ["python3", "-m", "http.server", str(port)],
            cwd=static_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process
    except Exception as e:
        print(f"Error starting preview server: {e}")
        return None

def create_preview(zip_data: bytes, base_url: str = "http://localhost") -> Optional[PreviewInfo]:
    """Create a preview from zip data"""
    # Generate unique token
    token = str(uuid.uuid4())
    
    # Create preview directory
    preview_dir = preview_manager.create_preview_directory(token)
    
    try:
        # Extract zip
        extract_zip_to_directory(zip_data, preview_dir)
        
        # Install dependencies if needed
        if not install_dependencies(preview_dir):
            print("Warning: Failed to install dependencies, continuing anyway")
        
        # Build if needed
        if not build_project(preview_dir):
            print("Warning: Build failed, serving source files")
        
        # Find available port
        port = preview_manager.find_available_port()
        
        # Start server
        process = start_preview_server(preview_dir, port)
        if not process:
            raise RuntimeError("Failed to start preview server")
        
        # Register preview
        preview_manager.register_preview(token, preview_dir, port, process)
        
        # Create preview info - use FastAPI proxy endpoint instead of direct port
        # This avoids CORS issues and provides better security
        preview_url = f"{base_url}/preview/{token}"
        expires_at = time.time() + (10 * 60)  # 10 minutes
        
        return PreviewInfo(
            preview_url=preview_url,
            preview_token=token,
            expires_at=expires_at,
            port=port
        )
    except Exception as e:
        # Cleanup on error
        if preview_dir.exists():
            import shutil
            shutil.rmtree(preview_dir, ignore_errors=True)
        print(f"Error creating preview: {e}")
        return None

