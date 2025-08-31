"""
Comprehensive Error Models for Enhanced Error Handling

Provides detailed error classification, validation results, and recovery options
for all file operation scenarios.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Callable


class ErrorCode(Enum):
    """Comprehensive error codes for all file operation scenarios"""
    
    # File System Errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    FILE_IN_USE = "FILE_IN_USE"
    DISK_FULL = "DISK_FULL"
    PATH_TOO_LONG = "PATH_TOO_LONG"
    INVALID_PATH = "INVALID_PATH"
    READ_ONLY_FILE = "READ_ONLY_FILE"
    
    # File Name Validation Errors
    INVALID_FILENAME = "INVALID_FILENAME"
    INVALID_CHARACTERS = "INVALID_CHARACTERS"
    RESERVED_FILENAME = "RESERVED_FILENAME"
    FILENAME_TOO_LONG = "FILENAME_TOO_LONG"
    DUPLICATE_NAME_CONFLICT = "DUPLICATE_NAME_CONFLICT"
    
    # Network and Drive Errors
    NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
    DRIVE_NOT_READY = "DRIVE_NOT_READY"
    REMOTE_PATH_NOT_FOUND = "REMOTE_PATH_NOT_FOUND"
    
    # Operation Errors
    OPERATION_CANCELLED = "OPERATION_CANCELLED"
    PARTIAL_OPERATION_FAILURE = "PARTIAL_OPERATION_FAILURE"
    OPERATION_TIMEOUT = "OPERATION_TIMEOUT"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    
    # System Errors
    INSUFFICIENT_MEMORY = "INSUFFICIENT_MEMORY"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorSeverity(Enum):
    """Error severity levels for appropriate handling"""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class RecoveryStrategy(Enum):
    """Available recovery strategies for different error types"""
    RETRY = "retry"
    RETRY_AS_ADMIN = "retry_as_admin"
    SKIP_FILE = "skip_file"
    MANUAL_INTERVENTION = "manual_intervention"
    CHANGE_DESTINATION = "change_destination"
    FREE_DISK_SPACE = "free_disk_space"
    RECONNECT_NETWORK = "reconnect_network"
    WAIT_FOR_FILE_RELEASE = "wait_for_file_release"
    RENAME_CONFLICTING_FILE = "rename_conflicting_file"
    NONE = "none"


@dataclass
class RecoveryOption:
    """Represents a recovery option available to the user"""
    strategy: RecoveryStrategy
    description: str
    callback: Optional[Callable[[], bool]] = None
    requires_user_input: bool = False
    estimated_time: Optional[str] = None
    success_probability: float = 0.5  # 0.0 to 1.0


@dataclass
class ApplicationError:
    """
    Comprehensive error model with context, recovery options, and user messaging
    """
    code: ErrorCode
    message: str
    severity: ErrorSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Context Information
    operation_id: Optional[str] = None
    file_path: Optional[str] = None
    operation_context: Dict[str, Any] = field(default_factory=dict)
    
    # Technical Details
    technical_details: Optional[str] = None
    exception_info: Optional[Exception] = None
    system_info: Dict[str, Any] = field(default_factory=dict)
    
    # User Experience
    user_message: Optional[str] = None
    recovery_options: List[RecoveryOption] = field(default_factory=list)
    help_url: Optional[str] = None
    
    # Error Correlation
    correlation_id: Optional[str] = None
    parent_error_id: Optional[str] = None
    
    def to_user_message(self) -> str:
        """Convert technical error to user-friendly message"""
        if self.user_message:
            return self.user_message
        
        # Generate user-friendly message based on error code
        message_map = {
            ErrorCode.PERMISSION_DENIED: self._format_permission_error(),
            ErrorCode.FILE_IN_USE: self._format_file_in_use_error(),
            ErrorCode.DISK_FULL: self._format_disk_full_error(),
            ErrorCode.NETWORK_UNAVAILABLE: self._format_network_error(),
            ErrorCode.INVALID_FILENAME: self._format_invalid_filename_error(),
            ErrorCode.DUPLICATE_NAME_CONFLICT: self._format_duplicate_name_error(),
            ErrorCode.PATH_TOO_LONG: self._format_path_too_long_error(),
        }
        
        return message_map.get(self.code, self.message)
    
    def _format_permission_error(self) -> str:
        """Format permission denied error message"""
        file_name = self.file_path.split('\\')[-1] if self.file_path else "file"
        return (f"Access denied to {file_name}. "
                f"The file may be protected or require administrator privileges.")
    
    def _format_file_in_use_error(self) -> str:
        """Format file in use error message"""
        file_name = self.file_path.split('\\')[-1] if self.file_path else "file"
        return (f"Cannot rename {file_name} because it is currently being used "
                f"by another program. Please close the file and try again.")
    
    def _format_disk_full_error(self) -> str:
        """Format disk full error message"""
        return ("Insufficient disk space to complete the operation. "
                "Please free up some space and try again.")
    
    def _format_network_error(self) -> str:
        """Format network error message"""
        return ("Network connection lost. Please check your network connection "
                "and ensure the destination is accessible.")
    
    def _format_invalid_filename_error(self) -> str:
        """Format invalid filename error message"""
        return ("The filename contains invalid characters or is not allowed. "
                "Please use only letters, numbers, spaces, and common punctuation.")
    
    def _format_duplicate_name_error(self) -> str:
        """Format duplicate name error message"""
        file_name = self.file_path.split('\\')[-1] if self.file_path else "file"
        return (f"A file named {file_name} already exists. "
                f"Choose a different name or rename the existing file.")
    
    def _format_path_too_long_error(self) -> str:
        """Format path too long error message"""
        return ("The file path is too long for Windows. "
                "Please use shorter folder names or move files to a shorter path.")
    
    def add_recovery_option(self, option: RecoveryOption):
        """Add a recovery option to this error"""
        self.recovery_options.append(option)
    
    def get_primary_recovery_option(self) -> Optional[RecoveryOption]:
        """Get the most likely successful recovery option"""
        if not self.recovery_options:
            return None
        
        # Sort by success probability (descending)
        sorted_options = sorted(self.recovery_options, 
                              key=lambda x: x.success_probability, 
                              reverse=True)
        return sorted_options[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging and serialization"""
        return {
            'error_id': id(self),
            'code': self.code.value,
            'message': self.message,
            'severity': self.severity.value,
            'timestamp': self.timestamp.isoformat(),
            'operation_id': self.operation_id,
            'file_path': self.file_path,
            'operation_context': self.operation_context,
            'technical_details': self.technical_details,
            'user_message': self.to_user_message(),
            'recovery_options': [
                {
                    'strategy': opt.strategy.value,
                    'description': opt.description,
                    'requires_user_input': opt.requires_user_input,
                    'estimated_time': opt.estimated_time,
                    'success_probability': opt.success_probability
                } for opt in self.recovery_options
            ],
            'help_url': self.help_url,
            'correlation_id': self.correlation_id
        }


