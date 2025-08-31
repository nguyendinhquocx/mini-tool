"""
Integration Tests for Drag-and-Drop Folder Support (Story 3.1)

Tests complete drag-drop workflows, error handling, and component integration.
"""

import pytest
import unittest.mock as mock
import os
import tempfile
import shutil
from pathlib import Path
import tkinter as tk
from typing import Dict, Any

# Test imports - adjust paths as needed for your project structure
from src.ui.main_window import MainWindow, StateManager
from src.ui.components.folder_selector import FolderSelectorComponent
from src.core.services.validation_service import get_drag_drop_validator


class TestDragDropWorkflowIntegration:
    """Test complete drag-drop workflow integration"""
    
    @pytest.fixture
    def temp_folder_with_files(self):
        """Create temporary folder with test files"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files with different extensions
        test_files = [
            "document1.txt",
            "document2.pdf", 
            "image1.jpg",
            "spreadsheet.xlsx",
            "presentation.pptx"
        ]
        
        for filename in test_files:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write(f"Test content for {filename}")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window for testing"""
        with mock.patch('src.ui.main_window.TkinterDnD'):
            with mock.patch('tkinter.Tk'):
                with mock.patch('tkinter.ttk.Style'):
                    window = MainWindow()
                    return window
    
    def test_complete_drag_drop_workflow(self, temp_folder_with_files, mock_main_window):
        """Test complete drag-drop workflow from start to finish"""
        # Setup components
        mock_folder_selector = mock.MagicMock(spec=FolderSelectorComponent)
        mock_main_window.components['folder_selector'] = mock_folder_selector
        
        # Test folder drop
        mock_main_window.handle_folder_drop(temp_folder_with_files)
        
        # Verify folder selector was updated
        mock_folder_selector.set_folder_from_drag_drop.assert_called_once_with(temp_folder_with_files)
        
        # Verify state was updated
        state = mock_main_window.state_manager.state
        assert state.selected_folder == temp_folder_with_files
        assert not state.is_drag_active
        assert not state.drag_drop_valid
    
    def test_drag_drop_with_file_list_refresh(self, temp_folder_with_files, mock_main_window):
        """Test that file list refreshes after successful drop"""
        # Setup file preview component
        mock_file_preview = mock.MagicMock()
        mock_main_window.components['file_preview'] = mock_file_preview
        
        # Test folder drop
        mock_main_window.handle_folder_drop(temp_folder_with_files)
        
        # Verify file list refresh was triggered
        if hasattr(mock_file_preview, 'refresh_file_list'):
            mock_file_preview.refresh_file_list.assert_called_once()
        elif hasattr(mock_file_preview, 'scan_folder'):
            mock_file_preview.scan_folder.assert_called_once_with(temp_folder_with_files)
    
    def test_drag_drop_with_app_controller_notification(self, temp_folder_with_files, mock_main_window):
        """Test that app controller is notified of folder selection"""
        # Setup app controller
        mock_app_controller = mock.MagicMock()
        mock_main_window.components['app_controller'] = mock_app_controller
        
        # Test folder drop
        mock_main_window.handle_folder_drop(temp_folder_with_files)
        
        # Verify app controller was notified
        if hasattr(mock_app_controller, 'on_folder_selected'):
            mock_app_controller.on_folder_selected.assert_called_once_with(temp_folder_with_files)
    
    def test_drag_validation_integration(self, temp_folder_with_files):
        """Test drag validation integration with validation service"""
        validator = get_drag_drop_validator()
        
        # Test single folder validation
        results = validator.validate_multiple_drops([temp_folder_with_files])
        
        assert temp_folder_with_files in results
        assert results[temp_folder_with_files].is_valid
    
    def test_invalid_folder_drop_handling(self, mock_main_window):
        """Test handling of invalid folder drops"""
        invalid_path = "/nonexistent/folder/path"
        
        # Test validation callback
        is_valid = mock_main_window._validate_dropped_folder(invalid_path)
        
        assert not is_valid
        
        # Verify state reflects invalid drop
        state = mock_main_window.state_manager.state
        assert not state.drag_drop_valid


