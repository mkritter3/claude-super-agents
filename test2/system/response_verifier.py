#!/usr/bin/env python3
"""
Response Verifier - Post-processes agent responses to validate claims and reduce hallucinations.

This system runs after agents complete their tasks to verify the accuracy of their responses
and flag potential hallucinations for human review.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from hallucination_guard import HallucinationGuard, FactClaim, Evidence
from logger_config import get_contextual_logger

@dataclass
class VerificationResult:
    """Result of verifying an agent's response."""
    agent_name: str
    ticket_id: str
    total_claims: int
    verified_claims: int
    unverified_claims: int
    confidence_score: float
    risk_level: str  # "low", "medium", "high", "critical"
    requires_human_review: bool
    issues: List[str]
    recommendations: List[str]

class ResponseVerifier:
    """
    Verifies agent responses after completion to catch hallucinations.
    
    This runs as a post-processing step to validate agent work and build
    confidence in autonomous operations.
    """
    
    def __init__(self):
        self.hallucination_guard = HallucinationGuard()
        self.logger = get_contextual_logger("response_verifier", component="verification")
        
        # Patterns that indicate high-confidence claims requiring verification
        self.high_confidence_patterns = [
            r"This (is|shows|indicates|demonstrates|proves)",
            r"The code (definitely|clearly|obviously)",
            r"According to the (file|implementation|code)",
            r"The (function|class|method) (does|is|has)",
            r"Based on (.+), (this|it|the)",
        ]
        
        # Patterns that suggest uncertainty (good - agents being honest)
        self.uncertainty_patterns = [
            r"I don't (know|have enough information)",
            r"(Unclear|Uncertain|Not sure) (if|whether|about)",
            r"(Might|Could|Possibly|Perhaps|Maybe)",
            r"Would need (more information|additional context)",
            r"Cannot (determine|confirm|verify) without"
        ]
    
    def verify_agent_response(self, agent_name: str, ticket_id: str, 
                            response_text: str, workspace_path: str,
                            verification_level: str = "evidence") -> VerificationResult:
        """
        Verify an agent's response for accuracy and evidence support.
        
        Args:
            agent_name: Name of the agent that provided the response
            ticket_id: Ticket ID for context
            response_text: The agent's response to verify
            workspace_path: Path to workspace for evidence checking
            verification_level: Level of verification required
            
        Returns:
            VerificationResult with confidence score and recommendations
        """
        
        self.logger.info("Verifying agent response", extra={
            'agent_name': agent_name,
            'ticket_id': ticket_id,
            'response_length': len(response_text),
            'verification_level': verification_level
        })
        
        # Extract claims from the response
        claims = self.hallucination_guard.extract_claims_from_response(
            response_text, agent_name, ticket_id
        )
        
        # Find evidence for claims
        evidence_map = self.hallucination_guard.verify_claims_with_evidence(
            claims, workspace_path
        )
        
        # Analyze response patterns
        confidence_indicators = self._analyze_confidence_patterns(response_text)
        uncertainty_indicators = self._analyze_uncertainty_patterns(response_text)
        
        # Calculate verification metrics
        total_claims = len(claims)
        verified_claims = len([claim for claim in claims 
                             if evidence_map.get(claim.claim, [])])
        unverified_claims = total_claims - verified_claims
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            verified_claims, total_claims, confidence_indicators, uncertainty_indicators
        )
        
        # Determine risk level
        risk_level = self._assess_risk_level(
            agent_name, unverified_claims, total_claims, confidence_score
        )
        
        # Check if human review is required
        requires_human_review = self._requires_human_review(
            agent_name, risk_level, unverified_claims, verification_level
        )
        
        # Generate issues and recommendations
        issues = self._identify_issues(claims, evidence_map, confidence_indicators)
        recommendations = self._generate_recommendations(
            agent_name, risk_level, issues, unverified_claims
        )
        
        # Log verification results
        self.logger.info("Verification complete", extra={
            'confidence_score': confidence_score,
            'risk_level': risk_level,
            'verified_claims': verified_claims,
            'total_claims': total_claims,
            'requires_review': requires_human_review
        })
        
        return VerificationResult(
            agent_name=agent_name,
            ticket_id=ticket_id,
            total_claims=total_claims,
            verified_claims=verified_claims,
            unverified_claims=unverified_claims,
            confidence_score=confidence_score,
            risk_level=risk_level,
            requires_human_review=requires_human_review,
            issues=issues,
            recommendations=recommendations
        )
    
    def _analyze_confidence_patterns(self, text: str) -> Dict[str, int]:
        """Analyze patterns that indicate high confidence claims."""
        indicators = {}
        
        for pattern in self.high_confidence_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            if matches > 0:
                indicators[pattern] = matches
        
        return indicators
    
    def _analyze_uncertainty_patterns(self, text: str) -> Dict[str, int]:
        """Analyze patterns that indicate appropriate uncertainty."""
        indicators = {}
        
        for pattern in self.uncertainty_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            if matches > 0:
                indicators[pattern] = matches
        
        return indicators
    
    def _calculate_confidence_score(self, verified_claims: int, total_claims: int,
                                  confidence_patterns: Dict, uncertainty_patterns: Dict) -> float:
        """Calculate overall confidence score for the response."""
        
        if total_claims == 0:
            # No claims made - safe but not very useful
            return 0.7
        
        # Base score from evidence verification
        evidence_score = verified_claims / total_claims
        
        # Adjust for confidence patterns (high confidence without evidence is bad)
        confidence_penalty = sum(confidence_patterns.values()) * 0.1
        if evidence_score < 0.5 and confidence_penalty > 0:
            evidence_score -= confidence_penalty
        
        # Reward appropriate uncertainty
        uncertainty_bonus = min(sum(uncertainty_patterns.values()) * 0.05, 0.2)
        evidence_score += uncertainty_bonus
        
        return max(0.0, min(1.0, evidence_score))
    
    def _assess_risk_level(self, agent_name: str, unverified_claims: int, 
                          total_claims: int, confidence_score: float) -> str:
        """Assess risk level based on agent and verification results."""
        
        # Critical agents with unverified claims are high risk
        critical_agents = {"contract-guardian", "security-agent", "database-agent", 
                          "data-migration-agent", "devops-agent"}
        
        if agent_name in critical_agents:
            if unverified_claims > 0 or confidence_score < 0.8:
                return "critical"
            elif confidence_score < 0.9:
                return "high"
        
        # General risk assessment
        if confidence_score < 0.3:
            return "critical"
        elif confidence_score < 0.5:
            return "high"
        elif confidence_score < 0.7:
            return "medium"
        else:
            return "low"
    
    def _requires_human_review(self, agent_name: str, risk_level: str, 
                              unverified_claims: int, verification_level: str) -> bool:
        """Determine if human review is required."""
        
        # Always require review for critical risk
        if risk_level == "critical":
            return True
        
        # Critical agents with any issues need review
        critical_agents = {"contract-guardian", "security-agent", "database-agent", 
                          "data-migration-agent", "devops-agent"}
        if agent_name in critical_agents and unverified_claims > 0:
            return True
        
        # High verification level with medium+ risk needs review
        if verification_level in ["critical", "consensus"] and risk_level in ["high", "medium"]:
            return True
        
        return False
    
    def _identify_issues(self, claims: List[FactClaim], evidence_map: Dict, 
                        confidence_patterns: Dict) -> List[str]:
        """Identify specific issues with the response."""
        issues = []
        
        # Check for unverified high-confidence claims
        for claim in claims:
            if claim.confidence > 0.8 and not evidence_map.get(claim.claim, []):
                issues.append(f"High-confidence claim without evidence: {claim.claim[:100]}...")
        
        # Check for excessive confidence patterns
        total_confidence_patterns = sum(confidence_patterns.values())
        if total_confidence_patterns > 5:
            issues.append(f"Excessive confidence language ({total_confidence_patterns} instances)")
        
        # Check for claims requiring evidence
        evidence_required_claims = [c for c in claims if c.evidence_required]
        unsupported_evidence_claims = [c for c in evidence_required_claims 
                                     if not evidence_map.get(c.claim, [])]
        
        if unsupported_evidence_claims:
            issues.append(f"{len(unsupported_evidence_claims)} claims requiring evidence lack support")
        
        return issues
    
    def _generate_recommendations(self, agent_name: str, risk_level: str, 
                                issues: List[str], unverified_claims: int) -> List[str]:
        """Generate recommendations based on verification results."""
        recommendations = []
        
        if risk_level in ["critical", "high"]:
            recommendations.append("Request human review before proceeding")
            
        if unverified_claims > 0:
            recommendations.append("Ask agent to provide file evidence for unsupported claims")
            
        if "confidence language" in str(issues):
            recommendations.append("Instruct agent to use more uncertain language when lacking evidence")
            
        if agent_name in ["contract-guardian", "security-agent", "database-agent"]:
            recommendations.append("Apply maximum verification level for critical operations")
            
        if not recommendations:
            recommendations.append("Response verified - proceed with confidence")
            
        return recommendations
    
    def save_verification_report(self, result: VerificationResult, output_path: str = None):
        """Save verification report to file."""
        
        if output_path is None:
            output_path = f".claude/verification/{result.ticket_id}_{result.agent_name}_verification.json"
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            "timestamp": Path().stat().st_mtime,  # Current time
            "agent_name": result.agent_name,
            "ticket_id": result.ticket_id,
            "verification_metrics": {
                "total_claims": result.total_claims,
                "verified_claims": result.verified_claims,
                "unverified_claims": result.unverified_claims,
                "confidence_score": result.confidence_score
            },
            "risk_assessment": {
                "risk_level": result.risk_level,
                "requires_human_review": result.requires_human_review
            },
            "findings": {
                "issues": result.issues,
                "recommendations": result.recommendations
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info("Verification report saved", extra={
            'output_path': output_path,
            'risk_level': result.risk_level
        })

# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python response_verifier.py <agent_name> <ticket_id> <response_file> [workspace_path]")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    ticket_id = sys.argv[2]
    response_file = sys.argv[3]
    workspace_path = sys.argv[4] if len(sys.argv) > 4 else ".claude/workspaces"
    
    verifier = ResponseVerifier()
    
    with open(response_file, 'r') as f:
        response_text = f.read()
    
    result = verifier.verify_agent_response(
        agent_name, ticket_id, response_text, workspace_path
    )
    
    print(f"Verification Result for {agent_name}:")
    print(f"Confidence Score: {result.confidence_score:.2f}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Requires Review: {result.requires_human_review}")
    print(f"Issues: {len(result.issues)}")
    print(f"Recommendations: {len(result.recommendations)}")
    
    verifier.save_verification_report(result)