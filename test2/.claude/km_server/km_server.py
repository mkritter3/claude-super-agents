#!/usr/bin/env python3
import json
import sqlite3
import hashlib
import time
import os
import argparse
from flask import Flask, request, jsonify
from pathlib import Path
from typing import Dict, List, Optional

app = Flask(__name__)

class KnowledgeManager:
    def __init__(self, db_path: str = "data/knowledge.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._initialize_db()
    
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS search_history (
                search_id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                results_count INTEGER,
                search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()
    
    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """Simple text search in knowledge base."""
        cursor = self.conn.execute("""
            SELECT * FROM knowledge_items 
            WHERE content LIKE ? OR title LIKE ?
            ORDER BY updated_at DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        results = [dict(row) for row in cursor.fetchall()]
        
        # Log search
        self.conn.execute("""
            INSERT INTO search_history (query, results_count)
            VALUES (?, ?)
        """, (query, len(results)))
        self.conn.commit()
        
        return results
    
    def add_knowledge(self, ticket_id: str, item_type: str, title: str, content: str) -> int:
        """Add knowledge item."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        cursor = self.conn.execute("""
            INSERT INTO knowledge_items (ticket_id, item_type, title, content, content_hash)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_id, item_type, title, content, content_hash))
        
        self.conn.commit()
        return cursor.lastrowid

# Global KM instance
km = KnowledgeManager()

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "knowledge-manager"})

@app.route('/mcp/spec')
def mcp_spec():
    return jsonify({
        "tools": [
            {
                "name": "search_knowledge",
                "description": "Search the knowledge base for relevant information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "add_knowledge", 
                "description": "Add knowledge to the base",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticket_id": {"type": "string"},
                        "item_type": {"type": "string"},
                        "title": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["ticket_id", "item_type", "title", "content"]
                }
            }
        ]
    })

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    data = request.get_json()
    method = data.get('method')
    params = data.get('params', {})
    
    try:
        if method == 'search_knowledge':
            result = km.search_knowledge(params.get('query', ''), params.get('limit', 10))
        elif method == 'add_knowledge':
            result = km.add_knowledge(
                params.get('ticket_id'),
                params.get('item_type'), 
                params.get('title'),
                params.get('content')
            )
        else:
            return jsonify({"error": f"Unknown method: {method}"}), 400
            
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5002)
    parser.add_argument('--host', default='localhost')
    args = parser.parse_args()
    
    print(f"Starting Knowledge Manager on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
