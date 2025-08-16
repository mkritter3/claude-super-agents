#!/usr/bin/env python3
"""
Quick verification script for Phase 0 implementations
Tests core functionality without full test suite
"""

import sys
import json
import time
import tempfile
import shutil
from pathlib import Path

# Add system path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "system"))

def test_structured_logging():
    """Test that structured logging works."""
    print("Testing structured logging...")
    
    try:
        from logger_config import get_contextual_logger, StructuredFormatter
        
        # Test logger creation
        logger = get_contextual_logger("test", 
                                     ticket_id="VERIFY-001", 
                                     agent="test-agent",
                                     component="verification")
        
        # Test formatter
        formatter = StructuredFormatter()
        
        print("✅ Structured logging imports successfully")
        return True
    except Exception as e:
        print(f"❌ Structured logging failed: {e}")
        return False

def test_circuit_breaker():
    """Test that circuit breaker is integrated."""
    print("Testing circuit breaker integration...")
    
    try:
        from context_assembler import ContextAssembler
        from reliability import CircuitBreaker
        
        # Create assembler
        assembler = ContextAssembler()
        
        # Check circuit breaker exists
        assert hasattr(assembler, 'km_circuit_breaker')
        assert isinstance(assembler.km_circuit_breaker, CircuitBreaker)
        
        print("✅ Circuit breaker integrated successfully")
        return True
    except Exception as e:
        print(f"❌ Circuit breaker integration failed: {e}")
        return False

def test_fallback_context():
    """Test fallback context generation."""
    print("Testing fallback context generation...")
    
    try:
        # Create temp directory for test
        temp_dir = tempfile.mkdtemp()
        original_cwd = Path.cwd()
        
        try:
            # Create test structure
            test_dir = Path(temp_dir)
            (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
            
            import os
            os.chdir(temp_dir)
            
            from context_assembler import ContextAssembler
            
            assembler = ContextAssembler()
            
            # Test fallback context generation
            start_time = time.time()
            context = assembler._get_fallback_context("developer-agent")
            duration = time.time() - start_time
            
            # Verify structure
            required_fields = ['knowledge', 'results', 'fallback_mode', 'fallback_reason']
            for field in required_fields:
                assert field in context, f"Missing field: {field}"
            
            assert context['fallback_mode'] is True
            assert duration < 0.1, f"Too slow: {duration:.3f}s"
            
            print(f"✅ Fallback context generation works ({duration:.3f}s)")
            return True
            
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(temp_dir)
    
    except Exception as e:
        print(f"❌ Fallback context generation failed: {e}")
        return False

def test_deployment_script():
    """Test that deployment script exists and is executable."""
    print("Testing deployment script...")
    
    try:
        script_path = Path(__file__).parent / "deploy_km.sh"
        
        if not script_path.exists():
            print("❌ Deployment script not found")
            return False
        
        if not script_path.is_file():
            print("❌ Deployment script is not a file")
            return False
        
        # Check if executable
        import stat
        st = script_path.stat()
        if not (st.st_mode & stat.S_IEXEC):
            print("❌ Deployment script is not executable")
            return False
        
        print("✅ Deployment script exists and is executable")
        return True
    
    except Exception as e:
        print(f"❌ Deployment script check failed: {e}")
        return False

def test_json_logging_output():
    """Test that logging actually outputs JSON."""
    print("Testing JSON log output...")
    
    try:
        import io
        import logging
        from logger_config import StructuredFormatter
        
        # Create string buffer to capture output
        log_stream = io.StringIO()
        
        # Create handler with structured formatter
        handler = logging.StreamHandler(log_stream)
        handler.setFormatter(StructuredFormatter())
        
        # Create test logger
        test_logger = logging.getLogger("json_test")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.INFO)
        
        # Log a test message
        test_logger.info("Test JSON message", extra={
            'ticket_id': 'JSON-001',
            'component': 'verification'
        })
        
        # Get output and verify it's valid JSON
        output = log_stream.getvalue().strip()
        
        if not output:
            print("❌ No log output generated")
            return False
        
        # Parse as JSON
        log_data = json.loads(output)
        
        # Verify required fields
        required_fields = ['timestamp', 'level', 'message', 'ticket_id']
        for field in required_fields:
            if field not in log_data:
                print(f"❌ Missing required field in JSON: {field}")
                return False
        
        # Verify values
        assert log_data['level'] == 'INFO'
        assert log_data['message'] == 'Test JSON message'
        assert log_data['ticket_id'] == 'JSON-001'
        assert log_data['component'] == 'verification'
        
        print("✅ JSON logging output works correctly")
        return True
    
    except json.JSONDecodeError as e:
        print(f"❌ Log output is not valid JSON: {e}")
        print(f"Output was: {output}")
        return False
    except Exception as e:
        print(f"❌ JSON logging test failed: {e}")
        return False

