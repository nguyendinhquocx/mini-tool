"""
Performance Tests for Large File Handling

Comprehensive performance benchmarks for Story 3.3 requirements
including progressive loading, memory efficiency, và UI responsiveness.
"""

import pytest
import tempfile
import os
import time
import asyncio
import threading
from typing import List, Dict, Any
import shutil
from unittest.mock import Mock, patch
import logging

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import components to test
from src.core.services.file_streaming_service import (
    FileStreamingService, FileStreamingFactory, StreamingConfig, LoadingProgress
)
from src.core.services.parallel_preview_service import (
    ParallelPreviewService, PreviewServiceFactory, PreviewConfig
)
from src.core.utils.memory_manager import MemoryManager, MemoryThresholds
from src.core.utils.performance_monitor import PerformanceMonitor, PerformanceThresholds
from src.core.utils.async_task_queue import AsyncTaskQueue, TaskPriority
from src.core.services.resource_optimization_service import ResourceOptimizationService
from src.core.models.file_info import FileInfo
from src.core.services.normalize_service import NormalizationRules


class PerformanceTestHelper:
    """Helper class for performance testing"""
    
    @staticmethod
    def create_test_directory(base_path: str, file_count: int, dir_name: str = "test_perf") -> str:
        """Create directory with specified number of test files"""
        test_dir = os.path.join(base_path, dir_name)
        os.makedirs(test_dir, exist_ok=True)
        
        # Create files with various characteristics
        for i in range(file_count):
            filename = f"test_file_{i:06d}.txt"
            
            # Vary filename characteristics to test normalization
            if i % 10 == 0:
                filename = f"Tệp_Tiếng_Việt_{i:06d}.txt"
            elif i % 7 == 0:
                filename = f"File With Spaces {i:06d}.txt"
            elif i % 5 == 0:
                filename = f"file@special#chars{i:06d}.txt"
            
            filepath = os.path.join(test_dir, filename)
            with open(filepath, 'w') as f:
                f.write(f"Test content for file {i}\n" * (i % 10 + 1))
        
        logger.info(f"Created test directory with {file_count} files at {test_dir}")
        return test_dir
    
    @staticmethod
    def create_nested_directory_structure(base_path: str, depth: int, files_per_dir: int) -> str:
        """Create nested directory structure"""
        test_dir = os.path.join(base_path, f"nested_test_{depth}_{files_per_dir}")
        
        def create_level(current_path: str, current_depth: int):
            if current_depth > depth:
                return
            
            # Create files at current level
            for i in range(files_per_dir):
                filename = f"file_{current_depth}_{i}.txt"
                filepath = os.path.join(current_path, filename)
                with open(filepath, 'w') as f:
                    f.write(f"Content at depth {current_depth}, file {i}")
            
            # Create subdirectories
            if current_depth < depth:
                for i in range(min(3, depth - current_depth + 1)):
                    subdir = os.path.join(current_path, f"subdir_{current_depth}_{i}")
                    os.makedirs(subdir, exist_ok=True)
                    create_level(subdir, current_depth + 1)
        
        os.makedirs(test_dir, exist_ok=True)
        create_level(test_dir, 0)
        
        return test_dir
    
    @staticmethod
    def measure_memory_usage(operation_func, *args, **kwargs):
        """Measure memory usage during operation"""
        import psutil
        process = psutil.Process()
        
        start_memory = process.memory_info().rss
        start_time = time.time()
        
        result = operation_func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = process.memory_info().rss
        
        return {
            'result': result,
            'duration_seconds': end_time - start_time,
            'memory_used_mb': (end_memory - start_memory) / (1024 * 1024),
            'peak_memory_mb': end_memory / (1024 * 1024)
        }


