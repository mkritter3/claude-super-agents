# Complete Guide to Building Autonomous Multi-Agent Systems

This comprehensive guide teaches you how to design, build, and deploy autonomous multi-agent systems that can handle complex tasks across any domain. Whether you're automating software engineering, content creation, social media management, or business operations, this framework provides the foundation for creating intelligent, collaborative AI systems.

## What is an Autonomous Multi-Agent System?

An Autonomous Multi-Agent System (AMAS) is a collection of specialized AI agents that work together to accomplish complex tasks with minimal human intervention. Each agent has specific expertise and capabilities, and they collaborate through shared knowledge, event coordination, and intelligent task distribution.

### Key Characteristics

- **Autonomous Operation**: Agents can make decisions and take actions independently
- **Specialization**: Each agent excels at specific types of tasks
- **Collaboration**: Agents share knowledge and coordinate their efforts
- **Event-Driven**: System responds to triggers and changing conditions
- **Self-Managing**: Includes monitoring, error recovery, and optimization
- **Scalable**: Can add new agents or capabilities without system redesign

### Real-World Applications

**Software Engineering:**
- Code review, testing, deployment automation
- Bug detection, performance optimization
- Documentation generation, dependency management

**Content Creation:**
- Writing, editing, fact-checking
- SEO optimization, multimedia production
- Translation, localization

**Social Media Management:**
- Content scheduling, audience engagement
- Trend analysis, influencer outreach
- Community moderation, crisis management

**Business Operations:**
- Customer service, lead qualification
- Invoice processing, compliance monitoring
- Market research, competitive analysis

## System Architecture Overview

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                    Control Layer                        │
├─────────────────────────────────────────────────────────┤
│  Event System  │  Knowledge Manager  │  Orchestrator   │
├─────────────────────────────────────────────────────────┤
│                   Agent Network                         │
├─────────────────────────────────────────────────────────┤
│ Agent A │ Agent B │ Agent C │ Agent D │ Agent E │ ... │
├─────────────────────────────────────────────────────────┤
│                 Integration Layer                       │
├─────────────────────────────────────────────────────────┤
│  MCP Bridge  │  API Connectors  │  File System  │ ... │
└─────────────────────────────────────────────────────────┘
```

### Agent Specialization Patterns

1. **Functional Specialists**: Focus on specific tasks (writer, reviewer, tester)
2. **Domain Experts**: Deep knowledge in particular areas (security, performance)
3. **Process Managers**: Coordinate workflows and multi-step operations
4. **Quality Gatekeepers**: Ensure standards and catch errors
5. **Integration Bridges**: Connect to external systems and APIs

### Communication & Coordination

- **Knowledge Sharing**: Centralized knowledge base with agent contributions
- **Event Propagation**: Trigger-based activation and response chains
- **Task Delegation**: Intelligent routing based on agent capabilities
- **Result Aggregation**: Combining outputs from multiple agents
- **Conflict Resolution**: Handling disagreements and priority conflicts

## Phase 1: System Design & Planning

### Step 1: Define Your Domain & Objectives

**Identify Core Tasks:**
```
Primary Objectives:
- What is the main goal of your system?
- What repetitive tasks consume the most time?
- What decisions require expertise but follow patterns?

Success Metrics:
- How will you measure system effectiveness?
- What quality standards must be maintained?
- What performance benchmarks are important?

Constraints & Requirements:
- What are the technical limitations?
- What compliance or security requirements exist?
- What is the acceptable level of automation vs. human oversight?
```

**Domain Analysis Template:**
```markdown
## Domain: [Your Domain Here]

### Current Workflow
1. [Manual Process Step 1]
2. [Manual Process Step 2]
3. [Manual Process Step 3]
...

### Pain Points
- [Bottleneck 1]: Time-consuming, repetitive
- [Error Prone Area]: High mistake frequency
- [Knowledge Gap]: Requires specific expertise

### Automation Opportunities
- [Task A]: High volume, rule-based → Good for automation
- [Task B]: Creative but templated → Partial automation
- [Task C]: Complex decision-making → Human + AI collaboration

### Success Vision
- Reduce [specific task] time by X%
- Improve quality of [deliverable] by Y%
- Enable scaling to Z times current capacity
```

### Step 2: Design Agent Architecture

**Agent Identification Framework:**
```python
# Agent Design Template
class AgentSpec:
    def __init__(self, name, domain, capabilities, triggers, outputs):
        self.name = name                    # Unique identifier
        self.domain = domain                # Area of expertise
        self.capabilities = capabilities    # What it can do
        self.triggers = triggers           # When it activates
        self.outputs = outputs             # What it produces
        self.dependencies = []             # What it needs from others
        self.consumers = []                # Who uses its outputs

# Example: Content Creation System
content_strategy_agent = AgentSpec(
    name="content-strategist",
    domain="Content Planning",
    capabilities=[
        "Analyze audience data",
        "Research trending topics", 
        "Create content calendars",
        "Define content pillars"
    ],
    triggers=[
        "Monthly planning cycle",
        "Audience metrics update",
        "Trend analysis request"
    ],
    outputs=[
        "Content calendar",
        "Topic recommendations",
        "Audience insights report"
    ]
)

content_writer_agent = AgentSpec(
    name="content-writer", 
    domain="Content Creation",
    capabilities=[
        "Write blog posts",
        "Create social media content",
        "Adapt tone and style",
        "SEO optimization"
    ],
    triggers=[
        "Content calendar item due",
        "Writing request",
        "Content revision needed"
    ],
    outputs=[
        "Draft content",
        "SEO metadata",
        "Content variations"
    ]
)
```

**Agent Relationship Mapping:**
```
Strategy Agent → Content Calendar → Writer Agent → Draft Content → Editor Agent → Final Content → Publisher Agent
      ↓                                    ↓                           ↓                    ↓
Analytics Agent ← Performance Data ← Social Agent ← Engagement Data ← Monitor Agent
```

### Step 3: Plan System Infrastructure

**Technology Stack Decisions:**
```yaml
Core Framework:
  - Language: Python/Node.js/Go
  - Agent Communication: Message queues (Redis/RabbitMQ)
  - Knowledge Storage: Vector database + Traditional DB
  - Event System: Event sourcing pattern
  - Orchestration: Workflow engine

Integration Layer:
  - API Framework: FastAPI/Express/Gin
  - External APIs: Service-specific SDKs
  - File System: Structured storage with versioning
  - Monitoring: Observability stack (metrics, logs, traces)

Security & Reliability:
  - Authentication: API keys, OAuth where needed
  - Data Protection: Encryption at rest and in transit
  - Error Handling: Circuit breakers, retry logic
  - Backup: Regular snapshots, disaster recovery
```

**Deployment Architecture:**
```
Development → Staging → Production

Local Development:
- Individual agent development
- Unit testing and integration testing
- Local knowledge manager and event system

Staging Environment:
- Full system integration testing
- Performance benchmarking
- User acceptance testing

