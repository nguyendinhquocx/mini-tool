"""
Resource Optimization Service

Provides adaptive performance scaling, system resource monitoring,
và automatic optimization based on system capabilities.
"""

import psutil
import threading
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum, auto
import logging
import json
from concurrent.futures import ThreadPoolExecutor

from ..utils.performance_monitor import get_performance_monitor, PerformanceMetrics
from ..utils.memory_manager import get_memory_manager, MemoryStats

logger = logging.getLogger(__name__)


class OptimizationLevel(Enum):
    """System optimization levels"""
    MAXIMUM_PERFORMANCE = auto()  # Use all resources
    BALANCED = auto()            # Balance performance và resource usage
    CONSERVATIVE = auto()        # Prioritize system stability
    BATTERY_SAVER = auto()       # Minimize resource usage


class ResourceType(Enum):
    """Types of system resources"""
    CPU = "cpu"
    MEMORY = "memory" 
    DISK_IO = "disk_io"
    NETWORK = "network"


@dataclass
class SystemCapabilities:
    """System hardware capabilities"""
    cpu_count: int
    cpu_frequency_mhz: float
    total_memory_gb: float
    available_memory_gb: float
    disk_type: str  # "SSD", "HDD", "Unknown"
    disk_free_gb: float
    platform: str
    
    @classmethod
    def detect_current(cls) -> 'SystemCapabilities':
        """Detect current system capabilities"""
        try:
            cpu_info = psutil.cpu_freq()
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            
            # Try to detect disk type (simplified)
            disk_type = "Unknown"
            try:
                # This is a simple heuristic - in practice you'd use more sophisticated detection
                disk_stats = psutil.disk_io_counters()
                if disk_stats and disk_stats.read_time > 0:
                    avg_read_time = disk_stats.read_time / max(1, disk_stats.read_count)
                    disk_type = "SSD" if avg_read_time < 10 else "HDD"
            except:
                pass
            
            return cls(
                cpu_count=psutil.cpu_count(),
                cpu_frequency_mhz=cpu_info.current if cpu_info else 0,
                total_memory_gb=memory_info.total / (1024**3),
                available_memory_gb=memory_info.available / (1024**3),
                disk_type=disk_type,
                disk_free_gb=disk_info.free / (1024**3),
                platform=psutil.os.name
            )
            
        except Exception as e:
            logger.error(f"Error detecting system capabilities: {e}")
            return cls(1, 0, 4, 2, "Unknown", 10, "unknown")


@dataclass
class OptimizationConfig:
    """Configuration for different optimization levels"""
    max_concurrent_tasks: int
    chunk_size: int
    memory_threshold_mb: float
    enable_caching: bool
    cache_size: int
    gc_frequency: int
    io_thread_count: int
    preview_batch_size: int
    enable_parallel_processing: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationConfig':
        return cls(**data)