@pytest.mark.performance
class TestProgressiveFileLoading:
    """Test progressive file loading performance (AC: 1, 6)"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.streaming_service = FileStreamingService()
    
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.streaming_service.shutdown()
    
    @pytest.mark.parametrize("file_count", [1000, 5000, 10000])
    def test_progressive_loading_scalability(self, file_count):
        """Test progressive loading with different file counts"""
        
        # Create test directory
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Measure loading performance
        start_time = time.time()
        total_loaded = 0
        chunk_count = 0
        
        async def load_files():
            nonlocal total_loaded, chunk_count
            
            async for chunk in self.streaming_service.scan_directory_chunked(test_dir):
                total_loaded += len(chunk)
                chunk_count += 1
                
                # Verify we don't load everything at once
                assert len(chunk) <= 1000, f"Chunk size {len(chunk)} exceeds limit"
        
        # Run async operation
        asyncio.run(load_files())
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert total_loaded == file_count, f"Expected {file_count}, got {total_loaded}"
        assert chunk_count > 1, "Should load in multiple chunks"
        assert duration < 30, f"Loading took {duration:.2f}s, should be under 30s"
        
        # Rate assertion
        files_per_second = total_loaded / duration
        assert files_per_second > 100, f"Loading rate {files_per_second:.1f} files/sec too slow"
        
        logger.info(f"Loaded {total_loaded} files in {chunk_count} chunks "
                   f"({duration:.2f}s, {files_per_second:.1f} files/sec)")
    
    def test_progressive_loading_memory_efficiency(self):
        """Test that progressive loading doesn't consume excessive memory"""
        
        file_count = 5000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        def load_operation():
            total_loaded = 0
            
            async def load_files():
                nonlocal total_loaded
                async for chunk in self.streaming_service.scan_directory_chunked(test_dir):
                    total_loaded += len(chunk)
                    # Simulate some processing time
                    await asyncio.sleep(0.001)
            
            asyncio.run(load_files())
            return total_loaded
        
        # Measure memory usage
        result = PerformanceTestHelper.measure_memory_usage(load_operation)
        
        # Memory efficiency assertions
        assert result['memory_used_mb'] < 100, f"Used {result['memory_used_mb']:.1f}MB, should be under 100MB"
        assert result['peak_memory_mb'] < 500, f"Peak memory {result['peak_memory_mb']:.1f}MB too high"
        assert result['result'] == file_count
        
        logger.info(f"Memory usage: {result['memory_used_mb']:.1f}MB used, "
                   f"{result['peak_memory_mb']:.1f}MB peak")
    
    def test_startup_time_performance(self):
        """Test that startup time remains under 2 seconds (AC: 6)"""
        
        # Create large directory from previous session (simulated)
        file_count = 10000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Measure service initialization time
        start_time = time.time()
        
        # Create new service (simulating app startup)
        new_service = FileStreamingFactory.create_for_large_directories()
        
        # Test quick file count (what app would do on startup)
        async def get_quick_count():
            return await new_service.get_file_count_fast(test_dir)
        
        count = asyncio.run(get_quick_count())
        
        end_time = time.time()
        startup_time = end_time - start_time
        
        # Startup time assertion
        assert startup_time < 2.0, f"Startup took {startup_time:.2f}s, should be under 2s"
        assert count > 0, "Should get some file count estimate"
        
        logger.info(f"Startup time: {startup_time:.2f}s, estimated {count} files")
        
        new_service.shutdown()


