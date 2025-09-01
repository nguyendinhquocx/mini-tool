"""
Parallel Preview Generation Service

Optimized preview generation using parallel processing, caching,
và estimated completion time calculation for large operations.
"""

import asyncio
import time
from typing import List, Optional, AsyncGenerator, Callable, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
import multiprocessing
import logging
from functools import lru_cache
import threading

from ..models.file_info import FileInfo, RenamePreview
from ..services.normalize_service import VietnameseNormalizer, NormalizationRules
from ..utils.performance_monitor import get_performance_monitor, PerformanceProfiler

logger = logging.getLogger(__name__)


@dataclass
class PreviewConfig:
    """Configuration for preview generation"""
    max_workers: Optional[int] = None  # Auto-detect based on CPU count
    chunk_size: int = 100
    enable_caching: bool = True
    cache_size: int = 10000
    use_process_pool: bool = False  # Use thread pool by default
    enable_estimated_time: bool = True
    progress_update_interval: float = 0.1  # 100ms


@dataclass
class PreviewProgress:
    """Progress tracking for preview generation"""
    total_files: int = 0
    completed_files: int = 0
    progress_percentage: float = 0.0
    estimated_completion_seconds: Optional[float] = None
    current_rate_files_per_second: float = 0.0
    start_time: float = field(default_factory=time.time)
    
    @property
    def elapsed_time_seconds(self) -> float:
        return time.time() - self.start_time


@dataclass
class PreviewBatch:
    """Batch of files for preview generation"""
    files: List[FileInfo]
    rules: NormalizationRules
    batch_id: int
    priority: int = 0


