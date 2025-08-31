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
        assert file_preview.selection_count_label is not None
        assert file_preview.loading_label is not None
        assert file_preview.preview_data == []
        assert file_preview.selected_files == set()

    def test_initial_state(self, file_preview):
        assert len(file_preview.get_preview_data()) == 0
        assert "No folder selected" in file_preview.status_label.cget("text")

    def test_update_files_valid_folder(self, file_preview, temp_folder_with_files, mock_callback):
        file_preview.update_files(temp_folder_with_files)
        
        # Wait for debounced update to complete
        import time
        time.sleep(0.6)
        
        preview_data = file_preview.get_preview_data()
        assert len(preview_data) > 0
        
        # Should contain both files and folders
        file_names = [item.file_info.name for item in preview_data]
        assert "test1.txt" in file_names
        assert "test2.py" in file_names
        assert "document.pdf" in file_names
        assert "subfolder" in file_names

    def test_update_files_empty_folder(self, file_preview, empty_temp_folder):
        file_preview.update_files(empty_temp_folder)
        
        # Wait for debounced update to complete
        import time
        time.sleep(0.6)
        
        preview_data = file_preview.get_preview_data()
        assert len(preview_data) == 0

    def test_update_files_nonexistent_folder(self, file_preview):
        nonexistent_path = "/nonexistent/folder/path"
        file_preview.update_files(nonexistent_path)
        
        # Wait for debounced update
        import time
        time.sleep(0.6)
        
        # Should handle gracefully
        assert len(file_preview.get_preview_data()) == 0
        status_text = file_preview.status_label.cget("text")
        assert "Invalid folder path" in status_text

    def test_update_files_none_path(self, file_preview):
        file_preview.update_files(None)
        
        assert len(file_preview.get_preview_data()) == 0
        status_text = file_preview.status_label.cget("text")
        assert "No folder selected" in status_text

    def test_generate_rename_preview_functionality(self, file_preview, temp_folder_with_files):
        preview_data = file_preview._generate_rename_preview(temp_folder_with_files)
        
        assert len(preview_data) > 0
        
        # Check data structure
        for preview in preview_data:
            assert hasattr(preview, 'file_info')
            assert hasattr(preview, 'normalized_name')
            assert hasattr(preview, 'file_id')
            assert preview.file_info.file_type.value in ["File", "Folder"]

    def test_file_size_formatting(self):
        # Test FileInfo's _format_file_size method directly
        from core.models.file_info import FileInfo, FileType
        file_info = FileInfo("test", "test", "/test", FileType.FILE)
        
        assert file_info._format_file_size(500) == "500.0 B"
        assert file_info._format_file_size(1500) == "1.5 KB"
        assert file_info._format_file_size(1500000) == "1.4 MB"
        assert file_info._format_file_size(1500000000) == "1.4 GB"

    def test_tree_population(self, file_preview, temp_folder_with_files):
        # First generate preview data
        preview_data = file_preview._generate_rename_preview(temp_folder_with_files)
        
        # Then populate tree
        file_preview._populate_preview_tree(preview_data)
        
        # Check tree has items
        tree_items = file_preview.tree.get_children()
        assert len(tree_items) == len(preview_data)

    def test_clear_preview(self, file_preview, temp_folder_with_files):
        # First load some files
        file_preview.update_files(temp_folder_with_files)
        import time
        time.sleep(0.6)  # Wait for debounced update
        assert len(file_preview.get_preview_data()) > 0
        
        # Then clear
        file_preview._clear_preview()
        assert len(file_preview.get_preview_data()) == 0
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


