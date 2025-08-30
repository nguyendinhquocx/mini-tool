# Backend Architecture

## Service Architecture

### Traditional Server Architecture

#### Controller/Route Organization
```
src/
├── core/
│   ├── application.py          # Main application controller
│   ├── services/
│   │   ├── file_service.py     # File operations business logic
│   │   ├── config_service.py   # Configuration management
│   │   ├── history_service.py  # Operation history tracking
│   │   └── normalize_service.py # Vietnamese text processing
│   ├── repositories/
│   │   ├── config_repository.py # Configuration persistence
│   │   ├── history_repository.py # History data access
│   │   └── file_repository.py   # File system abstractions
│   ├── models/
│   │   ├── file_info.py        # File metadata models
│   │   ├── operation.py        # Operation tracking models
│   │   └── config.py           # Configuration models
│   └── utils/
│       ├── error_handler.py    # Error management utilities
│       ├── logger.py           # Logging infrastructure
│       └── validators.py       # Input validation helpers
```

#### Controller Template
```python
from typing import List, Optional
from dataclasses import dataclass
from core.services.file_service import FileService
from core.services.config_service import ConfigService
from core.models.operation import RenameOperation, OperationResult

class ApplicationController:
    def __init__(self):
        self.file_service = FileService()
        self.config_service = ConfigService()
        self.current_operation: Optional[str] = None
    
    async def scan_folder(self, folder_path: str) -> List[FileInfo]:
        """Scan folder và return file information"""
        try:
            self.config_service.add_recent_folder(folder_path)
            return await self.file_service.scan_directory(folder_path)
        except Exception as e:
            self._handle_error("FOLDER_SCAN_ERROR", e)
            raise
    
    async def preview_rename_operations(
        self, 
        files: List[FileInfo], 
        rules: NormalizationRules
    ) -> List[RenamePreview]:
        """Generate preview của rename operations"""
        try:
            return await self.file_service.generate_preview(files, rules)
        except Exception as e:
            self._handle_error("PREVIEW_GENERATION_ERROR", e)
            raise
    
    async def execute_rename_batch(
        self, 
        operations: List[RenameOperation],
        progress_callback: Callable[[float, str], None]
    ) -> OperationResult:
        """Execute batch rename với progress updates"""
        operation_id = self.file_service.create_operation_id()
        self.current_operation = operation_id
        
        try:
            result = await self.file_service.execute_batch_rename(
                operations, 
                progress_callback
            )
            await self.config_service.save_operation_history(operation_id, result)
            return result
        except Exception as e:
            await self._handle_operation_error(operation_id, e)
            raise
        finally:
            self.current_operation = None
```

## Database Architecture

### Schema Design
```sql
-- Enhanced schema với performance optimizations
CREATE TABLE app_config (
    id INTEGER PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    data_type TEXT NOT NULL CHECK (data_type IN ('string', 'json', 'boolean', 'integer')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TRIGGER update_app_config_timestamp 
AFTER UPDATE ON app_config
BEGIN
    UPDATE app_config SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

### Data Access Layer
```python
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any
import sqlite3
import json
from core.models.config import AppConfiguration

class ConfigRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._initialize_database()
    
    @asynccontextmanager
    async def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    async def load_configuration(self) -> AppConfiguration:
        """Load complete application configuration"""
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value, data_type FROM app_config")
            
            config_data = {}
            for row in cursor.fetchall():
                key, value, data_type = row
                if data_type == 'json':
                    config_data[key] = json.loads(value)
                elif data_type == 'boolean':
                    config_data[key] = value.lower() == 'true'
                elif data_type == 'integer':
                    config_data[key] = int(value)
                else:
                    config_data[key] = value
            
            return AppConfiguration(**config_data)
    
    async def save_configuration(self, config: AppConfiguration) -> None:
        """Persist configuration changes"""
        async with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for key, value in config.__dict__.items():
                if isinstance(value, (dict, list)):
                    data_type, serialized = 'json', json.dumps(value)
                elif isinstance(value, bool):
                    data_type, serialized = 'boolean', str(value)
                elif isinstance(value, int):
                    data_type, serialized = 'integer', str(value)
                else:
                    data_type, serialized = 'string', str(value)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO app_config (key, value, data_type)
                    VALUES (?, ?, ?)
                """, (key, serialized, data_type))
            
            conn.commit()
```
