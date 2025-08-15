# PRD-Constitutional AI Integration Roadmap

## Overview

Transform the AET system from technical constitutional questionnaires to conversational PRD (Product Requirements Document) building. The PRD becomes the constitutional anchor that guides all development while users engage through natural product discovery conversations.

## Core Principles

- **PRD = Constitution**: Product requirements become the immutable source of truth
- **Conversational UX**: Users talk business, Claude handles architecture
- **Zero Breaking Changes**: Seamless integration with existing infrastructure
- **Progressive Enhancement**: Phased implementation with backward compatibility

---

## Phase 1: Foundation Refactor (Week 1)

### Task 1.1: Create PRD Structure
**File**: `.claude/system/prd_manager.py`
```python
class PRDManager:
    def load_prd(self, version_hash=None):
        """Load PRD from .claude/prd.yml or legacy constitution.yml"""
    
    def create_draft_prd(self, product_vision):
        """Create .claude/prd.draft.yml for conversational building"""
    
    def finalize_prd(self, draft_path):
        """Convert draft to final prd.yml and create git tag"""
```

### Task 1.2: Update Orchestrator for Backward Compatibility
**File**: `orchestrator.py` - modify initialization
```python
def __init__(self):
    # Existing code...
    self.prd_manager = PRDManager()
    
def load_project_constitution(self):
    """Check for prd.yml first, fallback to constitution.yml"""
    if Path(".claude/prd.yml").exists():
        return self.prd_manager.load_prd()
    elif Path(".claude/constitution.yml").exists():
        return self.load_legacy_constitution()
    else:
        return None  # New project needs initialization
```

### Task 1.3: Define PRD YAML Schema
**File**: `.claude/schemas/prd_schema.yml`
```yaml
# Example structure for validation
required_fields:
  - product_name
  - product_vision
  - user_personas
  - user_stories
  - non_functional_requirements
```

### Task 1.4: Create PRD Template System
**File**: `.claude/templates/prd_templates.yml`
```yaml
# App-type specific templates
mobile_app:
  default_nfrs:
    - "Responsive design for mobile devices"
    - "Offline capability for core features"
web_app:
  default_nfrs:
    - "Cross-browser compatibility"
    - "HTTPS encryption for all endpoints"
```

---

## Phase 2: Conversational PRD Builder (Week 2)

### Task 2.1: Implement Project Kickoff Mode
**File**: `orchestrator.py` - add new method
```python
def start_project_kickoff(self, initial_idea):
    """Begin conversational PRD building process"""
    conversation_state = {
        "phase": "vision_definition",
        "collected_data": {},
        "next_question": self.get_vision_question(initial_idea)
    }
    return conversation_state

def process_kickoff_response(self, response, conversation_state):
    """Process user response and advance conversation"""
    # Update collected_data
    # Determine next question
    # Return updated state
```

### Task 2.2: Create Conversation Flow Engine
**File**: `.claude/system/conversation_engine.py`
```python
class ConversationEngine:
    def __init__(self):
        self.question_sequences = self.load_question_templates()
    
    def get_next_question(self, phase, collected_data):
        """Determine next question based on conversation state"""
    
    def extract_prd_data(self, response, current_phase):
        """Convert natural language response to PRD components"""
    
    def generate_user_story(self, persona, goal, context):
        """Auto-generate user story from conversation data"""
```

### Task 2.3: Auto-Generate Technical Requirements
**File**: `orchestrator.py` - enhance with architect-agent integration
```python
def generate_nfrs(self, product_vision, user_stories, app_type):
    """Use architect-agent to generate non-functional requirements"""
    context = {
        "task": "generate_nfrs",
        "product_vision": product_vision,
        "user_stories": user_stories,
        "app_type": app_type
    }
    return self.invoke_agent("architect-agent", context)
```

### Task 2.4: Implement State Persistence
**File**: `.claude/system/conversation_state.py`
```python
class ConversationState:
    def save_draft(self, conversation_data):
        """Save to .claude/prd.draft.yml after each interaction"""
    
    def load_draft(self):
        """Resume interrupted conversation"""
    
    def validate_completeness(self):
        """Check if enough data collected to finalize PRD"""
```

