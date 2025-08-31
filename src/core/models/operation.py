"""
Operation and normalization rules data models
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class OperationType(Enum):
    """Type of file operation"""
    NORMALIZE = "normalize"
    RENAME = "rename"
    BATCH_RENAME = "batch_rename"
    PREVIEW = "preview"
    RESTORE = "restore"


class ValidationLevel(Enum):
    """Validation level for operations"""
    STRICT = "strict"
    NORMAL = "normal"
    PERMISSIVE = "permissive"


@dataclass
class NormalizationRules:
    """
    Enhanced normalization rules configuration
    """
    # Core normalization options
    remove_diacritics: bool = True
    lowercase_conversion: bool = True
    clean_special_chars: bool = True
    normalize_whitespace: bool = True
    preserve_extensions: bool = True
    
    # Advanced options
    preserve_case_for_extensions: bool = True
    preserve_numbers: bool = True
    preserve_english_words: bool = True
    
    # Safety and validation
    validation_level: ValidationLevel = ValidationLevel.NORMAL
    create_backup: bool = True
    confirm_overwrite: bool = True
    skip_readonly_files: bool = True
    skip_hidden_files: bool = False
    
    # Character replacement mappings
    safe_char_replacements: Dict[str, str] = field(default_factory=dict)
    custom_replacements: Dict[str, str] = field(default_factory=dict)
    
    # Processing limits
    max_filename_length: int = 255
    min_filename_length: int = 1
    
    # Rule metadata
    rule_name: str = "Default Vietnamese Normalization"
    rule_description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "System"
    
    def __post_init__(self):
        """Initialize default character replacements if not provided"""
        if not self.safe_char_replacements:
            self.safe_char_replacements = self._get_default_char_replacements()
    
    def _get_default_char_replacements(self) -> Dict[str, str]:
        """Get default safe character replacements"""
        return {
            # Unsafe filename characters
            '\\': ' ',
            '/': ' ',
            ':': ' ',
            '*': '',
            '?': '',
            '"': '',
            '<': '',
            '>': '',
            '|': ' ',
            
            # Special characters with meaningful replacements
            '!': '',
            '@': ' at ',
            '#': ' hash ',
            '$': ' dollar ',
            '%': ' percent ',
            '^': '',
            '&': ' and ',
            '(': '',
            ')': '',
            '[': '',
            ']': '',
            '{': '',
            '}': '',
            '`': '',
            '~': '',
            '+': ' plus ',
            '=': ' equals ',
            ';': '',
            ',': '',
            
            # Multiple consecutive dots
            '..': '.',
            '...': '.',
        }
    
    def merge_custom_replacements(self):
        """Merge custom replacements with safe replacements"""
        if self.custom_replacements:
            # Custom replacements take precedence
            merged = self.safe_char_replacements.copy()
            merged.update(self.custom_replacements)
            return merged
        return self.safe_char_replacements
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate normalization rules configuration
        
        Returns:
            Validation results with errors and warnings
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if at least one normalization rule is enabled
        normalization_enabled = any([
            self.remove_diacritics,
            self.lowercase_conversion,
            self.clean_special_chars,
            self.normalize_whitespace
        ])
        
        if not normalization_enabled:
            validation['warnings'].append("No normalization rules enabled")
        
        # Validate filename length constraints
        if self.max_filename_length < self.min_filename_length:
            validation['errors'].append("Max filename length must be >= min filename length")
            validation['valid'] = False
        
        if self.max_filename_length > 260:  # Windows path limit
            validation['warnings'].append("Max filename length exceeds Windows limit (260)")
        
        if self.min_filename_length < 1:
            validation['errors'].append("Min filename length must be at least 1")
            validation['valid'] = False
        
        # Validate character replacements
        all_replacements = self.merge_custom_replacements()
        for char, replacement in all_replacements.items():
            if not isinstance(char, str) or not isinstance(replacement, str):
                validation['errors'].append(f"Invalid character mapping: {char} -> {replacement}")
                validation['valid'] = False
        
        return validation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'remove_diacritics': self.remove_diacritics,
            'lowercase_conversion': self.lowercase_conversion,
            'clean_special_chars': self.clean_special_chars,
            'normalize_whitespace': self.normalize_whitespace,
            'preserve_extensions': self.preserve_extensions,
            'preserve_case_for_extensions': self.preserve_case_for_extensions,
            'preserve_numbers': self.preserve_numbers,
            'preserve_english_words': self.preserve_english_words,
            'validation_level': self.validation_level.value,
            'create_backup': self.create_backup,
            'confirm_overwrite': self.confirm_overwrite,
            'skip_readonly_files': self.skip_readonly_files,
            'skip_hidden_files': self.skip_hidden_files,
            'safe_char_replacements': self.safe_char_replacements,
            'custom_replacements': self.custom_replacements,
            'max_filename_length': self.max_filename_length,
            'min_filename_length': self.min_filename_length,
            'rule_name': self.rule_name,
            'rule_description': self.rule_description,
            'created_at': self.created_at.isoformat(),
            'created_by': self.created_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NormalizationRules':
        """Create from dictionary"""
        # Convert validation level string back to enum
        if 'validation_level' in data:
            data['validation_level'] = ValidationLevel(data['validation_level'])
        
        # Convert datetime string back to datetime
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        
        return cls(**data)


@dataclass
class BatchOperation:
    """
    Configuration and metadata for batch file operations
    """
    operation_type: OperationType
    normalization_rules: NormalizationRules
    
    # Target configuration
    source_directory: str = ""
    target_directory: Optional[str] = None  # None means in-place rename
    file_patterns: List[str] = field(default_factory=lambda: ["*"])
    
    # Processing options
    recursive: bool = False
    include_folders: bool = False
    dry_run: bool = True
    
    # Progress tracking
    total_files: int = 0
    processed_files: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0
    
    # Operation metadata
    operation_id: str = ""
    operation_name: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results and logging
    operation_log: List[str] = field(default_factory=list)
    error_log: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize computed fields"""
        if not self.operation_id:
            self.operation_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(self)}"
        
        if not self.operation_name:
            self.operation_name = f"{self.operation_type.value.title()} Operation"
    
    def start_operation(self):
        """Mark operation as started"""
        self.started_at = datetime.now()
        self.log_message(f"Started {self.operation_name}")
    
    def complete_operation(self):
        """Mark operation as completed"""
        self.completed_at = datetime.now()
        duration = self.get_duration()
        self.log_message(f"Completed {self.operation_name} in {duration:.2f} seconds")
    
    def log_message(self, message: str):
        """Add message to operation log"""
        timestamp = datetime.now().isoformat()
        self.operation_log.append(f"[{timestamp}] {message}")
    
    def log_error(self, error: str):
        """Add error to error log"""
        timestamp = datetime.now().isoformat()
        self.error_log.append(f"[{timestamp}] ERROR: {error}")
    
    def increment_progress(self, success: bool = True, skipped: bool = False):
        """Update progress counters"""
        self.processed_files += 1
        
        if skipped:
            self.skipped_operations += 1
        elif success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
    
    def get_progress_percentage(self) -> float:
        """Get operation progress as percentage"""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100.0
    
    def get_duration(self) -> float:
        """Get operation duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.now() - self.started_at).total_seconds()
        return 0.0
    
    def is_completed(self) -> bool:
        """Check if operation is completed"""
        return self.completed_at is not None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get operation summary"""
        return {
            'operation_id': self.operation_id,
            'operation_name': self.operation_name,
            'operation_type': self.operation_type.value,
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'successful_operations': self.successful_operations,
            'failed_operations': self.failed_operations,
            'skipped_operations': self.skipped_operations,
            'progress_percentage': self.get_progress_percentage(),
            'duration': self.get_duration(),
            'is_completed': self.is_completed(),
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        summary = self.get_summary()
        summary.update({
            'normalization_rules': self.normalization_rules.to_dict(),
            'source_directory': self.source_directory,
            'target_directory': self.target_directory,
            'file_patterns': self.file_patterns,
            'recursive': self.recursive,
            'include_folders': self.include_folders,
            'dry_run': self.dry_run,
            'operation_log': self.operation_log,
            'error_log': self.error_log
        })
        return summary