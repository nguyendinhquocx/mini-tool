# Coding Standards

## Critical Fullstack Rules

- **Error Handling Consistency**: All file operations must use the centralized ErrorHandler với standardized error codes và recovery options
- **Configuration Management**: Access settings only through ConfigService, never direct file/registry access
- **UI State Synchronization**: All UI updates must go through StateManager để maintain consistency across components
- **File Operation Safety**: Always create backup/undo information before destructive operations, validate paths before processing
- **Threading Discipline**: Long-running operations must execute on background threads với proper progress callbacks
- **Resource Management**: Always use context managers cho file operations, database connections, và UI resources
- **Logging Standards**: Use structured logging với operation IDs, include enough context for debugging
- **Input Validation**: Validate all user inputs at service layer boundaries, sanitize file paths và names

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `FileOperationsService`, `ConfigurationManager` |
| Functions/Methods | snake_case | `scan_directory()`, `execute_rename_operation()` |
| Variables | snake_case | `selected_folder`, `operation_result` |
| Constants | UPPER_SNAKE_CASE | `MAX_FILE_NAME_LENGTH`, `DEFAULT_TIMEOUT` |
| Files | snake_case.py | `file_service.py`, `main_window.py` |
| UI Components | PascalCase | `FilePreviewComponent`, `ProgressDialog` |
