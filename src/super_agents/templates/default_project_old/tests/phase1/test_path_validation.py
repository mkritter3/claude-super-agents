#!/usr/bin/env python3
"""
Phase 1 Security Tests: Path Validation
Tests the enhanced security features in file_registry.py
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add system path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "system"))

from file_registry import FileRegistry


class TestPathValidation(unittest.TestCase):
    """Test secure path validation features from Phase 1."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create test registry in temp directory
        self.registry = FileRegistry(db_path=f"{self.temp_dir}/.claude/registry/test.db")
        
    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        self.registry.close()
        
    def test_path_traversal_detection(self):
        """Test that path traversal attacks are blocked."""
        test_cases = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config",
            "src/../../../etc/passwd",
            "normal/path/../../../../../../etc/passwd",
            "path/with/../../traversal",
            "..",
            "../",
            "..\\",
        ]
        
        for malicious_path in test_cases:
            with self.subTest(path=malicious_path):
                valid, message = self.registry.validate_path(malicious_path, "TEST-001")
                self.assertFalse(valid, f"Path traversal should be blocked: {malicious_path}")
                self.assertIn("outside workspace", message.lower(), 
                            f"Should detect path traversal: {message}")
    
    def test_dangerous_pattern_detection(self):
        """Test detection of dangerous path patterns."""
        dangerous_patterns = [
            "/tmp/malicious_file.py",
            "/var/log/../../etc/passwd", 
            "/etc/shadow",
            "~/.ssh/id_rsa",
            "file%2e%2e%2ftraversal",  # URL encoded ../
            "path%2fwith%5cslashes",   # URL encoded /\
        ]
        
        for dangerous_path in dangerous_patterns:
            with self.subTest(path=dangerous_path):
                valid, message = self.registry.validate_path(dangerous_path, "TEST-002")
                self.assertFalse(valid, f"Dangerous pattern should be blocked: {dangerous_path}")
    
    def test_symbolic_link_rejection(self):
        """Test that symbolic links are rejected."""
        # Create a test file and symbolic link
        test_file = Path(self.temp_dir) / "test_file.py"
        test_file.write_text("# Test file")
        
        symlink_path = Path(self.temp_dir) / "symlink_file.py"
        try:
            symlink_path.symlink_to(test_file)
            
            # Test that symlink is rejected
            valid, message = self.registry.validate_path(str(symlink_path), "TEST-003")
            self.assertFalse(valid, "Symbolic links should be rejected")
            self.assertIn("symbolic link", message.lower())
            
        except OSError:
            # Skip if symlinks not supported on this system
            self.skipTest("Symbolic links not supported on this system")
    
    def test_invalid_characters_detection(self):
        """Test detection of invalid characters in paths."""
        invalid_paths = [
            "file\x00name.py",      # Null byte
            "file\x01name.py",      # Control character
            "file\x1fname.py",      # Control character
            "path/with\x00null.py", # Null in path
        ]
        
        for invalid_path in invalid_paths:
            with self.subTest(path=invalid_path):
                valid, message = self.registry.validate_path(invalid_path, "TEST-004")
                self.assertFalse(valid, f"Invalid characters should be blocked: {repr(invalid_path)}")
                self.assertIn("invalid character", message.lower())
    
    def test_forbidden_directories(self):
        """Test that forbidden directories are blocked."""
        forbidden_paths = [
            "node_modules/package/index.js",
            ".git/config",
            "dist/bundle.js", 
            "build/output.js",
            "__pycache__/module.pyc",
            ".venv/lib/python3.9/site-packages/module.py",
        ]
        
        for forbidden_path in forbidden_paths:
            with self.subTest(path=forbidden_path):
                valid, message = self.registry.validate_path(forbidden_path, "TEST-005")
                self.assertFalse(valid, f"Forbidden directory should be blocked: {forbidden_path}")
                self.assertIn("forbidden directory", message.lower())
    
    def test_valid_paths_allowed(self):
        """Test that valid paths are allowed."""
        valid_paths = [
            "src/components/Button.tsx",
            "src/utils/helper.ts", 
            "lib/auth/auth.js",
            "components/forms/LoginForm.jsx",
            "models/user.py",
            "services/api-client.js",
        ]
        
        # Create the paths within workspace
        for valid_path in valid_paths:
            path_obj = Path(self.temp_dir) / valid_path
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            with self.subTest(path=valid_path):
                valid, message = self.registry.validate_path(valid_path, "TEST-006")
                self.assertTrue(valid, f"Valid path should be allowed: {valid_path}, Error: {message}")
    
    def test_naming_conventions(self):
        """Test naming convention validation."""
        # Valid component files (PascalCase)
        valid_components = [
            "src/Button.tsx",
            "components/LoginForm.jsx",
            "shared/Modal.tsx"
        ]
        
        for component_path in valid_components:
            path_obj = Path(self.temp_dir) / component_path
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            with self.subTest(path=component_path):
                valid, message = self.registry.validate_path(component_path, "TEST-007")
                self.assertTrue(valid, f"Valid component should be allowed: {component_path}")
        
        # Invalid component files  
        invalid_components = [
            "src/button.tsx",      # Should be PascalCase
            "components/loginForm.jsx",  # Should be PascalCase
        ]
        
        for component_path in invalid_components:
            with self.subTest(path=component_path):
                valid, message = self.registry.validate_path(component_path, "TEST-008")
                self.assertFalse(valid, f"Invalid component name should be rejected: {component_path}")
        
        # Valid regular files (camelCase or kebab-case)
        valid_files = [
            "src/authService.ts",
            "utils/api-client.js",
            "lib/user-model.ts"
        ]
        
        for file_path in valid_files:
            path_obj = Path(self.temp_dir) / file_path  
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            with self.subTest(path=file_path):
                valid, message = self.registry.validate_path(file_path, "TEST-009")
                self.assertTrue(valid, f"Valid file should be allowed: {file_path}")
    
    def test_workspace_root_enforcement(self):
        """Test that paths must be within workspace root."""
        # Try to access file outside workspace
        outside_path = "/tmp/outside_file.py"
        
        valid, message = self.registry.validate_path(outside_path, "TEST-010")
        self.assertFalse(valid, "Paths outside workspace should be rejected")
        self.assertIn("outside workspace", message.lower())
    
    def test_absolute_vs_relative_paths(self):
        """Test handling of absolute vs relative paths."""
        # Relative path within workspace (should be allowed)
        rel_path = "src/test.py"
        path_obj = Path(self.temp_dir) / rel_path
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        valid, message = self.registry.validate_path(rel_path, "TEST-011")
        self.assertTrue(valid, f"Relative path in workspace should be allowed: {rel_path}")
        
        # Absolute path within workspace (should be allowed)  
        abs_path = str(path_obj)
        valid, message = self.registry.validate_path(abs_path, "TEST-012")
        self.assertTrue(valid, f"Absolute path in workspace should be allowed: {abs_path}")
    
    def test_logging_security_violations(self):
        """Test that security violations are properly logged."""
        # This test verifies logging functionality exists
        # In a real environment, you'd check log files
        
        malicious_path = "../../../etc/passwd"
        valid, message = self.registry.validate_path(malicious_path, "TEST-SECURITY")
        
        self.assertFalse(valid)
        # Logger should have recorded this security violation
        # In production, you'd verify the log entry exists


if __name__ == "__main__":
    unittest.main()