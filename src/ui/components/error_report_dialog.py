"""
Error Report Dialog

Provides comprehensive error reporting and analysis UI with charts,
filtering, and export capabilities for troubleshooting and monitoring.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import threading

from ...core.services.error_logging_service import (
    ComprehensiveErrorLoggingService, ErrorLogEntry, ErrorAnalysis
)
from ...core.models.error_models import ErrorSeverity


class ErrorReportDialog:
    """Comprehensive error reporting and analysis dialog"""
    
    def __init__(self, parent: Optional[tk.Widget], 
                 logging_service: ComprehensiveErrorLoggingService):
        self.parent = parent
        self.logging_service = logging_service
        self.dialog = None
        self.current_errors: List[ErrorLogEntry] = []
        self.current_analysis: Optional[ErrorAnalysis] = None
        
    def show(self):
        """Show the error report dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Error Report & Analysis - File Rename Tool")
        self.dialog.geometry("900x700")
        self.dialog.resizable(True, True)
        
        # Center the dialog
        if self.parent:
            self.dialog.transient(self.parent)
            self._center_dialog()
        
        self._create_widgets()
        self._load_initial_data()
        
        # Make dialog modal
        self.dialog.grab_set()
        self.dialog.focus_set()
    
    def _center_dialog(self):
        """Center dialog on parent"""
        self.dialog.update_idletasks()
        width = self.dialog.winfo_width()
        height = self.dialog.winfo_height()
        
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() // 2) - (height // 2)
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Title and controls
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="Error Report & Analysis", 
                               font=('Segoe UI', 14, 'bold'))
        title_label.pack(side="left")
        
        # Control buttons
        controls_frame = ttk.Frame(header_frame)
        controls_frame.pack(side="right")
        
        ttk.Button(controls_frame, text="Refresh", 
                  command=self._refresh_data).pack(side="left", padx=(0, 5))
        
        ttk.Button(controls_frame, text="Export Report", 
                  command=self._export_report).pack(side="left", padx=(0, 5))
        
        ttk.Button(controls_frame, text="Clear Old Logs", 
                  command=self._clear_old_logs).pack(side="left")
        
        # Filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filters", padding="10")
        filter_frame.pack(fill="x", pady=(0, 10))
        
        self._create_filter_controls(filter_frame)
        
        # Main content notebook
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Analysis tab
        analysis_frame = self._create_analysis_tab(notebook)
        notebook.add(analysis_frame, text="Analysis")
        
        # Error List tab
        error_list_frame = self._create_error_list_tab(notebook)
        notebook.add(error_list_frame, text="Error Details")
        
        # Trends tab
        trends_frame = self._create_trends_tab(notebook)
        notebook.add(trends_frame, text="Trends")
        
        # Close button
        close_frame = ttk.Frame(main_frame)
        close_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        ttk.Button(close_frame, text="Close", 
                  command=self.dialog.destroy).pack(side="right")
    
    def _create_filter_controls(self, parent):
        """Create filter control widgets"""
        # Time range filter
        time_frame = ttk.Frame(parent)
        time_frame.pack(fill="x", pady=2)
        
        ttk.Label(time_frame, text="Time Range:").pack(side="left", padx=(0, 5))
        
        self.time_range_var = tk.StringVar(value="24h")
        time_combo = ttk.Combobox(time_frame, textvariable=self.time_range_var, 
                                 values=["1h", "6h", "24h", "7d", "30d"], width=8)
        time_combo.pack(side="left", padx=(0, 15))
        time_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Severity filter
        ttk.Label(time_frame, text="Severity:").pack(side="left", padx=(0, 5))
        
        self.severity_var = tk.StringVar(value="All")
        severity_combo = ttk.Combobox(time_frame, textvariable=self.severity_var,
                                     values=["All", "CRITICAL", "ERROR", "WARNING", "INFO"], 
                                     width=10)
        severity_combo.pack(side="left", padx=(0, 15))
        severity_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        
        # Search filter
        ttk.Label(time_frame, text="Search:").pack(side="left", padx=(0, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(time_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side="left", padx=(0, 5))
        search_entry.bind("<KeyRelease>", lambda e: self.dialog.after(500, self._apply_filters))
        
        ttk.Button(time_frame, text="Apply", 
                  command=self._apply_filters).pack(side="left")
    
    def _create_analysis_tab(self, notebook) -> ttk.Frame:
        """Create analysis tab content"""
        frame = ttk.Frame(notebook)
        
        # Summary cards
        summary_frame = ttk.Frame(frame)
        summary_frame.pack(fill="x", pady=(0, 15))
        
        # Create summary cards
        self.summary_cards = {}
        card_data = [
            ("Total Errors", "total_errors", "❌"),
            ("Critical Errors", "critical_count", "🔥"),
            ("Error Rate/Hour", "error_rate", "📊"),
            ("Success Rate", "recovery_rate", "✅")
        ]
        
        for i, (title, key, icon) in enumerate(card_data):
            card = self._create_summary_card(summary_frame, title, "0", icon)
            card.grid(row=0, column=i, padx=5, sticky="ew")
            self.summary_cards[key] = card
            summary_frame.grid_columnconfigure(i, weight=1)
        
        # Most common errors
        common_frame = ttk.LabelFrame(frame, text="Most Common Errors", padding="10")
        common_frame.pack(fill="x", pady=(0, 15))
        
        # Treeview for common errors
        columns = ('error_code', 'count', 'percentage')
        self.common_tree = ttk.Treeview(common_frame, columns=columns, show='headings', height=6)
        
        self.common_tree.heading('error_code', text='Error Type')
        self.common_tree.heading('count', text='Count')
        self.common_tree.heading('percentage', text='Percentage')
        
        self.common_tree.column('error_code', width=200)
        self.common_tree.column('count', width=80, anchor='center')
        self.common_tree.column('percentage', width=80, anchor='center')
        
        self.common_tree.pack(fill="x")
        
        # Recommendations
        recommendations_frame = ttk.LabelFrame(frame, text="Recommendations", padding="10")
        recommendations_frame.pack(fill="both", expand=True)
        
        self.recommendations_text = tk.Text(recommendations_frame, height=8, wrap=tk.WORD,
                                          font=('Segoe UI', 9))
        self.recommendations_text.pack(fill="both", expand=True)
        
        return frame
    
    def _create_summary_card(self, parent, title, value, icon) -> ttk.Frame:
        """Create a summary card widget"""
        card = ttk.LabelFrame(parent, text=title, padding="10")
        
        # Icon and value
        content_frame = ttk.Frame(card)
        content_frame.pack(fill="both", expand=True)
        
        icon_label = ttk.Label(content_frame, text=icon, font=('Segoe UI', 16))
        icon_label.pack()
        
        value_label = ttk.Label(content_frame, text=value, font=('Segoe UI', 14, 'bold'))
        value_label.pack()
        
        # Store value label for updates
        card.value_label = value_label
        
        return card
    
    def _create_error_list_tab(self, notebook) -> ttk.Frame:
        """Create error list tab content"""
        frame = ttk.Frame(notebook)
        
        # Treeview for error details
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        columns = ('timestamp', 'severity', 'error_code', 'file_path', 'message')
        self.error_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        self.error_tree.heading('timestamp', text='Time')
        self.error_tree.heading('severity', text='Severity')
        self.error_tree.heading('error_code', text='Error Code')
        self.error_tree.heading('file_path', text='File')
        self.error_tree.heading('message', text='Message')
        
        self.error_tree.column('timestamp', width=120)
        self.error_tree.column('severity', width=80)
        self.error_tree.column('error_code', width=120)
        self.error_tree.column('file_path', width=150)
        self.error_tree.column('message', width=300)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.error_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.error_tree.xview)
        
        self.error_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.error_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Bind double-click for details
        self.error_tree.bind("<Double-1>", self._show_error_details)
        
        # Details frame
        details_frame = ttk.LabelFrame(frame, text="Error Details", padding="10")
        details_frame.pack(fill="x")
        
        self.details_text = tk.Text(details_frame, height=6, wrap=tk.WORD,
                                   font=('Consolas', 9), state='disabled')
        self.details_text.pack(fill="x")
        
        return frame
    
    def _create_trends_tab(self, notebook) -> ttk.Frame:
        """Create trends tab content"""
        frame = ttk.Frame(notebook)
        
        # Simple text-based trend display
        # In a full implementation, this would use matplotlib or similar
        trends_label = ttk.Label(frame, text="Error Trends Over Time", 
                                font=('Segoe UI', 12, 'bold'))
        trends_label.pack(pady=(0, 10))
        
        self.trends_text = tk.Text(frame, font=('Consolas', 10))
        self.trends_text.pack(fill="both", expand=True)
        
        return frame
    
    def _load_initial_data(self):
        """Load initial data in background thread"""
        def load_data():
            try:
                # Get recent errors
                self.current_errors = self.logging_service.get_recent_errors(limit=1000)
                self.current_analysis = self.logging_service.get_error_analysis()
                
                # Update UI on main thread
                self.dialog.after(0, self._update_ui_with_data)
            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror("Error", 
                    f"Failed to load error data: {str(e)}", parent=self.dialog))
        
        threading.Thread(target=load_data, daemon=True).start()
    
    def _update_ui_with_data(self):
        """Update UI with loaded data"""
        if not self.current_analysis:
            return
        
        # Update summary cards
        self.summary_cards["total_errors"].value_label.config(
            text=str(self.current_analysis.total_errors))
        
        self.summary_cards["critical_count"].value_label.config(
            text=str(self.current_analysis.critical_error_count))
        
        self.summary_cards["error_rate"].value_label.config(
            text=f"{self.current_analysis.error_rate_per_hour:.1f}")
        
        self.summary_cards["recovery_rate"].value_label.config(
            text=f"{self.current_analysis.recovery_success_rate:.1f}%")
        
        # Update common errors
        self.common_tree.delete(*self.common_tree.get_children())
        
        total_errors = self.current_analysis.total_errors or 1
        for error_code, count in self.current_analysis.most_common_errors:
            percentage = (count / total_errors) * 100
            self.common_tree.insert('', 'end', values=(
                error_code, count, f"{percentage:.1f}%"
            ))
        
        # Update error list
        self._populate_error_list()
        
        # Update recommendations
        self._update_recommendations()
        
        # Update trends
        self._update_trends()
    
    def _populate_error_list(self):
        """Populate error list tree"""
        self.error_tree.delete(*self.error_tree.get_children())
        
        for error in self.current_errors:
            timestamp = error.timestamp.strftime("%H:%M:%S")
            file_name = error.file_path.split('\\\\')[-1] if error.file_path else "N/A"
            
            self.error_tree.insert('', 'end', values=(
                timestamp,
                error.severity,
                error.error_code,
                file_name,
                error.message[:50] + "..." if len(error.message) > 50 else error.message
            ))
    
    def _update_recommendations(self):
        """Update recommendations text"""
        if not self.current_analysis:
            return
        
        recommendations = []
        
        if self.current_analysis.critical_error_count > 0:
            recommendations.append("🔥 Critical errors detected - immediate attention required")
        
        if self.current_analysis.error_rate_per_hour > 10:
            recommendations.append("📈 High error rate detected - investigate recurring issues")
        
        # Analyze common error patterns
        for error_code, count in self.current_analysis.most_common_errors[:3]:
            if count > 5:
                if error_code == "PERMISSION_DENIED":
                    recommendations.append("🔒 Frequent permission errors - consider running as administrator")
                elif error_code == "FILE_IN_USE":
                    recommendations.append("📁 Files frequently locked - check for other applications")
                elif error_code == "NETWORK_UNAVAILABLE":
                    recommendations.append("🌐 Network issues detected - verify network stability")
        
        if self.current_analysis.recovery_success_rate < 50:
            recommendations.append("⚡ Low recovery success rate - review error handling strategies")
        
        if not recommendations:
            recommendations.append("✅ No significant issues detected - system running normally")
        
        self.recommendations_text.config(state='normal')
        self.recommendations_text.delete('1.0', tk.END)
        
        for i, rec in enumerate(recommendations, 1):
            self.recommendations_text.insert(tk.END, f"{i}. {rec}\\n\\n")
        
        self.recommendations_text.config(state='disabled')
    
    def _update_trends(self):
        """Update trends display"""
        if not self.current_analysis:
            return
        
        trends_info = []
        trends_info.append("ERROR TRENDS ANALYSIS")
        trends_info.append("=" * 50)
        trends_info.append("")
        
        # Hourly trends
        if 'hourly' in self.current_analysis.error_trends:
            hourly_data = self.current_analysis.error_trends['hourly']
            trends_info.append("HOURLY ERROR DISTRIBUTION:")
            trends_info.append("")
            
            for i, count in enumerate(hourly_data[-12:]):  # Last 12 hours
                hour = (datetime.now().hour - (12 - i - 1)) % 24
                bar = "█" * min(count, 20)  # Simple bar chart
                trends_info.append(f"{hour:02d}:00  {bar} ({count})")
            
            trends_info.append("")
        
        # Error type distribution
        trends_info.append("TOP ERROR TYPES:")
        trends_info.append("")
        
        for error_code, count in self.current_analysis.most_common_errors[:10]:
            percentage = (count / max(1, self.current_analysis.total_errors)) * 100
            bar = "▓" * int(percentage / 5)  # Simple percentage bar
            trends_info.append(f"{error_code:<20} {bar} {count} ({percentage:.1f}%)")
        
        self.trends_text.config(state='normal')
        self.trends_text.delete('1.0', tk.END)
        self.trends_text.insert('1.0', "\\n".join(trends_info))
        self.trends_text.config(state='disabled')
    
    def _apply_filters(self):
        """Apply current filters and refresh data"""
        # This would filter the data based on current filter settings
        # For now, just reload data
        self._load_initial_data()
    
    def _refresh_data(self):
        """Refresh all data"""
        self._load_initial_data()
    
    def _show_error_details(self, event):
        """Show detailed error information"""
        selection = self.error_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        index = self.error_tree.index(item)
        
        if index < len(self.current_errors):
            error = self.current_errors[index]
            
            details = []
            details.append(f"Error ID: {error.error_id}")
            details.append(f"Timestamp: {error.timestamp}")
            details.append(f"Session ID: {error.session_id}")
            details.append(f"Operation ID: {error.operation_id or 'N/A'}")
            details.append(f"Correlation ID: {error.correlation_id or 'N/A'}")
            details.append("")
            details.append(f"Error Code: {error.error_code}")
            details.append(f"Severity: {error.severity}")
            details.append(f"Message: {error.message}")
            details.append(f"User Message: {error.user_message}")
            details.append("")
            
            if error.file_path:
                details.append(f"File: {error.file_path}")
            
            if error.technical_details:
                details.append(f"Technical Details: {error.technical_details}")
            
            if error.stack_trace:
                details.append("Stack Trace:")
                details.append(error.stack_trace)
            
            self.details_text.config(state='normal')
            self.details_text.delete('1.0', tk.END)
            self.details_text.insert('1.0', "\\n".join(details))
            self.details_text.config(state='disabled')
    
    def _export_report(self):
        """Export error report to file"""
        filename = filedialog.asksaveasfilename(
            parent=self.dialog,
            title="Export Error Report",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                exported_file = self.logging_service.export_error_report(filename)
                messagebox.showinfo("Export Complete", 
                    f"Error report exported to: {exported_file}", parent=self.dialog)
            except Exception as e:
                messagebox.showerror("Export Failed", 
                    f"Failed to export report: {str(e)}", parent=self.dialog)
    
    def _clear_old_logs(self):
        """Clear old log entries"""
        if messagebox.askyesno("Clear Old Logs", 
                             "This will permanently delete error logs older than 30 days. Continue?", 
                             parent=self.dialog):
            try:
                deleted_count = self.logging_service.cleanup_old_logs(days_to_keep=30)
                messagebox.showinfo("Cleanup Complete", 
                    f"Deleted {deleted_count} old log entries.", parent=self.dialog)
                self._refresh_data()
            except Exception as e:
                messagebox.showerror("Cleanup Failed", 
                    f"Failed to clean up logs: {str(e)}", parent=self.dialog)