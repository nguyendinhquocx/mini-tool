"""
Comprehensive Error Handler

Centralized error handling with classification, recovery options, and logging.
Provides consistent error management across all file operations.
"""

import os
import sys
import traceback
import logging
from typing import Optional, Dict, Any, List, Callable, Type
from contextlib import contextmanager
from datetime import datetime
import json

from ..models.error_models import (
    ApplicationError, ErrorCode, ErrorSeverity, RecoveryStrategy, RecoveryOption,
    create_permission_error, create_file_in_use_error, create_disk_full_error,
    create_network_error
)


class ErrorClassifier:
    """Classifies exceptions into structured ApplicationError objects"""
    
    # Error code mapping for common exceptions
    EXCEPTION_TO_ERROR_CODE = {
        PermissionError: ErrorCode.PERMISSION_DENIED,
        FileNotFoundError: ErrorCode.FILE_NOT_FOUND,
        OSError: ErrorCode.SYSTEM_ERROR,
        IOError: ErrorCode.SYSTEM_ERROR,
        ValueError: ErrorCode.INVALID_PATH,
        UnicodeError: ErrorCode.INVALID_FILENAME,
        MemoryError: ErrorCode.INSUFFICIENT_MEMORY,
    }
    
    # Windows-specific error codes
    WINDOWS_ERROR_CODES = {
        2: ErrorCode.FILE_NOT_FOUND,
        3: ErrorCode.INVALID_PATH,
        5: ErrorCode.PERMISSION_DENIED,
        32: ErrorCode.FILE_IN_USE,
        87: ErrorCode.INVALID_PATH,
        112: ErrorCode.DISK_FULL,
        206: ErrorCode.FILENAME_TOO_LONG,
        267: ErrorCode.INVALID_PATH,
    }
    
    @classmethod
    def classify_exception(cls, exception: Exception, context: Dict[str, Any] = None) -> ApplicationError:
        """
        Classify an exception into a structured ApplicationError
        
        Args:
            exception: The exception to classify
            context: Additional context information
            
        Returns:
            ApplicationError with appropriate classification and recovery options
        """
        context = context or {}
        file_path = context.get('file_path', '')
        operation_id = context.get('operation_id')
        
        # Handle Windows-specific errors
        if hasattr(exception, 'winerror') and exception.winerror in cls.WINDOWS_ERROR_CODES:
            error_code = cls.WINDOWS_ERROR_CODES[exception.winerror]
            return cls._create_windows_error(error_code, exception, file_path, operation_id, context)
        
        # Handle specific exception types
        if isinstance(exception, PermissionError):
            return create_permission_error(file_path, operation_id)
        
        elif isinstance(exception, FileNotFoundError):
            return cls._create_file_not_found_error(file_path, operation_id)
        
        elif isinstance(exception, OSError):
            return cls._classify_os_error(exception, file_path, operation_id, context)
        
        elif isinstance(exception, ValueError):
            return cls._create_invalid_path_error(str(exception), file_path, operation_id)
        
        else:
            return cls._create_unknown_error(exception, context)
    
    @classmethod
    def _create_windows_error(cls, error_code: ErrorCode, exception: Exception, 
                            file_path: str, operation_id: Optional[str], 
                            context: Dict[str, Any]) -> ApplicationError:
        """Create error based on Windows error code"""
        if error_code == ErrorCode.FILE_IN_USE:
            return create_file_in_use_error(file_path, operation_id)
        elif error_code == ErrorCode.DISK_FULL:
            return create_disk_full_error(
                context.get('required_space', 0),
                context.get('available_space', 0),
                operation_id
            )
        elif error_code == ErrorCode.PERMISSION_DENIED:
            return create_permission_error(file_path, operation_id)
        else:
            return ApplicationError(
                code=error_code,
                message=str(exception),
                severity=ErrorSeverity.ERROR,
                file_path=file_path,
                operation_id=operation_id,
                technical_details=f"Windows error {getattr(exception, 'winerror', 'unknown')}"
            )
    
    @classmethod
    def _create_file_not_found_error(cls, file_path: str, operation_id: Optional[str]) -> ApplicationError:
        """Create file not found error with recovery options"""
        error = ApplicationError(
            code=ErrorCode.FILE_NOT_FOUND,
            message=f"File not found: {file_path}",
            severity=ErrorSeverity.ERROR,
            file_path=file_path,
            operation_id=operation_id
        )
        
        # Add recovery options
        error.add_recovery_option(RecoveryOption(
            strategy=RecoveryStrategy.SKIP_FILE,
            description="Skip this file and continue",
            success_probability=1.0
        ))
        
        error.add_recovery_option(RecoveryOption(
            strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            description="Locate the file manually",
            requires_user_input=True,
            success_probability=0.7
        ))
        
        return error
    
    @classmethod
    def _classify_os_error(cls, exception: OSError, file_path: str, 
                          operation_id: Optional[str], context: Dict[str, Any]) -> ApplicationError:
        """Classify OSError into specific error types"""
        error_msg = str(exception).lower()
        
        # Check for specific error patterns
        if 'permission denied' in error_msg or 'access is denied' in error_msg:
            return create_permission_error(file_path, operation_id)
        elif 'being used by another process' in error_msg:
            return create_file_in_use_error(file_path, operation_id)
        elif 'not enough space' in error_msg or 'disk full' in error_msg:
            return create_disk_full_error(
                context.get('required_space', 0),
                context.get('available_space', 0),
                operation_id
            )
        elif 'network' in error_msg or 'remote' in error_msg:
            return create_network_error(file_path, operation_id)
        else:
            return ApplicationError(
                code=ErrorCode.SYSTEM_ERROR,
                message=str(exception),
                severity=ErrorSeverity.ERROR,
                file_path=file_path,
                operation_id=operation_id,
                technical_details=f"OSError: {exception}"
            )
    
    @classmethod
    def _create_invalid_path_error(cls, message: str, file_path: str, 
                                  operation_id: Optional[str]) -> ApplicationError:
        """Create invalid path error"""
        error = ApplicationError(
            code=ErrorCode.INVALID_PATH,
            message=f"Invalid path: {message}",
            severity=ErrorSeverity.ERROR,
            file_path=file_path,
            operation_id=operation_id
        )
        
        error.add_recovery_option(RecoveryOption(
            strategy=RecoveryStrategy.MANUAL_INTERVENTION,
            description="Choose a valid path",
            requires_user_input=True,
            success_probability=0.9
        ))
        
        return error
    
    @classmethod
    def _create_unknown_error(cls, exception: Exception, context: Dict[str, Any]) -> ApplicationError:
        """Create unknown error as fallback"""
        return ApplicationError(
            code=ErrorCode.UNKNOWN_ERROR,
            message=f"Unexpected error: {str(exception)}",
            severity=ErrorSeverity.ERROR,
            technical_details=traceback.format_exc(),
            operation_context=context,
            exception_info=exception
        )


