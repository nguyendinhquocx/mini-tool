"""
Memory Management Utilities

Provides memory-efficient data structures, garbage collection management,
và memory monitoring for large file operations.
"""

import gc
import sys
import psutil
import threading
import time
from typing import Iterator, List, Dict, Any, Optional, TypeVar, Generic, Callable
from dataclasses import dataclass
from collections import deque
from contextlib import contextmanager
import logging
import weakref

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class MemoryThresholds:
    """Memory usage thresholds for different operations"""
    warning_threshold_mb: float = 512.0  # Warn when approaching this limit
    critical_threshold_mb: float = 1024.0  # Take action when reaching this limit
    max_threshold_mb: float = 2048.0  # Hard limit - stop operations
    gc_trigger_threshold_mb: float = 256.0  # Trigger GC when exceeded
    
    def __post_init__(self):
        """Validate thresholds make sense"""
        if self.warning_threshold_mb >= self.critical_threshold_mb:
            raise ValueError("Warning threshold must be less than critical threshold")
        if self.critical_threshold_mb >= self.max_threshold_mb:
            raise ValueError("Critical threshold must be less than max threshold")


@dataclass
class MemoryStats:
    """Current memory statistics"""
    used_mb: float
    available_mb: float
    total_mb: float
    usage_percentage: float
    process_memory_mb: float
    
    @classmethod
    def get_current(cls) -> 'MemoryStats':
        """Get current system memory stats"""
        try:
            memory = psutil.virtual_memory()
            process = psutil.Process()
            process_memory = process.memory_info().rss / (1024 * 1024)
            
            return cls(
                used_mb=memory.used / (1024 * 1024),
                available_mb=memory.available / (1024 * 1024),
                total_mb=memory.total / (1024 * 1024),
                usage_percentage=memory.percent,
                process_memory_mb=process_memory
            )
        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return cls(0, 0, 0, 0, 0)


class MemoryAwareGenerator(Generic[T]):
    """
    Generator wrapper that monitors memory usage và triggers GC
    """
    
    def __init__(
        self,
        source_iterator: Iterator[T],
        memory_manager: 'MemoryManager',
        gc_frequency: int = 100  # Trigger GC every N items
    ):
        self.source_iterator = source_iterator
        self.memory_manager = memory_manager
        self.gc_frequency = gc_frequency
        self.item_count = 0
    
    def __iter__(self) -> Iterator[T]:
        return self
    
    def __next__(self) -> T:
        try:
            item = next(self.source_iterator)
            self.item_count += 1
            
            # Check memory và trigger GC if needed
            if self.item_count % self.gc_frequency == 0:
                current_memory = MemoryStats.get_current()
                
                if current_memory.process_memory_mb > self.memory_manager.thresholds.gc_trigger_threshold_mb:
                    self.memory_manager.trigger_gc()
                
                # Check for memory violations
                self.memory_manager.check_memory_violations(current_memory)
            
            return item
            
        except StopIteration:
            # Final cleanup
            self.memory_manager.trigger_gc()
            raise


