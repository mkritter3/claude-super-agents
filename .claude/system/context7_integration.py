#!/usr/bin/env python3
"""
Context7 Integration for AET System
Provides orchestrator-mediated RAG with latest library documentation
"""
import json
import subprocess
import re
from typing import List, Dict, Optional
from pathlib import Path

class Context7Manager:
    """Manages Context7 documentation fetching for AET agents"""
    
    def __init__(self):
        self.tech_keywords = {
            "react": ["react", "jsx", "hooks", "react.js", "reactjs"],
            "vue": ["vue", "vue.js", "vuejs", "composition api"],
            "angular": ["angular", "@angular", "angular.js"],
            "next.js": ["next", "next.js", "nextjs", "app router"],
            "nuxt": ["nuxt", "nuxt.js", "nuxt3"],
            "svelte": ["svelte", "sveltekit", "svelte 5"],
            "django": ["django", "django rest", "drf"],
            "flask": ["flask", "flask-restful"],
            "fastapi": ["fastapi", "pydantic", "starlette"],
            "express": ["express", "express.js", "expressjs"],
            "nest": ["nestjs", "nest.js", "@nestjs"],
            "tailwind": ["tailwind", "tailwindcss", "tailwind css"],
            "bootstrap": ["bootstrap", "bootstrap 5"],
            "prisma": ["prisma", "prisma orm", "@prisma"],
            "sequelize": ["sequelize", "sequelize orm"],
            "mongoose": ["mongoose", "mongodb mongoose"],
            "axios": ["axios", "axios http"],
            "lodash": ["lodash", "lodash utils"],
            "moment": ["moment", "moment.js", "momentjs"],
            "dayjs": ["dayjs", "day.js"],
            "chart.js": ["chart.js", "chartjs", "chart js"],
            "d3": ["d3", "d3.js", "d3js"],
            "three.js": ["three", "three.js", "threejs", "webgl"],
            "socket.io": ["socket.io", "socketio", "websocket"],
            "webpack": ["webpack", "webpack 5"],
            "vite": ["vite", "vite.js", "vitejs"],
            "eslint": ["eslint", "es lint"],
            "prettier": ["prettier", "code formatting"],
            "jest": ["jest", "jest testing"],
            "vitest": ["vitest", "vite test"],
            "cypress": ["cypress", "cypress testing"],
            "playwright": ["playwright", "microsoft playwright"],
            "typescript": ["typescript", "ts", "type definitions"],
            "graphql": ["graphql", "apollo", "relay"],
            "redis": ["redis", "redis cache"],
            "postgresql": ["postgresql", "postgres", "pg"],
            "mysql": ["mysql", "mariadb"],
            "docker": ["docker", "dockerfile", "container"],
            "kubernetes": ["kubernetes", "k8s", "kubectl"],
            "aws": ["aws", "amazon web services", "lambda", "s3"],
            "vercel": ["vercel", "vercel deployment"],
            "netlify": ["netlify", "netlify functions"]
        }
    
    def extract_libraries_from_context(self, context: Dict) -> List[str]:
        """Extract libraries from task description and workspace context"""
        found_libraries = []
        
        # Combine all text context for analysis
        text_sources = [
            context.get('original_prompt', ''),
            context.get('task_description', ''),
            context.get('current_status', ''),
            str(context.get('workspace', {}))
        ]
        
        # Check workspace files for technology indicators
        workspace_files = context.get('workspace', {}).get('files', [])
        for file_path in workspace_files:
            if isinstance(file_path, str):
                text_sources.append(file_path)
        
        combined_text = ' '.join(text_sources).lower()
        
        # Find matching libraries
        for lib, variants in self.tech_keywords.items():
            if any(variant in combined_text for variant in variants):
                found_libraries.append(lib)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(found_libraries))
    
    def check_context7_available(self) -> bool:
        """Check if Context7 MCP is available"""
        try:
            # Check if Context7 settings exist
            settings_path = Path('.claude/settings.json')
            if settings_path.exists():
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    if 'mcpServers' in settings and 'context7' in settings['mcpServers']:
                        return True
            return False
        except Exception:
            return False
    
    def fetch_library_docs(self, libraries: List[str], max_docs: int = 3) -> Optional[str]:
        """Fetch documentation for specified libraries using Context7 MCP"""
        if not libraries or not self.check_context7_available():
            return None
        
        # Limit to most relevant libraries to avoid context bloat
        priority_libs = libraries[:max_docs]
        docs_sections = []
        
        for lib in priority_libs:
            try:
                # Use Context7 resolve-library-id tool
                resolve_cmd = [
                    'claude', '--tool', 'mcp__context7__resolve-library-id',
                    '--args', json.dumps({"libraryName": lib})
                ]
                
                resolve_result = subprocess.run(
                    resolve_cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                
                if resolve_result.returncode == 0:
                    # Use Context7 get-library-docs tool
                    docs_cmd = [
                        'claude', '--tool', 'mcp__context7__get-library-docs',
                        '--args', json.dumps({
                            "context7CompatibleLibraryID": lib,
                            "tokens": 3000,  # Reasonable token limit per library
                            "topic": "best practices"
                        })
                    ]
                    
                    docs_result = subprocess.run(
                        docs_cmd,
                        capture_output=True,
                        text=True,
                        timeout=15
                    )
                    
                    if docs_result.returncode == 0 and docs_result.stdout.strip():
                        docs_sections.append(f"## {lib.title()} Documentation\n{docs_result.stdout.strip()}")
                        
            except (subprocess.TimeoutExpired, Exception) as e:
                # Log error but continue with other libraries
                continue
        
        if docs_sections:
            return "\n\n".join(docs_sections)
        
        return None
    
    def enrich_context_with_docs(self, context: Dict, agent_name: str) -> Dict:
        """Enrich agent context with relevant library documentation"""
        
        # Only enrich context for agents that write/implement code
        code_agents = {
            'developer-agent', 'frontend-agent', 'architect-agent', 
            'database-agent', 'devops-agent', 'security-agent'
        }
        
        if agent_name not in code_agents:
            return context
        
        # Extract libraries from context
        libraries = self.extract_libraries_from_context(context)
        
        if not libraries:
            return context
        
        # Fetch documentation
        docs = self.fetch_library_docs(libraries)
        
        if docs:
            # Add docs to context
            enhanced_context = context.copy()
            enhanced_context['latest_docs'] = {
                'libraries': libraries,
                'documentation': docs,
                'fetch_timestamp': subprocess.run(['date'], capture_output=True, text=True).stdout.strip(),
                'note': f"Latest documentation for {', '.join(libraries)} - use current patterns and best practices"
            }
            
            return enhanced_context
        
        return context

# Export for orchestrator integration
context7_manager = Context7Manager()