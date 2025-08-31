"""
Configuration Repository

Handles persistence and retrieval of application configuration using SQLite database.
Provides async/sync interface for configuration management với atomic transactions.
"""

import sqlite3
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

from ..models.config import AppConfiguration, get_default_config_path
from ..services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class ConfigRepository:
    """
    Repository for application configuration persistence
    
    Handles loading, saving, and managing application configuration data
    using SQLite database with JSON storage for complex data structures.
    """
    
    CONFIG_KEYS = {
        'normalization_rules': 'json',
        'ui_preferences': 'json',
        'operation_settings': 'json',
        'recent_folders': 'json',
        'version': 'string',
        'created_at': 'string',
        'last_updated': 'string'
    }
    
    def __init__(self, db_service: Optional[DatabaseService] = None, db_path: Optional[str] = None):
        """
        Initialize config repository
        
        Args:
            db_service: Optional database service instance
            db_path: Optional custom database path
        """
        if db_service:
            self.db_service = db_service
        else:
            # Create dedicated config database if not provided
            if db_path is None:
                db_path = str(get_default_config_path())
            self.db_service = DatabaseService(db_path)
        
        self._initialize_config_schema()
    
    def _initialize_config_schema(self):
        """Initialize configuration-specific database schema"""
        try:
            with self.db_service.transaction() as conn:
                # Create configuration table if it doesn't exist
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS app_configuration (
                        id INTEGER PRIMARY KEY,
                        config_key TEXT UNIQUE NOT NULL,
                        config_value TEXT NOT NULL,
                        value_type TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for faster lookups
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_app_config_key 
                    ON app_configuration(config_key)
                ''')
                
                # Create configuration metadata table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS config_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                logger.info("Configuration database schema initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize config schema: {e}")
            raise
    
    def load_configuration(self) -> AppConfiguration:
        """
        Load complete application configuration from database
        
        Returns:
            AppConfiguration instance, defaults if none exists
        """
        try:
            config_data = {}
            
            # Load all configuration values
            for key, value_type in self.CONFIG_KEYS.items():
                value = self._get_config_value(key, value_type)
                if value is not None:
                    config_data[key] = value
            
            if not config_data:
                # No configuration found, return defaults
                logger.info("No existing configuration found, using defaults")
                config = AppConfiguration()
                # Save default configuration
                self.save_configuration(config)
                return config
            
            # Create configuration from loaded data
            config = AppConfiguration.from_dict(config_data)
            
            # Validate loaded configuration
            is_valid, errors, warnings = config.validate()
            if not is_valid:
                logger.warning(f"Loaded configuration has errors: {errors}")
                # Could implement fallback to defaults here
            
            if warnings:
                logger.warning(f"Configuration warnings: {warnings}")
            
            logger.info("Configuration loaded successfully")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            # Return default configuration on error
            return AppConfiguration()
    
    def save_configuration(self, config: AppConfiguration) -> bool:
        """
        Save complete application configuration to database
        
        Args:
            config: Configuration to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate configuration before saving
            is_valid, errors, warnings = config.validate()
            if not is_valid:
                logger.error(f"Cannot save invalid configuration: {errors}")
                return False
            
            if warnings:
                logger.warning(f"Configuration warnings: {warnings}")
            
            # Update last modified timestamp
            config.last_updated = datetime.now()
            
            # Convert to dictionary
            config_data = config.to_dict()
            
            # Save each configuration section
            with self.db_service.transaction() as conn:
                for key, value_type in self.CONFIG_KEYS.items():
                    if key in config_data:
                        self._set_config_value(conn, key, config_data[key], value_type)
                
                # Update metadata
                conn.execute('''
                    INSERT OR REPLACE INTO config_metadata (key, value, updated_at)
                    VALUES ('last_save', ?, CURRENT_TIMESTAMP)
                ''', (datetime.now().isoformat(),))
            
            logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def reset_to_defaults(self) -> AppConfiguration:
        """
        Reset configuration to default values
        
        Returns:
            New default configuration
        """
        try:
            # Create backup of current configuration
            self._create_backup()
            
            # Clear all configuration data
            with self.db_service.transaction() as conn:
                conn.execute('DELETE FROM app_configuration')
                conn.execute('''
                    INSERT OR REPLACE INTO config_metadata (key, value, updated_at)
                    VALUES ('reset_to_defaults', ?, CURRENT_TIMESTAMP)
                ''', (datetime.now().isoformat(),))
            
            # Create and save default configuration
            default_config = AppConfiguration()
            default_config.created_at = datetime.now()
            default_config.last_updated = datetime.now()
            
            self.save_configuration(default_config)
            
            logger.info("Configuration reset to defaults")
            return default_config
            
        except Exception as e:
            logger.error(f"Failed to reset configuration: {e}")
            return AppConfiguration()
    
    def update_configuration_section(self, section_name: str, section_data: Dict[str, Any]) -> bool:
        """
        Update specific configuration section
        
        Args:
            section_name: Name of section to update (e.g., 'ui_preferences')
            section_data: Section data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if section_name not in self.CONFIG_KEYS:
                logger.error(f"Unknown configuration section: {section_name}")
                return False
            
            value_type = self.CONFIG_KEYS[section_name]
            
            with self.db_service.transaction() as conn:
                self._set_config_value(conn, section_name, section_data, value_type)
                
                # Update last modified timestamp
                self._set_config_value(conn, 'last_updated', datetime.now().isoformat(), 'string')
            
            logger.info(f"Configuration section '{section_name}' updated")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration section '{section_name}': {e}")
            return False
    
    def get_configuration_section(self, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Get specific configuration section
        
        Args:
            section_name: Name of section to retrieve
            
        Returns:
            Section data dictionary or None if not found
        """
        try:
            if section_name not in self.CONFIG_KEYS:
                logger.error(f"Unknown configuration section: {section_name}")
                return None
            
            value_type = self.CONFIG_KEYS[section_name]
            return self._get_config_value(section_name, value_type)
            
        except Exception as e:
            logger.error(f"Failed to get configuration section '{section_name}': {e}")
            return None
    
    def add_recent_folder(self, folder_path: str) -> bool:
        """
        Add folder to recent folders list
        
        Args:
            folder_path: Path to folder to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load current configuration
            config = self.load_configuration()
            
            # Add recent folder
            config.add_recent_folder(folder_path)
            
            # Save updated configuration
            return self.save_configuration(config)
            
        except Exception as e:
            logger.error(f"Failed to add recent folder '{folder_path}': {e}")
            return False
    
    def clean_recent_folders(self) -> int:
        """
        Remove non-existent folders from recent list
        
        Returns:
            Number of folders removed
        """
        try:
            config = self.load_configuration()
            removed_count = config.clean_recent_folders()
            
            if removed_count > 0:
                self.save_configuration(config)
                logger.info(f"Cleaned {removed_count} non-existent recent folders")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to clean recent folders: {e}")
            return 0
    
    def export_configuration(self) -> str:
        """
        Export configuration as JSON string
        
        Returns:
            JSON string của complete configuration
        """
        try:
            config = self.load_configuration()
            return config.to_json()
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return "{}"
    
    def import_configuration(self, json_str: str) -> bool:
        """
        Import configuration từ JSON string
        
        Args:
            json_str: JSON string containing configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup before import
            self._create_backup()
            
            # Parse and validate imported configuration
            config = AppConfiguration.from_json(json_str)
            is_valid, errors, warnings = config.validate()
            
            if not is_valid:
                logger.error(f"Invalid configuration import: {errors}")
                return False
            
            if warnings:
                logger.warning(f"Configuration import warnings: {warnings}")
            
            # Save imported configuration
            return self.save_configuration(config)
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration import: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False
    
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get configuration database information và statistics
        
        Returns:
            Information dictionary
        """
        try:
            with self.db_service.get_connection() as conn:
                # Get configuration count
                config_count = conn.execute(
                    'SELECT COUNT(*) as count FROM app_configuration'
                ).fetchone()['count']
                
                # Get last update time
                last_update = conn.execute(
                    'SELECT value FROM config_metadata WHERE key = "last_save"'
                ).fetchone()
                
                last_update_time = last_update['value'] if last_update else None
                
                # Get database info
                db_info = self.db_service.get_database_info()
                
                return {
                    'config_entries_count': config_count,
                    'last_updated': last_update_time,
                    'database_path': db_info.get('database_path'),
                    'database_size_bytes': db_info.get('database_size_bytes'),
                    'has_backups': self._has_backups()
                }
                
        except Exception as e:
            logger.error(f"Failed to get configuration info: {e}")
            return {}
    
    def _get_config_value(self, key: str, value_type: str) -> Optional[Any]:
        """Get configuration value với type conversion"""
        try:
            row = self.db_service.fetch_one(
                'SELECT config_value FROM app_configuration WHERE config_key = ?',
                (key,)
            )
            
            if not row:
                return None
            
            value = row['config_value']
            
            # Convert based on type
            if value_type == 'json':
                return json.loads(value)
            elif value_type == 'int':
                return int(value)
            elif value_type == 'float':
                return float(value)
            elif value_type == 'bool':
                return value.lower() in ('true', '1', 'yes')
            else:
                return value
                
        except Exception as e:
            logger.error(f"Failed to get config value '{key}': {e}")
            return None
    
    def _set_config_value(self, conn: sqlite3.Connection, key: str, value: Any, value_type: str):
        """Set configuration value với automatic serialization"""
        try:
            # Serialize value based on type
            if value_type == 'json':
                value_str = json.dumps(value, ensure_ascii=False)
            else:
                value_str = str(value)
            
            conn.execute('''
                INSERT OR REPLACE INTO app_configuration 
                (config_key, config_value, value_type, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, value_str, value_type))
            
        except Exception as e:
            logger.error(f"Failed to set config value '{key}': {e}")
            raise
    
    def _create_backup(self) -> bool:
        """Create backup của current configuration"""
        try:
            config_json = self.export_configuration()
            backup_name = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # Store backup in metadata table
            with self.db_service.transaction() as conn:
                conn.execute('''
                    INSERT INTO config_metadata (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (backup_name, config_json))
            
            logger.info(f"Configuration backup created: {backup_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create configuration backup: {e}")
            return False
    
    def _has_backups(self) -> bool:
        """Check if configuration backups exist"""
        try:
            row = self.db_service.fetch_one('''
                SELECT COUNT(*) as count FROM config_metadata 
                WHERE key LIKE 'config_backup_%'
            ''')
            return row['count'] > 0 if row else False
        except Exception:
            return False
    
    def list_backups(self) -> List[Dict[str, str]]:
        """
        List available configuration backups
        
        Returns:
            List của backup information dictionaries
        """
        try:
            rows = self.db_service.fetch_all('''
                SELECT key, updated_at FROM config_metadata 
                WHERE key LIKE 'config_backup_%'
                ORDER BY updated_at DESC
            ''')
            
            backups = []
            for row in rows:
                backup_name = row['key']
                timestamp = backup_name.replace('config_backup_', '').replace('.json', '')
                backups.append({
                    'name': backup_name,
                    'timestamp': timestamp,
                    'created_at': row['updated_at']
                })
            
            return backups
            
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def restore_backup(self, backup_name: str) -> bool:
        """
        Restore configuration từ backup
        
        Args:
            backup_name: Name của backup to restore
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get backup data
            row = self.db_service.fetch_one(
                'SELECT value FROM config_metadata WHERE key = ?',
                (backup_name,)
            )
            
            if not row:
                logger.error(f"Backup not found: {backup_name}")
                return False
            
            # Import backup configuration
            return self.import_configuration(row['value'])
            
        except Exception as e:
            logger.error(f"Failed to restore backup '{backup_name}': {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 5) -> int:
        """
        Clean up old configuration backups
        
        Args:
            keep_count: Number của recent backups to keep
            
        Returns:
            Number của backups removed
        """
        try:
            with self.db_service.transaction() as conn:
                # Get old backups
                rows = conn.execute('''
                    SELECT key FROM config_metadata 
                    WHERE key LIKE 'config_backup_%'
                    ORDER BY updated_at DESC
                    LIMIT -1 OFFSET ?
                ''', (keep_count,)).fetchall()
                
                removed_count = 0
                for row in rows:
                    conn.execute('DELETE FROM config_metadata WHERE key = ?', (row['key'],))
                    removed_count += 1
                
                if removed_count > 0:
                    logger.info(f"Cleaned up {removed_count} old configuration backups")
                
                return removed_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0


# Example usage và testing
if __name__ == "__main__":
    def test_config_repository():
        """Test configuration repository"""
        import tempfile
        import os
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Initialize repository
            repo = ConfigRepository(db_path=db_path)
            
            # Test loading default configuration
            config1 = repo.load_configuration()
            print(f"Loaded config version: {config1.version}")
            
            # Modify configuration
            config1.ui_preferences.window_width = 800
            config1.add_recent_folder("/test/folder1")
            config1.add_recent_folder("/test/folder2")
            
            # Test saving
            success = repo.save_configuration(config1)
            print(f"Save successful: {success}")
            
            # Test loading modified configuration
            config2 = repo.load_configuration()
            print(f"Window width: {config2.ui_preferences.window_width}")
            print(f"Recent folders: {config2.get_recent_folders_list()}")
            
            # Test export/import
            json_str = repo.export_configuration()
            print(f"Export JSON length: {len(json_str)}")
            
            # Test reset to defaults
            default_config = repo.reset_to_defaults()
            print(f"Reset successful, window width: {default_config.ui_preferences.window_width}")
            
            # Test configuration info
            info = repo.get_configuration_info()
            print(f"Config info: {info}")
            
            print("Configuration repository test completed successfully")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    test_config_repository()