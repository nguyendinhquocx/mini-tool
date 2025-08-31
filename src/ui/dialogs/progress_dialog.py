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
    """Progress information for batch operations"""
    current_file: str = ""
    processed_files: int = 0
    total_files: int = 0
    percentage: float = 0.0
    operation_name: str = "Processing"
    can_cancel: bool = True
    is_completed: bool = False
    error_message: Optional[str] = None


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
        self.dialog.geometry("450x200")
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
        dialog_width = 450
        dialog_height = 200
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
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
            current_file = info.current_file
            if len(current_file) > 50:
                current_file = "..." + current_file[-47:]
            self.current_file_label.config(text=current_file)
            
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
        """Handle operation completion"""
        if not self.dialog or not self.is_shown:
            return
            
        # Change cancel button to "Close"
        if self.cancel_button:
            self.cancel_button.config(text="Close", state='normal')
            
        # Auto-close after delay if no errors
        if not self.progress_info.error_message:
            self.dialog.after(2000, self._close_dialog)  # Close after 2 seconds
            
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