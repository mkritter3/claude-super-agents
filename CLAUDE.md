# AET System Instructions for Claude

This is the Autonomous Engineering Team (AET) system - a production-ready implementation of multi-agent orchestration.

## System Overview

The AET system uses specialized agents to handle different phases of software development:
- **pm-agent**: Project planning and task decomposition
- **architect-agent**: System design and technical architecture
- **developer-agent**: Code implementation
- **reviewer-agent**: Code review and quality checks
- **qa-agent**: Testing and validation
- **integrator-agent**: Safe merging and integration

## How to Use the System

### Creating Tasks
```bash
./.claude/aet create "Your task description"
```

### Processing Tasks
```bash
# Process all pending tasks
./.claude/aet process

# Process in parallel
./.claude/aet process --parallel
```

### Monitoring
```bash
./.claude/aet status
./.claude/aet health
./.claude/aet metrics
```

## Agent Delegation

When you need to delegate to a specialized agent, the system will:
1. Create an isolated workspace
2. Assemble relevant context
3. Invoke the appropriate agent
4. Track progress in the event log
5. Commit changes after each phase

## Important Files

- `.claude/system/orchestrator.py` - Main orchestration engine
- `.claude/system/context_assembler.py` - Context integration layer
- `.claude/agents/*.md` - Agent definitions
- `.claude/events/log.ndjson` - Event log
- `.claude/registry/registry.db` - File registry database

## Safety Features

The system includes:
- Atomic operations with file locking
- Three-phase write protocol
- Workspace isolation
- Rollback capabilities
- Dead letter queue for failed tasks

## Best Practices

1. Always use the CLI commands rather than directly modifying system files
2. Monitor health scores before processing critical tasks
3. Create backups before major operations
4. Use parallel processing for independent tasks
5. Check the DLQ for failed tasks regularly

The system is designed to be self-managing and resilient to failures.