"""
Batch Operation Service

Handles batch file operations in background threads with UI progress updates.
Provides thread-safe communication between background operations and UI components.
"""

import threading
import queue
import time
from typing import Optional, Callable, List, Any
from dataclasses import dataclass
from datetime import datetime
import logging

from ..models.file_info import FileInfo, RenamePreview
from ..models.operation import (
    BatchOperation, NormalizationRules, OperationType,
    CancellationToken, OperationResult, OperationStatus,
    FileOperationResult, TimeEstimator, ProgressCallback,
    OperationCancelledException
)
from .file_operations_engine import FileOperationsEngine
from .normalize_service import VietnameseNormalizer
from .operation_history_service import OperationHistoryService
from .database_service import DatabaseService

# Configure logging
logger = logging.getLogger(__name__)

# Constants for progress tracking
PROGRESS_SETUP_PERCENTAGE = 5.0
PROGRESS_EXECUTION_PERCENTAGE = 90.0
PROGRESS_CLEANUP_PERCENTAGE = 5.0
CANCELLATION_CHECK_INTERVAL = 10  # Check cancellation every N operations
THREAD_JOIN_TIMEOUT = 5.0  # Timeout for thread joins


@dataclass
class BatchOperationRequest:
    """Request for batch operation execution"""
    files: List[FileInfo]
    rules: NormalizationRules
    dry_run: bool = False
    source_directory: str = ""
    operation_type: OperationType = OperationType.BATCH_RENAME


@dataclass
class OperationProgress:
    """Enhanced progress update information with timing data"""
    operation_id: str
    percentage: float
    current_file: str
    processed_files: int
    total_files: int
    is_completed: bool = False
    has_error: bool = False
    error_message: Optional[str] = None
    
    # Enhanced timing information
    elapsed_time: Optional[str] = None
    estimated_time_remaining: Optional[str] = None
    processing_speed: Optional[str] = None
    
    # Results summary
    success_count: int = 0
    error_count: int = 0
    skipped_count: int = 0