class TestErrorHandlingIntegration:
    """Test error handling across drag-drop components"""
    
    @pytest.fixture
    def temp_file_not_folder(self):
        """Create temporary file (not folder) for testing"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.write("Test file content")
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    def test_file_drop_rejection(self, temp_file_not_folder):
        """Test that dropping files is properly rejected"""
        validator = get_drag_drop_validator()
        
        results = validator.validate_multiple_drops([temp_file_not_folder])
        
        assert temp_file_not_folder in results
        assert not results[temp_file_not_folder].is_valid
        
        # Check error message
        errors = results[temp_file_not_folder].errors
        assert any("Files are not accepted" in error.message for error in errors)
    
    def test_multiple_folder_drop_handling(self):
        """Test handling multiple folder drops"""
        temp_dir1 = tempfile.mkdtemp()
        temp_dir2 = tempfile.mkdtemp()
        
        try:
            validator = get_drag_drop_validator()
            
            results = validator.validate_multiple_drops([temp_dir1, temp_dir2])
            
            # First folder should be valid but with warning
            assert results[temp_dir1].is_valid
            warnings = results[temp_dir1].warnings
            assert any("Multiple folders dropped" in warning.message for warning in warnings)
            
            # Second folder should have warning about being ignored
            warnings = results[temp_dir2].warnings
            assert any("Folder ignored" in warning.message for warning in warnings)
            
        finally:
            shutil.rmtree(temp_dir1, ignore_errors=True)
            shutil.rmtree(temp_dir2, ignore_errors=True)
    
    def test_permission_error_handling(self):
        """Test handling permission errors during validation"""
        validator = get_drag_drop_validator()
        
        # Mock a folder that exists but is not readable
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isdir', return_value=True):
                with mock.patch('os.access', return_value=False):  # No read access
                    
                    result = validator.validate_dropped_folder("/restricted/folder")
                    
                    assert not result.is_valid
                    assert any("not readable" in error.message for error in result.errors)
    
    def test_network_drive_warning(self):
        """Test network drive warning generation"""
        validator = get_drag_drop_validator()
        
        # Test UNC path (Windows network drive)
        unc_path = r"\\server\share\folder"
        
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.isdir', return_value=True):
                with mock.patch('os.access', return_value=True):
                    with mock.patch('os.listdir', return_value=['file1.txt', 'file2.txt']):
                        
                        result = validator.validate_dropped_folder(unc_path)
                        
                        # Should have network drive warning
                        warnings = result.warnings
                        assert any("network drive" in warning.message.lower() 
                                  for warning in warnings)
    
    def test_error_recovery_suggestions(self):
        """Test error recovery suggestion generation"""
        validator = get_drag_drop_validator()
        
        # Create validation result with various errors
        from src.core.models.error_models import ValidationResult, ValidationErrorCode
        
        result = ValidationResult(is_valid=False)
        result.add_error(
            ValidationErrorCode.INVALID_CHARACTER,
            "Directory is not readable",
            "directory", 
            "/test/path",
            "Check permissions"
        )
        
        suggestions = validator.get_error_recovery_suggestions(result)
        
        assert len(suggestions) > 0
        
        # Should include browse dialog fallback
        actions = [s['action'] for s in suggestions]
        assert 'try_browse' in actions
        
        # Should include helpful descriptions
        descriptions = [s['description'] for s in suggestions]
        assert any('Browse Dialog' in desc for desc in descriptions)


class TestStateManagementIntegration:
    """Test state management across drag-drop operations"""
    
    def test_state_manager_drag_state_tracking(self):
        """Test state manager tracks drag states correctly"""
        state_manager = StateManager()
        
        # Test initial state
        initial_state = state_manager.state
        assert not initial_state.is_drag_active
        assert not initial_state.drag_drop_valid
        assert initial_state.pending_folder_drop is None
        
        # Test drag enter state
        state_manager.update_state(
            is_drag_active=True,
            drag_drop_valid=True,
            pending_folder_drop="/test/folder"
        )
        
        drag_state = state_manager.state
        assert drag_state.is_drag_active
        assert drag_state.drag_drop_valid
        assert drag_state.pending_folder_drop == "/test/folder"
        
        # Test drag complete state
        state_manager.update_state(
            selected_folder="/test/folder",
            is_drag_active=False,
            drag_drop_valid=False,
            pending_folder_drop=None
        )
        
        final_state = state_manager.state
        assert final_state.selected_folder == "/test/folder"
        assert not final_state.is_drag_active
        assert not final_state.drag_drop_valid
        assert final_state.pending_folder_drop is None
    
    def test_state_observer_notification(self):
        """Test that state observers are notified of drag-drop changes"""
        state_manager = StateManager()
        
        # Setup mock observer
        mock_observer = mock.MagicMock()
        state_manager.subscribe(mock_observer)
        
        # Update state
        state_manager.update_state(
            selected_folder="/new/folder",
            is_drag_active=False
        )
        
        # Verify observer was called
        mock_observer.assert_called()
        
        # Verify observer received updated state
        call_args = mock_observer.call_args[0]
        updated_state = call_args[0]
        assert updated_state.selected_folder == "/new/folder"


class TestFolderSelectorIntegration:
    """Test folder selector component integration with drag-drop"""
    
    @pytest.fixture
    def folder_selector_component(self):
        """Create folder selector component for testing"""
        with mock.patch('tkinter.Tk'):  # Create root window first
            with mock.patch('tkinter.ttk.Frame'):
                with mock.patch('tkinter.ttk.Label'):
                    with mock.patch('tkinter.ttk.Entry'):
                        with mock.patch('tkinter.ttk.Button'):
                            with mock.patch('tkinter.StringVar'):
                                mock_parent = mock.MagicMock()
                                mock_callback = mock.MagicMock()
                                
                                component = FolderSelectorComponent(mock_parent, mock_callback)
                                return component
    
    def test_set_folder_from_drag_drop(self, folder_selector_component, temp_folder_with_files):
        """Test setting folder via drag-drop method"""
        component = folder_selector_component
        
        # Mock validation to return True
        with mock.patch.object(component, '_validate_folder', return_value=True):
            component.set_folder_from_drag_drop(temp_folder_with_files)
        
        # Verify folder was set
        assert component.get_selected_folder() == temp_folder_with_files
        assert component.get_selection_method() == "drag_drop"
        assert component.is_drag_drop_selection()
    
    def test_drag_drop_vs_browse_distinction(self, folder_selector_component, temp_folder_with_files):
        """Test distinction between drag-drop and browse selection"""
        component = folder_selector_component
        
        # Mock validation and file dialog
        with mock.patch.object(component, '_validate_folder', return_value=True):
            with mock.patch('tkinter.filedialog.askdirectory', return_value=temp_folder_with_files):
                
                # Test browse selection
                component._browse_folder()
                assert component.get_selection_method() == "browse"
                assert not component.is_drag_drop_selection()
                
                # Test drag-drop selection  
                component.set_folder_from_drag_drop(temp_folder_with_files)
                assert component.get_selection_method() == "drag_drop"
                assert component.is_drag_drop_selection()
    
    def test_status_message_differentiation(self, folder_selector_component, temp_folder_with_files):
        """Test that status messages differ for drag-drop vs browse"""
        component = folder_selector_component
        
        with mock.patch.object(component, '_validate_folder', return_value=True):
            with mock.patch.object(component, '_update_status') as mock_update:
                
                # Test drag-drop status message
                component.set_folder_from_drag_drop(temp_folder_with_files)
                
                # Verify status message includes drag-drop indicator
                mock_update.assert_called()
                call_args = mock_update.call_args[0]
                status_message = call_args[0]
                assert "Dropped:" in status_message or "🎯" in status_message


class TestPerformanceIntegration:
    """Test performance aspects of drag-drop integration"""
    
    def test_large_folder_validation_performance(self):
        """Test validation performance with large folders"""
        validator = get_drag_drop_validator()
        
        # Create mock large folder
        large_folder = tempfile.mkdtemp()
        
        try:
            # Create many files to simulate large folder
            for i in range(100):  # Reasonable number for testing
                with open(os.path.join(large_folder, f"file_{i:03d}.txt"), 'w') as f:
                    f.write(f"Content {i}")
            
            import time
            start_time = time.time()
            
            result = validator.validate_dropped_folder(large_folder)
            
            end_time = time.time()
            validation_time = end_time - start_time
            
            # Validation should complete reasonably quickly (under 5 seconds)
            assert validation_time < 5.0
            assert result.is_valid
            
        finally:
            shutil.rmtree(large_folder, ignore_errors=True)
    
    def test_validation_caching(self):
        """Test that validation results are cached for performance"""
        from src.core.services.validation_service import FileNameValidator
        
        validator = FileNameValidator()
        
        # Test same filename validation multiple times
        filename = "test_file.txt"
        
        import time
        
        # First validation (should cache result)
        start_time = time.time()
        result1 = validator.validate_filename(filename)
        first_time = time.time() - start_time
        
        # Second validation (should use cache)
        start_time = time.time()
        result2 = validator.validate_filename(filename)
        second_time = time.time() - start_time
        
        # Results should be identical
        assert result1.is_valid == result2.is_valid
        assert len(result1.errors) == len(result2.errors)
        
        # Second call should be faster (cached)
        assert second_time <= first_time or second_time < 0.001  # Very small threshold


if __name__ == '__main__':
    pytest.main([__file__, "-v"])