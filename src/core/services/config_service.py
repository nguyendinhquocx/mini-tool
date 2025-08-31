"""
Configuration Service

High-level service for managing application configuration including
user preferences, settings persistence, and real-time configuration updates.
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from threading import Lock
from datetime import datetime

from ..models.config import AppConfiguration, NormalizationRulesConfig, UIPreferences, OperationSettings
from ..repositories.config_repository import ConfigRepository
from ..services.database_service import DatabaseService

logger = logging.getLogger(__name__)


class ConfigService:
    """
    Service for application configuration management
    
    Provides high-level interface for configuration operations including
    loading, saving, real-time updates, and change notifications.
    """
    
    def __init__(self, db_service: Optional[DatabaseService] = None, db_path: Optional[str] = None):
        """
        Initialize configuration service
        
        Args:
            db_service: Optional database service instance
            db_path: Optional custom database path
        """
        self.repository = ConfigRepository(db_service, db_path)
        self._current_config: Optional[AppConfiguration] = None
        self._change_listeners: List[Callable[[AppConfiguration], None]] = []
        self._lock = Lock()
        
        # Initialize configuration
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from repository"""
        try:
            with self._lock:
                self._current_config = self.repository.load_configuration()
                logger.info("Configuration service initialized")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._current_config = AppConfiguration()
    
    def get_current_config(self) -> AppConfiguration:
        """
        Get current configuration
        
        Returns:
            Current AppConfiguration instance
        """
        with self._lock:
            if self._current_config is None:
                self._load_configuration()
            return self._current_config
    
    def update_configuration(self, config: AppConfiguration, notify_listeners: bool = True) -> bool:
        """
        Update complete configuration
        
        Args:
            config: New configuration to apply
            notify_listeners: Whether to notify change listeners
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate configuration
            is_valid, errors, warnings = config.validate()
            if not is_valid:
                logger.error(f"Cannot update with invalid configuration: {errors}")
                return False
            
            if warnings:
                logger.warning(f"Configuration warnings: {warnings}")
            
            # Save to repository
            if not self.repository.save_configuration(config):
                logger.error("Failed to save configuration to repository")
                return False
            
            # Update current configuration
            with self._lock:
                old_config = self._current_config
                self._current_config = config
            
            # Notify listeners
            if notify_listeners:
                self._notify_listeners(config)
            
            logger.info("Configuration updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration: {e}")
            return False
    
    def get_normalization_rules(self) -> NormalizationRulesConfig:
        """
        Get current normalization rules configuration
        
        Returns:
            NormalizationRulesConfig instance
        """
        return self.get_current_config().normalization_rules
    
    def update_normalization_rules(self, rules: NormalizationRulesConfig) -> bool:
        """
        Update normalization rules configuration
        
        Args:
            rules: New normalization rules
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate rules
            is_valid, errors, warnings = rules.validate()
            if not is_valid:
                logger.error(f"Invalid normalization rules: {errors}")
                return False
            
            # Update configuration
            config = self.get_current_config()
            config.normalization_rules = rules
            config.last_updated = datetime.now()
            
            return self.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Failed to update normalization rules: {e}")
            return False
    
    def get_ui_preferences(self) -> UIPreferences:
        """
        Get current UI preferences
        
        Returns:
            UIPreferences instance
        """
        return self.get_current_config().ui_preferences
    
    def update_ui_preferences(self, preferences: UIPreferences) -> bool:
        """
        Update UI preferences
        
        Args:
            preferences: New UI preferences
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate preferences
            is_valid, errors, warnings = preferences.validate()
            if not is_valid:
                logger.error(f"Invalid UI preferences: {errors}")
                return False
            
            # Update configuration
            config = self.get_current_config()
            config.ui_preferences = preferences
            config.last_updated = datetime.now()
            
            return self.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Failed to update UI preferences: {e}")
            return False
    
    def get_operation_settings(self) -> OperationSettings:
        """
        Get current operation settings
        
        Returns:
            OperationSettings instance
        """
        return self.get_current_config().operation_settings
    
    def update_operation_settings(self, settings: OperationSettings) -> bool:
        """
        Update operation settings
        
        Args:
            settings: New operation settings
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Validate settings
            is_valid, errors, warnings = settings.validate()
            if not is_valid:
                logger.error(f"Invalid operation settings: {errors}")
                return False
            
            # Update configuration
            config = self.get_current_config()
            config.operation_settings = settings
            config.last_updated = datetime.now()
            
            return self.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Failed to update operation settings: {e}")
            return False
    
    def add_recent_folder(self, folder_path: str) -> bool:
        """
        Add folder to recent folders list
        
        Args:
            folder_path: Path to folder to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self.get_current_config()
            config.add_recent_folder(folder_path)
            
            return self.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Failed to add recent folder: {e}")
            return False
    
    def get_recent_folders(self) -> List[str]:
        """
        Get list of recent folder paths
        
        Returns:
            List of recent folder paths
        """
        return self.get_current_config().get_recent_folders_list()
    
    def clean_recent_folders(self) -> int:
        """
        Remove non-existent folders from recent list
        
        Returns:
            Number of folders removed
        """
        try:
            config = self.get_current_config()
            removed_count = config.clean_recent_folders()
            
            if removed_count > 0:
                self.update_configuration(config)
                logger.info(f"Cleaned {removed_count} non-existent recent folders")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to clean recent folders: {e}")
            return 0
    
    def reset_to_defaults(self, confirm_callback: Optional[Callable[[], bool]] = None) -> bool:
        """
        Reset configuration to default values
        
        Args:
            confirm_callback: Optional callback for user confirmation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get confirmation if callback provided
            if confirm_callback and not confirm_callback():
                logger.info("Reset to defaults cancelled by user")
                return False
            
            # Reset via repository
            default_config = self.repository.reset_to_defaults()
            
            # Update current configuration
            with self._lock:
                self._current_config = default_config
            
            # Notify listeners
            self._notify_listeners(default_config)
            
            logger.info("Configuration reset to defaults")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset to defaults: {e}")
            return False
    
    def export_configuration(self) -> str:
        """
        Export configuration as JSON string
        
        Returns:
            JSON string of complete configuration
        """
        try:
            return self.repository.export_configuration()
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
            return "{}"
    
    def import_configuration(self, json_str: str, confirm_callback: Optional[Callable[[], bool]] = None) -> bool:
        """
        Import configuration from JSON string
        
        Args:
            json_str: JSON string containing configuration
            confirm_callback: Optional callback for user confirmation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get confirmation if callback provided
            if confirm_callback and not confirm_callback():
                logger.info("Configuration import cancelled by user")
                return False
            
            # Import via repository
            if not self.repository.import_configuration(json_str):
                return False
            
            # Reload current configuration
            self._load_configuration()
            
            # Notify listeners
            if self._current_config:
                self._notify_listeners(self._current_config)
            
            logger.info("Configuration imported successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            return False
    
    def update_window_geometry(self, width: int, height: int, x: Optional[int] = None, y: Optional[int] = None, maximized: bool = False) -> bool:
        """
        Update window geometry in UI preferences
        
        Args:
            width: Window width
            height: Window height
            x: Window x position (optional)
            y: Window y position (optional)
            maximized: Whether window is maximized
            
        Returns:
            True if successful, False otherwise
        """
        try:
            config = self.get_current_config()
            
            config.ui_preferences.window_width = width
            config.ui_preferences.window_height = height
            if x is not None:
                config.ui_preferences.window_x = x
            if y is not None:
                config.ui_preferences.window_y = y
            config.ui_preferences.window_maximized = maximized
            
            # Save without notifying listeners (to avoid recursion)
            return self.repository.save_configuration(config)
            
        except Exception as e:
            logger.error(f"Failed to update window geometry: {e}")
            return False
    
    def add_change_listener(self, listener: Callable[[AppConfiguration], None]):
        """
        Add configuration change listener
        
        Args:
            listener: Callback function to call when configuration changes
        """
        with self._lock:
            if listener not in self._change_listeners:
                self._change_listeners.append(listener)
                logger.debug(f"Added configuration change listener: {listener}")
    
    def remove_change_listener(self, listener: Callable[[AppConfiguration], None]):
        """
        Remove configuration change listener
        
        Args:
            listener: Callback function to remove
        """
        with self._lock:
            if listener in self._change_listeners:
                self._change_listeners.remove(listener)
                logger.debug(f"Removed configuration change listener: {listener}")
    
    def _notify_listeners(self, config: AppConfiguration):
        """Notify all change listeners về configuration update"""
        with self._lock:
            listeners = self._change_listeners.copy()
        
        for listener in listeners:
            try:
                listener(config)
            except Exception as e:
                logger.error(f"Error notifying configuration change listener: {e}")
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get configuration service information
        
        Returns:
            Service information dictionary
        """
        try:
            config = self.get_current_config()
            repo_info = self.repository.get_configuration_info()
            
            return {
                'current_config_version': config.version,
                'last_updated': config.last_updated.isoformat() if config.last_updated else None,
                'recent_folders_count': len(config.recent_folders),
                'change_listeners_count': len(self._change_listeners),
                'repository_info': repo_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get service info: {e}")
            return {}
    
    def validate_current_configuration(self) -> Dict[str, Any]:
        """
        Validate current configuration và return results
        
        Returns:
            Validation results dictionary
        """
        try:
            config = self.get_current_config()
            is_valid, errors, warnings = config.validate()
            
            return {
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'config_version': config.version,
                'last_updated': config.last_updated.isoformat() if config.last_updated else None
            }
            
        except Exception as e:
            logger.error(f"Failed to validate configuration: {e}")
            return {
                'is_valid': False,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    def backup_configuration(self) -> bool:
        """
        Create backup của current configuration
        
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.repository._create_backup()
        except Exception as e:
            logger.error(f"Failed to backup configuration: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, str]]:
        """
        List available configuration backups
        
        Returns:
            List of backup information dictionaries
        """
        try:
            return self.repository.list_backups()
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
            return []
    
    def restore_backup(self, backup_name: str, confirm_callback: Optional[Callable[[], bool]] = None) -> bool:
        """
        Restore configuration từ backup
        
        Args:
            backup_name: Name của backup to restore
            confirm_callback: Optional callback for user confirmation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get confirmation if callback provided
            if confirm_callback and not confirm_callback():
                logger.info("Backup restore cancelled by user")
                return False
            
            if not self.repository.restore_backup(backup_name):
                return False
            
            # Reload current configuration
            self._load_configuration()
            
            # Notify listeners
            if self._current_config:
                self._notify_listeners(self._current_config)
            
            logger.info(f"Configuration restored từ backup: {backup_name}")
            return True
            
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
            return self.repository.cleanup_old_backups(keep_count)
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
            return 0
    
    def shutdown(self):
        """Shutdown configuration service và cleanup resources"""
        try:
            with self._lock:
                # Save current configuration if modified
                if self._current_config:
                    self.repository.save_configuration(self._current_config)
                
                # Clear listeners
                self._change_listeners.clear()
            
            logger.info("Configuration service shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during configuration service shutdown: {e}")


# Global configuration service instance
_config_service: Optional[ConfigService] = None


def get_config_service(db_service: Optional[DatabaseService] = None, db_path: Optional[str] = None) -> ConfigService:
    """
    Get global configuration service instance
    
    Args:
        db_service: Optional database service instance
        db_path: Optional custom database path
        
    Returns:
        ConfigService instance
    """
    global _config_service
    
    if _config_service is None:
        _config_service = ConfigService(db_service, db_path)
    
    return _config_service


# Example usage và testing
if __name__ == "__main__":
    def test_config_service():
        """Test configuration service"""
        import tempfile
        import os
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Initialize service
            service = ConfigService(db_path=db_path)
            
            # Test getting current configuration
            config = service.get_current_config()
            print(f"Current config version: {config.version}")
            
            # Test updating normalization rules
            rules = service.get_normalization_rules()
            rules.remove_diacritics = False
            success = service.update_normalization_rules(rules)
            print(f"Update rules successful: {success}")
            
            # Test adding recent folder
            success = service.add_recent_folder("/test/folder")
            print(f"Add recent folder successful: {success}")
            
            # Test getting recent folders
            folders = service.get_recent_folders()
            print(f"Recent folders: {folders}")
            
            # Test export/import
            json_str = service.export_configuration()
            print(f"Export JSON length: {len(json_str)}")
            
            # Test validation
            validation = service.validate_current_configuration()
            print(f"Configuration valid: {validation['is_valid']}")
            
            # Test service info
            info = service.get_service_info()
            print(f"Service info: {info}")
            
            print("Configuration service test completed successfully")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    test_config_service()