Production Deployment:
- Container orchestration (Docker/Kubernetes)
- Load balancing and auto-scaling
- Monitoring and alerting
- Backup and disaster recovery
```

## Phase 2: Core Infrastructure Implementation

### Step 1: Build the Knowledge Management System

**Knowledge Manager Design:**
```python
#!/usr/bin/env python3
"""
Universal Knowledge Manager for Multi-Agent Systems
Handles agent knowledge sharing, context preservation, and learning
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import hashlib

@dataclass
class Knowledge:
    id: str
    agent_id: str
    category: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None
    confidence: float = 1.0
    source: str = "agent"

class KnowledgeManager:
    def __init__(self, db_path: str = "knowledge.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize knowledge database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                category TEXT NOT NULL,
                content JSON NOT NULL,
                metadata JSON NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP,
                confidence REAL NOT NULL,
                source TEXT NOT NULL,
                content_hash TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_category 
            ON knowledge(agent_id, category)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category_created 
            ON knowledge(category, created_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def store_knowledge(self, knowledge: Knowledge) -> str:
        """Store knowledge with deduplication"""
        content_hash = hashlib.sha256(
            json.dumps(knowledge.content, sort_keys=True).encode()
        ).hexdigest()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for duplicate content
        cursor.execute(
            "SELECT id FROM knowledge WHERE content_hash = ? AND category = ?",
            (content_hash, knowledge.category)
        )
        
        if cursor.fetchone():
            conn.close()
            return "duplicate"
        
        # Store new knowledge
        cursor.execute("""
            INSERT INTO knowledge 
            (id, agent_id, category, content, metadata, created_at, 
             expires_at, confidence, source, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            knowledge.id,
            knowledge.agent_id,
            knowledge.category,
            json.dumps(knowledge.content),
            json.dumps(knowledge.metadata),
            knowledge.created_at,
            knowledge.expires_at,
            knowledge.confidence,
            knowledge.source,
            content_hash
        ))
        
        conn.commit()
        conn.close()
        return knowledge.id
    
    def retrieve_knowledge(self, 
                          category: str = None,
                          agent_id: str = None,
                          limit: int = 100) -> List[Knowledge]:
        """Retrieve knowledge with filtering"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM knowledge WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
            
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
        
        # Filter out expired knowledge
        query += " AND (expires_at IS NULL OR expires_at > ?)"
        params.append(datetime.now())
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        knowledge_list = []
        for row in rows:
            knowledge = Knowledge(
                id=row[0],
                agent_id=row[1],
                category=row[2],
                content=json.loads(row[3]),
                metadata=json.loads(row[4]),
                created_at=datetime.fromisoformat(row[5]),
                expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                confidence=row[7],
                source=row[8]
            )
            knowledge_list.append(knowledge)
        
        return knowledge_list
    
    def share_knowledge(self, source_agent: str, target_agent: str, 
                       category: str, content: Dict[str, Any]) -> str:
        """Share knowledge between agents"""
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            agent_id=target_agent,
            category=f"shared_{category}",
            content=content,
            metadata={
                "shared_from": source_agent,
                "share_timestamp": datetime.now().isoformat(),
                "share_type": "knowledge_transfer"
            },
            created_at=datetime.now(),
            source="knowledge_share"
        )
        
        return self.store_knowledge(knowledge)
```

### Step 2: Implement Event System

**Event-Driven Coordination:**
```python
#!/usr/bin/env python3
"""
Universal Event System for Multi-Agent Coordination
Handles triggers, event propagation, and agent activation
"""

import json
import threading
import queue
from datetime import datetime
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from enum import Enum
import uuid

class EventPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class EventType(Enum):
    TASK_REQUEST = "task_request"
    TASK_COMPLETE = "task_complete"
    DATA_UPDATE = "data_update"
    ERROR_OCCURRED = "error_occurred"
    SYSTEM_STATUS = "system_status"
    AGENT_MESSAGE = "agent_message"
    EXTERNAL_TRIGGER = "external_trigger"

@dataclass
class Event:
    id: str
    type: EventType
    source: str
    target: str = None  # None = broadcast
    data: Dict[str, Any] = None
    priority: EventPriority = EventPriority.NORMAL
    created_at: datetime = None
    expires_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.data is None:
            self.data = {}

class EventSystem:
    def __init__(self):
        self.event_queue = queue.PriorityQueue()
        self.subscribers: Dict[str, List[Callable]] = {}
        self.running = False
        self.processor_thread = None
        self.event_history: List[Event] = []
        self.max_history = 1000
    
    def start(self):
        """Start event processing"""
        self.running = True
        self.processor_thread = threading.Thread(target=self._process_events)
        self.processor_thread.start()
    
    def stop(self):
        """Stop event processing"""
        self.running = False
        if self.processor_thread:
            self.processor_thread.join()
    
    def publish(self, event: Event) -> str:
        """Publish event to the system"""
        # Add to queue with priority
        priority_value = 10 - event.priority.value  # Higher priority = lower number
        self.event_queue.put((priority_value, event.created_at, event))
        
        # Add to history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)
        
        return event.id
    
    def subscribe(self, event_type: EventType, agent_id: str, callback: Callable):
        """Subscribe agent to specific event types"""
        key = f"{event_type.value}:{agent_id}"
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
    
    def subscribe_all(self, agent_id: str, callback: Callable):
        """Subscribe agent to all events"""
        key = f"*:{agent_id}"
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
    
    def _process_events(self):
        """Process events from the queue"""
        while self.running:
            try:
                # Get event with timeout
                priority, timestamp, event = self.event_queue.get(timeout=1)
                
                # Check if event has expired
                if event.expires_at and datetime.now() > event.expires_at:
                    continue
                
                # Route event to subscribers
                self._route_event(event)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Event processing error: {e}")
    
    def _route_event(self, event: Event):
        """Route event to appropriate subscribers"""
        # Targeted delivery
        if event.target:
            key = f"{event.type.value}:{event.target}"
            if key in self.subscribers:
                for callback in self.subscribers[key]:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Callback error for {key}: {e}")
        
        # Broadcast delivery
        else:
            # Send to specific subscribers
            key = f"{event.type.value}:*"
            if key in self.subscribers:
                for callback in self.subscribers[key]:
                    try:
                        callback(event)
                    except Exception as e:
                        print(f"Broadcast callback error: {e}")
            
            # Send to catch-all subscribers
            for subscriber_key, callbacks in self.subscribers.items():
                if subscriber_key.startswith("*:"):
                    for callback in callbacks:
                        try:
                            callback(event)
                        except Exception as e:
                            print(f"Catch-all callback error: {e}")

# Event Helper Functions
def create_task_request(task_type: str, source: str, target: str = None, 
                       parameters: Dict[str, Any] = None) -> Event:
    """Create a task request event"""
    return Event(
        id=str(uuid.uuid4()),
        type=EventType.TASK_REQUEST,
        source=source,
        target=target,
        data={
            "task_type": task_type,
            "parameters": parameters or {},
            "timestamp": datetime.now().isoformat()
        }
    )

def create_data_update(data_type: str, source: str, data: Dict[str, Any]) -> Event:
    """Create a data update event"""
    return Event(
        id=str(uuid.uuid4()),
        type=EventType.DATA_UPDATE,
        source=source,
        data={
            "data_type": data_type,
            "update_data": data,
            "timestamp": datetime.now().isoformat()
        }
    )
```

### Step 3: Create Agent Base Framework

**Universal Agent Base Class:**
```python
#!/usr/bin/env python3
"""
Universal Agent Base Framework
Provides core functionality for all specialized agents
"""

import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

from knowledge_manager import KnowledgeManager, Knowledge
from event_system import EventSystem, Event, EventType, EventPriority

class AgentStatus(Enum):
    IDLE = "idle"
    WORKING = "working"  
    ERROR = "error"
    OFFLINE = "offline"

class AgentCapability:
    def __init__(self, name: str, description: str, 
                 input_schema: Dict[str, Any], 
                 output_schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema

class BaseAgent(ABC):
    def __init__(self, agent_id: str, agent_type: str, 
                 knowledge_manager: KnowledgeManager,
                 event_system: EventSystem):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.knowledge_manager = knowledge_manager
        self.event_system = event_system
        
        self.status = AgentStatus.OFFLINE
        self.capabilities: List[AgentCapability] = []
        self.current_tasks: Dict[str, Any] = {}
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "average_task_time": 0.0,
            "last_activity": None
        }
        
        # Setup logging
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # Register with event system
        self._register_event_handlers()
    
    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """Return list of agent capabilities"""
        pass
    
    @abstractmethod
    async def process_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process a specific task"""
        pass
    
    def start(self):
        """Start the agent"""
        self.status = AgentStatus.IDLE
        self.capabilities = self.get_capabilities()
        self.logger.info(f"Agent {self.agent_id} started with {len(self.capabilities)} capabilities")
        
        # Announce availability
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.SYSTEM_STATUS,
            source=self.agent_id,
            data={
                "status": "online",
                "capabilities": [cap.name for cap in self.capabilities],
                "timestamp": datetime.now().isoformat()
            }
        )
        self.event_system.publish(event)
    
    def stop(self):
        """Stop the agent"""
        self.status = AgentStatus.OFFLINE
        self.logger.info(f"Agent {self.agent_id} stopped")
        
        # Announce unavailability
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.SYSTEM_STATUS,
            source=self.agent_id,
            data={
                "status": "offline",
                "timestamp": datetime.now().isoformat()
            }
        )
        self.event_system.publish(event)
    
    async def handle_task_request(self, event: Event):
        """Handle incoming task requests"""
        task_type = event.data.get("task_type")
        parameters = event.data.get("parameters", {})
        
        # Check if we can handle this task
        if not self._can_handle_task(task_type):
            self.logger.warning(f"Cannot handle task type: {task_type}")
            return
        
        # Update status
        self.status = AgentStatus.WORKING
        task_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            # Store task start
            self.current_tasks[task_id] = {
                "type": task_type,
                "parameters": parameters,
                "started_at": start_time,
                "source": event.source
            }
            
            # Process the task
            result = await self.process_task(task_type, parameters)
            
            # Record completion
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.performance_metrics["tasks_completed"] += 1
            self._update_average_task_time(duration)
            self.performance_metrics["last_activity"] = end_time
            
            # Store knowledge about the task
            self._store_task_knowledge(task_type, parameters, result, duration)
            
            # Publish completion event
            completion_event = Event(
                id=str(uuid.uuid4()),
                type=EventType.TASK_COMPLETE,
                source=self.agent_id,
                target=event.source,
                data={
                    "task_id": task_id,
                    "task_type": task_type,
                    "result": result,
                    "duration": duration,
                    "timestamp": end_time.isoformat()
                }
            )
            self.event_system.publish(completion_event)
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            self.performance_metrics["tasks_failed"] += 1
            self.status = AgentStatus.ERROR
            
            # Publish error event
            error_event = Event(
                id=str(uuid.uuid4()),
                type=EventType.ERROR_OCCURRED,
                source=self.agent_id,
                data={
                    "task_id": task_id,
                    "task_type": task_type,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                },
                priority=EventPriority.HIGH
            )
            self.event_system.publish(error_event)
        
        finally:
            # Cleanup
            if task_id in self.current_tasks:
                del self.current_tasks[task_id]
            self.status = AgentStatus.IDLE
    
    def _can_handle_task(self, task_type: str) -> bool:
        """Check if agent can handle specific task type"""
        return any(cap.name == task_type for cap in self.capabilities)
    
    def _register_event_handlers(self):
        """Register event handlers"""
        self.event_system.subscribe(
            EventType.TASK_REQUEST, 
            self.agent_id, 
            self.handle_task_request
        )
    
    def _store_task_knowledge(self, task_type: str, parameters: Dict[str, Any], 
                            result: Dict[str, Any], duration: float):
        """Store knowledge about completed task"""
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            category="task_execution",
            content={
                "task_type": task_type,
                "parameters": parameters,
                "result": result,
                "execution_time": duration,
                "success": True
            },
            metadata={
                "agent_type": self.agent_type,
                "execution_timestamp": datetime.now().isoformat()
            },
            created_at=datetime.now(),
            confidence=1.0,
            source="task_execution"
        )
        
        self.knowledge_manager.store_knowledge(knowledge)
    
    def _update_average_task_time(self, duration: float):
        """Update average task execution time"""
        total_tasks = self.performance_metrics["tasks_completed"]
        current_avg = self.performance_metrics["average_task_time"]
        
        # Weighted average calculation
        new_avg = ((current_avg * (total_tasks - 1)) + duration) / total_tasks
        self.performance_metrics["average_task_time"] = new_avg
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.value,
            "capabilities": [cap.name for cap in self.capabilities],
            "current_tasks": len(self.current_tasks),
            "metrics": self.performance_metrics
        }
