"""
Partial Failure Dialog UI Component

Provides user interface for handling partial operation failures with detailed
error reporting, recovery options, and batch resolution capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, List, Tuple, Callable
import threading

from ...core.services.partial_failure_handler import (
    PartialFailureReport, FailedFileOperation, PartialFailureStrategy, FailureResolution
)
from ...core.models.error_models import ApplicationError, RecoveryStrategy
from .advanced_error_handler import AdvancedErrorHandler


class PartialFailureDialog:
    """Advanced dialog for handling partial operation failures"""
    
    def __init__(self, parent: Optional[tk.Widget], report: PartialFailureReport):
        self.parent = parent
        self.report = report
        self.selected_strategy = None
        self.files_to_retry: List[FailedFileOperation] = []
        self.individual_resolutions: Dict[str, FailureResolution] = {}
        self.dialog = None
        
    def show_and_get_strategy(self) -> Tuple[PartialFailureStrategy, List[FailedFileOperation]]:
        """Show dialog and return user-selected strategy and files to retry"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Operation Completed with Issues - File Rename Tool")
        self.dialog.geometry("800x600")
        self.dialog.resizable(True, True)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.transient(self.parent)
        self._center_dialog()
        
        self._create_widgets()
        
        # Wait for dialog to close
        self.dialog.wait_window()
        
        return self.selected_strategy or PartialFailureStrategy.SKIP_FAILED_CONTINUE, self.files_to_retry
    
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
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # Header with summary
        self._create_header(main_frame)
        
        # Main content notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(15, 0))
        
        # Summary tab
        summary_frame = self._create_summary_tab(notebook)
        notebook.add(summary_frame, text="Summary")
        
        # Failed Files tab
        if self.report.failed_files:
            failed_frame = self._create_failed_files_tab(notebook)
            notebook.add(failed_frame, text=f"Failed Files ({len(self.report.failed_files)})")
        
        # Recovery Options tab
        recovery_frame = self._create_recovery_options_tab(notebook)
        notebook.add(recovery_frame, text="Recovery Options")
        
        # Action buttons
        self._create_action_buttons(main_frame)
    
    def _create_header(self, parent):
        """Create header with operation summary"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 15))
        
        # Icon and title
        icon_frame = ttk.Frame(header_frame)
        icon_frame.pack(fill="x")
        
        # Status icon based on success rate
        if self.report.success_rate >= 80:
            icon = "⚠️"
            title = "Operation Completed with Minor Issues"
        elif self.report.success_rate >= 50:
            icon = "⚠️"
            title = "Operation Completed with Issues"
        else:
            icon = "❌"
            title = "Operation Failed with Multiple Errors"
        
        icon_label = ttk.Label(icon_frame, text=icon, font=('Segoe UI', 20))
        icon_label.pack(side="left", padx=(0, 10))
        
        title_label = ttk.Label(icon_frame, text=title, font=('Segoe UI', 14, 'bold'))
        title_label.pack(side="left")
        
        # Summary stats
        stats_frame = ttk.Frame(header_frame)
        stats_frame.pack(fill="x", pady=(10, 0))
        
        stats_text = (f"Processed {self.report.total_files} files: "
                     f"{self.report.successful_operations} successful, "
                     f"{self.report.failed_operations} failed")
        
        if self.report.skipped_operations > 0:
            stats_text += f", {self.report.skipped_operations} skipped"
        
        stats_text += f" (Success rate: {self.report.success_rate:.1f}%)"
        
        stats_label = ttk.Label(stats_frame, text=stats_text, font=('Segoe UI', 10))
        stats_label.pack()
    
    def _create_summary_tab(self, notebook) -> ttk.Frame:
        """Create summary tab content"""
        frame = ttk.Frame(notebook)
        
        # Success rate visualization
        progress_frame = ttk.LabelFrame(frame, text="Operation Results", padding="10")
        progress_frame.pack(fill="x", pady=(0, 10))
        
        # Progress bars for visual representation
        success_frame = ttk.Frame(progress_frame)
        success_frame.pack(fill="x", pady=2)
        
        ttk.Label(success_frame, text="Successful:", width=12).pack(side="left")
        success_progress = ttk.Progressbar(success_frame, length=300)
        success_progress.pack(side="left", padx=(5, 10))
        success_progress['value'] = (self.report.successful_operations / self.report.total_files) * 100
        ttk.Label(success_frame, text=f"{self.report.successful_operations}").pack(side="left")
        
        if self.report.failed_operations > 0:
            failed_frame = ttk.Frame(progress_frame)
            failed_frame.pack(fill="x", pady=2)
            
            ttk.Label(failed_frame, text="Failed:", width=12).pack(side="left")
            failed_progress = ttk.Progressbar(failed_frame, length=300)
            failed_progress.pack(side="left", padx=(5, 10))
            failed_progress['value'] = (self.report.failed_operations / self.report.total_files) * 100
            failed_progress.configure(style="red.Horizontal.TProgressbar")
            ttk.Label(failed_frame, text=f"{self.report.failed_operations}").pack(side="left")
        
        # Error categorization
        if self.report.failed_files:
            categories_frame = ttk.LabelFrame(frame, text="Error Categories", padding="10")
            categories_frame.pack(fill="x", pady=(0, 10))
            
            if self.report.critical_errors:
                critical_label = ttk.Label(categories_frame, 
                                         text=f"❌ Critical Errors: {len(self.report.critical_errors)}", 
                                         foreground="red")
                critical_label.pack(anchor="w", pady=2)
            
            if self.report.recoverable_errors:
                recoverable_label = ttk.Label(categories_frame, 
                                            text=f"🔄 Recoverable Errors: {len(self.report.recoverable_errors)}", 
                                            foreground="orange")
                recoverable_label.pack(anchor="w", pady=2)
            
            if self.report.manual_intervention_required:
                manual_label = ttk.Label(categories_frame, 
                                       text=f"👤 Requires Manual Fix: {len(self.report.manual_intervention_required)}", 
                                       foreground="blue")
                manual_label.pack(anchor="w", pady=2)
        
        # Recommendations
        if self.report.recommended_strategy:
            rec_frame = ttk.LabelFrame(frame, text="Recommended Action", padding="10")
            rec_frame.pack(fill="x")
            
            strategy_descriptions = {
                PartialFailureStrategy.SKIP_FAILED_CONTINUE: "Continue operation, skip failed files",
                PartialFailureStrategy.RETRY_FAILED_FILES: "Retry files that can be automatically fixed",
                PartialFailureStrategy.ROLLBACK_ALL_CHANGES: "Undo all changes made in this operation",
                PartialFailureStrategy.STOP_ON_FIRST_ERROR: "Stop operation to prevent further issues",
                PartialFailureStrategy.MANUAL_INTERVENTION: "Review and fix issues individually"
            }
            
            rec_text = strategy_descriptions.get(self.report.recommended_strategy, "Unknown strategy")
            rec_label = ttk.Label(rec_frame, text=f"💡 {rec_text}", font=('Segoe UI', 10, 'bold'))
            rec_label.pack(anchor="w")
        
        return frame
    
    def _create_failed_files_tab(self, notebook) -> ttk.Frame:
        """Create failed files tab content"""
        frame = ttk.Frame(notebook)
        
        # Treeview for failed files
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create treeview with columns
        columns = ('file', 'target', 'error', 'attempts', 'action')
        self.failed_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.failed_tree.heading('file', text='Original File')
        self.failed_tree.heading('target', text='Target Name')
        self.failed_tree.heading('error', text='Error Type')
        self.failed_tree.heading('attempts', text='Attempts')
        self.failed_tree.heading('action', text='Resolution')
        
        self.failed_tree.column('file', width=200, minwidth=150)
        self.failed_tree.column('target', width=200, minwidth=150)
        self.failed_tree.column('error', width=120, minwidth=100)
        self.failed_tree.column('attempts', width=80, minwidth=60, anchor='center')
        self.failed_tree.column('action', width=120, minwidth=100)
        
        # Add scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.failed_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.failed_tree.xview)
        
        self.failed_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.failed_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Populate tree with failed files
        self._populate_failed_files_tree()
        
        # Bind double-click to show error details
        self.failed_tree.bind("<Double-1>", self._on_failed_file_double_click)
        
        # Context menu
        self._create_failed_files_context_menu()
        
        # Individual action buttons
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill="x")
        
        ttk.Button(action_frame, text="Show Error Details", 
                  command=self._show_selected_error_details).pack(side="left", padx=(0, 5))
        
        ttk.Button(action_frame, text="Retry Selected", 
                  command=self._retry_selected_files).pack(side="left", padx=(0, 5))
        
        ttk.Button(action_frame, text="Skip Selected", 
                  command=self._skip_selected_files).pack(side="left")
        
        return frame
    
    def _populate_failed_files_tree(self):
        """Populate the failed files treeview"""
        for failed_file in self.report.failed_files:
            file_name = failed_file.file_path.split('\\\\')[-1]
            target_name = failed_file.target_path.split('\\\\')[-1] if failed_file.target_path else "N/A"
            error_type = self._get_user_friendly_error_type(failed_file.error)
            attempts = f"{failed_file.attempt_count}/{failed_file.max_attempts}"
            
            # Determine default action
            if failed_file.should_auto_retry:
                action = "Auto Retry"
            elif failed_file.requires_manual_intervention:
                action = "Manual Fix"
            else:
                action = "Skip"
            
            item_id = self.failed_tree.insert('', 'end', values=(
                file_name, target_name, error_type, attempts, action
            ))
            
            # Store failed file reference
            self.failed_tree.set(item_id, 'failed_file', failed_file)
    
    def _get_user_friendly_error_type(self, error: ApplicationError) -> str:
        """Convert error code to user-friendly description"""
        error_descriptions = {
            "PERMISSION_DENIED": "Access Denied",
            "FILE_IN_USE": "File Locked",
            "DISK_FULL": "No Space",
            "NETWORK_UNAVAILABLE": "Network Error",
            "INVALID_FILENAME": "Invalid Name",
            "DUPLICATE_NAME_CONFLICT": "Name Conflict",
            "PATH_TOO_LONG": "Path Too Long"
        }
        return error_descriptions.get(error.code.value, error.code.value)
    
    def _create_failed_files_context_menu(self):
        """Create context menu for failed files tree"""
        self.context_menu = tk.Menu(self.dialog, tearoff=0)
        self.context_menu.add_command(label="Show Error Details", command=self._show_selected_error_details)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Retry", command=self._retry_selected_files)
        self.context_menu.add_command(label="Skip", command=self._skip_selected_files)
        self.context_menu.add_command(label="Manual Fix", command=self._manual_fix_selected_files)
        
        def show_context_menu(event):
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
        
        self.failed_tree.bind("<Button-3>", show_context_menu)  # Right-click
    
    def _create_recovery_options_tab(self, notebook) -> ttk.Frame:
        """Create recovery options tab content"""
        frame = ttk.Frame(notebook)
        
        # Available strategies
        strategies_frame = ttk.LabelFrame(frame, text="Available Recovery Strategies", padding="10")
        strategies_frame.pack(fill="x", pady=(0, 15))
        
        self.strategy_var = tk.StringVar(value=self.report.recommended_strategy.value if self.report.recommended_strategy else "skip_failed_continue")
        
        strategy_descriptions = {
            PartialFailureStrategy.SKIP_FAILED_CONTINUE: {
                'title': "Continue Operation (Skip Failed Files)",
                'desc': "Skip files that failed and continue with the operation. Failed files remain unchanged.",
                'icon': "➡️"
            },
            PartialFailureStrategy.RETRY_FAILED_FILES: {
                'title': "Retry Failed Files",
                'desc': "Attempt to retry files that failed due to temporary issues.",
                'icon': "🔄"
            },
            PartialFailureStrategy.ROLLBACK_ALL_CHANGES: {
                'title': "Undo All Changes",
                'desc': "Reverse all successful operations and restore original state.",
                'icon': "↩️"
            },
            PartialFailureStrategy.STOP_ON_FIRST_ERROR: {
                'title': "Stop Operation",
                'desc': "Stop any further processing and review issues individually.",
                'icon': "🛑"
            },
            PartialFailureStrategy.MANUAL_INTERVENTION: {
                'title': "Manual Resolution",
                'desc': "Review and resolve each failed file individually.",
                'icon': "👤"
            }
        }
        
        for strategy in self.report.available_strategies:
            if strategy in strategy_descriptions:
                info = strategy_descriptions[strategy]
                
                # Create radio button frame
                radio_frame = ttk.Frame(strategies_frame)
                radio_frame.pack(fill="x", pady=5)
                
                # Radio button
                radio = ttk.Radiobutton(radio_frame, text="", variable=self.strategy_var, value=strategy.value)
                radio.pack(side="left")
                
                # Icon and title
                title_frame = ttk.Frame(radio_frame)
                title_frame.pack(side="left", fill="x", expand=True, padx=(5, 0))
                
                title_label = ttk.Label(title_frame, text=f"{info['icon']} {info['title']}", 
                                      font=('Segoe UI', 10, 'bold'))
                title_label.pack(anchor="w")
                
                desc_label = ttk.Label(title_frame, text=info['desc'], 
                                     font=('Segoe UI', 9), foreground="gray")
                desc_label.pack(anchor="w")
                
                # Highlight recommended option
                if self.report.recommended_strategy == strategy:
                    title_label.configure(foreground="blue")
                    recommended_badge = ttk.Label(title_frame, text="(Recommended)", 
                                                foreground="blue", font=('Segoe UI', 8, 'italic'))
                    recommended_badge.pack(anchor="w")
        
        # Additional options
        options_frame = ttk.LabelFrame(frame, text="Additional Options", padding="10")
        options_frame.pack(fill="x")
        
        self.create_report_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Generate detailed error report", 
                       variable=self.create_report_var).pack(anchor="w", pady=2)
        
        self.save_successful_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Keep successful changes", 
                       variable=self.save_successful_var).pack(anchor="w", pady=2)
        
        return frame
    
    def _create_action_buttons(self, parent):
        """Create action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(side="bottom", fill="x", pady=(15, 0))
        
        # Left side - Help button
        ttk.Button(button_frame, text="Help", command=self._show_help).pack(side="left")
        
        # Right side - Action buttons
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side="right")
        
        ttk.Button(right_frame, text="Cancel", 
                  command=self._cancel_action).pack(side="left", padx=(0, 10))
        
        ttk.Button(right_frame, text="Apply Selected Strategy", 
                  command=self._apply_strategy).pack(side="left")
    
    def _on_failed_file_double_click(self, event):
        """Handle double-click on failed file item"""
        self._show_selected_error_details()
    
    def _show_selected_error_details(self):
        """Show detailed error information for selected file"""
        selection = self.failed_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a failed file to view details.")
            return
        
        item = selection[0]
        # Get the failed file object (would need to be stored properly)
        for failed_file in self.report.failed_files:
            file_name = failed_file.file_path.split('\\\\')[-1]
            if file_name == self.failed_tree.item(item)['values'][0]:
                # Show advanced error dialog
                AdvancedErrorHandler.handle_application_error(failed_file.error, self.dialog)
                break
    
    def _retry_selected_files(self):
        """Mark selected files for retry"""
        selection = self.failed_tree.selection()
        for item in selection:
            self.failed_tree.set(item, 'action', 'Retry')
    
    def _skip_selected_files(self):
        """Mark selected files to be skipped"""
        selection = self.failed_tree.selection()
        for item in selection:
            self.failed_tree.set(item, 'action', 'Skip')
    
    def _manual_fix_selected_files(self):
        """Mark selected files for manual intervention"""
        selection = self.failed_tree.selection()
        for item in selection:
            self.failed_tree.set(item, 'action', 'Manual Fix')
    
    def _show_help(self):
        """Show help dialog"""
        help_text = \"\"\"
