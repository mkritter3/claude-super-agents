#!/usr/bin/env python3
"""
Event Watchers - Continuous monitoring for autonomous operations

This module implements the breakthrough insight: using the file system as a message bus
and hooks as daemon substitutes to enable truly autonomous operational agents.
"""

import os
import json
import time
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from event_logger import EventLogger
from logger_config import get_contextual_logger

class AmbientEventWatcher:
    """
    Continuously monitors for operational triggers and enables ambient operations.
    
    This is the core component that makes operational agents truly autonomous by:
    1. Monitoring .claude/events/log.ndjson for new events
    2. Watching .claude/triggers/ for pending operations
    3. Maintaining .claude/state/ with operational context
    4. Automatically triggering appropriate agents
    """
    
    TRIGGER_RULES = {
        "CODE_MERGED": ["monitoring-agent", "documentation-agent", "test-executor"],
        "CODE_COMMITTED": ["monitoring-agent", "documentation-agent", "test-executor"],
        "SCHEMA_CHANGED": ["data-migration-agent", "database-agent", "contract-guardian"],
        "API_CONTRACT_CHANGED": ["contract-guardian", "monitoring-agent", "documentation-agent"],
        "CONTRACT_CHANGES_DETECTED": ["contract-guardian"],
        "CODE_CHANGES_NEED_TESTING": ["test-executor"],
        "TEST_FAILED": ["incident-response-agent"],
        "TEST_SUITE_PASSED": ["documentation-agent"],
        "PERFORMANCE_DEGRADED": ["performance-optimizer-agent"],
        "DEPLOYMENT_STARTED": ["monitoring-agent", "test-executor"],
        "DEPLOYMENT_COMPLETE": ["monitoring-agent", "documentation-agent", "performance-optimizer-agent", "test-executor"],
        "ERROR_THRESHOLD_EXCEEDED": ["incident-response-agent"],
        "FILE_CHANGED": ["performance-optimizer-agent"],
        "SCHEMA_MIGRATION_NEEDED": ["data-migration-agent", "contract-guardian"],
        "INCIDENT_DETECTED": ["incident-response-agent"],
        "PERFORMANCE_BASELINE_NEEDED": ["performance-optimizer-agent"],
        "BREAKING_CHANGE_DETECTED": ["contract-guardian", "incident-response-agent"],
        "SECURITY_VULNERABILITY_FOUND": ["contract-guardian", "incident-response-agent"],
        
        # New full-stack triggers
        "FRONTEND_CHANGED": ["frontend-agent", "ux-agent"],
        "UX_VALIDATION_REQUIRED": ["ux-agent"],
        "FRONTEND_REVIEW_REQUIRED": ["frontend-agent"],
        "DATABASE_DESIGN_REVIEW": ["database-agent", "data-migration-agent"],
        "INFRASTRUCTURE_CHANGED": ["devops-agent", "security-agent"],
        "INFRASTRUCTURE_REVIEW": ["devops-agent"],
        "SECURITY_AUDIT_REQUIRED": ["security-agent"],
        "SECURITY_SENSITIVE_CHANGED": ["security-agent"],
        "PRODUCT_REQUIREMENTS_CHANGED": ["product-agent", "ux-agent"],
        
        # Coordinated full-stack workflows
        "FULL_STACK_FEATURE": ["product-agent", "architect-agent", "frontend-agent", "developer-agent"],
        "DEPLOYMENT_PIPELINE": ["devops-agent", "security-agent", "monitoring-agent"],
        "DATABASE_MIGRATION": ["database-agent", "data-migration-agent", "contract-guardian"],
        "UI_COMPONENT_CHANGES": ["frontend-agent", "ux-agent", "test-executor"],
        "SECURITY_COMPLIANCE_CHECK": ["security-agent", "contract-guardian"],
        "PRODUCT_FEATURE_REQUEST": ["product-agent", "ux-agent", "architect-agent"]
    }
    
    def __init__(self):
        self.event_logger = EventLogger()
        self.logger = get_contextual_logger("event_watcher", component="ambient_operations")
        self.running = False
        self.observers = []
        self.trigger_callbacks = {}
        
        # Create directories
        self.base_path = Path(".claude")
        self.triggers_path = self.base_path / "triggers"
        self.state_path = self.base_path / "state"
        self.ambient_path = self.base_path / "ambient"
        
        for path in [self.triggers_path, self.state_path, self.ambient_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Initialize state tracking
        self.operational_state = {
            "last_deployment": None,
            "monitoring_state": {},
            "performance_baselines": {},
            "incident_count": 0,
            "automation_level": "full"  # full, partial, manual
        }
        
        self.load_operational_state()
    
    def load_operational_state(self):
        """Load operational state from disk"""
        state_file = self.state_path / "operational_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    saved_state = json.load(f)
                    self.operational_state.update(saved_state)
                self.logger.info("Loaded operational state", extra={"state": self.operational_state})
            except Exception as e:
                self.logger.error("Failed to load operational state", extra={"error": str(e)})
    
    def save_operational_state(self):
        """Save operational state to disk"""
        state_file = self.state_path / "operational_state.json"
        try:
            with open(state_file, 'w') as f:
                json.dump(self.operational_state, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save operational state", extra={"error": str(e)})
    
    def start_watching(self):
        """Start all event watchers"""
        self.running = True
        
        self.logger.info("Starting ambient event watchers")
        
        # Start event log watcher
        event_thread = threading.Thread(target=self.watch_event_log, daemon=True)
        event_thread.start()
        
        # Start trigger file watcher
        trigger_observer = Observer()
        trigger_handler = TriggerFileHandler(self)
        trigger_observer.schedule(trigger_handler, str(self.triggers_path), recursive=True)
        trigger_observer.start()
        self.observers.append(trigger_observer)
        
        # Start file system watcher for project files
        project_observer = Observer()
        project_handler = ProjectFileHandler(self)
        project_observer.schedule(project_handler, ".", recursive=True)
        project_observer.start()
        self.observers.append(project_observer)
        
        # Start ambient rules checker
        ambient_thread = threading.Thread(target=self.run_ambient_checks, daemon=True)
        ambient_thread.start()
        
        self.logger.info("All event watchers started")
    
    def stop_watching(self):
        """Stop all event watchers"""
        self.running = False
        
        for observer in self.observers:
            observer.stop()
            observer.join()
        
        self.logger.info("Event watchers stopped")
    
    def watch_event_log(self):
        """Monitor .claude/events/log.ndjson for new events"""
        event_log_path = self.base_path / "events" / "log.ndjson"
        
        # Get initial file size
        last_size = event_log_path.stat().st_size if event_log_path.exists() else 0
        
        while self.running:
            try:
                if event_log_path.exists():
                    current_size = event_log_path.stat().st_size
                    
                    if current_size > last_size:
                        # New events detected
                        with open(event_log_path, 'r') as f:
                            f.seek(last_size)
                            new_lines = f.readlines()
                        
                        for line in new_lines:
                            if line.strip():
                                try:
                                    event = json.loads(line.strip())
                                    self.process_event(event)
                                except json.JSONDecodeError:
                                    continue
                        
                        last_size = current_size
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error("Error watching event log", extra={"error": str(e)})
                time.sleep(5)  # Wait longer on error
    
    def process_event(self, event: Dict):
        """Process a new event and trigger appropriate agents"""
        event_type = event.get("type", "")
        
        # Check for trigger rules
        if event_type in self.TRIGGER_RULES:
            agents_to_trigger = self.TRIGGER_RULES[event_type]
            
            self.logger.info("Event triggered agents", extra={
                "event_type": event_type,
                "agents": agents_to_trigger,
                "event_id": event.get("event_id")
            })
            
            # Create trigger files for each agent
            for agent in agents_to_trigger:
                self.create_agent_trigger(agent, event)
        
        # Update operational state based on event
        self.update_operational_state(event)
    
    def create_agent_trigger(self, agent_name: str, trigger_event: Dict):
        """Create trigger file for specific agent"""
        trigger_file = self.triggers_path / f"{agent_name}_trigger_{int(time.time())}.json"
        
        trigger_data = {
            "agent": agent_name,
            "trigger_event": trigger_event,
            "context": self.get_agent_context(agent_name, trigger_event),
            "created_at": datetime.now().isoformat(),
            "priority": self.calculate_priority(trigger_event),
            "automation_level": self.operational_state["automation_level"]
        }
        
        try:
            with open(trigger_file, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            self.logger.info("Created agent trigger", extra={
                "agent": agent_name,
                "trigger_file": str(trigger_file),
                "priority": trigger_data["priority"]
            })
            
        except Exception as e:
            self.logger.error("Failed to create agent trigger", extra={
                "agent": agent_name,
                "error": str(e)
            })
    
    def get_agent_context(self, agent_name: str, trigger_event: Dict) -> Dict:
        """Get relevant context for specific agent"""
        base_context = {
            "operational_state": self.operational_state,
            "trigger_event": trigger_event,
            "agent": agent_name
        }
        
        # Agent-specific context
        if agent_name == "monitoring-agent":
            base_context.update({
                "deployment_info": self.operational_state.get("last_deployment"),
                "existing_monitors": self.operational_state.get("monitoring_state", {})
            })
        
        elif agent_name == "performance-optimizer-agent":
            base_context.update({
                "current_baselines": self.operational_state.get("performance_baselines", {}),
                "performance_issues": self.get_recent_performance_issues()
            })
        
        elif agent_name == "incident-response-agent":
            base_context.update({
                "incident_history": self.get_recent_incidents(),
                "system_health": self.get_current_system_health()
            })
        
        elif agent_name == "documentation-agent":
            base_context.update({
                "recent_changes": self.get_recent_code_changes(),
                "documentation_gaps": self.identify_documentation_gaps()
            })
        
        return base_context
    
    def calculate_priority(self, trigger_event: Dict) -> str:
        """Calculate priority for triggered operation"""
        event_type = trigger_event.get("type", "")
        
        # High priority events
        if event_type in ["ERROR_THRESHOLD_EXCEEDED", "INCIDENT_DETECTED", "TEST_FAILED"]:
            return "critical"
        
        # Medium priority events  
        if event_type in ["PERFORMANCE_DEGRADED", "SCHEMA_CHANGED"]:
            return "high"
        
        # Normal priority events
        if event_type in ["DEPLOYMENT_COMPLETE", "CODE_MERGED"]:
            return "medium"
        
        return "low"
    
    def run_ambient_checks(self):
        """Run continuous ambient operation checks"""
        while self.running:
            try:
                # Check for ambient conditions that should trigger operations
                self.check_ambient_rules()
                
                # Update operational health
                self.update_system_health()
                
                # Cleanup old trigger files
                self.cleanup_old_triggers()
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error("Error in ambient checks", extra={"error": str(e)})
                time.sleep(60)  # Wait longer on error
    
    def check_ambient_rules(self):
        """Check ambient rules that should trigger operations without explicit events"""
        
        # Rule: Check for performance degradation
        if self.detect_performance_degradation():
            self.create_ambient_trigger("performance-optimizer-agent", {
                "type": "PERFORMANCE_DEGRADED",
                "detected_by": "ambient_watcher",
                "metrics": self.get_current_performance_metrics()
            })
        
        # Rule: Check for missing documentation
        if self.detect_documentation_drift():
            self.create_ambient_trigger("documentation-agent", {
                "type": "DOCUMENTATION_DRIFT_DETECTED",
                "detected_by": "ambient_watcher", 
                "changes_since_last_update": self.count_changes_since_last_doc_update()
            })
        
        # Rule: Check for monitoring gaps
        if self.detect_monitoring_gaps():
            self.create_ambient_trigger("monitoring-agent", {
                "type": "MONITORING_GAP_DETECTED",
                "detected_by": "ambient_watcher",
                "unmonitored_services": self.get_unmonitored_services()
            })
    
    def create_ambient_trigger(self, agent_name: str, ambient_event: Dict):
        """Create trigger for ambient (automatic) operation"""
        # Add ambient marker
        ambient_event["ambient"] = True
        ambient_event["silent"] = ambient_event.get("silent", True)
        
        self.create_agent_trigger(agent_name, ambient_event)
        
        self.logger.info("Created ambient trigger", extra={
            "agent": agent_name,
            "event_type": ambient_event.get("type"),
            "silent": ambient_event.get("silent")
        })
    
    def update_operational_state(self, event: Dict):
        """Update operational state based on processed event"""
        event_type = event.get("type", "")
        
        if event_type == "DEPLOYMENT_COMPLETE":
            self.operational_state["last_deployment"] = {
                "timestamp": event.get("timestamp"),
                "service": event.get("payload", {}).get("service"),
                "version": event.get("payload", {}).get("version")
            }
        
        elif event_type == "MONITORING_CONFIGURED":
            self.operational_state["monitoring_state"] = event.get("payload", {})
        
        elif event_type == "PERFORMANCE_BASELINE_ESTABLISHED":
            service = event.get("payload", {}).get("service", "default")
            self.operational_state.setdefault("performance_baselines", {})[service] = event.get("payload", {})
        
        elif event_type == "INCIDENT_DETECTED":
            self.operational_state["incident_count"] = self.operational_state.get("incident_count", 0) + 1
        
        self.save_operational_state()
    
    def cleanup_old_triggers(self):
        """Clean up old trigger files"""
        cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
        
        for trigger_file in self.triggers_path.glob("*_trigger_*.json"):
            try:
                # Extract timestamp from filename
                parts = trigger_file.stem.split("_")
                if len(parts) >= 3:
                    timestamp = int(parts[-1])
                    if timestamp < cutoff_time:
                        trigger_file.unlink()
                        self.logger.debug("Cleaned up old trigger", extra={"file": str(trigger_file)})
            except (ValueError, OSError):
                continue
    
    # Placeholder methods for specific detection logic
    def detect_performance_degradation(self) -> bool:
        """Detect if performance has degraded"""
        # TODO: Implement actual performance monitoring
        return False
    
    def detect_documentation_drift(self) -> bool:
        """Detect if documentation is out of date"""
        # TODO: Implement documentation drift detection
        return False
    
    def detect_monitoring_gaps(self) -> bool:
        """Detect if there are monitoring gaps"""
        # TODO: Implement monitoring gap detection
        return False
    
    def get_recent_performance_issues(self) -> List[Dict]:
        """Get recent performance issues"""
        # TODO: Implement performance issue tracking
        return []
    
    def get_recent_incidents(self) -> List[Dict]:
        """Get recent incidents"""
        # TODO: Implement incident tracking
        return []
    
    def get_current_system_health(self) -> Dict:
        """Get current system health status"""
        # TODO: Implement system health checking
        return {"status": "healthy"}
    
    def get_recent_code_changes(self) -> List[Dict]:
        """Get recent code changes"""
        # TODO: Implement code change tracking
        return []
    
    def identify_documentation_gaps(self) -> List[str]:
        """Identify documentation gaps"""
        # TODO: Implement documentation gap analysis
        return []
    
    def get_current_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        # TODO: Implement performance metric collection
        return {}
    
    def count_changes_since_last_doc_update(self) -> int:
        """Count changes since last documentation update"""
        # TODO: Implement change counting
        return 0
    
    def get_unmonitored_services(self) -> List[str]:
        """Get list of unmonitored services"""
        # TODO: Implement service monitoring detection
        return []
    
    def update_system_health(self):
        """Update system health metrics"""
        # TODO: Implement system health updating
        pass


class TriggerFileHandler(FileSystemEventHandler):
    """Handle trigger file events"""
    
    def __init__(self, watcher: AmbientEventWatcher):
        self.watcher = watcher
        self.logger = get_contextual_logger("trigger_handler", component="ambient_operations")
    
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.logger.info("Trigger file created", extra={"file": event.src_path})
            # Trigger files are processed by the orchestrator
    
    def on_deleted(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self.logger.debug("Trigger file processed", extra={"file": event.src_path})


class ProjectFileHandler(FileSystemEventHandler):
    """Handle project file changes for ambient operations"""
    
    def __init__(self, watcher: AmbientEventWatcher):
        self.watcher = watcher
        self.logger = get_contextual_logger("project_handler", component="ambient_operations")
        
        # Ignore these directories/files
        self.ignored_patterns = {
            '.git', '.claude', 'node_modules', '__pycache__', '.pytest_cache',
            'target', 'build', 'dist', '.next', '.nuxt'
        }
    
    def should_ignore(self, path: str) -> bool:
        """Check if file should be ignored"""
        path_parts = Path(path).parts
        return any(ignored in path_parts for ignored in self.ignored_patterns)
    
    def on_modified(self, event):
        if event.is_directory or self.should_ignore(event.src_path):
            return
        
        file_path = Path(event.src_path)
        
        # Detect schema changes
        if file_path.suffix in ['.sql', '.migration', '.schema']:
            self.watcher.create_ambient_trigger("data-migration-agent", {
                "type": "SCHEMA_CHANGED",
                "file": str(file_path),
                "detected_by": "file_watcher"
            })
        
        # Detect configuration changes
        elif file_path.name in ['package.json', 'requirements.txt', 'Cargo.toml', 'go.mod']:
            self.watcher.create_ambient_trigger("dependency-agent", {
                "type": "DEPENDENCIES_CHANGED", 
                "file": str(file_path),
                "detected_by": "file_watcher"
            })
        
        # Detect code changes that might need documentation
        elif file_path.suffix in ['.py', '.js', '.ts', '.go', '.rs', '.java']:
            # Don't trigger on every code change, but track them
            self.watcher.operational_state.setdefault("recent_changes", []).append({
                "file": str(file_path),
                "timestamp": time.time()
            })
            
            # Keep only recent changes (last hour)
            cutoff = time.time() - 3600
            self.watcher.operational_state["recent_changes"] = [
                change for change in self.watcher.operational_state.get("recent_changes", [])
                if change["timestamp"] > cutoff
            ]


def main():
    """Main entry point for event watchers"""
    watcher = AmbientEventWatcher()
    
    try:
        watcher.start_watching()
        print("Event watchers started. Press Ctrl+C to stop.")
        
        # Keep running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping event watchers...")
        watcher.stop_watching()
        print("Event watchers stopped.")


if __name__ == "__main__":
    main()