---

## Phase 3: Deep Integration (Week 3)

### Task 3.1: Context-Aware Agent Delegation
**File**: `orchestrator.py` - enhance invoke_agent method
```python
def invoke_agent(self, agent_name: str, context: Dict):
    # Existing hallucination protection code...
    
    # Add PRD context
    task_related_stories = self.find_related_user_stories(context.get('task', ''))
    relevant_nfrs = self.get_relevant_nfrs(agent_name, context)
    
    enhanced_context = context.copy()
    enhanced_context['prd_context'] = {
        'product_vision': self.prd['product_vision'],
        'user_stories': task_related_stories,
        'nfrs': relevant_nfrs,
        'acceptance_criteria': self.extract_acceptance_criteria(task_related_stories)
    }
```

### Task 3.2: Upgrade Compliance Agent
**File**: `.claude/agents/compliance-agent.md` - enhance with PRD validation
```markdown
## PRD Compliance Validation

When validating artifacts:
1. Check against user story acceptance criteria
2. Verify adherence to relevant NFRs
3. Ensure implementation serves defined user personas
4. Flag any features not defined in current PRD version

## Validation Process
```bash
# Load PRD for current task
PRD_VERSION=$(get_prd_version_for_task $TICKET_ID)
USER_STORIES=$(extract_related_stories $TICKET_ID $PRD_VERSION)
NFRS=$(extract_relevant_nfrs $AGENT_NAME $PRD_VERSION)

# Validate artifact against PRD
validate_against_acceptance_criteria $ARTIFACT_PATH $USER_STORIES
validate_against_nfrs $ARTIFACT_PATH $NFRS
```

### Task 3.3: Enhance Hallucination Guard
**File**: `.claude/system/hallucination_guard.py` - add PRD grounding
```python
def verify_claims_with_evidence(self, claims: List[FactClaim], workspace_path: str):
    # Existing evidence verification...
    
    # Add PRD verification
    prd = self.load_current_prd()
    for claim in claims:
        if self.is_feature_claim(claim):
            if not self.claim_supported_by_prd(claim, prd):
                claim.confidence = 0.0
                claim.evidence_required = True
                claim.note = "Feature not defined in current PRD"
```

### Task 3.4: Update Agent Prompting
**File**: `orchestrator.py` - enhance context building
```python
def build_context_bundle(self, ticket_id: str, job_id: str, agent_name: str):
    # Existing context assembly...
    
    context['prd_guidance'] = f"""
    PRODUCT CONTEXT:
    Vision: {self.prd['product_vision']}
    
    RELEVANT USER STORIES:
    {self.format_user_stories_for_agent(ticket_id)}
    
    CONSTRAINTS (Must Follow):
    {self.format_nfrs_for_agent(agent_name)}
    
    Remember: Only implement features defined in user stories. 
    Flag any undefined requirements for PRD evolution.
    """
```

---

## Phase 4: PRD Evolution System (Week 4)

### Task 4.1: Implement Evolution Command
**File**: `orchestrator.py` - add evolution workflow
```python
def handle_evolution_request(self, evolution_idea: str):
    """Start conversational process for adding new feature/story"""
    current_prd = self.prd_manager.load_prd()
    
    conversation = self.conversation_engine.start_evolution_session(
        evolution_idea, 
        current_prd
    )
    
    return conversation
```

### Task 4.2: Git-Based Change Management
**File**: `.claude/system/prd_evolution.py`
```python
class PRDEvolution:
    def create_evolution_branch(self, new_story_id):
        """Create feature branch for PRD evolution"""
        branch_name = f"prd-evolution/{new_story_id}"
        subprocess.run(['git', 'checkout', '-b', branch_name])
    
    def create_evolution_pr(self, changes_summary, new_stories):
        """Create PR with PRD changes for human approval"""
        pr_body = self.format_evolution_pr_body(changes_summary, new_stories)
        subprocess.run(['gh', 'pr', 'create', '--title', f"Add {new_stories[0]['story_id']}", '--body', pr_body])
    
    def handle_evolution_merge(self):
        """Post-merge hook: tag new PRD version, emit events"""
        self.tag_new_prd_version()
        self.emit_prd_updated_event()
