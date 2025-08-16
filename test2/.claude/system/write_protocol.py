#!/usr/bin/env python3
import json
import hashlib
import os
import shutil
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from file_registry import FileRegistry
from event_logger import EventLogger

class ThreePhaseWriter:
    """
    Three-Phase Write Protocol:
    Phase 1: Plan and Validate - Check paths, permissions, locks
    Phase 2: Validate in Context - Check for conflicts, dependencies
    Phase 3: Apply Changes - Atomic writes with rollback capability
    """
    
    def __init__(self):
        self.registry = FileRegistry()
        self.logger = EventLogger()
        
    def phase1_plan(self, intents: List[Dict], ticket_id: str) -> Tuple[List[Dict], List[str]]:
        """
        Phase 1: Plan and validate write intents.
        Returns: (validated_intents, errors)
        """
        validated = []
        errors = []
        request_id = str(uuid.uuid4())
        
        # Log the start of write request
        self._log_write_request(request_id, ticket_id, 1, intents, "pending")
        
        for intent in intents:
            path = intent['path']
            operation = intent['operation']
            
            # Validate path
            valid, message = self.registry.validate_path(path)
            if not valid:
                errors.append(f"{path}: {message}")
                intent['validation_status'] = 'rejected'
                intent['rejection_reason'] = message
                continue
            
            # Check for duplicates (for create operations)
            if operation == 'create' and 'content' in intent:
                content_hash = hashlib.sha256(
                    intent['content'].encode()
                ).hexdigest()
                
                duplicate_path = self.registry.check_duplicate(content_hash)
                if duplicate_path:
                    errors.append(f"{path}: Duplicate content exists at {duplicate_path}")
                    intent['validation_status'] = 'rejected'
                    intent['rejection_reason'] = f"Duplicate of {duplicate_path}"
                    continue
            
            # Try to acquire lock
            if not self.registry.acquire_lock(path, ticket_id):
                errors.append(f"{path}: Could not acquire lock")
                intent['validation_status'] = 'rejected'
                intent['rejection_reason'] = "Lock unavailable"
                continue
            
            # Canonicalize path
            intent['canonical_path'] = self.registry.canonicalize_path(
                path, 
                intent.get('component', 'unknown')
            )
            intent['validation_status'] = 'validated'
            intent['request_id'] = request_id
            validated.append(intent)
        
        # Update request status
        status = "validated" if not errors else "failed"
        self._log_write_request(request_id, ticket_id, 1, validated, status, 
                               "; ".join(errors) if errors else None)
        
        return validated, errors
    
    def phase2_validate(self, intents: List[Dict], workspace_path: str) -> Tuple[bool, List[str]]:
        """
        Phase 2: Additional validation in workspace context.
        Returns: (all_valid, errors)
        """
        errors = []
        workspace = Path(workspace_path)
        request_id = intents[0]['request_id'] if intents else str(uuid.uuid4())
        
        # Log phase 2 start
        self._log_write_request(request_id, intents[0].get('ticket_id', ''), 2, intents, "pending")
        
        for intent in intents:
            if intent['validation_status'] != 'validated':
                continue
            
            path = workspace / intent['path']
            operation = intent['operation']
            
            if operation == 'update' or operation == 'delete':
                # File must exist
                if not path.exists():
                    errors.append(f"{intent['path']}: File does not exist for {operation}")
                    intent['validation_status'] = 'rejected'
                    continue
                
                # Verify hash matches (prevent concurrent modification)
                if 'content_hash_before' in intent:
                    with open(path, 'rb') as f:
                        actual_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    if actual_hash != intent['content_hash_before']:
                        errors.append(f"{intent['path']}: File modified since read")
                        intent['validation_status'] = 'rejected'
                        continue
            
            elif operation == 'create':
                # File must not exist
                if path.exists():
                    errors.append(f"{intent['path']}: File already exists")
                    intent['validation_status'] = 'rejected'
                    continue
            
            # Check dependencies if specified
            if 'dependencies' in intent:
                for dep_path in intent['dependencies']:
                    dep_full_path = workspace / dep_path
                    if not dep_full_path.exists():
                        errors.append(f"{intent['path']}: Dependency {dep_path} not found")
                        intent['validation_status'] = 'rejected'
                        break
        
        # Update request status
        status = "validated" if not errors else "failed"
        self._log_write_request(request_id, intents[0].get('ticket_id', ''), 2, intents, status,
                               "; ".join(errors) if errors else None)
        
        return len(errors) == 0, errors
    
    def phase3_apply(self, 
                     intents: List[Dict], 
                     workspace_path: str,
                     ticket_id: str,
                     job_id: str,
                     agent_name: str) -> Tuple[bool, List[str]]:
        """
        Phase 3: Apply validated intents atomically.
        Returns: (success, results)
        """
        workspace = Path(workspace_path)
        results = []
        applied = []
        request_id = intents[0]['request_id'] if intents else str(uuid.uuid4())
        
        # Log phase 3 start
        self._log_write_request(request_id, ticket_id, 3, intents, "pending")
        
        # Create backup directory for rollback
        backup_dir = workspace / '.backup' / request_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            for intent in intents:
                if intent['validation_status'] != 'validated':
                    continue
                
                path = workspace / intent['path']
                operation = intent['operation']
                
                # Create parent directories if needed
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Backup existing file if it exists
                if path.exists():
                    backup_path = backup_dir / intent['path']
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, backup_path)
                
                if operation == 'create' or operation == 'update':
                    # Write content atomically (write to temp, then rename)
                    temp_path = path.with_suffix('.tmp')
                    with open(temp_path, 'w') as f:
                        f.write(intent['content'])
                    
                    # Calculate final hash
                    with open(temp_path, 'rb') as f:
                        content_hash = hashlib.sha256(f.read()).hexdigest()
                    
                    # Atomic rename
                    temp_path.rename(path)
                    
                    # Register in database
                    event_id = self.logger.append_event(
                        ticket_id=ticket_id,
                        event_type=f"FILE_{operation.upper()}",
                        payload={
                            "path": str(intent['path']),
                            "hash": content_hash,
                            "request_id": request_id
                        },
                        agent=agent_name
                    )
                    
                    self.registry.register_file(
                        str(intent['path']),
                        content_hash,
                        ticket_id,
                        job_id,
                        agent_name,
                        event_id,
                        intent.get('component'),
                        intent.get('dependencies')
                    )
                    
                    results.append(f"{operation} {intent['path']}: Success")
                    applied.append(intent)
                    
                elif operation == 'delete':
                    # Delete file
                    path.unlink()
                    
                    # Log deletion
                    event_id = self.logger.append_event(
                        ticket_id=ticket_id,
                        event_type="FILE_DELETED",
                        payload={
                            "path": str(intent['path']),
                            "request_id": request_id
                        },
                        agent=agent_name
                    )
                    
                    results.append(f"delete {intent['path']}: Success")
                    applied.append(intent)
            
            # Log successful completion
            self._log_write_request(request_id, ticket_id, 3, intents, "committed")
            
            # Clean up backup directory on success
            shutil.rmtree(backup_dir, ignore_errors=True)
            
            return True, results
            
        except Exception as e:
            # Rollback on error
            self._rollback_changes(applied, backup_dir, workspace)
            
            # Log rollback
            self._log_write_request(request_id, ticket_id, 3, intents, "rolled_back", str(e))
            
            return False, [f"Rollback due to error: {str(e)}"]
        
        finally:
            # Release all locks
            for intent in intents:
                self.registry.release_lock(intent['path'], ticket_id)
    
    def _rollback_changes(self, applied: List[Dict], backup_dir: Path, workspace: Path):
        """Rollback applied changes using backups."""
        for intent in applied:
            path = workspace / intent['path']
            backup_path = backup_dir / intent['path']
            
            if backup_path.exists():
                # Restore from backup
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, path)
            elif path.exists() and intent['operation'] == 'create':
                # Remove newly created file
                path.unlink()
    
    def _log_write_request(self, request_id: str, ticket_id: str, phase: int, 
                          intents: List[Dict], status: str, error_message: str = None):
        """Log write request status to database."""
        cursor = self.registry.conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO write_requests
            (request_id, ticket_id, phase, status, intents_json, 
             completed_at, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, ticket_id, phase, status, json.dumps(intents),
            datetime.now().isoformat() if status in ['committed', 'failed', 'rolled_back'] else None,
            error_message
        ))
        
        self.registry.conn.commit()
    
    def get_write_history(self, ticket_id: str) -> List[Dict]:
        """Get write history for a ticket."""
        cursor = self.registry.conn.cursor()
        cursor.execute("""
            SELECT * FROM write_requests 
            WHERE ticket_id = ? 
            ORDER BY created_at DESC
        """, (ticket_id,))
        
        return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    import sys
    writer = ThreePhaseWriter()
    
    if len(sys.argv) < 3:
        print("Usage: write_protocol.py <intents_json> <ticket_id> [workspace_path] [job_id] [agent_name]")
        sys.exit(1)
    
    intents = json.loads(sys.argv[1])
    ticket_id = sys.argv[2]
    workspace_path = sys.argv[3] if len(sys.argv) > 3 else "."
    job_id = sys.argv[4] if len(sys.argv) > 4 else "JOB-123"
    agent_name = sys.argv[5] if len(sys.argv) > 5 else "test-agent"
    
    # Phase 1: Plan
    validated, errors = writer.phase1_plan(intents, ticket_id)
    if errors:
        print(json.dumps({"phase": 1, "errors": errors}))
        sys.exit(1)
    
    # Phase 2: Validate
    valid, errors = writer.phase2_validate(validated, workspace_path)
    if not valid:
        print(json.dumps({"phase": 2, "errors": errors}))
        sys.exit(1)
    
    # Phase 3: Apply
    success, results = writer.phase3_apply(
        validated, workspace_path, ticket_id, job_id, agent_name
    )
    
    print(json.dumps({
        "success": success,
        "results": results
    }))