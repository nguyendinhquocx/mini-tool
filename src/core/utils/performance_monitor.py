"""
Performance Monitoring Utilities

Provides system resource monitoring và performance metrics collection
for optimizing application performance during large operations.
"""

import psutil
import time
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Single point-in-time performance measurement"""
    memory_usage_mb: float
    cpu_percentage: float
    io_read_bytes: int
    io_write_bytes: int
    operation_duration_ms: float
    files_per_second: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetrics':
        """Create from dictionary"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class PerformanceThresholds:
    """Performance threshold configuration"""
    max_memory_mb: float = 1024.0
    max_cpu_percentage: float = 80.0
    min_files_per_second: float = 10.0
    max_operation_duration_ms: float = 30000.0  # 30 seconds
    
    def check_violations(self, metrics: PerformanceMetrics) -> List[str]:
        """Check for threshold violations"""
        violations = []
        
        if metrics.memory_usage_mb > self.max_memory_mb:
            violations.append(f"Memory usage ({metrics.memory_usage_mb:.1f}MB) exceeds threshold ({self.max_memory_mb}MB)")
        
        if metrics.cpu_percentage > self.max_cpu_percentage:
            violations.append(f"CPU usage ({metrics.cpu_percentage:.1f}%) exceeds threshold ({self.max_cpu_percentage}%)")
        
        if metrics.files_per_second < self.min_files_per_second and metrics.files_per_second > 0:
            violations.append(f"Processing rate ({metrics.files_per_second:.1f} files/sec) below threshold ({self.min_files_per_second})")
        
        if metrics.operation_duration_ms > self.max_operation_duration_ms:
            violations.append(f"Operation duration ({metrics.operation_duration_ms:.0f}ms) exceeds threshold ({self.max_operation_duration_ms:.0f}ms)")
        
        return violations


