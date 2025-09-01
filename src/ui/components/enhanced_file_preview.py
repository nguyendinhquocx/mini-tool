"""
Enhanced File Preview Component - Performance Optimized

Progressive loading, virtualized display, và memory-efficient preview generation
for large directories với thousands of files.
"""

import tkinter as tk
from tkinter import ttk
import asyncio
import threading
import time
from typing import Callable, List, Dict, Any, Set, Optional, AsyncGenerator
import logging
from dataclasses import dataclass

# Core imports
from ...core.models.file_info import RenamePreview, FilePreviewState, FileInfo, FileType
from ...core.services.normalize_service import VietnameseNormalizer
from ...core.services.file_streaming_service import get_streaming_service, LoadingProgress
from ...core.utils.performance_monitor import get_performance_monitor, PerformanceProfiler

logger = logging.getLogger(__name__)


@dataclass
class ViewportConfig:
    """Configuration for virtualized viewport"""
    visible_rows: int = 50
    buffer_rows: int = 10
    row_height: int = 24
    scroll_sensitivity: int = 3


@dataclass
class ProgressiveLoadingState:
    """State tracking for progressive loading"""
    is_loading: bool = False
    total_files: int = 0
    loaded_files: int = 0
    loading_progress: float = 0.0
    estimated_completion: Optional[str] = None
    current_chunk: int = 0
    error_message: Optional[str] = None


