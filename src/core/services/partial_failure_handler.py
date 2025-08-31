"""
Partial Operation Failure Handler

Provides sophisticated handling of partial failures in batch operations,
including recovery strategies, rollback mechanisms, and detailed reporting.
"""

import threading
import time
from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

from ..models.error_models import (
    ApplicationError, ErrorCode, ErrorSeverity, RecoveryStrategy, RecoveryOption
)
from ..models.operation import (
    OperationResult, OperationStatus, FileOperationResult, 
    BatchOperation, CancellationToken
)
from ..models.undo_models import UndoOperation, UndoOperationType, UndoMetadata
from .undo_service import UndoService
from ..utils.error_handler import ApplicationErrorException, ErrorClassifier

logger = logging.getLogger(__name__)


class PartialFailureStrategy(Enum):
    """Strategy for handling partial failures"""
    STOP_ON_FIRST_ERROR = "stop_on_first_error"
    SKIP_FAILED_CONTINUE = "skip_failed_continue"
    RETRY_FAILED_FILES = "retry_failed_files"
    ROLLBACK_ALL_CHANGES = "rollback_all_changes"
    MANUAL_INTERVENTION = "manual_intervention"


class FailureResolution(Enum):
    """Resolution action for failed operations"""
    SKIP = "skip"
    RETRY = "retry"
    MANUAL_FIX = "manual_fix"
    ROLLBACK = "rollback"
    ABORT = "abort"


@dataclass
class FailedFileOperation:
    """Information about a failed file operation"""
    file_path: str
    target_path: str
    error: ApplicationError
    attempt_count: int = 0
    max_attempts: int = 3
    can_retry: bool = True
    requires_manual_intervention: bool = False
    rollback_info: Optional[Dict[str, Any]] = None
    
    @property
    def has_attempts_remaining(self) -> bool:
        return self.attempt_count < self.max_attempts
    
    @property
    def should_auto_retry(self) -> bool:
        """Determine if this failure should be automatically retried"""
        auto_retry_codes = {
            ErrorCode.NETWORK_TIMEOUT,
            ErrorCode.DRIVE_NOT_READY,
            ErrorCode.CONCURRENT_MODIFICATION
        }
        return (self.has_attempts_remaining and 
                self.error.code in auto_retry_codes and 
                not self.requires_manual_intervention)


@dataclass
class PartialFailureReport:
    """Comprehensive report of partial operation failures"""
    operation_id: str
    total_files: int
    successful_operations: int
    failed_operations: int
    skipped_operations: int
    failed_files: List[FailedFileOperation] = field(default_factory=list)
    
    # Error categorization
    critical_errors: List[FailedFileOperation] = field(default_factory=list)
    recoverable_errors: List[FailedFileOperation] = field(default_factory=list)
    manual_intervention_required: List[FailedFileOperation] = field(default_factory=list)
    
    # Recovery options
    available_strategies: List[PartialFailureStrategy] = field(default_factory=list)
    recommended_strategy: Optional[PartialFailureStrategy] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.successful_operations / self.total_files) * 100
    
    @property
    def has_critical_errors(self) -> bool:
        """Check if there are any critical errors"""
        return len(self.critical_errors) > 0
    
    @property
    def can_continue_operation(self) -> bool:
        """Check if operation can continue despite failures"""
        return not self.has_critical_errors and self.success_rate >= 50.0
    
    def categorize_failures(self):
        """Categorize failed files by error severity and recovery options"""
        self.critical_errors.clear()
        self.recoverable_errors.clear()
        self.manual_intervention_required.clear()
        
        for failed_file in self.failed_files:
            if failed_file.error.severity == ErrorSeverity.CRITICAL:
                self.critical_errors.append(failed_file)
            elif failed_file.requires_manual_intervention:
                self.manual_intervention_required.append(failed_file)
            else:
                self.recoverable_errors.append(failed_file)
        
        # Determine available strategies based on failure types
        self._determine_available_strategies()
        self._recommend_strategy()
    
    def _determine_available_strategies(self):
        """Determine which strategies are available based on failure types"""
        self.available_strategies.clear()
        
        # Always available
        self.available_strategies.append(PartialFailureStrategy.SKIP_FAILED_CONTINUE)
        self.available_strategies.append(PartialFailureStrategy.STOP_ON_FIRST_ERROR)
        
        # Available if we have recoverable errors
        if self.recoverable_errors:
            self.available_strategies.append(PartialFailureStrategy.RETRY_FAILED_FILES)
        
        # Available if we have rollback information
        if any(f.rollback_info for f in self.failed_files):
            self.available_strategies.append(PartialFailureStrategy.ROLLBACK_ALL_CHANGES)
        
        # Available if we have manual intervention items
        if self.manual_intervention_required:
            self.available_strategies.append(PartialFailureStrategy.MANUAL_INTERVENTION)
    
    def _recommend_strategy(self):
        """Recommend the best strategy based on failure analysis"""
        if self.has_critical_errors:
            self.recommended_strategy = PartialFailureStrategy.ROLLBACK_ALL_CHANGES
        elif self.success_rate < 30.0:
            self.recommended_strategy = PartialFailureStrategy.STOP_ON_FIRST_ERROR
        elif len(self.recoverable_errors) > len(self.manual_intervention_required):
            self.recommended_strategy = PartialFailureStrategy.RETRY_FAILED_FILES
        else:
            self.recommended_strategy = PartialFailureStrategy.SKIP_FAILED_CONTINUE


