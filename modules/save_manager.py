"""
save_manager.py — Centralized save/load logic with proper hash tracking.
Handles serialization, deserialization, and upload state management.
"""

import hashlib
from datetime import date
from modules.persistence import serialize_projects, deserialize_projects


class SaveManager:
    """Manages project save/load with file hash tracking."""
    
    def __init__(self):
        self.last_upload_hash = None
        self.last_upload_size = None
        self.last_save_fingerprint = None
        self.save_bytes = None
    
    def get_project_fingerprint(self, projects: list[dict]) -> tuple:
        """
        Generate a fingerprint to detect project changes.
        Cheap fingerprint — not cryptographic.
        """
        try:
            count = len(projects)
            total_parts = sum(
                len(p.get("parts_state", {})) 
                if isinstance(p.get("parts_state", {}), dict) 
                else 0 
                for p in projects
            )
            names_hash = sum(
                len(str(p.get("code", ""))) + len(str(p.get("description", ""))) 
                for p in projects
            )
            start_count = sum(1 for p in projects if p.get("start"))
            return (count, total_parts, names_hash, start_count)
        except Exception:
            return None
    
    def should_serialize(self, projects: list[dict]) -> bool:
        """Check if projects have changed and need re-serialization."""
        fp = self.get_project_fingerprint(projects)
        return fp != self.last_save_fingerprint or self.save_bytes is None
    
    def serialize(self, projects: list[dict]) -> bytes:
        """
        Serialize projects to JSON bytes and cache the result.
        Automatically clears upload tracking for fresh download/upload cycle.
        """
        fp = self.get_project_fingerprint(projects)
        self.last_save_fingerprint = fp
        
        print("[APP] Serializing projects for save...", flush=True)
        self.save_bytes = serialize_projects(projects)
        print(f"[APP] Serialized {len(projects)} project(s), size: {len(self.save_bytes)} bytes", flush=True)
        
        # Clear upload tracking when new save is generated
        # This ensures re-upload will process the new file
        self.reset_upload_tracking()
        print(f"[APP] Cleared upload hash - ready for fresh download/upload cycle", flush=True)
        
        return self.save_bytes
    
    def get_save_bytes(self, projects: list[dict]) -> bytes:
        """Get cached save bytes, or serialize if projects changed."""
        if self.should_serialize(projects):
            return self.serialize(projects)
        return self.save_bytes or b"{}"
    
    def process_upload(self, content: bytes) -> tuple[list[dict], str, bool]:
        """
        Process an uploaded file.
        Returns: (loaded_projects, feedback_message, was_processed)
        
        was_processed = True if file was loaded
        was_processed = False if file was skipped (already loaded)
        """
        if not content:
            return [], "No file content", False
        
        # Calculate file hash and size
        file_hash = hashlib.md5(content).hexdigest()
        current_size = len(content)
        
        print(f"[APP] File uploaded: size {current_size} bytes", flush=True)
        print(f"[APP] File hash: {file_hash[:8]}...", flush=True)
        
        # Check if this is a new file
        # Compare both hash AND size to catch browser cache issues
        is_new_file = (file_hash != self.last_upload_hash) or (current_size != self.last_upload_size)
        
        if not is_new_file:
            print(f"[APP] ⚠️  File not processed - same as previously loaded", flush=True)
            print(f"[APP]   → Hash: {file_hash[:8]}... | Size: {current_size} bytes", flush=True)
            print(f"[APP]   → Previous: {self.last_upload_hash[:8] if self.last_upload_hash else 'None'}... | Size: {self.last_upload_size} bytes", flush=True)
            return [], "File already loaded. Click Reset to reload.", False
        
        # File is new - process it
        print(f"[APP] New file detected - processing upload", flush=True)
        if file_hash != self.last_upload_hash:
            print(f"[APP]   → Hash changed: {self.last_upload_hash[:8] if self.last_upload_hash else 'None'}... → {file_hash[:8]}...", flush=True)
        if current_size != self.last_upload_size:
            print(f"[APP]   → Size changed: {self.last_upload_size} bytes → {current_size} bytes", flush=True)
        
        # Deserialize
        loaded, feedback = deserialize_projects(content)
        
        if loaded:
            print(f"[APP] ✅ Deserialization successful: {len(loaded)} project(s) loaded", flush=True)
            print(f"[APP] First project: code={loaded[0].get('code')}, name={loaded[0].get('name')}", flush=True)
            
            # Store hash and size to prevent re-loading on every rerun
            self.last_upload_hash = file_hash
            self.last_upload_size = current_size
            
            return loaded, f"✅ {feedback}", True
        else:
            print(f"[APP] ❌ Deserialization failed: {feedback}", flush=True)
            return [], f"❌ {feedback}", False
    
    def reset_upload_tracking(self):
        """Clear upload hash/size tracking for next upload."""
        self.last_upload_hash = None
        self.last_upload_size = None
        print(f"[APP] Upload tracking reset", flush=True)
    
    def clear_all(self):
        """Reset all save/load state."""
        self.last_upload_hash = None
        self.last_upload_size = None
        self.last_save_fingerprint = None
        self.save_bytes = None
        print(f"[APP] All save/load state cleared", flush=True)


# Global instance
_save_manager = SaveManager()


def get_save_manager() -> SaveManager:
    """Get the global SaveManager instance."""
    return _save_manager
