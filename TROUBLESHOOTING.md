# Troubleshooting Guide

This guide helps resolve common issues with the Super-Agents system.

## Table of Contents
- [Installation Issues](#installation-issues)
- [Runtime Errors](#runtime-errors)
- [Knowledge Manager Issues](#knowledge-manager-issues)
- [Agent Issues](#agent-issues)
- [Claude Integration](#claude-integration)
- [Platform-Specific Issues](#platform-specific-issues)

---

## Installation Issues

### Problem: "UNKNOWN-0.0.0" Package Name

**Symptoms:**
```
Successfully installed UNKNOWN-0.0.0
```

**Solution:**
1. Ensure you're in the super-agents directory
2. Include the dot when installing:
   ```bash
   sudo pip3 install --force-reinstall .  # Note the dot!
   ```
3. Or use the installer script:
   ```bash
   ./install.sh
   ```

### Problem: Command Not Found After Installation

**Symptoms:**
```bash
$ super-agents
command not found: super-agents
```

**Solutions:**

**For User Installation (Option 2):**
```bash
# Add Python user bin to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc  # macOS
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc # Linux
source ~/.zshrc  # or source ~/.bashrc

# Verify installation location
pip3 show super-agents | grep Location
```

**For Global Installation (Option 1):**
```bash
# Check if installed globally
ls -la /usr/local/bin/super-agents

# If missing, reinstall with sudo
sudo pip3 install --force-reinstall .
```

### Problem: Permission Denied During Installation

**Symptoms:**
```
ERROR: Could not install packages due to an EnvironmentError: [Errno 13] Permission denied
```

**Solutions:**
1. Use user installation instead:
   ```bash
   pip3 install --user .
   ```
2. Or use sudo for global:
   ```bash
   sudo pip3 install .
   ```

### Problem: Missing Dependencies

**Symptoms:**
```
ModuleNotFoundError: No module named 'click'
```

**Solution:**
```bash
# Install all dependencies
pip3 install click rich colorama flask numpy

# Or reinstall super-agents
pip3 install --user --force-reinstall .
```

---

## Runtime Errors

### Problem: TypeError When Running Commands

**Symptoms:**
```
TypeError: object of type 'PosixPath' has no len()
```

**Solution:**
Update to the latest version:
```bash
git pull
sudo pip3 install --force-reinstall .
```

### Problem: "Error: 'claude' command not found!"

**Symptoms:**
```
Error: 'claude' command not found!
Please ensure Claude Code is installed and in your PATH
```

**Solutions:**
1. Install Claude Code from https://claude.ai/code
2. Or use super-agents without Claude for agent management:
   ```bash
   super-agents init     # Still works
   super-agents status   # Still works
   super-agents monitor  # Still works
   ```

### Problem: Files Already Exist During Init

**Symptoms:**
```
⚠ The following files already exist:
  • CLAUDE.md
  • .claude/
```

**Solutions:**
1. Choose option 1 to backup and continue
2. Choose option 2 to skip existing files
3. Or clean up first:
   ```bash
   rm -rf .claude CLAUDE.md .super_agents_manifest.json
   super-agents init
   ```

---

## Knowledge Manager Issues

### Problem: Port Already in Use

**Symptoms:**
```
Failed to start Knowledge Manager
Address already in use
```

**Solutions:**
```bash
# List all running instances
super-agents list

# Stop the conflicting instance
cd /path/to/other/project
super-agents stop

# Or kill by port
kill $(lsof -ti:5001)  # Replace with actual port
```

### Problem: Knowledge Manager Not Starting

**Symptoms:**
```
Failed to start Knowledge Manager
Check .claude/logs/km_server.log for errors
```

**Solutions:**
1. Check Python dependencies:
   ```bash
   pip3 install flask numpy
   ```
2. Check the log file:
   ```bash
   cat .claude/logs/km_server.log
   ```
3. Try a different port:
   ```bash
   rm .claude/km.port
   super-agents  # Will allocate new port
   ```

### Problem: Knowledge Manager Not Responding

**Symptoms:**
```
Knowledge Manager started but not yet responding
```

**Solution:**
Wait a few seconds or check if firewall is blocking:
```bash
# Test manually
curl http://localhost:5001/health

# Check if process is running
ps aux | grep km_server
```

---

## Agent Issues

### Problem: Agents Not Found

**Symptoms:**
```
No AET agents found - initializing project...
```

**Solution:**
This is normal for new projects. Let it initialize:
```bash
super-agents init
```

### Problem: Agent Count Mismatch

**Symptoms:**
```
Partial agent configuration detected
```

**Solution:**
Upgrade to ensure all 23 agents are present:
```bash
super-agents upgrade
```

---

## Claude Integration

### Problem: Claude Doesn't Launch

**Symptoms:**
Nothing happens after "Launching Claude..."

**Solutions:**
1. Ensure Claude Code is installed:
   ```bash
   which claude
   ```
2. Install from https://claude.ai/code
3. Check if Claude is already running

### Problem: --wild Flag Not Working

**Symptoms:**
```
unrecognized arguments: --dangerously-skip-permissions
```

**Solution:**
Update Claude Code to the latest version that supports this flag.

---

## Platform-Specific Issues

### macOS Issues

#### Problem: pip Cache Warning with sudo
```
WARNING: The directory '/Users/username/Library/Caches/pip' or its parent directory is not owned or is not writable
```

**Solution:**
Use sudo with -H flag:
```bash
sudo -H pip3 install .
```

#### Problem: .zshrc vs .bashrc
**Solution:**
macOS uses zsh by default:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Linux Issues

#### Problem: python3 Not Found
**Solution:**
Install Python 3:
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip
```

### Windows (WSL) Issues

#### Problem: Line Ending Issues
**Solution:**
Configure git for Unix line endings:
```bash
git config --global core.autocrlf input
```

---

## Getting More Help

### Diagnostic Commands

Run these to gather information for bug reports:

```bash
# Version information
super-agents --version
python3 --version
pip3 --version

# Installation details
pip3 show super-agents

# Check PATH
echo $PATH

# List installed files
ls -la ~/.local/bin/super-agents  # or /usr/local/bin/super-agents

# Check logs
ls -la .claude/logs/
cat .claude/logs/km_server.log
```

### Reporting Issues

When reporting issues, include:
1. Error message (full traceback)
2. Operating system and version
3. Python version
4. Installation method used
5. Output of diagnostic commands above

Report issues at: https://github.com/yourusername/super-agents/issues

### Clean Reinstall

If all else fails, try a clean reinstall:

```bash
# Uninstall
pip3 uninstall super-agents
rm -f /usr/local/bin/super-agents
rm -f ~/.local/bin/super-agents

# Clean clone
cd ~
rm -rf super-agents
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Fresh install
./install.sh
```

---

## Quick Reference

### Essential Commands
```bash
# Update after git pull
sudo pip3 install --force-reinstall .

# Check what's installed
pip3 show super-agents

# Find the command
which super-agents

# Stop all Knowledge Managers
pkill -f km_server

# Remove all trigger files
rm -rf .claude/triggers/*

# Reset project
rm -rf .claude CLAUDE.md .super_agents_manifest.json
```

### Environment Variables
```bash
# Set custom port range
export SUPER_AGENTS_PORT_MIN=6000
export SUPER_AGENTS_PORT_MAX=6100

# Enable debug logging
export SUPER_AGENTS_DEBUG=1
```