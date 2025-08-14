#!/usr/bin/env python3
"""
Context Integration Layer - Connects all systems for intelligent context assembly.
This is what makes the AET system actually functional.
"""

import json
import time
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Set, Optional
from reliability import CircuitBreaker, RetryStrategy
from logger_config import get_contextual_logger, log_system_event

class ContextAssembler:
    """
    The critical integration layer that connects:
    - Knowledge Manager (semantic search)
    - File Registry (dependency tracking)
    - Event Log (history)
    - Workspaces (actual files)
    """
    
    def __init__(self):
        self.km_url = "http://localhost:5001/mcp"
        self.file_registry = None  # Will be initialized when FileRegistry exists
        self.event_logger = None  # Will be initialized when EventLogger exists
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.fallback_cache = {}  # Cache for fallback context
        self.fallback_cache_ttl = 3600  # 1 hour for fallback cache
        self.logger = get_contextual_logger("context_assembler", component="context_assembler")
        
        # Circuit breaker for Knowledge Manager
        self.km_circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception
        )
        
    def assemble_intelligent_context(self, 
                                    ticket_id: str,
                                    job_id: str,
                                    agent_type: str,
                                    max_tokens: int = 50000) -> Dict:
        """
        THIS METHOD IS THE HEART OF THE SYSTEM!
        Queries all systems and assembles exactly what each agent needs.
        """
        
        # Update logger context
        self.logger = get_contextual_logger("context_assembler", 
                                           ticket_id=ticket_id, 
                                           job_id=job_id, 
                                           agent=agent_type,
                                           component="context_assembler")
        
        self.logger.info("Starting context assembly", extra={
            'max_tokens': max_tokens,
            'agent_type': agent_type
        })
        
        # Check cache first
        cache_key = f"{ticket_id}_{agent_type}_{job_id}"
        if self._check_cache(cache_key):
            self.logger.info("Using cached context")
            return self.cache[cache_key]['data']
        
        context = {}
        
        # 1. SEMANTIC SEARCH - Ask KM what's relevant
        context['knowledge'] = self._query_knowledge_manager(
            ticket_id, agent_type
        )
        
        # 2. DEPENDENCY GRAPH - Find related files
        context['dependencies'] = list(self._get_file_dependencies(
            ticket_id, agent_type
        ))
        
        # 3. COMPONENT APIS - Get interfaces agent might need
        context['apis'] = self._get_relevant_apis(
            context['dependencies']
        )
        
        # 4. SMART FILE LOADING - Load only what's needed
        context['files'] = self._load_relevant_files(
            job_id,
            context['dependencies'],
            agent_type,
            max_tokens
        )
        
        # 5. DECISION HISTORY - Get relevant ADRs
        context['decisions'] = self._get_relevant_decisions(
            ticket_id,
            context['knowledge']
        )
        
        # 6. WORKSPACE INFO
        context['workspace'] = {
            'path': f".claude/workspaces/{job_id}/workspace",
            'artifacts': f".claude/workspaces/{job_id}/artifacts",
            'job_id': job_id,
            'ticket_id': ticket_id
        }
        
        # Cache the result
        self._cache_result(cache_key, context)
        
        return context
    
    @RetryStrategy(max_attempts=3, backoff_base=2.0, exceptions=(requests.RequestException,))
    def _query_knowledge_manager(self, ticket_id: str, agent_type: str) -> Dict:
        """Query KM for semantic context relevant to this agent."""
        
        # Build agent-specific query
        queries = {
            'pm-agent': f"planning decisions for {ticket_id}",
            'architect-agent': f"architectural patterns and design for {ticket_id}",
            'developer-agent': f"implementation details and code patterns for {ticket_id}",
            'reviewer-agent': f"code standards and review criteria for {ticket_id}",
            'qa-agent': f"testing strategies and quality metrics for {ticket_id}"
        }
        
        query = queries.get(agent_type, f"relevant information for {ticket_id}")
        
        try:
            # Apply circuit breaker
            return self.km_circuit_breaker(self._make_km_request)(query, ticket_id)
        except Exception as e:
            self.logger.error(f"KM query failed after retries: {e}")
            return self._get_fallback_context(agent_type)
    
    def _make_km_request(self, query: str, ticket_id: str) -> Dict:
        """Make the actual request to Knowledge Manager."""
        self.logger.debug(f"Querying KM: {query}")
        
        response = requests.post(self.km_url, 
                               json={
                                   'tool_name': 'query',
                                   'tool_input': {
                                       'question': query,
                                       'ticket_id': ticket_id,
                                       'limit': 10
                                   }
                               },
                               timeout=10)
        
        if not response.ok:
            self.logger.warning(f"KM query failed: HTTP {response.status_code}")
            raise requests.RequestException(f"KM returned {response.status_code}")
        
        result = response.json()['tool_response']
        self.logger.debug("KM query successful")
        return result
    
    def _get_fallback_context(self, agent_type: str) -> Dict:
        """Provide degraded but functional context when KM unavailable."""
        self.logger.warning(f"Using fallback context for {agent_type}")
        
        # Strategy: Use cached context if available, otherwise minimal defaults
        cache_key = f"fallback_{agent_type}"
        
        # Check if we have recent fallback cache
        if self._check_fallback_cache(cache_key):
            self.logger.info(f"Using cached fallback context for {agent_type}")
            context = self.fallback_cache[cache_key]['data'].copy()
            context['fallback_mode'] = True
            context['fallback_reason'] = 'KM unavailable - using cache'
            return context
        
        # Return minimal functional context
        fallback_context = {
            'knowledge': {},
            'results': [],
            'fallback_mode': True,
            'fallback_reason': 'KM unavailable - using defaults'
        }
        
        # Cache this fallback for future use
        self._cache_fallback_result(cache_key, fallback_context)
        
        log_system_event("fallback_context_used", {
            "agent_type": agent_type,
            "reason": "KM unavailable"
        }, component="context_assembler")
        
        return fallback_context
    
    def _get_file_dependencies(self, ticket_id: str, agent_type: str) -> Set[str]:
        """Get the dependency graph for files this agent needs."""
        
        if not self.file_registry:
            # Try to initialize file registry if not available
            try:
                from file_registry import FileRegistry
                self.file_registry = FileRegistry()
            except:
                self.logger.debug("File registry not available, returning empty dependencies")
                return set()  # Registry not yet available
        
        # Query file registry for dependencies
        try:
            cursor = self.file_registry.conn.cursor()
            
            # Get files directly modified by this ticket
            cursor.execute("""
                SELECT DISTINCT path, component 
                FROM files 
                WHERE ticket_id = ?
            """, (ticket_id,))
        except Exception as e:
            self.logger.debug(f"Database query failed: {e}")
            return set()  # Database not ready
        
        try:
            direct_files = set()
            components = set()
            
            for row in cursor.fetchall():
                direct_files.add(row['path'])
                if row['component']:
                    components.add(row['component'])
        except Exception as e:
            self.logger.debug(f"Database result processing failed: {e}")
            return set()
        
        # Get file-level dependencies using new relationships table
        file_dependent = set()
        try:
            for file_path in direct_files:
                cursor.execute("""
                    SELECT target_file 
                    FROM file_relationships 
                    WHERE source_file = ? AND relationship_type IN ('imports', 'implements')
                """, (file_path,))
                
                for row in cursor.fetchall():
                    file_dependent.add(row['target_file'])
        except Exception as e:
            self.logger.debug(f"File relationships query failed: {e}")
        
        # Get component dependencies
        component_dependent = set()
        try:
            for component in components:
                cursor.execute("""
                    SELECT f.path FROM files f
                    JOIN dependencies d ON f.component = d.target_component
                    WHERE d.source_component = ?
                """, (component,))
                
                for row in cursor.fetchall():
                    component_dependent.add(row['path'])
        except Exception as e:
            self.logger.debug(f"Component dependencies query failed: {e}")
        
        # Get test files that test the modified files
        test_files = set()
        try:
            if direct_files:  # Only query if we have files to query for
                cursor.execute("""
                    SELECT source_file 
                    FROM file_relationships 
                    WHERE target_file IN ({}) AND relationship_type = 'tests'
                """.format(','.join('?' * len(direct_files))), list(direct_files))
                
                for row in cursor.fetchall():
                    test_files.add(row['source_file'])
        except Exception as e:
            self.logger.debug(f"Test files query failed: {e}")
        
        # Filter based on agent type
        if agent_type == 'pm-agent':
            # PM only needs high-level structure
            return {f for f in direct_files if 'README' in f or '.md' in f}
        elif agent_type == 'developer-agent':
            # Developer needs everything
            return direct_files | file_dependent | component_dependent
        elif agent_type == 'reviewer-agent':
            # Reviewer needs changed files + tests + dependencies
            return direct_files | test_files | file_dependent
        elif agent_type == 'qa-agent':
            # QA needs test files and what they test
            return direct_files | test_files
        else:
            return direct_files
    
    def _get_relevant_apis(self, file_dependencies: Set[str]) -> Dict:
        """Get API definitions for components the agent might use."""
        
        # Extract component names from file paths
        components = set()
        for path in file_dependencies:
            parts = Path(path).parts
            if 'components' in parts:
                idx = parts.index('components')
                if idx + 1 < len(parts):
                    component_name = parts[idx + 1].replace('.tsx', '').replace('.jsx', '')
                    components.add(component_name)
        
        # Query KM for each component's API
        apis = {}
        for component in components:
            try:
                response = requests.post(self.km_url, json={
                    'tool_name': 'get_api',
                    'tool_input': {'component_name': component}
                })
                
                if response.ok:
                    result = response.json()['tool_response']
                    if 'api' in result:
                        apis[component] = result['api']
            except:
                pass  # KM might not be available
        
        return apis
    
    def _load_relevant_files(self, 
                            job_id: str,
                            dependencies: Set[str],
                            agent_type: str,
                            max_tokens: int) -> Dict[str, str]:
        """Intelligently load file contents within token budget."""
        
        workspace_path = Path(f".claude/workspaces/{job_id}/workspace")
        files = {}
        token_count = 0
        
        # Prioritize files based on agent type
        prioritized = self._prioritize_files(list(dependencies), agent_type)
        
        for file_path in prioritized:
            full_path = workspace_path / file_path
            
            if full_path.exists():
                content = full_path.read_text()
                # Rough token estimate (1 token ≈ 4 chars)
                file_tokens = len(content) // 4
                
                if token_count + file_tokens > max_tokens:
                    # Add summary instead of full content
                    files[file_path] = self._summarize_file(content)
                    token_count += 500  # Summary is ~500 tokens
                else:
                    files[file_path] = content
                    token_count += file_tokens
                
                if token_count >= max_tokens:
                    break
        
        return files
    
    def _prioritize_files(self, files: List[str], agent_type: str) -> List[str]:
        """Order files by relevance for the agent type."""
        
        def priority_score(path: str) -> int:
            score = 0
            
            if agent_type == 'developer-agent':
                if 'component' in path: score += 10
                if 'service' in path: score += 8
                if 'util' in path: score += 5
                if 'test' in path: score += 2
                
            elif agent_type == 'reviewer-agent':
                if 'test' in path: score += 10
                if 'component' in path: score += 8
                if '.md' in path: score += 5
                
            elif agent_type == 'qa-agent':
                if 'test' in path: score += 10
                if 'spec' in path: score += 8
            
            return score
        
        return sorted(files, key=priority_score, reverse=True)
    
    def _summarize_file(self, content: str) -> str:
        """Create a summary when full content exceeds token budget."""
        lines = content.split('\n')
        
        # Extract key information
        summary = "FILE SUMMARY (full content exceeded token limit):\n"
        summary += f"- Total lines: {len(lines)}\n"
        
        # Extract imports
        imports = [l for l in lines if l.strip().startswith('import')]
        if imports:
            summary += f"- Imports: {len(imports)} modules\n"
            summary += "  " + "\n  ".join(imports[:5]) + "\n"
        
        # Extract function/class definitions
        definitions = [l for l in lines if 'function' in l or 'class' in l or 'interface' in l]
        if definitions:
            summary += f"- Definitions: {len(definitions)}\n"
            summary += "  " + "\n  ".join(definitions[:10]) + "\n"
        
        return summary
    
    def _get_relevant_decisions(self, ticket_id: str, knowledge: Dict) -> List[str]:
        """Get ADRs relevant to the current context."""
        
        adr_path = Path(".claude/adr")
        decisions = []
        
        # Get ADRs for this ticket
        for adr_file in adr_path.glob(f"{ticket_id}-*.md"):
            decisions.append(adr_file.read_text())
        
        # Get ADRs mentioned in knowledge search
        if 'results' in knowledge:
            for result in knowledge['results']:
                if 'ADR' in result.get('content', ''):
                    # Extract ADR reference and load it
                    pass
        
        return decisions
    
    def _check_cache(self, key: str) -> bool:
        """Check if cached context is still valid."""
        if key in self.cache:
            cached_time = self.cache[key]['timestamp']
            if time.time() - cached_time < self.cache_ttl:
                return True
            else:
                del self.cache[key]
        return False
    
    def _cache_result(self, key: str, data: Dict):
        """Cache the assembled context."""
        self.cache[key] = {
            'timestamp': time.time(),
            'data': data
        }
    
    def _check_fallback_cache(self, key: str) -> bool:
        """Check if cached fallback context is still valid."""
        if key in self.fallback_cache:
            cached_time = self.fallback_cache[key]['timestamp']
            if time.time() - cached_time < self.fallback_cache_ttl:
                return True
            else:
                del self.fallback_cache[key]
        return False
    
    def _cache_fallback_result(self, key: str, data: Dict):
        """Cache fallback context for longer duration."""
        self.fallback_cache[key] = {
            'timestamp': time.time(),
            'data': data
        }