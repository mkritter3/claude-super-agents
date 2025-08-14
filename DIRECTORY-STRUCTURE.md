# AET System Directory Structure

## 📁 Root Directory
```
claude-super-agents/
├── README.md                      # Main project documentation
├── CLAUDE.md                      # Instructions for Claude AI
├── AET-UPGRADE-COMPLETE.md        # Comprehensive upgrade summary
├── UPGRADE-STATUS.md              # Detailed upgrade tracking
├── requirements-upgrade.txt       # Python dependencies
├── setup.sh                       # System setup script
├── .gitignore                     # Git ignore patterns
└── DIRECTORY-STRUCTURE.md         # This file
```

## 📁 Main Directories

### `.claude/` - Core System
```
.claude/
├── agents/                        # Agent definitions (12 agents)
├── system/                        # Core modules (25+ Python files)
│   ├── aet.py                    # CLI entry point
│   ├── orchestrator.py           # Main orchestration engine
│   ├── context_assembler.py      # Context integration (with circuit breakers)
│   ├── simple_orchestrator.py    # Lightweight mode
│   ├── state_rebuilder.py        # State recovery system
│   ├── metrics_collector.py      # Prometheus metrics
│   ├── tracing_config.py         # OpenTelemetry tracing
│   ├── logger_config.py          # Structured logging
│   └── ...                       # Other core modules
├── tests/                         # Test suites
│   ├── phase0/                   # Critical fixes tests
│   ├── phase1/                   # Security tests
│   ├── phase2/                   # State recovery tests
│   ├── phase3/                   # Simple mode tests
│   └── phase4/                   # Observability tests
├── monitoring/                    # Production monitoring
│   └── dashboards/               # Grafana dashboards (4 JSON files)
├── scripts/                       # Utility scripts
├── registry/                      # File and knowledge databases
├── events/                        # Event log storage
├── snapshots/                     # State snapshots
└── workspaces/                    # Agent workspaces
```

### `docs/` - Documentation
```
docs/
└── phase-completions/             # Phase completion reports
    ├── PHASE0-COMPLETE.md
    ├── PHASE0-IMPLEMENTATION-SUMMARY.md
    ├── PHASE1-COMPLETE.md
    ├── PHASE3-COMPLETE.md
    └── PHASE4-COMPLETE.md
```

### `examples/` - Example Code
```
examples/
└── demo_observability.py          # Observability demonstration
```

## 📊 Statistics

- **Total Python Modules**: 25+ in `.claude/system/`
- **Agent Definitions**: 12 specialized agents
- **Test Suites**: 5 phases with comprehensive tests
- **Grafana Dashboards**: 4 production-ready dashboards
- **Documentation Files**: 13+ markdown files

## 🧹 Cleanup Status

✅ **Cleaned:**
- All `__pycache__` directories removed
- All `.pyc` files deleted
- Temporary test files removed
- Old job workspaces cleared
- Phase reports organized into `docs/`
- Demo scripts moved to `examples/`

✅ **Organized:**
- Root directory reduced to essential files only
- Documentation properly categorized
- Examples separated from core code
- Test artifacts contained within test directories

## 🎯 Directory Purpose

| Directory | Purpose |
|-----------|---------|
| `.claude/system/` | Core AET system modules |
| `.claude/agents/` | Agent behavior definitions |
| `.claude/tests/` | Comprehensive test coverage |
| `.claude/monitoring/` | Production observability |
| `docs/` | All documentation |
| `examples/` | Demo and example scripts |

The structure is now clean, organized, and production-ready!