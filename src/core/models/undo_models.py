"""
Undo Operation Data Models

Enhanced data models for undo functionality with detailed file mappings,
external modification detection, and atomic operation support.
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from enum import Enum

from .operation import OperationResult, CancellationToken
from .file_info import FileInfo


class UndoEligibilityReason(Enum):
    """Reasons why an operation cannot be undone"""
    OPERATION_NOT_FOUND = "operation_not_found"
    DRY_RUN_OPERATION = "dry_run_operation"
    NO_SUCCESSFUL_FILES = "no_successful_files"
    FILES_MISSING = "files_missing"
    FILES_READONLY = "files_readonly"
    FILES_MODIFIED_EXTERNALLY = "files_modified_externally"
    OPERATION_TOO_OLD = "operation_too_old"
    NAME_CONFLICTS_EXIST = "name_conflicts_exist"
    DISK_SPACE_INSUFFICIENT = "disk_space_insufficient"
    PERMISSION_DENIED = "permission_denied"


class UndoExecutionStatus(Enum):
    """Status of undo execution"""
    NOT_STARTED = "not_started"
    VALIDATING = "validating"
    PREPARING = "preparing"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class FileValidationResult:
    """Result of validating a file for undo operation"""
    file_path: str
    original_name: str
    current_name: str
    original_modified_time: datetime
    current_modified_time: Optional[datetime]
    is_valid: bool
    validation_error: Optional[str] = None
    can_be_restored: bool = True
    conflict_with_existing: bool = False
    existing_file_path: Optional[str] = None
    
    @property
    def was_modified_externally(self) -> bool:
        """Check if file was modified after the original operation"""
        if not self.current_modified_time:
            return True  # File missing or inaccessible
        
        # Allow small time differences (file system precision)
        time_diff = abs((self.current_modified_time - self.original_modified_time).total_seconds())
        return time_diff > 2.0  # 2 second tolerance


@dataclass
class UndoEligibility:
    """Complete eligibility assessment for undo operation"""
    can_undo: bool
    primary_reason: str
    all_reasons: List[str] = field(default_factory=list)
    
    # File-level details
    total_files: int = 0
    valid_files: int = 0
    invalid_files: int = 0
    
    # Specific file issues
    conflicting_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    missing_files: List[str] = field(default_factory=list)
    readonly_files: List[str] = field(default_factory=list)
    
    # Validation details
    file_validations: List[FileValidationResult] = field(default_factory=list)
    validation_timestamp: datetime = field(default_factory=datetime.now)
    
    def add_invalid_file(self, file_path: str, reason: str):
        """Add a file that cannot be undone"""
        self.invalid_files += 1
        if reason == "missing":
            self.missing_files.append(file_path)
        elif reason == "modified":
            self.modified_files.append(file_path)
        elif reason == "readonly":
            self.readonly_files.append(file_path)
        elif reason == "conflict":
            self.conflicting_files.append(file_path)
    
    def get_summary_message(self) -> str:
        """Get human-readable summary of undo eligibility"""
        if self.can_undo:
            return f"Operation can be undone ({self.valid_files} files)"
        
        # Build detailed message with priority order
        issues = []
        if self.missing_files:
            issues.append(f"{len(self.missing_files)} files missing")
        if self.modified_files:
            issues.append(f"{len(self.modified_files)} files modified externally")
        if self.conflicting_files:
            issues.append(f"{len(self.conflicting_files)} name conflicts")
        if self.readonly_files:
            issues.append(f"{len(self.readonly_files)} files read-only")
        
        return f"Cannot undo: {', '.join(issues)}" if issues else f"Cannot undo: {self.primary_reason}"


@dataclass
class NameConflict:
    """Represents a file name conflict during undo operation"""
    original_file: str  # File we want to restore
    conflicting_file: str  # Existing file that would be overwritten
    original_path: str
    conflicting_path: str
    resolution_strategy: Optional[str] = None
    temp_name: Optional[str] = None
    
    def suggest_temp_name(self) -> str:
        """Suggest a temporary name to resolve the conflict"""
        if self.temp_name:
            return self.temp_name
        
        base, ext = os.path.splitext(self.original_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_name = f"{base}_undo_temp_{timestamp}{ext}"
        return self.temp_name


@dataclass
class UndoExecutionPlan:
    """Detailed plan for executing an undo operation"""
    operation_id: str
    undo_operation_id: str
    total_files: int
    
    # File mappings for undo
    file_mappings: List[Tuple[str, str, str]] = field(default_factory=list)  # (current_path, original_name, target_path)
    
    # Conflict resolution
    name_conflicts: List[NameConflict] = field(default_factory=list)
    temp_name_mappings: Dict[str, str] = field(default_factory=dict)  # current_name -> temp_name
    
    # Execution phases
    validation_phase: bool = True
    conflict_resolution_phase: bool = False
    execution_phase: bool = False
    cleanup_phase: bool = False
    
    # Metadata
    estimated_duration: Optional[float] = None
    disk_space_required: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_file_mapping(self, current_path: str, original_name: str):
        """Add a file to be restored in the undo operation"""
        directory = os.path.dirname(current_path)
        target_path = os.path.join(directory, original_name)
        self.file_mappings.append((current_path, original_name, target_path))
    
    def add_name_conflict(self, conflict: NameConflict):
        """Add a name conflict that needs resolution"""
        self.name_conflicts.append(conflict)
        self.conflict_resolution_phase = True
    
    def estimate_execution_time(self) -> float:
        """Estimate execution time based on file count and conflicts"""
        base_time = self.total_files * 0.1  # 0.1 seconds per file
        conflict_time = len(self.name_conflicts) * 0.5  # 0.5 seconds per conflict
        self.estimated_duration = base_time + conflict_time
        return self.estimated_duration


@dataclass
class UndoOperationMetadata:
    """Enhanced metadata for undo operations with external modification tracking"""
    operation_id: str
    original_operation_id: str
    folder_path: str
    
    # File tracking with timestamps
    file_mappings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    # Structure: {current_filename: {
    #     'original_name': str,
    #     'original_modified_time': datetime,
    #     'operation_modified_time': datetime,
    #     'file_size': int,
    #     'checksum': Optional[str]
    # }}
    
    # Operation timing
    can_be_undone: bool = True
    undo_expiry_time: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_validated_at: Optional[datetime] = None
    
    # External modification tracking
    externally_modified_files: List[str] = field(default_factory=list)
    validation_failures: List[str] = field(default_factory=list)
    
    def add_file_mapping(self, current_name: str, original_name: str, 
                        original_modified_time: datetime, file_size: int,
                        checksum: Optional[str] = None):
        """Add file mapping for undo tracking"""
        self.file_mappings[current_name] = {
            'original_name': original_name,
            'original_modified_time': original_modified_time,
            'operation_modified_time': datetime.now(),
            'file_size': file_size,
            'checksum': checksum
        }
    
    def validate_file_integrity(self, current_name: str, current_path: str) -> FileValidationResult:
        """Validate that a file hasn't been modified externally"""
        if current_name not in self.file_mappings:
            return FileValidationResult(
                file_path=current_path,
                original_name="unknown",
                current_name=current_name,
                original_modified_time=datetime.now(),
                current_modified_time=None,
                is_valid=False,
                validation_error="File not found in undo metadata"
            )
        
        mapping = self.file_mappings[current_name]
        original_name = mapping['original_name']
        original_modified_time = mapping['original_modified_time']
        
        # Check if file exists
        if not os.path.exists(current_path):
            return FileValidationResult(
                file_path=current_path,
                original_name=original_name,
                current_name=current_name,
                original_modified_time=original_modified_time,
                current_modified_time=None,
                is_valid=False,
                validation_error="File no longer exists",
                can_be_restored=False
            )
        
        # Check modification time
        try:
            current_stat = os.stat(current_path)
            current_modified_time = datetime.fromtimestamp(current_stat.st_mtime)
            
            # Check for external modifications
            time_diff = abs((current_modified_time - original_modified_time).total_seconds())
            was_modified = time_diff > 2.0  # 2 second tolerance
            
            # Check for name conflicts
            directory = os.path.dirname(current_path)
            target_path = os.path.join(directory, original_name)
            conflict_exists = os.path.exists(target_path) and target_path != current_path
            
            return FileValidationResult(
                file_path=current_path,
                original_name=original_name,
                current_name=current_name,
                original_modified_time=original_modified_time,
                current_modified_time=current_modified_time,
                is_valid=not was_modified and not conflict_exists,
                validation_error="File modified externally" if was_modified else "Name conflict exists" if conflict_exists else None,
                can_be_restored=not conflict_exists,
                conflict_with_existing=conflict_exists,
                existing_file_path=target_path if conflict_exists else None
            )
            
        except OSError as e:
            return FileValidationResult(
                file_path=current_path,
                original_name=original_name,
                current_name=current_name,
                original_modified_time=original_modified_time,
                current_modified_time=None,
                is_valid=False,
                validation_error=f"File system error: {e}",
                can_be_restored=False
            )
    
    def mark_externally_modified(self, filename: str, reason: str):
        """Mark a file as externally modified"""
        self.externally_modified_files.append(filename)
        self.validation_failures.append(f"{filename}: {reason}")
        self.can_be_undone = False
    
    def is_expired(self) -> bool:
        """Check if undo operation has expired"""
        if not self.undo_expiry_time:
            return False
        return datetime.now() > self.undo_expiry_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            'operation_id': self.operation_id,
            'original_operation_id': self.original_operation_id,
            'folder_path': self.folder_path,
            'file_mappings': self.file_mappings,
            'can_be_undone': self.can_be_undone,
            'undo_expiry_time': self.undo_expiry_time.isoformat() if self.undo_expiry_time else None,
            'created_at': self.created_at.isoformat(),
            'last_validated_at': self.last_validated_at.isoformat() if self.last_validated_at else None,
            'externally_modified_files': self.externally_modified_files,
            'validation_failures': self.validation_failures
        }