class ServiceErrorHandler:
    """Service-level error handling with context management"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._error_history: List[ApplicationError] = []
        self._max_history = 100
    
    @contextmanager
    def handle_service_errors(self, operation_name: str, operation_id: Optional[str] = None,
                             context: Optional[Dict[str, Any]] = None):
        """
        Context manager for service-level error handling
        
        Args:
            operation_name: Name of the operation for logging
            operation_id: Optional operation ID for correlation
            context: Additional context for error classification
        """
        context = context or {}
        context['operation_name'] = operation_name
        context['operation_id'] = operation_id
        
        try:
            yield
        except Exception as e:
            # Classify the error
            app_error = ErrorClassifier.classify_exception(e, context)
            app_error.operation_id = operation_id
            app_error.operation_context.update(context)
            
            # Log the error
            self._log_application_error(app_error)
            
            # Add to history
            self._add_to_history(app_error)
            
            # Re-raise as ApplicationError for consistent handling
            raise ApplicationErrorException(app_error) from e
    
    def _log_application_error(self, error: ApplicationError):
        """Log application error with appropriate level"""
        log_data = {
            'error_code': error.code.value,
            'message': error.message,
            'file_path': error.file_path,
            'operation_id': error.operation_id,
            'context': error.operation_context
        }
        
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.ERROR:
            self.logger.error(f"Error: {error.message}", extra=log_data)
        elif error.severity == ErrorSeverity.WARNING:
            self.logger.warning(f"Warning: {error.message}", extra=log_data)
        else:
            self.logger.info(f"Info: {error.message}", extra=log_data)
    
    def _add_to_history(self, error: ApplicationError):
        """Add error to history with size limit"""
        self._error_history.append(error)
        if len(self._error_history) > self._max_history:
            self._error_history.pop(0)
    
    def get_recent_errors(self, count: int = 10) -> List[ApplicationError]:
        """Get recent errors from history"""
        return self._error_history[-count:]
    
    def get_errors_for_operation(self, operation_id: str) -> List[ApplicationError]:
        """Get all errors for a specific operation"""
        return [error for error in self._error_history 
                if error.operation_id == operation_id]


class ApplicationErrorException(Exception):
    """Exception that wraps ApplicationError for consistent error handling"""
    
    def __init__(self, application_error: ApplicationError):
        self.application_error = application_error
        super().__init__(application_error.message)
    
    def __str__(self):
        return self.application_error.to_user_message()


# Global error handler instance
_global_error_handler = ServiceErrorHandler()


def get_error_handler() -> ServiceErrorHandler:
    """Get the global error handler instance"""
    return _global_error_handler


# Convenience functions for common error handling patterns
def handle_file_operation_error(func: Callable, file_path: str, 
                               operation_name: str = "File Operation",
                               operation_id: Optional[str] = None) -> Any:
    """
    Handle file operation with automatic error classification
    
    Args:
        func: Function to execute
        file_path: Path of file being operated on
        operation_name: Name of operation for logging
        operation_id: Optional operation ID
        
    Returns:
        Result of function execution
        
    Raises:
        ApplicationErrorException: If operation fails
    """
    handler = get_error_handler()
    context = {'file_path': file_path}
    
    with handler.handle_service_errors(operation_name, operation_id, context):
        return func()


def safe_file_operation(func: Callable, file_path: str, 
                       operation_name: str = "File Operation",
                       operation_id: Optional[str] = None,
                       default_return=None) -> Any:
    """
    Execute file operation safely with error handling
    
    Args:
        func: Function to execute
        file_path: Path of file being operated on
        operation_name: Name of operation for logging
        operation_id: Optional operation ID
        default_return: Value to return if operation fails
        
    Returns:
        Result of function execution or default_return on error
    """
    try:
        return handle_file_operation_error(func, file_path, operation_name, operation_id)
    except ApplicationErrorException as e:
        # Log error and return default
        get_error_handler()._log_application_error(e.application_error)
        return default_return


# Error recovery helper functions
def create_retry_callback(func: Callable, max_retries: int = 3, 
                         delay: float = 1.0) -> Callable[[], bool]:
    """Create a retry callback for recovery options"""
    def retry_with_delay():
        import time
        for attempt in range(max_retries):
            try:
                func()
                return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                else:
                    return False
        return False
    
    return retry_with_delay


def create_admin_retry_callback(func: Callable) -> Callable[[], bool]:
    """Create a callback that attempts to run function as administrator"""
    def retry_as_admin():
        try:
            # On Windows, attempt to elevate privileges
            if sys.platform.startswith('win'):
                import ctypes
                try:
                    # Check if already running as admin
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                    if not is_admin:
                        # Would need to restart with elevation - return False for now
                        return False
                except:
                    return False
            
            # Try the function again
            func()
            return True
        except Exception:
            return False
    
    return retry_as_admin