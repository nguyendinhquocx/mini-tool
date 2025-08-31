"""
Unit tests for Progress Dialog và Cancellation System (Story 2.2)

Tests all acceptance criteria for progress indication và operation cancellation.
"""

import pytest
import tkinter as tk
from tkinter import ttk
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Import components to test
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ui.dialogs.progress_dialog import ProgressDialog, ProgressInfo
from core.models.operation import (
    CancellationToken, OperationResult, OperationStatus,
    TimeEstimator, ProgressCallback, OperationCancelledException
)
from core.services.batch_operation_service import BatchOperationService, OperationProgress
from ui.services.operation_progress_coordinator import OperationProgressCoordinator


class TestProgressDialog:
    """Test ProgressDialog component functionality"""
    
    @pytest.fixture
    def root_window(self):
        root = tk.Tk()
        root.withdraw()  # Hide window during tests
        yield root
        root.destroy()
    
    @pytest.fixture
    def progress_dialog(self, root_window):
        return ProgressDialog(root_window, "Test Operation")
    
    def test_progress_dialog_creation(self, progress_dialog):
        """Test AC: 1 - Progress dialog displays when batch operation begins"""
        assert progress_dialog.operation_name == "Test Operation"
        assert not progress_dialog.is_visible()
        assert progress_dialog.progress_info.operation_name == "Test Operation"
    
    def test_progress_dialog_show_hide(self, progress_dialog):
        """Test dialog show/hide functionality"""
        # Show dialog
        progress_dialog.show()
        assert progress_dialog.is_visible()
        
        # Hide dialog
        progress_dialog.close()
        assert not progress_dialog.is_visible()
    
    def test_progress_bar_updates(self, progress_dialog):
        """Test AC: 2 - Progress bar shows percentage completion và current file"""
        progress_dialog.show()
        
        # Test progress update
        progress_info = ProgressInfo(
            current_file="test_file.txt",
            processed_files=5,
            total_files=10,
            percentage=50.0,
            operation_name="Test Operation"
        )
        
        progress_dialog.update_progress(progress_info)
        
        # Verify UI components updated
        assert progress_dialog.progress_bar['value'] == 50.0
        assert "test_file.txt" in progress_dialog.current_file_label.cget("text")
        assert "5 of 10" in progress_dialog.file_count_label.cget("text")
        
        progress_dialog.close()
    
    def test_estimated_time_display(self, progress_dialog):
        """Test AC: 5 - Estimated time remaining displayed during operation"""
        progress_dialog.show()
        
        progress_info = ProgressInfo(
            current_file="test_file.txt",
            processed_files=3,
            total_files=10,
            percentage=30.0,
            estimated_time_remaining="02:45",
            elapsed_time="01:15",
            processing_speed="2.5 files/sec"
        )
        
        progress_dialog.update_progress(progress_info)
        
        # Check timing displays
        assert progress_dialog.eta_label.cget("text") == "02:45"
        assert progress_dialog.elapsed_time_label.cget("text") == "01:15"
        assert progress_dialog.speed_label.cget("text") == "2.5 files/sec"
        
        progress_dialog.close()
    
    def test_completion_summary(self, progress_dialog):
        """Test AC: 6 - Success message shows number of files processed successfully"""
        progress_dialog.show()
        
        completion_info = ProgressInfo(
            current_file="Operation completed",
            processed_files=10,
            total_files=10,
            percentage=100.0,
            is_completed=True,
            success_count=8,
            error_count=1,
            skipped_count=1
        )
        
        progress_dialog.update_progress(completion_info)
        
        # Should show completion summary
        assert progress_dialog.completion_summary_frame is not None
        assert progress_dialog.cancel_button.cget("text") == "Close"
        
        progress_dialog.close()
    
    def test_auto_close_functionality(self, progress_dialog):
        """Test AC: 8 - Progress dialog automatically closes on completion"""
        progress_dialog.show()
        
        completion_info = ProgressInfo(
            current_file="Operation completed",
            processed_files=5,
            total_files=5,
            percentage=100.0,
            is_completed=True,
            success_count=5,
            error_count=0
        )
        
        # Mock the dialog's after method to test auto-close scheduling
        with patch.object(progress_dialog.dialog, 'after') as mock_after:
            progress_dialog.update_progress(completion_info)
            # Should schedule auto-close
            mock_after.assert_called_with(3000, progress_dialog._close_dialog)
        
        progress_dialog.close()
    
    def test_cancellation_confirmation(self, progress_dialog):
        """Test cancellation confirmation dialog"""
        progress_dialog.show()
        
        # Mock messagebox
        with patch('tkinter.messagebox.askyesno', return_value=True) as mock_msg:
            progress_dialog._confirm_cancellation()
            mock_msg.assert_called_once()
        
        progress_dialog.close()


