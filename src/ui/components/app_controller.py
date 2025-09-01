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
    from ...core.services.undo_service import UndoService
    from ...core.models.operation import NormalizationRules, OperationType, CancellationToken
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
    from core.services.undo_service import UndoService
    from core.models.operation import NormalizationRules, OperationType, CancellationToken
    from core.models.file_info import FileInfo


class AppController:
    def __init__(self):
        self.main_window = MainWindow()
        self.state_manager = self.main_window.get_state_manager()
        
        # Initialize core services
        self.db_service = DatabaseService()
        self.history_service = OperationHistoryService(self.db_service)
        self.undo_service = UndoService(self.db_service, self.history_service)
        self.batch_service = BatchOperationService(
            database_service=self.db_service,
            operation_history_service=self.history_service
        )
        
        # Initialize configuration service  
        from ...core.services.config_service import get_config_service
        self.config_service = get_config_service()
        
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
            # Update undo button state based on enhanced undo availability
            self._update_undo_button_state(state)
    
    def _update_undo_button_state(self, state: ApplicationState):
        """Update undo button state with enhanced validation and tooltip"""
        try:
            # Check if there's an undoable operation for current folder
            last_operation = self.undo_service.get_last_undoable_operation(state.selected_folder)
            
            if last_operation and not state.operation_in_progress:
                # Quick eligibility check
                eligibility = self.undo_service.can_undo_operation(last_operation['operation_id'])
                
                if eligibility.can_undo:
                    # Enable undo button
                    self.undo_button.config(state=tk.NORMAL)
                    
                    # Set informative tooltip
                    tooltip_text = (f"Undo: {last_operation['operation_name']} "
                                  f"({eligibility.valid_files} files)")
                    
                    # Update state for UI consistency
                    self.state_manager.update_state(
                        can_undo_last_operation=True,
                        last_operation_id=last_operation['operation_id'],
                        undo_button_tooltip=tooltip_text,
                        undo_disabled_reason=None
                    )
                else:
                    # Disable with reason
                    self.undo_button.config(state=tk.DISABLED)
                    
                    # Set explanatory tooltip
                    tooltip_text = f"Cannot undo: {eligibility.primary_reason}"
                    
                    # Update state
                    self.state_manager.update_state(
                        can_undo_last_operation=False,
                        undo_button_tooltip=tooltip_text,
                        undo_disabled_reason=eligibility.primary_reason
                    )
            else:
                # No undoable operations
                self.undo_button.config(state=tk.DISABLED)
                
                tooltip_text = "No operation to undo"
                if state.operation_in_progress:
                    tooltip_text = "Operation in progress"
                    
                # Update state
                self.state_manager.update_state(
                    can_undo_last_operation=False,
                    last_operation_id=None,
                    undo_button_tooltip=tooltip_text,
                    undo_disabled_reason=tooltip_text
                )
                
        except Exception as e:
            # Error checking undo status - disable button
            self.undo_button.config(state=tk.DISABLED)
            
            tooltip_text = f"Undo check failed: {str(e)}"
            
            # Update state
            self.state_manager.update_state(
                can_undo_last_operation=False,
                undo_button_tooltip=tooltip_text,
                undo_disabled_reason=str(e)
            )
    
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
                
            # Get current configuration for confirmation dialog
            config_rules = self.config_service.get_normalization_rules()
            operation_settings = self.config_service.get_operation_settings()
            
            # Build confirmation message based on current settings
            file_count = len(self._current_files)
            rules_description = []
            if config_rules.remove_diacritics:
                rules_description.append("Remove Vietnamese diacritics")
            if config_rules.convert_to_lowercase:
                rules_description.append("Convert to lowercase")
            if config_rules.clean_special_characters:
                rules_description.append("Replace special characters")
            if config_rules.normalize_whitespace:
                rules_description.append("Normalize whitespace")
            
            if not rules_description:
                rules_description.append("No normalization rules enabled")
            
            mode_text = "DRY RUN MODE - Preview only" if operation_settings.dry_run_by_default else "LIVE MODE - Files will be renamed"
            
            result = messagebox.askyesno(
                "Confirm Batch Rename",
                f"This will rename {file_count} files.\n\n"
                f"MODE: {mode_text}\n\n"
                f"Active rules:\n" + "\n".join(f"• {rule}" for rule in rules_description) + "\n\n"
                f"Do you want to continue?",
                parent=self.main_window.root
            )
            
            if not result:
                return
                
            # Create operation request với configuration rules
            current_state = self.state_manager.state
            
            # Get normalization rules từ configuration
            config_rules = self.config_service.get_normalization_rules()
            operation_settings = self.config_service.get_operation_settings()
            
            # Convert configuration rules to operation rules format
            # Note: Cần adapter để convert từ NormalizationRulesConfig sang NormalizationRules
            from ...core.services.normalize_service import VietnameseNormalizer
            normalizer = VietnameseNormalizer.from_config(config_rules)
            
            request = BatchOperationRequest(
                files=self._current_files,
                rules=normalizer.rules,  # Use rules từ configuration
                dry_run=operation_settings.dry_run_by_default,
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
        """Handle undo button click - enhanced undo with validation and progress"""
        try:
            # Get the last undoable operation for current folder
            current_state = self.state_manager.state
            last_operation = self.undo_service.get_last_undoable_operation(current_state.selected_folder)
            
            if not last_operation:
                messagebox.showinfo(
                    "No Operations to Undo",
                    "There are no recent operations that can be undone in this folder.",
                    parent=self.main_window.root
                )
                return
            
            operation_id = last_operation['operation_id']
            
            # Check detailed undo eligibility
            eligibility = self.undo_service.can_undo_operation(operation_id)
            
            if not eligibility.can_undo:
                # Show detailed reason why undo is not possible
                self._show_undo_eligibility_dialog(eligibility)
                return
            
            # Show undo confirmation dialog with operation details
            result = self._show_undo_confirmation_dialog(last_operation, eligibility)
            if not result:
                return
            
            # Update UI state
            self.state_manager.update_state(operation_in_progress=True)
            
            # Show enhanced progress dialog
            self.progress_dialog = ProgressDialog(self.main_window.root, "Undoing Operation")
            self.progress_dialog.show()
            
            # Create cancellation token for undo operation
            cancellation_token = CancellationToken()
            
            # Set up progress callback
            def progress_callback(percentage: float, current_file: str):
                if self.progress_dialog:
                    progress_info = ProgressInfo(
                        current_file=current_file,
                        percentage=percentage,
                        operation_name=f"Undoing: {last_operation['operation_name']}",
                        can_cancel=True
                    )
                    self.progress_dialog.update_progress(progress_info)
                    
                    # Check if user cancelled
                    if self.progress_dialog.is_cancelled:
                        cancellation_token.request_cancellation("User cancelled undo operation")
            
            # Execute enhanced undo operation
            undo_result = self.undo_service.execute_undo_operation(
                operation_id,
                progress_callback,
                cancellation_token
            )
            
            # Close progress dialog
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # Update UI state
            self.state_manager.update_state(
                operation_in_progress=False,
                can_undo_last_operation=False,  # No longer can undo this operation
                undo_button_tooltip="No operation to undo"
            )
            
            # Refresh file preview if we're in the same folder
            if current_state.selected_folder == last_operation['source_directory']:
                if self.file_preview:
                    self.file_preview.update_files(current_state.selected_folder)
            
            # Show detailed result dialog
            self._show_undo_result_dialog(undo_result, last_operation)
            
        except Exception as e:
            # Close progress dialog on error
            if self.progress_dialog:
                self.progress_dialog.close()
                self.progress_dialog = None
            
            # Update UI state
            self.state_manager.update_state(operation_in_progress=False)
            
            messagebox.showerror(
                "Undo Error",
                f"An error occurred during undo operation:\n\n{str(e)}",
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
    
    # Undo Helper Methods
    def _show_undo_eligibility_dialog(self, eligibility):
        """Show detailed dialog explaining why undo is not possible"""
        title = "Undo Not Available"
        
        message_parts = [
            "Cannot undo the last operation for the following reason:",
            "",
            eligibility.get_summary_message(),
            ""
        ]
        
        # Add specific details
        if eligibility.missing_files:
            message_parts.extend([
                f"Missing files ({len(eligibility.missing_files)}):",
                "• " + "\n• ".join(eligibility.missing_files[:5]),
                ("• ..." if len(eligibility.missing_files) > 5 else ""),
                ""
            ])
        
        if eligibility.modified_files:
            message_parts.extend([
                f"Files modified externally ({len(eligibility.modified_files)}):",
                "• " + "\n• ".join(eligibility.modified_files[:5]),
                ("• ..." if len(eligibility.modified_files) > 5 else ""),
                ""
            ])
        
        if eligibility.conflicting_files:
            message_parts.extend([
                f"Name conflicts ({len(eligibility.conflicting_files)}):",
                "• " + "\n• ".join(eligibility.conflicting_files[:5]),
                ("• ..." if len(eligibility.conflicting_files) > 5 else ""),
                ""
            ])
        
        message = "\n".join(filter(None, message_parts))
        
        messagebox.showwarning(title, message, parent=self.main_window.root)
    
    def _show_undo_confirmation_dialog(self, operation, eligibility):
        """Show enhanced undo confirmation dialog"""
        message_parts = [
            "This will undo the following operation:",
            "",
            f"Operation: {operation['operation_name']}",
            f"Files to restore: {eligibility.valid_files}",
            f"Completed: {operation['completed_at'][:19] if operation['completed_at'] else 'Unknown'}",
            ""
        ]
        
        if eligibility.file_validations:
            # Show sample of files that will be restored
            sample_files = []
            for validation in eligibility.file_validations[:3]:
                if validation.is_valid:
                    sample_files.append(f"  {validation.current_name} → {validation.original_name}")
            
            if sample_files:
                message_parts.extend([
                    "Sample files to be restored:",
                    "\n".join(sample_files),
                    ("  ..." if eligibility.valid_files > 3 else ""),
                    ""
                ])
        
        message_parts.extend([
            "This will restore the original file names.",
            "This action cannot be undone.",
            "",
            "Continue with undo operation?"
        ])
        
        message = "\n".join(filter(None, message_parts))
        
        return messagebox.askyesno(
            "Confirm Undo Operation",
            message,
            parent=self.main_window.root
        )
    
    def _show_undo_result_dialog(self, undo_result, original_operation):
        """Show detailed undo operation result"""
        if undo_result.is_successful:
            title = "Undo Completed Successfully"
            message_parts = [
                f"Successfully undone operation: {original_operation['operation_name']}",
                "",
                f"Files restored: {undo_result.successful_restorations}",
                f"Total duration: {undo_result.total_duration:.2f} seconds" if undo_result.total_duration else ""
            ]
            
            messagebox.showinfo(title, "\n".join(filter(None, message_parts)), parent=self.main_window.root)
            
        elif undo_result.partial_success:
            title = "Undo Partially Completed"
            message_parts = [
                f"Partially undone operation: {original_operation['operation_name']}",
                "",
                f"Files restored: {undo_result.successful_restorations}",
                f"Files failed: {undo_result.failed_restorations}",
                ""
            ]
            
            # Show failed files
            if undo_result.failed_files:
                message_parts.extend([
                    "Failed files:",
                    "• " + "\n• ".join([f"{f[0]}: {f[1]}" for f in undo_result.failed_files[:3]]),
                    ("• ..." if len(undo_result.failed_files) > 3 else "")
                ])
            
            messagebox.showwarning(title, "\n".join(filter(None, message_parts)), parent=self.main_window.root)
            
        else:
            title = "Undo Failed"
            message_parts = [
                f"Failed to undo operation: {original_operation['operation_name']}",
                "",
                undo_result.completion_message
            ]
            
            if undo_result.error_message:
                message_parts.extend(["", f"Error: {undo_result.error_message}"])
            
            messagebox.showerror(title, "\n".join(filter(None, message_parts)), parent=self.main_window.root)