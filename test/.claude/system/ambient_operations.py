#!/usr/bin/env python3
"""
Ambient Operations Framework - The Magic of Autonomous Intelligence

This module implements the final piece of the breakthrough insight: enabling three
operational modes simultaneously - Explicit, Implicit, and Ambient.

This is where automation becomes autonomy.
"""

import os
import json
import time
import asyncio
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Tuple
from dataclasses import dataclass
from logger_config import get_contextual_logger
from event_logger import EventLogger
from claude_bridge import ClaudeBridge

@dataclass
class AmbientRule:
    """Definition of an ambient operation rule"""
    name: str
    condition: Callable[[], bool]
    action: str
    agent: str
    silent: bool = True
    cooldown_minutes: int = 60
    priority: str = "normal"
    description: str = ""

class AmbientOperations:
    """
    Operations that happen without explicit requests - the autonomous intelligence layer.
    
    This system enables:
    1. Explicit Mode - User asks, agents respond
    2. Implicit Mode - User acts, agents infer needs  
    3. Ambient Mode - System self-monitors and self-heals
    
    The magic happens when all three modes work simultaneously.
    """
    
    def __init__(self):
        self.logger = get_contextual_logger("ambient_ops", component="autonomous_intelligence")
        self.event_logger = EventLogger()
        self.claude_bridge = ClaudeBridge()
        
        self.base_path = Path(".claude")
        self.state_path = self.base_path / "state"
        self.ambient_path = self.base_path / "ambient"
        self.triggers_path = self.base_path / "triggers"
        
        # Ensure directories exist
        for path in [self.state_path, self.ambient_path, self.triggers_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Track last execution times for cooldown
        self.last_execution = {}
        
        # System state
        self.system_state = {
            "last_backup": 0,
            "last_health_check": 0,
            "last_performance_check": 0,
            "last_security_scan": 0,
            "deployment_count": 0,
            "error_count_last_hour": 0,
            "performance_degradation_count": 0
        }
        
        # Load system state
        self.load_system_state()
        
        # Initialize ambient rules
        self.ambient_rules = self.initialize_ambient_rules()
        
        self.running = False
    
    def load_system_state(self):
        """Load system state from disk"""
        state_file = self.state_path / "ambient_system_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    saved_state = json.load(f)
                    self.system_state.update(saved_state)
            except Exception as e:
                self.logger.error("Failed to load system state", extra={"error": str(e)})
    
    def save_system_state(self):
        """Save system state to disk"""
        state_file = self.state_path / "ambient_system_state.json"
        try:
            self.system_state["last_updated"] = time.time()
            with open(state_file, 'w') as f:
                json.dump(self.system_state, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save system state", extra={"error": str(e)})
    
    def initialize_ambient_rules(self) -> List[AmbientRule]:
        """Initialize all ambient operation rules"""
        rules = []
        
        # Database backup rule
        rules.append(AmbientRule(
            name="database_backup",
            condition=lambda: self.time_since_last_backup() > 86400,  # 24 hours
            action="create_database_backup",
            agent="data-migration-agent",
            silent=True,
            cooldown_minutes=1440,  # 24 hours
            priority="high",
            description="Automatic daily database backup"
        ))
        
        # System health monitoring
        rules.append(AmbientRule(
            name="health_check", 
            condition=lambda: self.time_since_last_health_check() > 3600,  # 1 hour
            action="perform_health_check",
            agent="monitoring-agent",
            silent=True,
            cooldown_minutes=60,
            priority="normal",
            description="Hourly system health verification"
        ))
        
        # Performance degradation detection
        rules.append(AmbientRule(
            name="performance_monitoring",
            condition=lambda: self.detect_performance_issues(),
            action="analyze_performance_degradation",
            agent="performance-optimizer-agent",
            silent=False,  # Notify user of performance issues
            cooldown_minutes=30,
            priority="high",
            description="Detect and analyze performance degradation"
        ))
        
        # Error rate monitoring
        rules.append(AmbientRule(
            name="error_rate_monitoring",
            condition=lambda: self.error_rate_exceeded(),
            action="investigate_error_spike",
            agent="incident-response-agent",
            silent=False,  # Critical alerts should notify
            cooldown_minutes=15,
            priority="critical",
            description="Monitor and respond to error rate spikes"
        ))
        
        # Documentation drift detection
        rules.append(AmbientRule(
            name="documentation_drift",
            condition=lambda: self.documentation_outdated(),
            action="update_documentation",
            agent="documentation-agent",
            silent=True,
            cooldown_minutes=480,  # 8 hours
            priority="low",
            description="Detect and update outdated documentation"
        ))
        
        # Security scan
        rules.append(AmbientRule(
            name="security_scan",
            condition=lambda: self.time_since_security_scan() > 604800,  # 1 week
            action="perform_security_scan",
            agent="contract-guardian",
            silent=True,
            cooldown_minutes=10080,  # 1 week
            priority="medium",
            description="Weekly security vulnerability scan"
        ))
        
        # Monitoring gap detection
        rules.append(AmbientRule(
            name="monitoring_gaps",
            condition=lambda: self.unmonitored_services_detected(),
            action="setup_missing_monitoring",
            agent="monitoring-agent",
            silent=False,
            cooldown_minutes=240,  # 4 hours
            priority="medium",
            description="Detect and setup monitoring for unmonitored services"
        ))
        
        # Performance baseline updates
        rules.append(AmbientRule(
            name="performance_baselines",
            condition=lambda: self.performance_baselines_outdated(),
            action="update_performance_baselines",
            agent="performance-optimizer-agent",
            silent=True,
            cooldown_minutes=720,  # 12 hours
            priority="low", 
            description="Update performance baselines after deployments"
        ))
        
        return rules
    
    async def start_ambient_operations(self):
        """Start the ambient operations monitoring loop"""
        self.running = True
        self.logger.info("Starting ambient operations framework")
        
        # Start the main ambient loop
        await asyncio.create_task(self.ambient_monitoring_loop())
    
    def stop_ambient_operations(self):
        """Stop ambient operations"""
        self.running = False
        self.logger.info("Stopping ambient operations framework")
    
    async def ambient_monitoring_loop(self):
        """Main ambient monitoring loop - the heart of autonomous intelligence"""
        while self.running:
            try:
                # Check all ambient rules
                for rule in self.ambient_rules:
                    await self.check_ambient_rule(rule)
                
                # Update system metrics
                self.update_system_metrics()
                
                # Save state periodically
                self.save_system_state()
                
                # Sleep for 60 seconds between checks
                await asyncio.sleep(60)
                
            except Exception as e:
                self.logger.error("Error in ambient monitoring loop", extra={"error": str(e)})
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def check_ambient_rule(self, rule: AmbientRule):
        """Check if an ambient rule should be triggered"""
        
        # Check cooldown
        last_run = self.last_execution.get(rule.name, 0)
        cooldown_seconds = rule.cooldown_minutes * 60
        
        if time.time() - last_run < cooldown_seconds:
            return  # Still in cooldown
        
        try:
            # Check condition
            if rule.condition():
                self.logger.info("Ambient rule triggered", extra={
                    "rule": rule.name,
                    "agent": rule.agent,
                    "silent": rule.silent,
                    "priority": rule.priority
                })
                
                # Create ambient trigger
                await self.trigger_ambient_operation(rule)
                
                # Update last execution time
                self.last_execution[rule.name] = time.time()
                
        except Exception as e:
            self.logger.error("Error checking ambient rule", extra={
                "rule": rule.name,
                "error": str(e)
            })
    
    async def trigger_ambient_operation(self, rule: AmbientRule):
        """Trigger an ambient operation"""
        
        # Create ambient event
        ambient_event = {
            "type": "AMBIENT_OPERATION_TRIGGERED",
            "rule": rule.name,
            "agent": rule.agent,
            "action": rule.action,
            "priority": rule.priority,
            "silent": rule.silent,
            "description": rule.description,
            "triggered_at": time.time()
        }
        
        # Log the ambient event
        event_id = self.event_logger.append_event(
            ticket_id=f"ambient_{rule.name}_{int(time.time())}",
            event_type="AMBIENT_OPERATION",
            payload=ambient_event
        )
        
        # Create trigger file for the agent
        trigger_file = self.triggers_path / f"{rule.agent}_ambient_{int(time.time())}.json"
        
        trigger_data = {
            "agent": rule.agent,
            "trigger_event": ambient_event,
            "context": {
                "ambient_rule": rule.name,
                "action_required": rule.action,
                "system_state": self.system_state,
                "automation_level": "ambient"
            },
            "created_at": datetime.now().isoformat(),
            "priority": rule.priority,
            "automation_level": "ambient",
            "silent": rule.silent
        }
        
        try:
            with open(trigger_file, 'w') as f:
                json.dump(trigger_data, f, indent=2)
            
            # If not silent, create user notification
            if not rule.silent:
                await self.create_user_notification(rule, ambient_event)
            
            self.logger.info("Ambient operation triggered", extra={
                "rule": rule.name,
                "agent": rule.agent,
                "trigger_file": str(trigger_file),
                "silent": rule.silent
            })
            
        except Exception as e:
            self.logger.error("Failed to create ambient trigger", extra={
                "rule": rule.name,
                "agent": rule.agent,
                "error": str(e)
            })
    
    async def create_user_notification(self, rule: AmbientRule, event: Dict):
        """Create user notification for non-silent ambient operations"""
        
        # Use Claude Bridge to translate the event
        translated = self.claude_bridge.translate_ambient_event({
            "type": event["type"],
            "payload": event
        })
        
        if translated:
            notification = {
                "type": "AMBIENT_NOTIFICATION",
                "rule": rule.name,
                "message": translated["message"],
                "priority": rule.priority,
                "timestamp": time.time(),
                "requires_attention": rule.priority in ["critical", "high"]
            }
            
            # Save notification for Claude to see
            notification_file = self.ambient_path / "pending_notifications.json"
            
            notifications = []
            if notification_file.exists():
                try:
                    with open(notification_file, 'r') as f:
                        notifications = json.load(f)
                except:
                    notifications = []
            
            notifications.append(notification)
            
            # Keep only recent notifications (last 24 hours)
            cutoff = time.time() - 86400
            notifications = [n for n in notifications if n.get("timestamp", 0) > cutoff]
            
            with open(notification_file, 'w') as f:
                json.dump(notifications, f, indent=2)
    
    def update_system_metrics(self):
        """Update system metrics for ambient rule conditions"""
        current_time = time.time()
        
        # Update error count (last hour)
        try:
            error_count = self.count_recent_errors()
            self.system_state["error_count_last_hour"] = error_count
        except:
            pass
        
        # Update performance metrics
        try:
            perf_issues = self.count_performance_issues()
            self.system_state["performance_degradation_count"] = perf_issues
        except:
            pass
        
        # Update deployment count
        try:
            deployment_count = self.count_recent_deployments()
            self.system_state["deployment_count"] = deployment_count
        except:
            pass
    
    # Condition methods for ambient rules
    def time_since_last_backup(self) -> int:
        """Time since last database backup in seconds"""
        return int(time.time() - self.system_state.get("last_backup", 0))
    
    def time_since_last_health_check(self) -> int:
        """Time since last health check in seconds"""
        return int(time.time() - self.system_state.get("last_health_check", 0))
    
    def time_since_security_scan(self) -> int:
        """Time since last security scan in seconds"""
        return int(time.time() - self.system_state.get("last_security_scan", 0))
    
    def detect_performance_issues(self) -> bool:
        """Detect if there are current performance issues"""
        # Check for recent performance degradation events
        events_file = self.base_path / "events" / "log.ndjson"
        if not events_file.exists():
            return False
        
        try:
            # Look for performance events in last hour
            cutoff = time.time() - 3600
            performance_events = 0
            
            with open(events_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if (event.get("timestamp", 0) > cutoff and 
                            "PERFORMANCE" in event.get("type", "")):
                            performance_events += 1
                    except:
                        continue
            
            return performance_events > 2  # More than 2 performance events in last hour
            
        except:
            return False
    
    def error_rate_exceeded(self) -> bool:
        """Check if error rate has exceeded threshold"""
        return self.system_state.get("error_count_last_hour", 0) > 10
    
    def documentation_outdated(self) -> bool:
        """Check if documentation is outdated"""
        # Simple heuristic: check if there have been commits without doc updates
        try:
            # Check for recent code changes without documentation updates
            events_file = self.base_path / "events" / "log.ndjson"
            if not events_file.exists():
                return False
            
            cutoff = time.time() - 86400  # Last 24 hours
            code_commits = 0
            doc_updates = 0
            
            with open(events_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line.strip())
                        if event.get("timestamp", 0) > cutoff:
                            event_type = event.get("type", "")
                            if "COMMIT" in event_type:
                                code_commits += 1
                            elif "DOCUMENTATION" in event_type:
                                doc_updates += 1
                    except:
                        continue
            
            # Documentation outdated if more than 5 commits without doc updates
            return code_commits > 5 and doc_updates == 0
            
        except:
            return False
    
    def unmonitored_services_detected(self) -> bool:
        """Check if there are unmonitored services"""
        # This would integrate with actual service discovery
        # For now, return False as placeholder
        return False
    
    def performance_baselines_outdated(self) -> bool:
        """Check if performance baselines need updating"""
        # Check if there have been deployments without baseline updates
        deployment_count = self.system_state.get("deployment_count", 0)
        last_baseline = self.system_state.get("last_performance_baseline", 0)
        
        # Update baselines if more than 3 deployments since last baseline
        return deployment_count > 3 and time.time() - last_baseline > 43200  # 12 hours
    
    def count_recent_errors(self) -> int:
        """Count errors in the last hour"""
        # This would integrate with actual error tracking
        # For now, return a placeholder
        return 0
    
    def count_performance_issues(self) -> int:
        """Count recent performance issues"""
        # This would integrate with actual performance monitoring
        # For now, return a placeholder
        return 0
    
    def count_recent_deployments(self) -> int:
        """Count recent deployments"""
        # This would integrate with actual deployment tracking
        # For now, return a placeholder
        return self.system_state.get("deployment_count", 0)
    
    def get_ambient_status(self) -> Dict:
        """Get current ambient operations status"""
        return {
            "running": self.running,
            "active_rules": len(self.ambient_rules),
            "last_execution_times": self.last_execution,
            "system_state": self.system_state,
            "rules": [
                {
                    "name": rule.name,
                    "agent": rule.agent,
                    "description": rule.description,
                    "priority": rule.priority,
                    "last_run": self.last_execution.get(rule.name, 0),
                    "cooldown_remaining": max(0, (rule.cooldown_minutes * 60) - (time.time() - self.last_execution.get(rule.name, 0)))
                }
                for rule in self.ambient_rules
            ]
        }
    
    def get_pending_notifications(self) -> List[Dict]:
        """Get pending user notifications from ambient operations"""
        notification_file = self.ambient_path / "pending_notifications.json"
        
        if not notification_file.exists():
            return []
        
        try:
            with open(notification_file, 'r') as f:
                notifications = json.load(f)
            
            # Return only unread notifications
            return [n for n in notifications if not n.get("read", False)]
            
        except:
            return []
    
    def mark_notifications_read(self):
        """Mark all pending notifications as read"""
        notification_file = self.ambient_path / "pending_notifications.json"
        
        if not notification_file.exists():
            return
        
        try:
            with open(notification_file, 'r') as f:
                notifications = json.load(f)
            
            # Mark all as read
            for notification in notifications:
                notification["read"] = True
                notification["read_at"] = time.time()
            
            with open(notification_file, 'w') as f:
                json.dump(notifications, f, indent=2)
                
        except Exception as e:
            self.logger.error("Failed to mark notifications as read", extra={"error": str(e)})


async def main():
    """Main entry point for ambient operations"""
    ambient_ops = AmbientOperations()
    
    try:
        print("Starting ambient operations framework...")
        await ambient_ops.start_ambient_operations()
        
    except KeyboardInterrupt:
        print("\nStopping ambient operations...")
        ambient_ops.stop_ambient_operations()
        print("Ambient operations stopped.")


if __name__ == "__main__":
    asyncio.run(main())