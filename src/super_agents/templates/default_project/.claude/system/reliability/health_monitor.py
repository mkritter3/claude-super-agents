"""
Health monitoring system for system components
"""

import time
import threading
from typing import Dict, Callable, Any
from dataclasses import dataclass


@dataclass
class HealthCheckResult:
    """Result of a health check"""
    status: str  # "healthy", "warning", "unhealthy"
    response_time: float
    details: Dict[str, Any]
    timestamp: float


class HealthMonitor:
    """System health monitoring"""
    
    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.monitoring = False
        self.monitor_thread = None
        self.check_interval = 30  # seconds
        
    def register_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function
        
        Args:
            name: Name of the health check
            check_func: Function that returns health status
        """
        self.checks[name] = check_func
        
    def run_check(self, name: str) -> HealthCheckResult:
        """
        Run a specific health check
        
        Args:
            name: Name of the health check to run
            
        Returns:
            Health check result
        """
        if name not in self.checks:
            return HealthCheckResult(
                status="unhealthy",
                response_time=0,
                details={"error": f"Health check '{name}' not found"},
                timestamp=time.time()
            )
            
        start_time = time.time()
        try:
            result = self.checks[name]()
            response_time = time.time() - start_time
            
            return HealthCheckResult(
                status=result.get("status", "unknown"),
                response_time=response_time,
                details=result,
                timestamp=time.time()
            )
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                status="unhealthy",
                response_time=response_time,
                details={"error": str(e)},
                timestamp=time.time()
            )
    
    def check_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all registered health checks
        
        Returns:
            Dictionary of health check results
        """
        results = {}
        for name in self.checks:
            check_result = self.run_check(name)
            self.results[name] = check_result
            
            results[name] = {
                "status": check_result.status,
                "response_time": check_result.response_time,
                **check_result.details
            }
            
        return results
    
    def start_monitoring(self) -> None:
        """Start continuous health monitoring"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> None:
        """Stop continuous health monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join()
            
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.monitoring:
            self.check_health()
            time.sleep(self.check_interval)
            
    def get_system_status(self) -> str:
        """
        Get overall system status
        
        Returns:
            Overall status: "healthy", "warning", "unhealthy"
        """
        if not self.results:
            return "unknown"
            
        statuses = [result.status for result in self.results.values()]
        
        if "unhealthy" in statuses:
            return "unhealthy"
        elif "warning" in statuses:
            return "warning"
        else:
            return "healthy"