```

## Phase 3: Agent Development & Specialization

### Step 1: Create Specialized Agents

**Example: Content Writing Agent**
```python
#!/usr/bin/env python3
"""
Content Writing Agent
Specialized for creating various types of written content
"""

import asyncio
from typing import Dict, List, Any
from datetime import datetime

from base_agent import BaseAgent, AgentCapability

class ContentWriterAgent(BaseAgent):
    def __init__(self, agent_id: str, knowledge_manager, event_system, 
                 writing_config: Dict[str, Any] = None):
        super().__init__(agent_id, "content-writer", knowledge_manager, event_system)
        
        self.writing_config = writing_config or {
            "default_tone": "professional",
            "default_style": "informative",
            "max_length": 2000,
            "supported_formats": ["blog", "social", "email", "documentation"]
        }
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="write_blog_post",
                description="Write a complete blog post on given topic",
                input_schema={
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Blog post topic"},
                        "keywords": {"type": "array", "items": {"type": "string"}},
                        "tone": {"type": "string", "enum": ["professional", "casual", "technical"]},
                        "target_length": {"type": "integer", "minimum": 100, "maximum": 5000}
                    },
                    "required": ["topic"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "content": {"type": "string"},
                        "meta_description": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "word_count": {"type": "integer"},
                        "reading_time": {"type": "integer"}
                    }
                }
            ),
            AgentCapability(
                name="create_social_content",
                description="Create social media posts for various platforms",
                input_schema={
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "enum": ["twitter", "linkedin", "facebook", "instagram"]},
                        "message": {"type": "string", "description": "Core message to convey"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "include_cta": {"type": "boolean", "default": False}
                    },
                    "required": ["platform", "message"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "character_count": {"type": "integer"},
                        "hashtags": {"type": "array", "items": {"type": "string"}},
                        "suggested_posting_time": {"type": "string"}
                    }
                }
            ),
            AgentCapability(
                name="edit_content",
                description="Edit and improve existing content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Content to edit"},
                        "edit_type": {"type": "string", "enum": ["grammar", "style", "length", "tone"]},
                        "target_audience": {"type": "string"},
                        "feedback": {"type": "string", "description": "Specific feedback to address"}
                    },
                    "required": ["content", "edit_type"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "edited_content": {"type": "string"},
                        "changes_made": {"type": "array", "items": {"type": "string"}},
                        "improvement_score": {"type": "number", "minimum": 0, "maximum": 10}
                    }
                }
            )
        ]
    
    async def process_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process writing tasks"""
        if task_type == "write_blog_post":
            return await self._write_blog_post(parameters)
        elif task_type == "create_social_content":
            return await self._create_social_content(parameters)
        elif task_type == "edit_content":
            return await self._edit_content(parameters)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _write_blog_post(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Write a blog post"""
        topic = parameters["topic"]
        keywords = parameters.get("keywords", [])
        tone = parameters.get("tone", self.writing_config["default_tone"])
        target_length = parameters.get("target_length", 1500)
        
        # Get relevant knowledge
        related_knowledge = self.knowledge_manager.retrieve_knowledge(
            category="content_strategy",
            limit=10
        )
        
        # Simulate writing process (in real implementation, use LLM API)
        await asyncio.sleep(2)  # Simulate processing time
        
        title = f"Complete Guide to {topic.title()}"
        content = self._generate_blog_content(topic, keywords, tone, target_length)
        word_count = len(content.split())
        reading_time = max(1, word_count // 200)  # ~200 words per minute
        
        result = {
            "title": title,
            "content": content,
            "meta_description": f"Learn everything about {topic} in this comprehensive guide.",
            "tags": keywords + [topic.lower().replace(" ", "-")],
            "word_count": word_count,
            "reading_time": reading_time
        }
        
        # Store successful writing patterns
        self._store_writing_knowledge(task_type, parameters, result)
        
        return result
    
    async def _create_social_content(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Create social media content"""
        platform = parameters["platform"]
        message = parameters["message"]
        hashtags = parameters.get("hashtags", [])
        include_cta = parameters.get("include_cta", False)
        
        # Platform-specific constraints
        platform_limits = {
            "twitter": 280,
            "linkedin": 3000,
            "facebook": 2000,
            "instagram": 2200
        }
        
        char_limit = platform_limits.get(platform, 500)
        
        # Generate content (simulate)
        await asyncio.sleep(1)
        
        content = self._generate_social_content(message, platform, hashtags, include_cta, char_limit)
        
        result = {
            "content": content,
            "character_count": len(content),
            "hashtags": hashtags,
            "suggested_posting_time": self._get_optimal_posting_time(platform)
        }
        
        return result
    
    def _generate_blog_content(self, topic: str, keywords: List[str], 
                              tone: str, target_length: int) -> str:
        """Generate blog content (placeholder - use actual LLM in production)"""
        # This would call your chosen LLM API (OpenAI, Anthropic, etc.)
        sections = [
            f"## Introduction to {topic.title()}",
            f"## Understanding {topic}",
            f"## Key Benefits and Applications", 
            f"## Best Practices and Implementation",
            f"## Common Challenges and Solutions",
            f"## Conclusion"
        ]
        
        content_per_section = target_length // len(sections)
        content = "\n\n".join([
            f"{section}\n\n" + " ".join(["Content"] * (content_per_section // 8))
            for section in sections
        ])
        
        return content
    
    def _generate_social_content(self, message: str, platform: str, 
                               hashtags: List[str], include_cta: bool, char_limit: int) -> str:
        """Generate social media content"""
        # Platform-specific formatting
        if platform == "twitter":
            content = f"🔥 {message}"
        elif platform == "linkedin":
            content = f"💡 {message}\n\nWhat are your thoughts?"
        elif platform == "instagram":
            content = f"✨ {message} ✨"
        else:
            content = message
        
        # Add hashtags
        if hashtags:
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags])
            content += f"\n\n{hashtag_str}"
        
        # Add CTA
        if include_cta:
            cta_phrases = {
                "twitter": "What do you think? 💭",
                "linkedin": "Share your experience in the comments 👇",
                "instagram": "Double tap if you agree! ❤️",
                "facebook": "Let us know in the comments!"
            }
            content += f"\n\n{cta_phrases.get(platform, 'Share your thoughts!')}"
        
        # Trim if necessary
        if len(content) > char_limit:
            content = content[:char_limit-3] + "..."
        
        return content
    
    def _get_optimal_posting_time(self, platform: str) -> str:
        """Get optimal posting time for platform"""
        optimal_times = {
            "twitter": "9:00 AM or 3:00 PM",
            "linkedin": "8:00 AM or 12:00 PM", 
            "facebook": "1:00 PM or 3:00 PM",
            "instagram": "11:00 AM or 5:00 PM"
        }
        return optimal_times.get(platform, "12:00 PM")
    
    def _store_writing_knowledge(self, task_type: str, parameters: Dict[str, Any], 
                               result: Dict[str, Any]):
        """Store successful writing patterns"""
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            category="writing_patterns",
            content={
                "task_type": task_type,
                "input_params": parameters,
                "output_quality": self._assess_output_quality(result),
                "successful_techniques": self._extract_techniques(parameters, result)
            },
            metadata={
                "word_count": result.get("word_count", 0),
                "tone": parameters.get("tone"),
                "style": parameters.get("style"),
                "timestamp": datetime.now().isoformat()
            },
            created_at=datetime.now(),
            confidence=0.9
        )
        
        self.knowledge_manager.store_knowledge(knowledge)
    
    def _assess_output_quality(self, result: Dict[str, Any]) -> float:
        """Assess quality of writing output (simplified metric)"""
        # In production, this could use readability scores, 
        # engagement predictions, etc.
        base_score = 7.0
        
        if "word_count" in result:
            # Prefer moderate length content
            word_count = result["word_count"]
            if 800 <= word_count <= 2000:
                base_score += 1.0
            elif word_count < 400:
                base_score -= 1.0
        
        return min(10.0, base_score)
    
    def _extract_techniques(self, parameters: Dict[str, Any], 
                          result: Dict[str, Any]) -> List[str]:
        """Extract successful writing techniques"""
        techniques = []
        
        if parameters.get("keywords"):
            techniques.append("keyword_integration")
        
        if result.get("reading_time", 0) <= 5:
            techniques.append("concise_writing")
        
        if len(result.get("tags", [])) >= 3:
            techniques.append("comprehensive_tagging")
        
        return techniques
```

**Example: Social Media Management Agent**
```python
#!/usr/bin/env python3
"""
Social Media Management Agent
Handles scheduling, engagement, and analytics across platforms
"""

import asyncio
from typing import Dict, List, Any
from datetime import datetime, timedelta
import json

from base_agent import BaseAgent, AgentCapability

class SocialMediaAgent(BaseAgent):
    def __init__(self, agent_id: str, knowledge_manager, event_system,
                 platform_configs: Dict[str, Any] = None):
        super().__init__(agent_id, "social-media-manager", knowledge_manager, event_system)
        
        self.platform_configs = platform_configs or {
            "twitter": {"api_key": "xxx", "posting_limit": 50},
            "linkedin": {"api_key": "xxx", "posting_limit": 25},
            "facebook": {"api_key": "xxx", "posting_limit": 30},
            "instagram": {"api_key": "xxx", "posting_limit": 20}
        }
        
        self.scheduled_posts = {}
        self.engagement_queue = []
    
    def get_capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="schedule_post",
                description="Schedule content across social media platforms",
                input_schema={
                    "type": "object",
                    "properties": {
                        "platforms": {"type": "array", "items": {"type": "string"}},
                        "content": {"type": "string"},
                        "schedule_time": {"type": "string", "format": "date-time"},
                        "media_urls": {"type": "array", "items": {"type": "string"}},
                        "campaign_tag": {"type": "string"}
                    },
                    "required": ["platforms", "content", "schedule_time"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "post_ids": {"type": "array", "items": {"type": "string"}},
                        "scheduled_for": {"type": "string"},
                        "platforms": {"type": "array", "items": {"type": "string"}}
                    }
                }
            ),
            AgentCapability(
                name="monitor_engagement",
                description="Monitor and respond to social media engagement",
                input_schema={
                    "type": "object",
                    "properties": {
                        "platforms": {"type": "array", "items": {"type": "string"}},
                        "response_types": {"type": "array", "items": {"type": "string"}},
                        "auto_respond": {"type": "boolean", "default": False}
                    },
                    "required": ["platforms"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "engagement_summary": {"type": "object"},
                        "pending_responses": {"type": "array"},
                        "auto_responses_sent": {"type": "integer"}
                    }
                }
            ),
            AgentCapability(
                name="analyze_performance",
                description="Analyze social media performance and provide insights",
                input_schema={
                    "type": "object",
                    "properties": {
                        "time_period": {"type": "string", "enum": ["day", "week", "month"]},
                        "platforms": {"type": "array", "items": {"type": "string"}},
                        "metrics": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["time_period"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "performance_report": {"type": "object"},
                        "insights": {"type": "array", "items": {"type": "string"}},
                        "recommendations": {"type": "array", "items": {"type": "string"}}
                    }
                }
            )
        ]
    
    async def process_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Process social media management tasks"""
        if task_type == "schedule_post":
            return await self._schedule_post(parameters)
        elif task_type == "monitor_engagement":
            return await self._monitor_engagement(parameters)
        elif task_type == "analyze_performance":
            return await self._analyze_performance(parameters)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _schedule_post(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule posts across platforms"""
        platforms = parameters["platforms"]
        content = parameters["content"]
        schedule_time = parameters["schedule_time"]
        media_urls = parameters.get("media_urls", [])
        campaign_tag = parameters.get("campaign_tag")
        
        post_ids = []
        
        for platform in platforms:
            if platform not in self.platform_configs:
                self.logger.warning(f"Platform {platform} not configured")
                continue
            
            # Create platform-specific content
            platform_content = self._adapt_content_for_platform(content, platform)
            
            # Schedule the post (simulate API call)
            post_id = await self._schedule_platform_post(
                platform, platform_content, schedule_time, media_urls
            )
            
            if post_id:
                post_ids.append(post_id)
                
                # Store scheduled post
                self.scheduled_posts[post_id] = {
                    "platform": platform,
                    "content": platform_content,
                    "schedule_time": schedule_time,
                    "campaign_tag": campaign_tag,
                    "status": "scheduled"
                }
        
        # Store knowledge about successful scheduling
        self._store_scheduling_knowledge(parameters, post_ids)
        
        return {
            "post_ids": post_ids,
            "scheduled_for": schedule_time,
            "platforms": platforms
        }
    
    async def _monitor_engagement(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor social media engagement"""
        platforms = parameters["platforms"]
        response_types = parameters.get("response_types", ["comment", "mention", "dm"])
        auto_respond = parameters.get("auto_respond", False)
        
        engagement_summary = {}
        pending_responses = []
        auto_responses_sent = 0
        
        for platform in platforms:
            # Fetch recent engagement (simulate API call)
            engagement_data = await self._fetch_platform_engagement(platform)
            engagement_summary[platform] = engagement_data
            
            # Process engagement items
            for item in engagement_data.get("items", []):
                if item["type"] in response_types:
                    if auto_respond and self._should_auto_respond(item):
                        response = await self._generate_auto_response(item)
                        await self._send_response(platform, item["id"], response)
                        auto_responses_sent += 1
                    else:
                        pending_responses.append({
                            "platform": platform,
                            "type": item["type"],
                            "content": item["content"],
                            "user": item["user"],
                            "timestamp": item["timestamp"],
                            "suggested_response": await self._suggest_response(item)
                        })
        
        return {
            "engagement_summary": engagement_summary,
            "pending_responses": pending_responses,
            "auto_responses_sent": auto_responses_sent
        }
    
    def _adapt_content_for_platform(self, content: str, platform: str) -> str:
        """Adapt content for specific platform requirements"""
        adaptations = {
            "twitter": {
                "max_length": 280,
                "add_prefix": "🔥 ",
                "hashtag_style": "inline"
            },
            "linkedin": {
                "max_length": 3000,
                "add_prefix": "💡 ",
                "hashtag_style": "end"
            },
            "facebook": {
                "max_length": 2000,
                "add_prefix": "",
                "hashtag_style": "minimal"
            },
            "instagram": {
                "max_length": 2200,
                "add_prefix": "✨ ",
                "hashtag_style": "extensive"
            }
        }
        
        config = adaptations.get(platform, {})
        adapted_content = config.get("add_prefix", "") + content
        
        # Truncate if needed
        max_length = config.get("max_length", len(adapted_content))
        if len(adapted_content) > max_length:
            adapted_content = adapted_content[:max_length-3] + "..."
        
        return adapted_content
    
    async def _schedule_platform_post(self, platform: str, content: str, 
                                    schedule_time: str, media_urls: List[str]) -> str:
        """Schedule post on specific platform (simulate API call)"""
        await asyncio.sleep(0.5)  # Simulate API delay
        
        # In production, this would make actual API calls to:
        # - Twitter API v2
        # - LinkedIn API
        # - Facebook Graph API  
        # - Instagram Basic Display API
        
        post_id = f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.logger.info(f"Scheduled post {post_id} for {platform}")
        
        return post_id
    
    async def _fetch_platform_engagement(self, platform: str) -> Dict[str, Any]:
        """Fetch engagement data from platform"""
        await asyncio.sleep(0.3)  # Simulate API delay
        
        # Simulate engagement data
        return {
            "total_interactions": 156,
            "likes": 89,
            "comments": 23,
            "shares": 12,
            "mentions": 8,
            "items": [
                {
                    "id": f"item_{i}",
                    "type": "comment",
                    "content": f"Sample comment {i}",
                    "user": f"user_{i}",
                    "timestamp": datetime.now().isoformat(),
                    "sentiment": "positive"
                }
                for i in range(5)
            ]
        }
    
    def _should_auto_respond(self, engagement_item: Dict[str, Any]) -> bool:
        """Determine if item should get auto-response"""
        # Auto-respond to positive comments and simple questions
        sentiment = engagement_item.get("sentiment", "neutral")
        content = engagement_item.get("content", "").lower()
        
        if sentiment == "positive" and len(content.split()) <= 10:
            return True
            
        if any(word in content for word in ["thanks", "thank you", "great", "awesome"]):
            return True
            
        return False
    
    async def _generate_auto_response(self, engagement_item: Dict[str, Any]) -> str:
        """Generate automatic response"""
        content = engagement_item.get("content", "").lower()
        
        if any(word in content for word in ["thanks", "thank you"]):
            return "Thank you so much! We appreciate your support! 🙏"
        elif any(word in content for word in ["great", "awesome", "amazing"]):
            return "So glad you think so! Thanks for the positive feedback! 😊"
        elif "question" in content or "?" in content:
            return "Great question! We'll get back to you soon with more details."
        else:
            return "Thanks for engaging with our content! 💙"
    
    async def _suggest_response(self, engagement_item: Dict[str, Any]) -> str:
        """Suggest human response for complex engagement"""
        item_type = engagement_item.get("type")
        content = engagement_item.get("content", "")
        
        if item_type == "complaint":
            return "Thank you for bringing this to our attention. We'd like to help resolve this. Please send us a DM with more details."
        elif item_type == "question":
            return f"Thanks for your question about '{content[:50]}...'. Here's what we recommend: [provide specific answer]"
        else:
            return "Thank you for your engagement! We appreciate you being part of our community."
    
    def _store_scheduling_knowledge(self, parameters: Dict[str, Any], post_ids: List[str]):
        """Store knowledge about successful post scheduling"""
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            category="scheduling_patterns",
            content={
                "platforms": parameters["platforms"],
                "content_length": len(parameters["content"]),
                "schedule_success": len(post_ids) > 0,
                "platforms_reached": len(post_ids),
                "campaign_tag": parameters.get("campaign_tag")
            },
            metadata={
                "post_count": len(post_ids),
                "timestamp": datetime.now().isoformat()
            },
            created_at=datetime.now(),
            confidence=0.95
        )
        
        self.knowledge_manager.store_knowledge(knowledge)
```

### Step 2: Implement Agent Orchestration

**Orchestration Engine:**
```python
#!/usr/bin/env python3
"""
Agent Orchestration Engine
Coordinates complex multi-agent workflows and task distribution
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import uuid

from base_agent import BaseAgent
from event_system import EventSystem, Event, EventType, EventPriority
from knowledge_manager import KnowledgeManager

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class WorkflowStep:
    id: str
    agent_type: str
    task_type: str
    parameters: Dict[str, Any]
    dependencies: List[str] = None
    timeout: int = 300  # seconds
    retry_count: int = 3
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass 
class Workflow:
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = None
    started_at: datetime = None
    completed_at: datetime = None
    results: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.results is None:
            self.results = {}

class AgentOrchestrator:
    def __init__(self, event_system: EventSystem, knowledge_manager: KnowledgeManager):
        self.event_system = event_system
        self.knowledge_manager = knowledge_manager
        
        self.registered_agents: Dict[str, BaseAgent] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.active_workflows: Dict[str, Workflow] = {}
        self.workflow_templates: Dict[str, Workflow] = {}
        
        self.task_queue = asyncio.Queue()
        self.running = False
        
        # Register event handlers
        self._register_event_handlers()
    
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator"""
        self.registered_agents[agent.agent_id] = agent
        self.agent_capabilities[agent.agent_id] = [
            cap.name for cap in agent.get_capabilities()
        ]
        
        self.logger.info(f"Registered agent {agent.agent_id} with capabilities: {self.agent_capabilities[agent.agent_id]}")
    
    def register_workflow_template(self, template: Workflow):
        """Register a reusable workflow template"""
        self.workflow_templates[template.name] = template
        self.logger.info(f"Registered workflow template: {template.name}")
    
    async def start(self):
        """Start the orchestrator"""
        self.running = True
        
        # Start task processing loop
        asyncio.create_task(self._process_task_queue())
        
        self.logger.info("Agent orchestrator started")
    
    async def stop(self):
        """Stop the orchestrator"""
        self.running = False
        
        # Cancel active workflows
        for workflow_id in list(self.active_workflows.keys()):
            await self.cancel_workflow(workflow_id)
        
        self.logger.info("Agent orchestrator stopped")
    
    async def execute_workflow(self, workflow_name: str, 
                             parameters: Dict[str, Any] = None) -> str:
        """Execute a workflow from template"""
        if workflow_name not in self.workflow_templates:
            raise ValueError(f"Unknown workflow template: {workflow_name}")
        
        template = self.workflow_templates[workflow_name]
        
        # Create workflow instance
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=template.name,
            description=template.description,
            steps=[
                WorkflowStep(
                    id=str(uuid.uuid4()),
                    agent_type=step.agent_type,
                    task_type=step.task_type,
                    parameters={**step.parameters, **(parameters or {})},
                    dependencies=step.dependencies.copy(),
                    timeout=step.timeout,
                    retry_count=step.retry_count
                )
                for step in template.steps
            ]
        )
        
        # Start workflow execution
        await self._start_workflow(workflow)
        
        return workflow.id
    
    async def create_dynamic_workflow(self, workflow_spec: Dict[str, Any]) -> str:
        """Create and execute a dynamic workflow"""
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=workflow_spec["name"],
            description=workflow_spec.get("description", ""),
            steps=[
                WorkflowStep(
                    id=str(uuid.uuid4()),
                    **step_spec
                )
                for step_spec in workflow_spec["steps"]
            ]
        )
        
        await self._start_workflow(workflow)
        return workflow.id
    
    async def _start_workflow(self, workflow: Workflow):
        """Start workflow execution"""
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        
        self.active_workflows[workflow.id] = workflow
        
        # Find and execute ready steps
        await self._execute_ready_steps(workflow.id)
        
        self.logger.info(f"Started workflow {workflow.id}: {workflow.name}")
    
    async def _execute_ready_steps(self, workflow_id: str):
        """Execute workflow steps that have all dependencies met"""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow or workflow.status != WorkflowStatus.RUNNING:
            return
        
        for step in workflow.steps:
            if await self._is_step_ready(workflow, step):
                await self._execute_step(workflow, step)
    
    async def _is_step_ready(self, workflow: Workflow, step: WorkflowStep) -> bool:
        """Check if a workflow step is ready to execute"""
        # Check if step already completed
        if step.id in workflow.results:
            return False
        
        # Check if dependencies are met
        for dep_id in step.dependencies:
            if dep_id not in workflow.results:
                return False
        
        return True
    
    async def _execute_step(self, workflow: Workflow, step: WorkflowStep):
        """Execute a single workflow step"""
        # Find suitable agent
        agent = self._find_agent_for_task(step.agent_type, step.task_type)
        if not agent:
            self.logger.error(f"No agent found for step {step.id}: {step.agent_type}.{step.task_type}")
            await self._fail_workflow(workflow.id, f"No agent available for step {step.id}")
            return
        
        # Prepare parameters with dependency results
        step_parameters = step.parameters.copy()
        for dep_id in step.dependencies:
            if dep_id in workflow.results:
                step_parameters[f"dep_{dep_id}"] = workflow.results[dep_id]
        
        # Execute step with timeout and retry
        for attempt in range(step.retry_count):
            try:
                # Create task request event
                task_event = Event(
                    id=str(uuid.uuid4()),
                    type=EventType.TASK_REQUEST,
                    source="orchestrator",
                    target=agent.agent_id,
                    data={
                        "task_type": step.task_type,
                        "parameters": step_parameters,
                        "workflow_id": workflow.id,
                        "step_id": step.id,
                        "attempt": attempt + 1
                    }
                )
                
                # Send task and wait for completion
                self.event_system.publish(task_event)
                
                # Wait for result (implement timeout)
                result = await self._wait_for_step_result(workflow.id, step.id, step.timeout)
                
                if result:
                    workflow.results[step.id] = result
                    
                    # Check if workflow is complete
                    if len(workflow.results) == len(workflow.steps):
                        await self._complete_workflow(workflow.id)
                    else:
                        # Execute next ready steps
                        await self._execute_ready_steps(workflow.id)
                    
                    return
                    
            except Exception as e:
                self.logger.error(f"Step {step.id} attempt {attempt + 1} failed: {e}")
                if attempt == step.retry_count - 1:
                    await self._fail_workflow(workflow.id, f"Step {step.id} failed after {step.retry_count} attempts")
                    return
                
                # Wait before retry
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    def _find_agent_for_task(self, agent_type: str, task_type: str) -> Optional[BaseAgent]:
        """Find the best agent for a specific task"""
        # First, try to find agent with exact type match
        for agent_id, agent in self.registered_agents.items():
            if agent.agent_type == agent_type and task_type in self.agent_capabilities.get(agent_id, []):
                if agent.status == AgentStatus.IDLE:
                    return agent
        
        # Fall back to any agent that can handle the task
        for agent_id, agent in self.registered_agents.items():
            if task_type in self.agent_capabilities.get(agent_id, []):
                if agent.status == AgentStatus.IDLE:
                    return agent
        
        return None
    
    async def _wait_for_step_result(self, workflow_id: str, step_id: str, timeout: int) -> Dict[str, Any]:
        """Wait for step completion result"""
        # This would implement proper event waiting in production
        # For now, simulate async wait
        await asyncio.sleep(2)  # Simulate processing time
        
        # Return simulated result
        return {
            "success": True,
            "data": {"message": f"Step {step_id} completed successfully"},
            "timestamp": datetime.now().isoformat()
        }
    
    async def _complete_workflow(self, workflow_id: str):
        """Mark workflow as completed"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.now()
            
            # Store workflow knowledge
            self._store_workflow_knowledge(workflow)
            
            # Publish completion event
            completion_event = Event(
                id=str(uuid.uuid4()),
                type=EventType.TASK_COMPLETE,
                source="orchestrator",
                data={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.name,
                    "duration": (workflow.completed_at - workflow.started_at).total_seconds(),
                    "results": workflow.results
                }
            )
            self.event_system.publish(completion_event)
            
            self.logger.info(f"Completed workflow {workflow_id}: {workflow.name}")
    
    async def _fail_workflow(self, workflow_id: str, reason: str):
        """Mark workflow as failed"""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            
            # Publish failure event
            error_event = Event(
                id=str(uuid.uuid4()),
                type=EventType.ERROR_OCCURRED,
                source="orchestrator",
                data={
                    "workflow_id": workflow_id,
                    "workflow_name": workflow.name,
                    "failure_reason": reason,
                    "partial_results": workflow.results
                },
                priority=EventPriority.HIGH
            )
            self.event_system.publish(error_event)
            
            self.logger.error(f"Failed workflow {workflow_id}: {reason}")
    
    def _store_workflow_knowledge(self, workflow: Workflow):
        """Store knowledge about completed workflow"""
        duration = (workflow.completed_at - workflow.started_at).total_seconds() if workflow.completed_at else 0
        
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            agent_id="orchestrator",
            category="workflow_execution",
            content={
                "workflow_name": workflow.name,
                "step_count": len(workflow.steps),
                "execution_time": duration,
                "success_rate": 1.0 if workflow.status == WorkflowStatus.COMPLETED else 0.0,
                "agent_types_used": list(set(step.agent_type for step in workflow.steps))
            },
            metadata={
                "workflow_id": workflow.id,
                "status": workflow.status.value,
                "step_results": workflow.results
            },
            created_at=datetime.now(),
            confidence=0.9
        )
        
        self.knowledge_manager.store_knowledge(knowledge)
    
    def _register_event_handlers(self):
        """Register event handlers"""
        self.event_system.subscribe(
            EventType.TASK_COMPLETE,
            "orchestrator",
            self._handle_task_completion
        )
        
        self.event_system.subscribe(
            EventType.ERROR_OCCURRED,
            "orchestrator", 
            self._handle_task_error
        )
    
    async def _handle_task_completion(self, event: Event):
        """Handle task completion events"""
        workflow_id = event.data.get("workflow_id")
        step_id = event.data.get("step_id")
        
        if workflow_id and step_id and workflow_id in self.active_workflows:
            workflow = self.active_workflows[workflow_id]
            if step_id not in workflow.results:
                workflow.results[step_id] = event.data.get("result", {})
                
                # Continue workflow execution
                await self._execute_ready_steps(workflow_id)
    
    async def _handle_task_error(self, event: Event):
        """Handle task error events"""
        workflow_id = event.data.get("workflow_id")
        
        if workflow_id and workflow_id in self.active_workflows:
            reason = event.data.get("error", "Unknown error occurred")
            await self._fail_workflow(workflow_id, reason)
```

## Phase 4: Integration & External Connectivity

### Step 1: Create Integration Layer

**MCP Bridge for External Tools:**
```python
#!/usr/bin/env python3
"""
Model Context Protocol Bridge
Connects the multi-agent system to external tools and services
"""

import json
import sys
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Setup logging to file (never stdout - breaks MCP)
logging.basicConfig(
    filename='mcp_bridge.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class MCPBridge:
    def __init__(self, knowledge_manager, agent_orchestrator):
        self.knowledge_manager = knowledge_manager
        self.agent_orchestrator = agent_orchestrator
        self.server_info = {
            "name": "multi-agent-system-bridge",
            "version": "1.0.0"
        }
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from registered agents"""
        tools = []
        
        # Knowledge management tools
        tools.extend([
            {
                "name": "store_knowledge",
                "description": "Store knowledge in the system knowledge base",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Knowledge category"},
                        "content": {"type": "object", "description": "Knowledge content"},
                        "agent_id": {"type": "string", "description": "Source agent ID"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    },
                    "required": ["category", "content", "agent_id"]
                }
            },
            {
                "name": "retrieve_knowledge", 
                "description": "Retrieve knowledge from the system knowledge base",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Knowledge category to search"},
                        "agent_id": {"type": "string", "description": "Filter by agent ID"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                    }
                }
            }
        ])
        
        # Workflow execution tools
        tools.extend([
            {
                "name": "execute_workflow",
                "description": "Execute a predefined workflow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_name": {"type": "string", "description": "Name of workflow template"},
                        "parameters": {"type": "object", "description": "Workflow parameters"}
                    },
                    "required": ["workflow_name"]
                }
            },
            {
                "name": "create_dynamic_workflow",
                "description": "Create and execute a custom workflow",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_spec": {
                            "type": "object",
                            "description": "Complete workflow specification",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "steps": {"type": "array", "items": {"type": "object"}}
                            },
                            "required": ["name", "steps"]
                        }
                    },
                    "required": ["workflow_spec"]
                }
            }
        ])
        
        # Agent interaction tools
        tools.extend([
            {
                "name": "request_agent_task",
                "description": "Request a specific agent to perform a task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_type": {"type": "string", "description": "Type of agent to use"},
                        "task_type": {"type": "string", "description": "Type of task to perform"},
                        "parameters": {"type": "object", "description": "Task parameters"}
                    },
                    "required": ["agent_type", "task_type", "parameters"]
                }
            },
            {
                "name": "get_system_status",
                "description": "Get status of all agents and workflows",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_metrics": {"type": "boolean", "default": True},
                        "include_workflows": {"type": "boolean", "default": True}
                    }
                }
            }
        ])
        
        return tools
    
    async def handle_tool_call(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        try:
            if tool_name == "store_knowledge":
                return await self._store_knowledge(parameters)
            elif tool_name == "retrieve_knowledge":
                return await self._retrieve_knowledge(parameters)
            elif tool_name == "execute_workflow":
                return await self._execute_workflow(parameters)
            elif tool_name == "create_dynamic_workflow":
                return await self._create_dynamic_workflow(parameters)
            elif tool_name == "request_agent_task":
                return await self._request_agent_task(parameters)
            elif tool_name == "get_system_status":
                return await self._get_system_status(parameters)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
                
        except Exception as e:
            logging.error(f"Tool execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _store_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Store knowledge in the system"""
        from knowledge_manager import Knowledge
        
        knowledge = Knowledge(
            id=str(uuid.uuid4()),
            agent_id=parameters["agent_id"],
            category=parameters["category"],
            content=parameters["content"],
            metadata={
                "stored_via": "mcp_bridge",
                "timestamp": datetime.now().isoformat()
            },
            created_at=datetime.now(),
            confidence=parameters.get("confidence", 1.0),
            source="external_mcp"
        )
        
        knowledge_id = self.knowledge_manager.store_knowledge(knowledge)
        
        return {
            "success": True,
            "knowledge_id": knowledge_id,
            "message": "Knowledge stored successfully"
        }
    
    async def _retrieve_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve knowledge from the system"""
        knowledge_list = self.knowledge_manager.retrieve_knowledge(
            category=parameters.get("category"),
            agent_id=parameters.get("agent_id"),
            limit=parameters.get("limit", 20)
        )
        
        return {
            "success": True,
            "knowledge_count": len(knowledge_list),
            "knowledge": [
                {
                    "id": k.id,
                    "agent_id": k.agent_id,
                    "category": k.category,
                    "content": k.content,
                    "metadata": k.metadata,
                    "created_at": k.created_at.isoformat(),
                    "confidence": k.confidence
                }
                for k in knowledge_list
            ]
        }
    
    async def _execute_workflow(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow"""
        workflow_id = await self.agent_orchestrator.execute_workflow(
            parameters["workflow_name"],
            parameters.get("parameters", {})
        )
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "message": f"Workflow {parameters['workflow_name']} started"
        }
    
    async def _get_system_status(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Get system status"""
        include_metrics = parameters.get("include_metrics", True)
        include_workflows = parameters.get("include_workflows", True)
        
        status = {
            "timestamp": datetime.now().isoformat(),
            "agents": {}
        }
        
        # Get agent status
        for agent_id, agent in self.agent_orchestrator.registered_agents.items():
            agent_status = {
                "id": agent_id,
                "type": agent.agent_type,
                "status": agent.status.value,
                "capabilities": [cap.name for cap in agent.capabilities],
                "current_tasks": len(agent.current_tasks)
            }
            
            if include_metrics:
                agent_status["metrics"] = agent.performance_metrics
            
            status["agents"][agent_id] = agent_status
        
        # Get workflow status
        if include_workflows:
            status["workflows"] = {
                "active": len(self.agent_orchestrator.active_workflows),
                "templates": len(self.agent_orchestrator.workflow_templates),
                "active_details": [
                    {
                        "id": wf.id,
                        "name": wf.name,
                        "status": wf.status.value,
                        "progress": len(wf.results) / len(wf.steps) if wf.steps else 0
                    }
                    for wf in self.agent_orchestrator.active_workflows.values()
                ]
            }
        
        return {
            "success": True,
            "system_status": status
        }

# MCP Protocol Implementation
class MCPServer:
    def __init__(self, bridge: MCPBridge):
        self.bridge = bridge
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP protocol requests"""
        method = request.get("method", "")
        
        if method == "initialize":
            return {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": True}
                },
                "serverInfo": self.bridge.server_info
            }
        
        elif method == "tools/list":
            return {
                "tools": self.bridge.get_available_tools()
            }
        
        elif method == "tools/call":
            return asyncio.run(self._handle_tool_call(request))
        
        else:
            return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}
    
    async def _handle_tool_call(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool call requests"""
        params = request.get("params", {})
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        result = await self.bridge.handle_tool_call(tool_name, arguments)
        
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }
    
    def run(self):
        """Run the MCP server"""
        for line in sys.stdin:
            try:
                request = json.loads(line.strip())
                result = self.handle_request(request)
                
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id")
                }
                
                if "error" in result:
                    response["error"] = result["error"]
                else:
                    response["result"] = result
                
                print(json.dumps(response))
                sys.stdout.flush()
                
            except Exception as e:
                logging.error(f"Request handling error: {e}")

# Main entry point
if __name__ == "__main__":
    # Initialize system components
    from knowledge_manager import KnowledgeManager
    from agent_orchestrator import AgentOrchestrator
    from event_system import EventSystem
    
    event_system = EventSystem()
    knowledge_manager = KnowledgeManager()
    orchestrator = AgentOrchestrator(event_system, knowledge_manager)
    
    # Create and run MCP bridge
    bridge = MCPBridge(knowledge_manager, orchestrator)
    server = MCPServer(bridge)
    
    # Start system
    event_system.start()
    asyncio.run(orchestrator.start())
    
    # Run MCP server
    server.run()
```

### Step 2: Implement Monitoring & Health Checks

**System Monitoring:**
```python
#!/usr/bin/env python3
"""
System Monitoring and Health Management
Tracks performance, detects issues, and maintains system health
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics

@dataclass
class HealthMetric:
    name: str
    value: float
    unit: str
    timestamp: datetime
    threshold_warning: float = None
    threshold_critical: float = None
    
    @property
    def status(self) -> str:
        if self.threshold_critical and self.value >= self.threshold_critical:
            return "critical"
        elif self.threshold_warning and self.value >= self.threshold_warning:
            return "warning"
        else:
            return "healthy"

class SystemMonitor:
    def __init__(self, event_system, knowledge_manager, orchestrator):
        self.event_system = event_system
        self.knowledge_manager = knowledge_manager
        self.orchestrator = orchestrator
        
        self.metrics_history: Dict[str, List[HealthMetric]] = {}
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.monitoring_interval = 30  # seconds
        self.running = False
        
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default monitoring rules"""
        self.alert_rules = {
            "agent_failure_rate": {
                "threshold_warning": 0.1,  # 10% failure rate
                "threshold_critical": 0.25,  # 25% failure rate
                "window_minutes": 15
            },
            "workflow_completion_time": {
                "threshold_warning": 300,  # 5 minutes
                "threshold_critical": 900,  # 15 minutes
                "unit": "seconds"
            },
            "knowledge_storage_rate": {
                "threshold_warning": 100,  # operations per minute
                "threshold_critical": 500,
                "unit": "ops_per_minute"
            },
            "system_response_time": {
                "threshold_warning": 2.0,  # 2 seconds
                "threshold_critical": 5.0,  # 5 seconds
                "unit": "seconds"
            }
        }
    
    async def start_monitoring(self):
        """Start system monitoring"""
        self.running = True
        
        while self.running:
            try:
                await self._collect_metrics()
                await self._check_health()
                await self._cleanup_old_metrics()
                
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    def stop_monitoring(self):
        """Stop system monitoring"""
        self.running = False
    
    async def _collect_metrics(self):
        """Collect system metrics"""
        timestamp = datetime.now()
        
        # Agent performance metrics
        await self._collect_agent_metrics(timestamp)
        
        # Workflow metrics  
        await self._collect_workflow_metrics(timestamp)
        
        # Knowledge management metrics
        await self._collect_knowledge_metrics(timestamp)
        
        # System resource metrics
        await self._collect_system_metrics(timestamp)
    
    async def _collect_agent_metrics(self, timestamp: datetime):
        """Collect metrics from all agents"""
        total_agents = len(self.orchestrator.registered_agents)
        active_agents = 0
        total_tasks = 0
        failed_tasks = 0
        avg_task_times = []
        
        for agent in self.orchestrator.registered_agents.values():
            if agent.status != AgentStatus.OFFLINE:
                active_agents += 1
            
            metrics = agent.performance_metrics
            total_tasks += metrics["tasks_completed"]
            failed_tasks += metrics["tasks_failed"]
            
            if metrics["average_task_time"] > 0:
                avg_task_times.append(metrics["average_task_time"])
        
        # Store metrics
        self._store_metric("agents_total", total_agents, "count", timestamp)
        self._store_metric("agents_active", active_agents, "count", timestamp)
        
        if total_tasks > 0:
            failure_rate = failed_tasks / (total_tasks + failed_tasks)
            self._store_metric("agent_failure_rate", failure_rate, "ratio", timestamp,
                             self.alert_rules["agent_failure_rate"]["threshold_warning"],
                             self.alert_rules["agent_failure_rate"]["threshold_critical"])
        
        if avg_task_times:
            avg_response_time = statistics.mean(avg_task_times)
            self._store_metric("system_response_time", avg_response_time, "seconds", timestamp,
                             self.alert_rules["system_response_time"]["threshold_warning"],
                             self.alert_rules["system_response_time"]["threshold_critical"])
    
    async def _collect_workflow_metrics(self, timestamp: datetime):
        """Collect workflow performance metrics"""
        active_workflows = len(self.orchestrator.active_workflows)
        self._store_metric("workflows_active", active_workflows, "count", timestamp)
        
        # Get recent workflow completion times from knowledge
        recent_workflows = self.knowledge_manager.retrieve_knowledge(
            category="workflow_execution",
            limit=50
        )
        
        completion_times = []
        success_count = 0
        
        for workflow_knowledge in recent_workflows:
            content = workflow_knowledge.content
            execution_time = content.get("execution_time", 0)
            success_rate = content.get("success_rate", 0)
            
            if execution_time > 0:
                completion_times.append(execution_time)
            
            if success_rate > 0:
                success_count += 1
        
        if completion_times:
            avg_completion_time = statistics.mean(completion_times)
            self._store_metric("workflow_completion_time", avg_completion_time, "seconds", timestamp,
                             self.alert_rules["workflow_completion_time"]["threshold_warning"],
                             self.alert_rules["workflow_completion_time"]["threshold_critical"])
        
        if recent_workflows:
            workflow_success_rate = success_count / len(recent_workflows)
            self._store_metric("workflow_success_rate", workflow_success_rate, "ratio", timestamp)
    
    async def _collect_knowledge_metrics(self, timestamp: datetime):
        """Collect knowledge management metrics"""
        # This would require modifying KnowledgeManager to track operations
        # For now, simulate metrics
        knowledge_ops_per_minute = 15  # Placeholder
        
        self._store_metric("knowledge_storage_rate", knowledge_ops_per_minute, "ops_per_minute", timestamp,
                         self.alert_rules["knowledge_storage_rate"]["threshold_warning"],
                         self.alert_rules["knowledge_storage_rate"]["threshold_critical"])
    
    async def _collect_system_metrics(self, timestamp: datetime):
        """Collect system resource metrics"""
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self._store_metric("cpu_usage", cpu_percent, "percent", timestamp, 70, 90)
        
        # Memory usage
        memory = psutil.virtual_memory()
        self._store_metric("memory_usage", memory.percent, "percent", timestamp, 80, 95)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        self._store_metric("disk_usage", disk_percent, "percent", timestamp, 85, 95)
    
    def _store_metric(self, name: str, value: float, unit: str, timestamp: datetime,
                     threshold_warning: float = None, threshold_critical: float = None):
        """Store a metric value"""
        metric = HealthMetric(
            name=name,
            value=value,
            unit=unit,
            timestamp=timestamp,
            threshold_warning=threshold_warning,
            threshold_critical=threshold_critical
        )
        
        if name not in self.metrics_history:
            self.metrics_history[name] = []
        
        self.metrics_history[name].append(metric)
        
        # Keep only recent metrics (last 24 hours)
        cutoff_time = timestamp - timedelta(hours=24)
        self.metrics_history[name] = [
            m for m in self.metrics_history[name] 
            if m.timestamp > cutoff_time
        ]
    
    async def _check_health(self):
        """Check system health and trigger alerts"""
        alerts = []
        
        for metric_name, metrics in self.metrics_history.items():
            if not metrics:
                continue
            
            latest_metric = metrics[-1]
            
            if latest_metric.status != "healthy":
                alert = {
                    "metric": metric_name,
                    "value": latest_metric.value,
                    "unit": latest_metric.unit,
                    "status": latest_metric.status,
                    "timestamp": latest_metric.timestamp.isoformat(),
                    "message": self._generate_alert_message(latest_metric)
                }
                alerts.append(alert)
        
        # Send alerts if any
        if alerts:
            await self._send_alerts(alerts)
    
    def _generate_alert_message(self, metric: HealthMetric) -> str:
        """Generate human-readable alert message"""
        messages = {
            "agent_failure_rate": f"Agent failure rate is {metric.value:.1%}",
            "workflow_completion_time": f"Workflow completion time is {metric.value:.1f} seconds",
            "system_response_time": f"System response time is {metric.value:.1f} seconds",
            "cpu_usage": f"CPU usage is {metric.value:.1f}%",
            "memory_usage": f"Memory usage is {metric.value:.1f}%",
            "disk_usage": f"Disk usage is {metric.value:.1f}%"
        }
        
        return messages.get(metric.name, f"{metric.name} is {metric.value} {metric.unit}")
    
    async def _send_alerts(self, alerts: List[Dict[str, Any]]):
        """Send system alerts"""
        # Publish alert event
        from event_system import Event, EventType, EventPriority
        
        alert_event = Event(
            id=str(uuid.uuid4()),
            type=EventType.SYSTEM_STATUS,
            source="system_monitor",
            data={
                "alert_type": "health_check",
                "alerts": alerts,
                "timestamp": datetime.now().isoformat()
            },
            priority=EventPriority.HIGH
        )
        
        self.event_system.publish(alert_event)
        
        # Log alerts
        for alert in alerts:
            print(f"🚨 {alert['status'].upper()}: {alert['message']}")
    
    async def _cleanup_old_metrics(self):
        """Remove old metrics to prevent memory bloat"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for metric_name in self.metrics_history:
            self.metrics_history[metric_name] = [
                m for m in self.metrics_history[metric_name]
                if m.timestamp > cutoff_time
            ]
    
    def get_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive health report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "metrics": {},
            "alerts": []
        }
        
        critical_count = 0
        warning_count = 0
        
        for metric_name, metrics in self.metrics_history.items():
            if not metrics:
                continue
            
            latest_metric = metrics[-1]
            
            report["metrics"][metric_name] = {
                "current_value": latest_metric.value,
                "unit": latest_metric.unit,
                "status": latest_metric.status,
                "last_updated": latest_metric.timestamp.isoformat()
            }
            
            if latest_metric.status == "critical":
                critical_count += 1
                report["alerts"].append({
                    "severity": "critical",
                    "metric": metric_name,
                    "message": self._generate_alert_message(latest_metric)
                })
            elif latest_metric.status == "warning":
                warning_count += 1
                report["alerts"].append({
                    "severity": "warning", 
                    "metric": metric_name,
                    "message": self._generate_alert_message(latest_metric)
                })
        
        # Set overall status
        if critical_count > 0:
            report["overall_status"] = "critical"
        elif warning_count > 0:
            report["overall_status"] = "warning"
        
        report["summary"] = {
            "total_metrics": len(report["metrics"]),
            "critical_alerts": critical_count,
            "warning_alerts": warning_count
        }
        
        return report
