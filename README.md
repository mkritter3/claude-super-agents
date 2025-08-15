# Claude Super-Agents 🤖 - Autonomous Engineering Team

**Transform Claude Code into a fully autonomous engineering team with 17 specialized AI agents, autonomous operations, and comprehensive safety nets**

[![GitHub](https://img.shields.io/github/license/mkritter3/claude-super-agents)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)

## 🌟 What is Claude Super-Agents?

Claude Super-Agents (AET - Autonomous Engineering Team) is a **production-ready autonomous engineering system** that transforms Claude Code into a complete software engineering organization. It features 17 specialized AI agents, autonomous operations through git hooks, comprehensive safety nets, and true autonomous intelligence that works **without constant human supervision**.

### 🎯 **Core Innovation: True Autonomy**

Unlike traditional automation, this system achieves **true autonomy** through:
- **File System as Message Bus**: Agents communicate through structured file events
- **Hooks as Daemon Substitutes**: Git hooks trigger autonomous operations
- **Natural Language as Control Plane**: AI translates technical events into actionable prompts

## 🚀 **Three Operational Modes Working Simultaneously**

### 1. **Explicit Mode** - User asks → agents respond
```bash
user: "Deploy the user service"
→ pm-agent plans → architect-agent designs → developer-agent implements
```

### 2. **Implicit Mode** - User acts → agents infer needs  
```bash
user: git commit -m "Fix authentication bug"
→ Hooks detect code changes → test-executor runs tests → documentation-agent updates docs
```

### 3. **Ambient Mode** - System self-monitors → self-heals
```bash
Error rate spike detected → incident-response-agent investigates → Auto-rollback if needed
```

## 🛡️ **Autonomous Safety Net**

The system includes **6 operational agents** that work autonomously to prevent production issues:

- **🔒 contract-guardian**: Prevents API/schema breaking changes before they reach production
- **🧪 test-executor**: Automatic quality gates and test execution  
- **📊 monitoring-agent**: Auto-configures observability for deployments
- **📚 documentation-agent**: Maintains documentation automatically
- **🔄 data-migration-agent**: Safe schema evolution and migrations
- **⚡ performance-optimizer-agent**: Continuous performance analysis

## 🤖 **Complete Agent Team (17 Specialists)**

### **Core Engineering Agents**
| Agent | Model | Responsibility |
|-------|-------|----------------|
| **pm-agent** | Sonnet | Project planning and task decomposition |
| **architect-agent** | Sonnet | System design and technical architecture |
| **developer-agent** | Sonnet | Code implementation |
| **reviewer-agent** | Sonnet | Code review and quality assurance |
| **integrator-agent** | Sonnet | Safe merging and integration |

### **Operational Agents (Autonomous)**
| Agent | Model | Triggers | Purpose |
|-------|-------|----------|---------|
| **contract-guardian** | Sonnet | Schema/API changes | Prevent breaking changes |
| **test-executor** | Sonnet | Code commits | Quality gate automation |
| **monitoring-agent** | Sonnet | Deployments | Auto-observability setup |
| **documentation-agent** | Sonnet | Code changes | Maintain documentation |
| **data-migration-agent** | Sonnet | Schema changes | Safe data evolution |
| **performance-optimizer-agent** | Sonnet | Performance issues | Continuous optimization |
| **incident-response-agent** | Haiku | Error spikes | Autonomous incident handling |

### **Infrastructure Agents**
| Agent | Model | Responsibility |
|-------|-------|----------------|
| **builder-agent** | Sonnet | AET system implementation |
| **dependency-agent** | Sonnet | Package and dependency management |
| **filesystem-guardian** | Haiku | Security and path validation |
| **integration-tester** | Haiku | Cross-package testing |
| **verifier-agent** | Haiku | Consistency auditing |

## 🏗️ **Autonomous Architecture**

### **Event-Sourced Core**
```
Event Stream (.claude/events/log.ndjson)
├── All agent actions logged immutably
├── Complete audit trail and replay capability  
└── State recovery from any point in time

File System Message Bus
├── .claude/triggers/ → Agent trigger files
├── .claude/state/ → Shared operational state
└── .claude/ambient/ → Continuous monitoring state
```

### **Autonomous Integration Points**
```
Git Hooks (Daemon Substitutes)
├── pre-commit → Secret detection (security)
├── post-commit → Operational triggers (quality/docs/monitoring)
└── post-merge → Deployment readiness validation

Ambient Operations Framework
├── 8 intelligent rules for self-monitoring
├── Performance degradation detection
└── Error spike response automation

Claude Bridge (Natural Language Control)
├── Technical event → Natural language translation
├── Operational context injection
└── Proactive prompt generation
```

## 🚀 **Quick Install & Usage**

### **Option 1: Global Command (Recommended)**

```bash
# Clone and install globally
git clone https://github.com/mkritter3/claude-super-agents.git
cd claude-super-agents
sudo ./install-global.sh

# Use from ANY project directory
super-agents              # Sets up agents and autonomous operations
super-agents --upgrade    # Upgrade existing installation
super-agents --help       # Show all options
```

### **Option 2: Project-Specific Setup**

```bash
# Clone into your project
git clone https://github.com/mkritter3/claude-super-agents.git
cd claude-super-agents

# Setup and start
./setup.sh              # Install dependencies and configure
./start.sh              # Start autonomous operations
./.claude/hooks/install-hooks.sh  # Install git hooks for autonomy
```

## 🎯 **Usage Examples**

### **Explicit Mode: Direct Task Management**
```bash
# Create complex tasks
./.claude/aet create "Build user authentication with OAuth2 and JWT"
./.claude/aet create "Optimize database queries in payment service"

# Process tasks
./.claude/aet process           # Process all pending tasks
./.claude/aet process --parallel # Parallel execution
./.claude/aet process --simple   # Lightweight mode

# Monitor
./.claude/aet status            # System status
./.claude/aet health            # Health monitoring
./.claude/aet metrics           # Performance metrics
```

### **Implicit Mode: Autonomous Git Operations**
```bash
# These git actions automatically trigger agents:

git commit -m "Add user profile API"
# → test-executor runs relevant tests
# → documentation-agent updates API docs  
# → monitoring-agent prepares observability

git commit -m "ALTER TABLE users ADD COLUMN email"
# → contract-guardian validates schema changes
# → data-migration-agent creates migration scripts
# → Critical safety checks prevent breaking changes

git merge feature/payment-system  
# → monitoring-agent sets up comprehensive monitoring
# → documentation-agent updates deployment guides
# → performance-optimizer-agent establishes baselines
```

### **Ambient Mode: Autonomous Self-Healing**
```bash
# These happen automatically without user input:

# Error rate spike detected
# → incident-response-agent investigates automatically
# → Provides rollback recommendations if needed
# → Updates status page and generates incident report

# 5+ commits without documentation updates
# → documentation-agent silently updates docs after 24 hours
# → No user interruption, just keeps docs current

# Performance degradation detected  
# → performance-optimizer-agent analyzes bottlenecks
# → Provides optimization recommendations
# → Tracks trends and establishes new baselines
```

## 🛡️ **Security & Safety Features**

### **Pre-commit Security (The Only Blocking Hook)**
- **Secret Detection**: Prevents API keys, passwords, credentials from entering repository
- **Comprehensive Patterns**: AWS keys, database URLs, JWT tokens, private keys
- **Developer Friendly**: Clear error messages with fix suggestions
- **Bypass Option**: `git commit --no-verify` for false positives

### **Autonomous Safety Nets**
- **Breaking Change Prevention**: contract-guardian blocks unsafe API/schema changes
- **Quality Gates**: test-executor ensures code quality before integration
- **Observability**: monitoring-agent auto-configures alerts and dashboards
- **Data Safety**: data-migration-agent prevents data loss during schema changes

### **Production Safeguards**
- **Circuit Breakers**: Fault tolerance with graceful degradation
- **Resource Management**: CPU/memory limits and intelligent queuing
- **Rollback System**: Complete state recovery from any point
- **Audit Trail**: Immutable event log for compliance and debugging

## 🎈 **How It Works (Simple Explanation)**

Imagine you're managing a software company, but instead of hiring 17 different specialists, you have AI agents that work 24/7:

### **The Engineering Team**
- **🎯 Project Manager** plans your features
- **🏗️ Architect** designs the system  
- **👨‍💻 Developer** writes the code
- **🔍 Code Reviewer** checks quality
- **🧪 Tester** validates everything works

### **The Operations Team (Always Working)**
- **🛡️ Security Guard** prevents credential leaks and breaking changes
- **📊 Monitoring Specialist** sets up alerts and dashboards automatically
- **📚 Documentation Manager** keeps docs updated without being asked
- **🚨 Incident Responder** handles problems automatically
- **⚡ Performance Engineer** optimizes your code continuously

### **The Magic**
1. **You work normally** - Write code, commit changes, merge branches
2. **Agents work automatically** - Every git action triggers helpful agents
3. **Problems get prevented** - Safety nets catch issues before production
4. **System self-improves** - Continuous monitoring and optimization
5. **Everything is recorded** - Complete audit trail of all actions

## 🔧 **Configuration & Customization**

### **System Configuration**
- `.claude/config.json` - System settings and model preferences
- `CLAUDE.md` - Orchestration instructions for the current project
- `.claude/agents/*.md` - Individual agent definitions and capabilities

### **Autonomous Operations**
- `.claude/hooks/` - Git hooks for autonomous triggers
- `.claude/system/ambient_operations.py` - Self-monitoring rules
- `.claude/system/event_watchers.py` - Event processing and triggers
- `.claude/system/claude_bridge.py` - Natural language translation layer

### **Customization Examples**
```bash
# Adjust autonomous rules
nano .claude/system/ambient_operations.py

# Modify trigger patterns  
nano .claude/hooks/post-commit

# Configure agent models
nano .claude/agents/developer-agent.md
```

## 📊 **Cost Optimizations**

### **Advanced Cost Management**
- **70-80% cost reduction** through intelligent prompt caching
- **Smart Model Selection**: Haiku for simple tasks, Sonnet for complex reasoning
- **Batch Processing**: Parallel agent execution for efficiency
- **Context Optimization**: Intelligent file loading within token budgets

### **Performance Features**
- **Extended Thinking**: 30,000-50,000 token budgets for complex reasoning
- **Streaming Support**: Real-time feedback for long operations  
- **Prompt Caching**: 1-hour TTL for stable agent prompts
- **Resource Limits**: CPU/memory management prevents runaway processes

## 📚 **Comprehensive Documentation**

### **Architecture & Implementation**
- [Autonomous Integration Architecture](AUTONOMOUS_INTEGRATION_ARCHITECTURE.md) - How autonomy works
- [Operational Agents Roadmap](OPERATIONAL_AGENTS_ROADMAP.md) - Operational agent details
- [Natural Language Triggers](NATURAL_LANGUAGE_TRIGGERS.md) - Event translation system
- [Implementation Roadmap](IMPLEMENTATION_ROADMAP.md) - Development phases

### **Technical Details**
- [Directory Structure](DIRECTORY-STRUCTURE.md) - System organization
- [Optimizations](OPTIMIZATIONS.md) - Performance and cost optimization
- [Upgrade Status](UPGRADE-STATUS.md) - Current implementation status

## 🧪 **Testing & Validation**

### **Comprehensive Test Suites**
```bash
# Test autonomous operations
python3 .claude/system/integration_test.py

# Test specific components
python3 .claude/tests/run_all_tests.py

# Validate hooks system
./.claude/hooks/install-hooks.sh  # Includes validation
```

### **Real-World Validation**
The system includes **comprehensive integration testing** with 88.9% success rate across:
- File system message bus functionality
- Event watcher triggers and processing
- Claude bridge natural language translation
- Git hooks autonomous operation triggers
- Ambient operations self-monitoring
- End-to-end workflow validation

## 🛠️ **Requirements**

### **System Requirements**
- **Python 3.8+** with pip
- **Git** (hooks system requires git repository)
- **SQLite3** (for file registry and state management)
- **Claude Code CLI** (for agent execution)

### **Python Dependencies** (auto-installed)
```
structlog>=23.2.0          # Structured logging
psutil>=5.9.0              # Resource monitoring  
prometheus-client>=0.19.0  # Metrics collection
opentelemetry-api>=1.20.0  # Distributed tracing
gunicorn>=21.2.0           # Production server
```

## 🎁 **What You Get**

### **Immediate Benefits**
✅ **17 AI specialists** working as your engineering team  
✅ **Autonomous operations** that prevent production issues  
✅ **Comprehensive safety nets** for quality and security  
✅ **Complete audit trail** of all engineering activities  
✅ **Production-ready architecture** with fault tolerance  
✅ **70-80% cost savings** through intelligent optimizations  

### **Long-term Value**
🚀 **Faster development** with specialized expert agents  
🛡️ **Higher quality** through automated review and testing  
📈 **Better observability** with automatic monitoring setup  
🔄 **Continuous improvement** through performance optimization  
🎯 **Reduced cognitive load** - agents handle operational details  

## 🤝 **Contributing**

We welcome contributions! This system represents a breakthrough in autonomous AI operations. Areas for contribution:

- **New Operational Agents**: Additional safety nets and automation
- **Enhanced Triggers**: More intelligent event detection patterns
- **Integration Improvements**: Better toolchain integrations
- **Performance Optimizations**: Further cost and speed improvements

## 📜 **License**

MIT License - see LICENSE file for details

## 🙏 **Acknowledgments**

Built with **Claude Code** by the Anthropic team and enhanced through iterative development with Claude. This system represents a collaboration between human engineering insight and AI capability to create truly autonomous operations.

---

## 🚀 **Ready to Deploy Your Autonomous Engineering Team?**

```bash
# One command to transform your development workflow
git clone https://github.com/mkritter3/claude-super-agents.git && cd claude-super-agents && sudo ./install-global.sh

# Then from any project directory
super-agents
```

**Experience the future of autonomous software engineering** 🤖✨

### **What Happens Next?**
1. **Instant Setup**: 17 AI agents deployed and configured
2. **Autonomous Operations**: Git hooks enable autonomous triggers  
3. **Safety Nets Active**: Protection against breaking changes and credential leaks
4. **Self-Monitoring**: Ambient operations watch your system 24/7
5. **Production Ready**: Full observability, audit trails, and fault tolerance

**Transform your development workflow from manual to autonomous in minutes** 🎯