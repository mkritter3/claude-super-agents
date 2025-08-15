# AET System Enhancement Roadmap 2025

## Vision Statement
Systematically enhance the Autonomous Engineering Team (AET) system to become the industry-leading **Claude-native multi-agent platform** while preserving its core file-system-based architecture and extending it with MCP (Model Context Protocol) compatibility.

## Original Issues Being Addressed
**The problems that started this roadmap:**
1. ❌ `super-agents` command doesn't work in other directories (hardcoded paths)
2. ❌ Knowledge Manager fails to start even in source directory (import errors)
3. ❌ Multiple projects can't run simultaneously (port conflicts)
4. ❌ Global installation is brittle and breaks easily

**These are addressed as IMMEDIATE PRIORITY in Phase 1.2**

## Core Principles
- **Enhance, Don't Replace**: Build upon existing infrastructure
- **MCP Alignment**: Leverage Claude's native protocol for future compatibility
- **Backward Compatibility**: All improvements maintain existing workflows
- **Progressive Enhancement**: Each phase adds value independently
- **Production Stability**: Never compromise current functionality

---

## Phase 1: Stability & Robustness (Q1 2025)
**Goal**: Harden the existing system for production use at scale

### 1.1 Parallel Architecture: Batch + MCP 🆕 CRITICAL
**Goal**: Enable parallel operation of batch (async, high-volume) and MCP (real-time) agents

#### Batch Processing Lane (Async, Cost-Optimized)
- [ ] Implement Claude Batch API for bulk operations (100K requests/batch, 256MB limit)
- [ ] Create batch queue for test suites, docs generation, analysis
- [ ] Leverage 50% cost reduction for non-urgent operations
- [ ] Implement 1-hour cache duration for shared context (optimal for batch)
- [ ] Add batch result streaming with 29-day retention handling

#### MCP Real-time Lane (Synchronous, Immediate)
- [ ] Maintain MCP agents for critical path operations (pre-commit hooks)
- [ ] Ensure contract-guardian, security-agent remain real-time blocking
- [ ] Keep incident-response on MCP for sub-second response
- [ ] Preserve file-system triggers for autonomous real-time events

#### Smart Routing Logic
- [ ] Implement task router to decide batch vs MCP execution
- [ ] Add priority lanes: Critical (MCP) vs Bulk (Batch)
- [ ] Create unified result aggregation from both processing paths
- [ ] Ensure file-system message bus handles both streams

### 1.2 Global Installation & Multi-Project Support ✅ IMMEDIATE PRIORITY
**Critical**: Fix the original issues - run from any directory, support multiple independent projects

#### Two-Layer Architecture
**Global Layer** (One Installation):
- [ ] Single `/usr/local/bin/super-agents` command (like git, npm)
- [ ] Config file `~/.super-agents-config` stores source template location
- [ ] Source remains in original clone directory (e.g., ~/claude-super-agents)

**Project Layer** (Many Independent Projects):
- [ ] Each project gets its own `.claude/` directory when initialized
- [ ] Each project has independent state, ports, logs, databases
- [ ] Projects are fully isolated from each other

#### Path Resolution Fixes
- [ ] Replace hardcoded SOURCE_DIR with dynamic resolution (readlink -f)
- [ ] Store source template path in ~/.super-agents-config during install
- [ ] Fix KM startup to use PYTHONPATH instead of cd
- [ ] Ensure all agents use absolute paths within project directory

#### Dynamic Port Allocation (Per-Project Isolation)
- [ ] Implement port range 5001-5100 for KM instances
- [ ] Each project stores its own state in `.claude/state/km.port`, `km.pid`
- [ ] Add flock-based locking to prevent race conditions
- [ ] Auto-detect available ports with lsof
- [ ] Port allocation is project-specific, not global

#### Multi-Project Management
- [ ] Support concurrent projects with isolated resources
- [ ] Each project directory is self-contained after setup
- [ ] `super-agents status` shows KM status for current project
- [ ] `super-agents list --all` shows all projects with running KM instances
- [ ] No "switching" needed - just cd to project directory

### 1.3 Error Handling & Recovery
- [ ] Remove silent error suppression in database operations (critical for SQLite)
- [ ] Add comprehensive error logging with rotation
- [ ] Implement automatic recovery for common failures
- [ ] Add health check retries with exponential backoff
- [ ] Create error recovery playbooks for each agent

