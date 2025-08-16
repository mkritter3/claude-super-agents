# Super-Agents 🤖 - AI Team for Your Code

23 AI agents that help you write, review, and manage code. Each project gets its own isolated setup.

## 🚀 Install

```bash
git clone https://github.com/yourusername/super-agents.git
cd super-agents
pip install -e .
```

## 🎯 Use

```bash
# Initialize in any project
cd /your/project
super-agents init

# Launch Claude with AET agents
super-agents
```

## What You Get

✅ **23 Specialized Agents** - architect, developer, reviewer, security, devops, etc.  
✅ **Autonomous Operations** - Agents trigger automatically on git commits  
✅ **Local Knowledge Manager** - Per-project isolation with dynamic ports  
✅ **Claude Code Integration** - Seamless AI-powered development workflow

## Commands

- `super-agents init` - Set up AET in current project
- `super-agents` - Start system and launch Claude
- `super-agents status` - Check system health  
- `super-agents stop` - Stop Knowledge Manager
- `super-agents --help` - See all commands

## Requirements

- Python 3.8+
- Git (for autonomous operations)
- Claude Code (recommended)

All dependencies installed automatically.

## How It Works

1. **Initialize once**: `super-agents init` sets up 23 agents in your project
2. **Code normally**: Write code, make commits
3. **Agents activate**: Git hooks trigger autonomous operations
4. **Quality maintained**: Automatic testing, documentation, security checks

Each project is completely isolated with its own agent team.

## Agent Team

### Core Engineering
- **architect-agent** - System design and technical architecture
- **developer-agent** - Code implementation and features  
- **reviewer-agent** - Code review and quality assurance
- **integrator-agent** - Safe merging and integration

### Autonomous Operations  
- **contract-guardian** - Prevents API/schema breaking changes
- **test-executor** - Automatic quality gates and test execution
- **documentation-agent** - Maintains documentation automatically
- **monitoring-agent** - Auto-configures observability
- **security-agent** - Security audits and vulnerability scanning

### Full-Stack Development
- **frontend-agent** - React/Vue/Angular UI implementation
- **database-agent** - Schema design and query optimization  
- **devops-agent** - CI/CD pipelines and deployment automation
- **ux-agent** - User experience design and accessibility

...and 10 more specialized agents for complete project coverage.

## Troubleshooting

**Command not found?** Run `pip install -e .` in the super-agents directory.

**Need help?** Run `super-agents --help` or check `super-agents status`.

That's it! The system works flawlessly out of the box. 🚀