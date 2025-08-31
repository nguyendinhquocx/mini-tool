"""
UI Tests for Drag-and-Drop Interface (Story 3.1)

Tests visual feedback, user interactions, and cross-platform compatibility.
"""

import pytest
import unittest.mock as mock
import os
import tempfile
import shutil
import tkinter as tk
from unittest.mock import MagicMock, patch
from typing import Any

# Test imports - adjust paths as needed for your project structure  
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.ui.components.drag_drop_handler import DragVisualFeedback
from src.ui.main_window import MainWindow


class TestVisualFeedbackUI:
    """Test visual feedback during drag-drop operations"""
    
    @pytest.fixture
    def mock_tkinter_widget(self):
        """Create mock tkinter widget for UI testing"""
        widget = MagicMock()
        widget.configure = MagicMock()
        return widget
    
    def test_idle_state_visual_feedback(self, mock_tkinter_widget):
        """Test idle state visual appearance"""
        DragVisualFeedback.apply_state(mock_tkinter_widget, 'idle')
        
        # Verify configure was called (visual state applied)
        mock_tkinter_widget.configure.assert_called()
    
    def test_drag_over_valid_visual_feedback(self, mock_tkinter_widget):
        """Test visual feedback for valid drag-over state"""
        DragVisualFeedback.apply_state(mock_tkinter_widget, 'drag_over_valid')
        
        # Verify visual feedback was applied
        mock_tkinter_widget.configure.assert_called()
        
        # Check if appropriate visual properties would be set
        feedback_config = DragVisualFeedback.DRAG_STATES['drag_over_valid']
        assert feedback_config['bg'] == '#e7f3ff'  # Light blue background
        assert 'dashed' in feedback_config['border']  # Dashed border
        assert feedback_config['cursor'] == 'hand2'  # Hand cursor
    
    def test_drag_over_invalid_visual_feedback(self, mock_tkinter_widget):
        """Test visual feedback for invalid drag-over state"""
        DragVisualFeedback.apply_state(mock_tkinter_widget, 'drag_over_invalid')
        
        mock_tkinter_widget.configure.assert_called()
        
        # Check invalid drag-over appearance
        feedback_config = DragVisualFeedback.DRAG_STATES['drag_over_invalid']
        assert feedback_config['bg'] == '#ffe7e7'  # Light red background
        assert 'dashed' in feedback_config['border']  # Dashed border  
        assert feedback_config['cursor'] == 'no'  # No-drop cursor
    
    def test_drop_success_visual_feedback(self, mock_tkinter_widget):
        """Test visual feedback for successful drop"""
        DragVisualFeedback.apply_state(mock_tkinter_widget, 'drop_success')
        
        mock_tkinter_widget.configure.assert_called()
        
        # Check success state appearance
        feedback_config = DragVisualFeedback.DRAG_STATES['drop_success']
        assert feedback_config['bg'] == '#e7ffe7'  # Light green background
        assert 'solid' in feedback_config['border']  # Solid border
    
    def test_visual_state_transitions(self, mock_tkinter_widget):
        """Test visual state transitions during drag-drop sequence"""
        # Simulate drag-drop sequence
        states_sequence = ['idle', 'drag_over_valid', 'drop_success', 'idle']
        
        for state in states_sequence:
            DragVisualFeedback.apply_state(mock_tkinter_widget, state)
            mock_tkinter_widget.configure.assert_called()
            mock_tkinter_widget.configure.reset_mock()  # Reset for next call
    
    def test_visual_feedback_error_handling(self, mock_tkinter_widget):
        """Test visual feedback handles widget errors gracefully"""
        # Make configure method raise an error
        mock_tkinter_widget.configure.side_effect = tk.TclError("Widget error")
        
        # Should not raise exception
        DragVisualFeedback.apply_state(mock_tkinter_widget, 'idle')
        
        # Verify error was handled gracefully
        mock_tkinter_widget.configure.assert_called()


