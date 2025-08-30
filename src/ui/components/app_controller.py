import tkinter as tk
from tkinter import ttk
from typing import Optional
from ..main_window import MainWindow, ApplicationState
from .folder_selector import FolderSelectorComponent
from .file_preview import FilePreviewComponent


class AppController:
    def __init__(self):
        self.main_window = MainWindow()
        self.state_manager = self.main_window.get_state_manager()
        
        # Components
        self.folder_selector: Optional[FolderSelectorComponent] = None
        self.file_preview: Optional[FilePreviewComponent] = None
        
        # Guard against circular updates
        self._updating_file_preview = False
        
        self._setup_components()
        self._setup_observers()

    def _setup_components(self):
        content_frame = self.main_window.get_content_frame()
        
        # Create folder selector
        self.folder_selector = FolderSelectorComponent(
            content_frame, 
            self._on_component_state_changed
        )
        
        # Create file preview
        self.file_preview = FilePreviewComponent(
            content_frame,
            self._on_component_state_changed
        )
        
        # Register components with main window
        self.main_window.add_component("folder_selector", self.folder_selector)
        self.main_window.add_component("file_preview", self.file_preview)

    def _setup_observers(self):
        # Subscribe to state changes
        self.state_manager.subscribe(self._on_state_changed)

    def _on_component_state_changed(self, **kwargs):
        # Update application state based on component changes
        self.state_manager.update_state(**kwargs)

    def _on_state_changed(self, state: ApplicationState):
        # Handle state changes and update components accordingly
        try:
            # Update file preview when folder selection changes
            # Guard against circular updates
            if (state.selected_folder and self.file_preview and 
                not self._updating_file_preview):
                self._updating_file_preview = True
                try:
                    self.file_preview.update_files(state.selected_folder)
                finally:
                    self._updating_file_preview = False
                    
        except Exception as e:
            self._updating_file_preview = False
            self._handle_error(f"State update error: {str(e)}")

    def _handle_error(self, error: str):
        if self.folder_selector:
            self.folder_selector.handle_error(error)

    def set_initial_folder(self, folder_path: str):
        if self.folder_selector:
            self.folder_selector.set_folder(folder_path)

    def get_current_state(self) -> ApplicationState:
        return self.state_manager.state

    def run(self):
        self.main_window.run()

    def destroy(self):
        self.main_window.destroy()