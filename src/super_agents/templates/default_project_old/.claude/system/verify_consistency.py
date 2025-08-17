#!/usr/bin/env python3
import json
import hashlib
import os
from pathlib import Path
from typing import Dict, List, Set
from file_registry import FileRegistry

class ConsistencyVerifier:
    """
    Verifies consistency between the file system and the file registry.
    Detects:
    - Unregistered files (exist on disk but not in registry)
    - Ghost files (in registry but not on disk)
    - Hash mismatches (file modified outside protocol)
    - Orphaned dependencies (references to non-existent files)
    """
    
    def __init__(self):
        self.registry = FileRegistry()
        self.ignored_patterns = [
            '.git', 'node_modules', '__pycache__', 
            '.pytest_cache', 'dist', 'build', '.DS_Store',
            '.claude', 'tmp', '.tmp', '.backup'
        ]
    
    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        for pattern in self.ignored_patterns:
            if pattern in path:
                return True
        return path.startswith('.')
    
    def scan_filesystem(self, base_paths: List[str] = ["src", "."]) -> Dict[str, str]:
        """Scan filesystem and calculate hashes."""
        files = {}
        
        for base_path in base_paths:
            base = Path(base_path)
            
            if not base.exists():
                continue
            
            # Handle single file
            if base.is_file():
                if not self.should_ignore(str(base)):
                    with open(base, 'rb') as f:
                        content_hash = hashlib.sha256(f.read()).hexdigest()
                    files[str(base)] = content_hash
                continue
            
            # Handle directory
            for path in base.rglob("*"):
                if path.is_file() and not self.should_ignore(str(path)):
                    try:
                        with open(path, 'rb') as f:
                            content_hash = hashlib.sha256(f.read()).hexdigest()
                        files[str(path)] = content_hash
                    except (PermissionError, OSError):
                        # Skip files we can't read
                        continue
        
        return files
    
    def get_registry_files(self) -> Dict[str, str]:
        """Get all files from registry."""
        cursor = self.registry.conn.cursor()
        cursor.execute("SELECT path, content_hash FROM files")
        
        files = {}
        for row in cursor.fetchall():
            files[row['path']] = row['content_hash']
        
        return files
    
    def verify_consistency(self, base_paths: List[str] = ["src", "."]) -> Dict:
        """Verify consistency between filesystem and registry."""
        # Scan filesystem
        fs_files = self.scan_filesystem(base_paths)
        
        # Get registry files
        reg_files = self.get_registry_files()
        
        # Compare
        fs_paths = set(fs_files.keys())
        reg_paths = set(reg_files.keys())
        
        # Find discrepancies
        unregistered = list(fs_paths - reg_paths)
        ghost_files = list(reg_paths - fs_paths)
        
        # Check hashes for common files
        hash_mismatches = []
        for path in fs_paths & reg_paths:
            if fs_files[path] != reg_files[path]:
                hash_mismatches.append({
                    "path": path,
                    "expected": reg_files[path],
                    "actual": fs_files[path]
                })
        
        # Check for orphaned dependencies
        orphaned_deps = self._check_orphaned_dependencies()
        
        # Build report
        total_issues = len(unregistered) + len(ghost_files) + len(hash_mismatches) + len(orphaned_deps)
        
        report = {
            "status": "OK" if total_issues == 0 else "DRIFT_DETECTED",
            "unregistered_files": sorted(unregistered),
            "ghost_files": sorted(ghost_files),
            "hash_mismatches": hash_mismatches,
            "orphaned_dependencies": orphaned_deps,
            "total_files_checked": len(fs_paths | reg_paths),
            "total_issues": total_issues,
            "scan_paths": base_paths,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
        return report
    
    def _check_orphaned_dependencies(self) -> List[Dict]:
        """Check for dependency references to non-existent files."""
        cursor = self.registry.conn.cursor()
        
        # Get all file dependencies
        cursor.execute("""
            SELECT fr.source_file, fr.target_file, fr.relationship_type
            FROM file_relationships fr
            LEFT JOIN files f ON fr.target_file = f.path
            WHERE f.path IS NULL
        """)
        
        orphaned = []
        for row in cursor.fetchall():
            orphaned.append({
                "source_file": row['source_file'],
                "missing_target": row['target_file'],
                "relationship_type": row['relationship_type']
            })
        
        return orphaned
    
    def auto_reconcile(self, report: Dict, ticket_id: str = "RECONCILE") -> Dict:
        """Attempt to automatically reconcile discrepancies."""
        actions = []
        warnings = []
        
        # Register unregistered files
        for path in report['unregistered_files']:
            try:
                with open(path, 'rb') as f:
                    content_hash = hashlib.sha256(f.read()).hexdigest()
                
                self.registry.register_file(
                    path, content_hash, ticket_id,
                    "RECONCILE", "verifier-agent", "reconcile_event"
                )
                actions.append(f"Registered: {path}")
            except Exception as e:
                warnings.append(f"Failed to register {path}: {str(e)}")
        
        # Remove ghost files from registry
        cursor = self.registry.conn.cursor()
        for path in report['ghost_files']:
            cursor.execute("DELETE FROM files WHERE path = ?", (path,))
            actions.append(f"Removed ghost: {path}")
        
        # Clean up orphaned dependencies
        for orphan in report['orphaned_dependencies']:
            cursor.execute("""
                DELETE FROM file_relationships 
                WHERE source_file = ? AND target_file = ?
            """, (orphan['source_file'], orphan['missing_target']))
            actions.append(f"Removed orphaned dependency: {orphan['source_file']} -> {orphan['missing_target']}")
        
        self.registry.conn.commit()
        
        # Hash mismatches require manual intervention
        for mismatch in report['hash_mismatches']:
            warnings.append(f"MANUAL REQUIRED: {mismatch['path']} has been modified outside protocol")
        
        reconciliation_result = {
            "reconciliation_complete": len(report['hash_mismatches']) == 0,
            "actions_taken": actions,
            "warnings": warnings,
            "manual_intervention_required": len(report['hash_mismatches']) > 0
        }
        
        return reconciliation_result
    
    def verify_file_integrity(self, file_path: str) -> Dict:
        """Verify integrity of a specific file."""
        cursor = self.registry.conn.cursor()
        cursor.execute("SELECT * FROM files WHERE path = ?", (file_path,))
        
        registry_entry = cursor.fetchone()
        if not registry_entry:
            return {
                "status": "NOT_REGISTERED",
                "path": file_path,
                "error": "File not found in registry"
            }
        
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                "status": "MISSING",
                "path": file_path,
                "error": "File exists in registry but not on filesystem"
            }
        
        # Check hash
        with open(file_path_obj, 'rb') as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        expected_hash = registry_entry['content_hash']
        
        if actual_hash != expected_hash:
            return {
                "status": "MODIFIED",
                "path": file_path,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "last_modified": registry_entry['updated_at']
            }
        
        return {
            "status": "OK",
            "path": file_path,
            "hash": actual_hash,
            "last_modified": registry_entry['updated_at']
        }
    
    def get_dependency_health(self) -> Dict:
        """Get health report for all dependencies."""
        cursor = self.registry.conn.cursor()
        
        # Check file relationships
        cursor.execute("""
            SELECT 
                COUNT(*) as total_relationships,
                COUNT(CASE WHEN f.path IS NULL THEN 1 END) as broken_relationships
            FROM file_relationships fr
            LEFT JOIN files f ON fr.target_file = f.path
        """)
        
        rel_stats = cursor.fetchone()
        
        # Check component dependencies
        cursor.execute("""
            SELECT 
                COUNT(*) as total_component_deps,
                COUNT(DISTINCT source_component) as components_with_deps
            FROM dependencies
        """)
        
        comp_stats = cursor.fetchone()
        
        return {
            "file_relationships": {
                "total": rel_stats['total_relationships'],
                "broken": rel_stats['broken_relationships'],
                "health_percentage": round(
                    ((rel_stats['total_relationships'] - rel_stats['broken_relationships']) / 
                     max(rel_stats['total_relationships'], 1)) * 100, 2
                )
            },
            "component_dependencies": {
                "total": comp_stats['total_component_deps'],
                "components_with_deps": comp_stats['components_with_deps']
            }
        }

if __name__ == "__main__":
    import sys
    verifier = ConsistencyVerifier()
    
    if len(sys.argv) < 2:
        print("Usage: verify_consistency.py <command> [args...]")
        print("Commands: verify, reconcile, check_file, dep_health")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "verify":
        base_paths = sys.argv[2:] if len(sys.argv) > 2 else ["src", "."]
        report = verifier.verify_consistency(base_paths)
        print(json.dumps(report, indent=2))
    elif command == "reconcile":
        base_paths = sys.argv[2:] if len(sys.argv) > 2 else ["src", "."]
        report = verifier.verify_consistency(base_paths)
        if report['total_issues'] > 0:
            reconciliation = verifier.auto_reconcile(report)
            print(json.dumps(reconciliation, indent=2))
        else:
            print(json.dumps({"status": "No reconciliation needed"}))
    elif command == "check_file":
        if len(sys.argv) < 3:
            print("Usage: verify_consistency.py check_file <file_path>")
            sys.exit(1)
        result = verifier.verify_file_integrity(sys.argv[2])
        print(json.dumps(result, indent=2))
    elif command == "dep_health":
        health = verifier.get_dependency_health()
        print(json.dumps(health, indent=2))