class TestDragDropUserExperience:
    """Test user experience aspects of drag-drop functionality"""
    
    @pytest.fixture
    def temp_test_folder(self):
        """Create temporary folder with test files for UI testing"""
        temp_dir = tempfile.mkdtemp()
        
        # Create test files
        test_files = ["doc1.txt", "image1.jpg", "data.xlsx"]
        for filename in test_files:
            with open(os.path.join(temp_dir, filename), 'w') as f:
                f.write(f"Test content for {filename}")
        
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture  
    def mock_main_window_ui(self):
        """Create mock main window for UI testing"""
        with patch('src.ui.main_window.TkinterDnD'):
            with patch('tkinter.Tk'):
                with patch('tkinter.ttk.Style'):
                    window = MainWindow()
                    
                    # Mock UI components
                    window.content_frame = MagicMock()
                    window.content_frame.drop_target_register = MagicMock()
                    window.content_frame.dnd_bind = MagicMock()
                    
                    return window
    
    def test_drag_enter_user_feedback(self, mock_main_window_ui, temp_test_folder):
        """Test user feedback when drag enters window"""
        window = mock_main_window_ui
        
        # Setup drag-drop handler manually since we're mocking
        from src.ui.components.drag_drop_handler import DragDropHandler
        
        with patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(
                target_widget=window.content_frame,
                on_folder_dropped=window.handle_folder_drop
            )
        
        # Mock drag enter event
        mock_event = MagicMock()
        mock_event.data = temp_test_folder
        
        with patch.object(handler, '_extract_dropped_data', return_value=[temp_test_folder]):
            with patch.object(handler, '_validate_drag_data', return_value=True):
                handler._on_drag_enter(mock_event)
        
        # Verify drag state was updated
        assert handler.is_drag_active
        assert handler.current_drag_valid
    
    def test_drag_leave_user_feedback(self, mock_main_window_ui):
        """Test user feedback when drag leaves window"""
        window = mock_main_window_ui
        
        from src.ui.components.drag_drop_handler import DragDropHandler
        
        with patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(
                target_widget=window.content_frame,
                on_folder_dropped=window.handle_folder_drop
            )
        
        # Set up active drag state
        handler.is_drag_active = True
        handler.current_drag_valid = True
        
        # Mock drag leave event
        mock_event = MagicMock()
        handler._on_drag_leave(mock_event)
        
        # Verify drag state was reset
        assert not handler.is_drag_active
        assert not handler.current_drag_valid
    
    def test_successful_drop_user_feedback(self, mock_main_window_ui, temp_test_folder):
        """Test user feedback on successful folder drop"""
        window = mock_main_window_ui
        
        # Mock folder selector component
        mock_folder_selector = MagicMock()
        window.components['folder_selector'] = mock_folder_selector
        
        # Test successful drop
        window.handle_folder_drop(temp_test_folder)
        
        # Verify folder selector was updated with drag-drop method
        mock_folder_selector.set_folder_from_drag_drop.assert_called_once_with(temp_test_folder)
        
        # Verify state was updated
        state = window.state_manager.state
        assert state.selected_folder == temp_test_folder
    
    def test_invalid_drop_user_feedback(self, mock_main_window_ui):
        """Test user feedback for invalid drops"""
        window = mock_main_window_ui
        
        # Test validation with invalid path
        invalid_path = "/nonexistent/path"
        is_valid = window._validate_dropped_folder(invalid_path)
        
        assert not is_valid
        
        # Verify state reflects invalid drop
        state = window.state_manager.state
        assert not state.drag_drop_valid
    
    def test_folder_selector_status_messages(self, temp_test_folder):
        """Test folder selector status message updates"""
        from src.ui.components.folder_selector import FolderSelectorComponent
        
        # Mock UI components
        with patch('tkinter.ttk.Frame'), patch('tkinter.ttk.Label') as mock_label:
            with patch('tkinter.ttk.Entry'), patch('tkinter.ttk.Button'):
                
                mock_parent = MagicMock()
                mock_callback = MagicMock()
                
                component = FolderSelectorComponent(mock_parent, mock_callback)
                component.status_label = MagicMock()
                
                # Test drag-drop status message
                with patch.object(component, '_validate_folder', return_value=True):
                    component.set_folder_from_drag_drop(temp_test_folder)
                
                # Verify status was updated with drag-drop indicator
                component.status_label.config.assert_called()
                call_args = component.status_label.config.call_args
                
                # Check that status message indicates drag-drop
                if call_args and 'text' in call_args[1]:
                    status_text = call_args[1]['text']
                    assert "Dropped:" in status_text or "🎯" in status_text