class TestFilePreviewEnhancements:
    """Test enhanced functionality for Story 2.1"""
    
    @pytest.fixture
    def vietnamese_test_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create Vietnamese test files
            test_files = [
                "Tài liệu quan trọng.docx",
                "Báo cáo tháng 12.pdf", 
                "Ảnh gia đình.jpg",
                "Nhạc Việt Nam.mp3",
                "File with (special) chars!.txt"
            ]
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {filename}")
            yield temp_dir

    def test_two_column_layout_display(self, file_preview, vietnamese_test_folder):
        """Test AC: 1 - Two-column layout display"""
        file_preview.update_files(vietnamese_test_folder)
        
        # Wait for debounced update
        import time
        time.sleep(0.6)
        
        preview_data = file_preview.get_preview_data()
        assert len(preview_data) > 0
        
        # Check tree has correct columns
        columns = file_preview.tree["columns"]
        assert "current_name" in columns
        assert "new_name" in columns
        assert "status" in columns
        
        # Check tree items have both current and normalized names
        tree_items = file_preview.tree.get_children()
        assert len(tree_items) > 0
        
        for item_id in tree_items[:3]:  # Check first few items
            values = file_preview.tree.item(item_id)["values"]
            assert len(values) >= 3  # current_name, new_name, status
            current_name, new_name, status = values[0], values[1], values[2]
            assert current_name  # Should have current name
            assert new_name      # Should have normalized name
            assert status        # Should have status

    def test_unchanged_files_indication(self, file_preview, root_window, parent_frame, mock_callback):
        """Test AC: 2 - Files with no changes clearly indicated"""
        # Create fresh component for this test
        file_preview = FilePreviewComponent(parent_frame, mock_callback)
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files that won't change after normalization
            unchanged_files = ["test.txt", "document.pdf", "image.jpg"]
            for filename in unchanged_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write("test")
            
            file_preview.update_files(temp_dir)
            time.sleep(0.6)  # Wait for debounced update
            
            preview_data = file_preview.get_preview_data()
            
            # Check that files are marked as unchanged
            for preview in preview_data:
                if preview.file_info.name in unchanged_files:
                    assert preview.is_unchanged
                    # Status should indicate no changes
                    status_text = file_preview._get_status_text(preview)
                    assert "No changes" in status_text

    def test_conflict_detection_and_highlighting(self, parent_frame, mock_callback):
        """Test AC: 3 - Files with conflicts highlighted in red"""
        file_preview = FilePreviewComponent(parent_frame, mock_callback)
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files that will have same normalized name (conflict)
            conflict_files = ["Tài Liệu.txt", "tai lieu.txt", "TÀI LIỆU.txt"]
            for filename in conflict_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("test")
            
            file_preview.update_files(temp_dir)
            time.sleep(0.6)
            
            preview_data = file_preview.get_preview_data()
            
            # Should detect conflicts
            conflict_count = sum(1 for p in preview_data if p.has_conflict)
            assert conflict_count >= 2  # At least 2 files should have conflicts
            
            # Check conflict status text
            for preview in preview_data:
                if preview.has_conflict:
                    status_text = file_preview._get_status_text(preview)
                    assert "Conflict" in status_text

    def test_file_selection_toggle(self, file_preview, vietnamese_test_folder):
        """Test AC: 5 - User can toggle individual files on/off"""
        file_preview.update_files(vietnamese_test_folder)
        time.sleep(0.6)
        
        preview_data = file_preview.get_preview_data()
        assert len(preview_data) > 0
        
        # Initially all files should be selected
        selected_count = sum(1 for p in preview_data if p.is_selected)
        assert selected_count == len(preview_data)
        
        # Toggle first file off
        first_preview = preview_data[0]
        file_preview.toggle_file_selection(first_preview.file_id, False)
        
        # Check selection state changed
        updated_preview = next(p for p in file_preview.preview_data if p.file_id == first_preview.file_id)
        assert not updated_preview.is_selected
        assert first_preview.file_id not in file_preview.selected_files
        
        # Toggle back on
        file_preview.toggle_file_selection(first_preview.file_id, True)
        updated_preview = next(p for p in file_preview.preview_data if p.file_id == first_preview.file_id)
        assert updated_preview.is_selected
        assert first_preview.file_id in file_preview.selected_files

    def test_file_count_indicators(self, file_preview, vietnamese_test_folder):
        """Test AC: 6 - Clear visual indication of how many files will be affected"""
        file_preview.update_files(vietnamese_test_folder)
        time.sleep(0.6)
        
        preview_data = file_preview.get_preview_data()
        total_files = len(preview_data)
        
        # Check file count label
        count_text = file_preview.file_count_label.cget("text")
        assert str(total_files) in count_text
        assert "files)" in count_text
        
        # Check selection count label
        selection_text = file_preview.selection_count_label.cget("text")
        assert str(total_files) in selection_text
        assert "selected" in selection_text
        
        # Toggle some files off and check count updates
        if total_files > 1:
            first_preview = preview_data[0]
            file_preview.toggle_file_selection(first_preview.file_id, False)
            
            updated_selection_text = file_preview.selection_count_label.cget("text")
            assert str(total_files - 1) in updated_selection_text

    def test_large_file_set_performance(self, parent_frame, mock_callback):
        """Test AC: 7 - Preview loads quickly for folders with hundreds of files"""
        file_preview = FilePreviewComponent(parent_frame, mock_callback)
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create many test files
            file_count = 150
            for i in range(file_count):
                filename = f"test_file_{i:03d}.txt"
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w') as f:
                    f.write(f"Content {i}")
            
            import time
            start_time = time.time()
            
            file_preview.update_files(temp_dir)
            time.sleep(0.6)  # Wait for debounced update
            
            end_time = time.time()
            processing_time = end_time - start_time
            
            # Should process within reasonable time
            assert processing_time < 5.0  # 5 seconds max
            
            preview_data = file_preview.get_preview_data()
            assert len(preview_data) > 0

    def test_normalization_caching(self, file_preview, vietnamese_test_folder):
        """Test Vietnamese normalization caching for performance"""
        # Clear cache first
        file_preview.clear_caches()
        assert len(file_preview.normalization_cache) == 0
        
        # Process files to populate cache
        file_preview.update_files(vietnamese_test_folder)
        time.sleep(0.6)
        
        # Cache should have entries
        assert len(file_preview.normalization_cache) > 0
        
        # Test cached retrieval
        test_filename = "Tài liệu.docx"
        cached_result1 = file_preview._get_cached_normalized_name(test_filename)
        cached_result2 = file_preview._get_cached_normalized_name(test_filename)
        assert cached_result1 == cached_result2
        
        # Clear cache
        file_preview.clear_caches()
        assert len(file_preview.normalization_cache) == 0

    def test_debounced_updates(self, file_preview, vietnamese_test_folder):
        """Test AC: 4 - Debounced update mechanism to avoid excessive refreshes"""
        # Mock the callback to track calls
        callback_mock = Mock()
        file_preview.on_state_changed = callback_mock
        
        # Rapid successive calls should be debounced
        file_preview.update_files(vietnamese_test_folder)
        file_preview.update_files(vietnamese_test_folder)  
        file_preview.update_files(vietnamese_test_folder)
        
        # Wait for debounce delay
        time.sleep(0.6)
        
        # Should only process once after debounce delay
        assert file_preview.update_debounce_timer is not None
        
        # Final state should be correct
        preview_data = file_preview.get_preview_data()
        assert len(preview_data) > 0

    def test_loading_state_display(self, file_preview, vietnamese_test_folder):
        """Test loading indicator functionality"""
        # Should show loading initially
        file_preview.show_loading_state(True)
        loading_text = file_preview.loading_label.cget("text")
        assert "Loading" in loading_text
        
        # Should hide loading when done
        file_preview.show_loading_state(False)
        loading_text = file_preview.loading_label.cget("text")
        assert loading_text == ""