# Super-Agents 🤖

Transform Claude Code into an autonomous engineering team with 23 specialized AI agents.

## Quick Install

```bash
# 1. Clone this repository
git clone https://github.com/yourusername/super-agents.git
cd super-agents

# 2. Install pipx (a tool for installing Python apps)
python3 -m pip install --user pipx

# 3. Install super-agents
python3 -m pipx install .

# 4. Reload your terminal or run:
source ~/.zshrc  # Mac
source ~/.bashrc # Linux
```

That's it! Now you can use `super-agents` from any folder.

## Usage

```bash
# Initialize a project with AI agents
super-agents init

# Launch Claude with agents
super-agents

# Launch with special permissions
super-agents --wild

# Check status
super-agents status
```

## Upgrading

When you pull new changes:
```bash
cd super-agents
git pull
python3 -m pipx reinstall super-agents
```

## Uninstalling

```bash
python3 -m pipx uninstall super-agents
```

## What This Does

Gives you 23 specialized AI agents that work with Claude:
- Writes code
- Reviews pull requests  
- Fixes bugs
- Manages deployments
- And much more!

## Requirements

- Python 3.8 or newer (check with `python3 --version`)
- Git
- Claude Code (optional, for launching Claude)

## Troubleshooting

If `super-agents` command not found:
```bash
# Make sure pipx is in your PATH
python3 -m pipx ensurepath
source ~/.zshrc  # or ~/.bashrc on Linux

# Or just run directly with Python
python3 -m pipx run super-agents
```

## License

MIT