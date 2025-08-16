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

## 🚀 Super Simple Installation

### Step 1: Download This Project

Open Terminal (Mac/Linux) or Command Prompt (Windows) and run:

```bash
# Go to your home directory
cd ~

# Download the project
git clone https://github.com/yourusername/super-agents.git

# Enter the project folder
cd super-agents
```

### Step 2: Install Python Dependencies

```bash
# Install the requests library (needed for network communication)
python3 -m pip install requests

# That's it for dependencies!
```

### Step 3: Install Super-Agents

```bash
# Go back to the super-agents folder
cd ~/super-agents

# Install super-agents globally
./install.sh
```

When it asks for your password (sudo), enter your computer's login password.

### Step 4: Verify Installation

```bash
# Check if it worked
super-agents --version
super-agents-local help
```

## 🎯 How to Use It

### Setting Up a Project (Do This Once Per Project)

1. Go to your project folder:
   ```bash
   cd /path/to/your/project
   ```

2. Set up the AI agents:
   ```bash
   super-agents-local
   ```
   
   This creates a `.claude/` folder with everything needed.

3. Check if it's working:
   ```bash
   super-agents-local status
   ```

### Daily Use

Once set up, the AI agents work automatically when you:
- Open Claude Code in that project
- Make git commits
- Run various commands

## 🛠️ Troubleshooting

### "command not found"

If you get "command not found" errors:

1. Make sure you reopened Terminal after installation
2. Try running directly:
   ```bash
   python3 -m pipx run super-agents
   ```
3. Check your PATH:
   ```bash
   echo $PATH
   ```
   Should include something like `/Users/yourname/.local/bin`

### "No module named requests"

Install the requests library:
```bash
python3 -m pip install requests
```

### "Permission denied"

Make files executable:
```bash
chmod +x ~/super-agents/install.sh
chmod +x ~/super-agents/super-agents-local
```

### Can't find the project

Make sure you're in the right folder:
```bash
pwd  # Shows current directory
ls   # Lists files in current directory
```

## 📁 What Gets Installed Where

- **Your project**: Gets a `.claude/` folder with AI agents
- **Your computer**: 
  - `/usr/local/bin/super-agents-local` - Global command
  - `~/.local/bin/super-agents` - Main super-agents command
  - No system files are modified

## 🗑️ Uninstalling

To remove from a project:
```bash
super-agents-local clean
```

To remove from your computer:
```bash
python3 -m pipx uninstall super-agents
sudo rm /usr/local/bin/super-agents-local
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
4. Try running with full path: `~/super-agents/super-agents-local`

## 📝 What This Actually Does

When you run `super-agents-local` in a project, it:

1. Creates `.claude/agents/` with 23 AI agent configurations
2. Sets up a local Knowledge Manager server
3. Configures event tracking and automation
4. Installs git hooks for automatic operations

Each project is completely independent - no conflicts between projects.

## 🎉 You're Done!

Once installed, just run `super-agents-local` in any project folder to set up AI agents for that project. It's that simple!