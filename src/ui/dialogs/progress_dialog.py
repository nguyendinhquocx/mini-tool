"""
Progress Dialog Component

Displays progress information for long-running batch operations.
Shows current file being processed, progress percentage, and allows cancellation.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
from dataclasses import dataclass
import threading
import time


@dataclass
class ProgressInfo:
    """Progress information for batch operations with enhanced timing"""
    current_file: str = ""
    processed_files: int = 0
    total_files: int = 0
    percentage: float = 0.0
    operation_name: str = "Processing"
    can_cancel: bool = True
    is_completed: bool = False
    error_message: Optional[str] = None
    
    # Enhanced timing and estimation fields
    estimated_time_remaining: Optional[str] = None
    elapsed_time: Optional[str] = None
    processing_speed: Optional[str] = None  # "X files/sec"
    operation_start_time: Optional[float] = None
    
    # Results summary for completion
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0


class ProgressDialog:
    """
    Modal progress dialog for batch file operations
    
    Features:
    - Progress bar with percentage display
    - Current file being processed
    - File count (processed/total)
    - Cancel button with confirmation
    - Operation status messages
    """
    
    def __init__(self, parent: tk.Widget, operation_name: str = "Processing Files"):
        self.parent = parent
        self.operation_name = operation_name
        self.dialog = None
        self.progress_info = ProgressInfo(operation_name=operation_name)
        
        # Callbacks
        self.cancel_callback: Optional[Callable[[], None]] = None
        self.completion_callback: Optional[Callable[[bool], None]] = None
        
        # UI components
        self.progress_bar: Optional[ttk.Progressbar] = None
        self.progress_label: Optional[ttk.Label] = None
        self.current_file_label: Optional[ttk.Label] = None
        self.file_count_label: Optional[ttk.Label] = None
        self.cancel_button: Optional[ttk.Button] = None
        self.status_label: Optional[ttk.Label] = None
        
        # Enhanced timing components
        self.eta_label: Optional[ttk.Label] = None
        self.elapsed_time_label: Optional[ttk.Label] = None
        self.speed_label: Optional[ttk.Label] = None
        self.completion_summary_frame: Optional[ttk.Frame] = None
        
        # Dialog state
        self.is_cancelled = False
        self.is_shown = False
        
    def show(self, cancel_callback: Optional[Callable[[], None]] = None,
             completion_callback: Optional[Callable[[bool], None]] = None):
        """
        Show the progress dialog
        
        Args:
            cancel_callback: Function to call when user cancels operation
            completion_callback: Function to call when dialog is closed (success/failure)
        """
        if self.is_shown:
            return
            
        self.cancel_callback = cancel_callback
        self.completion_callback = completion_callback
        self._create_dialog()
        self.is_shown = True
        
    def _create_dialog(self):
        """Create and configure the dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.operation_name)
        # Constants for dialog sizing
        DIALOG_WIDTH = 500
        DIALOG_HEIGHT = 300
        self.dialog.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}")
        self.dialog.resizable(False, False)
        
        # Center dialog on parent
        self._center_dialog()
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Configure dialog close behavior
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_dialog_close)
        
        # Create UI components
        self._create_ui_components()
        
        # Initial update
        self._update_display()
        
    def _center_dialog(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        DIALOG_WIDTH = 500
        DIALOG_HEIGHT = 300
        x = parent_x + (parent_width - DIALOG_WIDTH) // 2
        y = parent_y + (parent_height - DIALOG_HEIGHT) // 2
        
        self.dialog.geometry(f"{DIALOG_WIDTH}x{DIALOG_HEIGHT}+{x}+{y}")
        
    def _create_ui_components(self):
        """Create all UI components for the dialog"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Operation name label
        operation_label = ttk.Label(
            main_frame, 
            text=self.operation_name,
            font=('Arial', 12, 'bold')
        )
        operation_label.pack(pady=(0, 10))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            main_frame,
            mode='determinate',
            length=350
        )
        self.progress_bar.pack(pady=5)
        
        # Progress percentage label
        self.progress_label = ttk.Label(main_frame, text="0%")
        self.progress_label.pack(pady=2)
        
        # File count label
        self.file_count_label = ttk.Label(main_frame, text="Processed 0 of 0 files")
        self.file_count_label.pack(pady=2)
        
        # Current file label
        current_file_frame = ttk.Frame(main_frame)
        current_file_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(current_file_frame, text="Current file:", font=('Arial', 9, 'bold')).pack(anchor='w')
        self.current_file_label = ttk.Label(
            current_file_frame, 
            text="Ready to start...",
            foreground='blue',
            font=('Arial', 9)
        )
        self.current_file_label.pack(anchor='w', fill=tk.X)
        
        # Timing information frame
        timing_frame = ttk.LabelFrame(main_frame, text="Timing Information", padding=5)
        timing_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Create three columns for timing info
        timing_grid = ttk.Frame(timing_frame)
        timing_grid.pack(fill=tk.X)
        
        # Column 1: Elapsed time
        elapsed_frame = ttk.Frame(timing_grid)
        elapsed_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(elapsed_frame, text="Elapsed:", font=('Arial', 8, 'bold')).pack(anchor='w')
        self.elapsed_time_label = ttk.Label(elapsed_frame, text="00:00", font=('Arial', 8))
        self.elapsed_time_label.pack(anchor='w')
        
        # Column 2: Estimated time remaining
        eta_frame = ttk.Frame(timing_grid)
        eta_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(eta_frame, text="Remaining:", font=('Arial', 8, 'bold')).pack(anchor='w')
        self.eta_label = ttk.Label(eta_frame, text="Calculating...", font=('Arial', 8))
        self.eta_label.pack(anchor='w')
        
        # Column 3: Processing speed
        speed_frame = ttk.Frame(timing_grid)
        speed_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(speed_frame, text="Speed:", font=('Arial', 8, 'bold')).pack(anchor='w')
        self.speed_label = ttk.Label(speed_frame, text="0 files/sec", font=('Arial', 8))
        self.speed_label.pack(anchor='w')
        
        # Status label for error messages
        self.status_label = ttk.Label(
            main_frame,
            text="",
            foreground='red',
            font=('Arial', 9)
        )
        self.status_label.pack(pady=(5, 0))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        
        # Cancel button
        self.cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel_clicked
        )
        self.cancel_button.pack(side=tk.RIGHT)
        
    def update_progress(self, progress_info: ProgressInfo):
        """
        Update progress display with new information
        
        Args:
            progress_info: Current progress information
        """
        if not self.dialog or not self.is_shown:
            return
            
        self.progress_info = progress_info
        
        # Schedule UI update on main thread
        self.dialog.after(0, self._update_display)
        
    def _update_display(self):
        """Update all UI components with current progress info"""
        if not self.dialog or not self.is_shown:
            return
            
        info = self.progress_info
        
        # Update progress bar
        if self.progress_bar:
            self.progress_bar['value'] = info.percentage
            
        # Update progress label
        if self.progress_label:
            self.progress_label.config(text=f"{info.percentage:.1f}%")
            
        # Update file count
        if self.file_count_label:
            self.file_count_label.config(
                text=f"Processed {info.processed_files} of {info.total_files} files"
            )
            
        # Update current file (truncate if too long)
        if self.current_file_label:
            current_file = self._truncate_filename(info.current_file)
            self.current_file_label.config(text=current_file)
            
        # Update timing information
        if self.elapsed_time_label and info.elapsed_time:
            self.elapsed_time_label.config(text=info.elapsed_time)
            
        if self.eta_label:
            if info.estimated_time_remaining:
                self.eta_label.config(text=info.estimated_time_remaining)
            elif info.percentage > 0:
                self.eta_label.config(text="Calculating...")
            else:
                self.eta_label.config(text="--:--")
                
        if self.speed_label and info.processing_speed:
            self.speed_label.config(text=info.processing_speed)
            
        # Update status/error message
        if self.status_label:
            if info.error_message:
                self.status_label.config(text=info.error_message, foreground='red')
            else:
                self.status_label.config(text="", foreground='red')
                
        # Handle completion
        if info.is_completed:
            self._handle_completion()
            
        # Disable cancel button if not allowed
        if self.cancel_button:
            self.cancel_button.config(state='normal' if info.can_cancel else 'disabled')
            
    def _handle_completion(self):
        """Handle operation completion with results summary"""
        if not self.dialog or not self.is_shown:
            return
            
        # Show completion summary
        self._show_completion_summary()
            
        # Change cancel button to "Close"
        if self.cancel_button:
            self.cancel_button.config(text="Close", state='normal')
            
        # Auto-close after delay if no errors (AC: 8)
        AUTO_CLOSE_DELAY_MS = 3000  # 3 seconds
        if not self.progress_info.error_message and self.progress_info.success_count > 0:
            self.dialog.after(AUTO_CLOSE_DELAY_MS, self._close_dialog)
    
    def _show_completion_summary(self):
        """Show operation completion summary (AC: 6)"""
        info = self.progress_info
        
        # Create completion summary if not exists
        if not self.completion_summary_frame:
            # Hide timing frame during completion
            for child in self.dialog.winfo_children():
                for frame in child.winfo_children():
                    if isinstance(frame, ttk.LabelFrame) and "Timing" in frame.cget("text"):
                        frame.pack_forget()
                        break
            
            # Get main frame
            main_frame = None
            for child in self.dialog.winfo_children():
                if isinstance(child, ttk.Frame):
                    main_frame = child
                    break
            
            if main_frame:
                self.completion_summary_frame = ttk.LabelFrame(
                    main_frame, 
                    text="Operation Results", 
                    padding=10
                )
                self.completion_summary_frame.pack(fill=tk.X, pady=(10, 0))
                
                # Success/failure summary
                summary_text = []
                if info.success_count > 0:
                    summary_text.append(f"✓ Successfully processed {info.success_count} files")
                if info.error_count > 0:
                    summary_text.append(f"✗ Failed to process {info.error_count} files")
                if info.skipped_count > 0:
                    summary_text.append(f"⚠ Skipped {info.skipped_count} files")
                
                if not summary_text:
                    summary_text = [f"✓ Operation completed ({info.processed_files} files)"]
                
                for text in summary_text:
                    color = "green" if text.startswith("✓") else "red" if text.startswith("✗") else "orange"
                    label = ttk.Label(
                        self.completion_summary_frame,
                        text=text,
                        font=('Arial', 10),
                        foreground=color
                    )
                    label.pack(anchor='w', pady=1)
            
    def _on_cancel_clicked(self):
        """Handle cancel button click"""
        if self.progress_info.is_completed:
            # Operation completed, close dialog
            self._close_dialog()
        else:
            # Operation in progress, confirm cancellation
            self._confirm_cancellation()
            
    def _confirm_cancellation(self):
        """Show cancellation confirmation dialog"""
        from tkinter import messagebox
        
        result = messagebox.askyesno(
            "Cancel Operation",
            "Are you sure you want to cancel the current operation?\n\n"
            "Files that have already been processed will remain changed.",
            parent=self.dialog
        )
        
        if result and self.cancel_callback:
            self.is_cancelled = True
            self.cancel_callback()
            self._close_dialog()
            
    def _on_dialog_close(self):
        """Handle dialog close event (X button)"""
        if self.progress_info.is_completed:
            self._close_dialog()
        else:
            self._confirm_cancellation()
            
    def _close_dialog(self):
        """Close the dialog and cleanup"""
        if not self.dialog:
            return
            
        success = not self.is_cancelled and not self.progress_info.error_message
        
        # Call completion callback
        if self.completion_callback:
            self.completion_callback(success)
            
        # Cleanup
        self.dialog.grab_release()
        self.dialog.destroy()
        self.dialog = None
        self.is_shown = False
        
    def close(self):
        """Public method to close dialog"""
        if self.dialog and self.is_shown:
            self._close_dialog()
            
    def _truncate_filename(self, filename: str, max_length: int = 50) -> str:
        """Truncate filename for display if too long"""
        if len(filename) <= max_length:
            return filename
        return "..." + filename[-(max_length - 3):]
    
    def is_visible(self) -> bool:
        """Check if dialog is currently visible"""
        return self.is_shown and self.dialog is not None


# Example usage and testing
if __name__ == "__main__":
    def test_progress_dialog():
        """Test the progress dialog with simulated progress"""
        root = tk.Tk()
        root.title("Progress Dialog Test")
        root.geometry("300x200")
        
        dialog = None
        
        def simulate_progress():
            """Simulate a batch operation with progress updates"""
            import threading
            
            def worker():
                files = [f"file_{i:03d}.txt" for i in range(50)]
                
                for i, filename in enumerate(files):
                    if dialog and dialog.is_cancelled:
                        break
                        
                    time.sleep(0.1)  # Simulate processing time
                    
                    progress = ProgressInfo(
                        current_file=filename,
                        processed_files=i + 1,
                        total_files=len(files),
                        percentage=((i + 1) / len(files)) * 100,
                        operation_name="Renaming Files"
                    )
                    
                    if dialog:
                        dialog.update_progress(progress)
                        
                # Mark as completed
                if dialog and not dialog.is_cancelled:
                    final_progress = ProgressInfo(
                        current_file="Operation completed successfully!",
                        processed_files=len(files),
                        total_files=len(files),
                        percentage=100.0,
                        operation_name="Renaming Files",
                        is_completed=True,
                        can_cancel=False
                    )
                    dialog.update_progress(final_progress)
                    
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            
        def start_operation():
            nonlocal dialog
            dialog = ProgressDialog(root, "Batch File Rename")
            dialog.show(
                cancel_callback=lambda: print("Operation cancelled"),
                completion_callback=lambda success: print(f"Operation completed: {success}")
            )
            simulate_progress()
            
        # Test button
        ttk.Button(root, text="Start Operation", command=start_operation).pack(pady=50)
        
        root.mainloop()
        
    test_progress_dialog()