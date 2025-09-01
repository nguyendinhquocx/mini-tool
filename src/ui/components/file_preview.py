import tkinter as tk
from tkinter import ttk
import os
import threading
import time
from typing import Callable, List, Dict, Any, Set, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Core imports
try:
    from ...core.models.file_info import RenamePreview, FilePreviewState, FileInfo, FileType
    from ...core.services.normalize_service import VietnameseNormalizer
except ImportError:
    # Fallback for test environment
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from core.models.file_info import RenamePreview, FilePreviewState, FileInfo, FileType
    from core.services.normalize_service import VietnameseNormalizer

from .error_handler import ErrorHandler

# File preview constants for two-column layout
DEFAULT_COLUMN_WIDTHS = {
    "checkbox": 30,
    "current_name": 300,
    "new_name": 300,
    "status": 120
}
MIN_COLUMN_WIDTHS = {
    "checkbox": 30,
    "current_name": 200,
    "new_name": 200,
    "status": 80
}

# Row styling colors
UNCHANGED_COLOR = "#E0E0E0"  # Light gray for unchanged files
CONFLICT_COLOR = "#FFCCCC"    # Light red for conflicts
SELECTED_COLOR = "#CCE5FF"    # Light blue for selected files
DEFAULT_COLOR = "#FFFFFF"     # White for normal files

# Performance constants
MAX_VISIBLE_ITEMS = 1000  # Limit visible items for large directories
LAZY_LOAD_BATCH_SIZE = 100  # Process files in batches
DEBOUNCE_DELAY_MS = 500  # Milliseconds to wait before updating
CACHE_SIZE_LIMIT = 10000  # Max cache entries before cleanup
CACHE_CLEANUP_SIZE = 1000  # Number of entries to remove during cleanup


