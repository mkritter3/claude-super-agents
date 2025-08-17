#!/usr/bin/env python3
"""
Indexing system for CLI performance improvements.

Implements intelligent file and metadata indexing to speed up searches,
project initialization, and agent operations. Targets significant 
performance improvements as specified in the roadmap.
"""

import os
import time
import json
import sqlite3
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class FileIndex:
    """File metadata index entry."""
    path: str
    size: int
    mtime: float
    hash_md5: Optional[str] = None
    file_type: Optional[str] = None
    is_binary: bool = False
    indexed_at: float = 0.0
    
    def __post_init__(self):
        if self.indexed_at == 0.0:
            self.indexed_at = time.time()

@dataclass
class AgentIndex:
    """Agent metadata index entry."""
    name: str
    path: str
    description: str
    triggers: List[str]
    capabilities: List[str]
    last_modified: float
    size_lines: int = 0
    
class ProjectIndexer:
    """High-performance project file and metadata indexer."""
    
    def __init__(self, index_db_path: Optional[Path] = None):
        if index_db_path is None:
            index_db_path = Path(".claude/indexes/project.db")
        
        self.db_path = index_db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_database()
        
        # Common file patterns to ignore
        self.ignore_patterns = {
            '.git', '.gitignore', '__pycache__', '*.pyc', '*.pyo',
            '.DS_Store', 'Thumbs.db', '*.tmp', '*.log', '*.swp',
            '.claude/events', '.claude/logs', '.claude/dlq'
        }
        
        # Binary file extensions
        self.binary_extensions = {
            '.exe', '.dll', '.so', '.dylib', '.jar', '.war', '.zip',
            '.tar', '.gz', '.bz2', '.xz', '.7z', '.rar', '.pdf',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico',
            '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',
            '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
        }
    
    def _init_database(self):
        """Initialize the index database."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS file_index (
                    path TEXT PRIMARY KEY,
                    size INTEGER NOT NULL,
                    mtime REAL NOT NULL,
                    hash_md5 TEXT,
                    file_type TEXT,
                    is_binary BOOLEAN NOT NULL DEFAULT 0,
                    indexed_at REAL NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS agent_index (
                    name TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    description TEXT NOT NULL,
                    triggers TEXT NOT NULL,  -- JSON array
                    capabilities TEXT NOT NULL,  -- JSON array
                    last_modified REAL NOT NULL,
                    size_lines INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS project_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_file_mtime ON file_index(mtime);
                CREATE INDEX IF NOT EXISTS idx_file_type ON file_index(file_type);
                CREATE INDEX IF NOT EXISTS idx_agent_triggers ON agent_index(triggers);
                CREATE INDEX IF NOT EXISTS idx_project_updated ON project_metadata(updated_at);
            """)
    
    def _should_ignore_path(self, path: Path) -> bool:
        """Check if path should be ignored during indexing."""
        path_str = str(path)
        
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                # Extension pattern
                if path_str.endswith(pattern[1:]):
                    return True
            else:
                # Directory or file pattern
                if pattern in path.parts or path.name == pattern:
                    return True
        
        return False
    
    def _detect_file_type(self, path: Path) -> Tuple[str, bool]:
        """Detect file type and whether it's binary."""
        suffix = path.suffix.lower()
        
        # Check if binary
        is_binary = suffix in self.binary_extensions
        
        # Detect type
        type_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.ts': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.md': 'markdown',
            '.txt': 'text',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.sh': 'shell',
            '.sql': 'sql',
            '.xml': 'xml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'config'
        }
        
        file_type = type_map.get(suffix, 'unknown')
        
        # Additional detection for files without extensions
        if file_type == 'unknown' and not is_binary:
            try:
                # Quick peek at file content
                with open(path, 'rb') as f:
                    sample = f.read(512)
                
                # Check for binary content
                if b'\x00' in sample:
                    is_binary = True
                    file_type = 'binary'
                else:
                    # Try to detect based on content
                    content = sample.decode('utf-8', errors='ignore').lower()
                    if content.startswith('#!/bin/bash') or content.startswith('#!/bin/sh'):
                        file_type = 'shell'
                    elif content.startswith('#!/usr/bin/env python') or content.startswith('#!/usr/bin/python'):
                        file_type = 'python'
                    elif '#!/usr/bin/env node' in content or 'node' in content:
                        file_type = 'javascript'
                    else:
                        file_type = 'text'
                        
            except (OSError, UnicodeDecodeError):
                is_binary = True
                file_type = 'binary'
        
        return file_type, is_binary
    
    def _calculate_file_hash(self, path: Path) -> Optional[str]:
        """Calculate MD5 hash of file content."""
        try:
            hash_md5 = hashlib.md5()
            with open(path, 'rb') as f:
                # Read in chunks for large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (OSError, MemoryError):
            return None
    
    def index_file(self, path: Path, calculate_hash: bool = False) -> FileIndex:
        """Index a single file."""
        try:
            stat = path.stat()
            file_type, is_binary = self._detect_file_type(path)
            
            hash_md5 = None
            if calculate_hash and not is_binary and stat.st_size < 1024 * 1024:  # Hash files < 1MB
                hash_md5 = self._calculate_file_hash(path)
            
            file_index = FileIndex(
                path=str(path),
                size=stat.st_size,
                mtime=stat.st_mtime,
                hash_md5=hash_md5,
                file_type=file_type,
                is_binary=is_binary
            )
            
            return file_index
            
        except (OSError, PermissionError):
            # Return minimal index for inaccessible files
            return FileIndex(
                path=str(path),
                size=0,
                mtime=0,
                file_type='error',
                is_binary=True
            )
    
    def index_project(self, root_path: Path = None, max_workers: int = 4, 
                     calculate_hashes: bool = False) -> Dict[str, Any]:
        """
        Index entire project with parallel processing.
        
        Args:
            root_path: Root directory to index (defaults to current directory)
            max_workers: Number of worker threads for parallel indexing
            calculate_hashes: Whether to calculate file hashes
        
        Returns:
            Indexing statistics
        """
        if root_path is None:
            root_path = Path.cwd()
        
        start_time = time.time()
        files_indexed = 0
        files_skipped = 0
        errors = 0
        
        # Collect all files to index
        files_to_index = []
        for root, dirs, files in os.walk(root_path):
            # Filter directories
            dirs[:] = [d for d in dirs if not self._should_ignore_path(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                if not self._should_ignore_path(file_path):
                    files_to_index.append(file_path)
                else:
                    files_skipped += 1
        
        # Index files in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit indexing tasks
            future_to_path = {
                executor.submit(self.index_file, path, calculate_hashes): path
                for path in files_to_index
            }
            
            # Collect results and store in database
            file_indexes = []
            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    file_index = future.result()
                    file_indexes.append(file_index)
                    files_indexed += 1
                except Exception as e:
                    errors += 1
                    print(f"Error indexing {path}: {e}")
        
        # Batch insert to database
        with self._lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Clear old entries
                conn.execute("DELETE FROM file_index")
                
                # Insert new entries
                for file_index in file_indexes:
                    conn.execute("""
                        INSERT INTO file_index 
                        (path, size, mtime, hash_md5, file_type, is_binary, indexed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        file_index.path,
                        file_index.size,
                        file_index.mtime,
                        file_index.hash_md5,
                        file_index.file_type,
                        file_index.is_binary,
                        file_index.indexed_at
                    ))
                
                # Update project metadata
                metadata = {
                    'last_full_index': time.time(),
                    'total_files': files_indexed,
                    'index_version': '1.0'
                }
                
                for key, value in metadata.items():
                    conn.execute("""
                        INSERT OR REPLACE INTO project_metadata (key, value, updated_at)
                        VALUES (?, ?, ?)
                    """, (key, str(value), time.time()))
        
        duration = time.time() - start_time
        
        return {
            'files_indexed': files_indexed,
            'files_skipped': files_skipped,
            'errors': errors,
            'duration': duration,
            'files_per_second': files_indexed / max(duration, 0.001)
        }
    
    def index_agents(self, agents_dir: Path = None) -> Dict[str, Any]:
        """Index agent definitions from .claude/agents directory."""
        if agents_dir is None:
            agents_dir = Path(".claude/agents")
        
        if not agents_dir.exists():
            return {'agents_indexed': 0, 'errors': 0}
        
        agents_indexed = 0
        errors = 0
        agent_indexes = []
        
        for agent_file in agents_dir.glob("*.md"):
            try:
                content = agent_file.read_text()
                lines = content.splitlines()
                
                # Extract agent metadata
                name = agent_file.stem
                description = ""
                triggers = []
                capabilities = []
                
                # Parse agent file for metadata
                in_triggers = False
                in_capabilities = False
                
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith('# ') and not description:
                        description = line[2:].strip()
                    elif 'triggers:' in line.lower() or 'trigger' in line.lower():
                        in_triggers = True
                        in_capabilities = False
                    elif 'capabilities:' in line.lower() or 'capability' in line.lower():
                        in_capabilities = True
                        in_triggers = False
                    elif line.startswith('- ') or line.startswith('* '):
                        item = line[2:].strip()
                        if in_triggers:
                            triggers.append(item)
                        elif in_capabilities:
                            capabilities.append(item)
                    elif line.startswith('#') and (in_triggers or in_capabilities):
                        # New section, stop parsing current list
                        in_triggers = False
                        in_capabilities = False
                
                agent_index = AgentIndex(
                    name=name,
                    path=str(agent_file),
                    description=description or f"Agent: {name}",
                    triggers=triggers,
                    capabilities=capabilities,
                    last_modified=agent_file.stat().st_mtime,
                    size_lines=len(lines)
                )
                
                agent_indexes.append(agent_index)
                agents_indexed += 1
                
            except (OSError, UnicodeDecodeError) as e:
                errors += 1
                print(f"Error indexing agent {agent_file}: {e}")
        
        # Store in database
        with self._lock:
            with sqlite3.connect(str(self.db_path)) as conn:
                # Clear old agent entries
                conn.execute("DELETE FROM agent_index")
                
                # Insert new entries
                for agent_index in agent_indexes:
                    conn.execute("""
                        INSERT INTO agent_index 
                        (name, path, description, triggers, capabilities, last_modified, size_lines)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        agent_index.name,
                        agent_index.path,
                        agent_index.description,
                        json.dumps(agent_index.triggers),
                        json.dumps(agent_index.capabilities),
                        agent_index.last_modified,
                        agent_index.size_lines
                    ))
        
        return {
            'agents_indexed': agents_indexed,
            'errors': errors
        }
    
    def search_files(self, query: str, file_type: Optional[str] = None, 
                    limit: int = 100) -> List[Dict[str, Any]]:
        """Search indexed files."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            sql = """
                SELECT path, size, mtime, file_type, is_binary
                FROM file_index 
                WHERE path LIKE ?
            """
            params = [f"%{query}%"]
            
            if file_type:
                sql += " AND file_type = ?"
                params.append(file_type)
            
            sql += " ORDER BY mtime DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def search_agents(self, query: str) -> List[Dict[str, Any]]:
        """Search indexed agents by name, description, or capabilities."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT name, description, triggers, capabilities, last_modified
                FROM agent_index 
                WHERE name LIKE ? OR description LIKE ? OR triggers LIKE ? OR capabilities LIKE ?
            """, [f"%{query}%"] * 4)
            
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                result['triggers'] = json.loads(result['triggers'])
                result['capabilities'] = json.loads(result['capabilities'])
                results.append(result)
            
            return results
    
    def get_file_stats(self) -> Dict[str, Any]:
        """Get file indexing statistics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(size) as total_size,
                    COUNT(DISTINCT file_type) as unique_types,
                    AVG(size) as avg_size,
                    MAX(mtime) as newest_file,
                    MIN(mtime) as oldest_file
                FROM file_index
                WHERE file_type != 'error'
            """)
            
            row = cursor.fetchone()
            if row:
                stats = {
                    'total_files': row[0] or 0,
                    'total_size': row[1] or 0, 
                    'unique_types': row[2] or 0,
                    'avg_size': row[3] or 0,
                    'newest_file': row[4] or 0,
                    'oldest_file': row[5] or 0
                }
            else:
                stats = {
                    'total_files': 0,
                    'total_size': 0,
                    'unique_types': 0,
                    'avg_size': 0,
                    'newest_file': 0,
                    'oldest_file': 0
                }
            
            # Get type distribution
            cursor = conn.execute("""
                SELECT file_type, COUNT(*) as count
                FROM file_index 
                WHERE file_type != 'error'
                GROUP BY file_type 
                ORDER BY count DESC
            """)
            
            stats['type_distribution'] = dict(cursor.fetchall())
            
            return stats
    
    def is_index_stale(self, max_age_hours: int = 24) -> bool:
        """Check if index needs updating."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.execute("""
                    SELECT value FROM project_metadata 
                    WHERE key = 'last_full_index'
                """)
                result = cursor.fetchone()
                
                if not result:
                    return True
                
                last_index = float(result[0])
                age_hours = (time.time() - last_index) / 3600
                
                return age_hours > max_age_hours
                
        except (sqlite3.Error, ValueError):
            return True
    
    def incremental_update(self) -> Dict[str, Any]:
        """Perform incremental index update for changed files."""
        if not self.db_path.exists():
            # No existing index, do full indexing
            return self.index_project()
        
        updated_files = 0
        new_files = 0
        deleted_files = 0
        
        # Get current file index
        current_files = {}
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT path, mtime FROM file_index")
            for path, mtime in cursor.fetchall():
                current_files[path] = mtime
        
        # Check for updates and new files
        files_to_update = []
        for root, dirs, files in os.walk(Path.cwd()):
            dirs[:] = [d for d in dirs if not self._should_ignore_path(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                if self._should_ignore_path(file_path):
                    continue
                
                file_path_str = str(file_path)
                
                try:
                    current_mtime = file_path.stat().st_mtime
                    
                    if file_path_str in current_files:
                        # Check if modified
                        if current_mtime > current_files[file_path_str]:
                            files_to_update.append(file_path)
                            updated_files += 1
                    else:
                        # New file
                        files_to_update.append(file_path)
                        new_files += 1
                        
                except OSError:
                    continue
        
        # Update modified/new files
        if files_to_update:
            with ThreadPoolExecutor(max_workers=4) as executor:
                file_indexes = list(executor.map(self.index_file, files_to_update))
            
            # Update database
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    for file_index in file_indexes:
                        conn.execute("""
                            INSERT OR REPLACE INTO file_index 
                            (path, size, mtime, hash_md5, file_type, is_binary, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            file_index.path,
                            file_index.size,
                            file_index.mtime,
                            file_index.hash_md5,
                            file_index.file_type,
                            file_index.is_binary,
                            file_index.indexed_at
                        ))
        
        # Check for deleted files
        all_current_files = set()
        for root, dirs, files in os.walk(Path.cwd()):
            dirs[:] = [d for d in dirs if not self._should_ignore_path(Path(root) / d)]
            for file in files:
                file_path = Path(root) / file
                if not self._should_ignore_path(file_path):
                    all_current_files.add(str(file_path))
        
        deleted_paths = set(current_files.keys()) - all_current_files
        if deleted_paths:
            with self._lock:
                with sqlite3.connect(str(self.db_path)) as conn:
                    for path in deleted_paths:
                        conn.execute("DELETE FROM file_index WHERE path = ?", (path,))
                        deleted_files += 1
        
        return {
            'updated_files': updated_files,
            'new_files': new_files,
            'deleted_files': deleted_files,
            'total_changes': updated_files + new_files + deleted_files
        }

# Global project indexer
_project_indexer = None

def get_project_indexer() -> ProjectIndexer:
    """Get or create global project indexer."""
    global _project_indexer
    if _project_indexer is None:
        _project_indexer = ProjectIndexer()
    return _project_indexer

def ensure_project_indexed():
    """Ensure project is indexed with incremental updates."""
    indexer = get_project_indexer()
    
    if indexer.is_index_stale():
        # Full reindex if stale
        return indexer.index_project()
    else:
        # Incremental update
        return indexer.incremental_update()