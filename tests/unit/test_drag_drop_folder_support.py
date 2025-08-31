"""
Unit Tests for Drag-and-Drop Folder Support (Story 3.1)

Tests drag-drop event handling, folder validation, visual feedback, and state management.
"""

import pytest
import unittest.mock as mock
import os
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

from src.ui.components.drag_drop_handler import (
    DragDropHandler, DragVisualFeedback, FolderDropValidator
)
from src.core.services.validation_service import (
    DragDropFolderValidator, ValidationResult, ValidationErrorCode
)
from src.ui.main_window import ApplicationState


class TestDragVisualFeedback:
    """Test visual feedback system for drag operations"""
    
    def test_drag_states_definition(self):
        """Test that all required drag states are defined"""
        states = DragVisualFeedback.DRAG_STATES
        
        assert 'idle' in states
        assert 'drag_over_valid' in states
        assert 'drag_over_invalid' in states
        assert 'drop_success' in states
        
        # Each state should have required properties
        for state_name, state_config in states.items():
            assert 'bg' in state_config
            assert 'border' in state_config
            assert 'relief' in state_config
            assert 'cursor' in state_config
    
    @mock.patch('tkinter.Widget')
    def test_apply_state_valid_widget(self, mock_widget):
        """Test applying visual state to valid widget"""
        mock_widget.configure = mock.MagicMock()
        
        DragVisualFeedback.apply_state(mock_widget, 'drag_over_valid')
        
        # Should attempt to configure the widget
        assert mock_widget.configure.called
    
    @mock.patch('tkinter.Widget')
    def test_apply_state_invalid_state(self, mock_widget):
        """Test applying invalid state defaults to idle"""
        mock_widget.configure = mock.MagicMock()
        
        DragVisualFeedback.apply_state(mock_widget, 'nonexistent_state')
        
        # Should still try to configure (with idle state)
        assert mock_widget.configure.called
    
    @mock.patch('tkinter.Widget')
    def test_apply_state_widget_error(self, mock_widget):
        """Test handling widget configuration errors gracefully"""
        mock_widget.configure = mock.MagicMock(side_effect=Exception("Widget error"))
        
        # Should not raise exception
        DragVisualFeedback.apply_state(mock_widget, 'idle')


class TestDragDropHandler:
    """Test main drag-drop handler functionality"""
    
    @pytest.fixture
    def temp_folder(self):
        """Create temporary folder for testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create some test files
        for i in range(3):
            with open(os.path.join(temp_dir, f"test_file_{i}.txt"), 'w') as f:
                f.write(f"Test content {i}")
        
        yield temp_dir
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def temp_file(self):
        """Create temporary file for testing"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        temp_file.write("Test file content")
        temp_file.close()
        
        yield temp_file.name
        
        # Cleanup
        os.unlink(temp_file.name)
    
    @mock.patch('src.ui.components.drag_drop_handler.TkinterDnD')
    def test_drag_drop_handler_initialization(self, mock_dnd):
        """Test drag-drop handler initialization"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        handler = DragDropHandler(
            target_widget=mock_widget,
            on_folder_dropped=mock_callback
        )
        
        assert handler.target_widget == mock_widget
        assert handler.on_folder_dropped == mock_callback
        assert not handler.is_drag_active
        assert not handler.current_drag_valid
        assert handler.visual_feedback is not None
    
    def test_extract_dropped_data_string_format(self):
        """Test extracting dropped data from string format"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Mock event with string data
        mock_event = mock.MagicMock()
        mock_event.data = "/path/to/folder"
        
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.abspath', return_value="/path/to/folder"):
                result = handler._extract_dropped_data(mock_event)
        
        assert result == ["/path/to/folder"]
    
    def test_extract_dropped_data_list_format(self):
        """Test extracting dropped data from list format"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Mock event with list data
        mock_event = mock.MagicMock()
        mock_event.data = ["/path/to/folder1", "/path/to/folder2"]
        
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.abspath', side_effect=lambda x: x):
                result = handler._extract_dropped_data(mock_event)
        
        assert result == ["/path/to/folder1", "/path/to/folder2"]
    
    def test_extract_dropped_data_no_data(self):
        """Test extracting dropped data when no data is present"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Mock event with no data
        mock_event = mock.MagicMock()
        mock_event.data = None
        
        result = handler._extract_dropped_data(mock_event)
        
        assert result is None
    
    def test_default_validation_valid_folder(self, temp_folder):
        """Test default validation with valid folder"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        result = handler._default_validation(temp_folder)
        
        assert result is True
    
    def test_default_validation_invalid_path(self):
        """Test default validation with invalid path"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        result = handler._default_validation("/nonexistent/path")
        
        assert result is False
    
    def test_default_validation_file_not_folder(self, temp_file):
        """Test default validation with file instead of folder"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        result = handler._default_validation(temp_file)
        
        assert result is False
    
    @mock.patch('src.ui.components.drag_drop_handler.logger')
    def test_drag_enter_valid_folder(self, mock_logger, temp_folder):
        """Test drag enter event with valid folder"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Mock event
        mock_event = mock.MagicMock()
        mock_event.data = temp_folder
        
        with mock.patch.object(handler, '_extract_dropped_data', return_value=[temp_folder]):
            with mock.patch.object(handler, '_validate_drag_data', return_value=True):
                handler._on_drag_enter(mock_event)
        
        assert handler.is_drag_active
        assert handler.current_drag_valid
    
    @mock.patch('src.ui.components.drag_drop_handler.logger')
    def test_drag_enter_invalid_data(self, mock_logger):
        """Test drag enter event with invalid data"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Mock event with invalid data
        mock_event = mock.MagicMock()
        mock_event.data = "invalid_path"
        
        with mock.patch.object(handler, '_extract_dropped_data', return_value=None):
            handler._on_drag_enter(mock_event)
        
        assert handler.is_drag_active
        assert not handler.current_drag_valid
    
    def test_reset_drag_state(self):
        """Test resetting drag state to idle"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Set active state
        handler.is_drag_active = True
        handler.current_drag_valid = True
        
        handler._reset_drag_state()
        
        assert not handler.is_drag_active
        assert not handler.current_drag_valid


