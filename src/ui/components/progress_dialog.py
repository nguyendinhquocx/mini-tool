"""
Progress Dialog with Enhanced Error Handling

Provides sophisticated progress tracking with error handling, recovery options,
and user-friendly status updates during long operations.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, Any, List
import threading
import time
from dataclasses import dataclass
from enum import Enum

from ...core.models.error_models import ApplicationError
from ...core.utils.error_handler import ApplicationErrorException
from .error_handler import ErrorHandler


class ProgressStatus(Enum):
    """Status of progress operation"""
    PREPARING = "preparing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"
    PAUSED = "paused"


@dataclass
class ProgressState:
    """Current state of progress operation"""
    status: ProgressStatus
    current_item: int = 0
    total_items: int = 0
    current_file: str = ""
    operation_name: str = ""
    elapsed_time: float = 0.0
    estimated_remaining: Optional[float] = None
    error: Optional[ApplicationError] = None
    warnings: List[ApplicationError] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    @property
    def progress_percent(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.current_item / self.total_items) * 100
    
    @property
    def items_remaining(self) -> int:
        """Get number of items remaining"""
        return max(0, self.total_items - self.current_item)


class EnhancedProgressDialog:
    """Enhanced progress dialog with error handling and recovery options"""
    
    def __init__(self, parent: Optional[tk.Widget], title: str = "Operation in Progress"):
        self.parent = parent
        self.title = title
        self.dialog = None
        self.state = ProgressState(ProgressStatus.PREPARING)
        self.start_time = time.time()
        self.cancelled = False
        self.paused = False
        self.recovery_mode = False
        
        # UI components
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar()
        self.file_var = tk.StringVar()
        self.time_var = tk.StringVar()
        self.items_var = tk.StringVar()
        
        # Callbacks
        self.cancel_callback: Optional[Callable[[], None]] = None
        self.pause_callback: Optional[Callable[[], None]] = None
        self.resume_callback: Optional[Callable[[], None]] = None
        
    def show(self) -> bool:
        """Show progress dialog and return True if completed successfully"""
        self._create_dialog()
        self._update_ui()
        
        # Start UI update loop
        self._schedule_update()
        
        return self.state.status == ProgressStatus.COMPLETED
    
    def _create_dialog(self):
        """Create the progress dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.geometry("500x350")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()
        
        # Prevent closing with X button
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close_attempt)
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self._center_dialog()
        
        self._create_widgets()
    
    def _center_dialog(self):
        """Center dialog on parent or screen"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        
        if self.parent:
            x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (width // 2)
            y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (height // 2)
        else:
            x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Header with operation name
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 15))
        
        operation_label = ttk.Label(header_frame, text=self.state.operation_name or "Processing...", 
                                   font=('Segoe UI', 12, 'bold'))
        operation_label.pack()
        
        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.pack(fill="x", pady=(0, 10))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          maximum=100, length=400)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        # Progress details
        details_frame = ttk.Frame(progress_frame)
        details_frame.pack(fill="x")
        
        ttk.Label(details_frame, text="Status:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        status_label = ttk.Label(details_frame, textvariable=self.status_var)
        status_label.grid(row=0, column=1, sticky="w")
        
        ttk.Label(details_frame, text="Items:").grid(row=1, column=0, sticky="w", padx=(0, 5))
        items_label = ttk.Label(details_frame, textvariable=self.items_var)
        items_label.grid(row=1, column=1, sticky="w")
        
        ttk.Label(details_frame, text="Time:").grid(row=2, column=0, sticky="w", padx=(0, 5))
        time_label = ttk.Label(details_frame, textvariable=self.time_var)
        time_label.grid(row=2, column=1, sticky="w")
        
        # Current file section
        file_frame = ttk.LabelFrame(main_frame, text="Current File", padding="10")
        file_frame.pack(fill="x", pady=(0, 10))
        
        self.file_label = ttk.Label(file_frame, textvariable=self.file_var, 
                                   font=('Segoe UI', 9), wraplength=450)
        self.file_label.pack(fill="x")
        
        # Error/Warning section (initially hidden)
        self.error_frame = ttk.LabelFrame(main_frame, text="Issues", padding="10")
        
        self.error_text = tk.Text(self.error_frame, height=4, wrap=tk.WORD, 
                                 font=('Segoe UI', 9), state='disabled')
        self.error_text.pack(fill="both", expand=True)
        
        # Control buttons
        self._create_control_buttons(main_frame)
    
    def _create_control_buttons(self, parent):
        """Create control buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(side="bottom", fill="x", pady=(15, 0))
        
        # Left side - Recovery options (hidden initially)
        self.recovery_frame = ttk.Frame(button_frame)
        
        self.skip_btn = ttk.Button(self.recovery_frame, text="Skip Current", 
                                  command=self._skip_current, state='disabled')
        self.skip_btn.pack(side="left", padx=(0, 5))
        
        self.retry_btn = ttk.Button(self.recovery_frame, text="Retry", 
                                   command=self._retry_current, state='disabled')
        self.retry_btn.pack(side="left", padx=(0, 5))
        
        # Right side - Main controls
        control_frame = ttk.Frame(button_frame)
        control_frame.pack(side="right")
        
        self.pause_btn = ttk.Button(control_frame, text="Pause", 
                                   command=self._toggle_pause)
        self.pause_btn.pack(side="left", padx=(0, 5))
        
        self.cancel_btn = ttk.Button(control_frame, text="Cancel", 
                                    command=self._cancel_operation)
        self.cancel_btn.pack(side="left")
    
    def update_progress(self, current: int, total: int, current_file: str = "", 
                       operation_name: str = "", status: str = ""):
        """Update progress information"""
        self.state.current_item = current
        self.state.total_items = total
        self.state.current_file = current_file
        if operation_name:
            self.state.operation_name = operation_name
        
        if current >= total and total > 0:
            self.state.status = ProgressStatus.COMPLETED
        elif self.state.status == ProgressStatus.PREPARING:
            self.state.status = ProgressStatus.IN_PROGRESS
        
        # Schedule UI update on main thread
        if self.dialog:
            self.dialog.after_idle(self._update_ui)
    
    def add_error(self, error: ApplicationError):
        """Add error to the dialog"""
        self.state.error = error
        self.state.status = ProgressStatus.ERROR
        
        if self.dialog:
            self.dialog.after_idle(self._show_error_recovery)
    
    def add_warning(self, warning: ApplicationError):
        """Add warning to the dialog"""
        self.state.warnings.append(warning)
        
        if self.dialog:
            self.dialog.after_idle(self._update_warning_display)
    
    def _update_ui(self):
        """Update UI elements"""
        if not self.dialog:
            return
        
        # Update progress bar
        self.progress_var.set(self.state.progress_percent)
        
        # Update status
        status_text = self._get_status_text()
        self.status_var.set(status_text)
        
        # Update file
        if self.state.current_file:
            # Handle both Windows and Unix path separators
            file_name = self.state.current_file.split('\\')[-1].split('/')[-1]
            self.file_var.set(file_name)
        
        # Update time
        self.state.elapsed_time = time.time() - self.start_time
        time_text = self._format_time_display()
        self.time_var.set(time_text)
        
        # Update items count
        items_text = f"{self.state.current_item} of {self.state.total_items}"
        if self.state.total_items > 0:
            items_text += f" ({self.state.progress_percent:.1f}%)"
        self.items_var.set(items_text)
        
        # Update button states
        self._update_button_states()
    
    def _get_status_text(self) -> str:
        """Get current status text"""
        status_map = {
            ProgressStatus.PREPARING: "Preparing...",
            ProgressStatus.IN_PROGRESS: "Processing files...",
            ProgressStatus.COMPLETED: "Completed successfully",
            ProgressStatus.CANCELLED: "Cancelled by user",
            ProgressStatus.ERROR: "Error occurred",
            ProgressStatus.PAUSED: "Paused"
        }
        return status_map.get(self.state.status, "Unknown")
    
    def _format_time_display(self) -> str:
        """Format time display"""
        elapsed = int(self.state.elapsed_time)
        elapsed_str = f"{elapsed // 60}:{elapsed % 60:02d}"
        
        if self.state.estimated_remaining and self.state.status == ProgressStatus.IN_PROGRESS:
            remaining = int(self.state.estimated_remaining)
            remaining_str = f"{remaining // 60}:{remaining % 60:02d}"
            return f"{elapsed_str} elapsed, ~{remaining_str} remaining"
        else:
            return f"{elapsed_str} elapsed"
    
    def _update_button_states(self):
        """Update button states based on current status"""
        if self.state.status == ProgressStatus.COMPLETED:
            self.pause_btn.config(state='disabled')
            self.cancel_btn.config(text="Close")
            if hasattr(self, 'recovery_frame'):
                self.recovery_frame.pack_forget()
        elif self.state.status == ProgressStatus.ERROR:
            self.pause_btn.config(state='disabled')
            self.recovery_frame.pack(side="left", padx=(0, 20))
            self.skip_btn.config(state='normal')
            self.retry_btn.config(state='normal')
        elif self.state.status == ProgressStatus.PAUSED:
            self.pause_btn.config(text="Resume")
        else:
            self.pause_btn.config(text="Pause", state='normal')
    
    def _show_error_recovery(self):
        """Show error recovery options"""
        if not self.state.error:
            return
        
        # Show error in text area
        self.error_frame.pack(fill="x", pady=(0, 10))
        
        self.error_text.config(state='normal')
        self.error_text.delete('1.0', tk.END)
        self.error_text.insert('1.0', self.state.error.to_user_message())
        self.error_text.config(state='disabled')
        
        # Show recovery options if available
        if self.state.error.recovery_options:
            recovery_action = ErrorHandler.handle_application_error(self.state.error, self.dialog)
            if recovery_action:
                self._handle_recovery_action(recovery_action)
    
    def _update_warning_display(self):
        """Update warning display"""
        if not self.state.warnings:
            return
        
        warning_count = len(self.state.warnings)
        if warning_count > 0:
            # Update status to show warnings
            current_status = self.status_var.get()
            if "warning" not in current_status.lower():
                self.status_var.set(f"{current_status} ({warning_count} warning{'s' if warning_count > 1 else ''})")
    
    def _handle_recovery_action(self, action: str):
        """Handle recovery action from error dialog"""
        if action == "skip":
            self._skip_current()
        elif action == "retry":
            self._retry_current()
        elif action == "cancel":
            self._cancel_operation()
        else:
            # Custom recovery action - continue with operation
            self.state.status = ProgressStatus.IN_PROGRESS
            self.state.error = None
            self._update_ui()
    
    def _skip_current(self):
        """Skip current file and continue"""
        self.state.error = None
        self.state.status = ProgressStatus.IN_PROGRESS
        self.error_frame.pack_forget()
        self._update_ui()
        
        # Notify operation to skip current file
        if hasattr(self, 'skip_callback') and self.skip_callback:
            self.skip_callback()
    
    def _retry_current(self):
        """Retry current file"""
        self.state.error = None
        self.state.status = ProgressStatus.IN_PROGRESS
        self.error_frame.pack_forget()
        self._update_ui()
        
        # Notify operation to retry current file
        if hasattr(self, 'retry_callback') and self.retry_callback:
            self.retry_callback()
    
    def _toggle_pause(self):
        """Toggle pause/resume"""
        if self.state.status == ProgressStatus.PAUSED:
            self.state.status = ProgressStatus.IN_PROGRESS
            self.paused = False
            if self.resume_callback:
                self.resume_callback()
        else:
            self.state.status = ProgressStatus.PAUSED
            self.paused = True
            if self.pause_callback:
                self.pause_callback()
        
        self._update_ui()
    
    def _cancel_operation(self):
        """Cancel the operation"""
        if self.state.status == ProgressStatus.COMPLETED:
            self._close_dialog()
            return
        
        # Confirm cancellation
        if messagebox.askyesno("Cancel Operation", 
                              "Are you sure you want to cancel the operation?", 
                              parent=self.dialog):
            self.cancelled = True
            self.state.status = ProgressStatus.CANCELLED
            
            if self.cancel_callback:
                self.cancel_callback()
            
            self._close_dialog()
    
    def _on_close_attempt(self):
        """Handle attempt to close dialog with X button"""
        if self.state.status in [ProgressStatus.COMPLETED, ProgressStatus.CANCELLED, ProgressStatus.ERROR]:
            self._close_dialog()
        else:
            # Ask for confirmation to cancel
            self._cancel_operation()
    
    def _close_dialog(self):
        """Close the dialog"""
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None
    
    def _schedule_update(self):
        """Schedule periodic UI updates"""
        if self.dialog and self.state.status not in [ProgressStatus.COMPLETED, ProgressStatus.CANCELLED]:
            self._update_ui()
            self.dialog.after(500, self._schedule_update)  # Update every 500ms
    
    def set_callbacks(self, cancel_callback: Optional[Callable] = None,
                     pause_callback: Optional[Callable] = None,
                     resume_callback: Optional[Callable] = None,
                     skip_callback: Optional[Callable] = None,
                     retry_callback: Optional[Callable] = None):
        """Set operation callbacks"""
        self.cancel_callback = cancel_callback
        self.pause_callback = pause_callback
        self.resume_callback = resume_callback
        if hasattr(self, 'skip_callback'):
            self.skip_callback = skip_callback
        else:
            setattr(self, 'skip_callback', skip_callback)
        if hasattr(self, 'retry_callback'):
            self.retry_callback = retry_callback
        else:
            setattr(self, 'retry_callback', retry_callback)
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self.cancelled
    
    def is_paused(self) -> bool:
        """Check if operation is paused"""
        return self.paused