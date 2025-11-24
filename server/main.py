from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from agent.graph import *
import json
import asyncio
import re

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CodeRequest(BaseModel):
    prompt: str

@app.post("/get_app")
def get_app(req: CodeRequest):
    response = build_code(req.prompt)

    return Response(
        content=response['mem_zip'].getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=codebase.zip"}
    )

async def generate_code_stream(prompt: str):
    """Generator function that yields SSE events during code generation"""
    try:
        from agent.graph import planner_agent, architect_agent, coder_agent, validator_fixer_agent, downloader_agent, preview_server_agent
        
        # Yield initial status
        yield f"data: {json.dumps({'status': 'starting', 'stage': 'planner', 'message': 'Starting code generation...'})}\n\n"
        
        state = {"user_prompt": prompt}
        
        # Execute planner
        yield f"data: {json.dumps({'status': 'processing', 'stage': 'planner', 'message': 'Planning your application...'})}\n\n"
        state.update(await asyncio.to_thread(planner_agent, state))
        
        # Execute architect
        yield f"data: {json.dumps({'status': 'processing', 'stage': 'architect', 'message': 'Designing architecture and file structure...'})}\n\n"
        state.update(await asyncio.to_thread(architect_agent, state))
        
        # Execute coder
        yield f"data: {json.dumps({'status': 'processing', 'stage': 'coder', 'message': 'Generating HTML, CSS, and JavaScript files...'})}\n\n"
        coder_result = await asyncio.to_thread(coder_agent, state)
        state.update(coder_result)
        
        # Get file count and errors for progress
        files_count = len(state.get("files", []))
        coder_errors = coder_result.get("coder_errors", [])
        if coder_errors:
            yield f"data: {json.dumps({'status': 'processing', 'stage': 'coder', 'message': f'Generated {files_count} files (with {len(coder_errors)} errors to fix)...'})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'processing', 'stage': 'coder', 'message': f'Generated {files_count} files...'})}\n\n"
        
        # Execute validator/fixer with error reporting
        yield f"data: {json.dumps({'status': 'processing', 'stage': 'validator_fixer', 'message': 'Validating and fixing errors...'})}\n\n"
        validator_result = await asyncio.to_thread(validator_fixer_agent, state)
        state.update(validator_result)
        
        # Get error information from validation
        from agent.validators.unified_validator import validate_all_files
        validation_result = validate_all_files(state.get("files", []))
        error_count = validation_result["total_errors"]
        validator_iteration = validator_result.get("validator_iteration", 1)
        
        # Get updated file count after validation/fixing
        files_count = len(state.get("files", []))
        
        if error_count > 0:
            yield f"data: {json.dumps({'status': 'processing', 'stage': 'validator_fixer', 'message': f'Iteration {validator_iteration}: Fixed issues in {files_count} files, {error_count} errors remaining...', 'error_count': error_count, 'iteration': validator_iteration})}\n\n"
        else:
            yield f"data: {json.dumps({'status': 'processing', 'stage': 'validator_fixer', 'message': f'Verified and fixed {files_count} files (all errors resolved)...', 'error_count': 0, 'iteration': validator_iteration})}\n\n"
        
        # Execute downloader
        yield f"data: {json.dumps({'status': 'processing', 'stage': 'downloader', 'message': 'Creating codebase archive...'})}\n\n"
        state.update(await asyncio.to_thread(downloader_agent, state))
        
        # Execute preview server
        yield f"data: {json.dumps({'status': 'processing', 'stage': 'preview_server', 'message': 'Starting preview server...'})}\n\n"
        preview_result = await asyncio.to_thread(preview_server_agent, state)
        state.update(preview_result)
        
        # Extract preview info
        preview_info = preview_result.get('preview_info')
        preview_url = None
        preview_token = None
        preview_expires_at = None
        
        if preview_info:
            preview_url = preview_info.preview_url if hasattr(preview_info, 'preview_url') else preview_info.get('preview_url')
            preview_token = preview_info.preview_token if hasattr(preview_info, 'preview_token') else preview_info.get('preview_token')
            preview_expires_at = preview_info.expires_at if hasattr(preview_info, 'expires_at') else preview_info.get('expires_at')
        
        # Convert zip to base64 for transmission
        import base64
        zip_data = state['mem_zip'].getvalue()
        zip_base64 = base64.b64encode(zip_data).decode('utf-8')
        
        # Yield completion with zip data and preview info
        completion_data = {
            'status': 'completed',
            'stage': 'preview_server',
            'message': 'Codebase ready!' + (' Preview available!' if preview_url else ''),
            'zip_data': zip_base64,
            'file_count': files_count
        }
        
        if preview_url:
            completion_data['preview_url'] = preview_url
        if preview_token:
            completion_data['preview_token'] = preview_token
        if preview_expires_at:
            completion_data['preview_expires_at'] = preview_expires_at
        
        yield f"data: {json.dumps(completion_data)}\n\n"
        
    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

