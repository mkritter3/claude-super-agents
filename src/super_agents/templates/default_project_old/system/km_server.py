#!/usr/bin/env python3
import json
import sqlite3
import hashlib
import numpy as np
import time
import os
from flask import Flask, request, jsonify
from pathlib import Path
from typing import Dict, List, Optional

app = Flask(__name__)

# Import observability components
try:
    from metrics_collector import get_metrics
    from tracing_config import get_tracer, trace_operation
    OBSERVABILITY_ENABLED = True
except ImportError:
    OBSERVABILITY_ENABLED = False

class KnowledgeManager:
    def __init__(self, db_path: str = ".claude/registry/knowledge.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_db()
        
        # Simple embedding fallback if sentence-transformers not available
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self.has_embeddings = True
        except ImportError:
            print("Warning: sentence-transformers not available, using simple keyword matching")
            self.model = None
            self.has_embeddings = False
    
    def _initialize_db(self):
        """Create knowledge tables."""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL,
                item_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(content_hash)
            );
            
            CREATE INDEX IF NOT EXISTS idx_knowledge_ticket 
                ON knowledge_items(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_knowledge_type 
                ON knowledge_items(item_type);
            
            CREATE TABLE IF NOT EXISTS file_summaries (
                file_path TEXT PRIMARY KEY,
                summary TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                embedding BLOB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS component_apis (
                component_name TEXT PRIMARY KEY,
                api_definition TEXT NOT NULL,
                file_paths TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    def save_knowledge(self, 
                      ticket_id: str,
                      item_type: str,
                      title: str,
                      content: str) -> int:
        """Save knowledge item with embedding."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check if already exists
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT item_id FROM knowledge_items 
            WHERE content_hash = ?
        """, (content_hash,))
        
        existing = cursor.fetchone()
        if existing:
            return existing['item_id']
        
        # Generate embedding if available
        embedding_blob = None
        if self.has_embeddings:
            embedding = self.model.encode(content)
            embedding_blob = embedding.tobytes()
        
        # Insert new item
        cursor.execute("""
            INSERT INTO knowledge_items 
            (ticket_id, item_type, title, content, content_hash, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticket_id, item_type, title, content, content_hash, embedding_blob))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def query_knowledge(self, 
                       query: str,
                       ticket_id: Optional[str] = None,
                       limit: int = 5) -> List[Dict]:
        """Semantic search for relevant knowledge."""
        cursor = self.conn.cursor()
        sql = "SELECT * FROM knowledge_items"
        params = []
        
        if ticket_id:
            sql += " WHERE ticket_id = ?"
            params.append(ticket_id)
        
        cursor.execute(sql, params)
        
        results = []
        
        if self.has_embeddings:
            # Semantic search with embeddings
            query_embedding = self.model.encode(query)
            
            for row in cursor.fetchall():
                if row['embedding']:
                    # Reconstruct embedding from blob
                    item_embedding = np.frombuffer(row['embedding'], dtype=np.float32)
                    
                    # Cosine similarity
                    similarity = np.dot(query_embedding, item_embedding) / (
                        np.linalg.norm(query_embedding) * np.linalg.norm(item_embedding)
                    )
                else:
                    # Fallback to keyword match
                    similarity = self._keyword_similarity(query, row['content'])
                
                results.append({
                    "item_id": row['item_id'],
                    "ticket_id": row['ticket_id'],
                    "type": row['item_type'],
                    "title": row['title'],
                    "content": row['content'],
                    "similarity": float(similarity)
                })
        else:
            # Keyword-based search fallback
            for row in cursor.fetchall():
                similarity = self._keyword_similarity(query, row['content'])
                
                results.append({
                    "item_id": row['item_id'],
                    "ticket_id": row['ticket_id'],
                    "type": row['item_type'],
                    "title": row['title'],
                    "content": row['content'],
                    "similarity": float(similarity)
                })
        
        # Sort by similarity and return top k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:limit]
    
    def _keyword_similarity(self, query: str, content: str) -> float:
        """Simple keyword-based similarity."""
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        intersection = query_words.intersection(content_words)
        return len(intersection) / len(query_words)
    
    def get_file_path(self, component_name: str, file_type: str) -> str:
        """Determine canonical file path for component."""
        # Load conventions
        config_path = Path(".claude/config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)
                pattern = config.get("conventions", {}).get("path_pattern", 
                                    "src/{domain}/{component}/{layer}")
        else:
            pattern = "src/{domain}/{component}/{layer}"
        
        # Determine domain and layer based on file type
        domain = self._infer_domain(component_name)
        layer = self._infer_layer(file_type)
        
        # Generate path
        path = pattern.format(
            domain=domain,
            component=component_name.lower(),
            layer=layer
        )
        
        # Add file extension
        if file_type == "component":
            filename = f"{component_name}.tsx"
        elif file_type == "service":
            filename = f"{component_name.lower()}.service.ts"
        elif file_type == "test":
            filename = f"{component_name.lower()}.test.ts"
        else:
            filename = f"{component_name.lower()}.ts"
        
        return f"{path}/{filename}"
    
    def _infer_domain(self, component_name: str) -> str:
        """Infer domain from component name."""
        name_lower = component_name.lower()
        
        if "auth" in name_lower or "login" in name_lower:
            return "auth"
        elif "user" in name_lower or "profile" in name_lower:
            return "users"
        elif "admin" in name_lower:
            return "admin"
        else:
            return "core"
    
    def _infer_layer(self, file_type: str) -> str:
        """Infer layer from file type."""
        if file_type == "component":
            return "components"
        elif file_type == "service":
            return "services"
        elif file_type == "model":
            return "models"
        elif file_type == "util":
            return "utils"
        else:
            return "lib"
    
    def register_api(self, 
                    component_name: str,
                    api_definition: str,
                    file_paths: List[str]):
        """Register component API definition."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO component_apis
            (component_name, api_definition, file_paths, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (component_name, api_definition, json.dumps(file_paths)))
        
        self.conn.commit()
    
    def get_api(self, component_name: str) -> Optional[Dict]:
        """Get component API definition."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM component_apis WHERE component_name = ?
        """, (component_name,))
        
        row = cursor.fetchone()
        if row:
            return {
                "component": row['component_name'],
                "api": row['api_definition'],
                "files": json.loads(row['file_paths'])
            }
        return None

# Global KM instance
km = KnowledgeManager()

# MCP Server Endpoints
@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    """MCP server endpoint."""
    data = request.json
    tool_name = data.get('tool_name')
    tool_input = data.get('tool_input', {})
    
    response = {}
    
    try:
        if tool_name == 'save':
            item_id = km.save_knowledge(
                tool_input.get('ticket_id', 'UNKNOWN'),
                tool_input.get('item_type', 'general'),
                tool_input.get('title', ''),
                tool_input.get('content', '')
            )
            response = {"success": True, "item_id": item_id}
        
        elif tool_name == 'query':
            results = km.query_knowledge(
                tool_input.get('question', ''),
                tool_input.get('ticket_id'),
                tool_input.get('limit', 5)
            )
            response = {
                "results": results,
                "summary": results[0]['content'] if results else "No relevant information found"
            }
        
        elif tool_name == 'get_file_path':
            path = km.get_file_path(
                tool_input.get('component_name', ''),
                tool_input.get('file_type', 'component')
            )
            response = {"path": path}
        
        elif tool_name == 'register_api':
            km.register_api(
                tool_input.get('component_name', ''),
                tool_input.get('api_definition', ''),
                tool_input.get('file_paths', [])
            )
            response = {"success": True}
        
        elif tool_name == 'get_api':
            api = km.get_api(tool_input.get('component_name', ''))
            response = api or {"error": "Component not found"}
        
        else:
            return jsonify({"error": f"Unknown tool: {tool_name}"}), 400
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    return jsonify({"tool_response": response})

# MCP specification endpoint
@app.route('/mcp/spec', methods=['GET'])
def mcp_spec():
    """Return MCP server specification."""
    spec = {
        "protocol_version": "1.0",
        "server_name": "knowledge-manager",
        "tools": [
            {
                "tool_name": "save",
                "description": "Save knowledge item with semantic embedding",
                "parameters": [
                    {"name": "ticket_id", "type": "string"},
                    {"name": "item_type", "type": "string"},
                    {"name": "title", "type": "string"},
                    {"name": "content", "type": "string"}
                ]
            },
            {
                "tool_name": "query",
                "description": "Semantic search for relevant knowledge",
                "parameters": [
                    {"name": "question", "type": "string"},
                    {"name": "ticket_id", "type": "string", "optional": True},
                    {"name": "limit", "type": "integer", "optional": True}
                ]
            },
            {
                "tool_name": "get_file_path",
                "description": "Get canonical file path for component",
                "parameters": [
                    {"name": "component_name", "type": "string"},
                    {"name": "file_type", "type": "string"}
                ]
            },
            {
                "tool_name": "register_api",
                "description": "Register component API definition",
                "parameters": [
                    {"name": "component_name", "type": "string"},
                    {"name": "api_definition", "type": "string"},
                    {"name": "file_paths", "type": "array"}
                ]
            },
            {
                "tool_name": "get_api",
                "description": "Get component API definition",
                "parameters": [
                    {"name": "component_name", "type": "string"}
                ]
            }
        ]
    }
    return jsonify(spec)

# Health and monitoring endpoints
@app.route('/health', methods=['GET'])
def health():
    """Basic health check endpoint."""
    start_time = time.time()
    
    try:
        # Test database connectivity
        km = KnowledgeManager()
        cursor = km.conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        
        db_healthy = True
    except Exception as e:
        db_healthy = False
    
    health_status = {
        'status': 'healthy' if db_healthy else 'unhealthy',
        'timestamp': time.time(),
        'service': 'knowledge-manager',
        'version': '1.0.0',
        'checks': {
            'database': 'ok' if db_healthy else 'error'
        }
    }
    
    # Record metrics if available
    if OBSERVABILITY_ENABLED:
        response_time = time.time() - start_time
        get_metrics().record_histogram('km_response_time', response_time, {'operation': 'health'})
        get_metrics().increment_counter('km_requests', {'operation': 'health', 'status': 'success'})
    
    status_code = 200 if db_healthy else 503
    return jsonify(health_status), status_code

@app.route('/ready', methods=['GET'])
def ready():
    """Readiness probe endpoint."""
    start_time = time.time()
    
    checks = {}
    all_ready = True
    
    # Check database
    try:
        km = KnowledgeManager()
        cursor = km.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM knowledge_items")
        cursor.fetchone()
        checks['database'] = {'status': 'ready', 'details': 'connected'}
    except Exception as e:
        checks['database'] = {'status': 'not_ready', 'details': str(e)}
        all_ready = False
    
    # Check embedding model if available
    try:
        km = KnowledgeManager()
        if km.has_embeddings:
            # Test embedding generation
            test_embedding = km.model.encode("test")
            checks['embeddings'] = {'status': 'ready', 'details': 'model loaded'}
        else:
            checks['embeddings'] = {'status': 'ready', 'details': 'fallback mode'}
    except Exception as e:
        checks['embeddings'] = {'status': 'not_ready', 'details': str(e)}
        all_ready = False
    
    # Check file system access
    try:
        knowledge_dir = Path('.claude/registry')
        if knowledge_dir.exists() and os.access(str(knowledge_dir), os.R_OK | os.W_OK):
            checks['filesystem'] = {'status': 'ready', 'details': 'accessible'}
        else:
            checks['filesystem'] = {'status': 'not_ready', 'details': 'directory not accessible'}
            all_ready = False
    except Exception as e:
        checks['filesystem'] = {'status': 'not_ready', 'details': str(e)}
        all_ready = False
    
    ready_status = {
        'ready': all_ready,
        'timestamp': time.time(),
        'service': 'knowledge-manager',
        'checks': checks
    }
    
    # Record metrics if available
    if OBSERVABILITY_ENABLED:
        response_time = time.time() - start_time
        get_metrics().record_histogram('km_response_time', response_time, {'operation': 'ready'})
        get_metrics().increment_counter('km_requests', {'operation': 'ready', 'status': 'success'})
    
    status_code = 200 if all_ready else 503
    return jsonify(ready_status), status_code

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint."""
    if not OBSERVABILITY_ENABLED:
        return "# Metrics not available\n", 200, {'Content-Type': 'text/plain'}
    
    try:
        # Update KM-specific metrics
        km = KnowledgeManager()
        
        # Count knowledge items
        cursor = km.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM knowledge_items")
        knowledge_count = cursor.fetchone()['count']
        get_metrics().set_gauge('registered_files', knowledge_count)
        
        # Count file summaries
        cursor.execute("SELECT COUNT(*) as count FROM file_summaries")
        summary_count = cursor.fetchone()['count']
        get_metrics().set_gauge('km_file_summaries_total', summary_count)
        
        # Database size
        db_size = Path('.claude/registry/knowledge.db').stat().st_size if Path('.claude/registry/knowledge.db').exists() else 0
        get_metrics().set_gauge('km_database_size_bytes', db_size)
        
        # Get prometheus metrics
        metrics_data = get_metrics().get_prometheus_metrics()
        
        return metrics_data, 200, {'Content-Type': 'text/plain'}
        
    except Exception as e:
        return f"# Error generating metrics: {str(e)}\n", 500, {'Content-Type': 'text/plain'}

@app.route('/status', methods=['GET'])
def status():
    """Detailed system status endpoint."""
    start_time = time.time()
    
    try:
        km = KnowledgeManager()
        
        # Database statistics
        cursor = km.conn.cursor()
        
        # Knowledge items stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_items,
                COUNT(DISTINCT ticket_id) as unique_tickets,
                COUNT(DISTINCT item_type) as item_types
            FROM knowledge_items
        """)
        knowledge_stats = dict(cursor.fetchone())
        
        # File summaries stats
        cursor.execute("SELECT COUNT(*) as total_summaries FROM file_summaries")
        summary_stats = dict(cursor.fetchone())
        
        # Component APIs stats
        cursor.execute("SELECT COUNT(*) as total_apis FROM component_apis")
        api_stats = dict(cursor.fetchone())
        
        # Database file size
        db_path = Path('.claude/registry/knowledge.db')
        db_size = db_path.stat().st_size if db_path.exists() else 0
        
        # System information
        status_info = {
            'timestamp': time.time(),
            'service': 'knowledge-manager',
            'version': '1.0.0',
            'uptime_seconds': time.time() - start_time,
            'embedding_model': {
                'available': km.has_embeddings,
                'model_name': 'all-MiniLM-L6-v2' if km.has_embeddings else None
            },
            'database': {
                'path': str(db_path),
                'size_bytes': db_size,
                'size_mb': round(db_size / 1024 / 1024, 2)
            },
            'statistics': {
                'knowledge_items': knowledge_stats,
                'file_summaries': summary_stats,
                'component_apis': api_stats
            },
            'observability': {
                'metrics_enabled': OBSERVABILITY_ENABLED,
                'tracing_enabled': OBSERVABILITY_ENABLED
            }
        }
        
        # Add performance metrics if available
        if OBSERVABILITY_ENABLED:
            metrics = get_metrics()
            performance = metrics.get_performance_impact()
            status_info['performance'] = performance
            
            # Record status request metrics
            response_time = time.time() - start_time
            metrics.record_histogram('km_response_time', response_time, {'operation': 'status'})
            metrics.increment_counter('km_requests', {'operation': 'status', 'status': 'success'})
        
        return jsonify(status_info)
        
    except Exception as e:
        error_response = {
            'timestamp': time.time(),
            'service': 'knowledge-manager',
            'status': 'error',
            'error': str(e)
        }
        
        if OBSERVABILITY_ENABLED:
            get_metrics().increment_counter('km_requests', {'operation': 'status', 'status': 'error'})
        
        return jsonify(error_response), 500

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'spec':
        # Print spec for MCP registration
        try:
            import requests
            response = requests.get('http://127.0.0.1:5001/mcp/spec')
            print(json.dumps(response.json(), indent=2))
        except:
            print("Server not running or requests not available")
    else:
        # Run server
        app.run(port=5001, debug=False)