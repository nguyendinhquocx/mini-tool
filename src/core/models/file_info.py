"""
File information data models for Vietnamese text processing
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class FileType(Enum):
    """File type enumeration"""
    FILE = "File"
    FOLDER = "Folder"
    UNKNOWN = "Unknown"


class OperationStatus(Enum):
    """File operation status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileInfo:
    """
    Comprehensive file information model
    
    Contains all metadata needed for file processing and normalization
    """
    # Basic file information
    name: str
    original_name: str
    path: str
    file_type: FileType
    
    # File system metadata
    size: int = 0
    size_formatted: str = ""
    modified_time: Optional[datetime] = None
    created_time: Optional[datetime] = None
    is_hidden: bool = False
    is_readonly: bool = False
    
    # Processing metadata
    is_selected: bool = True
    can_rename: bool = True
    processing_notes: List[str] = field(default_factory=list)
    
    # Extension handling
    extension: str = ""
    name_without_extension: str = ""
    
    def __post_init__(self):
        """Initialize computed fields after object creation"""
        if self.path and os.path.exists(self.path):
            self._populate_file_metadata()
        
        # Extract extension and name without extension
        if self.name:
            self.name_without_extension, self.extension = os.path.splitext(self.name)
    
    def _populate_file_metadata(self):
        """Populate file system metadata"""
        try:
            stat_info = os.stat(self.path)
            self.size = stat_info.st_size
            self.modified_time = datetime.fromtimestamp(stat_info.st_mtime)
            self.created_time = datetime.fromtimestamp(stat_info.st_ctime)
            
            # Check if file is hidden (starts with dot on Unix-like systems)
            self.is_hidden = os.path.basename(self.path).startswith('.')
            
            # Check read-only status
            self.is_readonly = not os.access(self.path, os.W_OK)
            
            # Format file size
            self.size_formatted = self._format_file_size(self.size)
            
        except (OSError, IOError) as e:
            self.processing_notes.append(f"Metadata error: {e}")
            self.can_rename = False
    
    def _format_file_size(self, size: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    @classmethod
    def from_path(cls, file_path: str) -> 'FileInfo':
        """
        Create FileInfo from file path
        
        Args:
            file_path: Absolute path to file or directory
            
        Returns:
            FileInfo object with populated metadata
        """
        if not os.path.exists(file_path):
            raise ValueError(f"Path does not exist: {file_path}")
            
        name = os.path.basename(file_path)
        is_file = os.path.isfile(file_path)
        
        return cls(
            name=name,
            original_name=name,
            path=os.path.abspath(file_path),
            file_type=FileType.FILE if is_file else FileType.FOLDER
        )
    
    def update_name(self, new_name: str):
        """Update the name and related fields"""
        self.name = new_name
        self.name_without_extension, self.extension = os.path.splitext(new_name)
    
    def add_processing_note(self, note: str):
        """Add a processing note"""
        self.processing_notes.append(f"{datetime.now().isoformat()}: {note}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'original_name': self.original_name,
            'path': self.path,
            'file_type': self.file_type.value,
            'size': self.size,
            'size_formatted': self.size_formatted,
            'modified_time': self.modified_time.isoformat() if self.modified_time else None,
            'created_time': self.created_time.isoformat() if self.created_time else None,
            'is_hidden': self.is_hidden,
            'is_readonly': self.is_readonly,
            'is_selected': self.is_selected,
            'can_rename': self.can_rename,
            'processing_notes': self.processing_notes,
            'extension': self.extension,
            'name_without_extension': self.name_without_extension
        }


@dataclass
class RenamePreview:
    """
    Preview of file rename operation showing before/after states
    Enhanced for two-column preview display with selection and conflict detection
    """
    # Core file data
    file_id: str
    file_info: FileInfo
    normalized_name: str
    normalized_full_path: str
    
    # Preview display state
    is_selected: bool = True
    has_conflict: bool = False
    is_unchanged: bool = False
    conflict_type: Optional[str] = None  # 'duplicate', 'invalid_chars'
    
    # Preview details
    changes_made: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    will_overwrite: bool = False
    target_exists: bool = False
    
    # Operation metadata
    operation_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def has_changes(self) -> bool:
        """Check if normalization will make any changes"""
        return self.file_info.name != self.normalized_name
    
    @property
    def original_name(self) -> str:
        """Get original filename"""
        return self.file_info.original_name
    
    @property
    def current_name(self) -> str:
        """Get current filename"""
        return self.file_info.name
    
    @property
    def preview_path(self) -> str:
        """Get full preview path"""
        return self.normalized_full_path
    
    def add_change_description(self, description: str):
        """Add description of change made during normalization"""
        self.changes_made.append(description)
    
    def add_warning(self, warning: str):
        """Add warning about the rename operation"""
        self.warnings.append(warning)
    
    def check_target_conflicts(self):
        """Check if target file already exists"""
        if os.path.exists(self.normalized_full_path):
            self.target_exists = True
            if self.normalized_full_path != self.file_info.path:
                self.will_overwrite = True
                self.add_warning(f"Target file already exists: {self.normalized_name}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'file_info': self.file_info.to_dict(),
            'normalized_name': self.normalized_name,
            'normalized_full_path': self.normalized_full_path,
            'changes_made': self.changes_made,
            'warnings': self.warnings,
            'will_overwrite': self.will_overwrite,
            'target_exists': self.target_exists,
            'has_changes': self.has_changes,
            'operation_id': self.operation_id,
            'created_at': self.created_at.isoformat()
        }


@dataclass
class FilePreviewState:
    """
    State management for file preview display with selection tracking
    """
    total_files: int = 0
    selected_files: int = 0
    unchanged_files: int = 0
    conflict_files: int = 0
    is_loading: bool = False
    
    def update_counts(self, preview_list: List['RenamePreview']):
        """Update counts based on preview list"""
        self.total_files = len(preview_list)
        self.selected_files = sum(1 for p in preview_list if p.is_selected)
        self.unchanged_files = sum(1 for p in preview_list if p.is_unchanged)
        self.conflict_files = sum(1 for p in preview_list if p.has_conflict)


@dataclass
class FileProcessingRecord:
    """
    Record of file processing operation with normalization metadata
    """
    file_info: FileInfo
    original_name: str
    processed_name: str
    operation_status: OperationStatus
    
    # Processing details
    normalization_applied: bool = False
    rules_used: Optional[Dict[str, Any]] = None
    processing_steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Operation metadata
    operation_id: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # File operation details
    source_path: str = ""
    target_path: str = ""
    backup_created: bool = False
    backup_path: Optional[str] = None
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.operation_id:
            self.operation_id = f"op_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
            
        if not self.source_path and self.file_info:
            self.source_path = self.file_info.path
    
    def start_processing(self):
        """Mark processing as started"""
        self.operation_status = OperationStatus.IN_PROGRESS
        self.started_at = datetime.now()
    
    def complete_processing(self, success: bool = True, error: Optional[str] = None):
        """Mark processing as completed"""
        self.completed_at = datetime.now()
        if success:
            self.operation_status = OperationStatus.SUCCESS
        else:
            self.operation_status = OperationStatus.FAILED
            self.error_message = error
    
    def add_processing_step(self, step_name: str, details: Dict[str, Any]):
        """Add a processing step record"""
        step = {
            'step_name': step_name,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.processing_steps.append(step)
    
    @property
    def processing_duration(self) -> Optional[float]:
        """Get processing duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_completed(self) -> bool:
        """Check if processing is completed"""
        return self.operation_status in [OperationStatus.SUCCESS, OperationStatus.FAILED, OperationStatus.SKIPPED]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'file_info': self.file_info.to_dict(),
            'original_name': self.original_name,
            'processed_name': self.processed_name,
            'operation_status': self.operation_status.value,
            'normalization_applied': self.normalization_applied,
            'rules_used': self.rules_used,
            'processing_steps': self.processing_steps,
            'operation_id': self.operation_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'source_path': self.source_path,
            'target_path': self.target_path,
            'backup_created': self.backup_created,
            'backup_path': self.backup_path,
            'processing_duration': self.processing_duration,
            'is_completed': self.is_completed
        }