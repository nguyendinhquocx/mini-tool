import pytest
import tkinter as tk
import sys
import os
import tempfile
from unittest.mock import patch

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ui.components.app_controller import AppController


class TestAppIntegration:
    @pytest.fixture
    def temp_folder_with_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with various types
            test_files = [
                ("document.txt", "Sample text content"),
                ("image.jpg", b"fake image data"),
                ("script.py", "print('Hello, World!')"),
                ("data.csv", "name,age\nJohn,30\nJane,25")
            ]
            
            for filename, content in test_files:
                file_path = os.path.join(temp_dir, filename)
                mode = 'wb' if isinstance(content, bytes) else 'w'
                with open(file_path, mode) as f:
                    f.write(content)
            
            # Create a subdirectory
            sub_dir = os.path.join(temp_dir, "subdirectory")
            os.makedirs(sub_dir)
            
            yield temp_dir

    @pytest.fixture
    def app_controller(self):
        controller = AppController()
        yield controller
        if controller.main_window.root:
            controller.destroy()

    def test_app_controller_initialization(self, app_controller):
        assert app_controller.main_window is not None
        assert app_controller.state_manager is not None
        assert app_controller.folder_selector is not None
        assert app_controller.file_preview is not None

    def test_folder_selection_updates_preview(self, app_controller, temp_folder_with_files):
        # Set folder through folder selector
        app_controller.set_initial_folder(temp_folder_with_files)
        
        # Allow time for UI updates and trigger state changes
        app_controller.main_window.root.update_idletasks()
        app_controller.main_window.root.update()
        
        # Check that file preview was updated
        files_data = app_controller.file_preview.get_files_data()
        assert len(files_data) > 0
        
        # Check that expected files are present
        file_names = [item["name"] for item in files_data]
        assert "document.txt" in file_names
        assert "script.py" in file_names
        assert "subdirectory" in file_names

    def test_state_management_integration(self, app_controller, temp_folder_with_files):
        # Set folder
        app_controller.set_initial_folder(temp_folder_with_files)
        
        # Check application state
        state = app_controller.get_current_state()
        assert state.selected_folder == temp_folder_with_files
        assert len(state.files_preview) > 0

    def test_component_communication(self, app_controller, temp_folder_with_files):
        # Folder selector should communicate with file preview via state manager
        folder_selector = app_controller.folder_selector
        file_preview = app_controller.file_preview
        
        # Initially no files
        assert len(file_preview.get_files_data()) == 0
        
        # Set folder through folder selector
        folder_selector.set_folder(temp_folder_with_files)
        
        # Allow UI update and trigger state changes
        app_controller.main_window.root.update_idletasks()
        app_controller.main_window.root.update()
        
        # File preview should now have files
        files_data = file_preview.get_files_data()
        assert len(files_data) > 0

    def test_error_handling_integration(self, app_controller):
        nonexistent_folder = "/nonexistent/folder/path"
        
        # Should handle invalid folder gracefully
        app_controller.set_initial_folder(nonexistent_folder)
        
        # Application should still be functional
        state = app_controller.get_current_state()
        assert state.selected_folder != nonexistent_folder

    def test_window_components_integration(self, app_controller):
        main_window = app_controller.main_window
        
        # Check that components are properly integrated
        assert "folder_selector" in main_window.components
        assert "file_preview" in main_window.components
        
        # Check that components are displayed
        content_frame = main_window.get_content_frame()
        assert content_frame.winfo_children()  # Should have child widgets

    def test_menu_functionality(self, app_controller):
        main_window = app_controller.main_window
        
        # Menu should exist
        menubar = main_window.root["menu"]
        assert menubar is not None

    def test_window_resizing(self, app_controller):
        main_window = app_controller.main_window
        
        # Test window can be resized
        initial_geometry = main_window.root.geometry()
        
        # Change size
        main_window.root.geometry("800x600")
        main_window.root.update()
        
        new_geometry = main_window.root.geometry()
        assert new_geometry != initial_geometry
        assert "800x600" in new_geometry

    @patch('sys.argv', ['main.py', '--folder', '/test/folder'])
    def test_command_line_integration(self, temp_folder_with_files):
        # This would test the main.py command line argument handling
        # Note: This is a simplified test - full CLI testing would require
        # more sophisticated mocking
        pass

    def test_multiple_folder_selections(self, app_controller, temp_folder_with_files):
        # Test changing folder selection multiple times
        folder_selector = app_controller.folder_selector
        file_preview = app_controller.file_preview
        
        # First folder
        folder_selector.set_folder(temp_folder_with_files)
        app_controller.main_window.root.update_idletasks()
        app_controller.main_window.root.update()
        first_files_count = len(file_preview.get_files_data())
        
        # Create another test folder
        with tempfile.TemporaryDirectory() as second_folder:
            # Add a single file to second folder
            test_file = os.path.join(second_folder, "single_file.txt")
            with open(test_file, 'w') as f:
                f.write("single file content")
            
            # Switch to second folder
            folder_selector.set_folder(second_folder)
            app_controller.main_window.root.update_idletasks()
            app_controller.main_window.root.update()
            second_files_count = len(file_preview.get_files_data())
            
            # Should show different number of files
            assert second_files_count != first_files_count
            assert second_files_count == 1  # Only one file in second folder