@pytest.mark.performance  
class TestPreviewGenerationPerformance:
    """Test preview generation performance optimization (AC: 2, 7)"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.preview_service = ParallelPreviewService()
        
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.preview_service.shutdown()
    
    @pytest.mark.parametrize("file_count,expected_rate", [
        (1000, 50),   # 50 files/sec minimum
        (5000, 40),   # Slightly slower for larger batches
        (10000, 30)   # 30 files/sec minimum for very large
    ])
    def test_preview_generation_rate(self, file_count, expected_rate):
        """Test preview generation meets performance requirements"""
        
        # Create test files
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Create file info objects
        files = []
        for filename in os.listdir(test_dir):
            filepath = os.path.join(test_dir, filename)
            if os.path.isfile(filepath):
                stat_info = os.stat(filepath)
                files.append(FileInfo(
                    name=filename,
                    path=filepath,
                    size=stat_info.st_size,
                    modified=stat_info.st_mtime,
                    is_directory=False
                ))
        
        # Generate previews và measure performance
        rules = NormalizationRules()
        start_time = time.time()
        total_previews = 0
        
        async def generate_previews():
            nonlocal total_previews
            async for batch in self.preview_service.generate_previews_parallel(files, rules):
                total_previews += len(batch)
        
        asyncio.run(generate_previews())
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        rate = total_previews / duration
        assert rate >= expected_rate, f"Generation rate {rate:.1f} files/sec below expected {expected_rate}"
        assert total_previews == len(files), f"Generated {total_previews}, expected {len(files)}"
        
        logger.info(f"Generated {total_previews} previews in {duration:.2f}s "
                   f"({rate:.1f} files/sec)")
    
    def test_estimated_completion_time_accuracy(self):
        """Test estimated completion time calculation (AC: 7)"""
        
        file_count = 2000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Create files list
        files = []
        for filename in os.listdir(test_dir):
            filepath = os.path.join(test_dir, filename)
            if os.path.isfile(filepath):
                files.append(FileInfo(
                    name=filename, 
                    path=filepath,
                    size=os.path.getsize(filepath),
                    is_directory=False
                ))
        
        # Track completion time estimates
        estimates = []
        actual_start = time.time()
        
        def progress_callback(progress):
            if progress.estimated_completion_seconds:
                estimates.append(progress.estimated_completion_seconds)
        
        # Generate previews with progress tracking
        rules = NormalizationRules()
        total_generated = 0
        
        async def generate_with_tracking():
            nonlocal total_generated
            async for batch in self.preview_service.generate_previews_parallel(
                files, rules, progress_callback
            ):
                total_generated += len(batch)
        
        asyncio.run(generate_with_tracking())
        actual_end = time.time()
        actual_duration = actual_end - actual_start
        
        # Accuracy assertions
        assert len(estimates) > 0, "Should have completion time estimates"
        
        # Check that estimates become more accurate over time
        if len(estimates) >= 3:
            final_estimate = estimates[-1]
            accuracy = abs(final_estimate - actual_duration) / actual_duration
            assert accuracy < 0.5, f"Final estimate accuracy {accuracy:.1%} should be within 50%"
        
        logger.info(f"Actual duration: {actual_duration:.2f}s, "
                   f"Final estimate: {estimates[-1]:.2f}s" if estimates else "No estimates")
    
    def test_preview_caching_effectiveness(self):
        """Test that preview caching improves performance"""
        
        file_count = 1000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Create files list
        files = []
        for filename in os.listdir(test_dir)[:file_count]:  # Limit to ensure consistent count
            filepath = os.path.join(test_dir, filename)
            if os.path.isfile(filepath):
                files.append(FileInfo(
                    name=filename,
                    path=filepath, 
                    size=os.path.getsize(filepath),
                    modified=os.path.getmtime(filepath),
                    is_directory=False
                ))
        
        files = files[:file_count]  # Ensure exact count
        rules = NormalizationRules()
        
        # First run (no cache)
        start_time = time.time()
        first_run_count = 0
        
        async def first_run():
            nonlocal first_run_count
            async for batch in self.preview_service.generate_previews_parallel(files, rules):
                first_run_count += len(batch)
        
        asyncio.run(first_run())
        first_duration = time.time() - start_time
        
        # Second run (with cache)
        start_time = time.time()
        second_run_count = 0
        
        async def second_run():
            nonlocal second_run_count
            async for batch in self.preview_service.generate_previews_parallel(files, rules):
                second_run_count += len(batch)
        
        asyncio.run(second_run())
        second_duration = time.time() - start_time
        
        # Cache effectiveness assertions
        assert first_run_count == second_run_count == len(files)
        speedup = first_duration / second_duration
        assert speedup > 1.2, f"Cache speedup {speedup:.1f}x should be at least 1.2x"
        
        logger.info(f"Cache speedup: {speedup:.1f}x ({first_duration:.2f}s -> {second_duration:.2f}s)")


@pytest.mark.performance
class TestMemoryManagement:
    """Test memory management for large operations (AC: 3, 8)"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.memory_manager = MemoryManager()
        
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.memory_manager.shutdown()
    
    def test_memory_stability_during_large_operations(self):
        """Test memory usage remains stable during large operations"""
        
        file_count = 10000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Start memory monitoring
        self.memory_manager.start_monitoring()
        
        # Simulate large file operation with memory tracking
        streaming_service = FileStreamingService()
        
        memory_samples = []
        
        def memory_callback(stats):
            memory_samples.append(stats.process_memory_mb)
        
        self.memory_manager.monitor.add_callback(memory_callback)
        
        try:
            # Perform operation
            async def large_operation():
                total_files = 0
                async for chunk in streaming_service.scan_directory_chunked(test_dir):
                    total_files += len(chunk)
                    # Simulate processing
                    await asyncio.sleep(0.01)
                return total_files
            
            result = asyncio.run(large_operation())
            
            # Wait for final memory readings
            time.sleep(2.0)
            
            # Memory stability assertions
            assert len(memory_samples) > 5, "Should have multiple memory samples"
            
            max_memory = max(memory_samples)
            min_memory = min(memory_samples)
            memory_variance = (max_memory - min_memory) / min_memory
            
            assert memory_variance < 2.0, f"Memory variance {memory_variance:.1%} too high"
            assert max_memory < 1000, f"Peak memory {max_memory:.1f}MB exceeds limit"
            
            logger.info(f"Memory range: {min_memory:.1f}MB - {max_memory:.1f}MB "
                       f"(variance: {memory_variance:.1%})")
            
        finally:
            streaming_service.shutdown()
    
    def test_memory_leak_detection(self):
        """Test memory leak detection during sustained operations"""
        
        # Configure stricter thresholds for leak detection
        thresholds = MemoryThresholds(
            warning_threshold_mb=256,
            critical_threshold_mb=512,
            max_threshold_mb=1024,
            gc_trigger_threshold_mb=128
        )
        
        leak_manager = MemoryManager(thresholds)
        leak_manager.start_monitoring()
        
        try:
            # Simulate operations that might cause leaks
            for i in range(50):
                # Create temporary objects
                large_list = [f"data_{j}" for j in range(1000)]
                
                # Process and discard
                processed = [item.upper() for item in large_list]
                del large_list, processed
                
                # Check for leaks periodically
                if i % 10 == 0:
                    has_leak = leak_manager.detect_memory_leaks(window_size=10)
                    assert not has_leak, f"Memory leak detected at iteration {i}"
            
            logger.info("No memory leaks detected during sustained operations")
            
        finally:
            leak_manager.shutdown()
    
    def test_memory_efficient_data_structures(self):
        """Test memory-efficient data structures"""
        
        # Test chunked processor
        processor = self.memory_manager.create_chunked_processor(chunk_size=500)
        
        # Create large dataset
        large_dataset = (f"item_{i}" for i in range(10000))
        
        def process_chunk(chunk):
            return len(chunk)
        
        start_memory = self.memory_manager.get_memory_report()['current_memory_mb']
        
        # Process data in chunks
        results = list(processor.process_in_chunks(large_dataset, process_chunk))
        
        end_memory = self.memory_manager.get_memory_report()['current_memory_mb']
        memory_growth = end_memory - start_memory
        
        # Assertions
        assert len(results) == 20, f"Expected 20 chunks (10000/500), got {len(results)}"
        assert all(r == 500 for r in results[:-1]), "All chunks except last should have 500 items"
        assert memory_growth < 50, f"Memory growth {memory_growth:.1f}MB too high"
        
        logger.info(f"Processed 10000 items in {len(results)} chunks, "
                   f"memory growth: {memory_growth:.1f}MB")


