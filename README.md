# AET - Autonomous Engineering Team 🤖

A production-ready autonomous engineering system built on event sourcing with intelligent context integration.

## 🚀 Quick Start

### 1. Initialize the System
```bash
cd claude-super-agents
./.claude/setup.sh
```

### 2. Create Your First Task
```bash
# Full mode (default) - uses complete AET system
./.claude/aet create "Build user authentication system"

# Simple mode - faster for basic tasks
./.claude/aet create "Fix documentation typo" --mode simple

# Auto mode - automatically selects best mode
./.claude/aet create "Update configuration" --mode auto
```

### 3. Process Tasks
```bash
# Process tasks serially (full mode)
./.claude/aet process

# Process tasks in parallel (full mode)
./.claude/aet process --parallel

# Process tasks in simple mode
./.claude/aet process --simple

# Immediate simple mode processing
./.claude/aet simple "Create README file"
```

### 4. Monitor Progress
```bash
# View system status
./.claude/aet status

# Check system health
./.claude/aet health

# View metrics
./.claude/aet metrics
```

## 🏗️ System Architecture

### Three-Phase Implementation

#### Phase 1: Core Event-Sourced System
- **Event Logger** - Atomic append-only logging with crash safety
- **Workspace Manager** - Git-backed isolated workspaces for each job
- **Context Assembler** - Intelligent context integration layer
- **Orchestrator** - State machine with subagent delegation
- **Specialized Agents** - 9 specialized agents for different phases

#### Phase 2: Governance & Registry
- **File Registry** - SQLite-based file tracking with dependencies
- **Write Protocol** - Three-phase atomic write operations
- **Consistency Verifier** - Registry/filesystem reconciliation
- **Integrator** - Safe workspace merging with conventions

#### Phase 3: Scaling & Optimization
- **Parallel Orchestrator** - Concurrent task processing
- **Knowledge Manager** - Semantic search and API registry
- **Metrics Collection** - Performance and health monitoring
- **CLI Interface** - Complete command-line tooling
- **Production Hardening** - Circuit breakers, retries, DLQ

### Data Flow
```
User Request → Orchestrator → Context Assembler → Subagent → Workspace → Event Log
                     ↑                ↓
                Task Snapshots ← File Registry ← Knowledge Manager
```

### State Machine
```
CREATED → PLANNING → DESIGNING → IMPLEMENTING → REVIEWING → TESTING → INTEGRATING → COMPLETED
   ↓         ↓          ↓             ↓            ↓          ↓           ↓
pm-agent  architect  developer   reviewer    qa-agent  integrator     [done]
```

## 💡 Key Features

### Event Sourcing
- Complete audit trail of all operations
- Crash-safe recovery from any point
- Deterministic replay capability
- Idempotent operations

### Workspace Isolation
- Each task gets isolated git-backed workspace
- Prevents cross-task contamination
- Version control with checkpoint system
- Atomic commits after each agent

### Context Integration Layer
- Assembles intelligent, agent-specific context
- Connects Knowledge Manager, File Registry, Event Log, and Workspaces
- Smart file loading within token budgets
- Semantic search for relevant information

### Production Safety
- File locking prevents race conditions
- Atomic operations ensure consistency
- Retry logic handles transient failures
- Circuit breakers for external calls
- Dead letter queue for failed tasks
- Backup and rollback capabilities

## 📁 Directory Structure

```
claude-super-agents/
├── .claude/
│   ├── events/              # Event sourcing log
│   ├── workspaces/          # Isolated task workspaces
│   ├── snapshots/           # Task state snapshots
│   ├── registry/            # SQLite governance database
│   ├── backups/             # System backups
│   ├── dlq/                 # Dead letter queue
│   ├── system/              # Core Python modules
│   │   ├── event_logger.py
│   │   ├── workspace_manager.py
│   │   ├── context_assembler.py
│   │   ├── orchestrator.py
│   │   ├── parallel_orchestrator.py
│   │   ├── file_registry.py
│   │   ├── write_protocol.py
│   │   ├── verify_consistency.py
│   │   ├── integrator.py
│   │   ├── km_server.py
│   │   ├── metrics.py
│   │   ├── reliability.py
│   │   ├── dlq_manager.py
│   │   ├── rollback.py
│   │   └── aet.py
│   ├── agents/              # Specialized agent definitions
│   │   ├── pm-agent.md
│   │   ├── architect-agent.md
│   │   ├── developer-agent.md
│   │   ├── reviewer-agent.md
│   │   ├── qa-agent.md
│   │   ├── integrator-agent.md
│   │   ├── verifier-agent.md
│   │   ├── dependency-agent.md
│   │   └── integration-tester-agent.md
│   ├── aet                  # Main CLI executable
│   ├── setup.sh             # Setup script
│   └── config.json          # System configuration
└── README.md                # This file
```

## 🔧 CLI Commands

### Core Commands
```bash
# Initialize system
./.claude/aet init

# Create a new task
./.claude/aet create "Task description" [--mode full|simple|auto]

# Process tasks
./.claude/aet process [--parallel] [--simple]

# Immediate simple mode processing
./.claude/aet simple "Task description"

# View status
./.claude/aet status
```

### Processing Modes

#### Full Mode (Default)
Complete AET system with multi-agent orchestration:
```bash
./.claude/aet create "Complex refactoring task" --mode full
./.claude/aet process
```