```

## Phase 5: Deployment & Production

### Step 1: Create Deployment Scripts

**Production Deployment:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  multi-agent-system:
    build: .
    container_name: multi-agent-system
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - KNOWLEDGE_DB_PATH=/data/knowledge.db
      - MAX_AGENTS=50
      - MONITORING_ENABLED=true
    volumes:
      - ./data:/data
      - ./logs:/app/logs
    ports:
      - "8000:8000"  # API port
      - "5001:5001"  # MCP bridge port
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "health_check.py"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  monitoring:
    image: grafana/grafana:latest
    container_name: monitoring-dashboard
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin_password_here
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    restart: unless-stopped

  redis:
    image: redis:alpine
    container_name: event-queue
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped

volumes:
  grafana-data:
  redis-data:
```

**Installation Script:**
```bash
#!/bin/bash
# install.sh - Production installation script

set -e

echo "🚀 Installing Multi-Agent System..."

# Check requirements
check_requirements() {
    echo "📋 Checking system requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker is required but not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo "❌ Docker Compose is required but not installed"
        exit 1
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo "❌ Python 3.8+ is required but not installed"
        exit 1
    fi
    
    echo "✅ All requirements satisfied"
}

# Setup directories
setup_directories() {
    echo "📁 Setting up directories..."
    
    mkdir -p data
    mkdir -p logs
    mkdir -p config
    mkdir -p monitoring/grafana
    
    echo "✅ Directories created"
}

# Generate configuration
generate_config() {
    echo "⚙️ Generating configuration..."
    
    cat > config/system.json << EOF
{
    "system": {
        "name": "multi-agent-system",
        "version": "1.0.0",
        "environment": "production"
    },
    "agents": {
        "max_concurrent": 50,
        "default_timeout": 300,
        "retry_attempts": 3
    },
    "knowledge_manager": {
        "db_path": "/data/knowledge.db",
        "max_history": 10000,
        "cleanup_interval": 3600
    },
    "monitoring": {
        "enabled": true,
        "interval": 30,
        "retention_hours": 168
    },
    "security": {
        "api_key_required": true,
        "rate_limiting": true,
        "max_requests_per_minute": 100
    }
}
EOF
    
    echo "✅ Configuration generated"
}

# Build and start services
deploy_services() {
    echo "🏗️ Building and starting services..."
    
    # Build the main application
    docker-compose build
    
    # Start all services
    docker-compose up -d
    
    # Wait for services to be ready
    echo "⏳ Waiting for services to start..."
    sleep 30
    
    # Check health
    if docker-compose ps | grep -q "unhealthy"; then
        echo "❌ Some services failed to start properly"
        docker-compose logs
        exit 1
    fi
    
    echo "✅ All services started successfully"
}

# Setup monitoring
setup_monitoring() {
    echo "📊 Setting up monitoring..."
    
    # Create Grafana dashboard config
    cat > monitoring/grafana/dashboards.yml << EOF
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /etc/grafana/provisioning/dashboards
EOF
    
    # Create basic dashboard
    cat > monitoring/grafana/multi-agent-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "Multi-Agent System Dashboard",
    "panels": [
      {
        "title": "Active Agents",
        "type": "stat",
        "fieldConfig": {
          "defaults": {
            "unit": "short"
          }
        }
      },
      {
        "title": "Workflow Success Rate",
        "type": "stat", 
        "fieldConfig": {
          "defaults": {
            "unit": "percent"
          }
        }
      }
    ]
  }
}
EOF
    
    echo "✅ Monitoring configured"
}

# Run installation
main() {
    echo "🔧 Multi-Agent System Installation"
    echo "=================================="
    
    check_requirements
    setup_directories
    generate_config
    setup_monitoring
    deploy_services
    
    echo ""
    echo "🎉 Installation completed successfully!"
    echo ""
    echo "📖 Next Steps:"
    echo "  1. Access the system at: http://localhost:8000"
    echo "  2. View monitoring at: http://localhost:3000 (admin/admin_password_here)"
    echo "  3. Check logs with: docker-compose logs -f"
    echo "  4. Stop system with: docker-compose down"
    echo ""
    echo "📚 Documentation: ./docs/"
    echo "🔧 Configuration: ./config/system.json"
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

### Step 2: Create Operational Tools

**Health Check Script:**
```python
#!/usr/bin/env python3
"""
Health Check Script for Multi-Agent System
Used by Docker healthcheck and monitoring systems
"""

