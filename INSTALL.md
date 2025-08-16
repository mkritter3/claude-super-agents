# Super Agents Installation

## One-Command Install

```bash
git clone https://github.com/yourusername/super-agents.git
cd super-agents
pip install -e .
```

## Quick Start

```bash
# Initialize in any project
cd /your/project
super-agents init

# Launch Claude with AET agents
super-agents
```

## What You Get

✅ **23 AI Agents** - Complete autonomous engineering team  
✅ **Local Knowledge Manager** - Per-project isolation  
✅ **Autonomous Operations** - Git hooks trigger agents automatically  
✅ **Claude Code Integration** - Seamless workflow

## Requirements

- Python 3.8+
- Git (for autonomous operations)
- Claude Code (recommended)

All Python dependencies installed automatically.

## Commands

- `super-agents init` - Set up AET in current project
- `super-agents` - Start system and launch Claude
- `super-agents status` - Check system health
- `super-agents stop` - Stop Knowledge Manager
- `super-agents --help` - See all commands

## Troubleshooting

**Command not found?** 
```bash
pip install -e . 
```

**Permission issues?** No sudo needed - installs to user directory.

That's it! The system now works flawlessly out of the box.