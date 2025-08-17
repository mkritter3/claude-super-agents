#!/usr/bin/env python3
"""
Hallucination Guard - Reduces AI hallucinations in autonomous engineering operations.

This system implements multiple verification strategies to ensure the autonomous
agents provide accurate, grounded responses based on actual codebase evidence.
"""

import json
import re
import hashlib
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path
import sqlite3
from dataclasses import dataclass
from enum import Enum

class VerificationLevel(Enum):
    BASIC = "basic"           # Simple fact checking
    EVIDENCE = "evidence"     # Require code/file evidence  
    CONSENSUS = "consensus"   # Multi-agent verification
    CRITICAL = "critical"     # Maximum verification for critical operations

@dataclass
class FactClaim:
    """A factual claim made by an agent that needs verification."""
    claim: str
    agent: str
    evidence_required: bool
    context: str
    confidence: float
    ticket_id: str

@dataclass
class Evidence:
    """Evidence supporting or refuting a claim."""
    source_file: str
    line_numbers: List[int]
    quote: str
    quote_hash: str
    verification_status: str  # "supports", "refutes", "neutral"

class HallucinationGuard:
    """
    Central hallucination reduction system for AET agents.
    
    Implements strategies from claude-infrastructure/reduce-hallucinations.md:
    - Allow agents to say "I don't know"
    - Require direct quotes for factual grounding
    - Verify with citations
    - Chain-of-thought verification
    - External knowledge restriction
    """
    
    def __init__(self, workspace_path: str = None):
        self.workspace_path = Path(workspace_path or ".claude/workspaces")
        self.db_path = Path(".claude/registry/hallucination_guard.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._initialize_db()
        
        # High-risk operations requiring maximum verification
        self.critical_operations = {
            "schema_changes", "api_modifications", "security_updates",
            "database_migrations", "deployment_configs", "breaking_changes"
        }
        
        # Agents that handle critical operations
        self.critical_agents = {
            "contract-guardian", "data-migration-agent", "security-agent",
            "database-agent", "devops-agent"
        }
    
    def _initialize_db(self):
        """Initialize hallucination tracking database."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS fact_claims (
                claim_id TEXT PRIMARY KEY,
                claim_text TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                ticket_id TEXT NOT NULL,
                confidence REAL NOT NULL,
                verification_level TEXT NOT NULL,
                evidence_required BOOLEAN NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                verification_status TEXT, -- "verified", "refuted", "insufficient_evidence"
                verification_notes TEXT
            );
            
            CREATE TABLE IF NOT EXISTS evidence_items (
                evidence_id TEXT PRIMARY KEY,
                claim_id TEXT NOT NULL,
                source_file TEXT NOT NULL,
                line_start INTEGER,
                line_end INTEGER,
                quote_text TEXT NOT NULL,
                quote_hash TEXT NOT NULL,
                verification_status TEXT NOT NULL, -- "supports", "refutes", "neutral"
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES fact_claims (claim_id)
            );
            
            CREATE TABLE IF NOT EXISTS verification_sessions (
                session_id TEXT PRIMARY KEY,
                ticket_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                verification_level TEXT NOT NULL,
                total_claims INTEGER DEFAULT 0,
                verified_claims INTEGER DEFAULT 0,
                refuted_claims INTEGER DEFAULT 0,
                insufficient_evidence INTEGER DEFAULT 0,
                confidence_score REAL,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_claims_agent ON fact_claims(agent_name);
            CREATE INDEX IF NOT EXISTS idx_claims_ticket ON fact_claims(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_claim ON evidence_items(claim_id);
        """)
        self.conn.commit()
    
    def get_verification_requirements(self, agent: str, operation_type: str, 
                                    ticket_id: str) -> VerificationLevel:
        """Determine required verification level based on agent and operation."""
        
        if agent in self.critical_agents or operation_type in self.critical_operations:
            return VerificationLevel.CRITICAL
        
        if operation_type in ["code_changes", "architecture_decisions", "api_design"]:
            return VerificationLevel.EVIDENCE
        
        if operation_type in ["review", "analysis", "planning"]:
            return VerificationLevel.CONSENSUS
        
        return VerificationLevel.BASIC
    
    def create_verification_prompt(self, base_prompt: str, verification_level: VerificationLevel,
                                 agent: str, workspace_files: List[str] = None) -> str:
        """
        Enhance agent prompts with hallucination reduction instructions.
        
        Implements strategies from the reduce-hallucinations guide.
        """
        
        verification_instructions = {
            VerificationLevel.BASIC: """
VERIFICATION REQUIREMENTS:
- If you're unsure about any aspect, say "I don't have enough information to confidently assess this."
- Base your response only on the provided context and files.
- Do not use general knowledge that isn't supported by the workspace.
""",
            
            VerificationLevel.EVIDENCE: """
EVIDENCE-BASED VERIFICATION REQUIREMENTS:
1. For any factual claim about the codebase, provide direct quotes from files as evidence.
2. Format evidence as: [File: path/to/file.ext, Lines: X-Y] "exact quote here"
3. If you cannot find supporting evidence in the provided files, state: "No evidence found in workspace for this claim."
4. Only make claims that can be directly supported by code, comments, or documentation in the workspace.
5. If uncertain about any aspect, explicitly state your uncertainty level.
""",
            
            VerificationLevel.CONSENSUS: """
CONSENSUS VERIFICATION REQUIREMENTS:
1. Provide step-by-step reasoning for your conclusions.
2. For each major claim, provide supporting evidence from the workspace.
3. Identify areas where you need additional information or agent consultation.
4. Rate your confidence level (1-10) for each significant conclusion.
5. Flag any assumptions you're making that aren't directly supported by evidence.
""",
            
            VerificationLevel.CRITICAL: """
CRITICAL OPERATION - MAXIMUM VERIFICATION:
1. EVIDENCE REQUIRED: Every factual claim must have direct file/line evidence.
2. UNCERTAINTY ACKNOWLEDGMENT: Explicitly state confidence levels and unknowns.
3. STEP-BY-STEP REASONING: Show your analytical process clearly.
4. ASSUMPTION FLAGGING: Mark all assumptions as [ASSUMPTION: ...].
5. QUOTE VERIFICATION: After your response, verify each claim by finding supporting quotes.
6. RETRACTION PROTOCOL: If you cannot find supporting evidence for a claim, retract it and mark with [RETRACTED: insufficient evidence].
7. EXTERNAL KNOWLEDGE RESTRICTION: Only use information from the provided workspace.

This is a CRITICAL OPERATION. Accuracy is paramount. When in doubt, request human review.
"""
        }
        
        # Add file context if provided
        file_context = ""
        if workspace_files:
            file_context = f"""
AVAILABLE WORKSPACE FILES:
{chr(10).join(f"- {file}" for file in workspace_files[:20])}
{"- ... and more" if len(workspace_files) > 20 else ""}

"""
        
        enhanced_prompt = f"""
{verification_instructions[verification_level]}

{file_context}ORIGINAL TASK:
{base_prompt}

Remember: It's better to admit uncertainty than to provide unverified information.
"""
        
        return enhanced_prompt
    
    def extract_claims_from_response(self, response: str, agent: str, 
                                   ticket_id: str) -> List[FactClaim]:
        """Extract factual claims from agent responses for verification."""
        
        # Patterns that indicate factual claims
        claim_patterns = [
            r"The (\w+) function (does|is|has|contains) (.+)",
            r"This file (contains|implements|defines) (.+)",
            r"The code (shows|indicates|demonstrates) (.+)",
            r"Based on (.+), the (.+)",
            r"The current implementation (.+)",
            r"This pattern (suggests|indicates|shows) (.+)"
        ]
        
        claims = []
        for pattern in claim_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                claim_text = match.group(0)
                claim_id = hashlib.md5(f"{agent}:{ticket_id}:{claim_text}".encode()).hexdigest()[:12]
                
                # Estimate confidence based on language used
                confidence = self._estimate_confidence(claim_text)
                evidence_required = confidence > 0.7  # High confidence claims need evidence
                
                claims.append(FactClaim(
                    claim=claim_text,
                    agent=agent,
                    evidence_required=evidence_required,
                    context=response[:200] + "..." if len(response) > 200 else response,
                    confidence=confidence,
                    ticket_id=ticket_id
                ))
        
        return claims
    
    def _estimate_confidence(self, claim_text: str) -> float:
        """Estimate confidence level based on language patterns."""
        
        high_confidence_words = ["definitely", "clearly", "obviously", "certainly", "always"]
        medium_confidence_words = ["likely", "probably", "appears", "seems", "suggests"]
        low_confidence_words = ["might", "could", "possibly", "maybe", "uncertain"]
        
        text_lower = claim_text.lower()
        
        if any(word in text_lower for word in high_confidence_words):
            return 0.9
        elif any(word in text_lower for word in medium_confidence_words):
            return 0.6
        elif any(word in text_lower for word in low_confidence_words):
            return 0.3
        else:
            return 0.7  # Default medium-high confidence
    
    def verify_claims_with_evidence(self, claims: List[FactClaim], 
                                  workspace_path: str) -> Dict[str, List[Evidence]]:
        """Verify claims by finding supporting evidence in workspace files."""
        
        evidence_map = {}
        workspace = Path(workspace_path)
        
        for claim in claims:
            if not claim.evidence_required:
                continue
                
            evidence_items = []
            
            # Search for evidence in code files
            for file_path in workspace.rglob("*"):
                if file_path.is_file() and file_path.suffix in ['.py', '.js', '.ts', '.md', '.json', '.yaml', '.yml']:
                    try:
                        content = file_path.read_text(encoding='utf-8')
                        evidence = self._find_evidence_in_file(claim.claim, content, str(file_path))
                        evidence_items.extend(evidence)
                    except (UnicodeDecodeError, IOError):
                        continue
            
            evidence_map[claim.claim] = evidence_items
        
        return evidence_map
    
    def _find_evidence_in_file(self, claim: str, file_content: str, file_path: str) -> List[Evidence]:
        """Find evidence for a claim within a specific file."""
        
        evidence_items = []
        lines = file_content.split('\n')
        
        # Extract key terms from claim for searching
        claim_words = re.findall(r'\b\w+\b', claim.lower())
        claim_words = [word for word in claim_words if len(word) > 3]  # Filter short words
        
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check if line contains multiple key terms from the claim
            matching_words = sum(1 for word in claim_words if word in line_lower)
            
            if matching_words >= min(2, len(claim_words)):  # At least 2 words or all words if < 2
                # Extract context (3 lines before and after)
                start_line = max(0, i - 1)
                end_line = min(len(lines), i + 2)
                context_lines = lines[start_line:end_line]
                quote = '\n'.join(context_lines)
                
                quote_hash = hashlib.md5(quote.encode()).hexdigest()[:8]
                
                evidence_items.append(Evidence(
                    source_file=file_path,
                    line_numbers=list(range(start_line + 1, end_line + 1)),  # 1-indexed
                    quote=quote,
                    quote_hash=quote_hash,
                    verification_status="supports"  # Default, could be refined
                ))
        
        return evidence_items
    
    def create_verification_report(self, ticket_id: str, agent: str) -> Dict:
        """Generate a verification report for an agent's work on a ticket."""
        
        cursor = self.conn.cursor()
        
        # Get claims for this ticket/agent
        cursor.execute("""
            SELECT * FROM fact_claims 
            WHERE ticket_id = ? AND agent_name = ?
        """, (ticket_id, agent))
        
        claims = [dict(row) for row in cursor.fetchall()]
        
        # Get evidence for these claims
        evidence_map = {}
        for claim in claims:
            cursor.execute("""
                SELECT * FROM evidence_items 
                WHERE claim_id = ?
            """, (claim['claim_id'],))
            evidence_map[claim['claim_id']] = [dict(row) for row in cursor.fetchall()]
        
        # Calculate verification statistics
        total_claims = len(claims)
        verified_claims = len([c for c in claims if c['verification_status'] == 'verified'])
        refuted_claims = len([c for c in claims if c['verification_status'] == 'refuted'])
        insufficient_evidence = len([c for c in claims if c['verification_status'] == 'insufficient_evidence'])
        
        confidence_score = verified_claims / total_claims if total_claims > 0 else 0
        
        return {
            "ticket_id": ticket_id,
            "agent": agent,
            "total_claims": total_claims,
            "verified_claims": verified_claims,
            "refuted_claims": refuted_claims,
            "insufficient_evidence": insufficient_evidence,
            "confidence_score": confidence_score,
            "claims": claims,
            "evidence": evidence_map,
            "recommendation": self._get_recommendation(confidence_score, refuted_claims)
        }
    
    def _get_recommendation(self, confidence_score: float, refuted_claims: int) -> str:
        """Get recommendation based on verification results."""
        
        if refuted_claims > 0:
            return "REVIEW REQUIRED: Agent made claims that were refuted by evidence."
        elif confidence_score < 0.5:
            return "CAUTION: Low confidence score. Request additional verification."
        elif confidence_score < 0.8:
            return "ACCEPTABLE: Moderate confidence. Consider human review for critical operations."
        else:
            return "HIGH CONFIDENCE: Agent responses well-supported by evidence."
    
    def save_verification_session(self, session_data: Dict):
        """Save verification session results to database."""
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO verification_sessions
            (session_id, ticket_id, agent_name, verification_level, 
             total_claims, verified_claims, refuted_claims, insufficient_evidence, 
             confidence_score, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            session_data['session_id'],
            session_data['ticket_id'],
            session_data['agent'],
            session_data.get('verification_level', 'basic'),
            session_data['total_claims'],
            session_data['verified_claims'],
            session_data['refuted_claims'],
            session_data['insufficient_evidence'],
            session_data['confidence_score']
        ))
        
        self.conn.commit()

def create_hallucination_resistant_prompt(agent_name: str, task_description: str, 
                                         verification_level: str = "evidence",
                                         workspace_files: List[str] = None) -> str:
    """
    Factory function to create hallucination-resistant prompts for agents.
    
    This is the main interface for the orchestrator to use.
    """
    
    guard = HallucinationGuard()
    level = VerificationLevel(verification_level)
    
    return guard.create_verification_prompt(
        base_prompt=task_description,
        verification_level=level,
        agent=agent_name,
        workspace_files=workspace_files
    )

if __name__ == "__main__":
    # Example usage and testing
    guard = HallucinationGuard()
    
    # Test prompt enhancement
    base_prompt = "Analyze the user authentication system and recommend improvements."
    enhanced = guard.create_verification_prompt(
        base_prompt, 
        VerificationLevel.EVIDENCE, 
        "security-agent"
    )
    
    print("Enhanced prompt:")
    print(enhanced)