import requests
import json
import sys
import os
from datetime import datetime

def check_system_health():
    """Perform comprehensive system health check"""
    health_report = {
        "timestamp": datetime.now().isoformat(),
        "status": "healthy",
        "checks": {}
    }
    
    # Check API availability
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_report["checks"]["api"] = {"status": "healthy", "response_time": response.elapsed.total_seconds()}
        else:
            health_report["checks"]["api"] = {"status": "unhealthy", "error": f"HTTP {response.status_code}"}
            health_report["status"] = "unhealthy"
    except Exception as e:
        health_report["checks"]["api"] = {"status": "unhealthy", "error": str(e)}
        health_report["status"] = "unhealthy"
    
    # Check MCP bridge
    try:
        # This would test MCP connection
        health_report["checks"]["mcp_bridge"] = {"status": "healthy"}
    except Exception as e:
        health_report["checks"]["mcp_bridge"] = {"status": "unhealthy", "error": str(e)}
        health_report["status"] = "unhealthy"
    
    # Check knowledge database
    if os.path.exists("/data/knowledge.db"):
        health_report["checks"]["knowledge_db"] = {"status": "healthy"}
    else:
        health_report["checks"]["knowledge_db"] = {"status": "unhealthy", "error": "Database file not found"}
        health_report["status"] = "unhealthy"
    
    # Output results
    print(json.dumps(health_report, indent=2))
    
    # Exit with appropriate code
    if health_report["status"] == "healthy":
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    check_system_health()
```

**Backup Script:**
```bash
#!/bin/bash
# backup.sh - Automated backup script

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="multi_agent_system_backup_${TIMESTAMP}"

