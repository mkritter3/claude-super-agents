-- AET Phase 2: File Registry and Governance Schema
-- This schema implements the complete governance layer for the AET system

-- Component dependency tracking (CRITICAL FOR CONTEXT INTEGRATION!)
CREATE TABLE IF NOT EXISTS dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_component TEXT NOT NULL,
    target_component TEXT NOT NULL,
    dependency_type TEXT NOT NULL, -- 'imports', 'extends', 'uses'
    ticket_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source_component, target_component, dependency_type)
);

CREATE INDEX IF NOT EXISTS idx_dep_source ON dependencies(source_component);
CREATE INDEX IF NOT EXISTS idx_dep_target ON dependencies(target_component);

-- File relationships (CRITICAL FOR CONTEXT INTEGRATION!)
CREATE TABLE IF NOT EXISTS file_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file TEXT NOT NULL,
    target_file TEXT NOT NULL,
    relationship_type TEXT NOT NULL, -- 'imports', 'tests', 'implements'
    strength INTEGER DEFAULT 1, -- How strongly related (1-10)
    UNIQUE(source_file, target_file, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_rel_source ON file_relationships(source_file);
CREATE INDEX IF NOT EXISTS idx_rel_target ON file_relationships(target_file);

-- File Registry Schema
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    canonical_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    job_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    component TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_event_id TEXT NOT NULL,
    lock_status TEXT DEFAULT 'unlocked',
    lock_owner TEXT,
    lock_expiry TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);
CREATE INDEX IF NOT EXISTS idx_files_ticket ON files(ticket_id);
CREATE INDEX IF NOT EXISTS idx_files_component ON files(component);
CREATE INDEX IF NOT EXISTS idx_files_hash ON files(content_hash);
CREATE INDEX IF NOT EXISTS idx_files_lock ON files(lock_status, lock_expiry);

-- Component Registry
CREATE TABLE IF NOT EXISTS components (
    component_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    path_pattern TEXT NOT NULL,
    description TEXT,
    owner_ticket TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Three-Phase Write Protocol tracking
CREATE TABLE IF NOT EXISTS write_requests (
    request_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL,
    phase INTEGER NOT NULL, -- 1, 2, 3
    status TEXT NOT NULL, -- 'pending', 'validated', 'committed', 'failed', 'rolled_back'
    intents_json TEXT NOT NULL, -- JSON blob of write intents
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_write_requests_ticket ON write_requests(ticket_id);
CREATE INDEX IF NOT EXISTS idx_write_requests_status ON write_requests(status);

-- Contract tracking for API stability
CREATE TABLE IF NOT EXISTS contracts (
    contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_name TEXT NOT NULL,
    contract_type TEXT NOT NULL, -- 'api', 'database', 'interface'
    contract_definition TEXT NOT NULL, -- JSON definition
    version TEXT NOT NULL,
    ticket_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deprecated_at TIMESTAMP,
    UNIQUE(component_name, contract_type, version)
);

CREATE INDEX IF NOT EXISTS idx_contracts_component ON contracts(component_name);
CREATE INDEX IF NOT EXISTS idx_contracts_type ON contracts(contract_type);

-- Architecture Decision Records
CREATE TABLE IF NOT EXISTS adrs (
    adr_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL,
    decision_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ticket_id, decision_number)
);

CREATE INDEX IF NOT EXISTS idx_adrs_ticket ON adrs(ticket_id);