### 1.4 Process Management
- [ ] Add systemd/launchd service definitions for KM
- [ ] Implement graceful shutdown handlers
- [ ] Add zombie process cleanup
- [ ] Create process monitoring dashboard

### 1.5 Security Hardening
- [ ] Add input validation for all user inputs
- [ ] Implement secure credential storage
- [ ] Add audit logging for sensitive operations
- [ ] Create security scanning pre-commit hooks
- [ ] Implement agent permission boundaries

### 1.6 Autonomous Core Hardening 🆕
- [ ] Implement atomic file writes for trigger/state files (prevent corruption)
- [ ] Add checksums/validation for event log (.claude/events/log.ndjson)
- [ ] Develop recovery strategy for failed autonomous triggers
- [ ] Stress-test file system as message bus at scale
- [ ] Implement event log rotation and archival (prevent unbounded growth)
- [ ] Add integration testing harness for git operations → agent behavior

### 1.7 Model-Specific Agent Optimization 🆕 CRITICAL
**Note**: All models support batch processing per Anthropic docs

#### Model Assignment Strategy
- [ ] Configure Haiku 3.5 for filesystem-guardian, incident-response (fast response)
- [ ] Use Opus 4.1 for architect-agent, contract-guardian (complex reasoning)
- [ ] Implement Sonnet 4 for developer-agent, reviewer-agent (balanced performance)
- [ ] All models available for both batch and real-time operations

#### Fallback & Availability
- [ ] Add model fallback chains: Opus 4.1 → Sonnet 4 → Haiku 3.5
- [ ] Implement rate limit handling with exponential backoff
- [ ] Monitor model availability and auto-switch
- [ ] Create model selection matrix based on task complexity + urgency

**Deliverables**: 
- **Global installation working from ANY directory** ✅
- **Multiple concurrent projects with dynamic ports** ✅
- **No more hardcoded paths or ports** ✅
- Parallel batch + MCP architecture operational
- Smart routing between async batch and real-time MCP
- Model-optimized agent selection with fallbacks
- Zero-downtime deployments
- Complete error visibility

---

## Phase 2: Performance & Scalability (Q2 2025)
**Goal**: Optimize for speed and scale without changing core behavior

### 2.1 MCP Local Server Implementation 🆕 CRITICAL
**Note**: Per Anthropic docs, MCP connector requires HTTP/SSE for remote servers, STDIO for local

#### Local STDIO Servers (Development)
- [ ] Wrap each agent as MCP STDIO server for local development
- [ ] Implement MCP tool discovery protocol per spec
- [ ] Maintain file-system fallback for reliability

#### Remote HTTP/SSE Servers (Production)
- [ ] Prepare agents for HTTP/SSE transport (required for MCP connector)
- [ ] Add OAuth Bearer token support (per MCP connector spec)
- [ ] Implement beta header support: "anthropic-beta: mcp-client-2025-04-04"
- [ ] Note: Local STDIO cannot connect directly to Messages API