class ValidationErrorCode(Enum):
    """Error codes specific to file validation"""
    INVALID_CHARACTER = "INVALID_CHARACTER"
    RESERVED_NAME = "RESERVED_NAME"
    TOO_LONG = "TOO_LONG"
    TOO_SHORT = "TOO_SHORT"
    DUPLICATE_NAME = "DUPLICATE_NAME"
    UNSAFE_EXTENSION = "UNSAFE_EXTENSION"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"


@dataclass
class ValidationError:
    """Detailed validation error with suggestions"""
    code: ValidationErrorCode
    message: str
    field: str
    value: str
    suggested_fix: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.ERROR
    
    def to_user_message(self) -> str:
        """Get user-friendly validation error message"""
        if self.suggested_fix:
            return f"{self.message} Suggestion: {self.suggested_fix}"
        return self.message


@dataclass
class ValidationResult:
    """Complete validation result with errors and warnings"""
    is_valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    
    def add_error(self, code: ValidationErrorCode, message: str, field: str, 
                  value: str, suggested_fix: Optional[str] = None):
        """Add validation error"""
        error = ValidationError(
            code=code,
            message=message,
            field=field,
            value=value,
            suggested_fix=suggested_fix,
            severity=ErrorSeverity.ERROR
        )
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, code: ValidationErrorCode, message: str, field: str,
                    value: str, suggested_fix: Optional[str] = None):
        """Add validation warning"""
        warning = ValidationError(
            code=code,
            message=message,
            field=field,
            value=value,
            suggested_fix=suggested_fix,
            severity=ErrorSeverity.WARNING
        )
        self.warnings.append(warning)
    
    def has_blocking_errors(self) -> bool:
        """Check if there are errors that should block the operation"""
        blocking_codes = {
            ValidationErrorCode.INVALID_CHARACTER,
            ValidationErrorCode.RESERVED_NAME,
            ValidationErrorCode.TOO_LONG,
            ValidationErrorCode.PATH_TRAVERSAL
        }
        return any(error.code in blocking_codes for error in self.errors)
    
    def get_summary_message(self) -> str:
        """Get summary of validation results"""
        if self.is_valid:
            if self.warnings:
                return f"Valid with {len(self.warnings)} warnings"
            return "Valid"
        
        error_count = len(self.errors)
        warning_count = len(self.warnings)
        
        parts = []
        if error_count > 0:
            parts.append(f"{error_count} error{'s' if error_count > 1 else ''}")
        if warning_count > 0:
            parts.append(f"{warning_count} warning{'s' if warning_count > 1 else ''}")
        
        return f"Invalid: {', '.join(parts)}"


