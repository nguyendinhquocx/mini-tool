import tkinter as tk
from tkinter import ttk
import os
from typing import Callable, List, Dict, Any
from .error_handler import ErrorHandler

# File preview constants
DEFAULT_COLUMN_WIDTHS = {
    "name": 300,
    "type": 80, 
    "size": 100
}
MIN_COLUMN_WIDTHS = {
    "name": 200,
    "type": 60,
    "size": 80
}
FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']


class FilePreviewComponent:
    def __init__(self, parent: ttk.Widget, state_changed_callback: Callable):
        self.parent = parent
        self.on_state_changed = state_changed_callback
        self.files_data = []
        self.setup_ui()

    def setup_ui(self):
        # Container frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid weights
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        
        # Header frame
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Label(header_frame, text="Files in Selected Folder:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        self.file_count_label = ttk.Label(header_frame, text="", foreground="gray")
        self.file_count_label.pack(side=tk.RIGHT)
        
        # Treeview frame with scrollbars
        tree_frame = ttk.Frame(self.frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        # Create Treeview
        self.tree = ttk.Treeview(tree_frame, columns=("type", "size"), show="tree headings")
        
        # Configure columns
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Size")
        
        self.tree.column("#0", width=DEFAULT_COLUMN_WIDTHS["name"], minwidth=MIN_COLUMN_WIDTHS["name"])
        self.tree.column("type", width=DEFAULT_COLUMN_WIDTHS["type"], minwidth=MIN_COLUMN_WIDTHS["type"])
        self.tree.column("size", width=DEFAULT_COLUMN_WIDTHS["size"], minwidth=MIN_COLUMN_WIDTHS["size"])
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Status frame
        status_frame = ttk.Frame(self.frame)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        
        self.status_label = ttk.Label(status_frame, text="No folder selected", foreground="gray")
        self.status_label.pack(side=tk.LEFT)

    def update_files(self, folder_path: str):
        try:
            if not folder_path or not os.path.exists(folder_path):
                self._clear_preview()
                self._update_status("Invalid folder path", "red")
                return
            
            if not os.access(folder_path, os.R_OK):
                self._clear_preview()
                self._update_status("Cannot access folder (permission denied)", "red")
                return
            
            # Scan folder contents
            files_data = self._scan_folder(folder_path)
            self.files_data = files_data
            
            # Update UI
            self._populate_tree(files_data)
            self._update_file_count(len(files_data))
            self._update_status(f"Loaded {len(files_data)} items", "green")
            
            # Notify state change
            if self.on_state_changed:
                self.on_state_changed(files_preview=files_data)
                
        except Exception as e:
            self.handle_error(f"Error loading files: {str(e)}")

    def _scan_folder(self, folder_path: str) -> List[Dict[str, Any]]:
        files_data = []
        
        try:
            items = os.listdir(folder_path)
            items.sort()  # Sort alphabetically
            
            for item in items:
                item_path = os.path.join(folder_path, item)
                
                try:
                    is_file = os.path.isfile(item_path)
                    is_dir = os.path.isdir(item_path)
                    
                    if is_file or is_dir:
                        file_info = {
                            "name": item,
                            "original_name": item,
                            "path": item_path,
                            "type": "File" if is_file else "Folder",
                            "size": self._get_file_size(item_path) if is_file else "",
                            "is_file": is_file
                        }
                        files_data.append(file_info)
                        
                except (OSError, IOError):
                    # Skip items that can't be accessed
                    continue
                    
        except (OSError, IOError) as e:
            raise Exception(f"Cannot read folder contents: {str(e)}")
        
        return files_data

    def _get_file_size(self, file_path: str) -> str:
        try:
            size = os.path.getsize(file_path)
            return self._format_file_size(size)
        except (OSError, IOError):
            return "Unknown"

    def _format_file_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in FILE_SIZE_UNITS[:-1]:  # All except last
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} {FILE_SIZE_UNITS[-1]}"  # TB

    def _populate_tree(self, files_data: List[Dict[str, Any]]):
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        
        # Add files and folders
        for file_info in files_data:
            item_type = file_info["type"]
            icon = "📁" if item_type == "Folder" else "📄"
            display_name = f"{icon} {file_info['name']}"
            
            self.tree.insert(
                "", 
                tk.END, 
                text=display_name,
                values=(item_type, file_info["size"])
            )

    def _clear_preview(self):
        self.tree.delete(*self.tree.get_children())
        self.files_data = []
        self._update_file_count(0)

    def _update_file_count(self, count: int):
        self.file_count_label.config(text=f"({count} items)")

    def _update_status(self, message: str, color: str = "gray"):
        self.status_label.config(text=message, foreground=color)

    def get_files_data(self) -> List[Dict[str, Any]]:
        return self.files_data.copy()

    def handle_error(self, error: str):
        """Handle errors with consistent UI feedback"""
        self._update_status(f"Error: {error}", "red")
        self._clear_preview()
        # Use centralized error handler for logging
        ErrorHandler.handle_ui_error(
            Exception(error), 
            "File Preview", 
            show_dialog=False  # Status already shown in UI
        )