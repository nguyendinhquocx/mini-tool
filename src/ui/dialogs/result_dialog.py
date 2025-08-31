"""
Result Dialog Component

Displays operation results and summaries after batch operations complete.
Shows success/failure counts, detailed file lists, and error information.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OperationResult:
    """Operation result information for display"""
    operation_id: str
    operation_name: str
    total_files: int
    successful_files: int
    failed_files: int
    skipped_files: int
    operation_duration: float
    success_details: List[Dict[str, str]]
    failure_details: List[Dict[str, str]]
    error_summary: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate operation success rate as percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.successful_files / self.total_files) * 100.0
    
    @property
    def has_failures(self) -> bool:
        """Check if operation had any failures"""
        return self.failed_files > 0
    
    @property
    def status_summary(self) -> str:
        """Get overall operation status"""
        if self.failed_files == 0:
            return "Completed Successfully"
        elif self.successful_files == 0:
            return "Operation Failed"
        else:
            return "Completed with Errors"


class ResultDialog:
    """
    Modal result dialog for batch operation summaries
    
    Features:
    - Operation summary with counts and percentages
    - Detailed success/failure file lists
    - Error messages and suggestions
    - Export option for results
    - Undo option if applicable
    """
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.dialog = None
        self.result: Optional[OperationResult] = None
        
        # Callbacks
        self.undo_callback: Optional[callable] = None
        self.export_callback: Optional[callable] = None
        
        # UI components
        self.notebook: Optional[ttk.Notebook] = None
        self.summary_frame: Optional[ttk.Frame] = None
        self.details_frame: Optional[ttk.Frame] = None
        self.errors_frame: Optional[ttk.Frame] = None
        
    def show(self, result: OperationResult, 
             undo_callback: Optional[callable] = None,
             export_callback: Optional[callable] = None):
        """
        Show the result dialog with operation summary
        
        Args:
            result: Operation result to display
            undo_callback: Function to call for undo operation
            export_callback: Function to call for result export
        """
        self.result = result
        self.undo_callback = undo_callback
        self.export_callback = export_callback
        
        self._create_dialog()
        
    def _create_dialog(self):
        """Create and configure the dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"Operation Results - {self.result.operation_name}")
        self.dialog.geometry("700x500")
        self.dialog.resizable(True, True)
        
        # Center dialog on parent
        self._center_dialog()
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Configure dialog close behavior
        self.dialog.protocol("WM_DELETE_WINDOW", self._close_dialog)
        
        # Create UI components
        self._create_ui_components()
        
    def _center_dialog(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()
        
        # Get parent window position and size
        parent_x = self.parent.winfo_rootx()
        parent_y = self.parent.winfo_rooty()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Calculate center position
        dialog_width = 700
        dialog_height = 500
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
    def _create_ui_components(self):
        """Create all UI components for the dialog"""
        # Main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with operation status
        self._create_header(main_frame)
        
        # Tabbed interface for different result views
        self._create_tabs(main_frame)
        
        # Button frame at bottom
        self._create_buttons(main_frame)
        
    def _create_header(self, parent):
        """Create header with operation summary"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Operation name and status
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            title_frame,
            text=self.result.operation_name,
            font=('Arial', 14, 'bold')
        )
        title_label.pack(side=tk.LEFT)
        
        # Status badge
        status_color = '#28a745' if not self.result.has_failures else '#dc3545' if self.result.successful_files == 0 else '#ffc107'
        status_frame = ttk.Frame(title_frame)
        status_frame.pack(side=tk.RIGHT)
        
        status_label = tk.Label(
            status_frame,
            text=self.result.status_summary,
            bg=status_color,
            fg='white' if status_color != '#ffc107' else 'black',
            padx=10,
            pady=2,
            font=('Arial', 9, 'bold')
        )
        status_label.pack()
        
        # Summary metrics in grid
        metrics_frame = ttk.Frame(header_frame)
        metrics_frame.pack(fill=tk.X)
        
        # Configure grid columns
        for i in range(5):
            metrics_frame.columnconfigure(i, weight=1)
            
        self._add_metric(metrics_frame, "Total Files", str(self.result.total_files), 0)
        self._add_metric(metrics_frame, "Successful", str(self.result.successful_files), 1)
        self._add_metric(metrics_frame, "Failed", str(self.result.failed_files), 2)
        self._add_metric(metrics_frame, "Success Rate", f"{self.result.success_rate:.1f}%", 3)
        self._add_metric(metrics_frame, "Duration", f"{self.result.operation_duration:.2f}s", 4)
        
    def _add_metric(self, parent, label: str, value: str, column: int):
        """Add a metric to the summary grid"""
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=column, padx=5, pady=5, sticky='ew')
        
        ttk.Label(frame, text=label, font=('Arial', 8)).pack()
        ttk.Label(frame, text=value, font=('Arial', 12, 'bold')).pack()
        
    def _create_tabs(self, parent):
        """Create tabbed interface for detailed results"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Summary tab
        self._create_summary_tab()
        
        # Success details tab
        if self.result.successful_files > 0:
            self._create_success_tab()
            
        # Failure details tab
        if self.result.failed_files > 0:
            self._create_failure_tab()
            
    def _create_summary_tab(self):
        """Create summary overview tab"""
        self.summary_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.summary_frame, text="Summary")
        
        # Scrollable text area for summary
        text_frame = ttk.Frame(self.summary_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        summary_text = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            height=15,
            font=('Courier', 10)
        )
        summary_text.pack(fill=tk.BOTH, expand=True)
        
        # Generate summary content
        summary_content = self._generate_summary_text()
        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)
        
    def _create_success_tab(self):
        """Create success details tab"""
        success_frame = ttk.Frame(self.notebook)
        self.notebook.add(success_frame, text=f"Success ({self.result.successful_files})")
        
        # Create treeview for success details
        tree_frame = ttk.Frame(success_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Success files treeview
        columns = ('Original Name', 'New Name', 'Status')
        success_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        success_tree.heading('Original Name', text='Original Name')
        success_tree.heading('New Name', text='New Name')
        success_tree.heading('Status', text='Status')
        
        success_tree.column('Original Name', width=250)
        success_tree.column('New Name', width=250)
        success_tree.column('Status', width=100)
        
        # Add scrollbar
        scrollbar_success = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=success_tree.yview)
        success_tree.configure(yscrollcommand=scrollbar_success.set)
        
        # Pack treeview and scrollbar
        success_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_success.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate with success data
        for detail in self.result.success_details:
            success_tree.insert('', tk.END, values=(
                detail.get('original_name', ''),
                detail.get('new_name', ''),
                detail.get('status', 'Success')
            ))
            
    def _create_failure_tab(self):
        """Create failure details tab"""
        failure_frame = ttk.Frame(self.notebook)
        self.notebook.add(failure_frame, text=f"Failures ({self.result.failed_files})")
        
        # Create treeview for failure details
        tree_frame = ttk.Frame(failure_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Failure files treeview
        columns = ('File Name', 'Error', 'Suggestion')
        failure_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        failure_tree.heading('File Name', text='File Name')
        failure_tree.heading('Error', text='Error Message')
        failure_tree.heading('Suggestion', text='Suggestion')
        
        failure_tree.column('File Name', width=200)
        failure_tree.column('Error', width=250)
        failure_tree.column('Suggestion', width=200)
        
        # Add scrollbar
        scrollbar_failure = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=failure_tree.yview)
        failure_tree.configure(yscrollcommand=scrollbar_failure.set)
        
        # Pack treeview and scrollbar
        failure_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_failure.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate with failure data
        for detail in self.result.failure_details:
            failure_tree.insert('', tk.END, values=(
                detail.get('file_name', ''),
                detail.get('error_message', ''),
                detail.get('suggestion', '')
            ))
            
    def _create_buttons(self, parent):
        """Create button frame with actions"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Left side buttons (actions)
        left_frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)
        
        if self.undo_callback:
            ttk.Button(
                left_frame,
                text="Undo Operation",
                command=self._on_undo_clicked
            ).pack(side=tk.LEFT, padx=(0, 10))
            
        if self.export_callback:
            ttk.Button(
                left_frame,
                text="Export Results",
                command=self._on_export_clicked
            ).pack(side=tk.LEFT)
            
        # Right side buttons (dialog control)
        right_frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)
        
        ttk.Button(
            right_frame,
            text="Close",
            command=self._close_dialog
        ).pack(side=tk.RIGHT)
        
    def _generate_summary_text(self) -> str:
        """Generate detailed summary text"""
        lines = []
        lines.append(f"Operation: {self.result.operation_name}")
        lines.append(f"Operation ID: {self.result.operation_id}")
        lines.append(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Duration: {self.result.operation_duration:.2f} seconds")
        lines.append("")
        
        lines.append("RESULTS SUMMARY")
        lines.append("=" * 50)
        lines.append(f"Total files processed: {self.result.total_files}")
        lines.append(f"Successfully processed: {self.result.successful_files}")
        lines.append(f"Failed: {self.result.failed_files}")
        lines.append(f"Skipped: {self.result.skipped_files}")
        lines.append(f"Success rate: {self.result.success_rate:.1f}%")
        lines.append("")
        
        if self.result.error_summary:
            lines.append("ERROR SUMMARY")
            lines.append("=" * 50)
            lines.append(self.result.error_summary)
            lines.append("")
            
        if self.result.successful_files > 0:
            lines.append("SUCCESSFUL FILES")
            lines.append("=" * 50)
            for detail in self.result.success_details[:10]:  # Show first 10
                lines.append(f"✓ {detail.get('original_name', '')} → {detail.get('new_name', '')}")
            if len(self.result.success_details) > 10:
                lines.append(f"... and {len(self.result.success_details) - 10} more files")
            lines.append("")
            
        if self.result.failed_files > 0:
            lines.append("FAILED FILES")
            lines.append("=" * 50)
            for detail in self.result.failure_details[:10]:  # Show first 10
                lines.append(f"✗ {detail.get('file_name', '')}: {detail.get('error_message', '')}")
            if len(self.result.failure_details) > 10:
                lines.append(f"... and {len(self.result.failure_details) - 10} more failures")
                
        return "\n".join(lines)
        
    def _on_undo_clicked(self):
        """Handle undo button click"""
        if self.undo_callback:
            # Confirm undo operation
            from tkinter import messagebox
            result = messagebox.askyesno(
                "Undo Operation",
                f"Are you sure you want to undo the '{self.result.operation_name}' operation?\n\n"
                f"This will attempt to restore {self.result.successful_files} files to their original names.",
                parent=self.dialog
            )
            
            if result:
                self.undo_callback(self.result.operation_id)
                self._close_dialog()
                
    def _on_export_clicked(self):
        """Handle export button click"""
        if self.export_callback:
            self.export_callback(self.result)
            
    def _close_dialog(self):
        """Close the dialog and cleanup"""
        if self.dialog:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None


# Example usage and testing
if __name__ == "__main__":
    def test_result_dialog():
        """Test the result dialog with sample data"""
        root = tk.Tk()
        root.title("Result Dialog Test")
        root.geometry("400x300")
        
        def show_success_result():
            """Show successful operation result"""
            result = OperationResult(
                operation_id="test_001",
                operation_name="Vietnamese File Rename",
                total_files=10,
                successful_files=10,
                failed_files=0,
                skipped_files=0,
                operation_duration=2.34,
                success_details=[
                    {"original_name": f"Tài liệu {i}.txt", "new_name": f"tai lieu {i}.txt", "status": "Success"}
                    for i in range(1, 11)
                ],
                failure_details=[]
            )
            
            dialog = ResultDialog(root)
            dialog.show(result)
            
        def show_mixed_result():
            """Show mixed success/failure result"""
            result = OperationResult(
                operation_id="test_002", 
                operation_name="Batch File Processing",
                total_files=15,
                successful_files=12,
                failed_files=3,
                skipped_files=0,
                operation_duration=4.67,
                success_details=[
                    {"original_name": f"File {i}.txt", "new_name": f"file {i}.txt", "status": "Success"}
                    for i in range(1, 13)
                ],
                failure_details=[
                    {"file_name": "locked_file.txt", "error_message": "File is in use by another process", "suggestion": "Close the file and retry"},
                    {"file_name": "readonly.doc", "error_message": "Permission denied", "suggestion": "Remove read-only attribute"},
                    {"file_name": "invalid?.txt", "error_message": "Invalid filename characters", "suggestion": "Rename manually"}
                ],
                error_summary="3 files failed due to permission and naming issues."
            )
            
            dialog = ResultDialog(root)
            dialog.show(
                result,
                undo_callback=lambda op_id: print(f"Undo operation {op_id}"),
                export_callback=lambda res: print(f"Export results for {res.operation_id}")
            )
            
        # Test buttons
        ttk.Button(root, text="Show Success Result", command=show_success_result).pack(pady=20)
        ttk.Button(root, text="Show Mixed Result", command=show_mixed_result).pack(pady=10)
        
        root.mainloop()
        
    test_result_dialog()