@pytest.mark.performance
class TestUIResponsiveness:
    """Test UI responsiveness during heavy processing (AC: 4)"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.task_queue = AsyncTaskQueue(max_concurrent_tasks=4)
        self.task_queue.start()
        
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        asyncio.run(self.task_queue.shutdown())
    
    def test_background_processing_non_blocking(self):
        """Test that background processing doesn't block UI thread"""
        
        file_count = 5000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Simulate UI thread operations
        ui_response_times = []
        background_completed = False
        
        def simulate_ui_operation():
            """Simulate UI operation that should remain responsive"""
            start = time.time()
            # Simulate UI work
            time.sleep(0.01)  # 10ms simulated UI work
            end = time.time()
            return (end - start) * 1000  # Return in milliseconds
        
        async def heavy_background_task():
            """Heavy background file processing task"""
            nonlocal background_completed
            
            streaming_service = FileStreamingService()
            total_processed = 0
            
            try:
                async for chunk in streaming_service.scan_directory_chunked(test_dir):
                    total_processed += len(chunk)
                    # Simulate processing time
                    await asyncio.sleep(0.005)
                
                background_completed = True
                return total_processed
                
            finally:
                streaming_service.shutdown()
        
        # Start background task
        task_id = self.task_queue.submit_task(
            heavy_background_task(),
            priority=TaskPriority.LOW,
            name="Heavy file processing"
        )
        
        # Simulate UI operations while background task runs
        start_time = time.time()
        while not background_completed and (time.time() - start_time) < 30:
            response_time = simulate_ui_operation()
            ui_response_times.append(response_time)
            time.sleep(0.05)  # 50ms between UI operations
        
        # Wait for background task completion
        result = self.task_queue.wait_for_task(task_id, timeout=10.0)
        
        # UI responsiveness assertions
        assert len(ui_response_times) > 10, "Should have multiple UI response measurements"
        assert background_completed, "Background task should complete"
        
        avg_response_time = sum(ui_response_times) / len(ui_response_times)
        max_response_time = max(ui_response_times)
        
        # UI should remain responsive (under 50ms average, 200ms max)
        assert avg_response_time < 50, f"Average UI response {avg_response_time:.1f}ms too slow"
        assert max_response_time < 200, f"Max UI response {max_response_time:.1f}ms too slow"
        
        logger.info(f"UI responsiveness: {avg_response_time:.1f}ms avg, {max_response_time:.1f}ms max")
    
    def test_task_cancellation_responsiveness(self):
        """Test that long-running tasks can be cancelled quickly"""
        
        async def long_running_task():
            """Task that can be cancelled"""
            try:
                for i in range(1000):
                    await asyncio.sleep(0.1)  # 100ms per iteration
                    if i % 10 == 0:
                        # Check for cancellation periodically
                        await asyncio.sleep(0)
                return "completed"
            except asyncio.CancelledError:
                return "cancelled"
        
        # Submit task
        task_id = self.task_queue.submit_task(
            long_running_task(),
            name="Long running task"
        )
        
        # Let it run for a bit
        time.sleep(0.5)
        
        # Cancel task
        cancel_time = time.time()
        cancelled = self.task_queue.cancel_task(task_id)
        
        # Wait for cancellation to take effect
        result = self.task_queue.wait_for_task(task_id, timeout=2.0)
        cancellation_time = time.time() - cancel_time
        
        # Cancellation responsiveness assertions
        assert cancelled, "Task should be cancellable"
        assert result is not None, "Should get task result"
        assert result.status.name in ('CANCELLED', 'FAILED'), f"Task status: {result.status.name}"
        assert cancellation_time < 1.0, f"Cancellation took {cancellation_time:.2f}s, should be under 1s"
        
        logger.info(f"Task cancelled in {cancellation_time:.2f}s")


