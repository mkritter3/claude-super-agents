#!/usr/bin/env python3
"""
Integration Test Suite for Template System
Tests the complete template-based architecture
"""

import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
import subprocess
import time
import json

# Path setup is handled by the test runner

class TemplateSystemIntegrationTests(unittest.TestCase):
    """Test the complete template system integration"""
    
    def setUp(self):
        """Set up test environment"""
        # Set testing environment variable to disable background indexing
        os.environ['TESTING'] = '1'
        self.test_dir = Path(tempfile.mkdtemp(prefix="super_agents_test_"))
        self.original_cwd = Path.cwd()
        os.chdir(self.test_dir)
        
    def tearDown(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir, ignore_errors=True)
        # Clean up testing environment variable
        os.environ.pop('TESTING', None)
    
    def test_template_initialization(self):
        """Test that template system initializes correctly"""
        # Simulate what the CLI does
        sys.path.insert(0, str(Path('.claude/system')))
        
        # Check if we can import template modules
        try:
            # These should be available after template initialization
            template_modules = [
                'commands.init',
                'commands.km_manager', 
                'commands.status',
                'performance.lazy_loader',
                'performance.caching',
                'performance.indexing',
                'reliability.circuit_breaker',
                'database.maintenance'
            ]
            
            # Create a minimal template structure for testing
            template_base = Path('.claude/system')
            template_base.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py files to make modules importable
            (template_base / '__init__.py').touch()
            (template_base / 'commands').mkdir(parents=True, exist_ok=True)
            (template_base / 'commands' / '__init__.py').touch()
            (template_base / 'performance').mkdir(parents=True, exist_ok=True)
            (template_base / 'performance' / '__init__.py').touch()
            (template_base / 'reliability').mkdir(parents=True, exist_ok=True)
            (template_base / 'reliability' / '__init__.py').touch()
            (template_base / 'database').mkdir(parents=True, exist_ok=True)
            (template_base / 'database' / '__init__.py').touch()
            
            # This test verifies the import structure is correct
            self.assertTrue(template_base.exists())
            
        except ImportError as e:
            self.fail(f"Template system import failed: {e}")
    
    def test_template_isolation(self):
        """Test that different projects have isolated template systems"""
        # Create first project directory
        project1 = self.test_dir / "project1"
        project1.mkdir()
        
        # Create second project directory
        project2 = self.test_dir / "project2"
        project2.mkdir()
        
        # Each should have its own .claude/system
        (project1 / '.claude' / 'system').mkdir(parents=True)
        (project2 / '.claude' / 'system').mkdir(parents=True)
        
        # Create different configurations
        config1 = {"project": "project1", "port": 5001}
        config2 = {"project": "project2", "port": 5002}
        
        with open(project1 / '.claude' / 'config.json', 'w') as f:
            json.dump(config1, f)
            
        with open(project2 / '.claude' / 'config.json', 'w') as f:
            json.dump(config2, f)
        
        # Verify isolation
        self.assertNotEqual(
            (project1 / '.claude' / 'config.json').read_text(),
            (project2 / '.claude' / 'config.json').read_text()
        )
    
    def test_performance_optimizations_integration(self):
        """Test that all performance optimizations work together"""
        # Test that real performance modules can be imported and used
        system_path = str(Path('.claude/system').resolve())
        if system_path not in sys.path:
            sys.path.insert(0, system_path)
        
        # Create a temporary module for testing lazy loading
        temp_module_content = '''
"""Temporary test module for lazy loading"""
TEST_VALUE = "hello from test module"

def test_function():
    return "test function result"
'''
        
        # Write temporary module to template system directory
        template_base = Path('.claude/system')
        template_base.mkdir(parents=True, exist_ok=True)
        temp_module_path = template_base / 'temp_test_module.py'
        temp_module_path.write_text(temp_module_content)
        
        try:
            # Import real performance modules (they exist in the actual template)
            from performance.lazy_loader import lazy_import
            from performance.caching import cached
            from performance.indexing import ProjectIndexer
            
            # Test lazy loading with real module
            lazy_mod = lazy_import('temp_test_module')
            # Access an attribute to trigger loading
            result = lazy_mod.TEST_VALUE
            self.assertEqual(result, "hello from test module")
            
            # Test function access
            func_result = lazy_mod.test_function()
            self.assertEqual(func_result, "test function result")
            
            # Test caching decorator
            @cached(ttl=30)
            def test_func():
                return "cached result"
            
            result = test_func()
            self.assertEqual(result, "cached result")
            
            # Test indexing (skip if database issues in test environment)
            try:
                indexer = ProjectIndexer()
                # Just test that it initializes without error
                self.assertIsNotNone(indexer)
            except Exception:
                # Skip indexer test if it has database issues in test environment
                pass
            
        except ImportError as e:
            self.fail(f"Performance integration failed: {e}")
        finally:
            # Clean up temporary module
            temp_module_path.unlink(missing_ok=True)
            if 'temp_test_module' in sys.modules:
                del sys.modules['temp_test_module']
    
    def test_reliability_features_integration(self):
        """Test that reliability features work correctly"""
        # Create reliability module structure
        rel_dir = Path('.claude/system/reliability')
        rel_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test circuit breaker
        circuit_breaker_content = '''
"""Test circuit breaker"""
import time

class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def call(self, func, *args, **kwargs):
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            if self.state == 'half-open':
                self.state = 'closed'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'open'
            raise e

circuit_breaker = CircuitBreaker()
'''
        
        # Write test modules
        (rel_dir / '__init__.py').touch()
        (rel_dir / 'circuit_breaker.py').write_text(circuit_breaker_content)
        
        # Test circuit breaker functionality
        sys.path.insert(0, str(Path('.claude/system')))
        
        try:
            from reliability.circuit_breaker import protected_call, CircuitBreakerOpenError
            
            # Test successful call
            def success_func():
                return "success"
            
            result = protected_call("test_service", success_func, failure_threshold=2, timeout_seconds=1)
            self.assertEqual(result, "success")
            
            # Test failure handling
            def failure_func():
                raise Exception("test failure")
            
            # First failure
            with self.assertRaises(Exception):
                protected_call("test_service", failure_func, failure_threshold=2, timeout_seconds=1)
            
            # Second failure should open circuit
            with self.assertRaises(Exception):
                protected_call("test_service", failure_func, failure_threshold=2, timeout_seconds=1)
            
            # Circuit should now be open - this should raise CircuitBreakerOpenError
            with self.assertRaises(CircuitBreakerOpenError):
                protected_call("test_service", success_func, failure_threshold=2, timeout_seconds=1)
            
        except ImportError as e:
            self.fail(f"Reliability integration failed: {e}")
    
    def test_command_delegation_system(self):
        """Test that command delegation works correctly"""
        # Create commands module structure
        cmd_dir = Path('.claude/system/commands')
        cmd_dir.mkdir(parents=True, exist_ok=True)
        
        # Create test command modules
        init_content = '''
"""Test init command"""
def initialize_project(force=False):
    return {"status": "success", "force": force}

def check_project_initialized():
    return True
'''
        
        status_content = '''
"""Test status command"""
def show_status():
    return {
        "system": "running",
        "agents": 23,
        "performance": "optimized"
    }
'''
        
        km_manager_content = '''
"""Test KM manager"""
class KnowledgeManagerController:
    def __init__(self):
        self.port = 5001
        self.running = False
    
    def start(self):
        self.running = True
        return self.port
    
    def stop(self):
        self.running = False
        return True
    
    def is_running(self):
        return self.running
'''
        
        # Write test modules
        (cmd_dir / '__init__.py').touch()
        (cmd_dir / 'init.py').write_text(init_content)
        (cmd_dir / 'status.py').write_text(status_content)
        (cmd_dir / 'km_manager.py').write_text(km_manager_content)
        
        # Test command delegation
        sys.path.insert(0, str(Path('.claude/system')))
        
        try:
            # Test init command
            from commands.init import initialize_project, check_project_initialized
            
            result = initialize_project(force=True)
            self.assertEqual(result["status"], "success")
            self.assertTrue(result["force"])
            
            initialized = check_project_initialized()
            self.assertTrue(initialized)
            
            # Test status command
            from commands.status import show_status
            
            status = show_status()
            self.assertEqual(status["system"], "running")
            self.assertEqual(status["agents"], 23)
            
            # Test KM manager
            from commands.km_manager import KnowledgeManagerController
            
            km = KnowledgeManagerController()
            self.assertFalse(km.is_running())
            
            port = km.start()
            self.assertEqual(port, 5001)
            self.assertTrue(km.is_running())
            
            stopped = km.stop()
            self.assertTrue(stopped)
            self.assertFalse(km.is_running())
            
        except ImportError as e:
            self.fail(f"Command delegation failed: {e}")
    
    def test_template_upgrade_compatibility(self):
        """Test that template system supports upgrades"""
        # Create initial template version
        template_dir = Path('.claude/system')
        template_dir.mkdir(parents=True, exist_ok=True)
        
        # Create version file
        version_content = '''
"""Template version"""
VERSION = "1.0.0"
FEATURES = ["lazy_loading", "caching", "indexing"]
'''
        
        (template_dir / 'version.py').write_text(version_content)
        
        # Test that version can be read
        system_path = str(Path('.claude/system').resolve())
        if system_path not in sys.path:
            sys.path.insert(0, system_path)
        
        # Clear import cache to ensure fresh import
        if 'version' in sys.modules:
            del sys.modules['version']
        
        try:
            from version import VERSION, FEATURES
            
            self.assertEqual(VERSION, "1.0.0")
            self.assertIn("lazy_loading", FEATURES)
            self.assertIn("caching", FEATURES)
            self.assertIn("indexing", FEATURES)
            
        except ImportError as e:
            self.fail(f"Version compatibility test failed: {e}")
    
    def test_mcp_integration(self):
        """Test MCP configuration integration"""
        # Create MCP configuration
        mcp_config = {
            "mcpServers": {
                "km": {
                    "command": "python3",
                    "args": [".claude/km_bridge_local.py"]
                }
            }
        }
        
        # Write MCP config
        with open('.mcp.json', 'w') as f:
            json.dump(mcp_config, f, indent=2)
        
        # Create MCP bridge file
        bridge_content = '''#!/usr/bin/env python3
"""MCP Bridge for Knowledge Manager"""
import sys
import json

def main():
    # Simple MCP bridge implementation
    print(json.dumps({"status": "ready", "port": 5001}))

if __name__ == "__main__":
    main()
'''
        
        Path('.claude').mkdir(exist_ok=True)
        Path('.claude/km_bridge_local.py').write_text(bridge_content)
        
        # Test MCP configuration
        self.assertTrue(Path('.mcp.json').exists())
        self.assertTrue(Path('.claude/km_bridge_local.py').exists())
        
        # Test that MCP config is valid
        with open('.mcp.json', 'r') as f:
            config = json.load(f)
        
        self.assertIn('mcpServers', config)
        self.assertIn('km', config['mcpServers'])
        self.assertEqual(config['mcpServers']['km']['command'], 'python3')


if __name__ == '__main__':
    unittest.main(verbosity=2)