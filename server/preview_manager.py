"""
Preview Manager - Handles preview lifecycle, cleanup, and resource management
"""
import os
import shutil
import time
import threading
import subprocess
import socket
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta

PREVIEW_BASE_DIR = Path("/tmp/previews")
PREVIEW_DURATION_MINUTES = 10

class PreviewManager:
    """Manages preview servers and cleanup"""
    
    def __init__(self):
        self.previews: Dict[str, dict] = {}  # token -> {path, port, process, expires_at}
        self.lock = threading.Lock()
        PREVIEW_BASE_DIR.mkdir(parents=True, exist_ok=True)
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for cleanup"""
        def cleanup_loop():
            while True:
                time.sleep(60)  # Check every minute
                self.cleanup_expired()
        
        thread = threading.Thread(target=cleanup_loop, daemon=True)
        thread.start()
    
    def find_available_port(self, start_port: int = 3000) -> int:
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + 100):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('localhost', port)) != 0:
                    return port
        raise RuntimeError("No available port found")
    
    def create_preview_directory(self, token: str) -> Path:
        """Create a temporary directory for preview"""
        preview_dir = PREVIEW_BASE_DIR / token
        preview_dir.mkdir(parents=True, exist_ok=True)
        return preview_dir
    
    def register_preview(self, token: str, preview_dir: Path, port: int, process: subprocess.Popen) -> None:
        """Register a preview with expiry time"""
        expires_at = time.time() + (PREVIEW_DURATION_MINUTES * 60)
        with self.lock:
            self.previews[token] = {
                "path": preview_dir,
                "port": port,
                "process": process,
                "expires_at": expires_at,
                "created_at": time.time()
            }
    
    def get_preview(self, token: str) -> Optional[dict]:
        """Get preview info if it exists and hasn't expired"""
        with self.lock:
            preview = self.previews.get(token)
            if preview and time.time() < preview["expires_at"]:
                return preview
            elif preview:
                # Expired, remove it
                self._remove_preview(token)
            return None
    
    def _remove_preview(self, token: str) -> None:
        """Remove a preview and cleanup resources"""
        preview = self.previews.get(token)
        if not preview:
            return
        
        try:
            # Kill the process
            process = preview.get("process")
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
            
            # Remove directory
            preview_dir = preview.get("path")
            if preview_dir and preview_dir.exists():
                shutil.rmtree(preview_dir, ignore_errors=True)
        except Exception as e:
            print(f"Error removing preview {token}: {e}")
        finally:
            with self.lock:
                self.previews.pop(token, None)
    
    def cleanup_expired(self) -> None:
        """Remove all expired previews"""
        current_time = time.time()
        expired_tokens = []
        
        with self.lock:
            for token, preview in self.previews.items():
                if current_time >= preview["expires_at"]:
                    expired_tokens.append(token)
        
        for token in expired_tokens:
            self._remove_preview(token)
    
    def stop_preview(self, token: str) -> bool:
        """Manually stop a preview"""
        preview = self.get_preview(token)
        if preview:
            self._remove_preview(token)
            return True
        return False
    
    def get_all_previews(self) -> Dict[str, dict]:
        """Get all active previews (for debugging)"""
        self.cleanup_expired()
        with self.lock:
            return {k: {
                "port": v["port"],
                "expires_at": datetime.fromtimestamp(v["expires_at"]).isoformat(),
                "created_at": datetime.fromtimestamp(v["created_at"]).isoformat()
            } for k, v in self.previews.items()}

# Global instance
preview_manager = PreviewManager()

