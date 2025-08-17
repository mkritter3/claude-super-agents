#!/usr/bin/env python3
"""
Initialize the AET Phase 2 File Registry and Governance System
"""

import os
import sys
from pathlib import Path
from file_registry import FileRegistry
from verify_consistency import ConsistencyVerifier
import json

def initialize_registry():
    """Initialize the file registry database and perform initial setup."""
    
    print("Initializing AET Phase 2: File Registry and Governance System...")
    
    # Create directories
    dirs = [
        ".claude/registry",
        ".claude/events", 
        ".claude/workspaces",
        ".claude/snapshots",
        ".claude/adr"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {dir_path}")
    
    # Initialize file registry (creates database)
    registry = FileRegistry()
    print("✓ Initialized file registry database")
    
    # Run initial consistency verification
    verifier = ConsistencyVerifier()
    report = verifier.verify_consistency(["src", "."])
    
    print(f"✓ Initial consistency check complete:")
    print(f"  - Files scanned: {report['total_files_checked']}")
    print(f"  - Issues found: {report['total_issues']}")
    
    if report['total_issues'] > 0:
        print("  - Running auto-reconciliation...")
        reconciliation = verifier.auto_reconcile(report)
        print(f"  - Actions taken: {len(reconciliation['actions_taken'])}")
        for action in reconciliation['actions_taken'][:5]:  # Show first 5
            print(f"    • {action}")
        if len(reconciliation['actions_taken']) > 5:
            print(f"    ... and {len(reconciliation['actions_taken']) - 5} more")
    
    # Update context assembler to use the registry
    try:
        from context_assembler import ContextAssembler
        context = ContextAssembler()
        context.file_registry = registry
        print("✓ Connected file registry to context assembler")
    except ImportError:
        print("⚠ Context assembler not available yet")
    
    registry.close()
    
    print("\n🎉 AET Phase 2 initialization complete!")
    print("\nAvailable commands:")
    print("  File Registry:")
    print("    python .claude/system/file_registry.py validate <path>")
    print("    python .claude/system/file_registry.py deps <path>")
    print("  Write Protocol:")
    print("    python .claude/system/write_protocol.py <intents_json> <ticket_id>")
    print("  Verification:")
    print("    python .claude/system/verify_consistency.py verify")
    print("    python .claude/system/verify_consistency.py reconcile")
    print("  Integration:")
    print("    python .claude/system/integrator.py <ticket_id> <job_id> <workspace_path>")

def health_check():
    """Perform a health check of the registry system."""
    print("AET Phase 2 Health Check")
    print("=" * 40)
    
    # Check database
    try:
        registry = FileRegistry()
        cursor = registry.conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = ['files', 'dependencies', 'file_relationships', 'components', 'write_requests', 'contracts', 'adrs']
        missing_tables = [t for t in required_tables if t not in tables]
        
        if missing_tables:
            print(f"❌ Missing tables: {missing_tables}")
            return False
        else:
            print("✅ All required tables present")
        
        # Check file counts
        cursor.execute("SELECT COUNT(*) FROM files")
        file_count = cursor.fetchone()[0]
        print(f"✅ Registry contains {file_count} files")
        
        cursor.execute("SELECT COUNT(*) FROM file_relationships")
        rel_count = cursor.fetchone()[0]
        print(f"✅ Registry contains {rel_count} file relationships")
        
        cursor.execute("SELECT COUNT(*) FROM dependencies")
        dep_count = cursor.fetchone()[0]
        print(f"✅ Registry contains {dep_count} component dependencies")
        
        registry.close()
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return False
    
    # Check consistency
    try:
        verifier = ConsistencyVerifier()
        report = verifier.verify_consistency()
        
        if report['status'] == 'OK':
            print("✅ File system consistency: OK")
        else:
            print(f"⚠ File system issues: {report['total_issues']} found")
            
    except Exception as e:
        print(f"❌ Consistency check error: {str(e)}")
        return False
    
    print("\n🎉 Phase 2 system is healthy!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "health":
        health_check()
    else:
        initialize_registry()