@dataclass  
class UndoOperationResult:
    """Result of an undo operation execution"""
    operation_id: str
    original_operation_id: str
    execution_status: UndoExecutionStatus
    
    # Execution statistics
    total_files: int = 0
    successful_restorations: int = 0
    failed_restorations: int = 0
    skipped_files: int = 0
    
    # Detailed results
    restored_files: List[Tuple[str, str]] = field(default_factory=list)  # (old_name, restored_name)
    failed_files: List[Tuple[str, str]] = field(default_factory=list)   # (filename, error_reason)
    skipped_files_list: List[Tuple[str, str]] = field(default_factory=list)  # (filename, skip_reason)
    
    # Execution timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration: Optional[float] = None
    
    # Cancellation support
    was_cancelled: bool = False
    cancellation_reason: Optional[str] = None
    cancellation_time: Optional[datetime] = None
    
    # Error handling
    error_message: Optional[str] = None
    fatal_error: bool = False
    partial_success: bool = False
    
    def start_execution(self):
        """Mark undo execution as started"""
        self.execution_status = UndoExecutionStatus.EXECUTING
        self.start_time = datetime.now()
    
    def complete_execution(self, success: bool = True):
        """Mark undo execution as completed"""
        if success:
            self.execution_status = UndoExecutionStatus.COMPLETED
        else:
            self.execution_status = UndoExecutionStatus.FAILED
            
        self.end_time = datetime.now()
        if self.start_time:
            self.total_duration = (self.end_time - self.start_time).total_seconds()
        
        # Determine if partially successful
        self.partial_success = (self.successful_restorations > 0 and 
                               self.failed_restorations > 0)
    
    def cancel_execution(self, reason: str):
        """Mark undo execution as cancelled"""
        self.execution_status = UndoExecutionStatus.CANCELLED
        self.was_cancelled = True
        self.cancellation_reason = reason
        self.cancellation_time = datetime.now()
        if self.start_time:
            self.total_duration = (self.cancellation_time - self.start_time).total_seconds()
    
    def add_successful_restoration(self, old_name: str, restored_name: str):
        """Record a successful file restoration"""
        self.restored_files.append((old_name, restored_name))
        self.successful_restorations += 1
    
    def add_failed_restoration(self, filename: str, error_reason: str):
        """Record a failed file restoration"""
        self.failed_files.append((filename, error_reason))
        self.failed_restorations += 1
    
    def add_skipped_file(self, filename: str, skip_reason: str):
        """Record a skipped file"""
        self.skipped_files_list.append((filename, skip_reason))
        self.skipped_files += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.successful_restorations / self.total_files) * 100.0
    
    @property
    def is_successful(self) -> bool:
        """Check if undo operation was successful"""
        return (self.execution_status == UndoExecutionStatus.COMPLETED and 
                self.failed_restorations == 0)
    
    @property
    def completion_message(self) -> str:
        """Get human-readable completion message"""
        if self.was_cancelled:
            return f"Undo cancelled: {self.cancellation_reason}"
        
        if self.execution_status == UndoExecutionStatus.FAILED:
            return f"Undo failed: {self.error_message}"
        
        if self.partial_success:
            return f"Undo partially successful: {self.successful_restorations} restored, {self.failed_restorations} failed"
        
        if self.is_successful:
            return f"Undo successful: {self.successful_restorations} files restored"
        
        return "Undo operation status unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'operation_id': self.operation_id,
            'original_operation_id': self.original_operation_id,
            'execution_status': self.execution_status.value,
            'total_files': self.total_files,
            'successful_restorations': self.successful_restorations,
            'failed_restorations': self.failed_restorations,
            'skipped_files': self.skipped_files,
            'restored_files': self.restored_files,
            'failed_files': self.failed_files,
            'skipped_files_list': self.skipped_files_list,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_duration': self.total_duration,
            'was_cancelled': self.was_cancelled,
            'cancellation_reason': self.cancellation_reason,
            'cancellation_time': self.cancellation_time.isoformat() if self.cancellation_time else None,
            'error_message': self.error_message,
            'fatal_error': self.fatal_error,
            'partial_success': self.partial_success,
            'success_rate': self.success_rate,
            'is_successful': self.is_successful,
            'completion_message': self.completion_message
        }