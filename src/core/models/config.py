"""
Configuration Data Models

Defines data structures for application configuration including
user preferences, normalization rules, UI settings, and recent folders.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from pathlib import Path


@dataclass
class NormalizationRulesConfig:
    """Configuration for Vietnamese text normalization rules"""
    remove_diacritics: bool = True
    convert_to_lowercase: bool = True
    clean_special_characters: bool = True
    normalize_whitespace: bool = True
    preserve_extensions: bool = True
    preserve_case_for_extensions: bool = True
    preserve_numbers: bool = True
    preserve_english_words: bool = True
    
    # Processing limits
    max_filename_length: int = 255
    min_filename_length: int = 1
    
    # Custom replacement rules
    custom_replacements: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'remove_diacritics': self.remove_diacritics,
            'convert_to_lowercase': self.convert_to_lowercase,
            'clean_special_characters': self.clean_special_characters,
            'normalize_whitespace': self.normalize_whitespace,
            'preserve_extensions': self.preserve_extensions,
            'preserve_case_for_extensions': self.preserve_case_for_extensions,
            'preserve_numbers': self.preserve_numbers,
            'preserve_english_words': self.preserve_english_words,
            'max_filename_length': self.max_filename_length,
            'min_filename_length': self.min_filename_length,
            'custom_replacements': self.custom_replacements
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NormalizationRulesConfig':
        """Create from dictionary"""
        return cls(**data)
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate configuration rules
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Check filename length constraints
        if self.max_filename_length < self.min_filename_length:
            errors.append("Max filename length must be >= min filename length")
        
        if self.max_filename_length > 260:
            warnings.append("Max filename length exceeds Windows limit (260)")
        
        if self.min_filename_length < 1:
            errors.append("Min filename length must be at least 1")
        
        # Check if at least one normalization rule is enabled
        normalization_enabled = any([
            self.remove_diacritics,
            self.convert_to_lowercase,
            self.clean_special_characters,
            self.normalize_whitespace
        ])
        
        if not normalization_enabled:
            warnings.append("No normalization rules enabled")
        
        # Validate custom replacements
        for char, replacement in self.custom_replacements.items():
            if not isinstance(char, str) or not isinstance(replacement, str):
                errors.append(f"Invalid character mapping: {char} -> {replacement}")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings


@dataclass
class UIPreferences:
    """UI preferences and window state configuration"""
    window_width: int = 600
    window_height: int = 500
    window_x: Optional[int] = None
    window_y: Optional[int] = None
    window_maximized: bool = False
    
    # Theme and appearance
    theme: str = "default"  # "default", "dark", "light"
    font_size: int = 10
    font_family: str = "Arial"
    
    # Recent folders settings
    max_recent_folders: int = 10
    recent_folders_in_menu: bool = True
    
    # Dialog preferences
    confirm_operations: bool = True
    confirm_reset: bool = True
    show_preview_dialog: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'window_width': self.window_width,
            'window_height': self.window_height,
            'window_x': self.window_x,
            'window_y': self.window_y,
            'window_maximized': self.window_maximized,
            'theme': self.theme,
            'font_size': self.font_size,
            'font_family': self.font_family,
            'max_recent_folders': self.max_recent_folders,
            'recent_folders_in_menu': self.recent_folders_in_menu,
            'confirm_operations': self.confirm_operations,
            'confirm_reset': self.confirm_reset,
            'show_preview_dialog': self.show_preview_dialog
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UIPreferences':
        """Create from dictionary"""
        return cls(**data)
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate UI preferences
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Validate window dimensions
        if self.window_width < 400:
            errors.append("Window width must be at least 400 pixels")
        if self.window_height < 300:
            errors.append("Window height must be at least 300 pixels")
        
        # Validate font size
        if self.font_size < 8:
            errors.append("Font size must be at least 8")
        if self.font_size > 32:
            warnings.append("Large font size may cause display issues")
        
        # Validate recent folders limit
        if self.max_recent_folders < 1:
            errors.append("Max recent folders must be at least 1")
        if self.max_recent_folders > 50:
            warnings.append("Large number of recent folders may impact performance")
        
        # Validate theme
        valid_themes = ["default", "dark", "light"]
        if self.theme not in valid_themes:
            warnings.append(f"Unknown theme '{self.theme}', will use 'default'")
            self.theme = "default"
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings


@dataclass
class OperationSettings:
    """Settings for file operation behavior"""
    dry_run_by_default: bool = True
    create_backups: bool = True
    backup_location: str = "same_folder"  # "same_folder", "backup_folder", "temp"
    max_concurrent_operations: int = 1
    
    # Safety settings
    skip_hidden_files: bool = True
    skip_system_files: bool = True
    require_confirmation_for_large_operations: bool = True
    large_operation_threshold: int = 100
    
    # Performance settings
    progress_update_interval: float = 0.5  # seconds
    file_scan_chunk_size: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'dry_run_by_default': self.dry_run_by_default,
            'create_backups': self.create_backups,
            'backup_location': self.backup_location,
            'max_concurrent_operations': self.max_concurrent_operations,
            'skip_hidden_files': self.skip_hidden_files,
            'skip_system_files': self.skip_system_files,
            'require_confirmation_for_large_operations': self.require_confirmation_for_large_operations,
            'large_operation_threshold': self.large_operation_threshold,
            'progress_update_interval': self.progress_update_interval,
            'file_scan_chunk_size': self.file_scan_chunk_size
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OperationSettings':
        """Create from dictionary"""
        return cls(**data)
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate operation settings
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Validate concurrent operations
        if self.max_concurrent_operations < 1:
            errors.append("Max concurrent operations must be at least 1")
        if self.max_concurrent_operations > 10:
            warnings.append("High concurrency may cause system instability")
        
        # Validate backup location
        valid_backup_locations = ["same_folder", "backup_folder", "temp"]
        if self.backup_location not in valid_backup_locations:
            errors.append(f"Invalid backup location: {self.backup_location}")
        
        # Validate thresholds
        if self.large_operation_threshold < 1:
            errors.append("Large operation threshold must be at least 1")
        
        # Validate performance settings
        if self.progress_update_interval < 0.1:
            warnings.append("Very frequent progress updates may impact performance")
        if self.progress_update_interval > 5.0:
            warnings.append("Slow progress updates may appear unresponsive")
        
        if self.file_scan_chunk_size < 100:
            warnings.append("Small chunk size may impact scanning performance")
        if self.file_scan_chunk_size > 10000:
            warnings.append("Large chunk size may cause memory issues")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings


@dataclass
class RecentFolder:
    """Recent folder entry với timestamp and usage tracking"""
    path: str
    last_accessed: datetime
    access_count: int = 1
    display_name: Optional[str] = None
    
    def __post_init__(self):
        if self.display_name is None:
            self.display_name = os.path.basename(self.path) or self.path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'path': self.path,
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
            'display_name': self.display_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecentFolder':
        """Create from dictionary"""
        last_accessed = datetime.fromisoformat(data['last_accessed'])
        return cls(
            path=data['path'],
            last_accessed=last_accessed,
            access_count=data.get('access_count', 1),
            display_name=data.get('display_name')
        )


@dataclass
class AppConfiguration:
    """Complete application configuration"""
    normalization_rules: NormalizationRulesConfig = field(default_factory=NormalizationRulesConfig)
    ui_preferences: UIPreferences = field(default_factory=UIPreferences)
    operation_settings: OperationSettings = field(default_factory=OperationSettings)
    recent_folders: List[RecentFolder] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0"
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'normalization_rules': self.normalization_rules.to_dict(),
            'ui_preferences': self.ui_preferences.to_dict(),
            'operation_settings': self.operation_settings.to_dict(),
            'recent_folders': [folder.to_dict() for folder in self.recent_folders],
            'version': self.version,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AppConfiguration':
        """Create from dictionary"""
        return cls(
            normalization_rules=NormalizationRulesConfig.from_dict(
                data.get('normalization_rules', {})
            ),
            ui_preferences=UIPreferences.from_dict(
                data.get('ui_preferences', {})
            ),
            operation_settings=OperationSettings.from_dict(
                data.get('operation_settings', {})
            ),
            recent_folders=[
                RecentFolder.from_dict(folder_data) 
                for folder_data in data.get('recent_folders', [])
            ],
            version=data.get('version', '1.0'),
            created_at=datetime.fromisoformat(data.get('created_at', datetime.now().isoformat())),
            last_updated=datetime.fromisoformat(data.get('last_updated', datetime.now().isoformat()))
        )
    
    def validate(self) -> Tuple[bool, List[str], List[str]]:
        """
        Validate complete configuration
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        all_errors = []
        all_warnings = []
        overall_valid = True
        
        # Validate normalization rules
        valid, errors, warnings = self.normalization_rules.validate()
        overall_valid &= valid
        all_errors.extend([f"Normalization Rules: {err}" for err in errors])
        all_warnings.extend([f"Normalization Rules: {warn}" for warn in warnings])
        
        # Validate UI preferences
        valid, errors, warnings = self.ui_preferences.validate()
        overall_valid &= valid
        all_errors.extend([f"UI Preferences: {err}" for err in errors])
        all_warnings.extend([f"UI Preferences: {warn}" for warn in warnings])
        
        # Validate operation settings
        valid, errors, warnings = self.operation_settings.validate()
        overall_valid &= valid
        all_errors.extend([f"Operation Settings: {err}" for err in errors])
        all_warnings.extend([f"Operation Settings: {warn}" for warn in warnings])
        
        # Validate recent folders
        for i, folder in enumerate(self.recent_folders):
            if not os.path.exists(folder.path):
                all_warnings.append(f"Recent folder {i+1} no longer exists: {folder.path}")
        
        # Check for duplicate recent folders
        paths = [folder.path for folder in self.recent_folders]
        if len(paths) != len(set(paths)):
            all_warnings.append("Duplicate entries found in recent folders")
        
        return overall_valid, all_errors, all_warnings
    
    def add_recent_folder(self, folder_path: str) -> None:
        """Add folder to recent folders list với deduplication và limit management"""
        folder_path = os.path.abspath(folder_path)
        
        # Remove existing entry if present
        self.recent_folders = [f for f in self.recent_folders if f.path != folder_path]
        
        # Add to beginning
        new_folder = RecentFolder(
            path=folder_path,
            last_accessed=datetime.now()
        )
        self.recent_folders.insert(0, new_folder)
        
        # Trim to max limit
        max_folders = self.ui_preferences.max_recent_folders
        if len(self.recent_folders) > max_folders:
            self.recent_folders = self.recent_folders[:max_folders]
        
        # Update last modified
        self.last_updated = datetime.now()
    
    def get_recent_folders_list(self) -> List[str]:
        """Get list of recent folder paths sorted by last accessed"""
        return [folder.path for folder in self.recent_folders]
    
    def clean_recent_folders(self) -> int:
        """Remove non-existent folders từ recent list"""
        initial_count = len(self.recent_folders)
        self.recent_folders = [
            folder for folder in self.recent_folders
            if os.path.exists(folder.path)
        ]
        removed_count = initial_count - len(self.recent_folders)
        
        if removed_count > 0:
            self.last_updated = datetime.now()
        
        return removed_count
    
    def reset_to_defaults(self) -> None:
        """Reset all configuration to default values"""
        self.normalization_rules = NormalizationRulesConfig()
        self.ui_preferences = UIPreferences()
        self.operation_settings = OperationSettings()
        self.recent_folders = []
        self.last_updated = datetime.now()
    
    def to_json(self) -> str:
        """Export configuration as JSON string"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AppConfiguration':
        """Import configuration from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