class ChunkedProcessor(Generic[T]):
    """
    Process data in memory-efficient chunks
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        memory_manager: Optional['MemoryManager'] = None
    ):
        self.chunk_size = chunk_size
        self.memory_manager = memory_manager or MemoryManager()
    
    def process_in_chunks(
        self,
        data_source: Iterator[T],
        processor: Callable[[List[T]], Any]
    ) -> Iterator[Any]:
        """
        Process data in chunks với memory monitoring
        
        Args:
            data_source: Source of data items
            processor: Function to process each chunk
            
        Yields:
            Results from processing each chunk
        """
        chunk = []
        
        try:
            for item in data_source:
                chunk.append(item)
                
                if len(chunk) >= self.chunk_size:
                    # Process chunk
                    result = processor(chunk)
                    yield result
                    
                    # Clear chunk và check memory
                    chunk.clear()
                    self._check_memory_and_gc()
            
            # Process remaining items
            if chunk:
                result = processor(chunk)
                yield result
                
        finally:
            # Cleanup
            chunk.clear()
            self.memory_manager.trigger_gc()
    
    def _check_memory_and_gc(self):
        """Check memory usage và trigger GC if needed"""
        current_memory = MemoryStats.get_current()
        
        if current_memory.process_memory_mb > self.memory_manager.thresholds.gc_trigger_threshold_mb:
            self.memory_manager.trigger_gc()
        
        self.memory_manager.check_memory_violations(current_memory)


class MemoryEfficientCache(Generic[T]):
    """
    Memory-efficient cache với automatic cleanup
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        memory_limit_mb: float = 100.0,
        cleanup_ratio: float = 0.2  # Remove 20% of items when cleaning
    ):
        self.max_size = max_size
        self.memory_limit_mb = memory_limit_mb
        self.cleanup_ratio = cleanup_ratio
        
        self._cache: Dict[str, T] = {}
        self._access_times: Dict[str, float] = {}
        self._size_estimates: Dict[str, int] = {}
        self._lock = threading.RLock()
        self._total_estimated_size = 0
    
    def get(self, key: str) -> Optional[T]:
        """Get item from cache"""
        with self._lock:
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]
        return None
    
    def put(self, key: str, value: T) -> bool:
        """
        Put item in cache
        
        Returns:
            True if item was cached, False if rejected due to memory limits
        """
        with self._lock:
            # Estimate size
            size_estimate = sys.getsizeof(value)
            
            # Check if we need to clean up
            if (len(self._cache) >= self.max_size or
                self._total_estimated_size + size_estimate > self.memory_limit_mb * 1024 * 1024):
                if not self._cleanup():
                    return False  # Cleanup failed, reject item
            
            # Store item
            self._cache[key] = value
            self._access_times[key] = time.time()
            self._size_estimates[key] = size_estimate
            self._total_estimated_size += size_estimate
            
            return True
    
    def _cleanup(self) -> bool:
        """
        Cleanup old items from cache
        
        Returns:
            True if cleanup was successful
        """
        if not self._access_times:
            return True
        
        # Calculate how many items to remove
        remove_count = max(1, int(len(self._cache) * self.cleanup_ratio))
        
        # Sort by access time và remove oldest
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
        
        removed_size = 0
        for key, _ in sorted_keys[:remove_count]:
            if key in self._cache:
                removed_size += self._size_estimates.get(key, 0)
                del self._cache[key]
                del self._access_times[key]
                if key in self._size_estimates:
                    del self._size_estimates[key]
        
        self._total_estimated_size -= removed_size
        
        logger.debug(f"Cache cleanup: removed {remove_count} items, freed ~{removed_size} bytes")
        return True
    
    def clear(self):
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
            self._size_estimates.clear()
            self._total_estimated_size = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'item_count': len(self._cache),
                'max_size': self.max_size,
                'estimated_size_mb': self._total_estimated_size / (1024 * 1024),
                'memory_limit_mb': self.memory_limit_mb,
                'utilization': len(self._cache) / self.max_size if self.max_size > 0 else 0
            }