# Error Creation Helper Functions
def create_permission_error(file_path: str, operation_id: Optional[str] = None) -> ApplicationError:
    """Create a permission denied error with appropriate recovery options"""
    error = ApplicationError(
        code=ErrorCode.PERMISSION_DENIED,
        message=f"Permission denied accessing {file_path}",
        severity=ErrorSeverity.ERROR,
        file_path=file_path,
        operation_id=operation_id
    )
    
    # Add recovery options
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.RETRY_AS_ADMIN,
        description="Run as Administrator",
        success_probability=0.8
    ))
    
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.SKIP_FILE,
        description="Skip this file and continue",
        success_probability=1.0
    ))
    
    return error


def create_file_in_use_error(file_path: str, operation_id: Optional[str] = None) -> ApplicationError:
    """Create a file in use error with appropriate recovery options"""
    error = ApplicationError(
        code=ErrorCode.FILE_IN_USE,
        message=f"File {file_path} is currently in use",
        severity=ErrorSeverity.ERROR,
        file_path=file_path,
        operation_id=operation_id
    )
    
    # Add recovery options
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.WAIT_FOR_FILE_RELEASE,
        description="Wait and retry automatically",
        estimated_time="30 seconds",
        success_probability=0.7
    ))
    
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.RETRY,
        description="Retry now",
        success_probability=0.3
    ))
    
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.SKIP_FILE,
        description="Skip this file and continue",
        success_probability=1.0
    ))
    
    return error


def create_disk_full_error(required_space: int, available_space: int, 
                          operation_id: Optional[str] = None) -> ApplicationError:
    """Create a disk full error with space information"""
    error = ApplicationError(
        code=ErrorCode.DISK_FULL,
        message="Insufficient disk space",
        severity=ErrorSeverity.ERROR,
        operation_id=operation_id,
        operation_context={
            'required_space_mb': required_space // (1024 * 1024),
            'available_space_mb': available_space // (1024 * 1024)
        }
    )
    
    # Add recovery options
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.FREE_DISK_SPACE,
        description=f"Free up {(required_space - available_space) // (1024 * 1024)} MB of disk space",
        requires_user_input=True,
        success_probability=0.9
    ))
    
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.CHANGE_DESTINATION,
        description="Choose a different destination folder",
        requires_user_input=True,
        success_probability=0.8
    ))
    
    return error


def create_network_error(network_path: str, operation_id: Optional[str] = None) -> ApplicationError:
    """Create a network unavailable error"""
    error = ApplicationError(
        code=ErrorCode.NETWORK_UNAVAILABLE,
        message=f"Network path {network_path} is not accessible",
        severity=ErrorSeverity.ERROR,
        file_path=network_path,
        operation_id=operation_id
    )
    
    # Add recovery options
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.RECONNECT_NETWORK,
        description="Reconnect to network drive",
        estimated_time="10 seconds",
        success_probability=0.6
    ))
    
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.RETRY,
        description="Retry connection",
        success_probability=0.4
    ))
    
    error.add_recovery_option(RecoveryOption(
        strategy=RecoveryStrategy.CHANGE_DESTINATION,
        description="Choose a local destination",
        requires_user_input=True,
        success_probability=0.9
    ))
    
    return error