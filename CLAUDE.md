# Local AET System Configuration

This project has a complete local AET (Autonomous Engineering Team) system configured.

## Components

- **23 Specialized Agents** in `.claude/agents/`
- **Local Knowledge Manager** in `.claude/km_server/`
- **Event System** in `.claude/events/`
- **Git Hooks** in `.claude/hooks/`
- **MCP Bridge** in `.claude/km_bridge_local.py`

## Status

Run `./.claude/aet_status.sh` to check system health.

## Usage

The system is already running. Claude Code will automatically:
1. Connect to the local Knowledge Manager
2. Use the 23 specialized agents
3. Track events and triggers
4. Apply autonomous operations

## Restart if Needed

```bash
./setup_local_aet.sh
```

This ensures everything is running properly.
