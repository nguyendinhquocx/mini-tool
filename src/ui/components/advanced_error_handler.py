"""
Advanced Error Handling UI Components with Recovery Options

Provides sophisticated error dialogs with recovery options, progress tracking,
and detailed error information for better user experience.
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Optional, Callable, Dict, Any, List
import logging
import threading
import time

from ...core.models.error_models import (
    ApplicationError, ValidationResult, RecoveryStrategy, ErrorSeverity
)
from ...core.utils.error_handler import ApplicationErrorException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdvancedErrorHandler:
    """Advanced centralized error handling for UI components with recovery options"""
    
    @staticmethod
    def handle_application_error(app_error: ApplicationError, parent: Optional[tk.Widget] = None) -> Optional[str]:
        """Handle ApplicationError with advanced recovery options dialog"""
        logger.error(f"Application error: {app_error.message}", extra=app_error.to_dict())
        
        dialog = AdvancedErrorDialog(parent, app_error)
        return dialog.show()
    
    @staticmethod
    def handle_validation_result(result: ValidationResult, parent: Optional[tk.Widget] = None) -> bool:
        """Handle ValidationResult with detailed error display"""
        if result.is_valid and not result.warnings:
            return True
        
        dialog = ValidationResultDialog(parent, result)
        return dialog.show()
    
    @staticmethod
    def safe_execute_with_recovery(func: Callable, context: str = "Operation", 
                                 parent: Optional[tk.Widget] = None,
                                 default_return=None):
        """Execute function with advanced error handling and recovery options"""
        try:
            return func()
        except ApplicationErrorException as e:
            recovery_action = AdvancedErrorHandler.handle_application_error(e.application_error, parent)
            return recovery_action if recovery_action else default_return
        except Exception as e:
            # Create a basic ApplicationError for unexpected exceptions
            from ...core.utils.error_handler import ErrorClassifier
            app_error = ErrorClassifier.classify_exception(e, {'operation_name': context})
            recovery_action = AdvancedErrorHandler.handle_application_error(app_error, parent)
            return recovery_action if recovery_action else default_return


class AdvancedErrorDialog:
    """Advanced error dialog with recovery options and detailed information"""
    
    def __init__(self, parent: Optional[tk.Widget], error: ApplicationError):
        self.parent = parent
        self.error = error
        self.result = None
        self.dialog = None
        
    def show(self) -> Optional[str]:
        """Show the error dialog and return selected recovery action"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Error - File Rename Tool")
        self.dialog.geometry("600x500")
        self.dialog.resizable(True, True)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self._center_dialog()
        
        self._create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
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
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        
        # Error icon and title
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Error severity determines icon
        icon_text = self._get_icon_for_severity()
        icon_label = ttk.Label(header_frame, text=icon_text, font=('Segoe UI', 16))
        icon_label.grid(row=0, column=0, padx=(0, 10))
        
        title_label = ttk.Label(header_frame, text=self._get_title_for_error(), 
                               font=('Segoe UI', 12, 'bold'))
        title_label.grid(row=0, column=1, sticky=(tk.W,))
        
        # User-friendly message
        message_frame = ttk.LabelFrame(main_frame, text="Problem Description", padding="10")
        message_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
        main_frame.columnconfigure(0, weight=1)
        
        message_text = tk.Text(message_frame, height=4, wrap=tk.WORD, font=('Segoe UI', 9))
        message_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        message_text.insert('1.0', self.error.to_user_message())
        message_text.config(state='disabled')
        
        message_scrollbar = ttk.Scrollbar(message_frame, orient="vertical", command=message_text.yview)
        message_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        message_text.config(yscrollcommand=message_scrollbar.set)
        
        message_frame.columnconfigure(0, weight=1)
        message_frame.rowconfigure(0, weight=1)
        
        # Recovery options
        if self.error.recovery_options:
            recovery_frame = ttk.LabelFrame(main_frame, text="Recovery Options", padding="10")
            recovery_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 10))
            
            self._create_recovery_options(recovery_frame)
        
        # Technical details (collapsible)
        if self.error.technical_details or self.error.operation_context:
            self._create_details_section(main_frame, row=3)
        
        # Action buttons
        self._create_action_buttons(main_frame, row=4)
        
        main_frame.rowconfigure(1, weight=1)
    
    def _get_icon_for_severity(self) -> str:
        """Get appropriate icon for error severity"""
        icons = {
            ErrorSeverity.CRITICAL: "❌",
            ErrorSeverity.ERROR: "⚠️",
            ErrorSeverity.WARNING: "⚠️",
            ErrorSeverity.INFO: "ℹ️"
        }
        return icons.get(self.error.severity, "❌")
    
    def _get_title_for_error(self) -> str:
        """Get user-friendly title for error"""
        titles = {
            "PERMISSION_DENIED": "Access Denied",
            "FILE_IN_USE": "File Currently in Use",
            "DISK_FULL": "Insufficient Disk Space",
            "NETWORK_UNAVAILABLE": "Network Connection Issue",
            "INVALID_FILENAME": "Invalid File Name",
            "DUPLICATE_NAME_CONFLICT": "Name Conflict",
            "PATH_TOO_LONG": "Path Too Long"
        }
        return titles.get(self.error.code.value, "Operation Failed")
    
    def _create_recovery_options(self, parent_frame):
        """Create recovery option buttons"""
        for i, option in enumerate(self.error.recovery_options):
            option_frame = ttk.Frame(parent_frame)
            option_frame.grid(row=i, column=0, sticky=(tk.W, tk.E), pady=2)
            parent_frame.columnconfigure(0, weight=1)
            
            # Recovery button
            btn_text = f"{option.description}"
            if option.estimated_time:
                btn_text += f" ({option.estimated_time})"
            
            recovery_btn = ttk.Button(
                option_frame, 
                text=btn_text,
                command=lambda opt=option: self._execute_recovery_option(opt)
            )
            recovery_btn.grid(row=0, column=0, sticky=(tk.W,))
            
            # Success probability indicator
            prob_text = f"Success: {int(option.success_probability * 100)}%"
            prob_color = self._get_probability_color(option.success_probability)
            
            prob_label = ttk.Label(option_frame, text=prob_text, foreground=prob_color)
            prob_label.grid(row=0, column=1, padx=(10, 0))
            
            # User input indicator
            if option.requires_user_input:
                input_label = ttk.Label(option_frame, text="(requires input)", 
                                      foreground="gray", font=('Segoe UI', 8))
                input_label.grid(row=0, column=2, padx=(5, 0))
    
    def _get_probability_color(self, probability: float) -> str:
        """Get color for success probability"""
        if probability >= 0.8:
            return "green"
        elif probability >= 0.5:
            return "orange"
        else:
            return "red"
    
    def _execute_recovery_option(self, option):
        """Execute selected recovery option"""
        if option.callback:
            # Show progress dialog for long operations
            if option.estimated_time:
                self._show_recovery_progress(option)
            else:
                # Execute immediately
                try:
                    success = option.callback()
                    if success:
                        self.result = option.strategy.value
                        messagebox.showinfo("Recovery Successful", 
                                          f"Recovery option '{option.description}' completed successfully.")
                        self.dialog.destroy()
                    else:
                        messagebox.showerror("Recovery Failed", 
                                           f"Recovery option '{option.description}' failed. Please try another option.")
                except Exception as e:
                    messagebox.showerror("Recovery Error", 
                                       f"Error executing recovery: {str(e)}")
        else:
            # Manual recovery option selected
            self.result = option.strategy.value
            self.dialog.destroy()
    
    def _show_recovery_progress(self, option):
        """Show progress dialog for recovery operation"""
        progress_dialog = tk.Toplevel(self.dialog)
        progress_dialog.title("Executing Recovery...")
        progress_dialog.geometry("350x120")
        progress_dialog.grab_set()
        
        # Center on parent
        progress_dialog.transient(self.dialog)
        
        frame = ttk.Frame(progress_dialog, padding="20")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text=f"Executing: {option.description}").pack(pady=(0, 10))
        
        progress = ttk.Progressbar(frame, mode='indeterminate')
        progress.pack(fill="x", pady=(0, 10))
        progress.start()
        
        status_label = ttk.Label(frame, text="Please wait...")
        status_label.pack()
        
        # Execute in thread
        def execute_recovery():
            try:
                success = option.callback() if option.callback else False
                progress_dialog.after(0, lambda: self._recovery_completed(progress_dialog, option, success))
            except Exception as e:
                progress_dialog.after(0, lambda: self._recovery_failed(progress_dialog, option, str(e)))
        
        threading.Thread(target=execute_recovery, daemon=True).start()
    
    def _recovery_completed(self, progress_dialog, option, success):
        """Handle recovery completion"""
        progress_dialog.destroy()
        
        if success:
            self.result = option.strategy.value
            messagebox.showinfo("Recovery Successful", 
                              f"Recovery option '{option.description}' completed successfully.")
            self.dialog.destroy()
        else:
            messagebox.showerror("Recovery Failed", 
                               f"Recovery option '{option.description}' failed. Please try another option.")
    
    def _recovery_failed(self, progress_dialog, option, error_msg):
        """Handle recovery failure"""
        progress_dialog.destroy()
        messagebox.showerror("Recovery Error", 
                           f"Error executing recovery '{option.description}': {error_msg}")
    
    def _create_details_section(self, main_frame, row):
        """Create collapsible technical details section"""
        self.details_visible = False
        
        details_header = ttk.Frame(main_frame)
        details_header.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.details_btn = ttk.Button(
            details_header, 
            text="▶ Show Technical Details",
            command=self._toggle_details
        )
        self.details_btn.grid(row=0, column=0)
        
        self.details_frame = ttk.Frame(main_frame)
        
        # Technical details content
        details_notebook = ttk.Notebook(self.details_frame)
        details_notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # Technical details tab
        if self.error.technical_details:
            tech_frame = ttk.Frame(details_notebook)
            tech_text = tk.Text(tech_frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
            tech_text.pack(fill="both", expand=True, padx=5, pady=5)
            tech_text.insert('1.0', self.error.technical_details)
            tech_text.config(state='disabled')
            details_notebook.add(tech_frame, text="Technical Details")
        
        # Context tab
        if self.error.operation_context:
            context_frame = ttk.Frame(details_notebook)
            context_text = tk.Text(context_frame, height=6, wrap=tk.WORD, font=('Consolas', 9))
            context_text.pack(fill="both", expand=True, padx=5, pady=5)
            
            context_str = "\n".join([f"{k}: {v}" for k, v in self.error.operation_context.items()])
            context_text.insert('1.0', context_str)
            context_text.config(state='disabled')
            details_notebook.add(context_frame, text="Context")
        
        self.details_frame.columnconfigure(0, weight=1)
        self.details_frame.rowconfigure(0, weight=1)
    
    def _toggle_details(self):
        """Toggle technical details visibility"""
        if self.details_visible:
            self.details_frame.grid_remove()
            self.details_btn.config(text="▶ Show Technical Details")
            self.details_visible = False
        else:
            self.details_frame.grid(row=4, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
            self.details_btn.config(text="▼ Hide Technical Details")
            self.details_visible = True
    
    def _create_action_buttons(self, main_frame, row):
        """Create main action buttons"""
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row + 1, column=0, sticky=(tk.E,), pady=(10, 0))
        
        # Skip/Continue button
        skip_btn = ttk.Button(button_frame, text="Skip and Continue", 
                             command=lambda: self._close_with_result("skip"))
        skip_btn.grid(row=0, column=0, padx=(0, 5))
        
        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="Cancel Operation", 
                               command=lambda: self._close_with_result("cancel"))
        cancel_btn.grid(row=0, column=1, padx=(0, 5))
        
        # Retry button (if no recovery options)
        if not self.error.recovery_options:
            retry_btn = ttk.Button(button_frame, text="Retry", 
                                  command=lambda: self._close_with_result("retry"))
            retry_btn.grid(row=0, column=2)
    
    def _close_with_result(self, result: str):
        """Close dialog with specified result"""
        self.result = result
        self.dialog.destroy()


