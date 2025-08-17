#!/usr/bin/env python3
"""
AET - Autonomous Engineering Team CLI
Main command-line interface for the AET system.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict

# Import AET modules
from event_logger import EventLogger
from orchestrator import TaskOrchestrator
from parallel_orchestrator import ParallelOrchestrator
from simple_orchestrator import SimpleOrchestrator
from workspace_manager import WorkspaceManager
from file_registry import FileRegistry
from metrics import MetricsCollector
from state_rebuilder import StateRebuilder

class AETCLI:
    def __init__(self):
        self.event_logger = EventLogger()
        self.orchestrator = TaskOrchestrator()
        self.parallel_orchestrator = ParallelOrchestrator()
        self.simple_orchestrator = SimpleOrchestrator()
        self.workspace_manager = WorkspaceManager()
        self.file_registry = FileRegistry()
        self.metrics = MetricsCollector()
        self.state_rebuilder = StateRebuilder()
    
    def init_system(self):
        """Initialize the AET system."""
        print("Initializing AET system...")
        
        # Create directory structure
        dirs = [
            ".claude/agents",
            ".claude/events", 
            ".claude/workspaces",
            ".claude/registry",
            ".claude/snapshots",
            ".claude/system",
            ".claude/adr",
            ".claude/dlq",
            ".claude/backups"
        ]
        
        for dir_path in dirs:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        
        # Initialize databases
        self.file_registry._initialize_db()
        self.metrics._initialize_db()
        
        # Create initial config
        config = {
            "version": "1.0",
            "max_workers": 3,
            "timeout_seconds": 300,
            "conventions": {
                "path_pattern": "src/{domain}/{component}/{layer}"
            }
        }
        
        config_path = Path(".claude/config.json")
        if not config_path.exists():
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        print("✓ AET system initialized successfully")
        return True
    
    def create_task(self, description: str, mode: str = "full") -> str:
        """Create a new task."""
        ticket_id = f"TICKET-{int(datetime.now().timestamp())}"
        
        # Check mode selection
        if mode == "auto":
            # Auto-select mode based on task complexity
            suitability = self.simple_orchestrator.is_suitable_for_simple_mode(description)
            mode = suitability["recommendation"]
            print(f"Auto-selected mode: {mode} (confidence: {suitability['confidence']:.2f})")
        
        # Log task creation
        self.event_logger.append_event(
            ticket_id=ticket_id,
            event_type="TASK_CREATED",
            payload={
                "description": description,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Create task snapshot
        job_id = self.workspace_manager.create_workspace(ticket_id, description)
        
        snapshot = {
            "ticket_id": ticket_id,
            "job_id": job_id,
            "status": "CREATED",
            "description": description,
            "mode": mode,
            "created_at": datetime.now().isoformat(),
            "retry_count": 0
        }
        
        self.orchestrator.save_snapshot(ticket_id, snapshot)
        
        print(f"✓ Created task: {ticket_id}")
        print(f"  Description: {description}")
        print(f"  Mode: {mode}")
        print(f"  Job ID: {job_id}")
        
        return ticket_id
    
    def process_tasks(self, parallel: bool = True, simple: bool = False):
        """Process pending tasks."""
        print("Processing tasks...")
        
        if simple:
            return self._process_tasks_simple()
        
        # Existing logic continues...
        
        if parallel:
            results = self.parallel_orchestrator.process_all_parallel()
            
            if results:
                print(f"Processed {len(results)} tasks in parallel:")
                for ticket_id, success in results.items():
                    status = "✓" if success else "✗"
                    print(f"  {status} {ticket_id}")
            else:
                print("No tasks ready for processing")
        else:
            # Single-threaded processing
            snapshots = self.orchestrator.load_snapshots()
            processed = 0
            
            for ticket_id, snapshot in snapshots.items():
                if snapshot["status"] not in ["COMPLETED", "FAILED"]:
                    success = self.orchestrator.process_ticket(ticket_id)
                    status = "✓" if success else "✗"
                    print(f"  {status} {ticket_id}")
                    processed += 1
            
            if processed == 0:
                print("No tasks to process")
    
    def show_status(self):
        """Show system status."""
        print("AET System Status")
        print("=" * 50)
        
        # Use simple snapshot analysis (more reliable)
        snapshots = self.orchestrator.load_snapshots()
        statuses = {}
        
        for snapshot in snapshots.values():
            status = snapshot['status']
            statuses[status] = statuses.get(status, 0) + 1
        
        for status, count in statuses.items():
            print(f"{status}: {count}")
        
        # Show individual tasks
        if snapshots:
            print("\nTasks:")
            for ticket_id, snapshot in snapshots.items():
                status = snapshot['status']
                desc = snapshot.get('description', 'No description')[:50]
                print(f"  {ticket_id}: {status} - {desc}")
        
        # System health
        print("\nSystem Health:")
        health = self.metrics.get_system_health()
        print(f"Health Score: {health['health_score']:.1f}/100")
        print(f"Events (Last Hour): {health['events_last_hour']}")
        print(f"Total Files: {health['file_consistency']['total_files']}")
    
    def show_logs(self, ticket_id: str = None):
        """Show event logs."""
        events = self.event_logger.replay_events()
        
        if ticket_id:
            events = [e for e in events if e.get('ticket_id') == ticket_id]
        
        # Show last 20 events
        for event in events[-20:]:
            timestamp = datetime.fromtimestamp(event['timestamp']/1000)
            print(f"[{timestamp.strftime('%H:%M:%S')}] {event['type']}: {event.get('description', '')}")
    
    def verify_consistency(self):
        """Verify file system consistency."""
        print("Verifying file consistency...")
        
        try:
            from verify_consistency import ConsistencyVerifier
            verifier = ConsistencyVerifier()
            result = verifier.verify_consistency()
            
            print(f"Status: {result['status']}")
            print(f"Files checked: {result['total_files_checked']}")
            print(f"Issues found: {result['total_issues']}")
            
            if result['issues']:
                print("\nIssues:")
                for issue in result['issues'][:10]:  # Show first 10
                    print(f"  - {issue}")
        except ImportError:
            print("Consistency verifier not available")
    
    def show_metrics(self):
        """Show system metrics."""
        report = self.metrics.generate_report()
        print(report)
    
    def show_health(self):
        """Show system health."""
        health = self.metrics.get_system_health()
        print(json.dumps(health, indent=2))
    
    def rebuild_state(self, from_timestamp: int = None):
        """Rebuild system state from event log."""
        print("Starting state rebuild...")
        
        if from_timestamp:
            print(f"Rebuilding from timestamp: {from_timestamp}")
        else:
            print("Rebuilding complete state from all events")
        
        # Progress callback
        def progress_callback(current, total):
            percent = (current / total) * 100
            print(f"\rProgress: {current}/{total} ({percent:.1f}%)", end="", flush=True)
        
        # Perform rebuild
        result = self.state_rebuilder.rebuild_from_events(
            from_timestamp=from_timestamp,
            progress_callback=progress_callback
        )
        
        print()  # New line after progress
        
        if result['status'] == 'success':
            print("✓ State rebuild completed successfully")
            print(f"  Events processed: {result['events_processed']}")
            if result.get('events_skipped', 0) > 0:
                print(f"  Events skipped: {result['events_skipped']}")
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
            
            if result['events_processed'] > 0:
                print(f"  Processing speed: {result['events_per_second']:.1f} events/second")
                
                # Performance check
                if result['duration_seconds'] > 300:  # 5 minutes
                    print("⚠ Warning: Rebuild took longer than target (5 minutes)")
                else:
                    print("✓ Rebuild completed within performance target")
        else:
            print("✗ State rebuild failed")
            print(f"  Error: {result.get('error', 'Unknown error')}")
            print(f"  Duration: {result['duration_seconds']:.2f} seconds")
            
        return result['status'] == 'success'
    
    def verify_state(self):
        """Verify system state consistency."""
        print("Verifying state consistency...")
        
        result = self.state_rebuilder.verify_state_consistency()
        
        print(f"Status: {result['status']}")
        
        if result['status'] == 'consistent':
            print("✓ All state components are consistent")
        elif result['status'] == 'inconsistent':
            print("⚠ State inconsistencies detected:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print("✗ State verification failed:")
            for issue in result['issues']:
                print(f"  - {issue}")
        
        return result['status'] == 'consistent'
    
    def _process_tasks_simple(self):
        """Process tasks using simple mode."""
        print("Processing tasks in simple mode...")
        
        snapshots = self.orchestrator.load_snapshots()
        processed = 0
        
        for ticket_id, snapshot in snapshots.items():
            # Process simple mode tasks or fallback complex tasks to simple
            mode = snapshot.get('mode', 'full')
            
            if snapshot["status"] not in ["COMPLETED", "FAILED"]:
                if mode == "simple" or self._should_fallback_to_simple(snapshot):
                    print(f"Processing {ticket_id} in simple mode...")
                    result = self.simple_orchestrator.process_task(
                        snapshot["description"], 
                        ticket_id
                    )
                    
                    # Update snapshot
                    snapshot["status"] = "COMPLETED" if result["success"] else "FAILED"
                    snapshot["mode"] = "simple"
                    snapshot["simple_result"] = result
                    self.orchestrator.save_snapshot(ticket_id, snapshot)
                    
                    status = "✓" if result["success"] else "✗"
                    print(f"  {status} {ticket_id} (simple mode)")
                    processed += 1
                else:
                    print(f"  Skipping {ticket_id} (requires full mode)")
        
        if processed == 0:
            print("No tasks suitable for simple mode processing")
            
        return processed
    
    def _should_fallback_to_simple(self, snapshot: Dict) -> bool:
        """Determine if a task should fallback to simple mode."""
        # Check if full mode dependencies are available
        try:
            # Try to import complex dependencies
            from km_server import KnowledgeManager
            from parallel_orchestrator import ParallelOrchestrator
            return False  # Full mode available
        except ImportError:
            return True  # Fallback to simple
        except Exception:
            return True  # Fallback on any error
    
    def process_simple(self, description: str) -> bool:
        """Process a single task in simple mode immediately."""
        print(f"Processing task in simple mode: {description}")
        
        result = self.simple_orchestrator.process_task(description)
        
        success = result.get("success", False)
        status = "✓" if success else "✗"
        
        print(f"{status} Task processed in simple mode")
        if not success and "error" in result:
            print(f"  Error: {result['error']}")
        
        if result.get("files_changed"):
            print(f"  Files modified: {len(result['files_changed'])}")
            for file_path in result["files_changed"]:
                print(f"    - {file_path}")
        
        return success

def main():
    parser = argparse.ArgumentParser(description='AET - Autonomous Engineering Team CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    subparsers.add_parser('init', help='Initialize AET system')
    
    # Create command
    create_parser = subparsers.add_parser('create', help='Create new task')
    create_parser.add_argument('description', help='Task description')
    create_parser.add_argument('--mode', choices=['full', 'simple', 'auto'], default='full', 
                              help='Processing mode (default: full)')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process pending tasks')
    process_parser.add_argument('--serial', action='store_true', help='Process tasks serially')
    process_parser.add_argument('--simple', action='store_true', help='Use simple mode for processing')
    
    # Simple command - immediate simple mode processing
    simple_parser = subparsers.add_parser('simple', help='Process task immediately in simple mode')
    simple_parser.add_argument('description', help='Task description')
    
    # Status command
    subparsers.add_parser('status', help='Show system status')
    
    # Logs command
    logs_parser = subparsers.add_parser('logs', help='Show event logs')
    logs_parser.add_argument('--ticket', help='Filter by ticket ID')
    
    # Verify command
    subparsers.add_parser('verify', help='Verify file consistency')
    
    # Metrics command
    subparsers.add_parser('metrics', help='Show system metrics')
    
    # Health command
    subparsers.add_parser('health', help='Show system health')
    
    # Rebuild command
    rebuild_parser = subparsers.add_parser('rebuild', help='Rebuild system state from events')
    rebuild_parser.add_argument('--from-timestamp', type=int, help='Rebuild from specific timestamp')
    
    # Verify state command  
    subparsers.add_parser('verify-state', help='Verify system state consistency')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = AETCLI()
    
    try:
        if args.command == 'init':
            cli.init_system()
        
        elif args.command == 'create':
            cli.create_task(args.description, args.mode)
        
        elif args.command == 'process':
            cli.process_tasks(parallel=not args.serial, simple=args.simple)
        
        elif args.command == 'status':
            cli.show_status()
        
        elif args.command == 'logs':
            cli.show_logs(args.ticket)
        
        elif args.command == 'verify':
            cli.verify_consistency()
        
        elif args.command == 'metrics':
            cli.show_metrics()
        
        elif args.command == 'health':
            cli.show_health()
        
        elif args.command == 'rebuild':
            success = cli.rebuild_state(args.from_timestamp)
            if not success:
                return 1
        
        elif args.command == 'verify-state':
            success = cli.verify_state()
            if not success:
                return 1
        
        elif args.command == 'simple':
            success = cli.process_simple(args.description)
            if not success:
                return 1
        
        else:
            print(f"Unknown command: {args.command}")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())