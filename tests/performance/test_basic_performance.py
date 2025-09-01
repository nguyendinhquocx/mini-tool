"""
Basic Performance Tests

Simple performance tests to validate core functionality and identify any major issues.
"""

import pytest
import tempfile
import os
import time
import shutil
from typing import List

from src.core.services.normalize_service import VietnameseNormalizer, NormalizationRules
from src.core.models.file_info import FileInfo, FileType
from src.core.services.batch_operation_service import BatchOperationService
from src.core.utils.memory_manager import get_memory_manager, MemoryStats


class TestBasicPerformance:
    """Basic performance validation tests"""
    
    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.normalizer = VietnameseNormalizer()
        self.memory_manager = get_memory_manager()
        
    def teardown_method(self):
        """Cleanup test environment"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_files(self, count: int) -> List[str]:
        """Create test files for performance testing"""
        files = []
        for i in range(count):
            filename = f"test_file_{i}.txt"
            if i % 5 == 0:
                filename = f"Tệp_Tiếng_Việt_{i}.txt"
            elif i % 3 == 0:
                filename = f"File With Spaces {i}.txt"
            
            filepath = os.path.join(self.temp_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test content for file {i}")
            files.append(filepath)
        
        return files
    
    def test_normalization_performance(self):
        """Test normalization performance with various file counts"""
        test_cases = [
            ("Small batch", 100),
            ("Medium batch", 500), 
            ("Large batch", 1000)
        ]
        
        for test_name, file_count in test_cases:
            print(f"\n--- {test_name}: {file_count} files ---")
            
            # Create test files
            files = self.create_test_files(file_count)
            
            # Measure normalization performance
            start_time = time.time()
            start_memory = MemoryStats.get_current()
            
            normalized_count = 0
            for filepath in files:
                filename = os.path.basename(filepath)
                normalized_name = self.normalizer.normalize_filename(filename)
                if normalized_name != filename:
                    normalized_count += 1
            
            end_time = time.time()
            end_memory = MemoryStats.get_current()
            
            # Calculate metrics
            duration = end_time - start_time
            files_per_second = file_count / duration if duration > 0 else float('inf')
            memory_used = end_memory.process_memory_mb - start_memory.process_memory_mb
            
            print(f"Duration: {duration:.3f}s")
            print(f"Files/sec: {files_per_second:.1f}")
            print(f"Memory used: {memory_used:.2f}MB")
            print(f"Files normalized: {normalized_count}")
            
            # Performance assertions (relaxed for basic validation)
            assert duration < 5.0, f"Normalization too slow: {duration:.3f}s for {file_count} files"
            assert files_per_second > 50, f"Processing rate too low: {files_per_second:.1f} files/sec"
            assert memory_used < 50, f"Memory usage too high: {memory_used:.2f}MB"
            
            # Clean up files
            for filepath in files:
                try:
                    os.remove(filepath)
                except:
                    pass
    
    def test_memory_stability(self):
        """Test memory stability during repeated operations"""
        print("\n--- Memory Stability Test ---")
        
        initial_memory = MemoryStats.get_current()
        print(f"Initial memory: {initial_memory.process_memory_mb:.2f}MB")
        
        # Perform repeated operations
        for round_num in range(5):
            files = self.create_test_files(200)
            
            # Normalize all files
            for filepath in files:
                filename = os.path.basename(filepath)
                self.normalizer.normalize_filename(filename)
            
            # Clean up
            for filepath in files:
                try:
                    os.remove(filepath)
                except:
                    pass
            
            # Force garbage collection
            self.memory_manager.trigger_gc(force=True)
            
            current_memory = MemoryStats.get_current()
            print(f"Round {round_num + 1} memory: {current_memory.process_memory_mb:.2f}MB")
        
        final_memory = MemoryStats.get_current()
        memory_growth = final_memory.process_memory_mb - initial_memory.process_memory_mb
        
        print(f"Final memory: {final_memory.process_memory_mb:.2f}MB")
        print(f"Memory growth: {memory_growth:.2f}MB")
        
        # Memory should not grow excessively
        assert memory_growth < 20, f"Memory growth too high: {memory_growth:.2f}MB"
    
    def test_file_info_creation_performance(self):
        """Test FileInfo object creation performance"""
        print("\n--- FileInfo Creation Performance ---")
        
        files = self.create_test_files(500)
        
        start_time = time.time()
        start_memory = MemoryStats.get_current()
        
        file_infos = []
        for filepath in files:
            try:
                file_info = FileInfo.from_path(filepath)
                file_infos.append(file_info)
            except Exception as e:
                print(f"Error creating FileInfo for {filepath}: {e}")
        
        end_time = time.time()
        end_memory = MemoryStats.get_current()
        
        duration = end_time - start_time
        objects_per_second = len(file_infos) / duration if duration > 0 else float('inf')
        memory_used = end_memory.process_memory_mb - start_memory.process_memory_mb
        
        print(f"Created {len(file_infos)} FileInfo objects in {duration:.3f}s")
        print(f"Objects/sec: {objects_per_second:.1f}")
        print(f"Memory used: {memory_used:.2f}MB")
        
        # Performance assertions
        assert len(file_infos) == len(files), "Not all FileInfo objects created"
        assert duration < 2.0, f"FileInfo creation too slow: {duration:.3f}s"
        assert objects_per_second > 100, f"Creation rate too low: {objects_per_second:.1f} objects/sec"
        assert memory_used < 20, f"Memory usage too high: {memory_used:.2f}MB"
    
    @pytest.mark.parametrize("file_count", [50, 100, 200])
    def test_directory_scanning_performance(self, file_count):
        """Test directory scanning performance"""
        print(f"\n--- Directory Scanning: {file_count} files ---")
        
        # Create test files
        files = self.create_test_files(file_count)
        
        start_time = time.time()
        
        # Scan directory
        scanned_files = []
        for item in os.listdir(self.temp_dir):
            item_path = os.path.join(self.temp_dir, item)
            if os.path.isfile(item_path):
                scanned_files.append(item_path)
        
        end_time = time.time()
        duration = end_time - start_time
        scan_rate = len(scanned_files) / duration if duration > 0 else float('inf')
        
        print(f"Scanned {len(scanned_files)} files in {duration:.4f}s")
        print(f"Scan rate: {scan_rate:.1f} files/sec")
        
        # Assertions
        assert len(scanned_files) == file_count, f"Expected {file_count}, got {len(scanned_files)}"
        assert duration < 0.5, f"Directory scan too slow: {duration:.4f}s"
        assert scan_rate > 500, f"Scan rate too low: {scan_rate:.1f} files/sec"


def test_performance_baseline():
    """Baseline performance test to ensure system is working"""
    print("\n--- Performance Baseline Test ---")
    
    # Simple operations
    start_time = time.time()
    
    # String operations
    test_strings = [f"Test_{i}_Tệp_Tiếng_Việt" for i in range(1000)]
    normalized_strings = []
    
    normalizer = VietnameseNormalizer()
    for s in test_strings:
        normalized = normalizer.normalize_text(s)
        normalized_strings.append(normalized)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"Processed {len(test_strings)} strings in {duration:.3f}s")
    print(f"String processing rate: {len(test_strings) / duration:.1f} strings/sec")
    
    assert len(normalized_strings) == len(test_strings)
    assert duration < 1.0, f"String processing too slow: {duration:.3f}s"
    assert all(isinstance(s, str) for s in normalized_strings), "Invalid normalization results"
    
    print("Performance baseline test passed!")


if __name__ == "__main__":
    # Can run directly for quick performance check
    test_performance_baseline()
    print("Basic performance test completed successfully!")