class PreviewCache:
    """Thread-safe cache for preview results"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._cache: Dict[str, RenamePreview] = {}
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def _generate_key(self, file_info: FileInfo, rules: NormalizationRules) -> str:
        """Generate cache key for file and rules"""
        rules_hash = hash((
            rules.remove_diacritics,
            rules.lowercase_conversion,
            rules.clean_special_chars,
            rules.normalize_whitespace,
            str(rules.custom_replacements) if rules.custom_replacements else ""
        ))
        return f"{file_info.path}:{file_info.modified}:{rules_hash}"
    
    def get(self, file_info: FileInfo, rules: NormalizationRules) -> Optional[RenamePreview]:
        """Get cached preview if available"""
        key = self._generate_key(file_info, rules)
        
        with self._lock:
            if key in self._cache:
                self._access_times[key] = time.time()
                return self._cache[key]
        
        return None
    
    def put(self, file_info: FileInfo, rules: NormalizationRules, preview: RenamePreview):
        """Store preview in cache"""
        key = self._generate_key(file_info, rules)
        current_time = time.time()
        
        with self._lock:
            # Check if cache is full
            if len(self._cache) >= self.max_size:
                self._evict_oldest()
            
            self._cache[key] = preview
            self._access_times[key] = current_time
    
    def _evict_oldest(self):
        """Evict oldest entries from cache"""
        if not self._access_times:
            return
        
        # Remove 10% of oldest entries
        remove_count = max(1, len(self._access_times) // 10)
        
        # Sort by access time and remove oldest
        sorted_keys = sorted(self._access_times.items(), key=lambda x: x[1])
        
        for key, _ in sorted_keys[:remove_count]:
            del self._cache[key]
            del self._access_times[key]
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
            self._access_times.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_ratio': getattr(self, '_hit_count', 0) / max(1, getattr(self, '_total_requests', 1))
            }


def generate_preview_batch_worker(batch_data: tuple) -> List[RenamePreview]:
    """
    Worker function for generating preview batch (for ProcessPoolExecutor)
    
    Args:
        batch_data: Tuple of (files, rules_dict, batch_id)
        
    Returns:
        List of generated previews
    """
    files, rules_dict, batch_id = batch_data
    
    try:
        # Reconstruct NormalizationRules from dict
        rules = NormalizationRules(**rules_dict)
        
        # Create normalizer
        normalizer = VietnameseNormalizer(rules)
        
        previews = []
        for file_info in files:
            try:
                normalized_name = normalizer.normalize_filename(file_info.name)
                
                preview = RenamePreview(
                    original_name=file_info.name,
                    new_name=normalized_name,
                    file_path=file_info.path,
                    file_size=file_info.size,
                    has_conflict=False,  # Will be checked later
                    status=None
                )
                
                previews.append(preview)
                
            except Exception as e:
                logger.debug(f"Error generating preview for {file_info.name}: {e}")
                continue
        
        return previews
        
    except Exception as e:
        logger.error(f"Error in batch worker {batch_id}: {e}")
        return []


class ParallelPreviewService:
    """
    Service for generating file previews using parallel processing
    """
    
    def __init__(self, config: Optional[PreviewConfig] = None):
        self.config = config or PreviewConfig()
        self.performance_monitor = get_performance_monitor()
        
        # Setup worker configuration
        if self.config.max_workers is None:
            self.config.max_workers = min(multiprocessing.cpu_count(), 8)
        
        # Initialize cache
        self.cache = PreviewCache(self.config.cache_size) if self.config.enable_caching else None
        
        # Executor pools
        self._thread_executor: Optional[ThreadPoolExecutor] = None
        self._process_executor: Optional[ProcessPoolExecutor] = None
        
        # Progress tracking
        self._current_progress: Optional[PreviewProgress] = None
        self._progress_lock = threading.Lock()
        
        logger.info(f"ParallelPreviewService initialized với {self.config.max_workers} workers")
    
    def _get_executor(self):
        """Get appropriate executor pool"""
        if self.config.use_process_pool:
            if self._process_executor is None:
                self._process_executor = ProcessPoolExecutor(
                    max_workers=self.config.max_workers
                )
            return self._process_executor
        else:
            if self._thread_executor is None:
                self._thread_executor = ThreadPoolExecutor(
                    max_workers=self.config.max_workers
                )
            return self._thread_executor
    
    async def generate_previews_parallel(
        self,
        files: List[FileInfo],
        rules: NormalizationRules,
        progress_callback: Optional[Callable[[PreviewProgress], None]] = None
    ) -> AsyncGenerator[List[RenamePreview], None]:
        """
        Generate previews using parallel processing
        
        Args:
            files: List of files to process
            rules: Normalization rules to apply
            progress_callback: Optional callback for progress updates
            
        Yields:
            Batches of generated previews
        """
        if not files:
            return
        
        with PerformanceProfiler(self.performance_monitor, f"Generate {len(files)} previews"):
            # Initialize progress tracking
            progress = PreviewProgress(total_files=len(files))
            self._current_progress = progress
            
            try:
                # Split files into batches
                batches = self._create_batches(files, rules)
                
                # Process batches in parallel
                executor = self._get_executor()
                loop = asyncio.get_event_loop()
                
                # Submit all batches
                futures = []
                for batch in batches:
                    if self.config.use_process_pool:
                        # For ProcessPoolExecutor, we need to serialize data
                        batch_data = (
                            batch.files,
                            batch.rules.to_dict(),
                            batch.batch_id
                        )
                        future = loop.run_in_executor(
                            executor,
                            generate_preview_batch_worker,
                            batch_data
                        )
                    else:
                        # For ThreadPoolExecutor, we can pass objects directly
                        future = loop.run_in_executor(
                            executor,
                            self._generate_batch_thread_worker,
                            batch
                        )
                    
                    futures.append((batch.batch_id, future))
                
                # Collect results as they complete
                for batch_id, future in futures:
                    try:
                        batch_previews = await future
                        
                        # Update progress
                        with self._progress_lock:
                            progress.completed_files += len(batch_previews)
                            progress.progress_percentage = (
                                progress.completed_files / progress.total_files * 100
                            )
                            
                            # Calculate rate và estimated completion time
                            elapsed = progress.elapsed_time_seconds
                            if elapsed > 0:
                                progress.current_rate_files_per_second = (
                                    progress.completed_files / elapsed
                                )
                                
                                if self.config.enable_estimated_time and progress.current_rate_files_per_second > 0:
                                    remaining_files = progress.total_files - progress.completed_files
                                    progress.estimated_completion_seconds = (
                                        remaining_files / progress.current_rate_files_per_second
                                    )
                        
                        # Notify progress
                        if progress_callback:
                            progress_callback(progress)
                        
                        # Yield batch results
                        if batch_previews:
                            yield batch_previews
                        
                        # Allow other coroutines to run
                        await asyncio.sleep(0.001)
                        
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_id}: {e}")
                        continue
                
                # Final progress update
                progress.progress_percentage = 100.0
                if progress_callback:
                    progress_callback(progress)
                
            except Exception as e:
                logger.error(f"Error in parallel preview generation: {e}")
                raise
            finally:
                self._current_progress = None
    
    def _create_batches(self, files: List[FileInfo], rules: NormalizationRules) -> List[PreviewBatch]:
        """Create processing batches from files"""
        batches = []
        batch_id = 0
        
        for i in range(0, len(files), self.config.chunk_size):
            batch_files = files[i:i + self.config.chunk_size]
            batch = PreviewBatch(
                files=batch_files,
                rules=rules,
                batch_id=batch_id
            )
            batches.append(batch)
            batch_id += 1
        
        logger.debug(f"Created {len(batches)} batches cho {len(files)} files")
        return batches
    
    def _generate_batch_thread_worker(self, batch: PreviewBatch) -> List[RenamePreview]:
        """Thread worker for generating preview batch"""
        try:
            normalizer = VietnameseNormalizer(batch.rules)
            previews = []
            
            for file_info in batch.files:
                try:
                    # Check cache first
                    if self.cache:
                        cached_preview = self.cache.get(file_info, batch.rules)
                        if cached_preview:
                            previews.append(cached_preview)
                            continue
                    
                    # Generate new preview
                    normalized_name = normalizer.normalize_filename(file_info.name)
                    
                    preview = RenamePreview(
                        original_name=file_info.name,
                        new_name=normalized_name,
                        file_path=file_info.path,
                        file_size=file_info.size,
                        has_conflict=False,
                        status=None
                    )
                    
                    previews.append(preview)
                    
                    # Cache the result
                    if self.cache:
                        self.cache.put(file_info, batch.rules, preview)
                    
                except Exception as e:
                    logger.debug(f"Error generating preview for {file_info.name}: {e}")
                    continue
            
            return previews
            
        except Exception as e:
            logger.error(f"Error in thread worker for batch {batch.batch_id}: {e}")
            return []
    
    def generate_single_preview(
        self,
        file_info: FileInfo,
        rules: NormalizationRules
    ) -> Optional[RenamePreview]:
        """
        Generate single preview synchronously (for quick operations)
        
        Args:
            file_info: File to process
            rules: Normalization rules
            
        Returns:
            Generated preview or None if error
        """
        try:
            # Check cache first
            if self.cache:
                cached_preview = self.cache.get(file_info, rules)
                if cached_preview:
                    return cached_preview
            
            # Generate preview
            normalizer = VietnameseNormalizer(rules)
            normalized_name = normalizer.normalize_filename(file_info.name)
            
            preview = RenamePreview(
                original_name=file_info.name,
                new_name=normalized_name,
                file_path=file_info.path,
                file_size=file_info.size,
                has_conflict=False,
                status=None
            )
            
            # Cache result
            if self.cache:
                self.cache.put(file_info, rules, preview)
            
            return preview
            
        except Exception as e:
            logger.error(f"Error generating single preview for {file_info.name}: {e}")
            return None
    
    def estimate_completion_time(
        self,
        total_files: int,
        sample_size: int = 10
    ) -> Optional[float]:
        """
        Estimate completion time by processing a sample
        
        Args:
            total_files: Total number of files to process
            sample_size: Number of files to use for estimation
            
        Returns:
            Estimated completion time in seconds, or None if cannot estimate
        """
        if not self.config.enable_estimated_time:
            return None
        
        try:
            # Use current progress if available
            if self._current_progress and self._current_progress.current_rate_files_per_second > 0:
                return total_files / self._current_progress.current_rate_files_per_second
            
            # Use historical performance data
            stats = self.performance_monitor.get_performance_summary()
            if stats.get('avg_files_per_second', 0) > 0:
                return total_files / stats['avg_files_per_second']
            
            # Default estimate based on CPU count
            estimated_rate = self.config.max_workers * 20  # 20 files/sec per worker
            return total_files / estimated_rate
            
        except Exception as e:
            logger.debug(f"Error estimating completion time: {e}")
            return None
    
    def get_current_progress(self) -> Optional[PreviewProgress]:
        """Get current operation progress"""
        with self._progress_lock:
            return self._current_progress
    
    def clear_cache(self):
        """Clear preview cache"""
        if self.cache:
            self.cache.clear()
            logger.info("Preview cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        base_stats = self.performance_monitor.get_performance_summary()
        
        # Add service-specific stats
        service_stats = {
            'max_workers': self.config.max_workers,
            'chunk_size': self.config.chunk_size,
            'use_process_pool': self.config.use_process_pool,
            'cache_enabled': self.config.enable_caching
        }
        
        if self.cache:
            service_stats.update(self.get_cache_stats())
        
        return {**base_stats, **service_stats}
    
    def shutdown(self):
        """Shutdown service và cleanup resources"""
        try:
            if self._thread_executor:
                self._thread_executor.shutdown(wait=False)
            
            if self._process_executor:
                self._process_executor.shutdown(wait=False)
            
            if self.cache:
                self.cache.clear()
            
            logger.info("ParallelPreviewService shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


class PreviewServiceFactory:
    """Factory for creating configured preview services"""
    
    @staticmethod
    def create_default() -> ParallelPreviewService:
        """Create service với default configuration"""
        return ParallelPreviewService()
    
    @staticmethod
    def create_for_large_operations() -> ParallelPreviewService:
        """Create service optimized for large operations"""
        config = PreviewConfig(
            max_workers=multiprocessing.cpu_count(),
            chunk_size=200,  # Larger chunks
            enable_caching=True,
            cache_size=20000,  # Larger cache
            use_process_pool=True,  # Use process pool for better parallelism
            enable_estimated_time=True
        )
        return ParallelPreviewService(config)
    
    @staticmethod
    def create_for_memory_efficiency() -> ParallelPreviewService:
        """Create service optimized for memory efficiency"""
        config = PreviewConfig(
            max_workers=min(multiprocessing.cpu_count(), 4),
            chunk_size=50,  # Smaller chunks
            enable_caching=True,
            cache_size=5000,  # Smaller cache
            use_process_pool=False,  # Thread pool uses less memory
            enable_estimated_time=True
        )
        return ParallelPreviewService(config)


# Global instance
_preview_service: Optional[ParallelPreviewService] = None


def get_preview_service() -> ParallelPreviewService:
    """Get global ParallelPreviewService instance"""
    global _preview_service
    if _preview_service is None:
        _preview_service = PreviewServiceFactory.create_default()
    return _preview_service


def set_preview_service(service: ParallelPreviewService):
    """Set global ParallelPreviewService instance"""
    global _preview_service
    if _preview_service is not None:
        _preview_service.shutdown()
    _preview_service = service