class PerformanceMonitor:
    """
    System performance monitoring và metrics collection
    
    Tracks memory usage, CPU usage, I/O operations, và custom metrics
    for performance optimization và bottleneck identification.
    """
    
    def __init__(self, history_size: int = 1000):
        self.history_size = history_size
        self.metrics_history: deque = deque(maxlen=history_size)
        self.baseline_memory = psutil.virtual_memory().used
        self.operation_start_time: Optional[float] = None
        self.thresholds = PerformanceThresholds()
        self._lock = threading.Lock()
        self._monitoring_active = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_monitoring = threading.Event()
        
        # Cache for expensive operations
        self._last_io_counters = None
        self._last_io_time = 0
        
        logger.debug("PerformanceMonitor initialized")
    
    def set_thresholds(self, thresholds: PerformanceThresholds):
        """Update performance thresholds"""
        with self._lock:
            self.thresholds = thresholds
        logger.info(f"Performance thresholds updated: {thresholds}")
    
    def start_operation_tracking(self):
        """Begin tracking performance metrics for an operation"""
        with self._lock:
            self.operation_start_time = time.time()
        logger.debug("Started operation tracking")
    
    def record_metrics(self, files_processed: int = 0) -> PerformanceMetrics:
        """
        Record current performance metrics
        
        Args:
            files_processed: Number of files processed so far
            
        Returns:
            Current performance metrics
        """
        try:
            # Get memory information
            memory = psutil.virtual_memory()
            memory_usage_mb = memory.used / (1024 * 1024)
            
            # Get CPU percentage (non-blocking)
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # Get I/O counters với caching
            io_read_bytes, io_write_bytes = self._get_io_counters()
            
            # Calculate operation metrics
            duration_ms = 0
            files_per_second = 0
            
            if self.operation_start_time:
                duration_ms = (time.time() - self.operation_start_time) * 1000
                if duration_ms > 0 and files_processed > 0:
                    files_per_second = files_processed / (duration_ms / 1000)
            
            # Create metrics object
            metrics = PerformanceMetrics(
                memory_usage_mb=memory_usage_mb,
                cpu_percentage=cpu_percent,
                io_read_bytes=io_read_bytes,
                io_write_bytes=io_write_bytes,
                operation_duration_ms=duration_ms,
                files_per_second=files_per_second,
                timestamp=datetime.now()
            )
            
            # Store in history
            with self._lock:
                self.metrics_history.append(metrics)
            
            # Check for threshold violations
            violations = self.thresholds.check_violations(metrics)
            if violations:
                for violation in violations:
                    logger.warning(f"Performance threshold violation: {violation}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recording performance metrics: {e}")
            # Return minimal metrics on error
            return PerformanceMetrics(
                memory_usage_mb=0,
                cpu_percentage=0,
                io_read_bytes=0,
                io_write_bytes=0,
                operation_duration_ms=0,
                files_per_second=0,
                timestamp=datetime.now()
            )
    
    def _get_io_counters(self) -> tuple[int, int]:
        """Get I/O counters với caching for performance"""
        current_time = time.time()
        
        # Cache I/O counters for 1 second to avoid expensive system calls
        if (self._last_io_counters and 
            current_time - self._last_io_time < 1.0):
            return self._last_io_counters
        
        try:
            io_counters = psutil.disk_io_counters()
            if io_counters:
                result = (io_counters.read_bytes, io_counters.write_bytes)
            else:
                result = (0, 0)
            
            self._last_io_counters = result
            self._last_io_time = current_time
            return result
            
        except Exception as e:
            logger.debug(f"Error getting I/O counters: {e}")
            return (0, 0)
    
    def get_performance_summary(self) -> Dict[str, float]:
        """
        Get performance summary for recent operations
        
        Returns:
            Dictionary with performance statistics
        """
        with self._lock:
            if not self.metrics_history:
                return {
                    'avg_memory_mb': 0,
                    'max_memory_mb': 0,
                    'avg_cpu_percent': 0,
                    'max_cpu_percent': 0,
                    'avg_files_per_second': 0,
                    'max_files_per_second': 0,
                    'total_duration_ms': 0,
                    'measurements_count': 0
                }
            
            # Get recent metrics (last 20 measurements or all if fewer)
            recent_metrics = list(self.metrics_history)[-20:]
            
            # Calculate statistics
            memory_values = [m.memory_usage_mb for m in recent_metrics]
            cpu_values = [m.cpu_percentage for m in recent_metrics]
            fps_values = [m.files_per_second for m in recent_metrics if m.files_per_second > 0]
            
            return {
                'avg_memory_mb': sum(memory_values) / len(memory_values),
                'max_memory_mb': max(memory_values),
                'avg_cpu_percent': sum(cpu_values) / len(cpu_values),
                'max_cpu_percent': max(cpu_values),
                'avg_files_per_second': sum(fps_values) / len(fps_values) if fps_values else 0,
                'max_files_per_second': max(fps_values) if fps_values else 0,
                'total_duration_ms': recent_metrics[-1].operation_duration_ms if recent_metrics else 0,
                'measurements_count': len(recent_metrics)
            }
    
    def get_memory_trend(self, duration_minutes: int = 5) -> List[float]:
        """
        Get memory usage trend over specified duration
        
        Args:
            duration_minutes: Duration to analyze
            
        Returns:
            List of memory usage values over time
        """
        cutoff_time = datetime.now() - timedelta(minutes=duration_minutes)
        
        with self._lock:
            recent_metrics = [
                m for m in self.metrics_history 
                if m.timestamp >= cutoff_time
            ]
        
        return [m.memory_usage_mb for m in recent_metrics]
    
    def detect_memory_leaks(self, window_size: int = 50) -> bool:
        """
        Detect potential memory leaks by analyzing memory growth trend
        
        Args:
            window_size: Number of measurements to analyze
            
        Returns:
            True if potential memory leak detected
        """
        with self._lock:
            if len(self.metrics_history) < window_size:
                return False
            
            # Get recent memory measurements
            recent_memory = [
                m.memory_usage_mb for m in list(self.metrics_history)[-window_size:]
            ]
        
        # Simple trend analysis
        first_half = recent_memory[:window_size//2]
        second_half = recent_memory[window_size//2:]
        
        first_avg = sum(first_half) / len(first_half)
        second_avg = sum(second_half) / len(second_half)
        
        # Consider it a leak if memory increased by more than 20%
        growth_threshold = 1.2
        is_leak = second_avg > first_avg * growth_threshold
        
        if is_leak:
            logger.warning(f"Potential memory leak detected: {first_avg:.1f}MB -> {second_avg:.1f}MB")
        
        return is_leak
    
    def start_continuous_monitoring(self, interval_seconds: float = 1.0):
        """
        Start continuous performance monitoring in background thread
        
        Args:
            interval_seconds: Monitoring interval
        """
        if self._monitoring_active:
            logger.warning("Continuous monitoring already active")
            return
        
        self._monitoring_active = True
        self._stop_monitoring.clear()
        
        def monitor_loop():
            logger.info(f"Started continuous monitoring (interval: {interval_seconds}s)")
            
            while not self._stop_monitoring.is_set():
                try:
                    self.record_metrics()
                    time.sleep(interval_seconds)
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    break
            
            logger.info("Continuous monitoring stopped")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_continuous_monitoring(self):
        """Stop continuous performance monitoring"""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._stop_monitoring.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
        
        logger.info("Continuous monitoring stopped")
    
    def export_metrics(self, format: str = 'dict') -> Any:
        """
        Export metrics history for analysis
        
        Args:
            format: Export format ('dict', 'json')
            
        Returns:
            Metrics data in requested format
        """
        with self._lock:
            metrics_data = [m.to_dict() for m in self.metrics_history]
        
        if format == 'json':
            import json
            return json.dumps(metrics_data, indent=2)
        
        return metrics_data
    
    def clear_history(self):
        """Clear metrics history"""
        with self._lock:
            self.metrics_history.clear()
        logger.info("Performance metrics history cleared")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get current system information"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_count': psutil.cpu_count(),
                'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                'memory_total_gb': memory.total / (1024**3),
                'memory_available_gb': memory.available / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'platform': psutil.os.name
            }
        except Exception as e:
            logger.error(f"Error getting system info: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on object destruction"""
        if self._monitoring_active:
            self.stop_continuous_monitoring()


class PerformanceProfiler:
    """Context manager for profiling code blocks"""
    
    def __init__(self, monitor: PerformanceMonitor, operation_name: str):
        self.monitor = monitor
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.monitor.start_operation_tracking()
        logger.debug(f"Started profiling: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        
        metrics = self.monitor.record_metrics()
        
        logger.info(
            f"Profiling complete: {self.operation_name} "
            f"({duration_ms:.1f}ms, {metrics.memory_usage_mb:.1f}MB, "
            f"{metrics.cpu_percentage:.1f}% CPU)"
        )


# Global instance
_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global PerformanceMonitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor


def set_performance_monitor(monitor: PerformanceMonitor):
    """Set global PerformanceMonitor instance"""
    global _performance_monitor
    _performance_monitor = monitor