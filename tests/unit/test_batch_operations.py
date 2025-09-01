"""
Unit tests for batch operations functionality

Tests comprehensive batch file processing including:
- Batch operation service
- Operation history service
- Database service
- Progress tracking
- Error handling
"""

import pytest
import tempfile
import os
import threading
import time
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.batch_operation_service import BatchOperationService, BatchOperationRequest, OperationProgress
from core.services.operation_history_service import OperationHistoryService
from core.services.database_service import DatabaseService
from core.models.file_info import FileInfo, FileType, OperationStatus
from core.models.operation import BatchOperation, NormalizationRules, OperationType


class TestBatchOperationService:
    """Test batch operation service functionality"""
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory with test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                "Tài liệu quan trọng.txt",
                "Báo cáo tháng 12.docx", 
                "Ảnh đại diện.jpg",
                "File với ký tự đặc biệt!@#.pdf",
                "UPPERCASE FILE.TXT"
            ]
            
            file_paths = []
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {filename}")
                file_paths.append(file_path)
                
            yield temp_dir, file_paths
            
    @pytest.fixture
    def file_info_list(self, temp_directory):
        """Create FileInfo objects for test files"""
        temp_dir, file_paths = temp_directory
        return [FileInfo.from_path(path) for path in file_paths]
        
    @pytest.fixture
    def batch_service(self):
        """Create batch operation service"""
        service = BatchOperationService()
        yield service
        service.cleanup()
        
    def test_service_initialization(self, batch_service):
        """Test service initializes correctly"""
        assert batch_service.file_engine is not None
        assert not batch_service.is_operation_running()
        assert batch_service.get_current_operation() is None
        
    def test_execute_batch_operation_success(self, batch_service, file_info_list, temp_directory):
        """Test successful batch operation execution"""
        temp_dir, _ = temp_directory
        
        # Track progress updates
        progress_updates = []
        completion_results = []
        
        def progress_callback(progress: OperationProgress):
            progress_updates.append(progress)
            
        def completion_callback(result: BatchOperation):
            completion_results.append(result)
            
        # Create operation request
        request = BatchOperationRequest(
            files=file_info_list,
            rules=NormalizationRules(),
            dry_run=True,  # Don't actually rename files for testing
            source_directory=temp_dir
        )
        
        # Execute operation
        operation_id = batch_service.execute_batch_operation(
            request,
            progress_callback,
            completion_callback
        )
        
        assert operation_id is not None
        assert batch_service.is_operation_running()
        
        # Wait for operation to complete
        timeout = 10  # seconds
        start_time = time.time()
        while batch_service.is_operation_running() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
            
        assert not batch_service.is_operation_running()
        assert len(progress_updates) > 0
        assert len(completion_results) == 1
        
        # Verify results
        result = completion_results[0]
        assert result.operation_id == operation_id
        assert result.total_files == len(file_info_list)
        assert result.is_completed
        
    def test_operation_cancellation(self, batch_service, file_info_list, temp_directory):
        """Test operation cancellation"""
        temp_dir, _ = temp_directory
        
        # Mock file engine to simulate slow operation
        with patch.object(batch_service.file_engine, 'execute_batch_rename') as mock_execute:
            def slow_execution(*args, **kwargs):
                time.sleep(2)  # Simulate slow operation
                return BatchOperation(OperationType.BATCH_RENAME, NormalizationRules())
                
            mock_execute.side_effect = slow_execution
            
            request = BatchOperationRequest(
                files=file_info_list[:2],  # Fewer files for faster test
                rules=NormalizationRules(),
                dry_run=True,
                source_directory=temp_dir
            )
            
            # Start operation
            operation_id = batch_service.execute_batch_operation(request)
            assert batch_service.is_operation_running()
            
            # Cancel operation
            time.sleep(0.1)  # Let operation start
            success = batch_service.cancel_operation()
            assert success
            
            # Wait for cancellation to take effect
            timeout = 5
            start_time = time.time()
            while batch_service.is_operation_running() and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            assert not batch_service.is_operation_running()
            
    def test_concurrent_operations_rejected(self, batch_service, file_info_list, temp_directory):
        """Test that concurrent operations are rejected"""
        temp_dir, _ = temp_directory
        
        # Mock slow operation
        with patch.object(batch_service.file_engine, 'execute_batch_rename') as mock_execute:
            mock_execute.side_effect = lambda *args, **kwargs: time.sleep(1)
            
            request = BatchOperationRequest(
                files=file_info_list[:1],
                rules=NormalizationRules(),
                dry_run=True,
                source_directory=temp_dir
            )
            
            # Start first operation
            operation_id1 = batch_service.execute_batch_operation(request)
            assert batch_service.is_operation_running()
            
            # Try to start second operation
            with pytest.raises(RuntimeError, match="Another batch operation is already running"):
                batch_service.execute_batch_operation(request)
                
            # Cleanup
            batch_service.cancel_operation()
            
    def test_error_handling(self, batch_service, file_info_list, temp_directory):
        """Test error handling in batch operations"""
        temp_dir, _ = temp_directory
        
        error_messages = []
        
        def error_callback(error: str):
            error_messages.append(error)
            
        # Mock file engine to raise exception
        with patch.object(batch_service.file_engine, 'preview_rename') as mock_preview:
            mock_preview.side_effect = Exception("Test error")
            
            request = BatchOperationRequest(
                files=file_info_list,
                rules=NormalizationRules(),
                dry_run=True,
                source_directory=temp_dir
            )
            
            # Execute operation
            operation_id = batch_service.execute_batch_operation(
                request,
                error_callback=error_callback
            )
            
            # Wait for error
            timeout = 5
            start_time = time.time()
            while batch_service.is_operation_running() and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            assert not batch_service.is_operation_running()
            assert len(error_messages) > 0
            assert "Test error" in error_messages[0] or "failed" in error_messages[0].lower()


