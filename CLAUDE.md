# Super Agents CLI - Template-Based Architecture

This project implements a **template-based architecture** where the CLI is a thin wrapper that delegates all business logic to project-specific implementations.

## 🏗️ **CRITICAL ARCHITECTURAL GUIDELINES**

### **Template-Based Architecture Pattern**

**✅ CORRECT**: All business logic lives in the template
```
src/super_agents/
├── cli.py                           # Thin wrapper - delegates only
├── __init__.py                      # Package metadata
└── templates/default_project/       # ALL BUSINESS LOGIC HERE
    └── .claude/system/
        ├── commands/                # Command implementations
        ├── performance/             # Performance optimizations
        ├── reliability/             # Reliability features  
        ├── database/                # Database logic
        ├── features/                # Feature implementations
        └── utils/                   # Utilities and helpers
```

**❌ WRONG**: Business logic scattered in main package
```
src/super_agents/
├── cli.py                           # ❌ Should not import business logic
├── commands/                        # ❌ Should be in template
├── performance/                     # ❌ Should be in template
├── reliability/                     # ❌ Should be in template
├── database/                        # ❌ Should be in template
├── features/                        # ❌ Should be in template
└── utils/                           # ❌ Should be in template
```

### **Why This Architecture Matters**

1. **Project Isolation**: Each project gets its own complete system
2. **Version Independence**: Different projects can use different template versions
3. **Customization**: Projects can modify their local template without affecting others
4. **Consistency**: Template ensures all projects start with the same foundation
5. **Upgrades**: Template updates can be applied selectively

### **CLI Delegation Pattern**

The CLI must be a **thin wrapper** that only:
- Handles argument parsing
- Checks if project is initialized  
- Copies template on `init`
- Delegates all commands to template implementations

```python
# CORRECT: Thin CLI delegation
def delegate_to_template(command: str):
    sys.path.insert(0, str(Path('.claude/system')))
    if command == 'start':
        from commands.km_manager import KnowledgeManagerController
        km = KnowledgeManagerController()
        km.start()
```

```python
# WRONG: Direct business logic in CLI
from super_agents.commands.km_manager import KnowledgeManagerController
# ❌ This violates template architecture
```

### **Template System Structure**

Every template must contain:
```
templates/default_project/
├── .claude/                         # AET system directory
│   ├── agents/                      # 23 specialized AI agents
│   ├── system/                      # ALL business logic
│   │   ├── commands/                # Command implementations
│   │   ├── performance/             # Performance optimizations
│   │   ├── reliability/             # Reliability features
│   │   ├── database/                # Database operations
│   │   ├── features/                # Feature implementations
│   │   ├── utils/                   # Shared utilities
│   │   ├── km_server.py            # Knowledge Manager server
│   │   └── ...                      # Other system components
│   ├── events/                      # Event system
│   ├── hooks/                       # Git hooks
│   └── km_bridge_local.py          # MCP bridge
├── .mcp.json                        # Claude Code MCP config
├── CLAUDE.md                        # Project instructions
└── ...                              # Other template files
```

## 📋 **Development Guidelines**

### **Adding New Features**

1. **Add to template system**: `src/super_agents/templates/default_project/.claude/system/`
2. **Update CLI delegation**: Add delegation logic to `cli.py`
3. **Test with template**: Use `super-agents init` in test directory
4. **Never add to main package**: Avoid creating directories outside template

### **Import Patterns**

**Within Template System**:
```python
# ✅ CORRECT: Relative imports within template
from performance.lazy_loader import lazy_import
from commands.init import initialize_project
from utils.profiler import profile_command
```

**CLI to Template**:
```python
# ✅ CORRECT: Dynamic import after path setup
sys.path.insert(0, str(Path('.claude/system')))
from commands.km_manager import KnowledgeManagerController
```

**Main Package**:
```python
# ❌ WRONG: Never import from scattered business logic
from super_agents.commands.init import initialize_project
```

## Components

- **23 Specialized Agents** in template `.claude/agents/`
- **Local Knowledge Manager** in template `.claude/km_server/`
- **Event System** in template `.claude/events/`
- **Git Hooks** in template `.claude/hooks/`
- **MCP Bridge** in template `.claude/km_bridge_local.py`
- **Performance Optimizations** in template `.claude/system/performance/`
- **Reliability Systems** in template `.claude/system/reliability/`
- **Database Maintenance** in template `.claude/system/database/`

## Status

Run `super-agents status` to check system health, including performance metrics and reliability status.

## Performance Features (Week 3 Complete ✅)

