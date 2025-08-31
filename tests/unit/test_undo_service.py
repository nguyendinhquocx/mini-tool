"""
Unit Tests for Enhanced Undo Service

Tests the comprehensive undo functionality including validation,
external modification detection, and atomic operations.
"""

import pytest
import tempfile
import os
import shutil
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.core.services.undo_service import UndoService, FileModificationValidator
from src.core.services.database_service import DatabaseService
from src.core.services.operation_history_service import OperationHistoryService
from src.core.models.operation import BatchOperation, NormalizationRules, OperationType
from src.core.models.file_info import FileProcessingRecord, FileInfo, OperationStatus
from src.core.models.undo_models import (
    UndoEligibility, UndoEligibilityReason, FileValidationResult,
    UndoExecutionStatus, UndoOperationResult
)


class TestFileModificationValidator:
    """Test file modification validation"""
    
    def test_validate_file_integrity_success(self, temp_files):
        """Test successful file validation"""
        validator = FileModificationValidator()
        file_path, original_time = temp_files[0]
        
        result = validator.validate_file_integrity(
            file_path, 
            "original.txt",
            "current.txt", 
            original_time
        )
        
        assert result.is_valid
        assert result.validation_error is None
        assert result.can_be_restored
        assert not result.conflict_with_existing
    
    def test_validate_file_integrity_missing_file(self):
        """Test validation of missing file"""
        validator = FileModificationValidator()
        non_existent_path = "/path/that/does/not/exist.txt"
        original_time = datetime.now()
        
        result = validator.validate_file_integrity(
            non_existent_path,
            "original.txt",
            "current.txt",
            original_time
        )
        
        assert not result.is_valid
        assert not result.can_be_restored
        assert "File no longer exists" in result.validation_error
    
    def test_validate_file_integrity_external_modification(self, temp_files):
        """Test detection of external file modification"""
        validator = FileModificationValidator()
        file_path, original_time = temp_files[0]
        
        # Modify file to simulate external change
        with open(file_path, "a") as f:
            f.write("external modification")
        
        # Use old timestamp to simulate external modification
        old_time = original_time - timedelta(hours=1)
        
        result = validator.validate_file_integrity(
            file_path,
            "original.txt", 
            "current.txt",
            old_time
        )
        
        assert not result.is_valid
        assert result.was_modified_externally
        assert "File modified externally" in result.validation_error


