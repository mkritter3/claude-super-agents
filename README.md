# Super-Agents 🤖 - AI Team for Your Code

This gives you 23 AI agents that help you write, review, and manage code. Each project gets its own isolated setup.

## 📋 Prerequisites (What You Need First)

Before installing, make sure you have:

1. **Python 3** - Check if you have it:
   ```bash
   python3 --version
   ```
   Should show something like `Python 3.9.6` or higher.
   
   If not installed:
   - Mac: Python 3 comes pre-installed
   - Windows: Download from [python.org](https://python.org)
   - Linux: `sudo apt install python3`

2. **Git** - Check if you have it:
   ```bash
   git --version
   ```
   
   If not installed:
   - Mac: `brew install git` or download from [git-scm.com](https://git-scm.com)
   - Windows: Download from [git-scm.com](https://git-scm.com)
   - Linux: `sudo apt install git`

3. **Claude Code** (optional but recommended)
   - Download from Anthropic if you have access

## 🚀 One-Command Installation

```bash
# Clone and install
git clone https://github.com/yourusername/super-agents.git
cd super-agents
pip install -e .
```

That's it! No sudo, no complex setup, no dependency management needed.

## 🎯 How to Use It

### Initialize Any Project (One Command)

```bash
cd /path/to/your/project
super-agents init
```

This sets up the complete AET system with 23 agents in your project.

### Launch Claude with AET Agents

```bash
super-agents
```

This starts the Knowledge Manager and launches Claude Code with all agents ready.

### Daily Workflow

1. **Initialize once per project**: `super-agents init`
2. **Start when coding**: `super-agents` (launches Claude)
3. **Agents work automatically** when you make git commits
4. **Stop when done**: `super-agents stop`

## 🛠️ Troubleshooting

### "command not found"

If `super-agents` command not found:

```bash
# Make sure you're in the right directory
cd super-agents
pip install -e .

# Or check where it was installed
pip show super-agents
```

### Missing Dependencies

All dependencies are automatically installed with `pip install -e .`

### Permission Issues

No sudo needed! The new system installs to your user directory only.

### Can't find the project

Make sure you're in the right folder:
```bash
pwd  # Shows current directory
ls   # Lists files in current directory
```

## 📁 What Gets Installed Where

- **Your project**: Gets a `.claude/` folder with AI agents
- **Your computer**: 
  - `/usr/local/bin/super-agents` - The super-agents command
  - No other system files are modified

## 🗑️ Uninstalling

To remove from a project:
```bash
super-agents clean
```

To remove from your computer:
```bash
sudo rm /usr/local/bin/super-agents
```

## 💡 Tips for Beginners

1. **Terminal Basics**:
   - `cd foldername` - Enter a folder
   - `cd ..` - Go back one folder
   - `ls` - List files in current folder
   - `pwd` - Show current folder path
   - `Tab` key - Auto-complete file/folder names

2. **Copy-Paste in Terminal**:
   - Mac: Cmd+C to copy, Cmd+V to paste
   - Windows: Right-click to paste
   - Linux: Ctrl+Shift+C to copy, Ctrl+Shift+V to paste

3. **File Paths**:
   - `~` means your home directory
   - `.` means current directory
   - `..` means parent directory

## 🆘 Getting Help

If you're stuck:

1. Check you're in the right folder: `pwd`
2. Check the file exists: `ls`
3. Check Python is installed: `python3 --version`
4. Try running with full path: `/usr/local/bin/super-agents`
5. Check available commands: `super-agents help`

## 📝 What This Actually Does

When you run `super-agents` in a project, it:

1. Creates `.claude/agents/` with 23 AI agent configurations
2. Sets up a local Knowledge Manager server
3. Configures event tracking and automation
4. Installs git hooks for automatic operations

Each project is completely independent - no conflicts between projects.

## 🎉 You're Done!

Once installed, just run `super-agents` in any project folder to set up AI agents for that project.

### Available Commands

- `super-agents` - Set up AET in current directory
- `super-agents start` - Start the Knowledge Manager server
- `super-agents stop` - Stop the server
- `super-agents restart` - Restart the server
- `super-agents status` - Check system health
- `super-agents clean` - Remove AET from current directory
- `super-agents help` - Show all commands

Each project gets its own isolated setup!