"""
Operation Progress Coordinator

Coordinates between BatchOperationService và ProgressDialog để ensure
smooth UI responsiveness during long-running operations với proper
cancellation handling và progress updates.
"""

import tkinter as tk
from typing import Optional, List, Callable
import logging
from datetime import datetime

# Import UI components
try:
    from ..dialogs.progress_dialog import ProgressDialog, ProgressInfo
    from ...core.services.batch_operation_service import (
        BatchOperationService, BatchOperationRequest, OperationProgress
    )
    from ...core.models.operation import OperationResult, OperationStatus
    from ...core.models.file_info import FileInfo
except ImportError:
    # Fallback for test environment
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
    from ui.dialogs.progress_dialog import ProgressDialog, ProgressInfo
    from core.services.batch_operation_service import (
        BatchOperationService, BatchOperationRequest, OperationProgress
    )
    from core.models.operation import OperationResult, OperationStatus
    from core.models.file_info import FileInfo

# Configure logging
logger = logging.getLogger(__name__)

# Constants
OPERATION_CLEANUP_DELAY_MS = 100  # Delay before cleanup
ERROR_DISPLAY_DELAY_MS = 500  # Delay for error display


class OperationProgressCoordinator:
    """
    Coordinates progress dialog và batch operations để ensure UI responsiveness
    
    Features:
    - Automatic progress dialog management
    - Thread-safe UI updates
    - Graceful cancellation handling
    - Completion notifications
    - Error handling và user feedback
    """
    
    def __init__(self, parent_window: tk.Widget):
        self.parent_window = parent_window
        self.batch_service = BatchOperationService()
        
        # Dialog management
        self.progress_dialog: Optional[ProgressDialog] = None
        self.is_operation_running = False
        
        # Operation tracking
        self.current_operation_id: Optional[str] = None
        self.current_start_time: Optional[datetime] = None
        
        # Callbacks
        self.completion_callback: Optional[Callable[[OperationResult, bool], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
    def execute_batch_rename(self,
                           files: List[FileInfo],
                           normalization_rules,
                           source_directory: str,
                           dry_run: bool = False,
                           completion_callback: Optional[Callable[[OperationResult, bool], None]] = None,
                           error_callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Execute batch rename operation với integrated progress dialog
        
        Args:
            files: List of files to process
            normalization_rules: Normalization rules to apply
            source_directory: Source directory path
            dry_run: If True, don't actually rename files
            completion_callback: Called when operation completes (result, success)
            error_callback: Called when operation errors occur
            
        Returns:
            True if operation started successfully, False otherwise
        """
        if self.is_operation_running:
            logger.warning("Cannot start operation - another operation is already running")
            return False
        
        try:
            # Store callbacks
            self.completion_callback = completion_callback
            self.error_callback = error_callback
            
            # Create operation request
            request = BatchOperationRequest(
                files=files,
                rules=normalization_rules,
                source_directory=source_directory,
                dry_run=dry_run
            )
            
            # Create và show progress dialog
            operation_name = "Dry Run - File Rename Preview" if dry_run else "Batch File Rename"
            self.progress_dialog = ProgressDialog(self.parent_window, operation_name)
            self.progress_dialog.show(
                cancel_callback=self._handle_user_cancellation,
                completion_callback=self._handle_dialog_completion
            )
            
            # Start batch operation
            self.current_operation_id = self.batch_service.execute_batch_operation(
                request,
                progress_callback=self._handle_progress_update,
                completion_callback=self._handle_operation_completion,
                error_callback=self._handle_operation_error
            )
            
            self.is_operation_running = True
            self.current_start_time = datetime.now()
            
            logger.info(f"Started batch operation {self.current_operation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start batch operation: {e}")
            if self.error_callback:
                self.error_callback(f"Failed to start operation: {str(e)}")
            self._cleanup_operation()
            return False
    
    def cancel_current_operation(self) -> bool:
        """
        Cancel the currently running operation
        
        Returns:
            True if cancellation was requested successfully
        """
        if not self.is_operation_running:
            return False
        
        logger.info("User requested operation cancellation")
        return self.batch_service.cancel_operation()
    
    def is_busy(self) -> bool:
        """Check if coordinator is currently managing an operation"""
        return self.is_operation_running
    
    def _handle_progress_update(self, progress: OperationProgress):
        """Handle progress updates from batch service"""
        if not self.progress_dialog or not self.progress_dialog.is_visible():
            return
        
        try:
            # Convert to ProgressInfo format
            progress_info = ProgressInfo(
                current_file=progress.current_file,
                processed_files=progress.processed_files,
                total_files=progress.total_files,
                percentage=progress.percentage,
                operation_name=self.progress_dialog.operation_name,
                can_cancel=not progress.is_completed,
                is_completed=progress.is_completed,
                error_message=progress.error_message,
                
                # Enhanced timing information
                estimated_time_remaining=progress.estimated_time_remaining,
                elapsed_time=progress.elapsed_time,
                processing_speed=progress.processing_speed,
                
                # Results summary
                success_count=progress.success_count,
                error_count=progress.error_count,
                skipped_count=progress.skipped_count
            )
            
            # Update dialog trên main thread
            self.parent_window.after(0, lambda: self._update_progress_dialog(progress_info))
            
        except Exception as e:
            logger.error(f"Error updating progress dialog: {e}")
    
    def _update_progress_dialog(self, progress_info: ProgressInfo):
        """Update progress dialog on main thread"""
        try:
            if self.progress_dialog and self.progress_dialog.is_visible():
                self.progress_dialog.update_progress(progress_info)
        except Exception as e:
            logger.error(f"Error in progress dialog update: {e}")
    
    def _handle_operation_completion(self, result: OperationResult):
        """Handle operation completion from batch service"""
        try:
            logger.info(f"Operation {result.operation_id} completed with status: {result.status.value}")
            
            # Determine success
            success = result.status == OperationStatus.COMPLETED and not result.fatal_error
            
            # Update dialog với final status
            if self.progress_dialog and self.progress_dialog.is_visible():
                final_progress = ProgressInfo(
                    current_file="Operation completed" if success else "Operation finished với errors",
                    processed_files=result.success_count + result.error_count + result.skipped_count,
                    total_files=result.total_files,
                    percentage=100.0,
                    operation_name=self.progress_dialog.operation_name,
                    can_cancel=False,
                    is_completed=True,
                    error_message=result.error_message if not success else None,
                    
                    # Final timing information
                    elapsed_time=f"{result.total_duration:.1f}s" if result.total_duration else None,
                    estimated_time_remaining="00:00",
                    processing_speed="Complete",
                    
                    # Final results summary
                    success_count=result.success_count,
                    error_count=result.error_count,
                    skipped_count=result.skipped_count
                )
                
                self.parent_window.after(0, lambda: self._update_progress_dialog(final_progress))
            
            # Call completion callback
            if self.completion_callback:
                self.parent_window.after(0, lambda: self.completion_callback(result, success))
            
        except Exception as e:
            logger.error(f"Error handling operation completion: {e}")
        finally:
            self.parent_window.after(OPERATION_CLEANUP_DELAY_MS, self._cleanup_operation)
    
    def _handle_operation_error(self, error_message: str):
        """Handle operation errors from batch service"""
        logger.error(f"Operation error: {error_message}")
        
        # Update dialog với error status
        if self.progress_dialog and self.progress_dialog.is_visible():
            error_progress = ProgressInfo(
                current_file="Operation failed",
                processed_files=0,
                total_files=0,
                percentage=0.0,
                operation_name=self.progress_dialog.operation_name,
                can_cancel=False,
                is_completed=True,
                error_message=error_message
            )
            
            self.parent_window.after(0, lambda: self._update_progress_dialog(error_progress))
        
        # Call error callback
        if self.error_callback:
            self.parent_window.after(0, lambda: self.error_callback(error_message))
        
        self.parent_window.after(ERROR_DISPLAY_DELAY_MS, self._cleanup_operation)
    
    def _handle_user_cancellation(self):
        """Handle user clicking cancel button"""
        logger.info("User requested cancellation via dialog")
        self.cancel_current_operation()
    
    def _handle_dialog_completion(self, success: bool):
        """Handle progress dialog being closed"""
        logger.info(f"Progress dialog closed, success: {success}")
        # Don't cleanup here - let operation completion handle it
        # This prevents race conditions
    
    def _cleanup_operation(self):
        """Clean up after operation completion"""
        try:
            # Close progress dialog if still open
            if self.progress_dialog and self.progress_dialog.is_visible():
                self.progress_dialog.close()
            
            # Reset state
            self.is_operation_running = False
            self.current_operation_id = None
            self.current_start_time = None
            self.progress_dialog = None
            self.completion_callback = None
            self.error_callback = None
            
            logger.info("Operation cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during operation cleanup: {e}")
    
    def cleanup(self):
        """Cleanup coordinator resources"""
        try:
            # Cancel any running operation
            if self.is_operation_running:
                self.cancel_current_operation()
            
            # Close dialog
            if self.progress_dialog:
                self.progress_dialog.close()
            
            # Cleanup batch service
            self.batch_service.cleanup()
            
            # Reset state
            self._cleanup_operation()
            
        except Exception as e:
            logger.error(f"Error during coordinator cleanup: {e}")


# Example integration với main application
class MainApplicationIntegration:
    """
    Example of how to integrate OperationProgressCoordinator với main application
    """
    
    def __init__(self, main_window: tk.Widget):
        self.main_window = main_window
        self.coordinator = OperationProgressCoordinator(main_window)
    
    def start_batch_rename(self, files: List[FileInfo], rules, source_directory: str):
        """Start batch rename operation với progress dialog"""
        
        def on_completion(result: OperationResult, success: bool):
            if success:
                message = f"Successfully processed {result.success_count} files"
                if result.error_count > 0:
                    message += f" ({result.error_count} errors)"
                self._show_completion_message("Operation Completed", message)
            else:
                error_msg = result.error_message or "Operation failed"
                self._show_error_message("Operation Failed", error_msg)
        
        def on_error(error_message: str):
            self._show_error_message("Operation Error", error_message)
        
        # Start operation
        success = self.coordinator.execute_batch_rename(
            files=files,
            normalization_rules=rules,
            source_directory=source_directory,
            dry_run=False,
            completion_callback=on_completion,
            error_callback=on_error
        )
        
        if not success:
            self._show_error_message("Cannot Start Operation", 
                                   "Another operation is already running or failed to start")
    
    def _show_completion_message(self, title: str, message: str):
        """Show completion message to user"""
        from tkinter import messagebox
        messagebox.showinfo(title, message, parent=self.main_window)
    
    def _show_error_message(self, title: str, message: str):
        """Show error message to user"""
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self.main_window)
    
    def cleanup(self):
        """Cleanup application integration"""
        self.coordinator.cleanup()