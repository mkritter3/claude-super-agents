# Super-Agents 🤖

Transform Claude Code into an autonomous engineering team with 23 specialized AI agents.

## Installation

### Recommended: Using pipx (Clean & Isolated)

```bash
# Install pipx if you don't have it
python3 -m pip install --user pipx
python3 -m pipx ensurepath

# Install super-agents
pipx install git+https://github.com/yourusername/super-agents.git
```

### Alternative: Using pip

```bash
# Install from repository
python3 -m pip install --user git+https://github.com/yourusername/super-agents.git
```

**Note:** You may need to add `~/.local/bin` to your PATH.

## Usage

After installation, use from ANY directory:

```bash
# Initialize project with AET agents
super-agents init

# Launch Claude with agents
super-agents

# Launch with --dangerously-skip-permissions
super-agents --wild

# Show status
super-agents status
```

## Upgrading

```bash
# With pipx
pipx upgrade super-agents

# With pip
python3 -m pip install --user --upgrade git+https://github.com/yourusername/super-agents.git
```

## Uninstalling

```bash
# With pipx
pipx uninstall super-agents

# With pip
python3 -m pip uninstall super-agents
```

## What You Get

- **23 Specialized Agents**: Complete engineering team coverage
- **Autonomous Operations**: Git hooks trigger agents automatically
- **Universal Command**: Works from any directory after installation
- **Dynamic Ports**: Multiple projects can run simultaneously (ports 5001-5100)

## Requirements

- Python 3.8+
- Git
- Claude Code (optional, for launching Claude)

## Development

For contributors:

```bash
# Clone repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# Install in development mode
pip install -e .

# Install dev dependencies
pip install -r requirements-dev.txt
```

## License

MIT