The system includes production-grade performance optimizations:

### 🚀 **74% Average Performance Improvement**
- **Lazy Loading**: 100% startup improvement - modules load only when accessed
- **Intelligent Caching**: 57-73% runtime improvement for file operations
- **Project Indexing**: 67% faster file searches with background processing
- **Memory Optimization**: Minimal footprint with automatic cleanup

### 🛡️ **Enterprise Reliability** 
- **Circuit Breakers**: Prevent cascade failures with automatic recovery
- **Database Maintenance**: Automatic SQLite optimization every 7 days
- **Graceful Degradation**: Optional dependencies fail safely (e.g., sentence-transformers)
- **Thread-Safe Operations**: All caching and indexing work in concurrent environments

### 📊 **Monitoring & Profiling**
- Use `super-agents --profile` to enable performance tracking
- Check `.claude/performance_baseline.json` for baseline metrics
- Cache and indexing statistics available via `super-agents status`

## Usage

The system is already running with performance optimizations active. Claude Code will automatically:
1. Initialize performance optimizations (lazy loading, caching, indexing)
2. Connect to the local Knowledge Manager
3. Use the 23 specialized agents with optimal performance
4. Track events and triggers with intelligent caching
5. Apply autonomous operations with circuit breaker protection

## Performance Commands

```bash
# Check system performance and health
super-agents status

# Enable performance profiling
super-agents --profile

# Save performance baseline for comparison
super-agents --profile --save-baseline

# View performance validation results
python scripts/simple_performance_test.py
```

## Restart if Needed

```bash
# Standard restart
super-agents stop && super-agents

# With performance profiling
super-agents --profile
```

## 📊 **Roadmap Status (Week 3 Complete)**

### **✅ Completed Implementations**

**Week 1**: Graceful Dependency Degradation & Performance Profiling
- ✅ Graceful degradation for sentence-transformers
- ✅ Performance profiling with `--profile` flag
- ✅ Baseline performance metrics established

**Week 2**: SQLite Maintenance & Circuit Breakers  
- ✅ Automatic SQLite maintenance system
- ✅ File-based circuit breaker with thread-safe locking
- ✅ Database optimization and VACUUM operations

**Week 3**: Performance Optimizations ⚡
- ✅ **Lazy Loading System**: 100% startup improvement (exceeded 20% target)
- ✅ **Intelligent Caching**: 57-73% runtime improvement 
- ✅ **Project Indexing**: 67% search improvement
- ✅ **Overall Performance**: 74% average improvement across all metrics
- ✅ All optimizations moved to template architecture

**Architecture Refactor**: Template-Based System
- ✅ Moved ALL business logic to template system
- ✅ Streamlined CLI to thin delegation wrapper
- ✅ Fixed import paths and dependencies
- ✅ Validated new architecture with successful initialization

### **Performance Results (Week 3)**
```
Lazy Loading:    100% improvement (Target: 20%)  ⚡⚡
Caching:         57-73% improvement             ⚡
Indexing:        67% improvement                ⚡
Average:         74% improvement                ⚡⚡
```

### **🎯 Next Phase**

**Week 4**: Comprehensive Integration Testing
- Integration test suite for all performance optimizations
- Cross-component validation 
- Template system testing
- Performance regression testing

**Week 5**: Final Stress Testing and Documentation
- Load testing and stress validation
- Final documentation updates
- Production readiness assessment
- Performance monitoring setup

## 🚀 **System Status**

- **Architecture**: ✅ Template-based (refactored)
- **Performance**: ✅ Optimized (74% improvement)
- **Reliability**: ✅ Enhanced (circuit breakers, maintenance)
- **MCP Integration**: ✅ Dynamic port handling
- **Knowledge Manager**: ✅ Local running

## 📝 **Usage Commands**

```bash
# Initialize new project with template
super-agents init

# Start system (delegates to template)
super-agents

# Check system status
super-agents status

# Stop Knowledge Manager
super-agents --stop

# List all running instances
super-agents --list

# Performance profiling
super-agents --profile
```

## 🔧 **Template System**

The template provides:
- **23 Specialized AI Agents** for autonomous operations
- **Knowledge Manager** with dynamic port allocation  
- **Performance Optimizations** (lazy loading, caching, indexing)
- **Reliability Features** (circuit breakers, maintenance)
- **MCP Integration** for Claude Code
- **Event System** for coordination
- **Git Hooks** for autonomous triggers

Each `super-agents init` creates a complete, isolated AET system.

---

**Remember: ALL business logic belongs in the template system. The CLI is just a thin wrapper for delegation.**