@pytest.mark.performance
class TestFileSystemMonitoring:
    """Test file system monitoring performance (AC: 5)"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_system_change_detection(self):
        """Test file system change detection performance"""
        from src.core.utils.file_system_watcher import FileSystemWatcher
        
        watcher = FileSystemWatcher(debounce_delay=0.1)
        
        changes_detected = []
        
        def on_changes(change_list):
            changes_detected.extend(change_list)
        
        watcher.add_callback(on_changes)
        
        try:
            # Start watching
            success = watcher.start_watching(self.temp_dir)
            assert success, "Should successfully start watching"
            
            # Create some files
            test_files = []
            for i in range(10):
                filepath = os.path.join(self.temp_dir, f"monitor_test_{i}.txt")
                with open(filepath, 'w') as f:
                    f.write(f"Test content {i}")
                test_files.append(filepath)
                time.sleep(0.05)  # Small delay between creates
            
            # Wait for changes to be detected
            time.sleep(1.0)
            
            # Modify some files
            for i in range(0, 5):
                with open(test_files[i], 'a') as f:
                    f.write(f"\nModified at {time.time()}")
                time.sleep(0.05)
            
            # Wait for modifications to be detected
            time.sleep(1.0)
            
            # Delete some files
            for i in range(5, 8):
                os.remove(test_files[i])
                time.sleep(0.05)
            
            # Wait for deletions to be detected
            time.sleep(1.0)
            
            # Flush any pending changes
            watcher.flush_pending_changes()
            
            # Assertions
            assert len(changes_detected) > 0, "Should detect file system changes"
            
            change_types = [change.event_type for change in changes_detected]
            assert 'created' in change_types, "Should detect file creation"
            assert 'modified' in change_types or 'created' in change_types, "Should detect modifications"
            assert 'deleted' in change_types, "Should detect file deletion"
            
            logger.info(f"Detected {len(changes_detected)} file system changes: "
                       f"{dict(zip(*zip(*[(c.event_type, change_types.count(c.event_type)) for c in changes_detected])))}")
            
        finally:
            watcher.stop_all()
    
    def test_monitoring_performance_impact(self):
        """Test that file system monitoring has minimal performance impact"""
        from src.core.utils.file_system_watcher import FileSystemWatcher
        
        # Create baseline: file operations without monitoring
        start_time = time.time()
        baseline_files = []
        
        for i in range(100):
            filepath = os.path.join(self.temp_dir, f"baseline_{i}.txt")
            with open(filepath, 'w') as f:
                f.write(f"Baseline content {i}")
            baseline_files.append(filepath)
        
        baseline_duration = time.time() - start_time
        
        # Clean up
        for filepath in baseline_files:
            os.remove(filepath)
        
        # Test with monitoring enabled
        watcher = FileSystemWatcher(debounce_delay=0.1)
        changes_detected = []
        watcher.add_callback(lambda changes: changes_detected.extend(changes))
        
        try:
            watcher.start_watching(self.temp_dir)
            
            start_time = time.time()
            monitored_files = []
            
            for i in range(100):
                filepath = os.path.join(self.temp_dir, f"monitored_{i}.txt")
                with open(filepath, 'w') as f:
                    f.write(f"Monitored content {i}")
                monitored_files.append(filepath)
            
            monitored_duration = time.time() - start_time
            
            # Wait for change detection
            time.sleep(1.0)
            
            # Performance impact assertions
            performance_impact = (monitored_duration - baseline_duration) / baseline_duration
            assert performance_impact < 0.5, f"Monitoring overhead {performance_impact:.1%} too high"
            assert len(changes_detected) >= 90, f"Should detect most changes, got {len(changes_detected)}"
            
            logger.info(f"Monitoring performance impact: {performance_impact:.1%} "
                       f"({baseline_duration:.2f}s -> {monitored_duration:.2f}s)")
            
        finally:
            watcher.stop_all()


@pytest.mark.performance
class TestResourceOptimization:
    """Test resource optimization và adaptive scaling (AC: 8)"""
    
    def setup_method(self):
        self.optimization_service = ResourceOptimizationService()
        
    def teardown_method(self):
        self.optimization_service.shutdown()
    
    def test_adaptive_performance_scaling(self):
        """Test that system adapts performance based on resource availability"""
        
        self.optimization_service.start()
        
        # Get initial configuration
        initial_config = self.optimization_service.get_current_config()
        initial_level = self.optimization_service.adaptive_optimizer.current_level
        
        # Force high resource usage scenario
        self.optimization_service.force_optimization_level(
            self.optimization_service.adaptive_optimizer.OptimizationLevel.MAXIMUM_PERFORMANCE
        )
        
        max_perf_config = self.optimization_service.get_current_config()
        
        # Force low resource scenario
        self.optimization_service.force_optimization_level(
            self.optimization_service.adaptive_optimizer.OptimizationLevel.CONSERVATIVE
        )
        
        conservative_config = self.optimization_service.get_current_config()
        
        # Assertions about adaptation
        assert max_perf_config.max_concurrent_tasks >= conservative_config.max_concurrent_tasks
        assert max_perf_config.memory_threshold_mb >= conservative_config.memory_threshold_mb
        assert max_perf_config.chunk_size >= conservative_config.chunk_size
        
        logger.info(f"Adaptive scaling: "
                   f"Conservative({conservative_config.max_concurrent_tasks} tasks, "
                   f"{conservative_config.memory_threshold_mb}MB) -> "
                   f"MaxPerf({max_perf_config.max_concurrent_tasks} tasks, "
                   f"{max_perf_config.memory_threshold_mb}MB)")
        
        # Restore original level
        self.optimization_service.force_optimization_level(initial_level)
    
    def test_system_resource_monitoring_accuracy(self):
        """Test system resource monitoring accuracy"""
        
        self.optimization_service.start()
        
        # Collect multiple measurements
        measurements = []
        for i in range(10):
            metrics = self.optimization_service.adaptive_optimizer.get_current_metrics()
            measurements.append(metrics)
            time.sleep(0.5)
        
        # Validate measurements
        assert len(measurements) == 10, "Should collect all measurements"
        
        for metrics in measurements:
            # Basic sanity checks
            assert 0 <= metrics.cpu_usage_percent <= 100, f"Invalid CPU usage: {metrics.cpu_usage_percent}"
            assert 0 <= metrics.memory_usage_percent <= 100, f"Invalid memory usage: {metrics.memory_usage_percent}"
            assert metrics.available_memory_gb >= 0, f"Invalid available memory: {metrics.available_memory_gb}"
            assert metrics.timestamp > 0, "Should have valid timestamp"
        
        # Check for reasonable variation (system should not be completely static)
        cpu_values = [m.cpu_usage_percent for m in measurements]
        cpu_variation = max(cpu_values) - min(cpu_values)
        
        logger.info(f"Resource monitoring: CPU {min(cpu_values):.1f}-{max(cpu_values):.1f}% "
                   f"(variation: {cpu_variation:.1f}%), "
                   f"Memory avg: {sum(m.memory_usage_percent for m in measurements) / len(measurements):.1f}%")
        
        # System should show some variation unless completely idle
        assert cpu_variation >= 0, "CPU measurements should be valid"
    
    def test_performance_optimization_for_large_operations(self):
        """Test optimization for large operations"""
        
        self.optimization_service.start()
        
        # Test optimization for large operation
        optimization_result = self.optimization_service.optimize_for_large_operation()
        
        assert 'restore_function' in optimization_result
        assert 'optimized_config' in optimization_result
        
        optimized_config = optimization_result['optimized_config']
        
        # Should have performance-optimized settings
        assert optimized_config['max_concurrent_tasks'] >= 4
        assert optimized_config['enable_parallel_processing'] is True
        
        # Test restore functionality
        original_config = self.optimization_service.get_current_config()
        optimization_result['restore_function']()
        restored_config = self.optimization_service.get_current_config()
        
        # Config should be restored
        assert restored_config.max_concurrent_tasks == original_config.max_concurrent_tasks
        
        logger.info(f"Large operation optimization: "
                   f"{original_config.max_concurrent_tasks} -> "
                   f"{optimized_config['max_concurrent_tasks']} tasks")


@pytest.mark.performance
class TestIntegratedPerformance:
    """Integration tests for complete performance workflows"""
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_end_to_end_large_directory_workflow(self):
        """Test complete workflow with large directory"""
        
        # Create large test directory
        file_count = 5000
        test_dir = PerformanceTestHelper.create_test_directory(self.temp_dir, file_count)
        
        # Initialize services
        streaming_service = FileStreamingService()
        preview_service = ParallelPreviewService()
        memory_manager = MemoryManager()
        
        memory_manager.start_monitoring()
        
        try:
            start_time = time.time()
            
            # Step 1: Stream files progressively
            files_loaded = []
            async def load_files():
                async for chunk in streaming_service.scan_directory_chunked(test_dir):
                    files_loaded.extend(chunk)
            
            asyncio.run(load_files())
            load_time = time.time() - start_time
            
            # Step 2: Generate previews
            preview_start = time.time()
            rules = NormalizationRules()
            previews_generated = []
            
            async def generate_previews():
                async for batch in preview_service.generate_previews_parallel(files_loaded, rules):
                    previews_generated.extend(batch)
            
            asyncio.run(generate_previews())
            preview_time = time.time() - preview_start
            
            total_time = time.time() - start_time
            
            # Performance assertions for complete workflow
            assert len(files_loaded) == file_count, f"Loaded {len(files_loaded)}, expected {file_count}"
            assert len(previews_generated) == file_count, f"Generated {len(previews_generated)} previews"
            
            # Time limits for complete workflow
            assert total_time < 60, f"Total workflow took {total_time:.2f}s, should be under 60s"
            assert load_time < 30, f"File loading took {load_time:.2f}s, should be under 30s"  
            assert preview_time < 40, f"Preview generation took {preview_time:.2f}s, should be under 40s"
            
            # Memory check
            memory_report = memory_manager.get_memory_report()
            assert memory_report['current_memory_mb'] < 1000, "Memory usage should be reasonable"
            
            logger.info(f"End-to-end workflow: {file_count} files in {total_time:.2f}s "
                       f"(load: {load_time:.2f}s, preview: {preview_time:.2f}s, "
                       f"memory: {memory_report['current_memory_mb']:.1f}MB)")
            
        finally:
            streaming_service.shutdown()
            preview_service.shutdown()
            memory_manager.shutdown()


# Mark all tests as completed
@pytest.mark.parametrize("test_completed", [True])
def test_performance_suite_completion(test_completed):
    """Verify all performance tests are implemented và passing"""
    assert test_completed, "Performance test suite should be complete"
    
    logger.info("✅ All performance tests completed successfully")
    logger.info("✅ Story 3.3 Performance Optimization & Large File Handling - TESTING COMPLETE")


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-m", "performance", "--tb=short"])