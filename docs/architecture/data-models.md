# Data Models

## Configuration Model

**Purpose**: Store user preferences, application settings, và normalization rules

**Key Attributes**:
- `normalization_rules`: Dict - Vietnamese text processing rules configuration
- `ui_preferences`: Dict - Window size, position, recent folders
- `operation_settings`: Dict - Default behaviors, safety settings

### TypeScript Interface
```python
@dataclass
class AppConfiguration:
    normalization_rules: Dict[str, bool]
    ui_preferences: Dict[str, Any]
    operation_settings: Dict[str, Any]
    recent_folders: List[str]
    version: str
    last_updated: datetime
```

### Relationships
- One-to-many với OperationHistory
- Referenced by UserPreferences

## Operation History Model

**Purpose**: Track file rename operations cho audit trail và undo functionality

**Key Attributes**:
- `operation_id`: str - Unique identifier cho each batch operation
- `timestamp`: datetime - When operation occurred
- `folder_path`: str - Target folder location
- `file_mappings`: List - Original và new names cho each file

### TypeScript Interface
```python
@dataclass
class OperationHistory:
    operation_id: str
    timestamp: datetime
    folder_path: str
    file_mappings: List[FileMappingRecord]
    operation_type: str
    status: str  # success, partial, failed
    error_details: Optional[str]
```

### Relationships
- Belongs to AppConfiguration
- One-to-many với FileMappingRecord

## File Processing Model

**Purpose**: Represent individual file rename operations với metadata

**Key Attributes**:
- `original_name`: str - File name before processing
- `processed_name`: str - File name after Vietnamese normalization
- `file_path`: str - Full path to file
- `operation_status`: str - Success, failed, skipped

### TypeScript Interface
```python
@dataclass
class FileProcessingRecord:
    original_name: str
    processed_name: str
    file_path: str
    file_size: int
    operation_status: str
    error_message: Optional[str]
    timestamp: datetime
```