@dataclass
class ResourceMetrics:
    """Current resource usage metrics"""
    cpu_usage_percent: float
    memory_usage_percent: float
    disk_io_read_mb_per_sec: float
    disk_io_write_mb_per_sec: float
    available_memory_gb: float
    load_average: Optional[float]  # Unix systems only
    timestamp: float
    
    @classmethod
    def get_current(cls) -> 'ResourceMetrics':
        """Get current resource metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory_info = psutil.virtual_memory()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            disk_read_mb = 0.0
            disk_write_mb = 0.0
            
            if disk_io:
                # This is instantaneous, real rate would need tracking over time
                disk_read_mb = disk_io.read_bytes / (1024 * 1024)
                disk_write_mb = disk_io.write_bytes / (1024 * 1024)
            
            # Load average (Unix only)
            load_avg = None
            try:
                load_avg = psutil.getloadavg()[0]  # 1-minute load average
            except (AttributeError, OSError):
                pass  # Not available on Windows
            
            return cls(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory_info.percent,
                disk_io_read_mb_per_sec=disk_read_mb,
                disk_io_write_mb_per_sec=disk_write_mb,
                available_memory_gb=memory_info.available / (1024**3),
                load_average=load_avg,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Error getting resource metrics: {e}")
            return cls(0, 0, 0, 0, 0, None, time.time())


class OptimizationProfile:
    """Optimization profile for different system configurations"""
    
    @staticmethod
    def create_for_capabilities(
        capabilities: SystemCapabilities,
        optimization_level: OptimizationLevel
    ) -> OptimizationConfig:
        """Create optimization config based on system capabilities"""
        
        # Base configuration
        base_config = {
            'max_concurrent_tasks': 4,
            'chunk_size': 1000,
            'memory_threshold_mb': 512,
            'enable_caching': True,
            'cache_size': 10000,
            'gc_frequency': 100,
            'io_thread_count': 2,
            'preview_batch_size': 100,
            'enable_parallel_processing': True
        }
        
        # Adjust based on CPU count
        cpu_multiplier = min(capabilities.cpu_count, 16) / 4.0
        base_config['max_concurrent_tasks'] = max(1, int(4 * cpu_multiplier))
        base_config['io_thread_count'] = max(1, int(2 * cpu_multiplier))
        
        # Adjust based on memory
        memory_multiplier = capabilities.available_memory_gb / 4.0
        if memory_multiplier > 2.0:
            base_config['memory_threshold_mb'] = 1024
            base_config['cache_size'] = 20000
            base_config['chunk_size'] = 2000
        elif memory_multiplier < 1.0:
            base_config['memory_threshold_mb'] = 256
            base_config['cache_size'] = 5000
            base_config['chunk_size'] = 500
        
        # Adjust based on disk type
        if capabilities.disk_type == "SSD":
            base_config['chunk_size'] = int(base_config['chunk_size'] * 1.5)
            base_config['preview_batch_size'] = int(base_config['preview_batch_size'] * 1.5)
        elif capabilities.disk_type == "HDD":
            base_config['chunk_size'] = int(base_config['chunk_size'] * 0.7)
            base_config['io_thread_count'] = max(1, base_config['io_thread_count'] // 2)
        
        # Apply optimization level adjustments
        if optimization_level == OptimizationLevel.MAXIMUM_PERFORMANCE:
            base_config['max_concurrent_tasks'] = int(base_config['max_concurrent_tasks'] * 1.5)
            base_config['memory_threshold_mb'] = int(base_config['memory_threshold_mb'] * 1.5)
            base_config['enable_parallel_processing'] = True
            
        elif optimization_level == OptimizationLevel.CONSERVATIVE:
            base_config['max_concurrent_tasks'] = max(1, base_config['max_concurrent_tasks'] // 2)
            base_config['memory_threshold_mb'] = int(base_config['memory_threshold_mb'] * 0.7)
            base_config['chunk_size'] = int(base_config['chunk_size'] * 0.8)
            
        elif optimization_level == OptimizationLevel.BATTERY_SAVER:
            base_config['max_concurrent_tasks'] = min(2, base_config['max_concurrent_tasks'] // 3)
            base_config['memory_threshold_mb'] = int(base_config['memory_threshold_mb'] * 0.5)
            base_config['enable_caching'] = False
            base_config['enable_parallel_processing'] = False
            base_config['gc_frequency'] = 50  # More frequent GC
        
        return OptimizationConfig(**base_config)


class AdaptiveOptimizer:
    """
    Adaptive optimizer that adjusts performance based on system conditions
    """
    
    def __init__(
        self,
        check_interval: float = 10.0,  # Check every 10 seconds
        adaptation_threshold: float = 0.2  # 20% change threshold
    ):
        self.check_interval = check_interval
        self.adaptation_threshold = adaptation_threshold
        
        self.capabilities = SystemCapabilities.detect_current()
        self.current_level = OptimizationLevel.BALANCED
        self.current_config = OptimizationProfile.create_for_capabilities(
            self.capabilities, self.current_level
        )
        
        # Monitoring
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Adaptation callbacks
        self._adaptation_callbacks: List[Callable[[OptimizationConfig], None]] = []
        
        # Historical data
        self._metrics_history: List[ResourceMetrics] = []
        self._max_history = 100
        
        logger.info(f"AdaptiveOptimizer initialized - {self.capabilities.cpu_count} CPUs, "
                   f"{self.capabilities.available_memory_gb:.1f}GB RAM, {self.capabilities.disk_type}")
    
    def add_adaptation_callback(self, callback: Callable[[OptimizationConfig], None]):
        """Add callback to be called when configuration changes"""
        self._adaptation_callbacks.append(callback)
    
    def start_monitoring(self):
        """Start adaptive monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        def monitor_loop():
            logger.info("Adaptive optimization monitoring started")
            
            while not self._stop_event.is_set():
                try:
                    # Collect current metrics
                    metrics = ResourceMetrics.get_current()
                    self._metrics_history.append(metrics)
                    
                    # Trim history
                    if len(self._metrics_history) > self._max_history:
                        self._metrics_history.pop(0)
                    
                    # Check if adaptation is needed
                    if len(self._metrics_history) >= 5:  # Need some history
                        new_level = self._determine_optimal_level()
                        if new_level != self.current_level:
                            self._adapt_to_level(new_level)
                    
                    # Wait for next check
                    if self._stop_event.wait(self.check_interval):
                        break
                        
                except Exception as e:
                    logger.error(f"Error in adaptive monitoring: {e}")
                    time.sleep(self.check_interval)
            
            logger.info("Adaptive optimization monitoring stopped")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop adaptive monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)
    
    def _determine_optimal_level(self) -> OptimizationLevel:
        """Determine optimal optimization level based on current conditions"""
        recent_metrics = self._metrics_history[-5:]  # Last 5 measurements
        
        # Calculate average resource usage
        avg_cpu = sum(m.cpu_usage_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_usage_percent for m in recent_metrics) / len(recent_metrics)
        min_available_memory = min(m.available_memory_gb for m in recent_metrics)
        
        # Decision logic
        if avg_cpu < 30 and avg_memory < 60 and min_available_memory > 2.0:
            # System has plenty of resources
            return OptimizationLevel.MAXIMUM_PERFORMANCE
        elif avg_cpu > 80 or avg_memory > 85 or min_available_memory < 1.0:
            # System is under stress
            return OptimizationLevel.CONSERVATIVE
        elif avg_cpu > 60 or avg_memory > 75:
            # Moderate system load
            return OptimizationLevel.BALANCED
        else:
            # Normal conditions
            return OptimizationLevel.BALANCED
    
    def _adapt_to_level(self, new_level: OptimizationLevel):
        """Adapt to new optimization level"""
        logger.info(f"Adapting optimization level: {self.current_level.name} -> {new_level.name}")
        
        self.current_level = new_level
        self.current_config = OptimizationProfile.create_for_capabilities(
            self.capabilities, new_level
        )
        
        # Notify callbacks
        for callback in self._adaptation_callbacks:
            try:
                callback(self.current_config)
            except Exception as e:
                logger.error(f"Error in adaptation callback: {e}")
    
    def force_adaptation(self, level: OptimizationLevel):
        """Force adaptation to specific level"""
        self._adapt_to_level(level)
    
    def get_current_config(self) -> OptimizationConfig:
        """Get current optimization configuration"""
        return self.current_config
    
    def get_current_metrics(self) -> ResourceMetrics:
        """Get current resource metrics"""
        return ResourceMetrics.get_current()
    
    def get_metrics_history(self) -> List[ResourceMetrics]:
        """Get historical metrics"""
        return self._metrics_history.copy()
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        current_metrics = self.get_current_metrics()
        
        report = {
            'system_capabilities': asdict(self.capabilities),
            'current_optimization_level': self.current_level.name,
            'current_config': self.current_config.to_dict(),
            'current_metrics': asdict(current_metrics),
            'monitoring_active': self._monitoring,
            'metrics_history_size': len(self._metrics_history)
        }
        
        # Add performance analysis
        if len(self._metrics_history) >= 2:
            recent = self._metrics_history[-10:]
            report['performance_analysis'] = {
                'avg_cpu_usage': sum(m.cpu_usage_percent for m in recent) / len(recent),
                'avg_memory_usage': sum(m.memory_usage_percent for m in recent) / len(recent),
                'min_available_memory_gb': min(m.available_memory_gb for m in recent),
                'resource_trend': self._analyze_trend(recent)
            }
        
        return report
    
    def _analyze_trend(self, metrics: List[ResourceMetrics]) -> str:
        """Analyze resource usage trend"""
        if len(metrics) < 5:
            return "insufficient_data"
        
        # Simple trend analysis
        early_cpu = sum(m.cpu_usage_percent for m in metrics[:len(metrics)//2]) / (len(metrics)//2)
        late_cpu = sum(m.cpu_usage_percent for m in metrics[len(metrics)//2:]) / (len(metrics)//2)
        
        early_memory = sum(m.memory_usage_percent for m in metrics[:len(metrics)//2]) / (len(metrics)//2)
        late_memory = sum(m.memory_usage_percent for m in metrics[len(metrics)//2:]) / (len(metrics)//2)
        
        cpu_trend = late_cpu - early_cpu
        memory_trend = late_memory - early_memory
        
        if cpu_trend > 10 or memory_trend > 10:
            return "increasing_load"
        elif cpu_trend < -10 or memory_trend < -10:
            return "decreasing_load"
        else:
            return "stable"


class ResourceOptimizationService:
    """
    Main service for resource optimization và adaptive performance scaling
    """
    
    def __init__(self):
        self.performance_monitor = get_performance_monitor()
        self.memory_manager = get_memory_manager()
        self.adaptive_optimizer = AdaptiveOptimizer()
        
        # Thread pool for background optimization tasks
        self._thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ResourceOpt")
        
        # Service state
        self._started = False
        
        # Setup callbacks
        self.adaptive_optimizer.add_adaptation_callback(self._on_configuration_changed)
        
        logger.info("ResourceOptimizationService initialized")
    
    def start(self):
        """Start the resource optimization service"""
        if self._started:
            return
        
        self._started = True
        
        # Start monitoring systems
        self.performance_monitor.start_continuous_monitoring()
        self.memory_manager.start_monitoring()
        self.adaptive_optimizer.start_monitoring()
        
        logger.info("Resource optimization service started")
    
    def stop(self):
        """Stop the resource optimization service"""
        if not self._started:
            return
        
        self._started = False
        
        # Stop monitoring systems
        self.performance_monitor.stop_continuous_monitoring()
        self.memory_manager.stop_monitoring()
        self.adaptive_optimizer.stop_monitoring()
        
        # Shutdown thread pool
        self._thread_pool.shutdown(wait=False)
        
        logger.info("Resource optimization service stopped")
    
    def _on_configuration_changed(self, new_config: OptimizationConfig):
        """Handle configuration changes"""
        logger.info(f"Applying new optimization configuration: "
                   f"max_tasks={new_config.max_concurrent_tasks}, "
                   f"chunk_size={new_config.chunk_size}, "
                   f"memory_threshold={new_config.memory_threshold_mb}MB")
        
        # Here you would apply the configuration to relevant services
        # This is where the optimization config would be used by:
        # - FileStreamingService
        # - ParallelPreviewService
        # - MemoryManager
        # - AsyncTaskQueue
        # etc.
    
    def get_current_config(self) -> OptimizationConfig:
        """Get current optimization configuration"""
        return self.adaptive_optimizer.get_current_config()
    
    def force_optimization_level(self, level: OptimizationLevel):
        """Force specific optimization level"""
        self.adaptive_optimizer.force_adaptation(level)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        optimization_report = self.adaptive_optimizer.get_optimization_report()
        performance_stats = self.performance_monitor.get_performance_summary()
        memory_report = self.memory_manager.get_memory_report()
        
        return {
            'optimization': optimization_report,
            'performance': performance_stats,
            'memory': memory_report,
            'service_status': {
                'started': self._started,
                'monitoring_active': (
                    self.adaptive_optimizer._monitoring and
                    self.memory_manager.monitor._monitoring
                )
            }
        }
    
    def export_performance_data(self, format: str = 'json') -> str:
        """Export performance data for analysis"""
        report = self.get_performance_report()
        
        if format == 'json':
            return json.dumps(report, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def optimize_for_large_operation(self) -> Dict[str, Any]:
        """Temporarily optimize for large operation"""
        logger.info("Optimizing for large operation")
        
        # Force maximum performance temporarily
        original_level = self.adaptive_optimizer.current_level
        self.adaptive_optimizer.force_adaptation(OptimizationLevel.MAXIMUM_PERFORMANCE)
        
        # Trigger garbage collection
        self.memory_manager.trigger_gc(force=True)
        
        # Return restoration function
        def restore():
            self.adaptive_optimizer.force_adaptation(original_level)
            logger.info("Restored original optimization level")
        
        return {
            'restore_function': restore,
            'optimized_config': self.get_current_config().to_dict()
        }
    
    def is_system_under_stress(self) -> bool:
        """Check if system is currently under stress"""
        metrics = self.adaptive_optimizer.get_current_metrics()
        
        return (
            metrics.cpu_usage_percent > 80 or
            metrics.memory_usage_percent > 85 or
            metrics.available_memory_gb < 1.0
        )
    
    def get_recommended_chunk_size(self, total_items: int) -> int:
        """Get recommended chunk size for processing"""
        config = self.get_current_config()
        base_chunk = config.chunk_size
        
        # Adjust based on total items
        if total_items > 50000:
            return min(base_chunk * 2, 5000)  # Larger chunks for very large datasets
        elif total_items < 1000:
            return max(base_chunk // 2, 100)  # Smaller chunks for small datasets
        
        return base_chunk
    
    def shutdown(self):
        """Shutdown the service và cleanup resources"""
        self.stop()
        logger.info("Resource optimization service shutdown complete")


# Global instance
_resource_optimization_service: Optional[ResourceOptimizationService] = None


def get_resource_optimization_service() -> ResourceOptimizationService:
    """Get global ResourceOptimizationService instance"""
    global _resource_optimization_service
    if _resource_optimization_service is None:
        _resource_optimization_service = ResourceOptimizationService()
    return _resource_optimization_service


def set_resource_optimization_service(service: ResourceOptimizationService):
    """Set global ResourceOptimizationService instance"""
    global _resource_optimization_service
    if _resource_optimization_service is not None:
        _resource_optimization_service.shutdown()
    _resource_optimization_service = service