"""
File Streaming Service - Progressive File Loading System

Provides memory-efficient directory scanning và progressive file loading
for large directories với thousands of files.
"""

import asyncio
import os
import time
from typing import AsyncGenerator, List, Optional, Callable, Iterator
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from pathlib import Path

from ..models.file_info import FileInfo
from ..utils.performance_monitor import PerformanceMonitor, PerformanceMetrics

logger = logging.getLogger(__name__)


@dataclass
class StreamingConfig:
    """Configuration for file streaming operations"""
    chunk_size: int = 1000
    max_concurrent_scans: int = 4
    memory_threshold_mb: int = 512  # Stop streaming if memory usage exceeds this
    scan_timeout_seconds: int = 30
    enable_caching: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes


@dataclass
class LoadingProgress:
    """Progress information for file loading operations"""
    files_scanned: int = 0
    total_estimated: int = 0
    current_directory: str = ""
    scan_rate_files_per_second: float = 0.0
    memory_usage_mb: float = 0.0
    elapsed_time_seconds: float = 0.0
    is_complete: bool = False
    error_message: Optional[str] = None


class FileStreamingService:
    """
    Service for progressive file loading and streaming
    
    Optimized for large directories với memory-efficient chunked loading.
    """
    
    def __init__(self, config: Optional[StreamingConfig] = None):
        self.config = config or StreamingConfig()
        self.performance_monitor = PerformanceMonitor()
        self.cache = {}
        self.cache_timestamps = {}
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_scans)
        self._current_scan_tasks = set()
        self._shutdown = False
    
    async def scan_directory_chunked(
        self, 
        folder_path: str,
        chunk_callback: Optional[Callable[[List[FileInfo], LoadingProgress], None]] = None,
        file_filter: Optional[Callable[[str], bool]] = None
    ) -> AsyncGenerator[List[FileInfo], None]:
        """
        Stream directory contents in configurable chunks
        
        Args:
            folder_path: Directory to scan
            chunk_callback: Optional callback for progress updates
            file_filter: Optional filter function for files
            
        Yields:
            Lists of FileInfo objects in chunks
        """
        if not os.path.exists(folder_path):
            logger.error(f"Directory does not exist: {folder_path}")
            return
        
        # Check cache first
        cache_key = f"{folder_path}:{self.config.chunk_size}"
        if self._is_cache_valid(cache_key):
            logger.info(f"Using cached results for {folder_path}")
            cached_chunks = self.cache[cache_key]
            for chunk in cached_chunks:
                yield chunk
            return
        
        # Start performance tracking
        self.performance_monitor.start_operation_tracking()
        start_time = time.time()
        
        progress = LoadingProgress(current_directory=folder_path)
        
        try:
            # First pass: get directory size estimate
            total_estimate = await self._estimate_directory_size(folder_path)
            progress.total_estimated = total_estimate
            
            if chunk_callback:
                chunk_callback([], progress)
            
            # Stream files in chunks
            chunks_yielded = []
            
            async for chunk in self._stream_files_from_directory(
                folder_path, file_filter, progress, chunk_callback
            ):
                # Check memory usage
                metrics = self.performance_monitor.record_metrics(progress.files_scanned)
                progress.memory_usage_mb = metrics.memory_usage_mb
                progress.elapsed_time_seconds = time.time() - start_time
                progress.scan_rate_files_per_second = metrics.files_per_second
                
                # Memory threshold check
                if metrics.memory_usage_mb > self.config.memory_threshold_mb:
                    logger.warning(f"Memory threshold exceeded: {metrics.memory_usage_mb}MB")
                    # Force garbage collection and continue với smaller chunks
                    import gc
                    gc.collect()
                    self.config.chunk_size = max(100, self.config.chunk_size // 2)
                
                chunks_yielded.append(chunk)
                yield chunk
            
            # Cache results if enabled
            if self.config.enable_caching:
                self.cache[cache_key] = chunks_yielded
                self.cache_timestamps[cache_key] = time.time()
            
            progress.is_complete = True
            if chunk_callback:
                chunk_callback([], progress)
            
        except Exception as e:
            error_msg = f"Error scanning directory {folder_path}: {e}"
            logger.error(error_msg)
            progress.error_message = error_msg
            if chunk_callback:
                chunk_callback([], progress)
            raise
    
    async def _stream_files_from_directory(
        self,
        folder_path: str,
        file_filter: Optional[Callable[[str], bool]],
        progress: LoadingProgress,
        chunk_callback: Optional[Callable[[List[FileInfo], LoadingProgress], None]]
    ) -> AsyncGenerator[List[FileInfo], None]:
        """Internal method to stream files from directory"""
        
        chunk = []
        loop = asyncio.get_event_loop()
        
        try:
            # Use thread pool for I/O operations
            future = self._executor.submit(self._scan_directory_sync, folder_path, file_filter)
            
            # Wait for completion với timeout
            file_iterator = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: future.result()),
                timeout=self.config.scan_timeout_seconds
            )
            
            for file_info in file_iterator:
                if self._shutdown:
                    break
                
                chunk.append(file_info)
                progress.files_scanned += 1
                
                # Yield chunk when size reached
                if len(chunk) >= self.config.chunk_size:
                    if chunk_callback:
                        chunk_callback(chunk.copy(), progress)
                    yield chunk.copy()
                    chunk.clear()
                    
                    # Allow other coroutines to run
                    await asyncio.sleep(0.001)
            
            # Yield remaining files
            if chunk:
                if chunk_callback:
                    chunk_callback(chunk.copy(), progress)
                yield chunk
                
        except asyncio.TimeoutError:
            logger.error(f"Directory scan timeout for {folder_path}")
            raise
        except Exception as e:
            logger.error(f"Error streaming files: {e}")
            raise
    
    def _scan_directory_sync(
        self,
        folder_path: str,
        file_filter: Optional[Callable[[str], bool]]
    ) -> Iterator[FileInfo]:
        """Synchronous directory scanning (run in thread pool)"""
        
        try:
            for root, dirs, files in os.walk(folder_path):
                if self._shutdown:
                    break
                
                for filename in files:
                    if self._shutdown:
                        break
                    
                    file_path = os.path.join(root, filename)
                    
                    # Apply filter if provided
                    if file_filter and not file_filter(file_path):
                        continue
                    
                    try:
                        stat_result = os.stat(file_path)
                        file_info = FileInfo(
                            name=filename,
                            path=file_path,
                            size=stat_result.st_size,
                            modified=stat_result.st_mtime,
                            is_directory=False
                        )
                        yield file_info
                        
                    except (OSError, PermissionError) as e:
                        logger.debug(f"Skipping file {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error in directory scan: {e}")
            raise
    
    async def _estimate_directory_size(self, folder_path: str) -> int:
        """Estimate total number of files in directory"""
        
        try:
            # Quick sampling approach for estimation
            sample_dirs = []
            total_dirs = 0
            
            for root, dirs, files in os.walk(folder_path):
                total_dirs += 1
                if len(sample_dirs) < 10:  # Sample first 10 directories
                    sample_dirs.append(len(files))
                
                if total_dirs > 100:  # Don't spend too long on estimation
                    break
            
            if sample_dirs:
                avg_files_per_dir = sum(sample_dirs) / len(sample_dirs)
                estimate = int(avg_files_per_dir * total_dirs)
                return max(estimate, 100)  # Minimum estimate
            
            return 1000  # Default estimate
            
        except Exception as e:
            logger.debug(f"Error estimating directory size: {e}")
            return 1000
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid"""
        
        if not self.config.enable_caching:
            return False
        
        if cache_key not in self.cache:
            return False
        
        cache_time = self.cache_timestamps.get(cache_key, 0)
        age = time.time() - cache_time
        
        return age < self.config.cache_ttl_seconds
    
    def clear_cache(self):
        """Clear the file scanning cache"""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("File streaming cache cleared")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            "cached_directories": len(self.cache),
            "total_memory_mb": sum(
                len(str(chunks)) for chunks in self.cache.values()
            ) / (1024 * 1024),
            "oldest_cache_age_seconds": (
                time.time() - min(self.cache_timestamps.values())
                if self.cache_timestamps else 0
            )
        }
    
    async def get_file_count_fast(self, folder_path: str) -> int:
        """
        Get approximate file count quickly (for UI display)
        
        Args:
            folder_path: Directory to count
            
        Returns:
            Estimated file count
        """
        if not os.path.exists(folder_path):
            return 0
        
        try:
            # Quick count using sampling
            count = 0
            max_scan_time = 2.0  # Maximum 2 seconds for quick count
            start_time = time.time()
            
            for root, dirs, files in os.walk(folder_path):
                count += len(files)
                
                # Time limit check
                if time.time() - start_time > max_scan_time:
                    # Estimate based on what we've seen so far
                    dirs_scanned = 1
                    total_dirs = len(dirs) + 1
                    estimated_count = int(count * (total_dirs / dirs_scanned))
                    logger.debug(f"Quick count estimate: {estimated_count} files in {folder_path}")
                    return estimated_count
            
            logger.debug(f"Quick count exact: {count} files in {folder_path}")
            return count
            
        except Exception as e:
            logger.error(f"Error in quick file count: {e}")
            return 0
    
    def cancel_current_operations(self):
        """Cancel all current scanning operations"""
        self._shutdown = True
        logger.info("File streaming operations cancelled")
    
    def shutdown(self):
        """Shutdown the service và cleanup resources"""
        self._shutdown = True
        self._executor.shutdown(wait=False)
        self.clear_cache()
        logger.info("File streaming service shutdown complete")
    
    def get_performance_stats(self) -> dict:
        """Get current performance statistics"""
        return self.performance_monitor.get_performance_summary()


class FileStreamingFactory:
    """Factory for creating configured FileStreamingService instances"""
    
    @staticmethod
    def create_default() -> FileStreamingService:
        """Create service với default configuration"""
        return FileStreamingService()
    
    @staticmethod
    def create_for_large_directories() -> FileStreamingService:
        """Create service optimized for large directories"""
        config = StreamingConfig(
            chunk_size=500,  # Smaller chunks for better responsiveness
            max_concurrent_scans=2,  # Fewer concurrent operations
            memory_threshold_mb=256,  # Lower memory threshold
            scan_timeout_seconds=60,  # Longer timeout for large dirs
            enable_caching=True,
            cache_ttl_seconds=600  # Longer cache TTL
        )
        return FileStreamingService(config)
    
    @staticmethod
    def create_for_performance() -> FileStreamingService:
        """Create service optimized for maximum performance"""
        config = StreamingConfig(
            chunk_size=2000,  # Larger chunks
            max_concurrent_scans=8,  # More concurrent operations
            memory_threshold_mb=1024,  # Higher memory threshold
            scan_timeout_seconds=15,  # Shorter timeout
            enable_caching=True,
            cache_ttl_seconds=180  # Shorter cache TTL
        )
        return FileStreamingService(config)


# Global instance (lazy-loaded)
_streaming_service: Optional[FileStreamingService] = None


def get_streaming_service() -> FileStreamingService:
    """Get global FileStreamingService instance"""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = FileStreamingFactory.create_default()
    return _streaming_service


def set_streaming_service(service: FileStreamingService):
    """Set global FileStreamingService instance"""
    global _streaming_service
    if _streaming_service is not None:
        _streaming_service.shutdown()
    _streaming_service = service