def test_context_assembly_with_failure():
    """Test context assembly handles KM failure gracefully."""
    print("Testing context assembly with KM failure...")
    
    try:
        # Create temp directory for test
        temp_dir = tempfile.mkdtemp()
        original_cwd = Path.cwd()
        
        try:
            # Create test structure
            test_dir = Path(temp_dir)
            (test_dir / ".claude" / "events").mkdir(parents=True, exist_ok=True)
            (test_dir / ".claude" / "registry").mkdir(parents=True, exist_ok=True)
            (test_dir / ".claude" / "logs").mkdir(parents=True, exist_ok=True)
            (test_dir / ".claude" / "workspaces" / "test-job").mkdir(parents=True, exist_ok=True)
            
            import os
            os.chdir(temp_dir)
            
            from context_assembler import ContextAssembler
            from unittest.mock import patch
            import requests
            
            assembler = ContextAssembler()
            
            # Mock KM failure
            with patch('requests.post', side_effect=requests.ConnectionError("KM unavailable")):
                context = assembler.assemble_intelligent_context(
                    ticket_id="FAIL-001",
                    job_id="test-job",
                    agent_type="developer-agent"
                )
            
            # Verify context is still functional
            assert 'knowledge' in context
            assert 'dependencies' in context
            assert 'workspace' in context
            
            # Verify workspace info is correct
            assert context['workspace']['ticket_id'] == "FAIL-001"
            assert context['workspace']['job_id'] == "test-job"
            
            print("✅ Context assembly handles KM failure gracefully")
            return True
            
        finally:
            os.chdir(original_cwd)
            shutil.rmtree(temp_dir)
    
    except Exception as e:
        print(f"❌ Context assembly failure test failed: {e}")
        return False

def main():
    """Run all verification tests."""
    print("🔍 Phase 0 Critical Fixes - Quick Verification")
    print("=" * 60)
    
    tests = [
        ("Structured Logging", test_structured_logging),
        ("Circuit Breaker Integration", test_circuit_breaker),
        ("Fallback Context Generation", test_fallback_context),
        ("Deployment Script", test_deployment_script),
        ("JSON Log Output", test_json_logging_output),
        ("Context Assembly Resilience", test_context_assembly_with_failure)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            else:
                print(f"   Test failed")
        except Exception as e:
            print(f"   Test error: {e}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL PHASE 0 VERIFICATIONS PASSED!")
        print("✅ Circuit breakers are integrated")
        print("✅ Structured logging is working")
        print("✅ Fallback context generation is functional")
        print("✅ System is resilient to KM failures")
        print("✅ Deployment tools are ready")
        print("\n➡️  Ready to proceed with full test suite")
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed")
        print("❌ Please fix issues before running full test suite")
        print("\nNext steps:")
        print("1. Review failed verifications above")
        print("2. Fix any import or integration issues")
        print("3. Re-run this verification script")
        print("4. Run full test suite: python .claude/tests/phase0/run_phase0_tests.py")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)