Recovery Strategy Guide:

🔄 Retry Failed Files: Automatically retry files that failed due to temporary issues like network timeouts or file locks.

➡️ Continue Operation: Keep successful changes and skip files that failed. This is usually the safest option.

↩️ Undo All Changes: Restore all files to their original state. Use this if the operation caused unexpected problems.

👤 Manual Resolution: Review each failed file individually and choose specific actions.

🛑 Stop Operation: Cancel any further processing. Use this to prevent additional problems.

Tips:
• Files marked as "Auto Retry" will be automatically retried
• "Manual Fix" items require your attention before proceeding
• Critical errors should typically trigger a rollback
• Success rates below 50% may indicate systematic issues
\"\"\"
        
        messagebox.showinfo("Recovery Help", help_text, parent=self.dialog)
    
    def _apply_strategy(self):
        """Apply the selected strategy and close dialog"""
        try:
            strategy_value = self.strategy_var.get()
            self.selected_strategy = PartialFailureStrategy(strategy_value)
            
            # Collect files to retry based on tree selections
            self.files_to_retry = []
            
            for item in self.failed_tree.get_children():
                action = self.failed_tree.item(item)['values'][4]
                if action == 'Retry' or action == 'Auto Retry':
                    # Find corresponding failed file
                    file_name = self.failed_tree.item(item)['values'][0]
                    for failed_file in self.report.failed_files:
                        if failed_file.file_path.split('\\\\')[-1] == file_name:
                            self.files_to_retry.append(failed_file)
                            break
            
            self.dialog.destroy()
            
        except ValueError:
            messagebox.showerror("Invalid Selection", "Please select a valid recovery strategy.")
    
    def _cancel_action(self):
        """Cancel and close dialog"""
        self.selected_strategy = None
        self.files_to_retry = []
        self.dialog.destroy()