class TestCancellationToken:
    """Test CancellationToken functionality"""
    
    @pytest.fixture
    def cancellation_token(self):
        return CancellationToken()
    
    def test_initial_state(self, cancellation_token):
        """Test initial cancellation token state"""
        assert not cancellation_token.is_cancelled
        assert cancellation_token.reason is None
        assert cancellation_token.requested_at is None
    
    def test_request_cancellation(self, cancellation_token):
        """Test AC: 3 - Operation can be cancelled mid-process"""
        reason = "User requested"
        cancellation_token.request_cancellation(reason)
        
        assert cancellation_token.is_cancelled
        assert cancellation_token.reason == reason
        assert cancellation_token.requested_at is not None
    
    def test_check_cancelled_raises_exception(self, cancellation_token):
        """Test cancellation check raises appropriate exception"""
        cancellation_token.request_cancellation("Test cancellation")
        
        with pytest.raises(OperationCancelledException) as exc_info:
            cancellation_token.check_cancelled()
        
        assert "Test cancellation" in str(exc_info.value)
    
    def test_token_reset(self, cancellation_token):
        """Test cancellation token reset functionality"""
        cancellation_token.request_cancellation("Test")
        assert cancellation_token.is_cancelled
        
        cancellation_token.reset()
        assert not cancellation_token.is_cancelled
        assert cancellation_token.reason is None
        assert cancellation_token.requested_at is None


class TestTimeEstimator:
    """Test TimeEstimator functionality"""
    
    @pytest.fixture
    def time_estimator(self):
        return TimeEstimator()
    
    def test_elapsed_time_calculation(self, time_estimator):
        """Test elapsed time calculation"""
        time_estimator.start()
        time.sleep(0.1)  # Small delay
        
        elapsed = time_estimator.get_elapsed_time()
        assert elapsed in ["00:00", "00:01"]  # Should be very short
    
    def test_processing_speed_calculation(self, time_estimator):
        """Test processing speed calculation"""
        time_estimator.start()
        time.sleep(0.1)
        
        speed = time_estimator.get_processing_speed(5)
        assert "files/sec" in speed
    
    def test_eta_estimation(self, time_estimator):
        """Test estimated time remaining calculation"""
        time_estimator.start()
        time_estimator.update(2, 10)
        time.sleep(0.1)
        time_estimator.update(4, 10)
        
        eta = time_estimator.estimate_remaining_time(4, 10)
        assert eta is not None
        # Should be "Calculating..." or actual time
        assert eta == "Calculating..." or ":" in eta


class TestOperationResult:
    """Test OperationResult functionality"""
    
    @pytest.fixture
    def operation_result(self):
        return OperationResult(
            operation_id="test_op",
            operation_type="batch_rename",
            status=OperationStatus.PENDING,
            total_files=10
        )
    
    def test_partial_operation_state_management(self, operation_result):
        """Test AC: 4 - Partial operations result in consistent state"""
        # Mark some files as processed
        operation_result.success_count = 5
        operation_result.error_count = 2
        
        # Mark as cancelled
        operation_result.mark_cancelled("User cancelled")
        
        # Verify state consistency
        assert operation_result.status == OperationStatus.CANCELLED
        assert operation_result.was_cancelled
        assert operation_result.cancellation_reason == "User cancelled"
        assert operation_result.success_count == 5  # Completed files remain
        assert operation_result.error_count == 2   # Error count preserved
    
    def test_completion_percentage(self, operation_result):
        """Test completion percentage calculation"""
        operation_result.success_count = 3
        operation_result.error_count = 1
        operation_result.skipped_count = 1
        operation_result.total_files = 10
        
        # 5 completed out of 10 = 50%
        assert operation_result.completion_percentage == 50.0
    
    def test_operation_completed_state(self, operation_result):
        """Test operation completion detection"""
        assert not operation_result.is_completed
        
        operation_result.mark_completed()
        assert operation_result.is_completed
        assert operation_result.status == OperationStatus.COMPLETED


class TestBatchOperationServiceIntegration:
    """Test BatchOperationService với progress và cancellation"""
    
    @pytest.fixture
    def mock_file_engine(self):
        with patch('core.services.batch_operation_service.FileOperationsEngine') as mock:
            yield mock
    
    @pytest.fixture
    def batch_service(self, mock_file_engine):
        return BatchOperationService()
    
    def test_service_responsiveness_during_operation(self, batch_service):
        """Test AC: 7 - Application remains responsive during large batch operations"""
        # This test verifies that service uses background threads
        assert not batch_service.is_operation_running()
        
        # Mock operation request
        from core.services.batch_operation_service import BatchOperationRequest
        from core.models.operation import NormalizationRules
        
        request = BatchOperationRequest(
            files=[],
            rules=NormalizationRules(),
            dry_run=True
        )
        
        progress_updates = []
        def progress_callback(progress):
            progress_updates.append(progress)
        
        # Start operation (should be non-blocking)
        operation_id = batch_service.execute_batch_operation(
            request,
            progress_callback=progress_callback
        )
        
        assert operation_id is not None
        assert batch_service.is_operation_running()
        
        # Should be able to cancel
        assert batch_service.cancel_operation()
        
        # Wait for operation to finish
        timeout = 5.0
        start_time = time.time()
        while batch_service.is_operation_running() and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        assert not batch_service.is_operation_running()
        batch_service.cleanup()


