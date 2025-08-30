# Database Schema

## SQLite Schema Design

```sql
-- Application Configuration
CREATE TABLE app_config (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    data_type TEXT NOT NULL, -- 'string', 'json', 'boolean', 'integer'
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Operation History
CREATE TABLE operation_history (
    operation_id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    folder_path TEXT NOT NULL,
    operation_type TEXT NOT NULL, -- 'batch_rename', 'undo'
    total_files INTEGER NOT NULL,
    successful_files INTEGER NOT NULL,
    failed_files INTEGER NOT NULL,
    status TEXT NOT NULL, -- 'success', 'partial', 'failed'
    error_summary TEXT
);

-- Individual File Operations
CREATE TABLE file_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_id TEXT NOT NULL,
    original_name TEXT NOT NULL,
    new_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    status TEXT NOT NULL, -- 'success', 'failed', 'skipped'
    error_message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operation_id) REFERENCES operation_history(operation_id)
);

-- Recent Folders
CREATE TABLE recent_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_path TEXT UNIQUE NOT NULL,
    last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 1
);

-- Create indexes for performance
CREATE INDEX idx_operation_history_timestamp ON operation_history(timestamp);
CREATE INDEX idx_file_operations_operation_id ON file_operations(operation_id);
CREATE INDEX idx_recent_folders_last_accessed ON recent_folders(last_accessed);
```
