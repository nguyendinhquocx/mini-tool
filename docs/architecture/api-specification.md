# API Specification

**Note**: Desktop application does not expose external APIs. This section covers internal component interfaces.

## Internal Component APIs

### File Operations Interface
```python
class FileOperationsEngine:
    def scan_folder(self, folder_path: str) -> List[FileInfo]
    def preview_rename(self, files: List[FileInfo], rules: NormalizationRules) -> List[RenamePreview]
    def execute_rename(self, operations: List[RenameOperation]) -> OperationResult
    def undo_operation(self, operation_id: str) -> UndoResult
```

### Configuration Manager Interface
```python
class ConfigurationManager:
    def load_settings(self) -> AppConfiguration
    def save_settings(self, config: AppConfiguration) -> bool
    def get_recent_folders(self) -> List[str]
    def add_recent_folder(self, folder_path: str) -> None
```

### Vietnamese Normalizer Interface
```python
class VietnameseNormalizer:
    def normalize_text(self, text: str) -> str
    def remove_diacritics(self, text: str) -> str
    def clean_special_chars(self, text: str) -> str
    def apply_case_rules(self, text: str) -> str
```
