# Claude Super-Agents 🤖 - Autonomous Engineering Team

**Transform Claude Code into a multi-agent engineering team with 12 specialized AI agents**

[![GitHub](https://img.shields.io/github/license/mkritter3/claude-super-agents)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)

## 🌟 What is Claude Super-Agents?

Claude Super-Agents (AET - Autonomous Engineering Team) is a production-ready orchestration system that enables Claude Code to delegate complex tasks to specialized AI agents. Each agent has specific expertise and responsibilities, working together to handle planning, architecture, development, review, testing, and integration autonomously.

## ✨ Key Features

- **12 Specialized Agents**: Each with defined roles and optimal model assignments
- **Event-Sourced Architecture**: Full audit trail and state recovery
- **Dual-Mode Operation**: Fast simple mode or comprehensive full mode
- **Production Ready**: Circuit breakers, fallback systems, resource management
- **One-Command Setup**: Global `super-agents` command for instant project setup
- **Project Isolation**: Each project gets its own independent AET system
- **Enterprise Observability**: Prometheus metrics, OpenTelemetry tracing

## 🚀 Quick Install

### Option 1: Global Command (Recommended)

```bash
# Clone the repository
git clone https://github.com/mkritter3/claude-super-agents.git
cd claude-super-agents

# Install the global command
sudo ./install-global.sh

# Now from ANY project directory:
super-agents
```

### Option 2: Manual Setup

```bash
# Clone into your project
git clone https://github.com/mkritter3/claude-super-agents.git
cd claude-super-agents

# Run setup
./setup.sh

# Start the system
./start.sh
```

## 🎯 Usage

### With Global Command

```bash
# In any project directory
super-agents              # Sets up agents and launches Claude
super-agents --upgrade    # Upgrade existing agents
super-agents --stop       # Stop services
super-agents --help       # Show help
```

### Direct AET Commands

```bash
# Create tasks
./.claude/aet create "Build user authentication system"
./.claude/aet create "Fix bug in payment processing" --mode simple

# Process tasks
./.claude/aet process           # Process all pending tasks
./.claude/aet process --parallel # Process in parallel
./.claude/aet process --simple   # Use simple mode

# Monitor
./.claude/aet status    # View system status
./.claude/aet health    # Check system health
./.claude/aet metrics   # View performance metrics
```

## 🤖 The Agent Team

| Agent | Model | Responsibility |
|-------|-------|----------------|
| **pm-agent** | Sonnet | Project planning and task decomposition |
| **architect-agent** | Sonnet | System design and technical architecture |
| **developer-agent** | Sonnet | Code implementation |
| **reviewer-agent** | Sonnet | Code review and quality assurance |
| **contract-guardian** | Sonnet | API/DB contract protection |
| **test-executor** | Sonnet | Test execution and analysis |
| **builder-agent** | Sonnet | AET system implementation |
| **dependency-agent** | Haiku | Package and dependency management |
| **filesystem-guardian** | Haiku | Security and path validation |
| **integration-tester** | Haiku | Cross-package testing |
| **integrator-agent** | Haiku | Workspace merging |
| **verifier-agent** | Haiku | Consistency auditing |

## 🏗️ System Architecture

```
Event-Sourced Core
├── Event Logger (Append-only log)
├── State Manager (Transactional snapshots)
└── Recovery System (Rebuild from events)

Context Integration Layer
├── Knowledge Manager (Semantic search)
├── File Registry (Dependency tracking)
└── Context Assembler (Agent-specific context)

Orchestration Engine
├── Full Mode (Complete workflow)
├── Simple Mode (Lightweight tasks)
└── Parallel Processor (Concurrent execution)

Safety Systems
├── Circuit Breakers (Fault tolerance)
├── Resource Manager (CPU/Memory limits)
└── Rollback System (State recovery)
```

## 📋 Features in Detail

### Event Sourcing
- Immutable append-only event log
- Complete audit trail of all actions
- State recovery from any point in time
- Transactional integrity with three-phase commits

### Intelligent Context
- Agent-specific context assembly
- Semantic search integration
- Dependency graph analysis
- Smart file loading within token budgets

### Production Safety
- Circuit breakers for service failures
- Graceful degradation with fallback modes
- Resource limits and queuing
- Comprehensive error handling

### Observability
- Structured JSON logging throughout
- Prometheus-compatible metrics
- OpenTelemetry distributed tracing
- Health monitoring endpoints
- Grafana dashboard templates

## 🔧 Configuration

The system is configured through:
- `.claude/config.json` - System configuration
- `CLAUDE.md` - Orchestration instructions
- `.claude/agents/*.md` - Agent definitions

## 📚 Documentation

- [Architecture Overview](docs/AET-UPGRADE-COMPLETE.md)
- [Agent Specifications](docs/AGENT-UPGRADES.md)
- [Phase Implementation](docs/phase-completions/)
- [Upgrade Status](UPGRADE-STATUS.md)

## 🧪 Testing

Comprehensive test suites for all components:

```bash
# Run all tests
python3 .claude/tests/phase0/run_phase0_tests.py
python3 .claude/tests/phase1/run_all_tests.py
python3 .claude/tests/phase2/run_all_tests.py
python3 .claude/tests/phase3/run_all_tests.py
python3 .claude/tests/phase4/run_all_tests.py
```

## 🛠️ Requirements

- Python 3.8+
- SQLite3
- Git
- Claude Code CLI

Python packages (auto-installed):
- structlog (structured logging)
- psutil (resource monitoring)
- prometheus-client (metrics)
- opentelemetry (tracing)
- gunicorn (production server)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

## 📜 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

Built with Claude Code by the Anthropic team and enhanced through iterative development with Claude.

---

**Ready to transform Claude Code into a full engineering team?**

```bash
git clone https://github.com/mkritter3/claude-super-agents.git && cd claude-super-agents && sudo ./install-global.sh
```

Then from any project: `super-agents` 🚀