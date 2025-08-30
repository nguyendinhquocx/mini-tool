import pytest
import tkinter as tk
from tkinter import ttk
import os
import sys
import tempfile
from unittest.mock import Mock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ui.components.file_preview import FilePreviewComponent


class TestFilePreviewComponent:
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
    def file_preview(self, parent_frame, mock_callback):
        return FilePreviewComponent(parent_frame, mock_callback)

    @pytest.fixture
    def temp_folder_with_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = ["test1.txt", "test2.py", "document.pdf"]
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(f"Test content for {filename}")
            
            # Create test subdirectory
            sub_dir = os.path.join(temp_dir, "subfolder")
            os.makedirs(sub_dir)
            
            yield temp_dir

    @pytest.fixture
    def empty_temp_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_component_initialization(self, file_preview):
        assert file_preview.frame is not None
        assert file_preview.tree is not None
        assert file_preview.status_label is not None
        assert file_preview.file_count_label is not None
        assert file_preview.files_data == []

    def test_initial_state(self, file_preview):
        assert len(file_preview.get_files_data()) == 0
        assert "No folder selected" in file_preview.status_label.cget("text")

    def test_update_files_valid_folder(self, file_preview, temp_folder_with_files, mock_callback):
        file_preview.update_files(temp_folder_with_files)
        
        files_data = file_preview.get_files_data()
        assert len(files_data) > 0
        
        # Should contain both files and folders
        file_names = [item["name"] for item in files_data]
        assert "test1.txt" in file_names
        assert "test2.py" in file_names
        assert "document.pdf" in file_names
        assert "subfolder" in file_names
        
        # Should call state callback
        mock_callback.assert_called_once()

    def test_update_files_empty_folder(self, file_preview, empty_temp_folder):
        file_preview.update_files(empty_temp_folder)
        
        files_data = file_preview.get_files_data()
        assert len(files_data) == 0

    def test_update_files_nonexistent_folder(self, file_preview):
        nonexistent_path = "/nonexistent/folder/path"
        file_preview.update_files(nonexistent_path)
        
        # Should handle gracefully
        assert len(file_preview.get_files_data()) == 0
        status_text = file_preview.status_label.cget("text")
        assert "Invalid folder path" in status_text

    def test_update_files_none_path(self, file_preview):
        file_preview.update_files(None)
        
        assert len(file_preview.get_files_data()) == 0
        status_text = file_preview.status_label.cget("text")
        assert "Invalid folder path" in status_text

    def test_scan_folder_functionality(self, file_preview, temp_folder_with_files):
        files_data = file_preview._scan_folder(temp_folder_with_files)
        
        assert len(files_data) > 0
        
        # Check data structure
        for file_info in files_data:
            assert "name" in file_info
            assert "original_name" in file_info
            assert "path" in file_info
            assert "type" in file_info
            assert "is_file" in file_info
            assert file_info["type"] in ["File", "Folder"]

    def test_file_size_formatting(self, file_preview):
        assert file_preview._format_file_size(500) == "500.0 B"
        assert file_preview._format_file_size(1500) == "1.5 KB"
        assert file_preview._format_file_size(1500000) == "1.4 MB"
        assert file_preview._format_file_size(1500000000) == "1.4 GB"

    def test_tree_population(self, file_preview, temp_folder_with_files):
        # First scan folder
        files_data = file_preview._scan_folder(temp_folder_with_files)
        
        # Then populate tree
        file_preview._populate_tree(files_data)
        
        # Check tree has items
        tree_items = file_preview.tree.get_children()
        assert len(tree_items) == len(files_data)

    def test_clear_preview(self, file_preview, temp_folder_with_files):
        # First load some files
        file_preview.update_files(temp_folder_with_files)
        assert len(file_preview.get_files_data()) > 0
        
        # Then clear
        file_preview._clear_preview()
        assert len(file_preview.get_files_data()) == 0
        assert len(file_preview.tree.get_children()) == 0

    def test_file_count_display(self, file_preview, temp_folder_with_files):
        file_preview.update_files(temp_folder_with_files)
        
        count_text = file_preview.file_count_label.cget("text")
        assert "items)" in count_text
        # Should show number of items in parentheses

    def test_status_updates(self, file_preview):
        test_message = "Test status"
        test_color = "red"
        
        file_preview._update_status(test_message, test_color)
        
        assert file_preview.status_label.cget("text") == test_message
        # Color objects in tkinter need to be compared as strings
        assert str(file_preview.status_label.cget("foreground")) == test_color

    def test_error_handling(self, file_preview):
        test_error = "Test error message"
        
        # Should not raise exception
        file_preview.handle_error(test_error)
        
        # Should update status with error
        status_text = file_preview.status_label.cget("text")
        assert "Error" in status_text