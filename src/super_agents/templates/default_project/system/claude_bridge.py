#!/usr/bin/env python3
"""
Claude Bridge - Natural Language Control Plane

This module implements the breakthrough insight: using natural language as the control plane
to make operational events understandable and actionable for Claude Code.

The bridge translates technical events into contextual prompts that Claude can act upon,
enabling truly conversational automation.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from logger_config import get_contextual_logger

class ClaudeBridge:
    """
    Translates operational events into Claude-understandable prompts and context.
    
    This is the critical component that enables natural language as the control plane:
    1. Converts technical events into conversational context
    2. Maintains operational awareness across conversations
    3. Provides ambient intelligence without overwhelming the user
    4. Enables Claude to be proactively helpful
    """
    
    def __init__(self):
        self.logger = get_contextual_logger("claude_bridge", component="natural_language_control")
        self.base_path = Path(".claude")
        self.state_path = self.base_path / "state"
        self.ambient_path = self.base_path / "ambient"
        
        # Ensure directories exist
        for path in [self.state_path, self.ambient_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        # Context templates for different event types
        self.event_templates = {
            # Deployment-related events
            "DEPLOYMENT_STARTED": {
                "template": "I've detected that a deployment has started for {service}. Let me automatically set up monitoring and prepare for post-deployment verification.",
                "silent": True,
                "actions": ["setup_monitoring", "prepare_verification"]
            },
            "DEPLOYMENT_COMPLETE": {
                "template": "Deployment of {service} is complete. I'm automatically setting up monitoring dashboards, updating documentation, and establishing performance baselines.",
                "silent": False,
                "actions": ["monitoring_setup", "documentation_update", "performance_baseline"]
            },
            
            # Performance-related events
            "PERFORMANCE_DEGRADED": {
                "template": "⚠️ Performance degradation detected in {service}. I'm analyzing the issue and will provide optimization recommendations.",
                "silent": False,
                "priority": "high",
                "actions": ["analyze_performance", "suggest_optimizations"]
            },
            "PERFORMANCE_BASELINE_NEEDED": {
                "template": "I'm establishing performance baselines for {service} to enable proactive monitoring and regression detection.",
                "silent": True,
                "actions": ["establish_baseline"]
            },
            
            # Incident-related events
            "INCIDENT_DETECTED": {
                "template": "🚨 INCIDENT: {error_type} affecting {service}. I'm investigating the root cause and preparing mitigation options.",
                "silent": False,
                "priority": "critical",
                "actions": ["investigate_incident", "prepare_mitigation", "gather_logs"]
            },
            "ERROR_THRESHOLD_EXCEEDED": {
                "template": "Error rate spike detected ({error_rate}% in {service}). I'm correlating with recent deployments and analyzing logs.",
                "silent": False,
                "priority": "high",
                "actions": ["correlate_with_deployments", "analyze_error_logs"]
            },
            
            # Code and schema changes
            "SCHEMA_CHANGED": {
                "template": "Database schema change detected in {file}. I'm validating the change and preparing migration scripts if needed.",
                "silent": True,
                "actions": ["validate_schema_change", "prepare_migration"]
            },
            "CODE_MERGED": {
                "template": "Code has been merged. I'm automatically updating documentation and ensuring monitoring coverage for any new endpoints.",
                "silent": True,
                "actions": ["update_documentation", "verify_monitoring"]
            },
            
            # Monitoring and observability
            "MONITORING_GAP_DETECTED": {
                "template": "I've identified services without proper monitoring: {unmonitored_services}. Let me set up comprehensive observability.",
                "silent": False,
                "actions": ["setup_comprehensive_monitoring"]
            },
            "DOCUMENTATION_DRIFT_DETECTED": {
                "template": "Documentation appears outdated ({changes_since_last_update} changes since last update). I'll refresh the relevant documentation.",
                "silent": True,
                "actions": ["refresh_documentation"]
            }
        }
        
        # Current operational context
        self.operational_context = {
            "active_incidents": [],
            "recent_deployments": [],
            "performance_issues": [],
            "pending_operations": [],
            "automation_level": "full"
        }
        
        self.load_operational_context()
    
    def load_operational_context(self):
        """Load operational context from disk"""
        context_file = self.state_path / "claude_context.json"
        if context_file.exists():
            try:
                with open(context_file, 'r') as f:
                    saved_context = json.load(f)
                    self.operational_context.update(saved_context)
            except Exception as e:
                self.logger.error("Failed to load operational context", extra={"error": str(e)})
    
    def save_operational_context(self):
        """Save operational context to disk"""
        context_file = self.state_path / "claude_context.json"
        try:
            with open(context_file, 'w') as f:
                json.dump(self.operational_context, f, indent=2)
        except Exception as e:
            self.logger.error("Failed to save operational context", extra={"error": str(e)})
    
    def translate_ambient_event(self, event: Dict) -> Optional[Dict]:
        """
        Translate an operational event into Claude-understandable context.
        
        Returns:
            Dict with 'message', 'silent', 'priority', and 'actions' keys
            None if event should not be presented to Claude
        """
        event_type = event.get("type", "")
        
        if event_type not in self.event_templates:
            return None
        
        template_config = self.event_templates[event_type]
        
        try:
            # Format the template with event data
            message = template_config["template"].format(**event.get("payload", {}))
            
            # Build translated event
            translated = {
                "message": message,
                "silent": template_config.get("silent", False),
                "priority": template_config.get("priority", "normal"),
                "actions": template_config.get("actions", []),
                "event_id": event.get("event_id"),
                "timestamp": event.get("timestamp", time.time()),
                "original_event": event
            }
            
            self.logger.info("Translated ambient event", extra={
                "event_type": event_type,
                "silent": translated["silent"],
                "priority": translated["priority"]
            })
            
            return translated
            
        except KeyError as e:
            self.logger.error("Failed to format event template", extra={
                "event_type": event_type,
                "missing_key": str(e),
                "payload": event.get("payload", {})
            })
            return None
    
    def inject_operational_context(self, user_message: str) -> str:
        """
        Inject operational context into user messages when relevant.
        
        This enables Claude to be aware of ongoing operations without being asked.
        """
        # Check for critical issues that should be mentioned immediately
        critical_context = []
        
        # Active incidents
        if self.operational_context.get("active_incidents"):
            incident_count = len(self.operational_context["active_incidents"])
            critical_context.append(f"🚨 {incident_count} active incident(s) requiring attention")
        
        # Recent performance issues
        performance_issues = [
            issue for issue in self.operational_context.get("performance_issues", [])
            if time.time() - issue.get("detected_at", 0) < 3600  # Last hour
        ]
        if performance_issues:
            critical_context.append(f"⚠️ {len(performance_issues)} performance issue(s) detected")
        
        # Pending high-priority operations
        high_priority_ops = [
            op for op in self.operational_context.get("pending_operations", [])
            if op.get("priority") in ["critical", "high"]
        ]
        if high_priority_ops:
            critical_context.append(f"📋 {len(high_priority_ops)} high-priority operation(s) pending")
        
        # Inject context if critical issues exist
        if critical_context:
            context_prefix = "[OPERATIONAL STATUS: " + " | ".join(critical_context) + "]\n\n"
            return context_prefix + user_message
        
        # Check for relevant background context
        background_context = self.get_relevant_background_context(user_message)
        if background_context:
            context_suffix = "\n\n[Background: " + background_context + "]"
            return user_message + context_suffix
        
        return user_message
    
    def get_relevant_background_context(self, user_message: str) -> Optional[str]:
        """Get relevant background context based on user message content"""
        
        # Deployment-related context
        if any(word in user_message.lower() for word in ["deploy", "deployment", "release"]):
            recent_deployments = self.operational_context.get("recent_deployments", [])
            if recent_deployments:
                latest = recent_deployments[-1]
                return f"Latest deployment: {latest.get('service')} at {latest.get('timestamp')}"
        
        # Performance-related context
        if any(word in user_message.lower() for word in ["performance", "slow", "latency", "speed"]):
            performance_issues = self.operational_context.get("performance_issues", [])
            if performance_issues:
                return f"{len(performance_issues)} recent performance issue(s) identified"
        
        # Monitoring-related context
        if any(word in user_message.lower() for word in ["monitor", "alert", "metric", "dashboard"]):
            pending_monitoring = [
                op for op in self.operational_context.get("pending_operations", [])
                if "monitoring" in op.get("type", "").lower()
            ]
            if pending_monitoring:
                return f"Monitoring setup pending for {len(pending_monitoring)} service(s)"
        
        return None
    
    def should_interrupt_conversation(self, event: Dict) -> bool:
        """
        Determine if an event should interrupt the current conversation.
        
        Critical events should interrupt, while normal operations should be silent.
        """
        event_type = event.get("type", "")
        priority = event.get("priority", "normal")
        
        # Always interrupt for critical events
        if priority == "critical":
            return True
        
        # Interrupt for high priority events with user impact
        if priority == "high" and event.get("user_impact", 0) > 0.5:
            return True
        
        # Don't interrupt for silent events
        if event.get("silent", False):
            return False
        
        # Don't interrupt for background operations
        if event.get("ambient", False):
            return False
        
        return False
    
    def create_proactive_prompt(self, context: Dict) -> str:
        """
        Create proactive prompt when Claude should take initiative.
        
        This enables scenarios like:
        "I noticed you deployed the user service. Let me set up monitoring..."
        """
        
        triggers = context.get("triggers", [])
        deployment_info = context.get("deployment_info")
        performance_issues = context.get("performance_issues", [])
        
        if deployment_info and "monitoring-agent" in triggers:
            service = deployment_info.get("service", "the service")
            return f"I noticed you deployed {service}. Let me automatically set up comprehensive monitoring including dashboards, alerts, and health checks."
        
        if performance_issues and "performance-optimizer-agent" in triggers:
            issue_count = len(performance_issues)
            return f"I've detected {issue_count} performance issue(s). Let me analyze and provide optimization recommendations."
        
        if "incident-response-agent" in triggers:
            return "I'm detecting signs of a potential incident. Let me investigate and prepare response procedures."
        
        # Default proactive response
        agent_names = ", ".join(triggers)
        return f"I'm automatically handling operational tasks with {agent_names} to ensure system reliability."
    
    def format_operational_summary(self) -> str:
        """
        Format current operational status for Claude.
        
        This provides Claude with situational awareness of what's happening operationally.
        """
        summary_parts = []
        
        # System health
        active_incidents = len(self.operational_context.get("active_incidents", []))
        if active_incidents > 0:
            summary_parts.append(f"🚨 {active_incidents} active incident(s)")
        else:
            summary_parts.append("✅ No active incidents")
        
        # Recent deployments
        recent_deployments = self.operational_context.get("recent_deployments", [])
        if recent_deployments:
            latest = recent_deployments[-1]
            summary_parts.append(f"📦 Latest deployment: {latest.get('service')} ({latest.get('status', 'unknown')})")
        
        # Pending operations
        pending_ops = self.operational_context.get("pending_operations", [])
        if pending_ops:
            summary_parts.append(f"⏳ {len(pending_ops)} pending operation(s)")
        
        # Performance status
        performance_issues = self.operational_context.get("performance_issues", [])
        if performance_issues:
            summary_parts.append(f"⚠️ {len(performance_issues)} performance issue(s)")
        else:
            summary_parts.append("🚀 Performance nominal")
        
        return " | ".join(summary_parts)
    
    def update_operational_awareness(self, event: Dict):
        """Update operational awareness based on new events"""
        event_type = event.get("type", "")
        timestamp = event.get("timestamp", time.time())
        
        # Update based on event type
        if event_type == "INCIDENT_DETECTED":
            self.operational_context.setdefault("active_incidents", []).append({
                "id": event.get("event_id"),
                "type": event.get("payload", {}).get("error_type"),
                "service": event.get("payload", {}).get("service"),
                "detected_at": timestamp
            })
        
        elif event_type == "INCIDENT_RESOLVED":
            # Remove resolved incident
            incident_id = event.get("payload", {}).get("incident_id")
            self.operational_context["active_incidents"] = [
                incident for incident in self.operational_context.get("active_incidents", [])
                if incident.get("id") != incident_id
            ]
        
        elif event_type == "DEPLOYMENT_COMPLETE":
            self.operational_context.setdefault("recent_deployments", []).append({
                "service": event.get("payload", {}).get("service"),
                "version": event.get("payload", {}).get("version"),
                "timestamp": timestamp,
                "status": "completed"
            })
            
            # Keep only recent deployments (last 24 hours)
            cutoff = timestamp - (24 * 60 * 60)
            self.operational_context["recent_deployments"] = [
                dep for dep in self.operational_context["recent_deployments"]
                if dep.get("timestamp", 0) > cutoff
            ]
        
        elif event_type == "PERFORMANCE_DEGRADED":
            self.operational_context.setdefault("performance_issues", []).append({
                "service": event.get("payload", {}).get("service"),
                "metric": event.get("payload", {}).get("metric"),
                "detected_at": timestamp,
                "severity": event.get("payload", {}).get("severity", "medium")
            })
        
        # Save updated context
        self.save_operational_context()
    
    def create_agent_prompt(self, agent_name: str, context: Dict) -> str:
        """
        Create natural language prompt for specific agent.
        
        This translates technical context into agent-specific instructions.
        """
        
        base_prompt = f"Use {agent_name} to handle this operational requirement."
        
        # Add context-specific instructions
        if agent_name == "monitoring-agent":
            deployment = context.get("deployment_info")
            if deployment:
                service = deployment.get("service", "the service")
                base_prompt += f" Set up comprehensive monitoring for {service} including metrics, alerts, and dashboards."
        
        elif agent_name == "performance-optimizer-agent":
            issues = context.get("performance_issues", [])
            if issues:
                issue_types = [issue.get("metric", "unknown") for issue in issues]
                base_prompt += f" Analyze and optimize performance issues: {', '.join(issue_types)}."
        
        elif agent_name == "incident-response-agent":
            incident = context.get("incident_info")
            if incident:
                error_type = incident.get("error_type", "unknown error")
                service = incident.get("service", "system")
                base_prompt += f" Investigate and respond to {error_type} affecting {service}."
        
        elif agent_name == "documentation-agent":
            changes = context.get("recent_changes", [])
            if changes:
                base_prompt += f" Update documentation for {len(changes)} recent changes."
        
        return base_prompt
    
    def get_ambient_status(self) -> Dict:
        """Get current ambient operational status for display"""
        return {
            "active_incidents": len(self.operational_context.get("active_incidents", [])),
            "pending_operations": len(self.operational_context.get("pending_operations", [])),
            "recent_deployments": len(self.operational_context.get("recent_deployments", [])),
            "performance_issues": len(self.operational_context.get("performance_issues", [])),
            "automation_level": self.operational_context.get("automation_level", "full"),
            "last_updated": datetime.now().isoformat()
        }


def create_operational_prompt_context(event_data: Dict) -> str:
    """
    Helper function to create operational prompt context from event data.
    
    This is used by the orchestrator to provide Claude with relevant context
    when operational agents are triggered.
    """
    bridge = ClaudeBridge()
    
    # Translate the event
    translated = bridge.translate_ambient_event(event_data)
    
    if not translated:
        return "Handle this operational requirement."
    
    # Create contextual prompt
    context_parts = [translated["message"]]
    
    # Add operational status if relevant
    if not translated.get("silent", False):
        status = bridge.format_operational_summary()
        context_parts.append(f"Current operational status: {status}")
    
    # Add any specific actions
    if translated.get("actions"):
        actions_text = ", ".join(translated["actions"])
        context_parts.append(f"Recommended actions: {actions_text}")
    
    return "\n\n".join(context_parts)


if __name__ == "__main__":
    # Test the bridge with sample events
    bridge = ClaudeBridge()
    
    test_events = [
        {
            "type": "DEPLOYMENT_COMPLETE",
            "payload": {"service": "user-api", "version": "v1.2.3"},
            "timestamp": time.time()
        },
        {
            "type": "PERFORMANCE_DEGRADED", 
            "payload": {"service": "database", "metric": "response_time"},
            "timestamp": time.time()
        },
        {
            "type": "INCIDENT_DETECTED",
            "payload": {"error_type": "high_error_rate", "service": "payment-service"},
            "timestamp": time.time()
        }
    ]
    
    for event in test_events:
        translated = bridge.translate_ambient_event(event)
        if translated:
            print(f"Event: {event['type']}")
            print(f"Message: {translated['message']}")
            print(f"Silent: {translated['silent']}")
            print(f"Priority: {translated['priority']}")
            print("---")