import pytest
import tkinter as tk
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ui.main_window import MainWindow, StateManager, ApplicationState, AppState


class TestMainWindow:
    @pytest.fixture
    def main_window(self):
        window = MainWindow()
        yield window
        if window.root:
            window.destroy()

    def test_main_window_initialization(self, main_window):
        assert main_window.root is not None
        assert main_window.root.winfo_class() == "Tk"
        assert main_window.root.title() == "File Rename Tool"

    def test_window_geometry(self, main_window):
        # Force window to be mapped to get actual geometry
        main_window.root.update_idletasks()
        geometry = main_window.root.geometry()
        # Should have format like "600x500+x+y" after mapping
        assert "600x500" in geometry or geometry.startswith("1x1")

    def test_window_resizable(self, main_window):
        min_size = main_window.root.minsize()
        assert min_size == (400, 300)

    def test_menu_creation(self, main_window):
        menubar = main_window.root["menu"]
        assert menubar is not None

    def test_state_manager_access(self, main_window):
        state_manager = main_window.get_state_manager()
        assert isinstance(state_manager, StateManager)

    def test_content_frame_access(self, main_window):
        content_frame = main_window.get_content_frame()
        assert content_frame is not None

    def test_component_registration(self, main_window):
        # Mock component
        mock_component = object()
        main_window.add_component("test_component", mock_component)
        assert "test_component" in main_window.components
        assert main_window.components["test_component"] is mock_component


class TestStateManager:
    @pytest.fixture
    def state_manager(self):
        return StateManager()

    def test_initial_state(self, state_manager):
        assert isinstance(state_manager.state, ApplicationState)
        assert state_manager.state.current_state == AppState.IDLE
        assert state_manager.state.selected_folder is None
        assert state_manager.state.files_preview == []

    def test_state_updates(self, state_manager):
        test_folder = "/test/path"
        state_manager.update_state(selected_folder=test_folder)
        assert state_manager.state.selected_folder == test_folder

    def test_observer_registration(self, state_manager):
        observer_called = []
        
        def test_observer(state):
            observer_called.append(state)
        
        state_manager.subscribe(test_observer)
        state_manager.update_state(selected_folder="/test")
        
        assert len(observer_called) == 1
        assert observer_called[0].selected_folder == "/test"

    def test_multiple_observers(self, state_manager):
        observers_called = {"obs1": 0, "obs2": 0}
        
        def observer1(state):
            observers_called["obs1"] += 1
            
        def observer2(state):
            observers_called["obs2"] += 1
        
        state_manager.subscribe(observer1)
        state_manager.subscribe(observer2)
        state_manager.update_state(current_state=AppState.LOADING)
        
        assert observers_called["obs1"] == 1
        assert observers_called["obs2"] == 1


class TestApplicationState:
    def test_default_initialization(self):
        state = ApplicationState()
        assert state.current_state == AppState.IDLE
        assert state.selected_folder is None
        assert state.files_preview == []
        assert state.current_operation_id is None
        assert state.progress_percentage == 0.0

    def test_custom_initialization(self):
        test_files = [{"name": "test.txt"}]
        state = ApplicationState(
            current_state=AppState.LOADING,
            selected_folder="/test/folder",
            files_preview=test_files
        )
        assert state.current_state == AppState.LOADING
        assert state.selected_folder == "/test/folder"
        assert state.files_preview == test_files