def get_default_config_path() -> Path:
    """Get default configuration file path based on platform"""
    if os.name == 'nt':  # Windows
        app_data = os.environ.get('APPDATA')
        if app_data:
            config_dir = Path(app_data) / "FileRenameTool"
        else:
            config_dir = Path.home() / "AppData" / "Roaming" / "FileRenameTool"
    else:  # Unix-like systems
        config_dir = Path.home() / ".config" / "filerenametool"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.db"


# Example usage and testing
if __name__ == "__main__":
    def test_configuration_models():
        """Test configuration data models"""
        
        # Test default configuration
        config = AppConfiguration()
        is_valid, errors, warnings = config.validate()
        print(f"Default config valid: {is_valid}")
        print(f"Errors: {errors}")
        print(f"Warnings: {warnings}")
        
        # Test adding recent folders
        config.add_recent_folder("/test/folder1")
        config.add_recent_folder("/test/folder2")
        config.add_recent_folder("/test/folder1")  # Should deduplicate
        
        print(f"Recent folders: {config.get_recent_folders_list()}")
        
        # Test serialization
        json_str = config.to_json()
        print(f"JSON length: {len(json_str)}")
        
        # Test deserialization
        config2 = AppConfiguration.from_json(json_str)
        assert config.version == config2.version
        assert len(config.recent_folders) == len(config2.recent_folders)
        
        print("Configuration models test completed successfully")
    
    test_configuration_models()