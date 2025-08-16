#!/usr/bin/env python3
"""
AET Security Manager
Implements security hardening features for Phase 1.5
- Input validation
- Secure credential storage
- Audit logging
- Permission boundaries
"""

import os
import re
import json
import hashlib
import hmac
import base64
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import logging
from functools import wraps
import getpass

class SecurityManager:
    """Comprehensive security management for AET system"""
    
    # Input validation patterns
    PATTERNS = {
        'filename': r'^[a-zA-Z0-9_\-\.]+$',
        'path': r'^[a-zA-Z0-9_\-\./]+$',
        'agent_name': r'^[a-z\-]+$',
        'port': r'^[0-9]{4,5}$',
        'command': r'^[a-zA-Z0-9_\-\s]+$',
        'json_key': r'^[a-zA-Z0-9_]+$'
    }
    
    # Sensitive operations that require audit logging
    SENSITIVE_OPS = [
        'credential_access',
        'credential_storage',
        'admin_command',
        'system_config_change',
        'agent_permission_change',
        'security_bypass'
    ]
    
    def __init__(self, project_dir: Path = None):
        self.project_dir = project_dir or Path.cwd()
        self.claude_dir = self.project_dir / ".claude"
        self.security_dir = self.claude_dir / "security"
        self.audit_dir = self.security_dir / "audit"
        self.vault_dir = self.security_dir / "vault"
        
        # Create secure directories with restricted permissions
        for dir_path in [self.security_dir, self.audit_dir, self.vault_dir]:
            dir_path.mkdir(parents=True, exist_ok=True, mode=0o700)
            
        # Initialize components
        self.logger = self._setup_audit_logger()
        self.vault = self._initialize_vault()
        
        # Agent permission boundaries
        self.agent_permissions = self._load_agent_permissions()
        
    def _setup_audit_logger(self) -> logging.Logger:
        """Setup secure audit logger"""
        logger = logging.getLogger("AET_Security_Audit")
        logger.setLevel(logging.INFO)
        
        # Audit log with restricted permissions
        audit_log = self.audit_dir / "security_audit.log"
        
        handler = logging.FileHandler(audit_log, mode='a')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        
        logger.addHandler(handler)
        
        # Set restrictive permissions on audit log
        if audit_log.exists():
            os.chmod(audit_log, 0o600)
            
        return logger
        
    def _initialize_vault(self) -> 'CredentialVault':
        """Initialize secure credential vault"""
        return CredentialVault(self.vault_dir)
        
    def _load_agent_permissions(self) -> Dict[str, Dict[str, Any]]:
        """Load agent permission boundaries"""
        permissions_file = self.security_dir / "agent_permissions.json"
        
        if permissions_file.exists():
            try:
                with open(permissions_file, 'r') as f:
                    return json.load(f)
            except:
                pass
                
        # Default permissions
        default_permissions = {
            "contract-guardian": {
                "read": ["*"],
                "write": [".claude/triggers/", ".claude/events/"],
                "execute": [],
                "network": False,
                "priority": "critical"
            },
            "security-agent": {
                "read": ["*"],
                "write": [".claude/security/", ".claude/triggers/"],
                "execute": ["security_scan.sh"],
                "network": False,
                "priority": "critical"
            },
            "test-executor": {
                "read": ["*"],
                "write": [".claude/test_reports/"],
                "execute": ["pytest", "npm test"],
                "network": False,
                "priority": "high"
            },
            "developer-agent": {
                "read": ["*"],
                "write": ["src/", "lib/", "tests/"],
                "execute": [],
                "network": False,
                "priority": "normal"
            },
            "monitoring-agent": {
                "read": ["*"],
                "write": [".claude/monitoring/"],
                "execute": [],
                "network": True,  # Can call monitoring APIs
                "priority": "high"
            }
        }
        
        # Save default permissions
        with open(permissions_file, 'w') as f:
            json.dump(default_permissions, f, indent=2)
        os.chmod(permissions_file, 0o600)
        
        return default_permissions
        
    # ========== Input Validation ==========
    
    def validate_input(self, value: str, input_type: str) -> bool:
        """Validate user input against patterns"""
        if input_type not in self.PATTERNS:
            self.audit_log("validation_error", f"Unknown input type: {input_type}")
            return False
            
        pattern = self.PATTERNS[input_type]
        if not re.match(pattern, value):
            self.audit_log("validation_failed", f"Invalid {input_type}: {value[:50]}")
            return False
            
        return True
        
    def sanitize_path(self, path: str) -> Optional[str]:
        """Sanitize and validate file paths"""
        # Remove null bytes
        path = path.replace('\0', '')
        
        # Resolve to absolute path
        try:
            resolved = Path(path).resolve()
        except:
            self.audit_log("path_sanitization_failed", f"Invalid path: {path[:100]}")
            return None
            
        # Check for path traversal
        project_root = self.project_dir.resolve()
        if not str(resolved).startswith(str(project_root)):
            self.audit_log("path_traversal_attempt", f"Path outside project: {resolved}")
            return None
            
        return str(resolved)
        
    def validate_json(self, data: str) -> Optional[Dict]:
        """Validate and parse JSON safely"""
        try:
            # Size limit (10MB)
            if len(data) > 10 * 1024 * 1024:
                self.audit_log("json_too_large", f"JSON size: {len(data)}")
                return None
                
            parsed = json.loads(data)
            
            # Depth limit to prevent DoS
            if self._json_depth(parsed) > 10:
                self.audit_log("json_too_deep", "JSON nesting exceeds limit")
                return None
                
            return parsed
            
        except json.JSONDecodeError as e:
            self.audit_log("json_parse_error", str(e))
            return None
            
    def _json_depth(self, obj: Any, depth: int = 0) -> int:
        """Calculate JSON nesting depth"""
        if depth > 100:  # Circuit breaker
            return depth
            
        if isinstance(obj, dict):
            return max([self._json_depth(v, depth + 1) for v in obj.values()] + [depth])
        elif isinstance(obj, list):
            return max([self._json_depth(v, depth + 1) for v in obj] + [depth])
        else:
            return depth
            
    # ========== Audit Logging ==========
    
    def audit_log(self, operation: str, details: str = "", 
                  severity: str = "INFO", user: str = None):
        """Log security-relevant operations"""
        user = user or os.environ.get('USER', 'unknown')
        
        # Check if sensitive operation
        is_sensitive = operation in self.SENSITIVE_OPS
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user,
            'operation': operation,
            'details': details,
            'severity': severity,
            'sensitive': is_sensitive,
            'pid': os.getpid()
        }
        
        # Log to audit file
        log_message = (
            f"{log_entry['timestamp']} | "
            f"{severity} | "
            f"USER={user} | "
            f"OP={operation} | "
            f"{details}"
        )
        
        if severity == "CRITICAL":
            self.logger.critical(log_message)
        elif severity == "ERROR":
            self.logger.error(log_message)
        elif severity == "WARNING":
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)
            
        # For sensitive operations, also create immutable record
        if is_sensitive:
            self._create_immutable_audit_record(log_entry)
            
    def _create_immutable_audit_record(self, log_entry: Dict):
        """Create tamper-evident audit record"""
        # Add hash chain
        prev_hash = self._get_last_audit_hash()
        log_entry['prev_hash'] = prev_hash
        
        # Calculate entry hash
        entry_str = json.dumps(log_entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_str.encode()).hexdigest()
        log_entry['hash'] = entry_hash
        
        # Save to immutable log
        immutable_log = self.audit_dir / "immutable_audit.jsonl"
        with open(immutable_log, 'a') as f:
            json.dump(log_entry, f)
            f.write('\n')
            
        # Set read-only
        os.chmod(immutable_log, 0o400)
        
    def _get_last_audit_hash(self) -> str:
        """Get hash of last audit entry for chain"""
        immutable_log = self.audit_dir / "immutable_audit.jsonl"
        
        if not immutable_log.exists():
            return "0" * 64  # Genesis hash
            
        try:
            # Temporarily make readable
            os.chmod(immutable_log, 0o600)
            
            with open(immutable_log, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_entry = json.loads(lines[-1])
                    return last_entry.get('hash', "0" * 64)
                    
            # Restore read-only
            os.chmod(immutable_log, 0o400)
            
        except:
            pass
            
        return "0" * 64
        
    # ========== Permission Boundaries ==========
    
    def check_agent_permission(self, agent: str, operation: str, 
                              resource: str) -> bool:
        """Check if agent has permission for operation"""
        if agent not in self.agent_permissions:
            self.audit_log("unknown_agent", f"Agent: {agent}", "WARNING")
            return False
            
        perms = self.agent_permissions[agent]
        
        # Check operation type
        if operation == "read":
            allowed_paths = perms.get('read', [])
        elif operation == "write":
            allowed_paths = perms.get('write', [])
        elif operation == "execute":
            allowed_paths = perms.get('execute', [])
        else:
            self.audit_log("invalid_operation", f"Op: {operation}", "WARNING")
            return False
            
        # Check if resource matches allowed paths
        resource_path = Path(resource).resolve()
        
        for allowed in allowed_paths:
            if allowed == "*":
                return True
            allowed_path = (self.project_dir / allowed).resolve()
            if str(resource_path).startswith(str(allowed_path)):
                return True
                
        self.audit_log("permission_denied", 
                      f"Agent={agent}, Op={operation}, Resource={resource}",
                      "WARNING")
        return False
        
    def enforce_permission(agent: str):
        """Decorator to enforce agent permissions"""
        def decorator(func):
            @wraps(func)
            def wrapper(self, *args, **kwargs):
                # Extract resource from function args
                resource = kwargs.get('resource') or (args[0] if args else None)
                
                # Determine operation from function name
                if 'read' in func.__name__:
                    operation = 'read'
                elif 'write' in func.__name__:
                    operation = 'write'
                elif 'execute' in func.__name__:
                    operation = 'execute'
                else:
                    operation = 'unknown'
                    
                # Check permission
                security = SecurityManager()
                if not security.check_agent_permission(agent, operation, resource):
                    raise PermissionError(f"Agent {agent} denied {operation} on {resource}")
                    
                # Audit the operation
                security.audit_log(f"agent_{operation}", 
                                 f"Agent={agent}, Resource={resource}")
                
                return func(self, *args, **kwargs)
            return wrapper
        return decorator


class CredentialVault:
    """Secure credential storage using encryption"""
    
    def __init__(self, vault_dir: Path):
        self.vault_dir = vault_dir
        self.vault_file = vault_dir / "credentials.vault"
        self.key_file = vault_dir / ".vault_key"
        
        # Initialize or load encryption key
        self.cipher = self._initialize_cipher()
        
    def _initialize_cipher(self) -> Fernet:
        """Initialize or load encryption key"""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Restrict permissions
            os.chmod(self.key_file, 0o600)
            
        return Fernet(key)
        
    def store_credential(self, name: str, value: str, 
                        metadata: Dict[str, Any] = None) -> bool:
        """Store encrypted credential"""
        try:
            # Load existing vault
            vault = self._load_vault()
            
            # Encrypt the value
            encrypted_value = self.cipher.encrypt(value.encode())
            
            # Store with metadata
            vault[name] = {
                'value': base64.b64encode(encrypted_value).decode(),
                'created': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Save vault
            self._save_vault(vault)
            
            # Audit log
            SecurityManager().audit_log("credential_storage", 
                                       f"Stored credential: {name}",
                                       "INFO")
            return True
            
        except Exception as e:
            SecurityManager().audit_log("credential_storage_failed",
                                       f"Failed to store {name}: {e}",
                                       "ERROR")
            return False
            
    def retrieve_credential(self, name: str) -> Optional[str]:
        """Retrieve decrypted credential"""
        try:
            vault = self._load_vault()
            
            if name not in vault:
                return None
                
            # Decrypt the value
            encrypted_value = base64.b64decode(vault[name]['value'])
            decrypted_value = self.cipher.decrypt(encrypted_value)
            
            # Audit log
            SecurityManager().audit_log("credential_access",
                                       f"Retrieved credential: {name}",
                                       "INFO")
            
            return decrypted_value.decode()
            
        except Exception as e:
            SecurityManager().audit_log("credential_retrieval_failed",
                                       f"Failed to retrieve {name}: {e}",
                                       "ERROR")
            return None
            
    def _load_vault(self) -> Dict:
        """Load vault file"""
        if not self.vault_file.exists():
            return {}
            
        try:
            with open(self.vault_file, 'r') as f:
                return json.load(f)
        except:
            return {}
            
    def _save_vault(self, vault: Dict):
        """Save vault file with restricted permissions"""
        with open(self.vault_file, 'w') as f:
            json.dump(vault, f, indent=2)
        os.chmod(self.vault_file, 0o600)


def main():
    """CLI interface for security manager"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AET Security Manager")
    parser.add_argument('--validate', metavar='TYPE:VALUE',
                       help='Validate input (e.g., path:/tmp/file)')
    parser.add_argument('--store-credential', metavar='NAME',
                       help='Store a credential securely')
    parser.add_argument('--get-credential', metavar='NAME',
                       help='Retrieve a credential')
    parser.add_argument('--audit-report', action='store_true',
                       help='Generate audit report')
    parser.add_argument('--check-permission', metavar='AGENT:OP:RESOURCE',
                       help='Check agent permission')
    
    args = parser.parse_args()
    
    security = SecurityManager()
    
    if args.validate:
        parts = args.validate.split(':', 1)
        if len(parts) == 2:
            input_type, value = parts
            if security.validate_input(value, input_type):
                print(f"✓ Valid {input_type}")
            else:
                print(f"✗ Invalid {input_type}")
                
    elif args.store_credential:
        value = getpass.getpass(f"Enter value for {args.store_credential}: ")
        if security.vault.store_credential(args.store_credential, value):
            print(f"✓ Credential stored: {args.store_credential}")
        else:
            print(f"✗ Failed to store credential")
            
    elif args.get_credential:
        value = security.vault.retrieve_credential(args.get_credential)
        if value:
            print(f"Credential value: {value}")
        else:
            print(f"✗ Credential not found")
            
    elif args.audit_report:
        # Generate audit report
        audit_log = security.audit_dir / "security_audit.log"
        if audit_log.exists():
            print("=== Recent Security Audit Events ===")
            with open(audit_log, 'r') as f:
                lines = f.readlines()[-20:]  # Last 20 events
                for line in lines:
                    print(line.strip())
        else:
            print("No audit events found")
            
    elif args.check_permission:
        parts = args.check_permission.split(':', 2)
        if len(parts) == 3:
            agent, op, resource = parts
            if security.check_agent_permission(agent, op, resource):
                print(f"✓ Permission granted")
            else:
                print(f"✗ Permission denied")
                
    else:
        parser.print_help()


if __name__ == "__main__":
    main()