@app.post("/get_app/stream")
async def get_app_stream(req: CodeRequest):
    """Streaming endpoint that provides real-time updates via Server-Sent Events"""
    return StreamingResponse(
        generate_code_stream(req.prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

def get_mime_type(file_path: Path) -> str:
    """Determine MIME type based on file extension"""
    ext = file_path.suffix.lower()
    mime_types = {
        '.html': 'text/html',
        '.htm': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.mjs': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.eot': 'application/vnd.ms-fontobject',
        '.xml': 'application/xml',
        '.txt': 'text/plain',
    }
    return mime_types.get(ext, 'application/octet-stream')

@app.get("/preview/{token}")
@app.get("/preview/{token}/{file_path:path}")
async def serve_preview(token: str, file_path: str = ""):
    """Proxy endpoint to serve preview files"""
    from preview_manager import preview_manager
    from fastapi.responses import FileResponse
    from fastapi import HTTPException
    from pathlib import Path
    
    preview = preview_manager.get_preview(token)
    if not preview:
        raise HTTPException(status_code=404, detail="Preview not found or expired")
    
    preview_dir = preview["path"]
    print(f"[PREVIEW] Serving preview for token {token}, file_path: '{file_path}', preview_dir: {preview_dir}")
    
    def find_index_file(search_dirs):
        """Find index.html in multiple directories"""
        index_files = ["index.html", "index.htm"]
        for search_dir in search_dirs:
            for index_file in index_files:
                index_path = search_dir / index_file
                if index_path.exists() and index_path.is_file():
                    return index_path
        return None
    
    def find_static_dir():
        """Find the directory containing static files to serve"""
        # Check build output directories first
        build_dirs = ["dist", "build", "out"]
        for build_dir in build_dirs:
            potential_dir = preview_dir / build_dir
            if potential_dir.exists() and potential_dir.is_dir():
                # Check if this directory has an index.html
                if find_index_file([potential_dir]):
                    return potential_dir
        
        # Check public directory
        public_dir = preview_dir / "public"
        if public_dir.exists() and public_dir.is_dir():
            if find_index_file([public_dir]):
                return public_dir
        
        # Check root directory (for Vite projects or vanilla HTML)
        if find_index_file([preview_dir]):
            return preview_dir
        
        # Fallback: return dist if it exists, otherwise root
        dist_dir = preview_dir / "dist"
        if dist_dir.exists() and dist_dir.is_dir():
            return dist_dir
        
        return preview_dir
    
    static_dir = find_static_dir()
    print(f"[PREVIEW] Using static_dir: {static_dir}")
    
    # Serve index.html for root path
    if not file_path or file_path == "/":
        # Try multiple locations for index.html
        search_locations = [static_dir, preview_dir]
        # Also check common subdirectories
        for subdir in ["dist", "build", "out", "public"]:
            subdir_path = preview_dir / subdir
            if subdir_path.exists():
                search_locations.append(subdir_path)
        
        index_path = find_index_file(search_locations)
        if index_path:
            print(f"[PREVIEW] Serving index.html from: {index_path}")
            mime_type = get_mime_type(index_path)
            
            # Read HTML content and fix relative paths to work with preview proxy
            try:
                html_content = index_path.read_text(encoding='utf-8')
                # Convert relative paths in href and src to absolute paths for preview proxy
                # Fix CSS links: href="styles/main.css" -> href="/preview/{token}/styles/main.css"
                def rewrite_link(match):
                    href_path = match.group(2)
                    if href_path.startswith(('http', '//', '/preview/')):
                        return match.group(0)
                    return f'{match.group(1)}/preview/{token}/{href_path.lstrip("/")}{match.group(3)}'
                
                def rewrite_script(match):
                    src_path = match.group(2)
                    if src_path.startswith(('http', '//', '/preview/')):
                        return match.group(0)
                    return f'{match.group(1)}/preview/{token}/{src_path.lstrip("/")}{match.group(3)}'
                
                html_content = re.sub(
                    r'(<link[^>]+href=["\'])([^"\']+)(["\'][^>]*>)',
                    rewrite_link,
                    html_content
                )
                # Fix JS scripts: src="scripts/main.js" -> src="/preview/{token}/scripts/main.js"
                html_content = re.sub(
                    r'(<script[^>]+src=["\'])([^"\']+)(["\'][^>]*>)',
                    rewrite_script,
                    html_content
                )
                
                print(f"[PREVIEW] Rewrote HTML paths for preview proxy")
                return HTMLResponse(content=html_content, media_type=mime_type)
            except Exception as read_error:
                print(f"[PREVIEW] Error reading/rewriting HTML: {read_error}")
                # Fallback: serve file without rewriting
                return FileResponse(index_path, media_type=mime_type)
        
        # Fallback: Generate index.html if it's missing (for web projects)
        # Check if this looks like a web project
        package_json = preview_dir / "package.json"
        src_dir = preview_dir / "src"
        is_web_project = package_json.exists() or src_dir.exists()
        
        if is_web_project:
            print(f"Warning: index.html missing, generating fallback for web project")
            
            # Find main entry point
            main_entry = None
            if src_dir.exists():
                for ext in ["main.tsx", "main.jsx", "main.ts", "main.js", "index.tsx", "index.jsx"]:
                    main_path = src_dir / ext
                    if main_path.exists():
                        main_entry = ext
                        break
            
            # Check if React project
            is_react = False
            if package_json.exists():
                try:
                    import json
                    with open(package_json) as f:
                        pkg_data = json.load(f)
                        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                        is_react = any("react" in dep.lower() for dep in deps.keys())
                except:
                    pass
            
            # Generate appropriate index.html
            if is_react:
                index_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/{main_entry or 'main.jsx'}"></script>
</body>
</html>"""
            else:
                index_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>App</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/{main_entry or 'main.js'}"></script>
</body>
</html>"""
            
            # Write index.html to static_dir
            index_path = static_dir / "index.html"
            index_path.write_text(index_content)
            print(f"[PREVIEW] Generated fallback index.html at {index_path}")
            # Rewrite paths for preview proxy
            html_content = index_content
            
            def rewrite_link(match):
                href_path = match.group(2)
                if href_path.startswith(('http', '//', '/preview/')):
                    return match.group(0)
                return f'{match.group(1)}/preview/{token}/{href_path.lstrip("/")}{match.group(3)}'
            
            def rewrite_script(match):
                src_path = match.group(2)
                if src_path.startswith(('http', '//', '/preview/')):
                    return match.group(0)
                return f'{match.group(1)}/preview/{token}/{src_path.lstrip("/")}{match.group(3)}'
            
            html_content = re.sub(
                r'(<link[^>]+href=["\'])([^"\']+)(["\'][^>]*>)',
                rewrite_link,
                html_content
            )
            html_content = re.sub(
                r'(<script[^>]+src=["\'])([^"\']+)(["\'][^>]*>)',
                rewrite_script,
                html_content
            )
            print(f"[PREVIEW] Rewrote fallback HTML paths for preview proxy")
            return HTMLResponse(content=html_content, media_type='text/html')
        
        # Provide helpful error message with directory listing
        error_detail = "No index.html found"
        try:
            root_files = [f.name for f in preview_dir.iterdir() if f.is_file()][:10]
            root_dirs = [f.name for f in preview_dir.iterdir() if f.is_dir()][:10]
            error_detail = f"No index.html found. Root files: {root_files}, Root dirs: {root_dirs}"
            if (preview_dir / "dist").exists():
                dist_files = [f.name for f in (preview_dir / "dist").iterdir() if f.is_file()][:10]
                error_detail += f", Dist files: {dist_files}"
        except Exception as e:
            error_detail = f"No index.html found. Error listing files: {e}"
        
        raise HTTPException(status_code=404, detail=error_detail)
    
    # Serve requested file
    requested_path = static_dir / file_path.lstrip("/")
    print(f"[PREVIEW] Attempting to serve file: {requested_path} (from static_dir: {static_dir})")
    
    # Security: ensure file is within static_dir
    try:
        requested_path.resolve().relative_to(static_dir.resolve())
    except ValueError:
        print(f"[PREVIEW] WARNING: Security check failed: {requested_path} is not within {static_dir}")
        raise HTTPException(status_code=403, detail="Access denied")
    
    if requested_path.exists():
        if requested_path.is_file():
            mime_type = get_mime_type(requested_path)
            print(f"[PREVIEW] Serving file: {requested_path} with MIME type: {mime_type}")
            return FileResponse(requested_path, media_type=mime_type)
        elif requested_path.is_dir():
            # Try to serve index.html from directory
            index_path = find_index_file([requested_path])
            if index_path:
                print(f"[PREVIEW] Serving directory index: {index_path}")
                return FileResponse(index_path, media_type='text/html')
            raise HTTPException(status_code=404, detail="Directory index not found")
    
    # If file not found in static_dir, check root directory (for vanilla HTML/CSS/JS projects)
    root_requested_path = preview_dir / file_path.lstrip("/")
    print(f"[PREVIEW] File not found in static_dir, checking root: {root_requested_path}")
    if root_requested_path.exists() and root_requested_path != requested_path:
        try:
            root_requested_path.resolve().relative_to(preview_dir.resolve())
            if root_requested_path.is_file():
                mime_type = get_mime_type(root_requested_path)
                print(f"[PREVIEW] Serving file from root: {root_requested_path} with MIME type: {mime_type}")
                return FileResponse(root_requested_path, media_type=mime_type)
        except ValueError:
            print(f"[PREVIEW] WARNING: Security check failed for root path: {root_requested_path}")
            pass
    
    print(f"[PREVIEW] ERROR: File not found: {file_path} (checked {requested_path} and {root_requested_path})")
    raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

@app.delete("/preview/{token}")
async def stop_preview(token: str):
    """Stop and cleanup a preview"""
    from preview_manager import preview_manager
    
    success = preview_manager.stop_preview(token)
    if success:
        return {"message": "Preview stopped successfully"}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Preview not found or already expired")