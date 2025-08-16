# Knowledge Manager MCP Bridge - The Simple Way

## How It Works

Each project directory gets its own local KM server in `./.claude/km_server/`. That's it.

## Setup

1. **Install requests for Python** (one time):
```bash
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python -m pip install requests
```

2. **Update Claude config** to use simple wrapper:
```json
{
  "km": {
    "command": "/path/to/km_bridge_wrapper_simple.sh",
    "args": []
  }
}
```

## Usage

```bash
# In any project directory:
super-agents --wild

# This creates ./.claude/km_server/ with a local KM instance
# Claude automatically connects to it
```

## Multiple Projects

```bash
# Project A
cd /project-a
super-agents --wild  # Gets its own server in ./.claude/km_server/

# Project B  
cd /project-b
super-agents --wild  # Gets its own server in ./.claude/km_server/

# No conflicts, no coordination needed
```

## How It's Different

**Old way**: Complex port management, project IDs, file locking, etc.

**New way**: Just look for `./.claude/km_server/port` in current directory.

## Benefits

- **Dead simple** - 150 lines instead of 1000+
- **No coordination** - Each directory is independent
- **No conflicts** - Each project has its own server
- **No complexity** - No hashing, no locking, no managers

## Troubleshooting

**"No local KM server found"**
→ Run `super-agents --wild` in your project directory

**"Connection refused"**  
→ The server crashed. Run `super-agents --wild` again

That's literally it. No more complexity needed.