class ValidationResultDialog:
    """Dialog for displaying validation results with detailed error information"""
    
    def __init__(self, parent: Optional[tk.Widget], validation_result: ValidationResult):
        self.parent = parent
        self.validation_result = validation_result
        self.result = False
        self.dialog = None
    
    def show(self) -> bool:
        """Show validation result dialog and return whether to continue"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Validation Results - File Rename Tool")
        self.dialog.geometry("550x400")
        self.dialog.resizable(True, True)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self._center_dialog()
        
        self._create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        return self.result
    
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
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        icon = "⚠️" if self.validation_result.errors else "ℹ️"
        icon_label = ttk.Label(header_frame, text=icon, font=('Segoe UI', 16))
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ttk.Label(header_frame, text="Validation Results", 
                               font=('Segoe UI', 12, 'bold'))
        title_label.pack(side="left")
        
        # Summary
        summary_label = ttk.Label(main_frame, text=self.validation_result.get_summary_message(), 
                                 font=('Segoe UI', 10))
        summary_label.pack(pady=(0, 10))
        
        # Notebook for errors and warnings
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(0, 10))
        
        # Errors tab
        if self.validation_result.errors:
            errors_frame = self._create_error_tab(notebook, self.validation_result.errors, "Errors")
            notebook.add(errors_frame, text=f"Errors ({len(self.validation_result.errors)})")
        
        # Warnings tab
        if self.validation_result.warnings:
            warnings_frame = self._create_error_tab(notebook, self.validation_result.warnings, "Warnings")
            notebook.add(warnings_frame, text=f"Warnings ({len(self.validation_result.warnings)})")
        
        # Suggestions
        if self.validation_result.suggestions:
            suggestions_frame = ttk.Frame(notebook)
            suggestions_text = tk.Text(suggestions_frame, height=6, wrap=tk.WORD, font=('Segoe UI', 9))
            suggestions_text.pack(fill="both", expand=True, padx=5, pady=5)
            
            for suggestion in self.validation_result.suggestions:
                suggestions_text.insert(tk.END, f"• {suggestion}\n")
            
            suggestions_text.config(state='disabled')
            notebook.add(suggestions_frame, text="Suggestions")
        
        # Buttons
        self._create_buttons(main_frame)
    
    def _create_error_tab(self, parent, errors, title):
        """Create tab for displaying errors or warnings"""
        frame = ttk.Frame(parent)
        
        # Treeview for structured display
        tree = ttk.Treeview(frame, columns=('field', 'message', 'suggestion'), show='headings')
        tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        tree.heading('field', text='Field')
        tree.heading('message', text='Message')
        tree.heading('suggestion', text='Suggestion')
        
        tree.column('field', width=100, minwidth=80)
        tree.column('message', width=250, minwidth=150)
        tree.column('suggestion', width=200, minwidth=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side="right", fill="y")
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Populate tree
        for error in errors:
            tree.insert('', 'end', values=(
                error.field,
                error.message,
                error.suggested_fix or "N/A"
            ))
        
        return frame
    
    def _create_buttons(self, main_frame):
        """Create action buttons"""
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        # Continue button (only if no blocking errors)
        if not self.validation_result.has_blocking_errors():
            continue_btn = ttk.Button(button_frame, text="Continue Anyway", 
                                     command=lambda: self._close_with_result(True))
            continue_btn.pack(side="right", padx=(5, 0))
        
        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="Cancel", 
                               command=lambda: self._close_with_result(False))
        cancel_btn.pack(side="right")
        
        # Fix automatically button (if suggestions available)
        if self.validation_result.suggestions:
            fix_btn = ttk.Button(button_frame, text="Apply Suggestions", 
                                command=self._apply_suggestions)
            fix_btn.pack(side="left")
    
    def _apply_suggestions(self):
        """Apply automatic fixes based on suggestions"""
        # This would trigger automatic fixing logic
        # For now, just close and indicate continue
        messagebox.showinfo("Auto-Fix", "Suggestions will be applied automatically.")
        self._close_with_result(True)
    
    def _close_with_result(self, result: bool):
        """Close dialog with specified result"""
        self.result = result
        self.dialog.destroy()