### 2.2 Knowledge Manager Optimization
- [ ] Add caching layer for frequent queries
- [ ] Implement connection pooling for database
- [ ] Add async processing for non-critical operations
- [ ] Optimize embedding generation pipeline
- [ ] Implement batch processing for multiple requests (leverage Claude's batch API patterns)

### 2.3 Agent Execution Optimization
- [ ] Add parallel agent execution where safe
- [ ] Implement agent result caching
- [ ] Create agent execution profiling
- [ ] Add smart agent selection based on task
- [ ] Optimize Context7 documentation fetching

### 2.4 Resource Management
- [ ] Add memory usage monitoring
- [ ] Implement automatic garbage collection
- [ ] Add disk space management
- [ ] Create resource usage alerts
- [ ] Implement rate limiting for expensive operations

### 2.5 Startup Performance
- [ ] Lazy load non-critical components
- [ ] Add dependency preloading
- [ ] Implement fast startup mode
- [ ] Cache agent definitions
- [ ] Optimize database initialization

### 2.6 MCP-Compatible Observability 🆕
- [ ] Inject unique correlation IDs (use MCP's tool_use_id format)
- [ ] Implement structured logging for all autonomous components
- [ ] Create CLI command to trace events by correlation ID
- [ ] Add MCP-style tool result blocks for agent responses
- [ ] Implement OpenTelemetry support (Claude standard)
- [ ] Create performance baselines for each agent

**Deliverables**:
- MCP-compatible agent servers (local STDIO)
- 50% reduction in startup time
- 3x improvement in concurrent project handling
- Sub-second agent response times
- Full event traceability with MCP correlation IDs

---

## Phase 3: Developer Experience (Q3 2025)
**Goal**: Make the system delightful to use while preserving existing workflows

### 3.1 CLI Enhancements
- [ ] Add interactive setup wizard (optional)
- [ ] Implement command autocomplete
- [ ] Add progress indicators for long operations
- [ ] Create helpful error messages with solutions
- [ ] Add `super-agents doctor` diagnostic command
- [ ] Add `super-agents status` command (show KM port, PID, health)

### 3.2 Configuration Management
- [ ] Add project templates for common setups
- [ ] Implement configuration validation
- [ ] Add configuration migration tools
- [ ] Create TUI (Text UI) configuration editor (defer web UI to future)
- [ ] Add configuration inheritance for multi-project
- [ ] Make port ranges configurable via environment variables

### 3.3 Debugging & Troubleshooting
- [ ] Add debug mode with verbose logging
- [ ] Implement agent execution tracing
- [ ] Add performance profiling commands
- [ ] Create troubleshooting knowledge base
- [ ] Add automatic issue detection and reporting

### 3.4 Documentation & Learning
- [ ] Add inline help for all commands
- [ ] Create interactive tutorials
- [ ] Add example projects repository
- [ ] Implement context-aware suggestions
- [ ] Create video walkthroughs

### 3.5 MCP Developer Tools 🆕
- [ ] Add agent versioning system (e.g., developer-agent_20250117)
- [ ] Create MCP spec endpoint for each agent (/mcp/spec)
- [ ] Add agent capability discovery command
- [ ] Implement batch task creation (.claude/aet create-batch)
- [ ] Add MCP inspector integration for agent debugging

**Deliverables**:
- 90% reduction in setup errors
- Self-documenting system
- Zero-friction onboarding
- MCP-compliant agent interfaces

---

## Phase 4: Advanced Features (Q4 2025)
**Goal**: Add powerful new capabilities as optional enhancements while maintaining file-system core

### 4.1 MCP Remote Server Support 🔄 CRITICAL
**Important**: MCP connector only supports HTTP/SSE transports, not STDIO (per Anthropic docs)

#### Production Remote Servers
- [ ] Add MCP HTTP/SSE server wrapper for each agent (required for Messages API)
- [ ] Implement OAuth Bearer token authentication (MCP connector standard)
- [ ] Add beta header support in all agent servers
- [ ] Create agent registry endpoint (/mcp/spec for discovery)
- [ ] Support multi-server connections in single request

#### Hybrid Architecture
- [ ] Implement hybrid mode: local file-system + remote MCP
- [ ] Batch operations via Batch API, real-time via MCP connector
- [ ] Support connecting to existing servers (Stripe, Linear, Notion)
- [ ] **Note**: File-system remains for local dev, MCP for production scale

### 4.2 Integration Ecosystem ✅ Priority
- [ ] Add GitHub Actions integration (high value, natural fit)
- [ ] Implement GitLab CI/CD support
- [ ] Add Slack/Discord notifications via webhooks
- [ ] Create Jenkins plugin
- [ ] Implement Azure DevOps integration
- [ ] Leverage Claude's batch API for CI/CD workflows

### 4.3 Batch Processing at Scale 🆕 CRITICAL
**Validated**: Batch API supports all features including tool use, vision, system messages

#### CI/CD Integration
- [ ] Implement batch queue for CI/CD pipelines (100K requests max)
- [ ] Add batch orchestration for test suites (respect 256MB limit)
- [ ] Handle 24-hour batch expiration gracefully
- [ ] Manage 29-day result retention window

#### Optimization & Recovery
- [ ] Implement 1-hour prompt caching for shared context
- [ ] Mix request types within single batch (tests + docs + analysis)
- [ ] Add batch failure recovery (expired vs errored vs canceled)
- [ ] Monitor rate limits for batch queue processing
- [ ] Leverage 50% cost savings across all agent operations

### 4.4 AI Enhancements ✅ Priority  
- [ ] Add agent learning from successful patterns
- [ ] Implement agent performance optimization
- [ ] Add predictive task routing based on history
- [ ] Create agent behavior analytics
- [ ] Implement adaptive agent selection
- [ ] Integrate with Claude's extended thinking for complex tasks

### 4.5 Advanced Monitoring (Defer to 2026)
- [ ] Real-time agent activity dashboard
- [ ] Predictive failure detection
- [ ] Cost tracking and optimization
- [ ] Performance regression detection
- [ ] SLA monitoring

### 4.6 Enterprise Features (Defer to Future Vision)
- [ ] Multi-tenant support
- [ ] RBAC for agents
- [ ] Compliance reporting
- [ ] Audit trail export
- [ ] SSO integration

**Deliverables**:
- MCP-compliant remote agent support (HTTP/SSE/OAuth)
- Batch processing at scale (100K requests, 50% cost reduction)
- Seamless CI/CD integration with batch orchestration
- Intelligent agent selection and routing
- 10x productivity gains through batch + MCP

---

## System Architecture

### Two-Layer Design: Global Command + Independent Projects

```
GLOBAL LAYER (One Installation):
~/.super-agents-config → /Users/you/claude-super-agents/ (source templates)
/usr/local/bin/super-agents → symlink to source

PROJECT LAYER (Many Independent Projects):
/Users/you/project-A/
  └── .claude/                 # Complete independent AET system
      ├── state/km.port (5001)  # Project A's port
      ├── state/km.pid          # Project A's process
      ├── system/               # Copied from templates
      ├── events/log.ndjson     # Project A's events
      └── registry/registry.db  # Project A's database

/Users/you/project-B/
  └── .claude/                 # Complete independent AET system
      ├── state/km.port (5002)  # Project B's port (different!)
      ├── state/km.pid          # Project B's process
      ├── system/               # Copied from templates
      ├── events/log.ndjson     # Project B's events
      └── registry/registry.db  # Project B's database

Each project is COMPLETELY ISOLATED - like separate git repositories
```

## Parallel Architecture Design

### How Batch and MCP Work Together

The AET system operates two parallel processing lanes that work simultaneously without blocking each other:

#### 1. **Batch Processing Lane** (Async, High-Volume, 50% Cost)
- **Technology**: Claude Batch API
- **Capacity**: 100K requests per batch, 256MB size limit
- **Timing**: Up to 24 hours completion, typically under 1 hour
- **Use Cases**:
  - CI/CD test suites (thousands of tests)
  - Bulk documentation generation
  - Large-scale code analysis
  - Performance benchmarking
- **Agents**: test-executor, documentation-agent, performance-optimizer

#### 2. **MCP Real-time Lane** (Sync, Immediate Response, Full Cost)
- **Technology**: MCP Protocol (HTTP/SSE for remote, STDIO for local)
- **Capacity**: Individual requests, sub-second response
- **Timing**: Immediate blocking operations
- **Use Cases**:
  - Pre-commit security checks (blocking)
  - API breaking change prevention
  - Incident response
  - Live development assistance
- **Agents**: contract-guardian, security-agent, incident-response

#### 3. **Smart Routing Decision Tree**
```
Request arrives → Is it blocking/critical?
  ├─ YES → MCP Real-time Lane
  │   └─ Examples: pre-commit hooks, security scans
  ├─ NO → Can it wait? Volume > 100?
  │   ├─ YES → Batch Processing Lane
  │   │   └─ Examples: test suites, bulk docs
  │   └─ NO → MCP Real-time Lane (default)
```

#### 4. **File System Message Bus**
Both lanes write to the same event log (`.claude/events/log.ndjson`), enabling:
- Unified audit trail
- Cross-lane coordination
- State synchronization
- Result aggregation

## Implementation Strategy

### Guiding Principles
1. **No Breaking Changes**: Every enhancement is backward compatible
2. **Feature Flags**: New features can be enabled/disabled
3. **Progressive Rollout**: Test with small groups first
4. **Continuous Validation**: Each change validated against existing tests
5. **Documentation First**: Document before implementing

### Release Cadence
- **Monthly**: Bug fixes and minor improvements
- **Quarterly**: Major feature releases
- **Continuous**: Security and critical fixes

### Success Metrics
- Zero regressions in existing functionality
- 95% user satisfaction score
- 50% reduction in support tickets
- 10x increase in concurrent users supported
- 90% of users adopt new features within 6 months

### Risk Mitigation
- Maintain feature branches for all major changes
- Automated testing for all enhancements
- Rollback procedures for every deployment
- User feedback loops at each phase
- Performance benchmarks before/after changes

---

## Quick Wins (Immediate Implementation)

### This Week - CRITICAL FIXES FIRST
**Priority 1: Fix Global Installation Issues**
1. Replace hardcoded SOURCE_DIR with dynamic path resolution
2. Store source template location in ~/.super-agents-config
3. Fix KM startup to use PYTHONPATH (no more cd)
4. Ensure super-agents copies templates to each project

**Priority 2: Per-Project Isolation**
5. Implement dynamic port allocation (5001-5100 range)
6. Store port/PID in each project's `.claude/state/` directory
7. Add flock-based locking per project
8. Each project gets independent KM instance

**Priority 3: Multi-Project Commands**
9. Add `super-agents status` (current project's KM)
10. Add `super-agents list --all` (find all projects with KM)
11. Support multiple concurrent isolated projects

**Priority 4: Stability Improvements**
12. Add timeout to curl health checks (--max-time 10)
13. Fix SQLite error suppression (remove 2>/dev/null || true)
14. Add better error messages for missing dependencies

### Next Month  
1. Add `super-agents doctor` command
2. Implement basic progress indicators
3. Add configuration validation
4. Create example projects
5. Add debug mode flag
6. Implement log rotation for .claude/logs/km_server.log
7. Add MCP spec endpoint stub for future compatibility
8. Version agents with dates (e.g., developer-agent_20250117)
9. Create batch processing proof-of-concept for test suites
10. Implement MCP STDIO wrapper for one agent (developer-agent)

---

## Community Involvement

### Open Source Contributions
- [ ] Create contribution guidelines
- [ ] Set up issue templates
- [ ] Implement PR automation
- [ ] Create community Discord/Slack
- [ ] Host monthly community calls

### Feedback Channels
- GitHub Issues for bug reports
- Discussions for feature requests
- Discord for real-time help
- Monthly surveys for satisfaction
- Beta testing program for new features

---

## Appendix: Technical Debt to Address

### Known Issues (from Gemini validation)
1. **Critical**: Race condition in port allocation (Phase 1.1)
2. **High**: Silent SQLite failures (Phase 1.2)
3. **Medium**: Missing curl timeouts (Phase 1.2)
4. **Low**: Redundant sys.path operations (Phase 2.1)
5. **Low**: Hardcoded port ranges (Phase 3.2)

### Architecture Improvements
- Modularize agent definitions
- Create plugin architecture for extensions
- Implement event-driven agent communication
- Add dependency injection for testing
- Create agent behavior contracts

### Code Quality
- Add type hints to Python code
- Implement shellcheck for bash scripts
- Add comprehensive test coverage
- Create coding standards document
- Implement automated code review

---

## Conclusion

This roadmap enhances the AET system systematically without disrupting its current excellence. Each phase builds upon the previous, creating a compound effect of improvements while maintaining the system's core identity and functionality.

**Remember**: We're not rebuilding - we're refining a already powerful system into something extraordinary.

---

*Last Updated: January 2025*
*Version: 2.0.0* 
*Status: Active Development - Claude Infrastructure Aligned*

## Key Infrastructure Insights Applied

Based on comprehensive analysis of Claude's infrastructure documentation:

### Validated Capabilities
1. **Claude Batch API** - Confirmed: 100K requests/batch, 256MB limit, 50% cost reduction
2. **MCP Protocol** - Confirmed: HTTP/SSE required for remote (not STDIO), OAuth Bearer tokens
3. **Model Support** - Confirmed: All models (Haiku, Sonnet, Opus) support batch processing
4. **Parallel Operation** - Confirmed: Batch and MCP can run simultaneously without conflict
5. **Prompt Caching** - Confirmed: 1-hour cache duration optimal for batch operations
6. **Tool Use in Batch** - Confirmed: Full feature parity including tool use, vision, system messages

### Architecture Decisions Based on Documentation
- **Dual-lane processing**: Batch for volume, MCP for real-time
- **Transport requirements**: STDIO for local dev, HTTP/SSE for production
- **Authentication**: OAuth Bearer tokens for MCP connector compatibility
- **Beta headers**: Required for MCP connector ("anthropic-beta: mcp-client-2025-04-04")
- **Result retention**: 29-day window for batch results
- **Rate limits**: Separate limits for batch queue and HTTP requests

These validated insights ensure our roadmap aligns perfectly with Anthropic's actual capabilities while maintaining the robust file-system foundation.