class TestOperationHistoryService:
    """Test operation history service functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        try:
            os.unlink(db_path)
        except OSError:
            pass
            
    @pytest.fixture
    def db_service(self, temp_db_path):
        """Create database service with temporary database"""
        service = DatabaseService(temp_db_path)
        yield service
        service.close_all_connections()
        
    @pytest.fixture
    def history_service(self, db_service):
        """Create operation history service"""
        return OperationHistoryService(db_service)
        
    @pytest.fixture
    def sample_operation(self):
        """Create sample batch operation"""
        operation = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            source_directory="/test/path",
            total_files=5
        )
        operation.start_operation()
        operation.successful_operations = 4
        operation.failed_operations = 1
        operation.complete_operation()
        return operation
        
    def test_save_and_retrieve_operation(self, history_service, sample_operation):
        """Test saving and retrieving operations"""
        # Save operation
        success = history_service.save_operation(sample_operation, [])
        assert success
        
        # Retrieve history
        history = history_service.get_operation_history()
        assert len(history) == 1
        assert history[0]['operation_id'] == sample_operation.operation_id
        assert history[0]['total_files'] == 5
        assert history[0]['successful_files'] == 4
        assert history[0]['failed_files'] == 1
        
    def test_get_operation_details(self, history_service, sample_operation):
        """Test retrieving detailed operation information"""
        # Save operation with file records
        from core.models.file_info import FileProcessingRecord
        
        file_records = [
            FileProcessingRecord(
                file_info=None,  # Simplified for testing
                original_name="test1.txt",
                processed_name="test1_normalized.txt",
                operation_status=OperationStatus.SUCCESS,
                operation_id=sample_operation.operation_id,
                source_path="/test/path/test1.txt",
                target_path="/test/path/test1_normalized.txt"
            )
        ]
        
        success = history_service.save_operation(sample_operation, file_records)
        assert success
        
        # Retrieve details
        details = history_service.get_operation_details(sample_operation.operation_id)
        assert details is not None
        assert details['operation_id'] == sample_operation.operation_id
        assert len(details['file_records']) == 1
        assert details['file_records'][0]['original_name'] == "test1.txt"
        
    def test_operation_filtering(self, history_service):
        """Test operation history filtering"""
        # Create operations of different types
        rename_op = BatchOperation(OperationType.BATCH_RENAME, NormalizationRules())
        restore_op = BatchOperation(OperationType.RESTORE, NormalizationRules())
        
        for op in [rename_op, restore_op]:
            op.start_operation()
            op.complete_operation()
            history_service.save_operation(op, [])
            
        # Test filtering by operation type
        rename_history = history_service.get_operation_history(
            operation_type=OperationType.BATCH_RENAME
        )
        assert len(rename_history) == 1
        assert rename_history[0]['operation_type'] == OperationType.BATCH_RENAME.value
        
        restore_history = history_service.get_operation_history(
            operation_type=OperationType.RESTORE
        )
        assert len(restore_history) == 1
        assert restore_history[0]['operation_type'] == OperationType.RESTORE.value
        
    def test_cleanup_old_operations(self, history_service):
        """Test cleanup of old operations"""
        # Create old operation by mocking the creation time
        old_operation = BatchOperation(OperationType.BATCH_RENAME, NormalizationRules())
        old_operation.start_operation()
        old_operation.complete_operation()
        
        # Mock the created_at to be old
        import datetime
        old_operation.created_at = datetime.datetime.now() - datetime.timedelta(days=45)
        
        # Save operation
        history_service.save_operation(old_operation, [])
        
        # Verify it exists
        history = history_service.get_operation_history()
        assert len(history) == 1
        
        # Cleanup operations older than 30 days
        deleted_count = history_service.cleanup_old_operations(days_to_keep=30)
        assert deleted_count == 1
        
        # Verify it's gone
        history = history_service.get_operation_history()
        assert len(history) == 0
        
    def test_operation_statistics(self, history_service):
        """Test operation statistics calculation"""
        # Create multiple operations
        operations = []
        for i in range(3):
            op = BatchOperation(OperationType.BATCH_RENAME, NormalizationRules())
            op.total_files = 10
            op.successful_operations = 8 + i  # Different success rates
            op.failed_operations = 2 - i
            op.start_operation()
            op.complete_operation()
            operations.append(op)
            history_service.save_operation(op, [])
            
        # Get statistics
        stats = history_service.get_operation_statistics()
        assert stats['total_operations'] == 3
        assert stats['total_files_processed'] == 30
        assert stats['total_successes'] == 8 + 9 + 10  # 27
        assert stats['total_failures'] == 2 + 1 + 0   # 3
        assert stats['success_rate'] == (27 / 30) * 100  # 90%


class TestDatabaseService:
    """Test database service functionality"""
    
    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        try:
            os.unlink(db_path)
        except OSError:
            pass
            
    @pytest.fixture
    def db_service(self, temp_db_path):
        """Create database service"""
        service = DatabaseService(temp_db_path)
        yield service
        service.close_all_connections()
        
    def test_database_initialization(self, db_service):
        """Test database initialization and schema creation"""
        # Check that tables exist
        with db_service.get_connection() as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            
        table_names = [row['name'] for row in tables]
        expected_tables = ['operation_history', 'file_operations', 'app_settings', 'schema_metadata']
        
        for table in expected_tables:
            assert table in table_names
            
    def test_settings_storage(self, db_service):
        """Test application settings storage and retrieval"""
        # Test different data types
        test_settings = {
            'string_setting': 'Hello World',
            'int_setting': 42,
            'bool_setting': True,
            'float_setting': 3.14,
            'json_setting': {'key': 'value', 'list': [1, 2, 3]}
        }
        
        # Save settings
        for key, value in test_settings.items():
            db_service.set_setting(key, value, f"Test {key}")
            
        # Retrieve and verify settings
        for key, expected_value in test_settings.items():
            retrieved_value = db_service.get_setting(key)
            assert retrieved_value == expected_value
            
        # Test default value
        assert db_service.get_setting('nonexistent', 'default') == 'default'
        
    def test_transaction_handling(self, db_service):
        """Test database transaction handling"""
        # Test successful transaction
        with db_service.transaction() as conn:
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?)",
                ('test_key', 'test_value')
            )
            
        # Verify data was committed
        value = db_service.get_setting('test_key')
        assert value == 'test_value'
        
        # Test failed transaction (should rollback)
        try:
            with db_service.transaction() as conn:
                conn.execute(
                    "INSERT INTO app_settings (key, value) VALUES (?, ?)",
                    ('test_key2', 'test_value2')
                )
                # Force an error
                raise Exception("Test error")
        except Exception:
            pass
            
        # Verify data was not committed
        value = db_service.get_setting('test_key2')
        assert value is None
        
    def test_database_info(self, db_service):
        """Test database information retrieval"""
        info = db_service.get_database_info()
        
        assert 'database_path' in info
        assert 'database_size_bytes' in info
        assert 'schema_version' in info
        assert 'tables' in info
        assert info['schema_version'] == db_service.SCHEMA_VERSION
        assert isinstance(info['tables'], list)
        assert len(info['tables']) > 0


class TestIntegration:
    """Integration tests for batch operations"""
    
    @pytest.fixture
    def temp_directory(self):
        """Create temporary directory with test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Vietnamese test files
            test_files = [
                "Báo cáo tài chính.docx",
                "Hướng dẫn sử dụng.pdf", 
                "Ảnh profile (mới).jpg"
            ]
            
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Content for {filename}")
                    
            yield temp_dir
            
    def test_end_to_end_batch_operation(self, temp_directory):
        """Test complete end-to-end batch operation workflow"""
        # Create services
        db_service = DatabaseService()
        history_service = OperationHistoryService(db_service)
        batch_service = BatchOperationService()
        
        try:
            # Scan directory
            files = []
            for filename in os.listdir(temp_directory):
                file_path = os.path.join(temp_directory, filename)
                if os.path.isfile(file_path):
                    files.append(FileInfo.from_path(file_path))
                    
            assert len(files) == 3
            
            # Create operation request  
            request = BatchOperationRequest(
                files=files,
                rules=NormalizationRules(),
                dry_run=True,  # Don't actually rename files
                source_directory=temp_directory
            )
            
            # Track results
            results = []
            
            def completion_callback(result):
                results.append(result)
                # Save to history
                history_service.save_operation(result, [])
                
            # Execute operation
            operation_id = batch_service.execute_batch_operation(
                request,
                completion_callback=completion_callback
            )
            
            # Wait for completion
            timeout = 10
            start_time = time.time()
            while batch_service.is_operation_running() and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            # Verify operation completed
            assert not batch_service.is_operation_running()
            assert len(results) == 1
            
            result = results[0]
            assert result.operation_id == operation_id
            assert result.total_files == 3
            
            # Verify history was saved
            history = history_service.get_operation_history()
            assert len(history) >= 1
            assert history[0]['operation_id'] == operation_id
            
            # Test statistics
            stats = history_service.get_operation_statistics()
            assert stats['total_operations'] >= 1
            assert stats['total_files_processed'] >= 3
            
        finally:
            # Cleanup
            batch_service.cleanup()
            db_service.close_all_connections()


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__ + "::TestBatchOperationService::test_service_initialization", "-v"])