# Super Agents Installation

## Quick Install (One Command)

```bash
pip install -e .
```

## Prerequisites

- Python 3.8+
- Git (for autonomous operations)  
- Claude Code (optional but recommended)

## Installation Steps

1. **Clone and install:**
   ```bash
   git clone https://github.com/yourusername/super-agents.git
   cd super-agents
   pip install -e .
   ```

2. **Initialize any project:**
   ```bash
   cd /path/to/your/project
   super-agents init
   ```

3. **Start the system:**
   ```bash
   super-agents
   ```
   This launches Claude Code with all 23 AET agents ready to go!

## What You Get

- ✅ **23 Specialized Agents** - Complete autonomous engineering team
- ✅ **Local Knowledge Manager** - Per-project isolation with dynamic ports
- ✅ **Event System** - Full autonomous operations with git hooks
- ✅ **Claude Code Integration** - Seamless AI-powered development

### Method 2: Virtual Environment (Best Practice)

Using a virtual environment isolates the installation and prevents conflicts:

```bash
# Clone the repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install the package
pip install .
```

### Method 3: Development Installation

For contributors who want to modify the code:

```bash
# Clone the repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Install development dependencies
pip install -r requirements-dev.txt

# Install in editable mode
pip install -e .
```

Changes to the source code will be immediately reflected without reinstalling.

## Updating

To update to the latest version:

```bash
cd super-agents
git pull

# Reinstall
pip install --upgrade .

# Or for development
pip install --upgrade -e .
```

## Verification

After installation, verify it works:

```bash
# Check installation
super-agents --version

# Initialize a test project
mkdir test-project
cd test-project
super-agents init
```

## Troubleshooting

### Command Not Found

If `super-agents` is not found after installation:

1. **Check installation location:**
   ```bash
   pip show super-agents
   ```

2. **Find the binary:**
   ```bash
   # Linux/macOS
   find ~/.local -name super-agents
   
   # Or
   python3 -m site --user-base
   ```

3. **Add to PATH if needed:**
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

### Permission Denied

If you get permission errors:
- Use Method 1 (user installation) instead of trying to install globally
- Never use `sudo pip install` - it's a security risk

### Windows Users

For native Windows (not WSL):
1. Install Python from python.org
2. Use `pip install .` in Command Prompt or PowerShell
3. The command will be available as `super-agents.exe`

## Uninstallation

To remove super-agents:

```bash
pip uninstall super-agents
```

## Future: PyPI Installation

Once published to PyPI, installation will be simplified to:

```bash
pip install super-agents
```

No cloning or downloading required!

---

**Note:** The old `install.sh` script is deprecated. Please use the standard pip methods above for better cross-platform compatibility and security.