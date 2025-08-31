"""
Database Service

SQLite-based database service for persistent storage of operation history,
settings, and other application data.
"""

import sqlite3
import os
import threading
from typing import Optional, Dict, Any, List, Tuple
from contextlib import contextmanager
from datetime import datetime
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)


class DatabaseService:
    """
    SQLite database service with connection pooling and thread safety
    
    Features:
    - Thread-safe database operations
    - Automatic schema creation and migrations
    - Connection pooling
    - Transaction support
    - JSON data type support
    """
    
    # Database schema version for migrations
    SCHEMA_VERSION = 2
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Default to app data directory
            app_data_dir = os.path.expanduser("~/.file_rename_tool")
            os.makedirs(app_data_dir, exist_ok=True)
            db_path = os.path.join(app_data_dir, "operations.db")
            
        self.db_path = db_path
        self._local_storage = threading.local()
        self._lock = threading.Lock()
        
        # Initialize database
        self._initialize_database()
        
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local_storage, 'connection'):
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=30.0
            )
            conn.row_factory = sqlite3.Row  # Enable column name access
            conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
            conn.execute("PRAGMA journal_mode = WAL")  # Enable WAL mode for better concurrency
            self._local_storage.connection = conn
            
        return self._local_storage.connection
        
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with automatic cleanup"""
        conn = self._get_connection()
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            # Connection is kept alive for thread reuse
            pass
            
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
                
    def _initialize_database(self):
        """Initialize database schema and run migrations"""
        with self.transaction() as conn:
            # Create metadata table for schema versioning
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check current schema version
            cursor = conn.execute(
                "SELECT value FROM schema_metadata WHERE key = 'version'"
            )
            row = cursor.fetchone()
            current_version = int(row['value']) if row else 0
            
            # Run migrations if needed
            if current_version < self.SCHEMA_VERSION:
                self._run_migrations(conn, current_version)
                
    def _run_migrations(self, conn: sqlite3.Connection, from_version: int):
        """Run database schema migrations"""
        logger.info(f"Running database migrations from version {from_version} to {self.SCHEMA_VERSION}")
        
        if from_version < 1:
            # Initial schema creation
            self._create_initial_schema(conn)
            
        if from_version < 2:
            # Add undo functionality enhancements
            self._migrate_to_version_2(conn)
            
        # Update schema version
        conn.execute(
            '''INSERT OR REPLACE INTO schema_metadata (key, value, updated_at) 
               VALUES ('version', ?, CURRENT_TIMESTAMP)''',
            (str(self.SCHEMA_VERSION),)
        )
        
        logger.info(f"Database migrations completed to version {self.SCHEMA_VERSION}")
        
    def _create_initial_schema(self, conn: sqlite3.Connection):
        """Create initial database schema"""
        
        # Operation history table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS operation_history (
                operation_id TEXT PRIMARY KEY,
                operation_name TEXT NOT NULL,
                operation_type TEXT NOT NULL,
                source_directory TEXT NOT NULL,
                target_directory TEXT,
                total_files INTEGER NOT NULL DEFAULT 0,
                successful_files INTEGER NOT NULL DEFAULT 0,
                failed_files INTEGER NOT NULL DEFAULT 0,
                skipped_files INTEGER NOT NULL DEFAULT 0,
                dry_run BOOLEAN NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                normalization_rules TEXT,  -- JSON
                operation_log TEXT,        -- JSON array
                error_log TEXT,           -- JSON array
                error_summary TEXT
            )
        ''')
        
        # File operations table (detailed per-file results)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS file_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                original_name TEXT NOT NULL,
                new_name TEXT NOT NULL,
                operation_status TEXT NOT NULL,
                error_message TEXT,
                processing_steps TEXT,    -- JSON array
                backup_path TEXT,
                backup_created BOOLEAN DEFAULT 0,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                FOREIGN KEY (operation_id) REFERENCES operation_history(operation_id) ON DELETE CASCADE
            )
        ''')
        
        # Application settings table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for better performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_operation_history_created_at ON operation_history(created_at)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_operation_history_status ON operation_history(status)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_file_operations_operation_id ON file_operations(operation_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_file_operations_status ON file_operations(operation_status)')
        
    def execute_query(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """Execute a SELECT query and return cursor"""
        with self.get_connection() as conn:
            return conn.execute(query, params)
            
    def execute_update(self, query: str, params: Tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount
            
    def execute_many(self, query: str, params_list: List[Tuple]) -> int:
        """Execute query with multiple parameter sets"""
        with self.transaction() as conn:
            cursor = conn.executemany(query, params_list)
            return cursor.rowcount
            
    def fetch_one(self, query: str, params: Tuple = ()) -> Optional[sqlite3.Row]:
        """Execute query and fetch one row"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchone()
            
    def fetch_all(self, query: str, params: Tuple = ()) -> List[sqlite3.Row]:
        """Execute query and fetch all rows"""
        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()
            
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting with type conversion"""
        row = self.fetch_one(
            "SELECT value, value_type FROM app_settings WHERE key = ?",
            (key,)
        )
        
        if not row:
            return default
            
        value, value_type = row['value'], row['value_type']
        
        # Convert value based on type
        if value_type == 'json':
            return json.loads(value)
        elif value_type == 'int':
            return int(value)
        elif value_type == 'float':
            return float(value)
        elif value_type == 'bool':
            return value.lower() in ('true', '1', 'yes', 'on')
        else:
            return value
            
    def set_setting(self, key: str, value: Any, description: Optional[str] = None):
        """Set application setting with automatic type detection"""
        # Determine value type and serialize
        if isinstance(value, (dict, list)):
            value_str = json.dumps(value)
            value_type = 'json'
        elif isinstance(value, bool):
            value_str = str(value).lower()
            value_type = 'bool'
        elif isinstance(value, int):
            value_str = str(value)
            value_type = 'int'
        elif isinstance(value, float):
            value_str = str(value)
            value_type = 'float'
        else:
            value_str = str(value)
            value_type = 'string'
            
        self.execute_update(
            '''INSERT OR REPLACE INTO app_settings (key, value, value_type, description, updated_at)
               VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
            (key, value_str, value_type, description)
        )
        
    def vacuum(self):
        """Optimize database by running VACUUM"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
            
    def close_all_connections(self):
        """Close all thread-local connections"""
        # This is called during application shutdown
        if hasattr(self._local_storage, 'connection'):
            try:
                self._local_storage.connection.close()
                delattr(self._local_storage, 'connection')
            except Exception as e:
                logger.error(f"Error closing database connection: {e}")
                
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics"""
        with self.get_connection() as conn:
            # Get database file size
            try:
                db_size = os.path.getsize(self.db_path)
            except OSError:
                db_size = 0
                
            # Get table information
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            
            info = {
                'database_path': self.db_path,
                'database_size_bytes': db_size,
                'schema_version': self.SCHEMA_VERSION,
                'tables': [row['name'] for row in tables]
            }
            
            # Get record counts for main tables
            for table in ['operation_history', 'file_operations', 'app_settings']:
                if table in info['tables']:
                    count = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()
                    info[f'{table}_count'] = count['count'] if count else 0
                    
            return info
    
    def _migrate_to_version_2(self, conn: sqlite3.Connection):
        """Migrate database to version 2 - Add undo functionality support"""
        logger.info("Migrating database to version 2: Adding undo functionality")
        
        # Add undo-specific columns to operation_history table
        try:
            conn.execute('ALTER TABLE operation_history ADD COLUMN can_be_undone BOOLEAN DEFAULT 1')
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        try:
            conn.execute('ALTER TABLE operation_history ADD COLUMN undo_expiry_time TIMESTAMP')
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        try:
            conn.execute('ALTER TABLE operation_history ADD COLUMN undo_operation_id TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Add original modification timestamps to file_operations table
        try:
            conn.execute('ALTER TABLE file_operations ADD COLUMN original_modified_time TIMESTAMP')
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        try:
            conn.execute('ALTER TABLE file_operations ADD COLUMN file_size_bytes INTEGER')
        except sqlite3.OperationalError:
            # Column already exists
            pass
            
        try:
            conn.execute('ALTER TABLE file_operations ADD COLUMN file_checksum TEXT')
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Create undo_operations table for detailed undo tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS undo_operations (
                undo_operation_id TEXT PRIMARY KEY,
                original_operation_id TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                total_files INTEGER NOT NULL DEFAULT 0,
                successful_restorations INTEGER NOT NULL DEFAULT 0,
                failed_restorations INTEGER NOT NULL DEFAULT 0,
                skipped_files INTEGER NOT NULL DEFAULT 0,
                execution_status TEXT NOT NULL DEFAULT 'not_started',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                duration_seconds REAL,
                was_cancelled BOOLEAN DEFAULT 0,
                cancellation_reason TEXT,
                error_message TEXT,
                file_mappings TEXT,  -- JSON
                validation_results TEXT,  -- JSON
                restored_files TEXT,  -- JSON array
                failed_files TEXT,   -- JSON array
                FOREIGN KEY (original_operation_id) REFERENCES operation_history(operation_id) ON DELETE CASCADE
            )
        ''')
        
        # Create file_validation_cache for external modification detection
        conn.execute('''
            CREATE TABLE IF NOT EXISTS file_validation_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                current_name TEXT NOT NULL,
                original_name TEXT NOT NULL,
                original_modified_time TIMESTAMP NOT NULL,
                last_validated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validation_status TEXT NOT NULL DEFAULT 'valid',
                validation_error TEXT,
                can_be_restored BOOLEAN DEFAULT 1,
                conflict_with_existing BOOLEAN DEFAULT 0,
                existing_file_path TEXT,
                FOREIGN KEY (operation_id) REFERENCES operation_history(operation_id) ON DELETE CASCADE
            )
        ''')
        
        # Create additional indexes for better performance
        conn.execute('CREATE INDEX IF NOT EXISTS idx_operation_history_can_undo ON operation_history(can_be_undone)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_operation_history_expiry ON operation_history(undo_expiry_time)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_undo_operations_original_id ON undo_operations(original_operation_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_file_validation_operation_id ON file_validation_cache(operation_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_file_validation_status ON file_validation_cache(validation_status)')
        
        logger.info("Database migration to version 2 completed successfully")


# Example usage and testing
if __name__ == "__main__":
    def test_database_service():
        """Test the database service"""
        import tempfile
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            
        try:
            # Initialize service
            db = DatabaseService(db_path)
            
            # Test settings
            db.set_setting('test_string', 'Hello World', 'Test string setting')
            db.set_setting('test_int', 42, 'Test integer setting')
            db.set_setting('test_bool', True, 'Test boolean setting')
            db.set_setting('test_json', {'key': 'value', 'list': [1, 2, 3]}, 'Test JSON setting')
            
            # Test retrieval
            assert db.get_setting('test_string') == 'Hello World'
            assert db.get_setting('test_int') == 42
            assert db.get_setting('test_bool') is True
            assert db.get_setting('test_json') == {'key': 'value', 'list': [1, 2, 3]}
            assert db.get_setting('nonexistent', 'default') == 'default'
            
            # Test database info
            info = db.get_database_info()
            print(f"Database info: {info}")
            
            print("Database service test completed successfully")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass
                
    test_database_service()