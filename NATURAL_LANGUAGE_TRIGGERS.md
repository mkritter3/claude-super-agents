# Natural Language Agent Triggering Enhancement

## Current State Analysis

### How Zen-MCP Works
The zen-mcp-server uses **descriptive tool descriptions** that Claude's infrastructure automatically matches to user intents:

```python
def get_description(self) -> str:
    return (
        "GENERAL CHAT & COLLABORATIVE THINKING - Use the AI model as your thinking partner! "
        "Perfect for: bouncing ideas during your own analysis, getting second opinions..."
        "Use this when you want to ask questions, brainstorm ideas, get opinions..."
    )
```

Key patterns:
- **Trigger phrases** embedded in descriptions
- **Use cases** explicitly listed
- **Keywords** that match common user phrases

### How Our Agents Currently Work
Our agents have brief descriptions in their frontmatter:
```yaml
description: "The Project Manager. Decomposes high-level user requests into actionable, technical plans."
```

Only `test-executor` has natural language examples with `<example>` blocks.

## Implementation Strategy

Based on Claude's infrastructure documentation, we can enhance our agents in **two ways**:

### 1. Enhanced Descriptions (Immediate - No Code Changes)
Add trigger phrases and use cases to agent descriptions:

```yaml
---
name: pm-agent
description: "PROJECT PLANNING & TASK DECOMPOSITION - The Project Manager. Perfect for: breaking down features, creating project plans, defining requirements, task prioritization. Use this when you need to plan a new feature, create a roadmap, break down complex tasks, or organize work. Triggers on: 'plan this', 'break down', 'create tasks', 'project plan', 'requirements'."
---
```

### 2. Example Blocks (Enhanced Triggering)
Add `<example>` blocks like test-executor:

```yaml
description: |
  The Project Manager. <example>
  Context: User wants to plan a new feature
  user: "I need to add authentication to my app"
  assistant: "I'll use the pm-agent to create a comprehensive plan"
  </example>
  <example>
  user: "plan this feature"
  assistant: "Let me delegate to pm-agent for planning"
  </example>
```

## Proposed Agent Descriptions with Natural Language Triggers

### pm-agent
```yaml
description: "PROJECT PLANNING & REQUIREMENTS - Break down complex features into actionable tasks. Perfect for: feature planning, requirements gathering, task decomposition, roadmap creation. Use when: starting new projects, planning features, creating technical specifications, organizing work. Triggers: 'plan', 'break down', 'requirements', 'roadmap', 'tasks', 'project'."
```

### architect-agent
```yaml
description: "TECHNICAL ARCHITECTURE & DESIGN - Design system architecture and technical implementation. Perfect for: system design, API design, database schema, component structure. Use when: designing solutions, planning architecture, defining interfaces, structuring code. Triggers: 'design', 'architecture', 'structure', 'schema', 'API design'."
```

### developer-agent
```yaml
description: "CODE IMPLEMENTATION - Write production-ready code following specifications. Perfect for: implementing features, writing functions, creating components, coding solutions. Use when: implementing designs, writing new code, creating features, building functionality. Triggers: 'implement', 'code this', 'write', 'build', 'create function'."
```

### reviewer-agent
```yaml
description: "CODE REVIEW & QUALITY - Review code for quality, security, and best practices. Perfect for: code reviews, quality checks, security audits, performance analysis. Use when: reviewing pull requests, checking code quality, validating implementations. Triggers: 'review', 'check quality', 'audit', 'validate code'."
```

### contract-guardian
```yaml
description: "API & SCHEMA PROTECTION - Guard critical data contracts and prevent breaking changes. Perfect for: API changes, database migrations, schema updates, contract validation. Use when: modifying APIs, changing schemas, updating contracts. Triggers: 'API change', 'schema update', 'breaking change', 'migration'."
```

### dependency-agent
```yaml
description: "DEPENDENCY MANAGEMENT - Manage packages and dependencies across the project. Perfect for: package updates, dependency resolution, version management, security updates. Use when: adding packages, updating dependencies, resolving conflicts. Triggers: 'dependencies', 'packages', 'npm install', 'update packages'."
```

### integration-tester-agent
```yaml
description: "INTEGRATION TESTING - Run tests across affected components. Perfect for: integration tests, regression testing, cross-component validation. Use when: testing changes, validating integrations, running test suites. Triggers: 'integration test', 'run tests', 'test affected', 'regression'."
```

### filesystem-guardian-agent
```yaml
description: "SECURITY VALIDATION - Validate file operations and prevent security vulnerabilities. Perfect for: path validation, security checks, file access control. Use when: validating file paths, checking permissions, preventing attacks. Triggers: 'validate path', 'security check', 'file permission'."
```

### builder-agent
```yaml
description: "SYSTEM BUILDING - Build complete AET infrastructure and systems. Perfect for: system setup, infrastructure creation, tooling implementation. Use when: setting up new systems, building infrastructure, creating tools. Triggers: 'build system', 'setup infrastructure', 'create tools'."
```

### test-executor
Already has good examples - keep as is.

### integrator-agent
```yaml
description: "CODE INTEGRATION - Merge validated changes into main codebase. Perfect for: merging branches, integration workflows, conflict resolution. Use when: integrating features, merging code, resolving conflicts. Triggers: 'merge', 'integrate', 'combine branches'."
```

### verifier-agent
```yaml
description: "CONSISTENCY VERIFICATION - Audit file system against registry. Perfect for: consistency checks, registry validation, file verification. Use when: verifying state, checking consistency, auditing files. Triggers: 'verify', 'audit files', 'check consistency'."
```

## Implementation Benefits

1. **Natural Language Activation**: Users can say "review this code" instead of explicitly calling reviewer-agent
2. **Contextual Triggering**: Claude will understand intent and delegate appropriately
3. **Backward Compatible**: Existing explicit calls still work
4. **Progressive Enhancement**: Can add more examples over time

## How Claude's Infrastructure Handles This

Based on the official documentation:

1. **Tool Discovery**: Claude scans all available tools/agents
2. **Intent Matching**: Uses NLP to match user intent to tool descriptions
3. **Confidence Scoring**: Picks the best matching tool based on description
4. **Automatic Delegation**: Calls the Task tool with the appropriate agent

## Testing Natural Language Triggers

After implementation, test with phrases like:
- "plan this authentication feature" → pm-agent
- "review my latest changes" → reviewer-agent
- "check my dependencies" → dependency-agent
- "design the database schema" → architect-agent
- "implement the login function" → developer-agent

## Next Steps

1. Update all agent descriptions with trigger phrases
2. Add example blocks for critical agents
3. Test natural language activation
4. Document common trigger phrases for users
5. Consider adding a "routing agent" that specializes in delegation