class TestDragDropFolderValidator:
    """Test specialized drag-drop folder validator"""
    
    def test_initialization(self):
        """Test validator initialization"""
        validator = DragDropFolderValidator()
        
        assert validator.base_validator is not None
    
    def test_validate_multiple_drops_single_folder(self, temp_folder=None):
        """Test validating single folder drop"""
        if temp_folder is None:
            temp_folder = tempfile.mkdtemp()
        
        try:
            validator = DragDropFolderValidator()
            
            with mock.patch.object(validator, 'validate_dropped_folder') as mock_validate:
                mock_result = ValidationResult(is_valid=True)
                mock_validate.return_value = mock_result
                
                results = validator.validate_multiple_drops([temp_folder])
            
            assert temp_folder in results
            assert results[temp_folder].is_valid
            
        finally:
            if os.path.exists(temp_folder):
                shutil.rmtree(temp_folder, ignore_errors=True)
    
    def test_validate_multiple_drops_file_rejected(self, temp_file=None):
        """Test that files are rejected in multiple drops"""
        if temp_file is None:
            temp_file = tempfile.NamedTemporaryFile(delete=False).name
        
        try:
            validator = DragDropFolderValidator()
            
            results = validator.validate_multiple_drops([temp_file])
            
            assert temp_file in results
            assert not results[temp_file].is_valid
            assert any("Files are not accepted" in error.message 
                      for error in results[temp_file].errors)
            
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    def test_validate_multiple_drops_multiple_folders(self):
        """Test handling multiple folder drops (should use first one)"""
        temp_dir1 = tempfile.mkdtemp()
        temp_dir2 = tempfile.mkdtemp()
        
        try:
            validator = DragDropFolderValidator()
            
            with mock.patch.object(validator, 'validate_dropped_folder') as mock_validate:
                mock_result = ValidationResult(is_valid=True)
                mock_validate.return_value = mock_result
                
                results = validator.validate_multiple_drops([temp_dir1, temp_dir2])
            
            # First folder should be valid with warning
            assert results[temp_dir1].is_valid
            assert any("Multiple folders dropped" in warning.message 
                      for warning in results[temp_dir1].warnings)
            
            # Second folder should have warning about being ignored
            assert any("Folder ignored" in warning.message 
                      for warning in results[temp_dir2].warnings)
            
        finally:
            shutil.rmtree(temp_dir1, ignore_errors=True)
            shutil.rmtree(temp_dir2, ignore_errors=True)
    
    def test_get_error_recovery_suggestions(self):
        """Test getting error recovery suggestions"""
        validator = DragDropFolderValidator()
        
        # Create validation result with permission error
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
        assert any(suggestion['action'] == 'try_browse' for suggestion in suggestions)
        assert any(suggestion['action'] == 'run_as_admin' for suggestion in suggestions)
    
    def test_validate_folder_suitability_empty_folder(self):
        """Test validation of empty folder"""
        empty_folder = tempfile.mkdtemp()
        
        try:
            validator = DragDropFolderValidator()
            result = ValidationResult(is_valid=True)
            
            validator._validate_folder_suitability(empty_folder, result)
            
            # Should have warning about no processable files
            assert any("no processable files" in warning.message 
                      for warning in result.warnings)
            
        finally:
            shutil.rmtree(empty_folder, ignore_errors=True)
    
    def test_validate_folder_suitability_many_files(self):
        """Test validation of folder with many files"""
        temp_folder = tempfile.mkdtemp()
        
        try:
            # Create many files (simulate large folder)
            for i in range(1100):  # More than warning threshold
                with open(os.path.join(temp_folder, f"file_{i}.txt"), 'w') as f:
                    f.write(f"Content {i}")
            
            validator = DragDropFolderValidator()
            result = ValidationResult(is_valid=True)
            
            validator._validate_folder_suitability(temp_folder, result)
            
            # Should have warning about many files
            assert any("processing may be slow" in warning.message 
                      for warning in result.warnings)
            
        finally:
            shutil.rmtree(temp_folder, ignore_errors=True)
    
    def test_validate_network_location_unc_path(self):
        """Test validation of UNC network path"""
        validator = DragDropFolderValidator()
        result = ValidationResult(is_valid=True)
        
        # Test UNC path
        unc_path = r"\\server\share\folder"
        validator._validate_network_location(unc_path, result)
        
        # Should have warning about network drive
        assert any("network drive" in warning.message 
                  for warning in result.warnings)