class TestCrossPlatformUICompatibility:
    """Test cross-platform UI compatibility"""
    
    def test_windows_path_display(self):
        """Test Windows path display in UI components"""
        from src.ui.components.folder_selector import FolderSelectorComponent
        
        windows_path = r"C:\Users\TestUser\Documents\TestFolder"
        
        with patch('tkinter.ttk.Frame'), patch('tkinter.ttk.Label'):
            with patch('tkinter.ttk.Entry'), patch('tkinter.ttk.Button'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            
                            mock_parent = MagicMock()
                            mock_callback = MagicMock()
                            
                            component = FolderSelectorComponent(mock_parent, mock_callback)
                            component.status_label = MagicMock()
                            
                            component.set_folder_from_drag_drop(windows_path)
                            
                            # Verify path was accepted
                            assert component.get_selected_folder() == windows_path
    
    def test_unix_path_display(self):
        """Test Unix path display in UI components"""
        from src.ui.components.folder_selector import FolderSelectorComponent
        
        unix_path = "/home/testuser/documents/testfolder"
        
        with patch('tkinter.ttk.Frame'), patch('tkinter.ttk.Label'):
            with patch('tkinter.ttk.Entry'), patch('tkinter.ttk.Button'):
                with patch('os.path.exists', return_value=True):
                    with patch('os.path.isdir', return_value=True):
                        with patch('os.access', return_value=True):
                            
                            mock_parent = MagicMock()
                            mock_callback = MagicMock()
                            
                            component = FolderSelectorComponent(mock_parent, mock_callback)
                            component.status_label = MagicMock()
                            
                            component.set_folder_from_drag_drop(unix_path)
                            
                            # Verify path was accepted
                            assert component.get_selected_folder() == unix_path
    
    def test_network_path_handling(self):
        """Test network path handling in UI"""
        from src.core.services.validation_service import get_drag_drop_validator
        
        # Test UNC path
        unc_path = r"\\server\share\folder"
        
        validator = get_drag_drop_validator()
        
        with patch('os.path.exists', return_value=True):
            with patch('os.path.isdir', return_value=True):
                with patch('os.access', return_value=True):
                    with patch('os.listdir', return_value=['file1.txt']):
                        
                        result = validator.validate_dropped_folder(unc_path)
                        
                        # Should be valid but with network warning
                        assert result.is_valid
                        
                        warnings = result.warnings
                        assert any("network drive" in warning.message.lower() 
                                  for warning in warnings)


class TestAccessibilityAndUsability:
    """Test accessibility and usability aspects"""
    
    def test_visual_feedback_color_contrast(self):
        """Test that visual feedback colors have adequate contrast"""
        states = DragVisualFeedback.DRAG_STATES
        
        # Test that background colors are distinct
        bg_colors = [state['bg'] for state in states.values()]
        assert len(set(bg_colors)) == len(bg_colors)  # All colors should be unique
        
        # Test specific color requirements
        assert states['drag_over_valid']['bg'] == '#e7f3ff'  # Light blue
        assert states['drag_over_invalid']['bg'] == '#ffe7e7'  # Light red
        assert states['drop_success']['bg'] == '#e7ffe7'  # Light green
    
    def test_cursor_feedback(self):
        """Test that appropriate cursors are used"""
        states = DragVisualFeedback.DRAG_STATES
        
        # Check cursor types
        assert states['idle']['cursor'] == 'arrow'
        assert states['drag_over_valid']['cursor'] == 'hand2'  
        assert states['drag_over_invalid']['cursor'] == 'no'
        assert states['drop_success']['cursor'] == 'hand2'
    
    def test_border_feedback(self):
        """Test that border styles provide clear feedback"""
        states = DragVisualFeedback.DRAG_STATES
        
        # Valid drag-over should have dashed border
        assert 'dashed' in states['drag_over_valid']['border']
        
        # Invalid drag-over should have dashed border (different color)
        assert 'dashed' in states['drag_over_invalid']['border']
        
        # Success should have solid border
        assert 'solid' in states['drop_success']['border']
    
    def test_error_message_clarity(self):
        """Test that error messages are clear and actionable"""
        from src.core.services.validation_service import get_drag_drop_validator
        
        validator = get_drag_drop_validator()
        
        # Test file drop error message
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()
        
        try:
            results = validator.validate_multiple_drops([temp_file.name])
            
            errors = results[temp_file.name].errors
            assert any("Files are not accepted" in error.message for error in errors)
            assert any("only folders" in error.message for error in errors)
            
        finally:
            os.unlink(temp_file.name)
    
    def test_recovery_suggestions_usability(self):
        """Test that recovery suggestions are user-friendly"""
        from src.core.services.validation_service import DragDropFolderValidator
        from src.core.models.error_models import ValidationResult, ValidationErrorCode
        
        validator = DragDropFolderValidator()
        
        # Create test validation result with error
        result = ValidationResult(is_valid=False)
        result.add_error(
            ValidationErrorCode.INVALID_CHARACTER,
            "Directory is not readable",
            "directory",
            "/test/path", 
            "Check permissions"
        )
        
        suggestions = validator.get_error_recovery_suggestions(result)
        
        # Verify suggestions are present and actionable
        assert len(suggestions) > 0
        
        for suggestion in suggestions:
            assert 'action' in suggestion
            assert 'description' in suggestion
            assert 'button_text' in suggestion
            
            # Check that descriptions are user-friendly
            assert len(suggestion['description']) > 10  # Meaningful description
            assert len(suggestion['button_text']) > 0   # Has button text


class TestDragDropAnimation:
    """Test drag-drop animation and timing"""
    
    def test_drop_success_animation_timing(self):
        """Test that success animation has appropriate timing"""
        from src.ui.components.drag_drop_handler import DragDropHandler
        
        mock_widget = MagicMock()
        mock_callback = MagicMock()
        
        with patch('src.ui.components.drag_drop_handler.TkinterDnD'):
            handler = DragDropHandler(mock_widget, mock_callback)
        
        # Mock successful drop
        mock_event = MagicMock()
        mock_event.data = "/test/folder"
        
        with patch.object(handler, '_extract_dropped_data', return_value=["/test/folder"]):
            with patch.object(handler, '_validate_drag_data', return_value=True):
                with patch('os.path.exists', return_value=True):
                    
                    handler._on_drop(mock_event)
                    
                    # Verify that a delayed reset was scheduled
                    mock_widget.after.assert_called_with(500, handler._reset_drag_state)
    
    def test_visual_state_persistence(self):
        """Test that visual states persist appropriately"""
        mock_widget = MagicMock()
        
        # Apply drag-over state
        DragVisualFeedback.apply_state(mock_widget, 'drag_over_valid')
        initial_calls = mock_widget.configure.call_count
        
        # Apply same state again
        DragVisualFeedback.apply_state(mock_widget, 'drag_over_valid')
        
        # Should still attempt to configure (for consistency)
        assert mock_widget.configure.call_count > initial_calls


if __name__ == '__main__':
    pytest.main([__file__, "-v"])