class BatchOperationService:
    """
    Service for executing batch operations in background threads
    
    Features:
    - Non-blocking batch file operations
    - Thread-safe progress updates
    - Operation cancellation support
    - Result callbacks
    - Error handling and reporting
    """
    
    def __init__(self, normalizer: Optional[VietnameseNormalizer] = None,
                 database_service: Optional[DatabaseService] = None,
                 operation_history_service: Optional[OperationHistoryService] = None):
        self.file_engine = FileOperationsEngine(normalizer)
        
        # Database and history services for undo functionality
        self.db = database_service or DatabaseService()
        self.history_service = operation_history_service or OperationHistoryService(self.db)
        
        # Threading components
        self._worker_thread: Optional[threading.Thread] = None
        self._progress_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._state_lock = threading.Lock()
        
        # Enhanced cancellation and progress tracking
        self._cancellation_token = CancellationToken()
        self._time_estimator = TimeEstimator()
        
        # Operation state
        self._current_operation: Optional[BatchOperation] = None
        self._current_result: Optional[OperationResult] = None
        self._is_running = False
        
        # Callbacks
        self.progress_callback: Optional[Callable[[OperationProgress], None]] = None
        self.completion_callback: Optional[Callable[[OperationResult], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
    def execute_batch_operation(self, request: BatchOperationRequest,
                              progress_callback: Optional[Callable[[OperationProgress], None]] = None,
                              completion_callback: Optional[Callable[[OperationResult], None]] = None,
                              error_callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Execute batch operation in background thread
        
        Args:
            request: Batch operation request
            progress_callback: Callback for progress updates
            completion_callback: Callback for operation completion
            error_callback: Callback for error handling
            
        Returns:
            Operation ID for tracking
            
        Raises:
            RuntimeError: If another operation is already running
        """
        if self._is_running:
            raise RuntimeError("Another batch operation is already running")
            
        # Set callbacks
        self.progress_callback = progress_callback
        self.completion_callback = completion_callback
        self.error_callback = error_callback
        
        # Create operation configuration
        operation_config = BatchOperation(
            operation_type=request.operation_type,
            normalization_rules=request.rules,
            source_directory=request.source_directory,
            total_files=len(request.files),
            dry_run=request.dry_run
        )
        
        # Create operation result tracker
        self._current_result = OperationResult(
            operation_id=operation_config.operation_id,
            operation_type=request.operation_type.value,
            status=OperationStatus.PENDING,
            total_files=len(request.files),
            start_time=datetime.now()
        )
        
        self._current_operation = operation_config
        self._is_running = True
        self._cancel_event.clear()
        self._cancellation_token.reset()
        self._time_estimator.start()
        
        # Start worker thread
        self._worker_thread = threading.Thread(
            target=self._worker_thread_function,
            args=(request, operation_config),
            name=f"BatchOperation-{operation_config.operation_id}"
        )
        self._worker_thread.daemon = True
        self._worker_thread.start()
        
        # Start progress monitoring
        self._start_progress_monitor()
        
        return operation_config.operation_id
        
    def cancel_operation(self) -> bool:
        """
        Cancel the current batch operation
        
        Returns:
            True if cancellation was requested, False if no operation running
        """
        if not self._is_running:
            return False
            
        operation_id = self._current_operation.operation_id if self._current_operation else "unknown"
        logger.info(f"Cancellation requested for operation {operation_id}")
        self._cancel_event.set()
        self._cancellation_token.request_cancellation("User requested cancellation")
        self.file_engine.cancel_current_operation()
        return True
        
    def is_operation_running(self) -> bool:
        """Check if a batch operation is currently running"""
        # Thread-safe check
        with self._state_lock:
            return self._is_running and (self._worker_thread and self._worker_thread.is_alive())
        
    def get_current_operation(self) -> Optional[BatchOperation]:
        """Get the currently running operation"""
        return self._current_operation
        
    def _worker_thread_function(self, request: BatchOperationRequest, operation_config: BatchOperation):
        """Main worker thread function for batch operations với enhanced cancellation và timing"""
        try:
            logger.info(f"Starting batch operation {operation_config.operation_id}")
            self._current_result.status = OperationStatus.RUNNING
            
            # Generate rename previews
            self._cancellation_token.check_cancelled()
            self._send_progress_update(0.0, "Scanning files and generating previews...", operation_config)
            previews = self.file_engine.preview_rename(request.files, request.rules)
            
            self._cancellation_token.check_cancelled()
                
            # Resolve conflicts
            self._send_progress_update(PROGRESS_SETUP_PERCENTAGE, "Resolving naming conflicts...", operation_config)
            previews = self.file_engine.detect_and_resolve_conflicts(previews)
            
            self._cancellation_token.check_cancelled()
                
            # Execute batch rename với enhanced progress tracking
            def progress_update_wrapper(percentage: float, current_file: str):
                # Map to overall progress
                overall_percentage = PROGRESS_SETUP_PERCENTAGE + (percentage * (PROGRESS_EXECUTION_PERCENTAGE / 100.0))
                
                # Update time estimator
                current_processed = int((overall_percentage / 100.0) * self._current_result.total_files)
                self._time_estimator.update(current_processed, self._current_result.total_files)
                
                self._send_progress_update(overall_percentage, current_file, operation_config)
                
                # Check for cancellation with new token
                self._cancellation_token.check_cancelled()
                    
            result = self.file_engine.execute_batch_rename(
                previews, 
                operation_config, 
                progress_update_wrapper,
                self._cancellation_token
            )
            
            # Update result with file operations
            for file_result in result.operation_log:  # Assuming operation_log contains results
                # Create FileOperationResult from log entry
                # This is a simplified conversion - real implementation would need proper parsing
                pass
            
            # Final progress update
            self._cancellation_token.check_cancelled()
            self._current_result.mark_completed()
            
            # Save operation to history with undo metadata (if not dry run)
            if not operation_config.dry_run:
                self._save_operation_with_undo_metadata(operation_config, result, previews)
            
            self._send_progress_update(100.0, "Operation completed successfully", operation_config)
            self._send_completion_result(self._current_result)
            logger.info(f"Batch operation {operation_config.operation_id} completed successfully")
            
        except OperationCancelledException as e:
            self._handle_cancellation_with_result(e.reason, e.partial_result)
        except InterruptedError:
            self._handle_cancellation_with_result("User interrupted operation")
        except Exception as e:
            error_msg = f"Batch operation failed: {str(e)}"
            logger.error(f"Operation {operation_config.operation_id} failed: {e}")
            self._current_result.mark_failed(error_msg, fatal=True)
            self._send_error_result(error_msg, operation_config)
        finally:
            self._is_running = False
            
    def _send_progress_update(self, percentage: float, current_file: str, operation_config: BatchOperation):
        """Send enhanced progress update với timing information to UI thread"""
        try:
            # Calculate current processed files from percentage
            current_processed = int((percentage / 100.0) * operation_config.total_files)
            
            # Update time estimator
            self._time_estimator.update(current_processed, operation_config.total_files)
            
            progress = self._create_progress_info(
                operation_config, percentage, current_file, current_processed
            )
            
            # Send to queue (non-blocking)
            self._progress_queue.put_nowait(progress)
            
        except queue.Full:
            # Queue is full, skip this update to maintain responsiveness
            logger.debug("Progress queue full, skipping update")
        except Exception as e:
            logger.warning(f"Error sending progress update: {e}")
    
    def _create_progress_info(self, operation_config: BatchOperation, 
                            percentage: float, current_file: str, 
                            current_processed: int) -> OperationProgress:
        """Create progress info object with all timing and status data"""
        return OperationProgress(
            operation_id=operation_config.operation_id,
            percentage=percentage,
            current_file=current_file,
            processed_files=current_processed,
            total_files=operation_config.total_files,
            
            # Enhanced timing information
            elapsed_time=self._time_estimator.get_elapsed_time(),
            estimated_time_remaining=self._time_estimator.estimate_remaining_time(
                current_processed, operation_config.total_files
            ),
            processing_speed=self._time_estimator.get_processing_speed(current_processed),
            
            # Results summary from current result
            success_count=self._current_result.success_count if self._current_result else 0,
            error_count=self._current_result.error_count if self._current_result else 0,
            skipped_count=self._current_result.skipped_count if self._current_result else 0
        )
            
    def _send_completion_result(self, result: OperationResult):
        """Send completion result to UI thread"""
        try:
            self._result_queue.put_nowait(('completed', result))
        except queue.Full:
            logger.warning("Result queue full, completion result may be lost")
            
    def _send_error_result(self, error_message: str, operation_config: BatchOperation):
        """Send error result to UI thread"""
        progress = OperationProgress(
            operation_id=operation_config.operation_id,
            percentage=0.0,
            current_file="",
            processed_files=0,
            total_files=operation_config.total_files,
            is_completed=True,
            has_error=True,
            error_message=error_message
        )
        
        try:
            self._progress_queue.put_nowait(progress)
            self._result_queue.put_nowait(('error', error_message))
        except queue.Full:
            logger.warning("Queue full, error result may be lost")
            
    def _handle_cancellation_with_result(self, reason: str, partial_result: Optional[OperationResult] = None):
        """Handle operation cancellation với enhanced result tracking"""
        operation_id = self._current_operation.operation_id if self._current_operation else "unknown"
        logger.info(f"Operation {operation_id} was cancelled: {reason}")
        
        # Mark current result as cancelled
        if self._current_result:
            self._current_result.mark_cancelled(reason)
        
        if self._current_operation:
            self._current_operation.log_message(f"Operation cancelled: {reason}")
        
        # Create final progress update
        progress = OperationProgress(
            operation_id=operation_id,
            percentage=self._current_result.completion_percentage if self._current_result else 0.0,
            current_file="Operation cancelled",
            processed_files=self._current_result.success_count + self._current_result.error_count if self._current_result else 0,
            total_files=self._current_result.total_files if self._current_result else 0,
            is_completed=True,
            has_error=True,
            error_message=f"Operation cancelled: {reason}",
            
            # Include timing information
            elapsed_time=self._time_estimator.get_elapsed_time(),
            success_count=self._current_result.success_count if self._current_result else 0,
            error_count=self._current_result.error_count if self._current_result else 0,
            skipped_count=self._current_result.skipped_count if self._current_result else 0
        )
        
        try:
            self._progress_queue.put_nowait(progress)
            self._result_queue.put_nowait(('cancelled', self._current_result or partial_result))
        except queue.Full:
            pass
            
    def _start_progress_monitor(self):
        """Start progress monitoring in a separate thread"""
        monitor_thread = threading.Thread(
            target=self._progress_monitor_function,
            name=f"ProgressMonitor-{self._current_operation.operation_id}"
        )
        monitor_thread.daemon = True
        monitor_thread.start()
        
    def _progress_monitor_function(self):
        """Monitor progress updates and call callbacks on UI thread"""
        while self._is_running or not self._progress_queue.empty():
            try:
                # Check for progress updates
                progress = self._progress_queue.get(timeout=0.1)
                if self.progress_callback:
                    self.progress_callback(progress)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in progress monitor: {e}")
                
        # Check for final results
        try:
            while not self._result_queue.empty():
                result_type, result_data = self._result_queue.get_nowait()
                
                if result_type == 'completed' and self.completion_callback:
                    self.completion_callback(result_data)
                elif result_type == 'error' and self.error_callback:
                    self.error_callback(result_data)
                elif result_type == 'cancelled' and self.completion_callback:
                    self.completion_callback(result_data)
                    
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error processing final results: {e}")
            
    def cleanup(self):
        """Cleanup resources and stop any running operations"""
        if self._is_running:
            self.cancel_operation()
            
        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=THREAD_JOIN_TIMEOUT)
            if self._worker_thread.is_alive():
                logger.warning("Worker thread did not terminate cleanly")
                
        # Clear queues
        try:
            while not self._progress_queue.empty():
                self._progress_queue.get_nowait()
        except queue.Empty:
            pass
            
        try:
            while not self._result_queue.empty():
                self._result_queue.get_nowait()
        except queue.Empty:
            pass
            
        self._is_running = False
        self._current_operation = None
    
    def _save_operation_with_undo_metadata(self, operation_config: BatchOperation, 
                                          result: Any, previews: List[RenamePreview]):
        """Save operation with enhanced metadata for undo functionality"""
        try:
            from datetime import timedelta
            import os
            
            # Create file processing records with undo metadata
            file_records = []
            
            for preview in previews:
                if preview.has_changes and not preview.has_conflict:
                    # Get file modification time for undo validation
                    original_modified_time = None
                    file_size = 0
                    
                    try:
                        if os.path.exists(preview.file_info.path):
                            stat_info = os.stat(preview.file_info.path)
                            original_modified_time = datetime.fromtimestamp(stat_info.st_mtime)
                            file_size = stat_info.st_size
                    except (OSError, IOError) as e:
                        logger.warning(f"Could not get file stats for {preview.file_info.path}: {e}")
                        continue
                    
                    # Create file processing record
                    from ..models.file_info import FileProcessingRecord, OperationStatus
                    
                    record = FileProcessingRecord(
                        file_info=preview.file_info,
                        original_name=preview.file_info.name,
                        processed_name=preview.normalized_name,
                        operation_status=OperationStatus.SUCCESS,  # Assume success for now
                        operation_id=operation_config.operation_id,
                        source_path=preview.file_info.path,
                        target_path=preview.normalized_full_path,
                        started_at=operation_config.started_at,
                        completed_at=operation_config.completed_at
                    )
                    
                    file_records.append(record)
            
            # Save to history service
            success = self.history_service.save_operation(operation_config, file_records)
            
            if success:
                # Set undo expiry time (7 days from completion)
                expiry_time = datetime.now() + timedelta(days=7)
                
                # Update operation in database with undo-specific fields
                self.db.execute_update('''
                    UPDATE operation_history 
                    SET can_be_undone = ?, undo_expiry_time = ?
                    WHERE operation_id = ?
                ''', (True, expiry_time.isoformat(), operation_config.operation_id))
                
                # Save file metadata with original modification times for validation
                file_metadata = []
                for record in file_records:
                    try:
                        if os.path.exists(record.target_path):
                            stat_info = os.stat(record.target_path)
                            original_modified_time = datetime.fromtimestamp(stat_info.st_mtime)
                            
                            file_metadata.append((
                                operation_config.operation_id,
                                record.target_path,
                                record.processed_name,
                                record.original_name,
                                original_modified_time.isoformat(),
                                record.file_info.size,
                                None  # checksum - could be calculated if needed
                            ))
                    except (OSError, IOError):
                        continue
                
                if file_metadata:
                    self.db.execute_many('''
                        INSERT OR REPLACE INTO file_operations (
                            operation_id, file_path, new_name, original_name,
                            original_modified_time, file_size_bytes, file_checksum
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', file_metadata)
                
                logger.info(f"Saved operation {operation_config.operation_id} with undo metadata")
            else:
                logger.warning(f"Failed to save operation {operation_config.operation_id} to history")
                
        except Exception as e:
            logger.error(f"Failed to save operation with undo metadata: {e}")
        

# Example usage for testing
if __name__ == "__main__":
    def test_batch_operation_service():
        """Test the batch operation service"""
        import tempfile
        import os
        
        # Create test files
        with tempfile.TemporaryDirectory() as temp_dir:
            test_files = []
            for i in range(5):
                file_path = os.path.join(temp_dir, f"Tài liệu {i}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content {i}")
                test_files.append(FileInfo.from_path(file_path))
                
            # Create service
            service = BatchOperationService()
            
            def progress_handler(progress: OperationProgress):
                print(f"Progress: {progress.percentage:.1f}% - {progress.current_file}")
                
            def completion_handler(result: BatchOperation):
                print(f"Operation completed: {result.operation_id}")
                print(f"Success: {result.successful_operations}")
                print(f"Failed: {result.failed_operations}")
                
            def error_handler(error: str):
                print(f"Operation error: {error}")
                
            # Execute operation
            request = BatchOperationRequest(
                files=test_files,
                rules=NormalizationRules(),
                dry_run=True,  # Don't actually rename files
                source_directory=temp_dir
            )
            
            operation_id = service.execute_batch_operation(
                request,
                progress_handler,
                completion_handler,
                error_handler
            )
            
            print(f"Started operation: {operation_id}")
            
            # Wait for completion
            while service.is_operation_running():
                time.sleep(0.1)
                
            service.cleanup()
            print("Test completed")
            
    test_batch_operation_service()