#!/usr/bin/env python3
"""
AET Orchestrator V2 - Production-ready orchestrator using Task tool
This version is designed to be invoked by Claude in interactive mode
"""
import json
import time
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime

class AETOrchestratorV2:
    def __init__(self):
        self.base_path = Path(".claude")
        self.event_log = self.base_path / "events" / "log.ndjson"
        self.snapshots = self.base_path / "snapshots" / "tasks.json"
        self.registry_db = self.base_path / "registry" / "files.db"
        
        # Ensure directories exist
        self.event_log.parent.mkdir(parents=True, exist_ok=True)
        self.snapshots.parent.mkdir(parents=True, exist_ok=True)
        self.registry_db.parent.mkdir(parents=True, exist_ok=True)
        
        # Workflow definition
        self.workflow = {
            "CREATED": ("pm-agent", "PLANNING"),
            "PLANNING": ("architect-agent", "DESIGNING"),
            "DESIGNING": ("developer-agent", "IMPLEMENTING"),
            "IMPLEMENTING": ("reviewer-agent", "REVIEWING"),
            "REVIEWING": ("qa-agent", "TESTING"),
            "TESTING": ("integrator-agent", "INTEGRATING"),
            "INTEGRATING": (None, "COMPLETED")
        }
        
        # Agent descriptions for clarity
        self.agent_descriptions = {
            "pm-agent": "Project Manager - Creates detailed plans and requirements",
            "architect-agent": "Architect - Designs technical architecture",
            "developer-agent": "Developer - Implements the solution",
            "reviewer-agent": "Code Reviewer - Reviews implementation",
            "qa-agent": "QA Engineer - Tests the solution",
            "integrator-agent": "Integration Specialist - Prepares for deployment"
        }
    
    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        timestamp = int(time.time() * 1000)
        random_suffix = hashlib.sha256(str(timestamp).encode()).hexdigest()[:6]
        return f"{prefix}-{timestamp}-{random_suffix}"
    
    def _append_event(self, event: Dict) -> None:
        """Append event to the event log"""
        with open(self.event_log, "a") as f:
            f.write(json.dumps(event) + "\n")
    
    def _load_snapshots(self) -> Dict:
        """Load task snapshots"""
        if not self.snapshots.exists():
            return {}
        try:
            with open(self.snapshots, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def _save_snapshots(self, snapshots: Dict) -> None:
        """Save task snapshots"""
        with open(self.snapshots, "w") as f:
            json.dump(snapshots, f, indent=2)
    
    def create_task(self, ticket_id: str, description: str) -> Tuple[str, str]:
        """Create a new task and return (job_id, status_message)"""
        
        # Generate job ID
        job_id = self._generate_id("JOB")
        
        # Create workspace
        workspace = self.base_path / "workspaces" / job_id
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "artifacts").mkdir(exist_ok=True)
        
        # Create initial manifest
        manifest = {
            "job_id": job_id,
            "ticket_id": ticket_id,
            "description": description,
            "status": "CREATED",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        with open(workspace / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)
        
        # Log creation event
        event = {
            "event_id": self._generate_id("evt"),
            "ticket_id": ticket_id,
            "type": "TASK_CREATED",
            "timestamp": time.time(),
            "payload": {
                "job_id": job_id,
                "description": description
            }
        }
        self._append_event(event)
        
        # Update snapshots
        snapshots = self._load_snapshots()
        snapshots[ticket_id] = {
            "job_id": job_id,
            "status": "CREATED",
            "description": description,
            "created_at": datetime.now().isoformat(),
            "current_agent": None,
            "retry_count": 0
        }
        self._save_snapshots(snapshots)
        
        return job_id, f"✅ Created task {ticket_id} with workspace {job_id}"
    
    def get_agent_prompt(self, agent_type: str, ticket_id: str, job_id: str, description: str) -> str:
        """Generate comprehensive prompt for Task agent"""
        
        prompt = f"""You are the {agent_type} working on task {ticket_id}.

## Task Description
{description}

## Your Workspace
- Main workspace: .claude/workspaces/{job_id}/
- Artifacts directory: .claude/workspaces/{job_id}/artifacts/

## Available Tools and Protocols

### 1. Event Log Access
Read the complete event history:
```
Read(".claude/events/log.ndjson")
```
Then filter for your ticket_id: {ticket_id}

### 2. Database Queries
Query the file registry using sqlite3:
```bash
# Find files for this ticket
sqlite3 .claude/registry/files.db "SELECT * FROM files WHERE ticket_id='{ticket_id}'"

# Find dependencies
sqlite3 .claude/registry/files.db "SELECT * FROM dependencies WHERE source_file IN (SELECT path FROM files WHERE ticket_id='{ticket_id}')"

# Find components
sqlite3 .claude/registry/files.db "SELECT * FROM components WHERE ticket_id='{ticket_id}'"
```

### 3. Knowledge Manager (if running)
Query for semantic context:
```
WebFetch(
    url="http://localhost:5001/mcp",
    prompt="Get relevant patterns for {agent_type} working on: {description}"
)
```
Note: This may fail if KM is not running - that's okay, continue without it.

### 4. Previous Artifacts
Check what previous agents created:
```
Glob(".claude/workspaces/{job_id}/artifacts/*.md")
Read(".claude/workspaces/{job_id}/artifacts/<filename>")
```

"""
        
        # Add agent-specific instructions
        if agent_type == "pm-agent":
            prompt += """
## Your Specific Task: Project Planning

1. Analyze the task description
2. Break it down into clear, actionable steps
3. Define acceptance criteria
4. Identify technical requirements
5. Consider edge cases and risks

Output:
- Write detailed plan to: .claude/workspaces/{job_id}/artifacts/plan.md
- Include: objectives, requirements, steps, acceptance criteria, risks

Structure your plan.md as:
```markdown
# Project Plan: {description}

## Objectives
- Clear goals...

## Requirements
### Functional Requirements
- ...
### Technical Requirements
- ...

## Implementation Steps
1. ...
2. ...

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Risks and Mitigations
- Risk: ... Mitigation: ...
```
""".format(job_id=job_id, description=description)
        
        elif agent_type == "architect-agent":
            prompt += """
## Your Specific Task: Technical Architecture

1. Read the PM's plan: .claude/workspaces/{job_id}/artifacts/plan.md
2. Design the technical architecture
3. Identify components and their interactions
4. Define interfaces and contracts
5. Consider scalability and maintainability

Output:
- Write architecture to: .claude/workspaces/{job_id}/artifacts/architecture.md
- Include: components, interfaces, data flow, technology choices

Structure your architecture.md as:
```markdown
# Technical Architecture

## Overview
High-level architecture description...

## Components
### Component 1
- Purpose: ...
- Interface: ...
- Dependencies: ...

## Data Flow
1. ...

## Technology Stack
- Language: ...
- Framework: ...
- Database: ...

## Interfaces
```
""".format(job_id=job_id)
        
        elif agent_type == "developer-agent":
            prompt += """
## Your Specific Task: Implementation

1. Read plan.md and architecture.md from artifacts/
2. Implement the solution according to specifications
3. Write clean, documented code
4. Follow the architectural design
5. Register new files in the database

Output:
- Write code to: .claude/workspaces/{job_id}/src/
- Create implementation summary: .claude/workspaces/{job_id}/artifacts/implementation.md

After creating each file, register it:
```bash
sqlite3 .claude/registry/files.db "INSERT INTO files (path, ticket_id, job_id, agent_name) VALUES ('path/to/file', '{ticket_id}', '{job_id}', 'developer-agent')"
```
""".format(job_id=job_id, ticket_id=ticket_id)
        
        elif agent_type == "reviewer-agent":
            prompt += """
## Your Specific Task: Code Review

1. Read all previous artifacts
2. Review the implementation in src/
3. Check for:
   - Code quality and standards
   - Security issues
   - Performance concerns
   - Architectural compliance
   - Best practices

Output:
- Write review to: .claude/workspaces/{job_id}/artifacts/review.md
- Include: findings, suggestions, approval status

Structure your review.md as:
```markdown
# Code Review Report

## Summary
Overall assessment...

## Findings
### Critical Issues
- None / List issues...

### Suggestions
- ...

## Approval Status
- [ ] Approved
- [ ] Approved with minor changes
- [ ] Needs revision
```
""".format(job_id=job_id)
        
        elif agent_type == "qa-agent":
            prompt += """
## Your Specific Task: Quality Assurance

1. Read implementation and review
2. Design test cases
3. Execute tests if possible
4. Document test results
5. Verify acceptance criteria

Output:
- Write test report to: .claude/workspaces/{job_id}/artifacts/qa-report.md
- Include: test cases, results, coverage, recommendations
""".format(job_id=job_id)
        
        elif agent_type == "integrator-agent":
            prompt += """
## Your Specific Task: Integration Preparation

1. Read all artifacts
2. Verify completeness
3. Check for integration issues
4. Prepare deployment checklist
5. Document integration steps

Output:
- Write integration plan to: .claude/workspaces/{job_id}/artifacts/integration.md
- Include: checklist, dependencies, deployment steps
""".format(job_id=job_id)
        
        # Add completion protocol
        prompt += f"""

## Completion Protocol

When you've completed your task:

1. Write a completion event to the log:
```python
import json
import time

event = {{
    "event_id": "evt_" + str(int(time.time() * 1000)),
    "ticket_id": "{ticket_id}",
    "type": "AGENT_COMPLETED",
    "agent": "{agent_type}",
    "timestamp": time.time(),
    "payload": {{
        "status": "success",
        "summary": "Brief summary of what you accomplished",
        "artifacts": ["List", "of", "files", "created"]
    }}
}}

# Use Bash to append
Bash(f"echo '{{json.dumps(event)}}' >> .claude/events/log.ndjson")
```

2. Confirm the event was written:
```
Bash("tail -1 .claude/events/log.ndjson")
```

Begin your work now. Be thorough and professional.
"""
        
        return prompt
    
    def process_next(self, ticket_id: str) -> Tuple[str, str, Optional[str]]:
        """
        Process the next step for a ticket
        Returns: (status, message, agent_prompt_or_none)
        """
        
        snapshots = self._load_snapshots()
        
        if ticket_id not in snapshots:
            return "error", f"❌ Task {ticket_id} not found", None
        
        task = snapshots[ticket_id]
        current_status = task["status"]
        job_id = task["job_id"]
        description = task["description"]
        
        # Check if task is already complete
        if current_status == "COMPLETED":
            return "completed", f"✅ Task {ticket_id} is already complete", None
        
        # Get next agent
        if current_status not in self.workflow:
            return "error", f"❌ Invalid status: {current_status}", None
        
        agent_type, next_status = self.workflow[current_status]
        
        if agent_type is None:
            # Mark as complete
            task["status"] = "COMPLETED"
            task["updated_at"] = datetime.now().isoformat()
            self._save_snapshots(snapshots)
            
            return "completed", f"🎉 Task {ticket_id} is now COMPLETE!", None
        
        # Generate agent prompt
        agent_prompt = self.get_agent_prompt(agent_type, ticket_id, job_id, description)
        
        # Update snapshot to show agent is running
        task["current_agent"] = agent_type
        task["updated_at"] = datetime.now().isoformat()
        self._save_snapshots(snapshots)
        
        # Log agent start
        event = {
            "event_id": self._generate_id("evt"),
            "ticket_id": ticket_id,
            "type": "AGENT_STARTED",
            "agent": agent_type,
            "timestamp": time.time(),
            "payload": {
                "job_id": job_id,
                "status": current_status
            }
        }
        self._append_event(event)
        
        message = f"""
🚀 **Starting {agent_type}**
   
📋 Task: {ticket_id}
📂 Workspace: {job_id}
📝 Current Status: {current_status} → {next_status}
🤖 Agent: {self.agent_descriptions.get(agent_type, agent_type)}

The agent prompt has been prepared. Please invoke the Task tool to execute the agent.
"""
        
        return "ready", message, agent_prompt
    
    def check_completion(self, ticket_id: str) -> Tuple[bool, str]:
        """Check if the current agent has completed"""
        
        snapshots = self._load_snapshots()
        
        if ticket_id not in snapshots:
            return False, f"Task {ticket_id} not found"
        
        task = snapshots[ticket_id]
        current_agent = task.get("current_agent")
        
        if not current_agent:
            return False, "No agent currently running"
        
        # Check event log for completion
        if self.event_log.exists():
            with open(self.event_log, "r") as f:
                # Read lines in reverse to find most recent
                lines = f.readlines()
                for line in reversed(lines):
                    try:
                        event = json.loads(line.strip())
                        if (event.get("ticket_id") == ticket_id and
                            event.get("type") == "AGENT_COMPLETED" and
                            event.get("agent") == current_agent):
                            return True, f"✅ {current_agent} has completed"
                    except:
                        continue
        
        return False, f"⏳ {current_agent} is still running"
    
    def advance(self, ticket_id: str) -> str:
        """Advance task to next status after agent completion"""
        
        snapshots = self._load_snapshots()
        
        if ticket_id not in snapshots:
            return f"❌ Task {ticket_id} not found"
        
        task = snapshots[ticket_id]
        current_status = task["status"]
        
        if current_status not in self.workflow:
            return f"❌ Invalid status: {current_status}"
        
        _, next_status = self.workflow[current_status]
        
        # Update task
        task["status"] = next_status
        task["current_agent"] = None
        task["updated_at"] = datetime.now().isoformat()
        task["retry_count"] = 0  # Reset retry count
        
        self._save_snapshots(snapshots)
        
        return f"✅ Advanced {ticket_id}: {current_status} → {next_status}"
    
    def status(self, ticket_id: Optional[str] = None) -> str:
        """Get status of task(s)"""
        
        snapshots = self._load_snapshots()
        
        if not snapshots:
            return "📭 No tasks found"
        
        if ticket_id:
            if ticket_id not in snapshots:
                return f"❌ Task {ticket_id} not found"
            
            task = snapshots[ticket_id]
            status_msg = f"""
📋 **Task Status: {ticket_id}**

- Status: {task['status']}
- Job ID: {task['job_id']}
- Current Agent: {task.get('current_agent', 'None')}
- Created: {task.get('created_at', 'Unknown')}
- Updated: {task.get('updated_at', 'Unknown')}
- Description: {task.get('description', 'No description')}
"""
            return status_msg
        
        # Show all tasks
        status_msg = "📊 **All Tasks:**\n\n"
        for tid, task in snapshots.items():
            status_msg += f"- {tid}: {task['status']}"
            if task.get('current_agent'):
                status_msg += f" (Running: {task['current_agent']})"
            status_msg += "\n"
        
        return status_msg


def main():
    """CLI interface for the orchestrator"""
    import sys
    
    orchestrator = AETOrchestratorV2()
    
    if len(sys.argv) < 2:
        print("""
AET Orchestrator V2 - Usage:

  orchestrator_v2.py create <ticket_id> <description>
    Create a new task
    
  orchestrator_v2.py process <ticket_id>  
    Process next step for a task
    
  orchestrator_v2.py check <ticket_id>
    Check if current agent has completed
    
  orchestrator_v2.py advance <ticket_id>
    Advance task to next state
    
  orchestrator_v2.py status [ticket_id]
    Show status of task(s)
""")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        if len(sys.argv) < 4:
            print("❌ Usage: create <ticket_id> <description>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        description = " ".join(sys.argv[3:])
        job_id, message = orchestrator.create_task(ticket_id, description)
        print(message)
    
    elif command == "process":
        if len(sys.argv) < 3:
            print("❌ Usage: process <ticket_id>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        status, message, agent_prompt = orchestrator.process_next(ticket_id)
        
        print(message)
        
        if agent_prompt:
            print("\n" + "="*60)
            print("AGENT PROMPT (for Task tool):")
            print("="*60)
            print(agent_prompt)
    
    elif command == "check":
        if len(sys.argv) < 3:
            print("❌ Usage: check <ticket_id>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        is_complete, message = orchestrator.check_completion(ticket_id)
        print(message)
        
        if is_complete:
            print("\n💡 Next: Run 'orchestrator_v2.py advance {}' to continue".format(ticket_id))
    
    elif command == "advance":
        if len(sys.argv) < 3:
            print("❌ Usage: advance <ticket_id>")
            sys.exit(1)
        
        ticket_id = sys.argv[2]
        message = orchestrator.advance(ticket_id)
        print(message)
        print("\n💡 Next: Run 'orchestrator_v2.py process {}' to continue".format(ticket_id))
    
    elif command == "status":
        ticket_id = sys.argv[2] if len(sys.argv) > 2 else None
        status = orchestrator.status(ticket_id)
        print(status)
    
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()