class VirtualizedTreeView(ttk.Treeview):
    """
    Virtualized TreeView implementation for handling large datasets
    """
    
    def __init__(self, parent, config: ViewportConfig, **kwargs):
        super().__init__(parent, **kwargs)
        self.config = config
        self.data_source: List[RenamePreview] = []
        self.visible_start = 0
        self.visible_end = 0
        self.total_items = 0
        
        # Bind scroll events
        self.bind('<MouseWheel>', self._on_mouse_wheel)
        self.bind('<Button-4>', self._on_mouse_wheel)
        self.bind('<Button-5>', self._on_mouse_wheel)
        self.bind('<Key>', self._on_key_press)
        
        # Virtual scrollbar
        self._setup_virtual_scrolling()
    
    def _setup_virtual_scrolling(self):
        """Setup virtual scrolling mechanism"""
        # Configure scrolling behavior
        self.configure(height=self.config.visible_rows)
    
    def set_data_source(self, data: List[RenamePreview]):
        """Set the data source for virtualization"""
        self.data_source = data
        self.total_items = len(data)
        self._refresh_viewport()
    
    def append_data(self, new_data: List[RenamePreview]):
        """Append new data to existing dataset (for progressive loading)"""
        self.data_source.extend(new_data)
        self.total_items = len(self.data_source)
        self._refresh_viewport()
    
    def _refresh_viewport(self):
        """Refresh the visible viewport"""
        # Clear existing items
        for item in self.get_children():
            self.delete(item)
        
        # Calculate visible range
        buffer_size = self.config.buffer_rows
        start = max(0, self.visible_start - buffer_size)
        end = min(self.total_items, self.visible_end + buffer_size)
        
        # Populate visible items
        for i in range(start, end):
            if i < len(self.data_source):
                preview = self.data_source[i]
                self.insert('', 'end', iid=str(i), values=(
                    preview.original_name,
                    preview.new_name,
                    preview.status.value if preview.status else 'Unknown'
                ))
    
    def _on_mouse_wheel(self, event):
        """Handle mouse wheel scrolling"""
        # Calculate scroll delta
        if hasattr(event, 'delta'):
            delta = -1 * (event.delta // 120)
        else:
            delta = 1 if event.num == 5 else -1
        
        # Apply scroll sensitivity
        scroll_amount = delta * self.config.scroll_sensitivity
        
        # Update visible range
        new_start = max(0, min(
            self.visible_start + scroll_amount,
            self.total_items - self.config.visible_rows
        ))
        
        if new_start != self.visible_start:
            self.visible_start = new_start
            self.visible_end = min(self.total_items, new_start + self.config.visible_rows)
            self._refresh_viewport()
        
        return "break"
    
    def _on_key_press(self, event):
        """Handle keyboard navigation"""
        if event.keysym in ('Up', 'Down', 'Page_Up', 'Page_Down', 'Home', 'End'):
            # Handle keyboard scrolling
            if event.keysym == 'Up':
                self._scroll_by(-1)
            elif event.keysym == 'Down':
                self._scroll_by(1)
            elif event.keysym == 'Page_Up':
                self._scroll_by(-self.config.visible_rows)
            elif event.keysym == 'Page_Down':
                self._scroll_by(self.config.visible_rows)
            elif event.keysym == 'Home':
                self._scroll_to(0)
            elif event.keysym == 'End':
                self._scroll_to(self.total_items - self.config.visible_rows)
            
            return "break"
    
    def _scroll_by(self, delta: int):
        """Scroll by specified amount"""
        new_start = max(0, min(
            self.visible_start + delta,
            self.total_items - self.config.visible_rows
        ))
        
        if new_start != self.visible_start:
            self.visible_start = new_start
            self.visible_end = min(self.total_items, new_start + self.config.visible_rows)
            self._refresh_viewport()
    
    def _scroll_to(self, position: int):
        """Scroll to specific position"""
        self.visible_start = max(0, min(position, self.total_items - self.config.visible_rows))
        self.visible_end = min(self.total_items, self.visible_start + self.config.visible_rows)
        self._refresh_viewport()


class EnhancedFilePreviewComponent:
    """
    Performance-optimized file preview component với progressive loading
    """
    
    def __init__(self, parent: ttk.Widget, state_changed_callback: Callable):
        self.parent = parent
        self.on_state_changed = state_changed_callback
        
        # Services
        self.streaming_service = get_streaming_service()
        self.performance_monitor = get_performance_monitor()
        self.normalizer = VietnameseNormalizer()
        
        # State management
        self.preview_data: List[RenamePreview] = []
        self.selected_files: Set[str] = set()
        self.folder_path: Optional[str] = None
        self.loading_state = ProgressiveLoadingState()
        
        # UI Configuration
        self.viewport_config = ViewportConfig()
        
        # Threading and async
        self.loading_task: Optional[asyncio.Task] = None
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
        self.loop_thread: Optional[threading.Thread] = None
        
        # Performance optimization
        self.normalization_cache: Dict[str, str] = {}
        self.last_update_time = 0
        
        self.setup_ui()
        self._start_event_loop()
    
    def setup_ui(self):
        """Setup the enhanced UI components"""
        # Main container
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid
        self.frame.rowconfigure(2, weight=1)
        self.frame.columnconfigure(0, weight=1)
        
        # Header với loading progress
        self._setup_header()
        
        # Progress bar
        self._setup_progress_bar()
        
        # Virtualized tree view
        self._setup_tree_view()
        
        # Status footer
        self._setup_status_footer()
    
    def _setup_header(self):
        """Setup header với file count và loading status"""
        header_frame = ttk.Frame(self.frame)
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        header_frame.columnconfigure(1, weight=1)
        
        # Title
        ttk.Label(header_frame, text="File Preview", 
                 font=('Arial', 12, 'bold')).grid(row=0, column=0, sticky="w")
        
        # File count label
        self.file_count_label = ttk.Label(header_frame, text="No files loaded")
        self.file_count_label.grid(row=0, column=1, sticky="e")
        
        # Loading status
        self.loading_status_label = ttk.Label(header_frame, text="", foreground="blue")
        self.loading_status_label.grid(row=1, column=0, columnspan=2, sticky="w")
    
    def _setup_progress_bar(self):
        """Setup progress bar cho loading operations"""
        progress_frame = ttk.Frame(self.frame)
        progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            mode='determinate',
            length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        
        # Initially hidden
        progress_frame.grid_remove()
        self.progress_frame = progress_frame
    
    def _setup_tree_view(self):
        """Setup virtualized tree view"""
        tree_frame = ttk.Frame(self.frame)
        tree_frame.grid(row=2, column=0, sticky="nsew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        
        # Create virtualized tree view
        self.tree = VirtualizedTreeView(
            tree_frame,
            config=self.viewport_config,
            columns=('original', 'new', 'status'),
            show='tree headings'
        )
        
        # Configure columns
        self.tree.heading('#0', text='#', anchor=tk.W)
        self.tree.heading('original', text='Current Name', anchor=tk.W)
        self.tree.heading('new', text='New Name', anchor=tk.W) 
        self.tree.heading('status', text='Status', anchor=tk.W)
        
        self.tree.column('#0', width=50, minwidth=30)
        self.tree.column('original', width=300, minwidth=200)
        self.tree.column('new', width=300, minwidth=200)
        self.tree.column('status', width=100, minwidth=80)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=h_scrollbar.set)
    
    def _setup_status_footer(self):
        """Setup status footer với performance metrics"""
        status_frame = ttk.Frame(self.frame)
        status_frame.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        status_frame.columnconfigure(2, weight=1)
        
        # Performance metrics
        self.perf_label = ttk.Label(status_frame, text="", foreground="gray", font=('Arial', 8))
        self.perf_label.grid(row=0, column=0, sticky="w")
        
        # Memory usage
        self.memory_label = ttk.Label(status_frame, text="", foreground="gray", font=('Arial', 8))
        self.memory_label.grid(row=0, column=1, sticky="w", padx=(20, 0))
        
        # Status message
        self.status_message = ttk.Label(status_frame, text="Ready", font=('Arial', 8))
        self.status_message.grid(row=0, column=2, sticky="e")
    
    def _start_event_loop(self):
        """Start async event loop trong background thread"""
        def run_loop():
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            try:
                self.event_loop.run_forever()
            except Exception as e:
                logger.error(f"Error in event loop: {e}")
            finally:
                self.event_loop.close()
        
        self.loop_thread = threading.Thread(target=run_loop, daemon=True)
        self.loop_thread.start()
    
    async def update_files_async(self, folder_path: str):
        """
        Asynchronously update files using progressive loading
        
        Args:
            folder_path: Directory to scan
        """
        if not folder_path or not os.path.exists(folder_path):
            logger.warning(f"Invalid folder path: {folder_path}")
            return
        
        self.folder_path = folder_path
        self.loading_state = ProgressiveLoadingState(is_loading=True)
        
        # Reset UI state
        self._update_ui_thread_safe(lambda: self._reset_ui_for_loading())
        
        try:
            with PerformanceProfiler(self.performance_monitor, f"Load files from {folder_path}"):
                # Start progressive loading
                chunk_count = 0
                total_loaded = 0
                
                async for chunk in self.streaming_service.scan_directory_chunked(
                    folder_path,
                    chunk_callback=self._on_loading_progress
                ):
                    if not chunk:
                        continue
                    
                    chunk_count += 1
                    total_loaded += len(chunk)
                    
                    # Generate previews for chunk
                    preview_chunk = await self._generate_preview_chunk(chunk)
                    
                    # Update UI with new chunk
                    self._update_ui_thread_safe(lambda: self._append_preview_chunk(preview_chunk))
                    
                    # Update loading progress
                    self.loading_state.loaded_files = total_loaded
                    self.loading_state.current_chunk = chunk_count
                    
                    # Allow UI to update
                    await asyncio.sleep(0.01)
                
                # Loading complete
                self.loading_state.is_loading = False
                self.loading_state.loading_progress = 100.0
                
                # Final UI update
                self._update_ui_thread_safe(lambda: self._finalize_loading())
                
        except Exception as e:
            error_msg = f"Error loading files from {folder_path}: {e}"
            logger.error(error_msg)
            self.loading_state.error_message = error_msg
            self.loading_state.is_loading = False
            
            self._update_ui_thread_safe(lambda: self._handle_loading_error(error_msg))
    
    def update_files(self, folder_path: str):
        """
        Update files using progressive loading (public interface)
        
        Args:
            folder_path: Directory to scan
        """
        if not self.event_loop:
            logger.error("Event loop not available")
            return
        
        # Cancel existing loading task
        if self.loading_task and not self.loading_task.done():
            self.loading_task.cancel()
        
        # Schedule new loading task
        future = asyncio.run_coroutine_threadsafe(
            self.update_files_async(folder_path),
            self.event_loop
        )
        
        self.loading_task = asyncio.wrap_future(future)
    
    def _on_loading_progress(self, chunk: List[FileInfo], progress: LoadingProgress):
        """Handle loading progress updates"""
        self.loading_state.total_files = progress.total_estimated
        self.loading_state.loaded_files = progress.files_scanned
        
        if progress.total_estimated > 0:
            self.loading_state.loading_progress = (
                progress.files_scanned / progress.total_estimated * 100
            )
        
        # Update UI
        self._update_ui_thread_safe(lambda: self._update_loading_progress(progress))
    
    async def _generate_preview_chunk(self, files: List[FileInfo]) -> List[RenamePreview]:
        """Generate preview for a chunk của files"""
        previews = []
        
        for file_info in files:
            try:
                # Check cache first
                cache_key = f"{file_info.name}:{file_info.modified}"
                if cache_key in self.normalization_cache:
                    normalized_name = self.normalization_cache[cache_key]
                else:
                    # Generate normalized name
                    normalized_name = self.normalizer.normalize_filename(file_info.name)
                    self.normalization_cache[cache_key] = normalized_name
                
                # Create preview
                preview = RenamePreview(
                    original_name=file_info.name,
                    new_name=normalized_name,
                    file_path=file_info.path,
                    file_size=file_info.size,
                    has_conflict=False,  # Will be checked later
                    status=None  # Will be determined based on changes
                )
                
                previews.append(preview)
                
            except Exception as e:
                logger.debug(f"Error generating preview for {file_info.name}: {e}")
                continue
        
        return previews
    
    def _update_ui_thread_safe(self, update_func: Callable):
        """Execute UI updates in main thread"""
        if self.parent.winfo_exists():
            self.parent.after_idle(update_func)
    
    def _reset_ui_for_loading(self):
        """Reset UI for new loading operation"""
        self.preview_data.clear()
        self.tree.set_data_source([])
        self.progress_frame.grid()
        self.progress_var.set(0)
        self.loading_status_label.config(text="Loading files...")
        self.file_count_label.config(text="Loading...")
    
    def _append_preview_chunk(self, chunk: List[RenamePreview]):
        """Append new preview chunk to UI"""
        self.preview_data.extend(chunk)
        self.tree.append_data(chunk)
        
        # Update file count
        self.file_count_label.config(text=f"{len(self.preview_data)} files loaded")
    
    def _update_loading_progress(self, progress: LoadingProgress):
        """Update loading progress display"""
        if progress.total_estimated > 0:
            progress_percent = (progress.files_scanned / progress.total_estimated) * 100
            self.progress_var.set(progress_percent)
            
            status_text = f"Loading: {progress.files_scanned}/{progress.total_estimated} files"
            if progress.scan_rate_files_per_second > 0:
                status_text += f" ({progress.scan_rate_files_per_second:.1f} files/sec)"
            
            self.loading_status_label.config(text=status_text)
        
        # Update performance metrics
        self._update_performance_display(progress.memory_usage_mb)
    
    def _finalize_loading(self):
        """Finalize loading operation"""
        self.progress_frame.grid_remove()
        self.loading_status_label.config(text="Loading complete")
        
        # Update final file count
        self.file_count_label.config(text=f"{len(self.preview_data)} files")
        
        # Update status
        if self.preview_data:
            changed_count = len([p for p in self.preview_data 
                               if p.original_name != p.new_name])
            self.status_message.config(
                text=f"Ready - {changed_count} files will be renamed"
            )
        else:
            self.status_message.config(text="No files found")
        
        # Notify state change
        self.on_state_changed(
            files_preview=self.preview_data,
            preview_ready=True
        )
    
    def _handle_loading_error(self, error_msg: str):
        """Handle loading errors"""
        self.progress_frame.grid_remove()
        self.loading_status_label.config(text=f"Error: {error_msg}", foreground="red")
        self.file_count_label.config(text="Error loading files")
        self.status_message.config(text="Error occurred")
    
    def _update_performance_display(self, memory_mb: float):
        """Update performance metrics display"""
        # Get current performance stats
        stats = self.performance_monitor.get_performance_summary()
        
        # Update performance label
        if stats.get('avg_files_per_second', 0) > 0:
            perf_text = f"{stats['avg_files_per_second']:.1f} files/sec"
            self.perf_label.config(text=perf_text)
        
        # Update memory label
        if memory_mb > 0:
            memory_text = f"Memory: {memory_mb:.1f} MB"
            self.memory_label.config(text=memory_text)
    
    def get_selected_files(self) -> List[FileInfo]:
        """Get currently selected files"""
        selected_items = self.tree.selection()
        selected_previews = []
        
        for item_id in selected_items:
            try:
                index = int(item_id)
                if 0 <= index < len(self.preview_data):
                    preview = self.preview_data[index]
                    # Convert to FileInfo
                    file_info = FileInfo(
                        name=preview.original_name,
                        path=preview.file_path,
                        size=preview.file_size,
                        is_directory=False
                    )
                    selected_previews.append(file_info)
            except (ValueError, IndexError):
                continue
        
        return selected_previews
    
    def get_all_files(self) -> List[FileInfo]:
        """Get all loaded files"""
        return [
            FileInfo(
                name=preview.original_name,
                path=preview.file_path,
                size=preview.file_size,
                is_directory=False
            )
            for preview in self.preview_data
        ]
    
    def clear_cache(self):
        """Clear normalization cache"""
        self.normalization_cache.clear()
        logger.info("Preview cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.normalization_cache),
            "memory_estimate_mb": len(str(self.normalization_cache)) / (1024 * 1024)
        }
    
    def shutdown(self):
        """Shutdown the component và cleanup resources"""
        # Cancel loading task
        if self.loading_task and not self.loading_task.done():
            self.loading_task.cancel()
        
        # Stop event loop
        if self.event_loop and self.event_loop.is_running():
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        
        # Clear caches
        self.clear_cache()
        
        logger.info("Enhanced file preview component shutdown complete")


# Factory function for creating enhanced preview components
def create_enhanced_file_preview(parent: ttk.Widget, state_callback: Callable) -> EnhancedFilePreviewComponent:
    """Create an enhanced file preview component"""
    return EnhancedFilePreviewComponent(parent, state_callback)