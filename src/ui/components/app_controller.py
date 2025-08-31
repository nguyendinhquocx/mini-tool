import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List
from ..main_window import MainWindow, ApplicationState
from .folder_selector import FolderSelectorComponent
from .file_preview import FilePreviewComponent
try:
    from ..dialogs import ProgressDialog, ProgressInfo, ResultDialog, OperationResult
    from ...core.services.batch_operation_service import BatchOperationService, BatchOperationRequest, OperationProgress
    from ...core.services.operation_history_service import OperationHistoryService
    from ...core.services.database_service import DatabaseService
    from ...core.models.operation import NormalizationRules, OperationType
    from ...core.models.file_info import FileInfo
except ImportError:
    # Handle absolute imports when running tests
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from ui.dialogs import ProgressDialog, ProgressInfo, ResultDialog, OperationResult
    from core.services.batch_operation_service import BatchOperationService, BatchOperationRequest, OperationProgress
    from core.services.operation_history_service import OperationHistoryService
    from core.services.database_service import DatabaseService
    from core.models.operation import NormalizationRules, OperationType
    from core.models.file_info import FileInfo


class AppController:
    def __init__(self):
        self.main_window = MainWindow()
        self.state_manager = self.main_window.get_state_manager()
        
        # Initialize core services
        self.db_service = DatabaseService()
        self.history_service = OperationHistoryService(self.db_service)
        self.batch_service = BatchOperationService()
        
        # UI Components
        self.folder_selector: Optional[FolderSelectorComponent] = None
        self.file_preview: Optional[FilePreviewComponent] = None
        
        # Action buttons
        self.rename_button: Optional[tk.Button] = None
        self.undo_button: Optional[tk.Button] = None
        
        # Dialogs
        self.progress_dialog: Optional[ProgressDialog] = None
        
        # Guard against circular updates
        self._updating_file_preview = False
        
        # Current operation state
        self._current_files: List[FileInfo] = []
        
        self._setup_components()
        self._setup_action_buttons()
        self._setup_observers()

    def _setup_components(self):
        content_frame = self.main_window.get_content_frame()
        
        # Create folder selector
        self.folder_selector = FolderSelectorComponent(
            content_frame, 
            self._on_component_state_changed
        )
        
        # Create file preview
        self.file_preview = FilePreviewComponent(
            content_frame,
            self._on_component_state_changed
        )
        
        # Register components with main window
        self.main_window.add_component("folder_selector", self.folder_selector)
        self.main_window.add_component("file_preview", self.file_preview)
    
    def _setup_action_buttons(self):
        """Setup action buttons for batch operations"""
        action_frame = self.main_window.get_action_frame()
        
        # Create buttons container
        buttons_container = ttk.Frame(action_frame)
        buttons_container.pack(expand=True)
        
        # Rename Files button (main action)
        self.rename_button = ttk.Button(
            buttons_container,
            text="Rename Files",
            command=self._on_rename_files_clicked,
            style="Accent.TButton"
        )
        self.rename_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Undo Last Operation button
        self.undo_button = ttk.Button(
            buttons_container,
            text="Undo Last Operation",
            command=self._on_undo_clicked,
            state=tk.DISABLED  # Initially disabled
        )
        self.undo_button.pack(side=tk.LEFT)
        
        # Initially disable rename button until folder selected
        self.rename_button.config(state=tk.DISABLED)

    def _setup_observers(self):
        # Subscribe to state changes
        self.state_manager.subscribe(self._on_state_changed)

    def _on_component_state_changed(self, **kwargs):
        # Update application state based on component changes
        self.state_manager.update_state(**kwargs)

    def _on_state_changed(self, state: ApplicationState):
        # Handle state changes and update components accordingly
        try:
            # Update file preview when folder selection changes
            # Guard against circular updates
            if (state.selected_folder and self.file_preview and 
                not self._updating_file_preview):
                self._updating_file_preview = True
                try:
                    self.file_preview.update_files(state.selected_folder)
                finally:
                    self._updating_file_preview = False
                    
        except Exception as e:
            self._updating_file_preview = False
            self._handle_error(f"State update error: {str(e)}")
            
        # Update current files for batch operations
        if hasattr(state, 'files_preview'):
            self._current_files = state.files_preview
        
        # Update button states based on current state
        self._update_button_states(state)

    def _handle_error(self, error: str):
        if self.folder_selector:
            self.folder_selector.handle_error(error)

    def set_initial_folder(self, folder_path: str):
        if self.folder_selector:
            self.folder_selector.set_folder(folder_path)

    def get_current_state(self) -> ApplicationState:
        return self.state_manager.state

    def run(self):
        self.main_window.run()

    def destroy(self):
        """Cleanup and destroy the application"""
        try:
            # Cleanup batch service
            if self.batch_service:
                self.batch_service.cleanup()
                
            # Close database connections
            if self.db_service:
                self.db_service.close_all_connections()
                
            # Close any open dialogs
            if self.progress_dialog:
                self.progress_dialog.close()
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
        finally:
            self.main_window.destroy()
    
    def _update_button_states(self, state: ApplicationState):
        """Update button states based on current application state"""
        if self.rename_button:
            # Enable rename button if folder is selected and not currently processing
            can_rename = (state.selected_folder and 
                         len(state.files_preview) > 0 and
                         not state.operation_in_progress)
            self.rename_button.config(state=tk.NORMAL if can_rename else tk.DISABLED)
            
        if self.undo_button:
            # Enable undo button if there's a recent operation to undo
            try:
                history = self.history_service.get_operation_history(limit=5)
                has_undoable = False
                
                for op in history:
                    if (op['operation_type'] != OperationType.RESTORE.value and 
                        op['successful_files'] > 0):
                        can_undo, _ = self.history_service.can_undo_operation(op['operation_id'])
                        if can_undo:
                            has_undoable = True
                            break
                            
                self.undo_button.config(state=tk.NORMAL if has_undoable else tk.DISABLED)
                
            except Exception:
                # If there's any error checking undo status, disable button
                self.undo_button.config(state=tk.DISABLED)
    
    def _on_rename_files_clicked(self):
        """Handle rename files button click - execute batch rename operation"""
        try:
            # Validate preconditions
            if not self._current_files:
                messagebox.showwarning(
                    "No Files Selected",
                    "Please select a folder with files to rename.",
                    parent=self.main_window.root
                )
                return
                
            if self.batch_service.is_operation_running():
                messagebox.showwarning(
                    "Operation In Progress",
                    "Another batch operation is already running. Please wait for it to complete.",
                    parent=self.main_window.root
                )
                return
                
            # Confirm operation with user
            file_count = len(self._current_files)
            result = messagebox.askyesno(
                "Confirm Batch Rename",
                f"This will rename {file_count} files using Vietnamese normalization.\n\n"
                f"Files will be processed to:\n"
                f"• Remove Vietnamese diacritics\n"
                f"• Convert to lowercase\n"
                f"• Replace special characters\n"
                f"• Normalize whitespace\n\n"
                f"Do you want to continue?",
                parent=self.main_window.root
            )
            
            if not result:
                return
                
            # Create operation request
            current_state = self.state_manager.state
            request = BatchOperationRequest(
                files=self._current_files,
                rules=NormalizationRules(),  # Use default rules
                dry_run=False,
                source_directory=current_state.selected_folder or "",
                operation_type=OperationType.BATCH_RENAME
            )
            
            # Update UI state
            self.state_manager.update_state(operation_in_progress=True)
            
            # Start batch operation
            operation_id = self.batch_service.execute_batch_operation(
                request,
                progress_callback=self._on_operation_progress,
                completion_callback=self._on_operation_completed,
                error_callback=self._on_operation_error
            )
            
            # Show progress dialog
            self.progress_dialog = ProgressDialog(self.main_window.root, "Vietnamese File Rename")
            self.progress_dialog.show(
                cancel_callback=self._on_operation_cancelled,
                completion_callback=self._on_progress_dialog_closed
            )
            
            print(f"Started batch rename operation: {operation_id}")
            
        except Exception as e:
            self._handle_operation_error(f"Failed to start batch operation: {str(e)}")
    
    def _on_undo_clicked(self):
        """Handle undo button click - undo last operation"""
        try:
            # Get recent operations that can be undone
            history = self.history_service.get_operation_history(limit=10)
            undoable_ops = []
            
            for op in history:
                if op['operation_type'] != OperationType.RESTORE.value and op['successful_files'] > 0:
                    can_undo, reason = self.history_service.can_undo_operation(op['operation_id'])
                    if can_undo:
                        undoable_ops.append(op)
                        
            if not undoable_ops:
                messagebox.showinfo(
                    "No Operations to Undo",
                    "There are no recent operations that can be undone.",
                    parent=self.main_window.root
                )
                return
                
            # Use the most recent undoable operation
            last_op = undoable_ops[0]
            
            # Confirm undo with user
            result = messagebox.askyesno(
                "Confirm Undo Operation",
                f"This will undo the operation:\n\n"
                f"Operation: {last_op['operation_name']}\n"
                f"Files affected: {last_op['successful_files']}\n"
                f"Completed: {last_op['completed_at'][:19] if last_op['completed_at'] else 'Unknown'}\n\n"
                f"This will restore the original file names. Continue?",
                parent=self.main_window.root
            )
            
            if not result:
                return
                
            # Show progress and execute undo
            self.progress_dialog = ProgressDialog(self.main_window.root, "Undoing Operation")
            self.progress_dialog.show()
            
            # Execute undo in background (simulated for now - could be made async)
            def progress_callback(percentage, current_file):
                if self.progress_dialog:
                    progress_info = ProgressInfo(
                        current_file=current_file,
                        percentage=percentage,
                        operation_name="Undoing Operation",
                        can_cancel=False
                    )
                    self.progress_dialog.update_progress(progress_info)
                    
            success, message, failed_files = self.history_service.undo_operation(
                last_op['operation_id'],
                progress_callback
            )
            
            # Show completion
            if self.progress_dialog:
                final_progress = ProgressInfo(
                    current_file="Undo operation completed",
                    percentage=100.0,
                    operation_name="Undoing Operation",
                    is_completed=True,
                    can_cancel=False
                )
                self.progress_dialog.update_progress(final_progress)
                
            # Refresh file preview if we're in the same folder
            current_state = self.state_manager.state
            if current_state.selected_folder == last_op['source_directory']:
                if self.file_preview:
                    self.file_preview.update_files(current_state.selected_folder)
                    
            # Show result message
            if success:
                if failed_files:
                    messagebox.showwarning(
                        "Undo Partially Completed",
                        f"{message}\n\nFailed files:\n" + "\n".join(failed_files[:5]),
                        parent=self.main_window.root
                    )
                else:
                    messagebox.showinfo(
                        "Undo Completed",
                        message,
                        parent=self.main_window.root
                    )
            else:
                messagebox.showerror(
                    "Undo Failed",
                    f"Failed to undo operation: {message}",
                    parent=self.main_window.root
                )
                
        except Exception as e:
            messagebox.showerror(
                "Undo Error",
                f"An error occurred during undo: {str(e)}",
                parent=self.main_window.root
            )
    
    # Batch operation callbacks
    def _on_operation_progress(self, progress: OperationProgress):
        """Handle progress updates from batch operations"""
        if self.progress_dialog:
            progress_info = ProgressInfo(
                current_file=progress.current_file,
                processed_files=progress.processed_files,
                total_files=progress.total_files,
                percentage=progress.percentage,
                operation_name="Vietnamese File Rename",
                can_cancel=True,
                is_completed=progress.is_completed,
                error_message=progress.error_message if progress.has_error else None
            )
            self.progress_dialog.update_progress(progress_info)
            
        # Update application state
        self.state_manager.update_state(
            progress_percentage=progress.percentage,
            current_file_being_processed=progress.current_file
        )
        
    def _on_operation_completed(self, result):
        """Handle batch operation completion"""
        try:
            # Update UI state
            self.state_manager.update_state(operation_in_progress=False)
            
            # Save operation to history
            # Note: result is a BatchOperation object from the batch service
            # We need to get the file records from the service
            # For now, we'll save with empty file records
            self.history_service.save_operation(result, [])
            
            # Refresh file preview
            current_state = self.state_manager.state
            if current_state.selected_folder and self.file_preview:
                self.file_preview.update_files(current_state.selected_folder)
                
            # Create result for dialog
            operation_result = OperationResult(
                operation_id=result.operation_id,
                operation_name=result.operation_name,
                total_files=result.total_files,
                successful_files=result.successful_operations,
                failed_files=result.failed_operations,
                skipped_files=result.skipped_operations,
                operation_duration=result.get_duration(),
                success_details=[],  # Could be populated from file records
                failure_details=[],  # Could be populated from error log
                error_summary="; ".join(result.error_log) if result.error_log else None
            )
            
            # Show result dialog after progress dialog closes
            def show_result_dialog():
                if operation_result.has_failures or operation_result.error_summary:
                    # Show detailed results for operations with failures
                    result_dialog = ResultDialog(self.main_window.root)
                    result_dialog.show(
                        operation_result,
                        undo_callback=self._on_result_undo_requested,
                        export_callback=self._on_result_export_requested
                    )
                else:
                    # Show simple success message
                    messagebox.showinfo(
                        "Operation Completed",
                        f"Successfully renamed {operation_result.successful_files} files!",
                        parent=self.main_window.root
                    )
                    
            # Delay showing result dialog to let progress dialog close first
            self.main_window.root.after(500, show_result_dialog)
            
        except Exception as e:
            self._handle_operation_error(f"Error handling operation completion: {str(e)}")
            
    def _on_operation_error(self, error_message: str):
        """Handle batch operation errors"""
        self.state_manager.update_state(operation_in_progress=False)
        self._handle_operation_error(error_message)
        
    def _on_operation_cancelled(self):
        """Handle operation cancellation"""
        if self.batch_service.is_operation_running():
            self.batch_service.cancel_operation()
        self.state_manager.update_state(operation_in_progress=False)
        
    def _on_progress_dialog_closed(self, success: bool):
        """Handle progress dialog being closed"""
        self.progress_dialog = None
        
    def _on_result_undo_requested(self, operation_id: str):
        """Handle undo request from result dialog"""
        # Close result dialog and trigger undo
        self._on_undo_clicked()
        
    def _on_result_export_requested(self, result: OperationResult):
        """Handle export request from result dialog"""
        # TODO: Implement result export functionality
        messagebox.showinfo(
            "Export Results",
            "Export functionality will be implemented in a future update.",
            parent=self.main_window.root
        )
        
    def _handle_operation_error(self, error_message: str):
        """Handle operation errors with user feedback"""
        # Close progress dialog if open
        if self.progress_dialog:
            self.progress_dialog.close()
            
        # Show error to user
        messagebox.showerror(
            "Operation Error",
            error_message,
            parent=self.main_window.root
        )
        
        # Log error
        print(f"Operation error: {error_message}")