# Super-Agents 🤖 - Autonomous Engineering Team

[![GitHub](https://img.shields.io/github/license/mkritter3/claude-super-agents)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://python.org)
[![Version](https://img.shields.io/badge/version-1.0.0-green)](https://github.com/mkritter3/claude-super-agents)

**Transform Claude Code into a fully autonomous engineering team with 23 specialized AI agents, autonomous operations, and comprehensive safety nets**

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Install globally (one-time setup)
./install.sh

# Now use from ANY directory!
cd ~/my-project
super-agents              # Auto-init + launch Claude with agents
super-agents --wild       # Launch with --dangerously-skip-permissions
```

## 🌟 What is Super-Agents?

Super-Agents (AET - Autonomous Engineering Team) is a **production-ready autonomous engineering system** that transforms Claude Code into a complete software engineering organization. It features:

- **23 Specialized AI Agents** - Complete engineering team coverage
- **True Autonomous Operations** - Works without constant supervision
- **Universal Portability** - Install once, use anywhere
- **Comprehensive Safety Nets** - Prevents production issues automatically
- **Dynamic Multi-Project Support** - Run multiple projects simultaneously

### 🎯 Core Innovation: True Autonomy

Unlike traditional automation, this system achieves **true autonomy** through:
- **File System as Message Bus** - Agents communicate through structured events
- **Git Hooks as Daemon Substitutes** - Autonomous triggers without background services
- **Natural Language Control Plane** - AI translates technical events into actions

## 📦 Installation

### Recommended: Standard Python Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Install for current user (recommended - no sudo required)
pip install .

# Or install in development mode (for contributors)
pip install -e .
```

**Note:** The `install.sh` script is deprecated. Use standard `pip` commands for better cross-platform compatibility.

For detailed installation instructions, see [INSTALL.md](INSTALL.md).

### Requirements

- **Python 3.8+** - Check with `python3 --version`
- **pip** - Python package manager
- **Git** - For autonomous operations
- **Claude Code** (optional) - For launching Claude (`claude` command)

### Updating

To update to the latest version after pulling changes:

```bash
cd super-agents
git pull

# Reinstall (pip automatically detects the appropriate location)
pip install --upgrade .

# Or for development mode
pip install --upgrade -e .
```

## 🎮 Usage

Once installed, `super-agents` works from ANY directory:

### Basic Commands

```bash
# Initialize a new project
super-agents init

# Launch Claude with agents
super-agents

# Launch in wild mode (skip permissions)
super-agents --wild

# Upgrade existing project
super-agents upgrade
```

### Management Commands

```bash
super-agents status       # Show project status
super-agents stop         # Stop Knowledge Manager
super-agents list         # List all running instances
super-agents --help       # Show all commands
```

### Advanced Commands

```bash
super-agents recover      # Run error recovery
super-agents monitor      # Monitor process health
super-agents validate     # Validate system integrity
super-agents security     # Security audit
super-agents optimize     # Model optimization
super-agents parallel     # Start parallel executor
```

## 🤖 Three Operational Modes (Working Simultaneously)

### 1. **Explicit Mode** - User asks → agents respond
```bash
user: "Build user authentication with OAuth2"
→ pm-agent plans → architect-agent designs → developer-agent implements
```

### 2. **Implicit Mode** - User acts → agents infer needs  
```bash
user: git commit -m "Fix authentication bug"
→ Hooks trigger → test-executor runs tests → documentation-agent updates docs
```

### 3. **Ambient Mode** - System self-monitors → self-heals
```bash
Error rate spike detected
→ incident-response-agent investigates → Auto-rollback if needed
```

## 🛡️ Autonomous Safety Net

Six operational agents work autonomously to prevent issues:

| Agent | Role | Priority |
|-------|------|----------|
| 🔒 **contract-guardian** | Prevents API/schema breaking changes | CRITICAL |
| 🧪 **test-executor** | Automatic quality gates and testing | HIGH |
| 📊 **monitoring-agent** | Auto-configures observability | HIGH |
| 📚 **documentation-agent** | Maintains documentation automatically | MEDIUM |
| 🔄 **data-migration-agent** | Safe schema evolution | HIGH |
| ⚡ **performance-optimizer** | Continuous performance analysis | MEDIUM |

## 👥 Complete Agent Team (23 Specialists)

### Core Engineering Agents
- **pm-agent** - Project planning and task decomposition
- **architect-agent** - System design and technical architecture
- **developer-agent** - Code implementation
- **reviewer-agent** - Code review and quality assurance
- **integrator-agent** - Safe merging and integration

### Operational Agents (Autonomous)
- **contract-guardian** - API/schema protection
- **test-executor** - Quality gates
- **monitoring-agent** - Observability setup
- **documentation-agent** - Documentation maintenance
- **data-migration-agent** - Schema migrations
- **performance-optimizer-agent** - Performance tuning
- **incident-response-agent** - Incident handling

### Infrastructure Agents
- **builder-agent** - AET system implementation
- **dependency-agent** - Package management
- **filesystem-guardian** - Security validation
- **integration-tester** - Cross-package testing
- **verifier-agent** - Consistency auditing

### Full-Stack Development Agents
- **frontend-agent** - UI/UX implementation
- **ux-agent** - User experience design
- **product-agent** - Product strategy
- **devops-agent** - Infrastructure automation
- **database-agent** - Database architecture
- **security-agent** - Security auditing

## 🔒 Safety Features

### File Protection
- Never silently overwrites existing files
- Prompts with options: backup, skip, or cancel
- Timestamped backups during upgrades

### Manifest Tracking
- `.super_agents_manifest.json` tracks all created files
- Enables safe upgrades and clean uninstalls
- Preserves user configurations

### Pre-commit Security
- Automatic secret detection (only blocking hook)
- Prevents commits with API keys, passwords, credentials
- Clear error messages with actionable fixes

## 🌍 Universal Portability

### How It Works
1. **Package Distribution** - All files bundled in Python package
2. **Template System** - Uses `importlib.resources` for file access
3. **Dynamic Ports** - Each project gets unique port (5001-5100)
4. **Manifest Tracking** - Safe upgrades with file tracking

### Cross-Platform Support
- ✅ macOS (11.0+)
- ✅ Ubuntu (20.04+)
- ✅ Windows (with WSL)
- ✅ Any Unix-like system with Python

## 📊 Architecture

### System Structure
```
super-agents/
├── src/super_agents/       # Python package
│   ├── cli.py             # Main CLI (Click-based)
│   ├── commands/          # Command implementations
│   └── templates/         # Bundled agent files
├── .claude/               # Agent system (copied to projects)
│   ├── agents/           # 23 agent definitions
│   ├── system/           # Core Python systems
│   └── hooks/            # Git hooks for autonomy
└── install.sh            # Installation script
```

### Autonomous Trigger System
```
Git Operation → Hook Activation → Event Creation → Agent Trigger → Action
```

Example flow:
1. User: `git commit -m "Add user model"`
2. Hook: Detects Python file changes
3. Event: Creates test trigger
4. Agent: test-executor runs tests
5. Result: Quality gate enforced

## 🔧 Advanced Features

### Multi-Project Support
```bash
# Project A on port 5001
cd ~/project-a
super-agents  # Starts on 5001

# Project B on port 5002
cd ~/project-b
super-agents  # Starts on 5002

# List all running projects
super-agents list
```

### Parallel Processing (Phase 1.1)
```bash
# Start parallel executor
super-agents parallel

# Submit tasks
super-agents submit developer-agent:implement_auth
super-agents submit test-executor:run_tests

# Check status
super-agents queue-stats
```

### Context7 Integration
- Automatic library documentation fetching
- Current patterns and best practices
- Integrated with Task delegation

## 🔄 Upgrading

### Package Upgrade
```bash
# From source
cd super-agents
git pull
./install.sh
```

### Project Upgrade
```bash
# Upgrade specific project
cd ~/my-project
super-agents upgrade  # Creates backup, preserves configs
```

## 🗑️ Uninstallation

```bash
# Complete uninstall
cd super-agents
./uninstall.sh

# Manual uninstall
pip uninstall super-agents
rm ~/.super-agents-config  # Optional
```

## 🤝 Contributing

### Development Setup
```bash
# Clone repo
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Install in development mode
./install.sh  # Choose option 3

# Make changes - they reflect immediately!
```

### Adding New Agents
1. Add agent file to `src/super_agents/templates/default_project/.claude/agents/`
2. Update agent count checks if needed
3. Test with `super-agents init` in a new directory

## 📈 Roadmap

### Phase 1: Foundation ✅
- [x] 23 specialized agents
- [x] Autonomous operations
- [x] Universal portability
- [x] Safety nets

### Phase 2: Enhancement (In Progress)
- [ ] PyPI publishing for `pip install super-agents`
- [ ] Cloud sync for configurations
- [ ] Web UI dashboard
- [ ] Agent marketplace

### Phase 3: Scale
- [ ] Distributed agent execution
- [ ] Cloud-native deployment
- [ ] Enterprise features
- [ ] Custom agent SDK

## 🆘 Troubleshooting

### Installation Issues

#### "UNKNOWN-0.0.0" Package Name
If you see this during installation, ensure:
1. You're in the super-agents directory
2. Run: `sudo pip3 install --force-reinstall .` (note the dot!)
3. Or use: `./install.sh` for guided installation

#### Command Not Found
```bash
# Check if installed
pip3 show super-agents

# For user installations, add to PATH:
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc  # macOS
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc # Linux
source ~/.zshrc  # or ~/.bashrc
```

#### Permission Errors
```bash
# If you get permission errors, use user installation:
pip3 install --user .

# Or for global, ensure sudo:
sudo pip3 install .
```

### Runtime Issues

#### Claude Command Not Found
If you get "Error: 'claude' command not found!":
- Install Claude Code from https://claude.ai/code
- Or use super-agents without Claude for agent management only

#### Port Conflicts
```bash
# List all running instances
super-agents list

# Stop specific project's Knowledge Manager
cd project-dir
super-agents stop

# Or stop by port
kill $(lsof -ti:5001)  # Replace 5001 with actual port
```

#### Missing Dependencies
```bash
# Install all required packages
pip3 install click rich colorama flask numpy

# Or reinstall super-agents to get dependencies
pip3 install --user --force-reinstall .
```

#### TypeError or Crashes
Update to the latest version:
```bash
git pull
sudo pip3 install --force-reinstall .  # or pip3 install --user --force-reinstall .
```

## 📚 Documentation

- [Architecture Guide](docs/AUTONOMOUS_INTEGRATION_ARCHITECTURE.md)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Agent Specifications](docs/AGENT-UPGRADES.md)
- [Phase Completions](docs/phase-completions/)

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- Built for the Claude Code community
- Inspired by autonomous systems research
- Powered by Anthropic's Claude AI

---

**Ready to orchestrate your autonomous engineering team from anywhere!** 🤖✨

For support, issues, or contributions, visit [GitHub Issues](https://github.com/yourusername/super-agents/issues)