class TestOperationProgressCoordinator:
    """Test OperationProgressCoordinator integration"""
    
    @pytest.fixture
    def root_window(self):
        root = tk.Tk()
        root.withdraw()
        yield root
        root.destroy()
    
    @pytest.fixture
    def coordinator(self, root_window):
        return OperationProgressCoordinator(root_window)
    
    def test_coordinator_initialization(self, coordinator):
        """Test coordinator initialization"""
        assert coordinator.parent_window is not None
        assert coordinator.batch_service is not None
        assert not coordinator.is_busy()
    
    def test_operation_lifecycle(self, coordinator):
        """Test complete operation lifecycle"""
        from core.models.file_info import FileInfo, FileType
        from core.models.operation import NormalizationRules
        
        # Create test files
        test_files = [
            FileInfo("test1.txt", "test1.txt", "/test/test1.txt", FileType.FILE),
            FileInfo("test2.txt", "test2.txt", "/test/test2.txt", FileType.FILE)
        ]
        
        completion_called = False
        completion_result = None
        
        def completion_callback(result, success):
            nonlocal completion_called, completion_result
            completion_called = True
            completion_result = (result, success)
        
        # Mock the batch service to avoid actual file operations
        with patch.object(coordinator.batch_service, 'execute_batch_operation') as mock_execute:
            mock_execute.return_value = "test_operation_id"
            
            # Start operation
            success = coordinator.execute_batch_rename(
                files=test_files,
                normalization_rules=NormalizationRules(),
                source_directory="/test",
                dry_run=True,
                completion_callback=completion_callback
            )
            
            assert success
            assert coordinator.is_busy()
            mock_execute.assert_called_once()
        
        # Test cancellation
        assert coordinator.cancel_current_operation()
        
        # Cleanup
        coordinator.cleanup()
        assert not coordinator.is_busy()


class TestPerformanceAndResponsiveness:
    """Test performance characteristics và UI responsiveness"""
    
    def test_progress_update_throttling(self):
        """Test progress updates are properly throttled"""
        callback_func = Mock()
        progress_callback = ProgressCallback(callback_func, update_interval=0.1)
        
        # Rapid updates should be throttled
        progress_callback.report_progress(10.0, "file1.txt")
        progress_callback.report_progress(20.0, "file2.txt")  # Should be skipped
        progress_callback.report_progress(30.0, "file3.txt")  # Should be skipped
        
        # Only first call should execute immediately
        assert callback_func.call_count == 1
        
        # Wait for throttle period
        time.sleep(0.15)
        
        # Now next update should execute
        progress_callback.report_progress(40.0, "file4.txt")
        assert callback_func.call_count == 2
    
    def test_cancellation_responsiveness(self):
        """Test cancellation is responsive"""
        token = CancellationToken()
        
        # Simulate long operation với cancellation checks
        start_time = time.time()
        operations_completed = 0
        
        try:
            for i in range(1000):
                # Simulate work
                operations_completed = i
                
                # Check for cancellation every 10 operations
                if i % 10 == 0:
                    token.check_cancelled()
                
                # Cancel after 50 operations
                if i == 50:
                    token.request_cancellation("Test cancellation")
                
                time.sleep(0.001)  # Simulate small work
                
        except OperationCancelledException:
            pass
        
        end_time = time.time()
        
        # Should have cancelled quickly (before completing all operations)
        assert operations_completed < 100  # Should cancel well before 1000
        assert (end_time - start_time) < 1.0  # Should cancel within 1 second


# Integration test cho complete workflow
class TestCompleteWorkflow:
    """Integration test for complete progress dialog và cancellation workflow"""
    
    @pytest.fixture
    def root_window(self):
        root = tk.Tk()
        root.withdraw()
        yield root
        root.destroy()
    
    def test_complete_operation_workflow(self, root_window):
        """Test complete workflow from start to completion"""
        coordinator = OperationProgressCoordinator(root_window)
        
        # Track callbacks
        completion_called = False
        error_called = False
        
        def completion_callback(result, success):
            nonlocal completion_called
            completion_called = True
        
        def error_callback(error):
            nonlocal error_called
            error_called = True
        
        # Mock file operations to avoid actual file system changes
        with patch.object(coordinator.batch_service, 'file_engine'):
            with patch.object(coordinator.batch_service, 'execute_batch_operation') as mock_execute:
                mock_execute.return_value = "test_op"
                
                # Start operation
                from core.models.file_info import FileInfo, FileType
                from core.models.operation import NormalizationRules
                
                test_files = [FileInfo("test.txt", "test.txt", "/test.txt", FileType.FILE)]
                
                success = coordinator.execute_batch_rename(
                    files=test_files,
                    normalization_rules=NormalizationRules(),
                    source_directory="/test",
                    completion_callback=completion_callback,
                    error_callback=error_callback
                )
                
                # Verify operation started
                assert success
                assert coordinator.is_busy()
                assert coordinator.progress_dialog is not None
                assert coordinator.progress_dialog.is_visible()
        
        # Cleanup
        coordinator.cleanup()
        assert not coordinator.is_busy()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])