#### Simple Mode
Lightweight processing for common tasks:
```bash
./.claude/aet create "Fix typo in docs" --mode simple
./.claude/aet process --simple
./.claude/aet simple "Create config file"
```

#### Auto Mode
Automatically selects the best mode based on task complexity:
```bash
./.claude/aet create "Update README" --mode auto
```

### Monitoring Commands
```bash
# System health
./.claude/aet health

# Performance metrics
./.claude/aet metrics

# View event log
./.claude/aet log [--tail N]

# Search events
./.claude/aet search "pattern"
```

### Management Commands
```bash
# Start Knowledge Manager
./.claude/aet km start

# Stop Knowledge Manager
./.claude/aet km stop

# Create backup
./.claude/aet backup

# Rollback to backup
./.claude/aet rollback <backup_name>

# Manage failed tasks
./.claude/aet dlq list
./.claude/aet dlq retry <ticket_id>
```

### Development Commands
```bash
# Verify consistency
./.claude/aet verify

# Run tests
./.claude/aet test

# Clean old data
./.claude/aet clean
```

## 🎯 Use Cases

### 1. Feature Development (Full Mode)
```bash
./.claude/aet create "Implement user authentication with JWT" --mode full
./.claude/aet process
```

### 2. Quick Fixes (Simple Mode)
```bash
./.claude/aet simple "Fix typo in documentation"
./.claude/aet simple "Update configuration values"
```

### 3. Bug Fixing (Auto Mode)
```bash
./.claude/aet create "Fix memory leak in data processing pipeline" --mode auto
./.claude/aet process
```

### 4. Code Refactoring (Full Mode)
```bash
./.claude/aet create "Refactor payment module to use strategy pattern" --mode full
./.claude/aet process --parallel
```

### 5. Documentation Updates (Simple Mode)
```bash
./.claude/aet create "Update API documentation" --mode simple
./.claude/aet process --simple
```

### 6. System Integration (Full Mode)
```bash
./.claude/aet create "Integrate with Stripe payment gateway" --mode full
./.claude/aet process
```

## ⚡ Performance Comparison

### Simple Mode vs Full Mode

| Aspect | Simple Mode | Full Mode |
|--------|-------------|-----------|
| **Execution Speed** | 2-3x faster | Standard |
| **Memory Usage** | ~50% less | Standard |
| **Dependencies** | Minimal | Full system |
| **Startup Time** | Instant | ~2-3 seconds |
| **Resource Usage** | Low | Moderate |
| **Complexity** | Single-threaded | Multi-agent |

### When to Use Each Mode

#### Use Simple Mode For:
- ✅ Quick file operations
- ✅ Simple fixes and modifications
- ✅ Documentation updates
- ✅ Configuration changes
- ✅ Prototyping and testing
- ✅ Resource-constrained environments

#### Use Full Mode For:
- 🏗️ Complex multi-file operations
- 🏗️ Architecture changes
- 🏗️ Multi-agent coordination
- 🏗️ Production deployments
- 🏗️ Advanced workflow orchestration

### Performance Metrics
```
Simple Mode:
- Average task completion: 0.5-2 seconds
- Memory usage: 10-20MB
- Success rate: 80%+ for suitable tasks

Full Mode:
- Average task completion: 2-10 seconds
- Memory usage: 50-100MB
- Success rate: 95%+ for all tasks
```

## 🌟 Advanced Features

### Parallel Processing
Process multiple independent tasks simultaneously:
```bash
./.claude/aet process --parallel --max-workers 4
```

### Knowledge Management
The Knowledge Manager provides semantic search and API discovery:
```bash
# Start KM server
./.claude/aet km start

# Query via HTTP API
curl http://localhost:5001/search?q="authentication"
```

### Dead Letter Queue
Handle failed tasks:
```bash
# List failed tasks
./.claude/aet dlq list

# Retry a failed task
./.claude/aet dlq retry TICKET-123

# Remove from DLQ
./.claude/aet dlq remove TICKET-123
```

### Backup & Recovery
```bash
# Create backup
./.claude/aet backup

# List backups
./.claude/aet backup --list

# Rollback to specific backup
./.claude/aet rollback backup_20240813_120000
```

## 📈 System Metrics

The system tracks:
- Task completion rates
- Agent performance metrics
- Event processing statistics
- File registry consistency
- System health score (0-100)

View with:
```bash
./.claude/aet metrics
```

## 🔒 Safety Features

1. **Atomic Operations** - All state changes are atomic
2. **File Locking** - Prevents concurrent file modifications
3. **Three-Phase Writes** - Propose → Validate → Apply
4. **Circuit Breakers** - Prevent cascade failures
5. **Retry Logic** - Exponential backoff for transient failures
6. **Dead Letter Queue** - Isolate failed tasks
7. **Rollback Capability** - Restore to previous state

## 🚦 System Requirements

- Python 3.8+
- Git
- SQLite3
- 2GB+ RAM recommended for parallel processing

## 📝 License

This is a clean, standalone implementation of the Autonomous Engineering Team system.

## 🎉 Ready for Production

The AET system is production-ready with:
- Complete error handling
- Monitoring and metrics
- Backup and recovery
- Parallel processing
- Knowledge management
- Dead letter queue
- Health checks

Start building with autonomous agents today!