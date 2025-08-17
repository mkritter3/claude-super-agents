#!/usr/bin/env python3
import sqlite3
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import re
from logger_config import get_contextual_logger

class FileRegistry:
    def __init__(self, db_path: str = ".claude/registry/registry.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._initialize_db()
        self._load_conventions()
        
        # Initialize workspace root for secure path validation
        self.workspace_root = Path(os.getcwd()).resolve()
        self.logger = get_contextual_logger("file_registry", component="registry")
        
        # CRITICAL: Initialize Context Assembler connection
        self._init_context_integration()
    
    def _init_context_integration(self):
        """Initialize connection to Context Integration Layer."""
        try:
            from context_assembler import ContextAssembler
            # Register this registry with the context assembler
            ContextAssembler.file_registry = self
        except ImportError:
            pass  # Context assembler might not be created yet
    
    def _initialize_db(self):
        """Create tables if they don't exist."""
        schema_path = Path('.claude/system/schema.sql')
        if schema_path.exists():
            with open(schema_path, 'r') as f:
                self.conn.executescript(f.read())
        self.conn.commit()
    
    def _load_conventions(self):
        """Load naming conventions from config."""
        config_path = Path(".claude/config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                self.conventions = config.get("conventions", {})
        else:
            self.conventions = {}
    
    def canonicalize_path(self, path: str, component: str) -> str:
        """Convert path to canonical form based on conventions."""
        pattern = self.conventions.get("path_pattern", "src/{domain}/{component}/{layer}")
        
        # Extract parts from path
        parts = Path(path).parts
        
        # Apply pattern
        canonical = pattern.format(
            domain=self._infer_domain(path),
            component=component,
            layer=self._infer_layer(path)
        )
        
        return canonical
    
    def _infer_domain(self, path: str) -> str:
        """Infer domain from path or component."""
        # Domain inference logic
        if "auth" in path.lower():
            return "auth"
        elif "user" in path.lower():
            return "users"
        elif "api" in path.lower():
            return "api"
        else:
            return "core"
    
    def _infer_layer(self, path: str) -> str:
        """Infer architectural layer from path."""
        if "component" in path.lower():
            return "components"
        elif "service" in path.lower():
            return "services"
        elif "util" in path.lower() or "helper" in path.lower():
            return "utils"
        elif "model" in path.lower():
            return "models"
        else:
            return "lib"
    
    def validate_path(self, path: str, ticket_id: str = None) -> Tuple[bool, str]:
        """Validate path against security requirements and conventions.
        
        Phase 1 Security Enhancement:
        - Uses os.path.abspath for robust validation
        - Checks paths stay within workspace root  
        - Rejects symbolic links
        - Prevents directory traversal attacks
        """
        errors = []
        
        try:
            # Convert to absolute path for robust validation
            abs_path = Path(os.path.abspath(path)).resolve()
            
            # Security Check 1: Ensure path is within workspace root
            try:
                abs_path.relative_to(self.workspace_root)
            except ValueError:
                errors.append("Path outside workspace root")
                self.logger.warning("Path traversal attempt blocked", extra={
                    'attempted_path': path,
                    'resolved_path': str(abs_path),
                    'workspace_root': str(self.workspace_root),
                    'ticket_id': ticket_id,
                    'security_violation': 'path_traversal'
                })
            
            # Security Check 2: Reject symbolic links
            if abs_path.is_symlink() or any(p.is_symlink() for p in abs_path.parents):
                errors.append("Symbolic links not allowed")
                self.logger.warning("Symbolic link access blocked", extra={
                    'attempted_path': path,
                    'ticket_id': ticket_id,
                    'security_violation': 'symlink_access'
                })
            
            # Security Check 3: Prevent directory traversal patterns
            path_str = str(abs_path)
            dangerous_patterns = [
                "../", "..\\", "..", 
                "~", "/tmp", "/var", "/etc",
                "%2e%2e", "%2f", "%5c"  # URL encoded traversals
            ]
            for pattern in dangerous_patterns:
                if pattern in path.lower() or pattern in path_str.lower():
                    errors.append(f"Dangerous path pattern detected: {pattern}")
                    self.logger.warning("Dangerous path pattern blocked", extra={
                        'attempted_path': path,
                        'dangerous_pattern': pattern,
                        'ticket_id': ticket_id,
                        'security_violation': 'path_injection'
                    })
            
            # Security Check 4: Check for null bytes and control characters
            if '\x00' in path or any(ord(c) < 32 for c in path if c != '\t' and c != '\n'):
                errors.append("Invalid characters in path")
                self.logger.warning("Invalid path characters blocked", extra={
                    'attempted_path': repr(path),
                    'ticket_id': ticket_id,
                    'security_violation': 'invalid_chars'
                })
            
        except (OSError, ValueError) as e:
            errors.append(f"Invalid path format: {e}")
            self.logger.warning("Invalid path format", extra={
                'attempted_path': path,
                'error': str(e),
                'ticket_id': ticket_id,
                'security_violation': 'invalid_format'
            })
        
        # Check naming conventions (if path is valid)
        if not errors:
            try:
                filename = Path(path).name
                if filename.endswith(".tsx") or filename.endswith(".jsx"):
                    # Component files should be PascalCase
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*\.(tsx|jsx)$', filename):
                        errors.append(f"Component file should be PascalCase: {filename}")
                elif filename.endswith(".ts") or filename.endswith(".js"):
                    # Regular files should be camelCase or kebab-case
                    if not re.match(r'^[a-z][a-zA-Z0-9-]*\.(ts|js)$', filename):
                        errors.append(f"File should be camelCase or kebab-case: {filename}")
                
                # Check forbidden directories
                forbidden = ["node_modules", ".git", "dist", "build", "__pycache__", ".venv"]
                path_parts = Path(path).parts
                for forbidden_dir in forbidden:
                    if forbidden_dir in path_parts:
                        errors.append(f"Cannot write to forbidden directory: {forbidden_dir}")
                        
            except Exception as e:
                errors.append(f"Error validating conventions: {e}")
        
        if errors:
            self.logger.info("Path validation failed", extra={
                'path': path,
                'errors': errors,
                'ticket_id': ticket_id
            })
            return False, "; ".join(errors)
        
        self.logger.debug("Path validation successful", extra={
            'path': path,
            'ticket_id': ticket_id
        })
        return True, "Valid"
    
    def acquire_lock(self, path: str, ticket_id: str, duration_seconds: int = 600) -> bool:
        """Acquire advisory lock on file."""
        cursor = self.conn.cursor()
        
        # Clean up expired locks first
        self.cleanup_expired_locks()
        
        # Check if file exists and is locked
        cursor.execute("""
            SELECT lock_status, lock_owner, lock_expiry 
            FROM files 
            WHERE path = ?
        """, (path,))
        
        row = cursor.fetchone()
        
        if row:
            # Check if lock is expired
            if row['lock_status'] == 'locked':
                expiry = datetime.fromisoformat(row['lock_expiry'])
                if expiry > datetime.now():
                    # Lock is still valid
                    if row['lock_owner'] != ticket_id:
                        return False  # Someone else has the lock
                    # Same owner, extend lock
                
        # Acquire or extend lock
        expiry = datetime.now() + timedelta(seconds=duration_seconds)
        
        if row:
            cursor.execute("""
                UPDATE files 
                SET lock_status = 'locked', 
                    lock_owner = ?, 
                    lock_expiry = ?
                WHERE path = ?
            """, (ticket_id, expiry.isoformat(), path))
        else:
            # File doesn't exist yet, create placeholder
            cursor.execute("""
                INSERT INTO files (path, canonical_path, content_hash, ticket_id, 
                                 job_id, agent_name, last_event_id, lock_status, 
                                 lock_owner, lock_expiry)
                VALUES (?, ?, '', ?, '', '', '', 'locked', ?, ?)
            """, (path, path, ticket_id, ticket_id, expiry.isoformat()))
        
        self.conn.commit()
        return True
    
    def release_lock(self, path: str, ticket_id: str) -> bool:
        """Release lock on file."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE files 
            SET lock_status = 'unlocked', 
                lock_owner = NULL, 
                lock_expiry = NULL
            WHERE path = ? AND lock_owner = ?
        """, (path, ticket_id))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def register_file(self, 
                     path: str,
                     content_hash: str,
                     ticket_id: str,
                     job_id: str,
                     agent_name: str,
                     event_id: str,
                     component: Optional[str] = None,
                     dependencies: Optional[List[str]] = None) -> bool:
        """Register file in registry WITH DEPENDENCY TRACKING."""
        canonical_path = self.canonicalize_path(path, component or "unknown")
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO files 
            (path, canonical_path, content_hash, ticket_id, job_id, 
             agent_name, component, last_event_id, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (path, canonical_path, content_hash, ticket_id, job_id,
              agent_name, component, event_id, datetime.now().isoformat()))
        
        # CRITICAL: Register dependencies for Context Integration
        if dependencies:
            for dep_path in dependencies:
                cursor.execute("""
                    INSERT OR IGNORE INTO file_relationships
                    (source_file, target_file, relationship_type, strength)
                    VALUES (?, ?, 'imports', 5)
                """, (path, dep_path))
        
        self.conn.commit()
        return True
    
    def register_component_dependency(self, 
                                    source_component: str,
                                    target_component: str,
                                    dependency_type: str,
                                    ticket_id: str) -> bool:
        """Register component-level dependency."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO dependencies
            (source_component, target_component, dependency_type, ticket_id)
            VALUES (?, ?, ?, ?)
        """, (source_component, target_component, dependency_type, ticket_id))
        
        self.conn.commit()
        return cursor.rowcount > 0
    
    def check_duplicate(self, content_hash: str) -> Optional[str]:
        """Check if file with same content already exists."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT path FROM files WHERE content_hash = ?
        """, (content_hash,))
        
        row = cursor.fetchone()
        return row['path'] if row else None
    
    def get_component_files(self, component: str) -> List[Dict]:
        """Get all files for a component."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM files WHERE component = ?
        """, (component,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_file_dependencies(self, file_path: str) -> List[Dict]:
        """Get dependencies for a specific file."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT fr.target_file, fr.relationship_type, fr.strength,
                   f.component, f.content_hash
            FROM file_relationships fr
            LEFT JOIN files f ON fr.target_file = f.path
            WHERE fr.source_file = ?
            ORDER BY fr.strength DESC
        """, (file_path,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_component_dependencies(self, component: str) -> List[Dict]:
        """Get component-level dependencies."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT target_component, dependency_type, ticket_id, created_at
            FROM dependencies
            WHERE source_component = ?
            ORDER BY created_at DESC
        """, (component,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_expired_locks(self):
        """Clean up expired locks."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE files 
            SET lock_status = 'unlocked', 
                lock_owner = NULL, 
                lock_expiry = NULL
            WHERE lock_status = 'locked' 
                AND lock_expiry < ?
        """, (datetime.now().isoformat(),))
        
        self.conn.commit()
        return cursor.rowcount
    
    def get_all_files(self) -> List[Dict]:
        """Get all registered files."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM files ORDER BY updated_at DESC
        """)
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    import sys
    registry = FileRegistry()
    
    if len(sys.argv) < 2:
        print("Usage: file_registry.py <command> [args...]")
        print("Commands: validate, lock, unlock, register, check_duplicate, deps")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "validate":
        ticket_id = sys.argv[3] if len(sys.argv) > 3 else None
        valid, message = registry.validate_path(sys.argv[2], ticket_id)
        print(json.dumps({"valid": valid, "message": message}))
    elif command == "lock":
        success = registry.acquire_lock(sys.argv[2], sys.argv[3])
        print(json.dumps({"success": success}))
    elif command == "unlock":
        success = registry.release_lock(sys.argv[2], sys.argv[3])
        print(json.dumps({"success": success}))
    elif command == "register":
        # register <path> <hash> <ticket> <job> <agent> <event>
        success = registry.register_file(
            sys.argv[2], sys.argv[3], sys.argv[4],
            sys.argv[5], sys.argv[6], sys.argv[7]
        )
        print(json.dumps({"success": success}))
    elif command == "deps":
        deps = registry.get_file_dependencies(sys.argv[2])
        print(json.dumps(deps, indent=2))
    elif command == "check_duplicate":
        duplicate = registry.check_duplicate(sys.argv[2])
        print(json.dumps({"duplicate_path": duplicate}))