```

### Task 4.3: Automated Merge Handling
**File**: `.claude/hooks/post-merge` - enhance existing hook
```bash
#!/bin/bash
# Existing post-merge logic...

# Check if PRD was updated
if git diff HEAD~1 --name-only | grep -q ".claude/prd.yml"; then
    echo "PRD updated - triggering evolution workflow"
    python3 .claude/system/prd_evolution.py handle_merge
fi
```

### Task 4.4: Evolution State Management
**File**: `.claude/system/evolution_tracker.py`
```python
class EvolutionTracker:
    def track_pending_evolutions(self):
        """Track open PRs with PRD changes"""
    
    def validate_evolution_completeness(self, evolution_data):
        """Ensure new stories have required fields"""
    
    def merge_evolution_into_prd(self, approved_changes):
        """Update prd.yml with approved changes"""
```

---

## Integration Points & Testing

### Backward Compatibility Testing
```bash
# Test with existing constitution.yml project
cd existing_aet_project
./.claude/aet create "test task"  # Should work unchanged

# Test PRD migration
./.claude/aet migrate-to-prd  # Convert constitution.yml to prd.yml
```

### New Project Flow Testing
```bash
# Test conversational PRD creation
./.claude/aet create "photo sharing app for families"
# Should trigger conversational flow

# Test evolution
./.claude/aet evolve "users want to comment on photos"
# Should create PR with new user story
```

### Agent Integration Testing
```python
# Test agent receives PRD context
def test_agent_gets_prd_context():
    context = orchestrator.build_context_bundle("TICKET-001", "JOB-001", "developer-agent")
    assert 'prd_guidance' in context
    assert 'user_stories' in context['prd_guidance']
```

---

## Migration Strategy

### For Existing Projects
1. **Optional Migration**: Keep `constitution.yml` projects working
2. **Gradual Adoption**: Offer `./.claude/aet migrate-to-prd` for voluntary conversion
3. **Feature Parity**: Ensure all constitutional features work with PRD format

### For New Projects
1. **Mandatory PRD**: All new projects must complete conversational PRD building
2. **Smart Defaults**: Auto-generate technical requirements based on app type
3. **Guided Experience**: One question at a time, natural conversation flow

---

## Success Metrics

### User Experience
- Time to create new project: < 5 minutes conversational interaction
- User satisfaction: Can non-technical users successfully create PRDs?
- Completion rate: % of started PRD conversations that finish

### Technical Quality
- Agent adherence: % of agent outputs that comply with PRD requirements
- Scope drift: Reduction in features built outside defined user stories
- Constitutional violations: Zero technical requirement violations

### System Reliability
- Backward compatibility: 100% of existing projects continue working
- Migration success: Smooth constitution.yml → prd.yml transitions
- Performance impact: No degradation in agent response times

---

## Risk Mitigation

### Technical Risks
- **Breaking Changes**: Phased rollout with backward compatibility
- **Performance Impact**: Lazy loading of PRD context, caching
- **Data Loss**: Atomic file operations, git-based versioning

### User Experience Risks
- **Conversation Fatigue**: Keep initial PRD building under 10 questions
- **Technical Complexity**: Hide all architecture decisions from user
- **Evolution Friction**: Make adding features feel natural and fast

### Business Risks
- **Adoption Resistance**: Maintain existing workflows during transition
- **Feature Completeness**: Ensure PRD system has all constitutional capabilities
- **Scalability**: Design for projects with 100+ user stories

---

## Implementation Timeline

**Week 1**: Foundation refactor, backward compatibility
**Week 2**: Conversational PRD builder, question flow engine  
**Week 3**: Deep integration, agent context enhancement
**Week 4**: Evolution system, Git workflow automation

**Total Duration**: 4 weeks for complete transformation
**Rollout Strategy**: Gradual deployment with feature flags
**Testing Phase**: 1 week comprehensive testing before general availability