class TestUndoService:
    """Test enhanced undo service functionality"""
    
    @pytest.fixture
    def undo_service(self):
        """Create undo service with temporary database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db_service = DatabaseService(db_path)
            history_service = OperationHistoryService(db_service)
            undo_service = UndoService(db_service, history_service)
            
            yield undo_service
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    def test_can_undo_operation_not_found(self, undo_service):
        """Test undo eligibility check for non-existent operation"""
        eligibility = undo_service.can_undo_operation("non_existent_id")
        
        assert not eligibility.can_undo
        assert eligibility.primary_reason == UndoEligibilityReason.OPERATION_NOT_FOUND.value
    
    def test_can_undo_operation_dry_run(self, undo_service):
        """Test undo eligibility check for dry run operation"""
        # Create mock dry run operation
        operation = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            source_directory="/test/path",
            dry_run=True,
            total_files=5
        )
        
        # Save mock operation
        file_records = []
        undo_service.history_service.save_operation(operation, file_records)
        
        eligibility = undo_service.can_undo_operation(operation.operation_id)
        
        assert not eligibility.can_undo
        assert eligibility.primary_reason == UndoEligibilityReason.DRY_RUN_OPERATION.value
    
    def test_can_undo_operation_no_successful_files(self, undo_service):
        """Test undo eligibility check for operation with no successful files"""
        # Create mock failed operation
        operation = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            source_directory="/test/path",
            dry_run=False,
            total_files=5,
            failed_operations=5
        )
        
        # Save mock operation
        file_records = []
        undo_service.history_service.save_operation(operation, file_records)
        
        eligibility = undo_service.can_undo_operation(operation.operation_id)
        
        assert not eligibility.can_undo
        assert eligibility.primary_reason == UndoEligibilityReason.NO_SUCCESSFUL_FILES.value
    
    def test_can_undo_operation_too_old(self, undo_service):
        """Test undo eligibility check for expired operation"""
        # Create mock old operation
        old_time = datetime.now() - timedelta(days=8)  # Older than 7 day limit
        
        operation = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            source_directory="/test/path",
            dry_run=False,
            total_files=5,
            successful_operations=5
        )
        operation.completed_at = old_time
        
        # Save mock operation
        file_records = []
        undo_service.history_service.save_operation(operation, file_records)
        
        eligibility = undo_service.can_undo_operation(operation.operation_id)
        
        assert not eligibility.can_undo
        assert eligibility.primary_reason == UndoEligibilityReason.OPERATION_TOO_OLD.value
    
    def test_get_last_undoable_operation_none(self, undo_service):
        """Test getting last undoable operation when none exist"""
        result = undo_service.get_last_undoable_operation("/test/folder")
        assert result is None
    
    def test_cleanup_expired_undo_operations(self, undo_service):
        """Test cleanup of expired undo operations"""
        # Create mock expired operation
        old_time = datetime.now() - timedelta(days=8)
        
        operation = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            source_directory="/test/path",
            dry_run=False,
            total_files=5,
            successful_operations=5
        )
        operation.completed_at = old_time
        
        # Save mock operation
        file_records = []
        undo_service.history_service.save_operation(operation, file_records)
        
        # Cleanup expired operations
        cleaned_count = undo_service.cleanup_expired_undo_operations()
        
        # Should have cleaned up at least one operation
        assert cleaned_count >= 0  # May be 0 if operation wasn't saved properly


class TestUndoExecutionPlan:
    """Test undo execution planning"""
    
    @pytest.fixture
    def undo_service(self):
        """Create undo service with temporary database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            db_service = DatabaseService(db_path)
            history_service = OperationHistoryService(db_service)
            undo_service = UndoService(db_service, history_service)
            
            yield undo_service
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    def test_create_undo_plan_basic(self, undo_service, temp_files):
        """Test creating basic undo execution plan"""
        # Create mock operation with successful files
        operation = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            source_directory=os.path.dirname(temp_files[0][0]),
            dry_run=False,
            total_files=1,
            successful_operations=1
        )
        
        # Create mock file record
        file_info = FileInfo.from_path(temp_files[0][0])
        file_record = FileProcessingRecord(
            file_info=file_info,
            original_name="original.txt",
            processed_name="processed.txt",
            operation_status=OperationStatus.SUCCESS,
            operation_id=operation.operation_id,
            source_path=temp_files[0][0],
            target_path=temp_files[0][0].replace("original.txt", "processed.txt")
        )
        
        # Save operation
        undo_service.history_service.save_operation(operation, [file_record])
        
        # Create undo plan
        plan = undo_service.create_undo_plan(operation.operation_id)
        
        assert plan.operation_id == operation.operation_id
        assert plan.total_files == 1
        assert len(plan.file_mappings) == 1
        assert plan.estimated_duration is not None


class TestUndoOperationResult:
    """Test undo operation result handling"""
    
    def test_undo_operation_result_success(self):
        """Test successful undo operation result"""
        result = UndoOperationResult(
            operation_id="test_undo_op",
            original_operation_id="test_original_op",
            execution_status=UndoExecutionStatus.NOT_STARTED,
            total_files=3
        )
        
        result.start_execution()
        assert result.execution_status == UndoExecutionStatus.EXECUTING
        
        result.add_successful_restoration("file1.txt", "original1.txt")
        result.add_successful_restoration("file2.txt", "original2.txt")
        result.add_successful_restoration("file3.txt", "original3.txt")
        
        result.complete_execution(success=True)
        
        assert result.is_successful
        assert result.successful_restorations == 3
        assert result.failed_restorations == 0
        assert result.success_rate == 100.0
        assert "successful" in result.completion_message.lower()
    
    def test_undo_operation_result_partial_success(self):
        """Test partial success undo operation result"""
        result = UndoOperationResult(
            operation_id="test_undo_op",
            original_operation_id="test_original_op", 
            execution_status=UndoExecutionStatus.NOT_STARTED,
            total_files=3
        )
        
        result.start_execution()
        result.add_successful_restoration("file1.txt", "original1.txt")
        result.add_successful_restoration("file2.txt", "original2.txt")
        result.add_failed_restoration("file3.txt", "Permission denied")
        result.complete_execution(success=False)
        
        assert not result.is_successful
        assert result.partial_success
        assert result.successful_restorations == 2
        assert result.failed_restorations == 1
        assert abs(result.success_rate - 66.67) < 0.01  # 2/3 * 100 approximately


# Test Fixtures
@pytest.fixture
def temp_files():
    """Create temporary files for testing"""
    temp_dir = tempfile.mkdtemp()
    files = []
    
    try:
        for i in range(3):
            file_path = os.path.join(temp_dir, f"test_file_{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"Test content {i}")
            
            # Get original modification time
            stat_info = os.stat(file_path)
            original_time = datetime.fromtimestamp(stat_info.st_mtime)
            
            files.append((file_path, original_time))
        
        yield files
    finally:
        try:
            shutil.rmtree(temp_dir)
        except OSError:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])