echo "🔄 Starting backup: $BACKUP_NAME"

# Create backup directory
mkdir -p "$BACKUP_DIR/$BACKUP_NAME"

# Backup knowledge database
echo "📊 Backing up knowledge database..."
cp /data/knowledge.db "$BACKUP_DIR/$BACKUP_NAME/"

# Backup configuration
echo "⚙️ Backing up configuration..."
cp -r config/ "$BACKUP_DIR/$BACKUP_NAME/"

# Backup logs (last 7 days)
echo "📋 Backing up recent logs..."
find logs/ -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/$BACKUP_NAME/" \;

# Create backup manifest
echo "📄 Creating backup manifest..."
cat > "$BACKUP_DIR/$BACKUP_NAME/manifest.json" << EOF
{
    "backup_name": "$BACKUP_NAME",
    "timestamp": "$(date -Iseconds)",
    "version": "1.0.0",
    "contents": [
        "knowledge.db",
        "config/",
        "logs/"
    ],
    "size_mb": $(du -sm "$BACKUP_DIR/$BACKUP_NAME" | cut -f1)
}
EOF

# Compress backup
echo "🗜️ Compressing backup..."
cd "$BACKUP_DIR"
tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

echo "✅ Backup completed: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo "📊 Size: $(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)"

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "multi_agent_system_backup_*.tar.gz" -mtime +30 -delete

echo "🧹 Cleaned up old backups"
```

## Summary

This guide provides a complete framework for building autonomous multi-agent systems that can be applied to any domain. The key components include:

**Core Infrastructure:**
- Knowledge Management System for shared learning
- Event-Driven Architecture for coordination
- Base Agent Framework for consistent behavior
- Orchestration Engine for complex workflows

**Specialized Agents:**
- Domain-specific implementations
- Capability-based task routing
- Performance tracking and optimization
- Error handling and recovery

**Integration & Operations:**
- MCP Bridge for external tool access
- Monitoring and health management
- Production deployment scripts
- Backup and maintenance tools

**Key Success Factors:**
1. **Start Simple**: Begin with a few agents and basic workflows
2. **Design for Growth**: Plan architecture to scale with new agents
3. **Monitor Everything**: Track performance and detect issues early
4. **Automate Operations**: Reduce manual intervention where possible
5. **Document Thoroughly**: Maintain clear documentation for all components

This framework can be adapted for any domain by:
- Defining domain-specific agent types
- Creating relevant workflow templates
- Implementing domain-specific knowledge categories
- Adding external integrations for your tools and services

The result is a robust, scalable system that can handle complex multi-step tasks with minimal human oversight while maintaining high quality and reliability standards.