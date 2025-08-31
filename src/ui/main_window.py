import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import TkinterDnD
from typing import Optional, Callable, Any, List
from dataclasses import dataclass, field
from enum import Enum

# UI Constants
DEFAULT_WINDOW_WIDTH = 600
DEFAULT_WINDOW_HEIGHT = 500
MINIMUM_WINDOW_WIDTH = 400
MINIMUM_WINDOW_HEIGHT = 300
DEFAULT_FONT = ('Arial', 10)
TITLE_FONT = ('Arial', 14, 'bold')
MAIN_PADDING = "10"


class AppState(Enum):
    IDLE = "idle"
    LOADING = "loading"
    ERROR = "error"


@dataclass
class ApplicationState:
    """Application state container with type-safe defaults"""
    current_state: AppState = AppState.IDLE
    selected_folder: Optional[str] = None
    files_preview: List[Any] = field(default_factory=list)
    current_operation_id: Optional[str] = None
    operation_in_progress: bool = False
    progress_percentage: float = 0.0
    current_file_being_processed: Optional[str] = None
    last_operation_result: Optional[Any] = None
    
    # Undo State Management
    last_operation_id: Optional[str] = None
    can_undo_last_operation: bool = False
    undo_button_tooltip: str = "No operation to undo"
    undo_disabled_reason: Optional[str] = None
    files_modified_externally: List[str] = field(default_factory=list)
    
    # Drag-Drop State
    is_drag_active: bool = False
    drag_drop_valid: bool = False
    pending_folder_drop: Optional[str] = None


class StateManager:
    def __init__(self):
        self.state = ApplicationState()
        self._observers = []

    def subscribe(self, observer: Callable[[ApplicationState], None]):
        self._observers.append(observer)

    def update_state(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self._notify_observers()

    def _notify_observers(self):
        for observer in self._observers:
            observer(self.state)


class MainWindow:
    def __init__(self):
        self.root = None
        self.state_manager = StateManager()
        self.components = {}
        self.drag_drop_handler = None
        self._setup_window()
        self._setup_layout()
        self._create_menu()
        self._setup_drag_drop_handling()

    def _setup_window(self):
        # Initialize TkinterDnD before creating Tk root
        self.root = TkinterDnD.Tk()
        self.root.title("File Rename Tool")
        self.root.minsize(MINIMUM_WINDOW_WIDTH, MINIMUM_WINDOW_HEIGHT)
        
        # Center window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - DEFAULT_WINDOW_WIDTH) // 2
        y = (screen_height - DEFAULT_WINDOW_HEIGHT) // 2
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}+{x}+{y}")

        # Configure style
        self.style = ttk.Style()
        self.style.configure('TButton', font=DEFAULT_FONT)
        self.style.configure('TLabel', font=DEFAULT_FONT)
        self.style.configure('TEntry', font=DEFAULT_FONT)

    def _setup_layout(self):
        # Main container with padding
        self.main_frame = ttk.Frame(self.root, padding=MAIN_PADDING)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid weights for resizing
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        # Title frame
        self.title_frame = ttk.Frame(self.main_frame)
        self.title_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        title_label = ttk.Label(
            self.title_frame, 
            text="File Rename Tool", 
            font=TITLE_FONT
        )
        title_label.pack()

        # Content frame for components
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky="nsew")
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)
        
        # Action buttons frame
        self.action_frame = ttk.Frame(self.main_frame)
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.action_frame.columnconfigure(0, weight=1)

    def _create_menu(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        # File menu
        file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Exit", command=self._on_exit, accelerator="Ctrl+Q")

        # Edit menu
        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help menu
        help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)

        # Bind keyboard shortcuts
        self.root.bind('<Control-q>', lambda e: self._on_exit())
    
    def _setup_drag_drop_handling(self):
        """Configure window to accept drag-and-drop operations"""
        try:
            from .components.drag_drop_handler import DragDropHandler
            from ..core.services.validation_service import get_drag_drop_validator
            
            # Get specialized drag-drop validator
            drag_validator = get_drag_drop_validator()
            
            # Create drag-drop handler for main content frame
            self.drag_drop_handler = DragDropHandler(
                target_widget=self.content_frame,
                on_folder_dropped=self.handle_folder_drop,
                validation_callback=self._validate_dropped_folder,
                drag_drop_validator=drag_validator
            )
            
            # Update state to indicate drag-drop is ready
            self.state_manager.update_state(is_drag_active=False)
            
        except ImportError as e:
            print(f"Warning: Drag-drop functionality not available: {e}")
            self.drag_drop_handler = None
        except Exception as e:
            print(f"Error setting up drag-drop: {e}")
            self.drag_drop_handler = None
    
    def handle_folder_drop(self, folder_path: str):
        """Handle successful folder drop"""
        try:
            # Update application state
            self.state_manager.update_state(
                selected_folder=folder_path,
                pending_folder_drop=None,
                is_drag_active=False,
                drag_drop_valid=False
            )
            
            # If folder selector component exists, update it
            if 'folder_selector' in self.components:
                folder_selector = self.components['folder_selector']
                if hasattr(folder_selector, 'set_folder_from_drag_drop'):
                    folder_selector.set_folder_from_drag_drop(folder_path)
                elif hasattr(folder_selector, 'set_folder'):
                    folder_selector.set_folder(folder_path, "drag_drop")
            
            # Trigger file list refresh if file preview component exists
            self._refresh_file_list_after_drop(folder_path)
                    
        except Exception as e:
            print(f"Error handling folder drop: {e}")
    
    def _refresh_file_list_after_drop(self, folder_path: str):
        """Trigger file list refresh after successful folder drop"""
        try:
            # If file preview component exists, refresh it
            if 'file_preview' in self.components:
                file_preview = self.components['file_preview']
                if hasattr(file_preview, 'refresh_file_list'):
                    file_preview.refresh_file_list()
                elif hasattr(file_preview, 'scan_folder'):
                    file_preview.scan_folder(folder_path)
            
            # If app controller exists, notify it
            if 'app_controller' in self.components:
                app_controller = self.components['app_controller']
                if hasattr(app_controller, 'on_folder_selected'):
                    app_controller.on_folder_selected(folder_path)
                    
        except Exception as e:
            print(f"Error refreshing file list after drop: {e}")
    
    def _validate_dropped_folder(self, folder_path: str) -> bool:
        """Validate dropped folder before processing"""
        try:
            import os
            
            # Basic validation
            if not folder_path or not os.path.exists(folder_path):
                return False
            
            if not os.path.isdir(folder_path):
                return False
            
            if not os.access(folder_path, os.R_OK):
                return False
            
            # Update drag state during validation
            self.state_manager.update_state(
                pending_folder_drop=folder_path,
                drag_drop_valid=True
            )
            
            return True
            
        except Exception as e:
            print(f"Error validating dropped folder: {e}")
            self.state_manager.update_state(drag_drop_valid=False)
            return False

    def _on_exit(self):
        self.root.quit()
        self.root.destroy()

    def _show_about(self):
        from tkinter import messagebox
        messagebox.showinfo(
            "About", 
            "File Rename Tool v2.0\n\nA desktop application for batch file renaming."
        )

    def add_component(self, name: str, component):
        self.components[name] = component

    def get_content_frame(self):
        return self.content_frame
    
    def get_action_frame(self):
        return self.action_frame

    def get_state_manager(self):
        return self.state_manager

    def run(self):
        if self.root:
            self.root.mainloop()

    def destroy(self):
        if self.drag_drop_handler:
            self.drag_drop_handler.destroy()
        if self.root:
            self.root.destroy()