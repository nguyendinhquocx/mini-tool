import pytest
import tkinter as tk
from tkinter import ttk
import os
import sys
import tempfile
from unittest.mock import Mock, patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ui.components.folder_selector import FolderSelectorComponent


class TestFolderSelectorComponent:
    @pytest.fixture
    def root_window(self):
        root = tk.Tk()
        root.withdraw()  # Hide window during tests
        yield root
        root.destroy()

    @pytest.fixture
    def parent_frame(self, root_window):
        return ttk.Frame(root_window)

    @pytest.fixture
    def mock_callback(self):
        return Mock()

    @pytest.fixture
    def folder_selector(self, parent_frame, mock_callback):
        return FolderSelectorComponent(parent_frame, mock_callback)

    @pytest.fixture
    def temp_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_component_initialization(self, folder_selector):
        assert folder_selector.frame is not None
        assert folder_selector.path_entry is not None
        assert folder_selector.browse_button is not None
        assert folder_selector.status_label is not None

    def test_initial_state(self, folder_selector):
        assert folder_selector.get_selected_folder() is None
        assert folder_selector.folder_path.get() == ""

    def test_set_valid_folder(self, folder_selector, temp_folder):
        folder_selector.set_folder(temp_folder)
        assert folder_selector.get_selected_folder() == temp_folder
        assert temp_folder in folder_selector.folder_path.get()

    def test_set_invalid_folder(self, folder_selector):
        invalid_path = "/nonexistent/folder/path"
        folder_selector.set_folder(invalid_path)
        # Should not set the invalid path
        assert folder_selector.get_selected_folder() != invalid_path

    def test_validate_folder_valid(self, folder_selector, temp_folder):
        assert folder_selector._validate_folder(temp_folder) is True

    def test_validate_folder_nonexistent(self, folder_selector):
        assert folder_selector._validate_folder("/nonexistent/path") is False

    def test_validate_folder_not_directory(self, folder_selector):
        with tempfile.NamedTemporaryFile() as temp_file:
            assert folder_selector._validate_folder(temp_file.name) is False

    def test_clear_selection(self, folder_selector, temp_folder):
        folder_selector.set_folder(temp_folder)
        assert folder_selector.get_selected_folder() is not None
        
        folder_selector.clear_selection()
        assert folder_selector.get_selected_folder() is None
        assert folder_selector.folder_path.get() == ""

    def test_state_change_callback(self, parent_frame, mock_callback, temp_folder):
        folder_selector = FolderSelectorComponent(parent_frame, mock_callback)
        folder_selector.set_folder(temp_folder)
        
        # Callback should be called when folder changes
        mock_callback.assert_called_with(selected_folder=temp_folder)

    @patch('tkinter.filedialog.askdirectory')
    def test_browse_folder_success(self, mock_askdirectory, folder_selector, temp_folder):
        mock_askdirectory.return_value = temp_folder
        
        folder_selector._browse_folder()
        
        assert folder_selector.get_selected_folder() == temp_folder
        mock_askdirectory.assert_called_once()

    @patch('tkinter.filedialog.askdirectory')
    def test_browse_folder_cancel(self, mock_askdirectory, folder_selector):
        mock_askdirectory.return_value = ""  # User cancelled
        
        initial_folder = folder_selector.get_selected_folder()
        folder_selector._browse_folder()
        
        # Should not change current selection
        assert folder_selector.get_selected_folder() == initial_folder

    @patch('tkinter.filedialog.askdirectory')
    def test_browse_folder_invalid_selection(self, mock_askdirectory, folder_selector):
        mock_askdirectory.return_value = "/nonexistent/path"
        
        folder_selector._browse_folder()
        
        # Should not set invalid path
        assert folder_selector.get_selected_folder() != "/nonexistent/path"

    def test_error_handling(self, folder_selector):
        test_error = "Test error message"
        
        # Should not raise exception
        folder_selector.handle_error(test_error)
        
        # Status should show error
        status_text = folder_selector.status_label.cget("text")
        assert "Error" in status_text

    def test_status_updates(self, folder_selector):
        test_message = "Test status message"
        
        folder_selector._update_status(test_message, "blue")
        
        assert folder_selector.status_label.cget("text") == test_message
        # Color objects in tkinter need to be compared as strings
        assert str(folder_selector.status_label.cget("foreground")) == "blue"