import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
from typing import Callable, Optional

from ...core.services.config_service import get_config_service


class FolderSelectorComponent:
    def __init__(self, parent: ttk.Widget, state_changed_callback: Callable):
        self.parent = parent
        self.on_state_changed = state_changed_callback
        self.folder_path = tk.StringVar()
        self.folder_path.trace('w', self._on_folder_changed)
        self.config_service = get_config_service()
        self.setup_ui()
        
        # Track last selection method for UI feedback
        self.last_selection_method = "none"  # "browse", "drag_drop", or "none"

    def setup_ui(self):
        # Container frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Configure grid
        self.frame.columnconfigure(1, weight=1)
        
        # Label
        ttk.Label(self.frame, text="Folder:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5)
        )
        
        # Entry field for folder path
        self.path_entry = ttk.Entry(
            self.frame, 
            textvariable=self.folder_path, 
            state="readonly"
        )
        self.path_entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        
        # Browse button
        self.browse_button = ttk.Button(
            self.frame, 
            text="Browse", 
            command=self._browse_folder,
            width=10
        )
        self.browse_button.grid(row=0, column=2)

        # Status label for feedback
        self.status_label = ttk.Label(self.frame, text="", foreground="gray")
        self.status_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(5, 0))

    def _browse_folder(self):
        try:
            folder_path = filedialog.askdirectory(
                title="Select folder containing files to rename"
            )
            
            if folder_path:
                if self._validate_folder(folder_path):
                    self.last_selection_method = "browse"
                    self.folder_path.set(folder_path)
                    self._update_status(f"Browsed: {os.path.basename(folder_path)}", "green")
                    
                    # Add to recent folders
                    try:
                        self.config_service.add_recent_folder(folder_path)
                    except Exception as e:
                        print(f"Error adding recent folder: {e}")
                else:
                    self._update_status("Selected folder is not accessible", "red")
        except Exception as e:
            self.handle_error(f"Error selecting folder: {str(e)}")

    def _validate_folder(self, folder_path: str) -> bool:
        try:
            if not os.path.exists(folder_path):
                return False
            
            if not os.path.isdir(folder_path):
                return False
                
            if not os.access(folder_path, os.R_OK):
                return False
                
            return True
        except Exception:
            return False

    def _on_folder_changed(self, *args):
        folder_path = self.folder_path.get()
        if folder_path and self.on_state_changed:
            self.on_state_changed(selected_folder=folder_path)

    def _update_status(self, message: str, color: str = "gray"):
        self.status_label.config(text=message, foreground=color)

    def get_selected_folder(self) -> Optional[str]:
        path = self.folder_path.get()
        return path if path else None

    def set_folder(self, folder_path: str, method: str = "external"):
        """
        Set folder programmatically (from drag-drop or other sources)
        
        Args:
            folder_path: Path to set
            method: Selection method ("drag_drop", "browse", "external")
        """
        if self._validate_folder(folder_path):
            self.last_selection_method = method
            self.folder_path.set(folder_path)
            
            # Add to recent folders for any valid method
            try:
                self.config_service.add_recent_folder(folder_path)
            except Exception as e:
                print(f"Error adding recent folder: {e}")
            
            # Update status based on selection method
            if method == "drag_drop":
                self._update_status(f"Dropped: {os.path.basename(folder_path)} 🎯", "green")
            elif method == "browse":
                self._update_status(f"Browsed: {os.path.basename(folder_path)}", "green")
            else:
                self._update_status(f"Set: {os.path.basename(folder_path)}", "green")
        else:
            self.handle_error(f"Invalid folder path: {folder_path}")
    
    def set_folder_from_drag_drop(self, folder_path: str):
        """
        Convenience method for drag-drop integration
        """
        self.set_folder(folder_path, "drag_drop")

    def clear_selection(self):
        self.folder_path.set("")
        self.last_selection_method = "none"
        self._update_status("No folder selected", "gray")

    def get_selection_method(self) -> str:
        """
        Get the method used for current selection
        
        Returns:
            Selection method: "browse", "drag_drop", "external", or "none"
        """
        return self.last_selection_method
    
    def is_drag_drop_selection(self) -> bool:
        """
        Check if current selection was made via drag-drop
        """
        return self.last_selection_method == "drag_drop"
    
    def handle_error(self, error: str):
        self._update_status(f"Error: {error}", "red")
        messagebox.showerror("Folder Selection Error", error)