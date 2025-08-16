# Super Agents Installation

Complete beginner's guide to installing and using the Autonomous Engineering Team.

## Step 1: Install Python (if not already installed)

### Check if Python is installed
Open your terminal and type:
```bash
python3 --version
```

If you see a version number (like `Python 3.9.7`), skip to Step 2.

### Install Python if needed

**On macOS:**
```bash
# Install using Homebrew (recommended)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python3
```

**On Windows:**
1. Go to https://python.org/downloads
2. Download Python 3.8 or newer
3. Run installer and check "Add Python to PATH"

**On Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

### Verify pip is installed
```bash
pip3 --version
```
If pip is missing, install it:
```bash
python3 -m ensurepip --upgrade
```

## Step 2: Install Git (if not already installed)

### Check if Git is installed
```bash
git --version
```

### Install Git if needed

**On macOS:** `brew install git`  
**On Windows:** Download from https://git-scm.com  
**On Linux:** `sudo apt install git`

## Step 3: Clone and Install Super Agents

```bash
# 1. Download the project
git clone https://github.com/yourusername/super-agents.git

# 2. Enter the project directory
cd super-agents

# 3. Install everything automatically
pip3 install -e .
```

## Step 4: Verify Installation

```bash
super-agents --help
```

You should see a list of available commands.

## Step 5: Use in Your Project

```bash
# 1. Go to your project directory
cd /path/to/your/project

# 2. Initialize the AET system
super-agents init

# 3. Start the system and launch Claude
super-agents
```

## What You Get

✅ **23 AI Agents** - Complete autonomous engineering team  
✅ **Local Knowledge Manager** - Per-project isolation  
✅ **Autonomous Operations** - Git hooks trigger agents automatically  
✅ **Claude Code Integration** - Seamless workflow

## Requirements Met Automatically

- Python 3.8+ ✓
- Git ✓ 
- All Python dependencies ✓

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