class TestApplicationStateIntegration:
    """Test drag-drop integration with application state"""
    
    def test_application_state_drag_fields(self):
        """Test that ApplicationState has drag-drop fields"""
        state = ApplicationState()
        
        assert hasattr(state, 'is_drag_active')
        assert hasattr(state, 'drag_drop_valid')
        assert hasattr(state, 'pending_folder_drop')
        
        # Check default values
        assert not state.is_drag_active
        assert not state.drag_drop_valid
        assert state.pending_folder_drop is None
    
    def test_handle_folder_drop_state_update(self):
        """Test folder drop updates application state correctly"""
        from src.ui.main_window import StateManager
        
        state_manager = StateManager()
        initial_state = state_manager.state
        
        # Test state update during folder drop
        test_folder = "/test/folder/path"
        
        state_manager.update_state(
            selected_folder=test_folder,
            pending_folder_drop=None,
            is_drag_active=False,
            drag_drop_valid=False
        )
        
        updated_state = state_manager.state
        
        assert updated_state.selected_folder == test_folder
        assert not updated_state.is_drag_active
        assert not updated_state.drag_drop_valid
        assert updated_state.pending_folder_drop is None


class TestCrossPlatformCompatibility:
    """Test cross-platform drag-drop functionality"""
    
    def test_path_normalization_windows(self):
        """Test path normalization for Windows paths"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Test Windows path with backslashes
        mock_event = mock.MagicMock()
        mock_event.data = r"C:\Users\Test\Documents\Folder"
        
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.abspath') as mock_abspath:
                mock_abspath.return_value = r"C:\Users\Test\Documents\Folder"
                result = handler._extract_dropped_data(mock_event)
        
        assert result == [r"C:\Users\Test\Documents\Folder"]
    
    def test_path_normalization_unix(self):
        """Test path normalization for Unix paths"""
        mock_widget = mock.MagicMock()
        mock_callback = mock.MagicMock()
        
        with mock.patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Test Unix path
        mock_event = mock.MagicMock()
        mock_event.data = "/home/user/documents/folder"
        
        with mock.patch('os.path.exists', return_value=True):
            with mock.patch('os.path.abspath') as mock_abspath:
                mock_abspath.return_value = "/home/user/documents/folder"
                result = handler._extract_dropped_data(mock_event)
        
        assert result == ["/home/user/documents/folder"]


if __name__ == '__main__':
    pytest.main([__file__, "-v"])