class MemoryMonitor:
    """
    Continuous memory monitoring with alerts
    """
    
    def __init__(
        self,
        thresholds: MemoryThresholds,
        check_interval: float = 1.0  # Check every second
    ):
        self.thresholds = thresholds
        self.check_interval = check_interval
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks: List[Callable[[MemoryStats], None]] = []
        self._violation_callbacks: List[Callable[[str, MemoryStats], None]] = []
    
    def add_callback(self, callback: Callable[[MemoryStats], None]):
        """Add callback for memory updates"""
        self._callbacks.append(callback)
    
    def add_violation_callback(self, callback: Callable[[str, MemoryStats], None]):
        """Add callback for memory violations"""
        self._violation_callbacks.append(callback)
    
    def start_monitoring(self):
        """Start continuous memory monitoring"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._stop_event.clear()
        
        def monitor_loop():
            logger.info("Memory monitoring started")
            
            while not self._stop_event.is_set():
                try:
                    stats = MemoryStats.get_current()
                    
                    # Notify callbacks
                    for callback in self._callbacks:
                        try:
                            callback(stats)
                        except Exception as e:
                            logger.error(f"Error in memory callback: {e}")
                    
                    # Check for violations
                    self._check_violations(stats)
                    
                    time.sleep(self.check_interval)
                    
                except Exception as e:
                    logger.error(f"Error in memory monitoring: {e}")
                    time.sleep(self.check_interval)
            
            logger.info("Memory monitoring stopped")
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        self._stop_event.set()
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
    
    def _check_violations(self, stats: MemoryStats):
        """Check for memory threshold violations"""
        if stats.process_memory_mb > self.thresholds.max_threshold_mb:
            self._notify_violation("CRITICAL: Max memory threshold exceeded", stats)
        elif stats.process_memory_mb > self.thresholds.critical_threshold_mb:
            self._notify_violation("CRITICAL: Critical memory threshold exceeded", stats)
        elif stats.process_memory_mb > self.thresholds.warning_threshold_mb:
            self._notify_violation("WARNING: Memory usage high", stats)
    
    def _notify_violation(self, message: str, stats: MemoryStats):
        """Notify violation callbacks"""
        for callback in self._violation_callbacks:
            try:
                callback(message, stats)
            except Exception as e:
                logger.error(f"Error in violation callback: {e}")


class MemoryManager:
    """
    Comprehensive memory management system
    """
    
    def __init__(self, thresholds: Optional[MemoryThresholds] = None):
        self.thresholds = thresholds or MemoryThresholds()
        self.monitor = MemoryMonitor(self.thresholds)
        self._gc_count = 0
        self._last_gc_time = 0
        self._min_gc_interval = 5.0  # Minimum 5 seconds between GC calls
        
        # Setup violation handling
        self.monitor.add_violation_callback(self._handle_memory_violation)
        
        logger.info(f"MemoryManager initialized với thresholds: {self.thresholds}")
    
    def create_memory_aware_generator(
        self,
        source_iterator: Iterator[T],
        gc_frequency: int = 100
    ) -> MemoryAwareGenerator[T]:
        """Create memory-aware generator wrapper"""
        return MemoryAwareGenerator(source_iterator, self, gc_frequency)
    
    def create_chunked_processor(self, chunk_size: int = 1000) -> ChunkedProcessor[T]:
        """Create chunked processor"""
        return ChunkedProcessor(chunk_size, self)
    
    def create_efficient_cache(
        self,
        max_size: int = 10000,
        memory_limit_mb: float = 100.0
    ) -> MemoryEfficientCache[T]:
        """Create memory-efficient cache"""
        return MemoryEfficientCache(max_size, memory_limit_mb)
    
    def trigger_gc(self, force: bool = False) -> int:
        """
        Trigger garbage collection
        
        Args:
            force: Force GC even if minimum interval hasn't passed
            
        Returns:
            Number of objects collected
        """
        current_time = time.time()
        
        # Respect minimum interval unless forced
        if not force and (current_time - self._last_gc_time) < self._min_gc_interval:
            return 0
        
        try:
            # Record pre-GC memory
            pre_gc_stats = MemoryStats.get_current()
            
            # Run garbage collection
            collected = gc.collect()
            self._gc_count += 1
            self._last_gc_time = current_time
            
            # Record post-GC memory
            post_gc_stats = MemoryStats.get_current()
            freed_mb = pre_gc_stats.process_memory_mb - post_gc_stats.process_memory_mb
            
            if freed_mb > 0:
                logger.debug(f"GC collected {collected} objects, freed ~{freed_mb:.1f}MB")
            
            return collected
            
        except Exception as e:
            logger.error(f"Error during garbage collection: {e}")
            return 0
    
    def check_memory_violations(self, stats: Optional[MemoryStats] = None):
        """Check for memory violations và take action"""
        if stats is None:
            stats = MemoryStats.get_current()
        
        self.monitor._check_violations(stats)
    
    def _handle_memory_violation(self, message: str, stats: MemoryStats):
        """Handle memory threshold violations"""
        logger.warning(f"Memory violation: {message} (Process: {stats.process_memory_mb:.1f}MB)")
        
        # Take action based on severity
        if stats.process_memory_mb > self.thresholds.critical_threshold_mb:
            logger.warning("Triggering emergency garbage collection")
            self.trigger_gc(force=True)
            
            # Additional cleanup actions could go here
            # (e.g., clearing caches, reducing chunk sizes, etc.)
    
    @contextmanager
    def memory_tracking(self, operation_name: str = "operation"):
        """Context manager for tracking memory usage during operations"""
        start_stats = MemoryStats.get_current()
        start_time = time.time()
        
        logger.debug(f"Starting {operation_name} - Memory: {start_stats.process_memory_mb:.1f}MB")
        
        try:
            yield start_stats
        finally:
            end_stats = MemoryStats.get_current()
            duration = time.time() - start_time
            memory_change = end_stats.process_memory_mb - start_stats.process_memory_mb
            
            if memory_change > 0:
                logger.debug(
                    f"Completed {operation_name} in {duration:.2f}s - "
                    f"Memory increased by {memory_change:.1f}MB"
                )
            else:
                logger.debug(
                    f"Completed {operation_name} in {duration:.2f}s - "
                    f"Memory decreased by {abs(memory_change):.1f}MB"
                )
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Get comprehensive memory report"""
        stats = MemoryStats.get_current()
        
        return {
            'current_memory_mb': stats.process_memory_mb,
            'system_memory_usage_percent': stats.usage_percentage,
            'available_memory_mb': stats.available_mb,
            'thresholds': {
                'warning_mb': self.thresholds.warning_threshold_mb,
                'critical_mb': self.thresholds.critical_threshold_mb,
                'max_mb': self.thresholds.max_threshold_mb
            },
            'gc_stats': {
                'gc_count': self._gc_count,
                'last_gc_time': self._last_gc_time,
                'gc_collections': gc.get_stats()
            }
        }
    
    def start_monitoring(self):
        """Start continuous memory monitoring"""
        self.monitor.start_monitoring()
    
    def stop_monitoring(self):
        """Stop memory monitoring"""
        self.monitor.stop_monitoring()
    
    def shutdown(self):
        """Shutdown memory manager và cleanup"""
        self.stop_monitoring()
        logger.info("Memory manager shutdown complete")


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Get global MemoryManager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager()
    return _memory_manager


def set_memory_manager(manager: MemoryManager):
    """Set global MemoryManager instance"""
    global _memory_manager
    if _memory_manager is not None:
        _memory_manager.shutdown()
    _memory_manager = manager