"""
Integration tests for full batch rename workflow

Tests the complete application workflow from UI interaction to file operations:
- AppController integration
- Dialog components
- Service coordination
- State management
- Error scenarios
"""

import pytest
import tempfile
import os
import time
import threading
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ui.components.app_controller import AppController
from ui.dialogs import ProgressDialog, ResultDialog, ProgressInfo, OperationResult
from core.models.file_info import FileInfo
from core.models.operation import NormalizationRules, OperationType


class TestFullWorkflowIntegration:
    """Test complete application workflow integration"""
    
    @pytest.fixture
    def temp_directory_with_files(self):
        """Create temporary directory with Vietnamese test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with Vietnamese names
            test_files = [
                "Tài liệu quan trọng.txt",
                "Báo cáo tháng 12 năm 2024.docx",
                "Ảnh đại diện (mới).jpg", 
                "Hướng dẫn sử dụng & Cài đặt.pdf",
                "File với ký tự đặc biệt!@#$%^&*().txt"
            ]
            
            created_files = []
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {filename}")
                created_files.append(file_path)
                
            yield temp_dir, created_files
            
    @pytest.fixture
    def mock_tkinter_root(self):
        """Create mock tkinter root for testing without GUI"""
        mock_root = MagicMock()
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_root.winfo_rootx.return_value = 100
        mock_root.winfo_rooty.return_value = 100
        mock_root.winfo_width.return_value = 800
        mock_root.winfo_height.return_value = 600
        return mock_root
        
    def test_app_controller_initialization(self):
        """Test AppController initializes all services correctly"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            # Verify services are initialized
            assert controller.db_service is not None
            assert controller.history_service is not None
            assert controller.batch_service is not None
            
            # Verify components are set up
            assert controller.folder_selector is not None
            assert controller.file_preview is not None
            assert controller.rename_button is not None
            assert controller.undo_button is not None
            
            controller.destroy()
            
    def test_state_management_flow(self):
        """Test state management throughout operation workflow"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Initial state
                state = controller.get_current_state()
                assert not state.operation_in_progress
                assert state.progress_percentage == 0.0
                
                # Simulate folder selection
                test_folder = "/test/folder"
                controller.state_manager.update_state(
                    selected_folder=test_folder,
                    files_preview=[FileInfo("test.txt", "test.txt", "/test/folder/test.txt", None)]
                )
                
                # Verify state updated
                state = controller.get_current_state()
                assert state.selected_folder == test_folder
                assert len(state.files_preview) == 1
                
                # Simulate operation in progress
                controller.state_manager.update_state(
                    operation_in_progress=True,
                    progress_percentage=50.0,
                    current_file_being_processed="processing_file.txt"
                )
                
                state = controller.get_current_state()
                assert state.operation_in_progress
                assert state.progress_percentage == 50.0
                assert state.current_file_being_processed == "processing_file.txt"
                
            finally:
                controller.destroy()
                
    def test_batch_operation_workflow_with_mocks(self):
        """Test complete batch operation workflow with mocked services"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Mock the batch service to avoid actual file operations
                mock_batch_service = MagicMock()
                mock_batch_service.is_operation_running.return_value = False
                mock_batch_service.execute_batch_operation.return_value = "test_op_123"
                controller.batch_service = mock_batch_service
                
                # Set up test files
                test_files = [
                    FileInfo("Tài liệu.txt", "Tài liệu.txt", "/test/Tài liệu.txt", None),
                    FileInfo("Báo cáo.docx", "Báo cáo.docx", "/test/Báo cáo.docx", None)
                ]
                controller._current_files = test_files
                controller.state_manager.update_state(
                    selected_folder="/test",
                    files_preview=test_files
                )
                
                # Mock messagebox to auto-confirm
                with patch('ui.components.app_controller.messagebox.askyesno', return_value=True):
                    # Mock progress dialog
                    with patch('ui.components.app_controller.ProgressDialog') as mock_progress_dialog:
                        mock_dialog_instance = MagicMock()
                        mock_progress_dialog.return_value = mock_dialog_instance
                        
                        # Execute rename operation
                        controller._on_rename_files_clicked()
                        
                        # Verify batch service was called
                        mock_batch_service.execute_batch_operation.assert_called_once()
                        call_args = mock_batch_service.execute_batch_operation.call_args
                        
                        # Verify request parameters
                        request = call_args[0][0]
                        assert len(request.files) == 2
                        assert request.source_directory == "/test"
                        assert not request.dry_run
                        
                        # Verify callbacks were set
                        assert call_args[1]['progress_callback'] is not None
                        assert call_args[1]['completion_callback'] is not None
                        assert call_args[1]['error_callback'] is not None
                        
                        # Verify progress dialog was shown
                        mock_progress_dialog.assert_called_once()
                        mock_dialog_instance.show.assert_called_once()
                        
            finally:
                controller.destroy()
                
    def test_operation_progress_handling(self):
        """Test handling of operation progress updates"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Mock progress dialog
                mock_progress_dialog = MagicMock()
                controller.progress_dialog = mock_progress_dialog
                
                # Simulate progress update
                from core.services.batch_operation_service import OperationProgress
                progress = OperationProgress(
                    operation_id="test_123",
                    percentage=75.0,
                    current_file="tai lieu.txt",
                    processed_files=3,
                    total_files=4
                )
                
                controller._on_operation_progress(progress)
                
                # Verify progress dialog was updated
                mock_progress_dialog.update_progress.assert_called_once()
                
                # Verify state was updated
                state = controller.get_current_state()
                assert state.progress_percentage == 75.0
                assert state.current_file_being_processed == "tai lieu.txt"
                
            finally:
                controller.destroy()
                
    def test_operation_completion_handling(self):
        """Test handling of operation completion"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Mock file preview to avoid actual UI updates
                controller.file_preview = MagicMock()
                
                # Mock history service
                controller.history_service = MagicMock()
                controller.history_service.save_operation.return_value = True
                
                # Create mock operation result
                from core.models.operation import BatchOperation
                result = BatchOperation(
                    operation_type=OperationType.BATCH_RENAME,
                    normalization_rules=NormalizationRules(),
                    total_files=5
                )
                result.operation_id = "test_op_456"
                result.operation_name = "Test Operation"
                result.successful_operations = 4
                result.failed_operations = 1
                result.start_operation()
                result.complete_operation()
                
                # Mock main window root for after() method
                controller.main_window.root = MagicMock()
                
                # Mock messagebox for success dialog
                with patch('ui.components.app_controller.messagebox.showinfo') as mock_showinfo:
                    controller._on_operation_completed(result)
                    
                    # Verify state was updated
                    state = controller.get_current_state()
                    assert not state.operation_in_progress
                    
                    # Verify history was saved
                    controller.history_service.save_operation.assert_called_once_with(result, [])
                    
                    # Verify file preview was refreshed
                    # (This would be called if selected_folder was set)
                    
                    # Verify result dialog scheduling
                    controller.main_window.root.after.assert_called_once()
                    
            finally:
                controller.destroy()
                
    def test_operation_error_handling(self):
        """Test error handling during operations"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Mock progress dialog
                mock_progress_dialog = MagicMock()
                controller.progress_dialog = mock_progress_dialog
                
                # Mock messagebox for error display
                with patch('ui.components.app_controller.messagebox.showerror') as mock_showerror:
                    # Simulate error
                    error_message = "Test operation failed: File not found"
                    controller._on_operation_error(error_message)
                    
                    # Verify state was updated
                    state = controller.get_current_state()
                    assert not state.operation_in_progress
                    
                    # Verify progress dialog was closed
                    mock_progress_dialog.close.assert_called_once()
                    
                    # Verify error was shown to user
                    mock_showerror.assert_called_once()
                    
            finally:
                controller.destroy()
                
    def test_undo_operation_workflow(self):
        """Test undo operation workflow"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Mock history service with undoable operation
                controller.history_service = MagicMock()
                controller.history_service.get_operation_history.return_value = [{
                    'operation_id': 'test_op_789',
                    'operation_name': 'Test Rename',
                    'operation_type': OperationType.BATCH_RENAME.value,
                    'successful_files': 3,
                    'completed_at': '2024-01-01 12:00:00',
                    'source_directory': '/test'
                }]
                controller.history_service.can_undo_operation.return_value = (True, "Can undo")
                controller.history_service.undo_operation.return_value = (True, "Successfully undone", [])
                
                # Mock file preview
                controller.file_preview = MagicMock()
                
                # Mock dialogs
                with patch('ui.components.app_controller.messagebox.askyesno', return_value=True):
                    with patch('ui.components.app_controller.messagebox.showinfo') as mock_showinfo:
                        with patch('ui.components.app_controller.ProgressDialog') as mock_progress_dialog:
                            # Set current folder to match operation
                            controller.state_manager.update_state(selected_folder='/test')
                            
                            # Execute undo
                            controller._on_undo_clicked()
                            
                            # Verify undo was called
                            controller.history_service.undo_operation.assert_called_once()
                            
                            # Verify file preview was refreshed
                            controller.file_preview.update_files.assert_called_once_with('/test')
                            
                            # Verify success message was shown
                            mock_showinfo.assert_called_once()
                            
            finally:
                controller.destroy()
                
    def test_button_state_management(self):
        """Test button enable/disable based on application state"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            try:
                # Mock buttons
                controller.rename_button = MagicMock()
                controller.undo_button = MagicMock()
                
                # Mock history service for undo button state
                controller.history_service = MagicMock()
                controller.history_service.get_operation_history.return_value = []
                
                # Test initial state - no files, no operations
                from ui.main_window import ApplicationState, AppState
                state = ApplicationState(
                    current_state=AppState.IDLE,
                    selected_folder=None,
                    files_preview=[],
                    operation_in_progress=False
                )
                
                controller._update_button_states(state)
                
                # Rename button should be disabled (no files)
                controller.rename_button.config.assert_called_with(state='disabled')
                
                # Undo button should be disabled (no operations)
                controller.undo_button.config.assert_called_with(state='disabled')
                
                # Test with files but no operation
                state.selected_folder = "/test"
                state.files_preview = [FileInfo("test.txt", "test.txt", "/test/test.txt", None)]
                
                controller._update_button_states(state)
                
                # Rename button should be enabled
                calls = controller.rename_button.config.call_args_list
                assert any(call[1]['state'] == 'normal' for call in calls)
                
                # Test with operation in progress
                state.operation_in_progress = True
                controller._update_button_states(state)
                
                # Rename button should be disabled during operation
                calls = controller.rename_button.config.call_args_list
                assert any(call[1]['state'] == 'disabled' for call in calls)
                
            finally:
                controller.destroy()
                
    def test_resource_cleanup(self):
        """Test proper resource cleanup during application shutdown"""
        with patch('ui.components.app_controller.tk.Tk'):
            controller = AppController()
            
            # Mock services
            controller.batch_service = MagicMock()
            controller.db_service = MagicMock()
            controller.progress_dialog = MagicMock()
            
            # Test cleanup
            controller.destroy()
            
            # Verify cleanup was called
            controller.batch_service.cleanup.assert_called_once()
            controller.db_service.close_all_connections.assert_called_once()
            controller.progress_dialog.close.assert_called_once()


class TestDialogIntegration:
    """Test dialog component integration"""
    
    def test_progress_dialog_workflow(self, mock_tkinter_root):
        """Test progress dialog integration workflow"""
        with patch('ui.dialogs.progress_dialog.tk.Toplevel') as mock_toplevel:
            # Mock dialog window
            mock_dialog_window = MagicMock()
            mock_toplevel.return_value = mock_dialog_window
            
            # Create progress dialog
            progress_dialog = ProgressDialog(mock_tkinter_root, "Test Operation")
            
            # Mock cancel callback
            cancel_callback = MagicMock()
            completion_callback = MagicMock()
            
            # Show dialog
            progress_dialog.show(cancel_callback, completion_callback)
            
            # Simulate progress updates
            progress_info = ProgressInfo(
                current_file="test_file.txt",
                processed_files=1,
                total_files=3,
                percentage=33.3,
                operation_name="Test Operation"
            )
            
            progress_dialog.update_progress(progress_info)
            
            # Simulate completion
            progress_info.is_completed = True
            progress_info.percentage = 100.0
            progress_dialog.update_progress(progress_info)
            
            # Verify dialog was configured correctly
            assert progress_dialog.is_visible()
            
    def test_result_dialog_workflow(self, mock_tkinter_root):
        """Test result dialog integration workflow"""
        with patch('ui.dialogs.result_dialog.tk.Toplevel') as mock_toplevel:
            # Mock dialog window
            mock_dialog_window = MagicMock()
            mock_toplevel.return_value = mock_dialog_window
            
            # Create result dialog
            result_dialog = ResultDialog(mock_tkinter_root)
            
            # Create test result
            result = OperationResult(
                operation_id="test_123",
                operation_name="Vietnamese File Rename",
                total_files=5,
                successful_files=4,
                failed_files=1,
                skipped_files=0,
                operation_duration=2.5,
                success_details=[
                    {"original_name": "Tài liệu.txt", "new_name": "tai lieu.txt", "status": "Success"}
                ],
                failure_details=[
                    {"file_name": "locked.txt", "error_message": "File in use", "suggestion": "Close file"}
                ]
            )
            
            # Mock callbacks
            undo_callback = MagicMock()
            export_callback = MagicMock()
            
            # Show result dialog
            result_dialog.show(result, undo_callback, export_callback)
            
            # Verify dialog was created and configured
            mock_toplevel.assert_called_once()


if __name__ == "__main__":
    # Run specific test
    pytest.main([__file__ + "::TestFullWorkflowIntegration::test_app_controller_initialization", "-v"])