# Components

## UI Controller Component
**Responsibility**: Coordinate between user interface và business logic, handle user interactions và application state

**Key Interfaces**:
- `handle_folder_selection()` - Process folder browse events
- `update_preview_display()` - Refresh file preview list
- `execute_rename_operation()` - Trigger batch rename với progress feedback

**Dependencies**: FileOperationsEngine, ConfigurationManager, ErrorHandler

**Technology Stack**: Python Tkinter với custom event handling patterns

## File Operations Engine
**Responsibility**: Core business logic cho file scanning, preview generation, và batch rename execution

**Key Interfaces**:
- `scan_folder_contents()` - Analyze folder và extract file information
- `generate_rename_preview()` - Create before/after preview với Vietnamese normalization
- `execute_batch_rename()` - Perform actual file system operations với error handling

**Dependencies**: VietnameseNormalizer, FileSystemAPIs, ErrorHandler

**Technology Stack**: Python os/pathlib libraries với custom file operation wrappers

## Configuration Manager
**Responsibility**: Persistent storage và retrieval của user preferences, application settings

**Key Interfaces**:
- `load_user_preferences()` - Initialize application với saved settings
- `save_configuration_changes()` - Persist user modifications to disk
- `manage_recent_folders()` - Track và provide quick access to frequently used locations

**Dependencies**: SQLite database, FileSystem access

**Technology Stack**: Python ConfigParser với SQLite backend cho structured data

## Vietnamese Text Processor
**Responsibility**: Specialized text normalization cho Vietnamese language files

**Key Interfaces**:
- `normalize_vietnamese_text()` - Apply diacritic removal và standardization rules
- `clean_file_name()` - Remove unsafe characters từ file names
- `apply_custom_rules()` - Process user-defined text transformation patterns

**Dependencies**: Unidecode library, custom Vietnamese character mappings

**Technology Stack**: Python string processing với Unicode normalization libraries
