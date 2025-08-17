#!/usr/bin/env python3
"""
Context7 Documentation Fetcher Hook - Project Level
Automatically fetches latest library docs before agent tasks
"""
import json
import sys
import subprocess
import shutil
from pathlib import Path

def check_context7_mcp():
    """Check if Context7 MCP is available"""
    try:
        # Check if mcp__context7 tools are available
        result = subprocess.run(['claude', '--list-tools'], 
                              capture_output=True, text=True, timeout=5)
        if 'mcp__context7' in result.stdout:
            return True
    except Exception:
        pass
    
    return False

def setup_context7_project_level():
    """Setup Context7 at project level only"""
    try:
        project_settings = Path('.claude/settings.json')
        
        # Load existing project settings
        if project_settings.exists():
            with open(project_settings, 'r') as f:
                settings = json.load(f)
        else:
            settings = {}
        
        # Add Context7 MCP server to project settings only
        if 'mcpServers' not in settings:
            settings['mcpServers'] = {}
        
        if 'context7' not in settings['mcpServers']:
            settings['mcpServers']['context7'] = {
                "command": "npx",
                "args": ["-y", "@upstash/context7"]
            }
            
            # Save project-level settings
            project_settings.parent.mkdir(parents=True, exist_ok=True)
            with open(project_settings, 'w') as f:
                json.dump(settings, f, indent=2)
            
            print("📚 Context7 configured for this project")
            return True
    
    except Exception as e:
        print(f"⚠️  Could not configure Context7: {e}")
        return False
    
    return True

def fetch_library_docs(libraries):
    """Fetch documentation using Context7 MCP with fallback"""
    if not libraries:
        return
    
    # Try to setup Context7 if not available
    if not check_context7_mcp():
        if not setup_context7_project_level():
            print("📖 Context7 not available - agents will use built-in knowledge")
            return
    
    for lib in libraries:
        try:
            print(f"📚 Fetching latest {lib} documentation...", file=sys.stderr)
            
            # Use Context7 MCP tools
            # First resolve library ID
            resolve_result = subprocess.run([
                'claude', '--tool', 'mcp__context7__resolve-library-id',
                '--', json.dumps({"libraryName": lib})
            ], capture_output=True, text=True, timeout=10)
            
            if resolve_result.returncode == 0:
                # Then get library docs
                docs_result = subprocess.run([
                    'claude', '--tool', 'mcp__context7__get-library-docs', 
                    '--', json.dumps({"context7CompatibleLibraryID": lib, "tokens": 5000})
                ], capture_output=True, text=True, timeout=15)
                
                if docs_result.returncode == 0:
                    print(f"✅ Retrieved {lib} documentation", file=sys.stderr)
                else:
                    print(f"⚠️  Could not fetch {lib} docs: API error", file=sys.stderr)
            
        except subprocess.TimeoutExpired:
            print(f"⚠️  Timeout fetching {lib} documentation", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Error fetching {lib} docs: {e}", file=sys.stderr)

def extract_libraries(prompt):
    """Extract library/framework names from task description"""
    # Common frameworks and libraries that benefit from latest docs
    tech_keywords = {
        "react": ["react", "jsx", "hooks", "react.js"],
        "vue": ["vue", "vue.js", "vuejs"],
        "angular": ["angular", "@angular"],
        "next.js": ["next", "next.js", "nextjs"],
        "nuxt": ["nuxt", "nuxt.js"],
        "svelte": ["svelte", "sveltekit"],
        "django": ["django"],
        "flask": ["flask"],
        "fastapi": ["fastapi"],
        "express": ["express", "express.js"],
        "nest": ["nestjs", "nest.js"],
        "tailwind": ["tailwind", "tailwindcss"],
        "bootstrap": ["bootstrap"],
        "prisma": ["prisma"],
        "sequelize": ["sequelize"],
        "mongoose": ["mongoose"],
        "axios": ["axios"],
        "lodash": ["lodash"],
        "moment": ["moment", "moment.js"],
        "dayjs": ["dayjs"],
        "chart.js": ["chart.js", "chartjs"],
        "d3": ["d3", "d3.js"],
        "three.js": ["three", "three.js", "threejs"],
        "socket.io": ["socket.io", "socketio"],
        "webpack": ["webpack"],
        "vite": ["vite"],
        "eslint": ["eslint"],
        "prettier": ["prettier"],
        "jest": ["jest"],
        "vitest": ["vitest"],
        "cypress": ["cypress"],
        "playwright": ["playwright"]
    }
    
    found_libraries = []
    prompt_lower = prompt.lower()
    
    for lib, variants in tech_keywords.items():
        if any(variant in prompt_lower for variant in variants):
            found_libraries.append(lib)
    
    # Remove duplicates while preserving order
    return list(dict.fromkeys(found_libraries))

def main():
    try:
        # Read hook input from stdin
        input_data = json.load(sys.stdin)
        
        # Only process Task tool calls (agent invocations)
        if input_data.get("tool_name") != "Task":
            sys.exit(0)
        
        # Extract task prompt
        task_prompt = input_data.get("tool_input", {}).get("prompt", "")
        
        # Find libraries mentioned in the task
        libraries = extract_libraries(task_prompt)
        
        if libraries:
            print(f"📋 Task mentions: {', '.join(libraries)}", file=sys.stderr)
            fetch_library_docs(libraries)
        
        # Always exit successfully - never block agent execution
        sys.exit(0)
        
    except json.JSONDecodeError:
        # Invalid JSON input - just continue
        sys.exit(0)
    except Exception as e:
        # Log error but don't block
        print(f"Context7 hook error: {e}", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()