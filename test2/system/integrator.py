#!/usr/bin/env python3
import json
import subprocess
import shutil
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Set
from write_protocol import ThreePhaseWriter
from file_registry import FileRegistry
from event_logger import EventLogger

class Integrator:
    """
    Integrates validated workspace changes into the main repository.
    Handles dependency registration, API updates, and knowledge management.
    """
    
    def __init__(self):
        self.writer = ThreePhaseWriter()
        self.registry = FileRegistry()
        self.logger = EventLogger()
        self.km_url = "http://localhost:5001/mcp"
    
    def prepare_integration(self, job_id: str, workspace_path: str) -> Tuple[List[Dict], List[str]]:
        """Prepare file intents for integration by analyzing workspace changes."""
        workspace = Path(workspace_path)
        intents = []
        errors = []
        
        if not workspace.exists():
            errors.append(f"Workspace path does not exist: {workspace_path}")
            return intents, errors
        
        # Get list of changed files using git
        try:
            result = subprocess.run(
                ["git", "diff", "--name-status", "HEAD"],
                cwd=workspace,
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            # Fallback: scan for all files if git fails
            return self._fallback_file_scan(workspace)
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split('\t')
            status = parts[0]
            filepath = parts[1]
            
            if status == 'A' or status == 'M':
                # Added or modified
                full_path = workspace / filepath
                if full_path.exists():
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except UnicodeDecodeError:
                        # Skip binary files
                        continue
                    
                    intent = {
                        "operation": "create" if status == 'A' else "update",
                        "path": filepath,
                        "content": content,
                        "component": self._infer_component(filepath),
                        "dependencies": self._extract_dependencies(content, filepath)
                    }
                    intents.append(intent)
            
            elif status == 'D':
                # Deleted
                intent = {
                    "operation": "delete",
                    "path": filepath
                }
                intents.append(intent)
        
        return intents, errors
    
    def _fallback_file_scan(self, workspace: Path) -> Tuple[List[Dict], List[str]]:
        """Fallback method to scan workspace when git is not available."""
        intents = []
        errors = []
        
        for file_path in workspace.rglob("*"):
            if file_path.is_file() and not self._should_ignore_file(str(file_path)):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    relative_path = file_path.relative_to(workspace)
                    intent = {
                        "operation": "create",
                        "path": str(relative_path),
                        "content": content,
                        "component": self._infer_component(str(relative_path)),
                        "dependencies": self._extract_dependencies(content, str(relative_path))
                    }
                    intents.append(intent)
                except (UnicodeDecodeError, PermissionError):
                    continue
        
        return intents, errors
    
    def _should_ignore_file(self, path: str) -> bool:
        """Check if file should be ignored during integration."""
        ignored_patterns = [
            '.git', 'node_modules', '__pycache__', '.DS_Store',
            '.tmp', '.backup', 'tmp'
        ]
        return any(pattern in path for pattern in ignored_patterns)
    
    def _infer_component(self, filepath: str) -> str:
        """Infer component name from file path."""
        parts = Path(filepath).parts
        
        # Look for common component indicators
        if 'components' in parts:
            idx = parts.index('components')
            if idx + 1 < len(parts):
                return parts[idx + 1]
        
        # Use directory name as component
        if len(parts) > 1:
            return parts[-2]  # Parent directory
        
        return "core"
    
    def _extract_dependencies(self, content: str, filepath: str) -> List[str]:
        """Extract file dependencies from content."""
        dependencies = []
        
        # Extract import statements (JavaScript/TypeScript)
        import re
        
        # ES6 imports
        import_patterns = [
            r'import\s+.*?from\s+[\'"]([^\'"\s]+)[\'"]',
            r'import\s+[\'"]([^\'"\s]+)[\'"]',
            r'require\([\'"]([^\'"\s]+)[\'"]\)',
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                # Convert relative imports to file paths
                if match.startswith('./') or match.startswith('../'):
                    dep_path = self._resolve_relative_import(filepath, match)
                    if dep_path:
                        dependencies.append(dep_path)
        
        return dependencies
    
    def _resolve_relative_import(self, source_file: str, import_path: str) -> str:
        """Resolve relative import to actual file path."""
        source_dir = Path(source_file).parent
        resolved = (source_dir / import_path).resolve()
        
        # Add common extensions if missing
        extensions = ['.ts', '.tsx', '.js', '.jsx']
        if not resolved.suffix:
            for ext in extensions:
                if (resolved.with_suffix(ext)).exists():
                    return str(resolved.with_suffix(ext))
        
        return str(resolved) if resolved.exists() else None
    
    def check_conflicts(self, workspace_path: str) -> List[str]:
        """Check for merge conflicts with main branch."""
        conflicts = []
        
        try:
            # Fetch latest main
            subprocess.run(
                ["git", "fetch", "origin", "main"],
                cwd=workspace_path,
                capture_output=True,
                check=True
            )
            
            # Try merge --no-commit to check for conflicts
            result = subprocess.run(
                ["git", "merge", "--no-commit", "--no-ff", "origin/main"],
                cwd=workspace_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # Get list of conflicted files
                conflict_result = subprocess.run(
                    ["git", "diff", "--name-only", "--diff-filter=U"],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True
                )
                conflicts = conflict_result.stdout.strip().split('\n')
                
                # Abort the merge
                subprocess.run(
                    ["git", "merge", "--abort"],
                    cwd=workspace_path,
                    capture_output=True
                )
        except subprocess.CalledProcessError:
            # Git operations failed, assume no conflicts
            pass
        
        return [c for c in conflicts if c]  # Filter empty strings
    
    def integrate(self, 
                 ticket_id: str,
                 job_id: str,
                 workspace_path: str,
                 target_path: str = ".") -> Dict:
        """Perform full integration with dependency registration."""
        workspace = Path(workspace_path)
        target = Path(target_path)
        
        # Check for conflicts
        conflicts = self.check_conflicts(workspace_path)
        if conflicts:
            return {
                "status": "FAILED",
                "files_integrated": [],
                "conflicts": conflicts,
                "commit_hash": "",
                "errors": ["Merge conflicts detected"]
            }
        
        # Prepare intents
        intents, errors = self.prepare_integration(job_id, workspace_path)
        if errors:
            return {
                "status": "FAILED",
                "files_integrated": [],
                "conflicts": [],
                "commit_hash": "",
                "errors": errors
            }
        
        if not intents:
            return {
                "status": "SUCCESS",
                "files_integrated": [],
                "conflicts": [],
                "commit_hash": "",
                "errors": ["No changes to integrate"]
            }
        
        # Execute three-phase protocol
        # Phase 1: Plan
        validated, errors = self.writer.phase1_plan(intents, ticket_id)
        if errors:
            return {
                "status": "FAILED",
                "files_integrated": [],
                "conflicts": [],
                "commit_hash": "",
                "errors": errors
            }
        
        # Phase 2: Validate
        valid, errors = self.writer.phase2_validate(validated, str(target))
        if not valid:
            return {
                "status": "FAILED",
                "files_integrated": [],
                "conflicts": [],
                "commit_hash": "",
                "errors": errors
            }
        
        # Phase 3: Apply
        success, results = self.writer.phase3_apply(
            validated, str(target), ticket_id, job_id, "integrator-agent"
        )
        
        if not success:
            return {
                "status": "FAILED",
                "files_integrated": [],
                "conflicts": [],
                "commit_hash": "",
                "errors": results
            }
        
        # Post-integration tasks
        integrated_files = [intent['path'] for intent in validated]
        
        # Register component dependencies
        self._register_component_dependencies(validated, ticket_id)
        
        # Update Knowledge Manager with API information
        self._update_knowledge_manager(validated, ticket_id)
        
        # Create commit if in git repository
        commit_hash = self._create_commit(integrated_files, ticket_id, job_id, target)
        
        # Log success
        self.logger.append_event(
            ticket_id=ticket_id,
            event_type="INTEGRATION_COMPLETE",
            payload={
                "job_id": job_id,
                "files": integrated_files,
                "commit": commit_hash
            },
            agent="integrator-agent"
        )
        
        return {
            "status": "SUCCESS",
            "files_integrated": integrated_files,
            "conflicts": [],
            "commit_hash": commit_hash,
            "errors": []
        }
    
    def _register_component_dependencies(self, intents: List[Dict], ticket_id: str):
        """Register component-level dependencies."""
        components = set()
        
        # Collect all components
        for intent in intents:
            if intent.get('component'):
                components.add(intent['component'])
        
        # Register dependencies between components
        for intent in intents:
            source_component = intent.get('component')
            if not source_component:
                continue
            
            dependencies = intent.get('dependencies', [])
            for dep_path in dependencies:
                target_component = self._infer_component(dep_path)
                if target_component and target_component != source_component:
                    self.registry.register_component_dependency(
                        source_component, target_component, 'imports', ticket_id
                    )
    
    def _update_knowledge_manager(self, intents: List[Dict], ticket_id: str):
        """Update Knowledge Manager with component APIs and decisions."""
        for intent in intents:
            if intent['operation'] in ['create', 'update']:
                component = intent.get('component')
                content = intent.get('content', '')
                
                # Extract API information for components
                if component and ('component' in intent['path'].lower() or 
                                 intent['path'].endswith(('.tsx', '.jsx'))):
                    api_info = self._extract_api_info(content, intent['path'])
                    if api_info:
                        self._register_api_with_km(component, api_info, ticket_id)
    
    def _extract_api_info(self, content: str, filepath: str) -> Dict:
        """Extract API information from component content."""
        api_info = {
            "file_path": filepath,
            "exports": [],
            "props": {},
            "methods": []
        }
        
        # Simple regex-based extraction (could be enhanced with AST parsing)
        import re
        
        # Find exported functions/classes
        export_patterns = [
            r'export\s+(?:default\s+)?(?:function|class)\s+(\w+)',
            r'export\s+const\s+(\w+)\s*=',
            r'export\s*{\s*([^}]+)\s*}'
        ]
        
        for pattern in export_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            for match in matches:
                if isinstance(match, str):
                    api_info["exports"].append(match.strip())
                else:
                    # Handle export lists
                    exports = [e.strip() for e in match.split(',')]
                    api_info["exports"].extend(exports)
        
        # Find interface/type definitions
        interface_pattern = r'interface\s+(\w+)\s*{([^}]+)}'
        interfaces = re.findall(interface_pattern, content, re.MULTILINE | re.DOTALL)
        
        for interface_name, interface_body in interfaces:
            api_info["props"][interface_name] = interface_body.strip()
        
        return api_info if api_info["exports"] else None
    
    def _register_api_with_km(self, component: str, api_info: Dict, ticket_id: str):
        """Register API information with Knowledge Manager."""
        try:
            requests.post(self.km_url, json={
                'tool_name': 'register_api',
                'tool_input': {
                    'component_name': component,
                    'api_definition': api_info,
                    'ticket_id': ticket_id
                }
            }, timeout=5)
        except:
            # KM might not be available, continue silently
            pass
    
    def _create_commit(self, files: List[str], ticket_id: str, job_id: str, target: Path) -> str:
        """Create git commit for integrated changes."""
        try:
            # Check if we're in a git repository
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=target,
                capture_output=True,
                check=True
            )
            
            # Stage changes
            for filepath in files:
                subprocess.run(
                    ["git", "add", filepath],
                    cwd=target,
                    capture_output=True
                )
            
            # Commit
            commit_message = f"Integrate {ticket_id}: {len(files)} files\n\nJob: {job_id}\nFiles:\n" + \
                           "\n".join(f"- {f}" for f in files[:10])  # Limit to first 10 files
            
            if len(files) > 10:
                commit_message += f"\n... and {len(files) - 10} more files"
            
            result = subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=target,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                # Get commit hash
                commit_hash = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=target,
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip()
                
                return commit_hash
        except subprocess.CalledProcessError:
            # Git operations failed
            pass
        
        return ""

if __name__ == "__main__":
    import sys
    integrator = Integrator()
    
    if len(sys.argv) < 4:
        print("Usage: integrator.py <ticket_id> <job_id> <workspace_path> [target_path]")
        sys.exit(1)
    
    result = integrator.integrate(
        sys.argv[1],  # ticket_id
        sys.argv[2],  # job_id
        sys.argv[3],  # workspace_path
        sys.argv[4] if len(sys.argv) > 4 else "."  # target_path
    )
    
    print(json.dumps(result, indent=2))