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
from ..models.operation import BatchOperation, NormalizationRules, OperationType
from .file_operations_engine import FileOperationsEngine
from .normalize_service import VietnameseNormalizer

# Configure logging
logger = logging.getLogger(__name__)


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
    """Progress update information"""
    operation_id: str
    percentage: float
    current_file: str
    processed_files: int
    total_files: int
    is_completed: bool = False
    has_error: bool = False
    error_message: Optional[str] = None


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
    
    def __init__(self, normalizer: Optional[VietnameseNormalizer] = None):
        self.file_engine = FileOperationsEngine(normalizer)
        
        # Threading components
        self._worker_thread: Optional[threading.Thread] = None
        self._progress_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._state_lock = threading.Lock()
        
        # Operation state
        self._current_operation: Optional[BatchOperation] = None
        self._is_running = False
        
        # Callbacks
        self.progress_callback: Optional[Callable[[OperationProgress], None]] = None
        self.completion_callback: Optional[Callable[[BatchOperation], None]] = None
        self.error_callback: Optional[Callable[[str], None]] = None
        
    def execute_batch_operation(self, request: BatchOperationRequest,
                              progress_callback: Optional[Callable[[OperationProgress], None]] = None,
                              completion_callback: Optional[Callable[[BatchOperation], None]] = None,
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
        
        self._current_operation = operation_config
        self._is_running = True
        self._cancel_event.clear()
        
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
            
        logger.info(f"Cancellation requested for operation {self._current_operation.operation_id}")
        self._cancel_event.set()
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
        """Main worker thread function for batch operations"""
        try:
            logger.info(f"Starting batch operation {operation_config.operation_id}")
            
            # Generate rename previews
            self._send_progress_update(0.0, "Scanning files and generating previews...", operation_config)
            previews = self.file_engine.preview_rename(request.files, request.rules)
            
            if self._cancel_event.is_set():
                self._handle_cancellation(operation_config)
                return
                
            # Resolve conflicts
            self._send_progress_update(5.0, "Resolving naming conflicts...", operation_config)
            previews = self.file_engine.detect_and_resolve_conflicts(previews)
            
            if self._cancel_event.is_set():
                self._handle_cancellation(operation_config)
                return
                
            # Execute batch rename with progress updates
            def progress_update_wrapper(percentage: float, current_file: str):
                # Map to overall progress (5% for setup, 90% for execution, 5% for cleanup)
                overall_percentage = 5 + (percentage * 0.9)
                self._send_progress_update(overall_percentage, current_file, operation_config)
                
                # Check for cancellation
                if self._cancel_event.is_set():
                    raise InterruptedError("Operation cancelled by user")
                    
            result = self.file_engine.execute_batch_rename(
                previews, 
                operation_config, 
                progress_update_wrapper
            )
            
            # Final progress update
            if not self._cancel_event.is_set():
                self._send_progress_update(100.0, "Operation completed", operation_config)
                self._send_completion_result(result)
                logger.info(f"Batch operation {operation_config.operation_id} completed successfully")
            
        except InterruptedError:
            self._handle_cancellation(operation_config)
        except Exception as e:
            error_msg = f"Batch operation failed: {str(e)}"
            logger.error(f"Operation {operation_config.operation_id} failed: {e}")
            self._send_error_result(error_msg, operation_config)
        finally:
            self._is_running = False
            
    def _send_progress_update(self, percentage: float, current_file: str, operation_config: BatchOperation):
        """Send progress update to UI thread"""
        progress = OperationProgress(
            operation_id=operation_config.operation_id,
            percentage=percentage,
            current_file=current_file,
            processed_files=operation_config.processed_files,
            total_files=operation_config.total_files
        )
        
        try:
            self._progress_queue.put_nowait(progress)
        except queue.Full:
            # Queue is full, skip this update
            pass
            
    def _send_completion_result(self, result: BatchOperation):
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
            
    def _handle_cancellation(self, operation_config: BatchOperation):
        """Handle operation cancellation"""
        logger.info(f"Operation {operation_config.operation_id} was cancelled")
        operation_config.log_message("Operation cancelled by user")
        
        progress = OperationProgress(
            operation_id=operation_config.operation_id,
            percentage=0.0,
            current_file="Operation cancelled",
            processed_files=operation_config.processed_files,
            total_files=operation_config.total_files,
            is_completed=True,
            has_error=True,
            error_message="Operation cancelled by user"
        )
        
        try:
            self._progress_queue.put_nowait(progress)
            self._result_queue.put_nowait(('cancelled', operation_config))
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
            self._worker_thread.join(timeout=5.0)
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