class FilePreviewComponent:
    def __init__(self, parent: ttk.Widget, state_changed_callback: Callable):
        self.parent = parent
        self.on_state_changed = state_changed_callback
        
        # Enhanced data structures for two-column preview
        self.preview_data: List[RenamePreview] = []
        self.selected_files: Set[str] = set()
        self.preview_state = FilePreviewState()
        self.normalizer = VietnameseNormalizer()
        
        # UI state
        self.folder_path: Optional[str] = None
        
        # Debounce mechanism for automatic updates
        self.update_debounce_timer: Optional[threading.Timer] = None
        self.debounce_delay = DEBOUNCE_DELAY_MS / 1000.0  # Convert to seconds
        
        # Performance optimization settings
        self.max_visible_items = MAX_VISIBLE_ITEMS
        self.lazy_load_batch_size = LAZY_LOAD_BATCH_SIZE
        self.normalization_cache = {}  # Cache for Vietnamese normalization results
        
        self.setup_ui()

    def setup_ui(self):
        # Container frame
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid weights
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        
        # Header frame with file count and selection info
        self.setup_header_frame()
        
        # Main preview frame with two-column layout
        self.setup_preview_frame()
        
        # Status frame with operation summary
        self.setup_status_frame()
    
    def setup_header_frame(self):
        """Setup header with title and file count indicators"""
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Label(header_frame, text="File Rename Preview:", font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        # File count and selection indicators
        count_frame = ttk.Frame(header_frame)
        count_frame.pack(side=tk.RIGHT)
        
        self.file_count_label = ttk.Label(count_frame, text="", foreground="gray")
        self.file_count_label.pack(side=tk.RIGHT, padx=(0, 10))
        
        self.selection_count_label = ttk.Label(count_frame, text="", foreground="blue")
        self.selection_count_label.pack(side=tk.RIGHT, padx=(0, 10))
    
    def setup_preview_frame(self):
        """Setup main preview frame with two-column TreeView"""
        tree_frame = ttk.Frame(self.frame)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        # Create enhanced Treeview with four columns
        columns = ("current_name", "new_name", "status")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="tree headings")
        
        # Configure column headers
        self.tree.heading("#0", text="☑")  # Checkbox column
        self.tree.heading("current_name", text="Current Name")
        self.tree.heading("new_name", text="New Name")
        self.tree.heading("status", text="Status")
        
        # Configure column widths
        self.tree.column("#0", width=DEFAULT_COLUMN_WIDTHS["checkbox"], minwidth=MIN_COLUMN_WIDTHS["checkbox"])
        self.tree.column("current_name", width=DEFAULT_COLUMN_WIDTHS["current_name"], minwidth=MIN_COLUMN_WIDTHS["current_name"])
        self.tree.column("new_name", width=DEFAULT_COLUMN_WIDTHS["new_name"], minwidth=MIN_COLUMN_WIDTHS["new_name"])
        self.tree.column("status", width=DEFAULT_COLUMN_WIDTHS["status"], minwidth=MIN_COLUMN_WIDTHS["status"])
        
        # Bind events for file selection toggle
        self.tree.bind("<Button-1>", self.on_tree_click)
        self.tree.bind("<space>", self.on_space_pressed)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
    
    def setup_status_frame(self):
        """Setup status frame with operation summary"""
        status_frame = ttk.Frame(self.frame)
        status_frame.grid(row=2, column=0, sticky="ew", pady=(5, 0))
        
        self.status_label = ttk.Label(status_frame, text="No folder selected", foreground="gray")
        self.status_label.pack(side=tk.LEFT)
        
        # Loading indicator
        self.loading_label = ttk.Label(status_frame, text="", foreground="blue")
        self.loading_label.pack(side=tk.RIGHT)

    def update_files(self, folder_path: str):
        """Update preview with files from selected folder (immediate, no debounce)"""
        # Cancel any existing debounce timer
        if self.update_debounce_timer:
            self.update_debounce_timer.cancel()
        
        if not folder_path:
            self._clear_preview()
            self._update_status("No folder selected", "gray")
            return
        
        # Show immediate loading state FIRST
        self.show_loading_state(True)
        self._update_status("Loading preview...", "blue")
        
        # Force UI update before processing
        self.parent.update_idletasks()
        
        # Start processing immediately in background thread (no debounce delay)
        def immediate_background_process():
            try:
                # Short delay to ensure UI has updated
                import time
                time.sleep(0.05)  # 50ms for UI to show loading state
                
                self._debounced_update_files(folder_path)
            except Exception as e:
                self.parent.after(0, self._handle_error_thread_safe, f"Error in immediate processing: {str(e)}")
        
        # Start immediately
        import threading
        process_thread = threading.Thread(target=immediate_background_process, daemon=True)
        process_thread.start()
    
    def _debounced_update_files(self, folder_path: str):
        """Actual update implementation called after debounce delay"""
        try:
            # Validate folder path
            if not self._validate_folder_path(folder_path):
                return
            
            self.folder_path = folder_path
            
            # Show immediate feedback in UI thread
            self.parent.after(0, self._thread_safe_update_status, "Scanning folder...", "blue")
            
            # Generate rename preview data (in background thread)
            # Use threading to prevent blocking
            def background_scan():
                try:
                    # Add timeout safety for large directories
                    import signal
                    import time
                    
                    start_time = time.time()
                    preview_data = self._generate_rename_preview(folder_path)
                    process_time = time.time() - start_time
                    
                    # Update UI in main thread
                    self.parent.after(0, self._update_ui_with_preview, preview_data)
                    
                    # Log processing time for debugging
                    if process_time > 1.0:  # Log if takes more than 1 second
                        self.parent.after(0, self._thread_safe_update_status, 
                                        f"Processed {len(preview_data)} files in {process_time:.1f}s", "green")
                        
                except MemoryError:
                    self.parent.after(0, self._handle_error_thread_safe, "Directory too large - out of memory")
                except PermissionError:
                    self.parent.after(0, self._handle_error_thread_safe, "Permission denied accessing folder")
                except OSError as e:
                    self.parent.after(0, self._handle_error_thread_safe, f"System error: {str(e)[:100]}")
                except Exception as e:
                    self.parent.after(0, self._handle_error_thread_safe, f"Error generating preview: {str(e)[:100]}")
            
            # Run in background thread
            import threading
            scan_thread = threading.Thread(target=background_scan, daemon=True)
            scan_thread.start()
                
        except Exception as e:
            self.parent.after(0, self._handle_error_thread_safe, f"Error generating preview: {str(e)}")
    
    def _validate_folder_path(self, folder_path: str) -> bool:
        """Validate folder path and permissions"""
        if not folder_path or not os.path.exists(folder_path):
            self._thread_safe_clear_preview()
            self._thread_safe_update_status("Invalid folder path", "red")
            return False
        
        if not os.access(folder_path, os.R_OK):
            self._thread_safe_clear_preview()
            self._thread_safe_update_status("Cannot access folder (permission denied)", "red")
            return False
        
        return True
    
    def _update_ui_with_preview(self, preview_data: List[RenamePreview]):
        """Update UI with preview data (called in main thread)"""
        try:
            self.preview_data = preview_data
            
            # Update UI with preview data
            self._populate_preview_tree(preview_data)
            self._update_counts()
            self._update_status(f"Preview generated for {len(preview_data)} items", "green")
            
            # Hide loading state
            self.preview_state.is_loading = False
            self.show_loading_state(False)
            
            # Notify state change
            if self.on_state_changed:
                self.on_state_changed(files_preview=preview_data)
                
        except Exception as e:
            self.handle_error(f"Error updating UI: {str(e)}")
    
    def _thread_safe_clear_preview(self):
        """Clear preview from background thread"""
        self.parent.after(0, self._clear_preview)
    
    def _thread_safe_update_status(self, message: str, color: str):
        """Update status from background thread"""
        self.parent.after(0, lambda: self._update_status(message, color))
        self.parent.after(0, lambda: self.show_loading_state(False))
    
    def _handle_error_thread_safe(self, error: str):
        """Handle error from background thread"""
        self.preview_state.is_loading = False
        self.show_loading_state(False)
        self.handle_error(error)

    def _generate_rename_preview(self, folder_path: str) -> List[RenamePreview]:
        """Generate rename preview data for all files in folder with performance optimizations"""
        preview_data = []
        
        try:
            items = os.listdir(folder_path)
            items.sort()  # Sort alphabetically
            
            # Performance limit for large directories - be more aggressive
            max_items = min(self.max_visible_items, 500)  # Cap at 500 for responsiveness
            if len(items) > max_items:
                original_count = len(items)
                items = items[:max_items]
                logger.warning(f"Large directory detected ({original_count} items), limiting to {max_items} for performance")
            
            # Track normalized names for conflict detection
            normalized_names = {}
            
            # Process files in batches for better performance with smaller batch sizes
            batch_size = min(self.lazy_load_batch_size, 50)  # Smaller batches for responsiveness
            total_items = len(items)
            for batch_start in range(0, total_items, batch_size):
                batch_end = min(batch_start + batch_size, total_items)
                batch_items = items[batch_start:batch_end]
                
                batch_previews = self._process_batch(folder_path, batch_items, batch_start, normalized_names)
                preview_data.extend(batch_previews)
                
                # Yield control occasionally for responsiveness
                if batch_start % 100 == 0:
                    import time
                    time.sleep(0.001)  # Tiny sleep to yield control
                
                # Allow UI updates between batches for large datasets
                if len(preview_data) % (self.lazy_load_batch_size * 2) == 0:
                    time.sleep(0.001)  # Small yield for UI responsiveness
                    
        except (OSError, IOError) as e:
            raise Exception(f"Cannot read folder contents: {str(e)}")
        
        return preview_data
    
    def _process_batch(self, folder_path: str, batch_items: List[str], start_index: int, 
                      normalized_names: Dict[str, RenamePreview]) -> List[RenamePreview]:
        """Process a batch of files for better performance"""
        batch_previews = []
        
        for i, item in enumerate(batch_items):
            preview = self._create_file_preview(folder_path, item, start_index + i)
            if preview:
                self._detect_conflicts(preview, normalized_names)
                batch_previews.append(preview)
        
        return batch_previews
    
    def _create_file_preview(self, folder_path: str, item_name: str, index: int) -> Optional[RenamePreview]:
        """Create a single file preview with error handling"""
        item_path = os.path.join(folder_path, item_name)
        
        try:
            if not (os.path.isfile(item_path) or os.path.isdir(item_path)):
                return None
            
            # Create file info
            file_info = FileInfo(
                name=item_name,
                original_name=item_name,
                path=item_path,
                file_type=FileType.FILE if os.path.isfile(item_path) else FileType.FOLDER
            )
            
            # Generate normalized name with caching
            normalized_name = self._get_cached_normalized_name(item_name)
            normalized_path = os.path.join(folder_path, normalized_name)
            
            # Create preview object
            file_id = f"file_{index}_{hash(item_path)}"
            preview = RenamePreview(
                file_id=file_id,
                file_info=file_info,
                normalized_name=normalized_name,
                normalized_full_path=normalized_path
            )
            
            # Check if file will be unchanged
            preview.is_unchanged = (item_name == normalized_name)
            
            return preview
            
        except (OSError, IOError):
            return None
    
    def _detect_conflicts(self, preview: RenamePreview, normalized_names: Dict[str, RenamePreview]):
        """Detect and mark conflicts for duplicate normalized names"""
        normalized_name = preview.normalized_name
        
        if normalized_name in normalized_names:
            # Mark both files as conflicting
            preview.has_conflict = True
            preview.conflict_type = "duplicate"
            
            existing_preview = normalized_names[normalized_name]
            existing_preview.has_conflict = True
            existing_preview.conflict_type = "duplicate"
        else:
            normalized_names[normalized_name] = preview
    
    def _get_cached_normalized_name(self, filename: str) -> str:
        """Get normalized filename with caching for performance"""
        if filename in self.normalization_cache:
            return self.normalization_cache[filename]
        
        normalized = self.normalizer.normalize_filename(filename)
        self.normalization_cache[filename] = normalized
        
        # Limit cache size to prevent memory issues
        if len(self.normalization_cache) > CACHE_SIZE_LIMIT:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self.normalization_cache.keys())[:CACHE_CLEANUP_SIZE]
            for key in keys_to_remove:
                del self.normalization_cache[key]
        
        return normalized

    def toggle_file_selection(self, file_id: str, selected: bool):
        """Toggle selection state of individual file"""
        for preview in self.preview_data:
            if preview.file_id == file_id:
                preview.is_selected = selected
                if selected:
                    self.selected_files.add(file_id)
                else:
                    self.selected_files.discard(file_id)
                break
        
        # Update counts and UI
        self._update_counts()
        self._refresh_tree_item(file_id)
        
        # Notify state change
        if self.on_state_changed:
            self.on_state_changed(selected_files=self.selected_files)

    def _populate_preview_tree(self, preview_data: List[RenamePreview]):
        """Populate tree with two-column preview data"""
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        
        # Add preview items
        for preview in preview_data:
            checkbox_icon = "☑" if preview.is_selected else "☐"
            status_text = self._get_status_text(preview)
            
            item_id = self.tree.insert(
                "",
                tk.END,
                text=checkbox_icon,
                values=(preview.file_info.name, preview.normalized_name, status_text),
                tags=(preview.file_id,)
            )
            
            # Apply row coloring based on file state
            self._apply_row_styling(item_id, preview)
    
    def _get_status_text(self, preview: RenamePreview) -> str:
        """Get status text for preview item"""
        if preview.has_conflict:
            return f"Conflict ({preview.conflict_type})"
        elif preview.is_unchanged:
            return "No changes"
        else:
            return "Will rename"
    
    def _apply_row_styling(self, item_id: str, preview: RenamePreview):
        """Apply color styling to tree row based on file state"""
        if preview.has_conflict:
            self.tree.set(item_id, "#0", "⚠")
            # Note: tkinter TreeView doesn't support direct background color per row
            # This would need a custom implementation or different approach
        elif preview.is_unchanged:
            pass  # Gray styling would be applied here
        elif preview.is_selected:
            pass  # Blue styling would be applied here

    def _clear_preview(self):
        """Clear all preview data and UI"""
        self.tree.delete(*self.tree.get_children())
        self.preview_data = []
        self.selected_files.clear()
        self.preview_state = FilePreviewState()
        self._update_counts()
        
        # Clean up performance caches
        self.clear_caches()
    
    def clear_caches(self):
        """Clear performance caches to free memory"""
        self.normalization_cache.clear()
        logger.debug("Performance caches cleared")

    def _update_counts(self):
        """Update all count displays"""
        self.preview_state.update_counts(self.preview_data)
        
        # Update file count label
        self.file_count_label.config(
            text=f"({self.preview_state.total_files} files)"
        )
        
        # Update selection count label
        self.selection_count_label.config(
            text=f"{self.preview_state.selected_files} of {self.preview_state.total_files} selected"
        )
        
        # Show conflict count if any
        if self.preview_state.conflict_files > 0:
            conflict_text = f", {self.preview_state.conflict_files} conflicts"
            current_text = self.selection_count_label.cget("text")
            self.selection_count_label.config(text=current_text + conflict_text)

    def _update_status(self, message: str, color: str = "gray"):
        self.status_label.config(text=message, foreground=color)

    def get_preview_data(self) -> List[RenamePreview]:
        """Get copy of current preview data"""
        return self.preview_data.copy()
    
    def get_selected_files(self) -> Set[str]:
        """Get set of selected file IDs"""
        return self.selected_files.copy()
    
    def show_loading_state(self, is_loading: bool):
        """Show/hide loading indicator"""
        if is_loading:
            self.loading_label.config(text="Loading preview...", foreground="blue")
        else:
            self.loading_label.config(text="")
    
    def on_tree_click(self, event):
        """Handle tree click events for file selection toggle"""
        region = self.tree.identify_region(event.x, event.y)
        if region == "tree":  # Clicked on checkbox column
            item_id = self.tree.identify_row(event.y)
            if item_id:
                tags = self.tree.item(item_id, "tags")
                if tags:
                    file_id = tags[0]
                    # Find preview and toggle selection
                    for preview in self.preview_data:
                        if preview.file_id == file_id:
                            self.toggle_file_selection(file_id, not preview.is_selected)
                            break
    
    def on_space_pressed(self, event):
        """Handle space key press for selection toggle"""
        selected_item = self.tree.selection()
        if selected_item:
            item_id = selected_item[0]
            tags = self.tree.item(item_id, "tags")
            if tags:
                file_id = tags[0]
                for preview in self.preview_data:
                    if preview.file_id == file_id:
                        self.toggle_file_selection(file_id, not preview.is_selected)
                        break
    
    def _refresh_tree_item(self, file_id: str):
        """Refresh single tree item display"""
        for item_id in self.tree.get_children():
            tags = self.tree.item(item_id, "tags")
            if tags and tags[0] == file_id:
                # Find corresponding preview
                for preview in self.preview_data:
                    if preview.file_id == file_id:
                        checkbox_icon = "☑" if preview.is_selected else "☐"
                        self.tree.item(item_id, text=checkbox_icon)
                        break
                break

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