class PartialFailureHandler:
    """Advanced handler for partial operation failures"""
    
    def __init__(self, undo_service: Optional[UndoService] = None):
        self.undo_service = undo_service
        self._active_failures: Dict[str, PartialFailureReport] = {}
        self._resolution_callbacks: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        
    def initialize_operation_tracking(self, operation_id: str, total_files: int) -> PartialFailureReport:
        """Initialize tracking for a new operation"""
        report = PartialFailureReport(
            operation_id=operation_id,
            total_files=total_files,
            successful_operations=0,
            failed_operations=0,
            skipped_operations=0
        )
        
        with self._lock:
            self._active_failures[operation_id] = report
        
        return report
    
    def record_success(self, operation_id: str):
        """Record a successful operation"""
        with self._lock:
            if operation_id in self._active_failures:
                self._active_failures[operation_id].successful_operations += 1
    
    def record_failure(self, operation_id: str, file_path: str, target_path: str, 
                      error: ApplicationError, rollback_info: Optional[Dict[str, Any]] = None) -> FailedFileOperation:
        """Record a failed operation and return failure information"""
        failed_operation = FailedFileOperation(
            file_path=file_path,
            target_path=target_path,
            error=error,
            rollback_info=rollback_info,
            requires_manual_intervention=self._requires_manual_intervention(error)
        )
        
        with self._lock:
            if operation_id in self._active_failures:
                report = self._active_failures[operation_id]
                report.failed_operations += 1
                report.failed_files.append(failed_operation)
                
                # Categorize failures after adding new one
                report.categorize_failures()
        
        return failed_operation
    
    def record_skip(self, operation_id: str):
        """Record a skipped operation"""
        with self._lock:
            if operation_id in self._active_failures:
                self._active_failures[operation_id].skipped_operations += 1
    
    def get_failure_report(self, operation_id: str) -> Optional[PartialFailureReport]:
        """Get current failure report for operation"""
        with self._lock:
            return self._active_failures.get(operation_id)
    
    def should_continue_operation(self, operation_id: str, strategy: PartialFailureStrategy) -> bool:
        """Determine if operation should continue based on strategy and current failures"""
        report = self.get_failure_report(operation_id)
        if not report:
            return True
        
        if strategy == PartialFailureStrategy.STOP_ON_FIRST_ERROR:
            return report.failed_operations == 0
        elif strategy == PartialFailureStrategy.SKIP_FAILED_CONTINUE:
            return report.can_continue_operation
        elif strategy == PartialFailureStrategy.ROLLBACK_ALL_CHANGES:
            return False  # Stop to perform rollback
        else:
            return report.can_continue_operation
    
    def handle_partial_failure(self, operation_id: str, 
                             strategy: PartialFailureStrategy = PartialFailureStrategy.SKIP_FAILED_CONTINUE,
                             user_callback: Optional[Callable[[PartialFailureReport], PartialFailureStrategy]] = None) -> Tuple[PartialFailureStrategy, List[FailedFileOperation]]:
        """
        Handle partial failures according to strategy
        
        Returns:
            Tuple of (final_strategy, files_to_retry)
        """
        report = self.get_failure_report(operation_id)
        if not report or not report.failed_files:
            return strategy, []
        
        # If user callback provided, let user choose strategy
        if user_callback:
            strategy = user_callback(report)
        elif strategy == PartialFailureStrategy.MANUAL_INTERVENTION and not user_callback:
            # Default to skip if no user callback for manual intervention
            strategy = PartialFailureStrategy.SKIP_FAILED_CONTINUE
        
        files_to_retry = []
        
        if strategy == PartialFailureStrategy.RETRY_FAILED_FILES:
            files_to_retry = self._prepare_retry_files(report)
        elif strategy == PartialFailureStrategy.ROLLBACK_ALL_CHANGES:
            self._perform_rollback(operation_id)
        elif strategy == PartialFailureStrategy.MANUAL_INTERVENTION:
            files_to_retry = self._handle_manual_intervention(report)
        
        return strategy, files_to_retry
    
    def _requires_manual_intervention(self, error: ApplicationError) -> bool:
        """Determine if error requires manual intervention"""
        manual_intervention_codes = {
            ErrorCode.PERMISSION_DENIED,
            ErrorCode.FILE_IN_USE,
            ErrorCode.DUPLICATE_NAME_CONFLICT,
            ErrorCode.INVALID_FILENAME,
            ErrorCode.PATH_TOO_LONG
        }
        return error.code in manual_intervention_codes
    
    def _prepare_retry_files(self, report: PartialFailureReport) -> List[FailedFileOperation]:
        """Prepare list of files that should be retried"""
        retry_files = []
        
        for failed_file in report.failed_files:
            if failed_file.should_auto_retry:
                failed_file.attempt_count += 1
                retry_files.append(failed_file)
        
        return retry_files
    
    def _perform_rollback(self, operation_id: str):
        """Perform rollback of all successful operations"""
        if not self.undo_service:
            logger.error(f"Cannot perform rollback for operation {operation_id}: No undo service available")
            return
        
        try:
            # Get the most recent undo operation for this operation_id
            recent_operations = self.undo_service.get_recent_operations(limit=10)
            
            for undo_op in recent_operations:
                if undo_op.operation_id == operation_id:
                    success = self.undo_service.execute_undo(undo_op.operation_id)
                    if success:
                        logger.info(f"Successfully rolled back operation {operation_id}")
                    else:
                        logger.error(f"Failed to rollback operation {operation_id}")
                    break
            else:
                logger.warning(f"No undo information found for operation {operation_id}")
                
        except Exception as e:
            logger.error(f"Error during rollback of operation {operation_id}: {str(e)}")
    
    def _handle_manual_intervention(self, report: PartialFailureReport) -> List[FailedFileOperation]:
        """Handle files requiring manual intervention"""
        # For now, return empty list - this would be extended to provide
        # user interface for manual resolution
        logger.info(f"Manual intervention required for {len(report.manual_intervention_required)} files")
        return []
    
    def create_recovery_options(self, failed_file: FailedFileOperation) -> List[RecoveryOption]:
        """Create recovery options for a failed file operation"""
        options = []
        
        # Skip option - always available
        options.append(RecoveryOption(
            strategy=RecoveryStrategy.SKIP_FILE,
            description="Skip this file and continue with others",
            success_probability=1.0
        ))
        
        # Retry option - if file has attempts remaining
        if failed_file.has_attempts_remaining:
            options.append(RecoveryOption(
                strategy=RecoveryStrategy.RETRY,
                description=f"Retry operation (attempt {failed_file.attempt_count + 1} of {failed_file.max_attempts})",
                success_probability=max(0.3, 0.8 - (failed_file.attempt_count * 0.2))
            ))
        
        # Error-specific options
        if failed_file.error.code == ErrorCode.PERMISSION_DENIED:
            options.append(RecoveryOption(
                strategy=RecoveryStrategy.RETRY_AS_ADMIN,
                description="Retry with administrator privileges",
                success_probability=0.8
            ))
        
        elif failed_file.error.code == ErrorCode.FILE_IN_USE:
            options.append(RecoveryOption(
                strategy=RecoveryStrategy.WAIT_FOR_FILE_RELEASE,
                description="Wait for file to be released and retry",
                estimated_time="30 seconds",
                success_probability=0.7
            ))
        
        elif failed_file.error.code == ErrorCode.DUPLICATE_NAME_CONFLICT:
            options.append(RecoveryOption(
                strategy=RecoveryStrategy.RENAME_CONFLICTING_FILE,
                description="Rename to avoid conflict",
                requires_user_input=True,
                success_probability=0.9
            ))
        
        elif failed_file.error.code in [ErrorCode.NETWORK_UNAVAILABLE, ErrorCode.NETWORK_TIMEOUT]:
            options.append(RecoveryOption(
                strategy=RecoveryStrategy.RECONNECT_NETWORK,
                description="Reconnect to network and retry",
                estimated_time="10 seconds",
                success_probability=0.6
            ))
        
        return options
    
    def finalize_operation(self, operation_id: str) -> Optional[PartialFailureReport]:
        """Finalize operation tracking and return final report"""
        with self._lock:
            return self._active_failures.pop(operation_id, None)
    
    def cleanup_old_operations(self, max_age_hours: int = 24):
        """Clean up old operation tracking data"""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        
        with self._lock:
            # Remove operations older than cutoff
            # This is a simple implementation - in practice you'd want to track creation time
            old_operations = []
            for op_id in self._active_failures.keys():
                # Simple cleanup - could be enhanced with timestamp tracking
                if len(self._active_failures) > 100:  # Keep only recent 100 operations
                    old_operations.append(op_id)
            
            for op_id in old_operations[:50]:  # Remove oldest 50
                self._active_failures.pop(op_id, None)


class PartialFailureDialog:
    """Dialog for handling partial operation failures with user interaction"""
    
    def __init__(self, parent, report: PartialFailureReport):
        self.parent = parent
        self.report = report
        self.selected_strategy = None
        self.files_to_retry = []
    
    def show_and_get_strategy(self) -> Tuple[PartialFailureStrategy, List[FailedFileOperation]]:
        """Show dialog and return user-selected strategy and files to retry"""
        # This would create a sophisticated UI dialog
        # For now, return default strategy
        
        if self.report.recommended_strategy:
            return self.report.recommended_strategy, []
        else:
            return PartialFailureStrategy.SKIP_FAILED_CONTINUE, []