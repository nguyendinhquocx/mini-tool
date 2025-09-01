"""
Unit Tests for User Preferences & Settings System

Tests configuration data models, persistence, và settings dialog functionality.
"""

import pytest
import tempfile
import os
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Import components to test
from src.core.models.config import (
    AppConfiguration, NormalizationRulesConfig, 
    UIPreferences, OperationSettings, RecentFolder
)
from src.core.repositories.config_repository import ConfigRepository
from src.core.services.config_service import ConfigService
from src.core.services.database_service import DatabaseService


def normalize_test_path(path: str) -> str:
    """Normalize path for cross-platform testing"""
    if os.name == 'nt' and not os.path.isabs(path):
        # On Windows, convert Unix-style paths to Windows absolute paths
        return os.path.abspath(path.replace('/', os.sep))
    elif os.name == 'nt' and path.startswith('/'):
        # Convert Unix absolute paths to Windows
        return os.path.abspath(path)
    return path


class TestAppConfiguration:
    """Test AppConfiguration data model"""
    
    def test_default_configuration_creation(self):
        """Test creating default configuration"""
        config = AppConfiguration()
        
        assert config.version == "1.0"
        assert isinstance(config.normalization_rules, NormalizationRulesConfig)
        assert isinstance(config.ui_preferences, UIPreferences)
        assert isinstance(config.operation_settings, OperationSettings)
        assert config.recent_folders == []
        assert isinstance(config.created_at, datetime)
        assert isinstance(config.last_updated, datetime)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        config = AppConfiguration()
        
        is_valid, errors, warnings = config.validate()
        
        assert is_valid
        assert isinstance(errors, list)
        assert isinstance(warnings, list)
    
    def test_configuration_serialization(self):
        """Test configuration to_dict và from_dict"""
        config = AppConfiguration()
        config.add_recent_folder("/test/path")
        
        # Test to_dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert 'normalization_rules' in config_dict
        assert 'ui_preferences' in config_dict
        assert 'operation_settings' in config_dict
        assert 'recent_folders' in config_dict
        
        # Test from_dict
        config2 = AppConfiguration.from_dict(config_dict)
        assert config2.version == config.version
        assert len(config2.recent_folders) == len(config.recent_folders)
    
    def test_add_recent_folder(self):
        """Test adding recent folders với deduplication"""
        config = AppConfiguration()
        
        # Add folders (using normalized paths)
        path1 = os.path.abspath("/path/1") if os.name == 'nt' else "/path/1"
        path2 = os.path.abspath("/path/2") if os.name == 'nt' else "/path/2"
        
        config.add_recent_folder(path1)
        config.add_recent_folder(path2)
        config.add_recent_folder(path1)  # Duplicate
        
        # Should have only 2 unique folders
        assert len(config.recent_folders) == 2
        assert config.recent_folders[0].path == path1  # Most recent first
        assert config.recent_folders[1].path == path2
    
    def test_clean_recent_folders(self):
        """Test cleaning non-existent recent folders"""
        config = AppConfiguration()
        
        # Add mix của existing và non-existing paths
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_path = temp_dir
            non_existing_path = "/definitely/does/not/exist"
            
            config.add_recent_folder(existing_path)
            config.add_recent_folder(non_existing_path)
            
            # Clean non-existing folders
            removed_count = config.clean_recent_folders()
            
            assert removed_count == 1
            assert len(config.recent_folders) == 1
            assert config.recent_folders[0].path == existing_path
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults"""
        config = AppConfiguration()
        config.add_recent_folder("/test/path")
        config.normalization_rules.remove_diacritics = False
        
        config.reset_to_defaults()
        
        assert len(config.recent_folders) == 0
        assert config.normalization_rules.remove_diacritics is True


class TestNormalizationRulesConfig:
    """Test NormalizationRulesConfig model"""
    
    def test_default_rules(self):
        """Test default normalization rules"""
        rules = NormalizationRulesConfig()
        
        assert rules.remove_diacritics is True
        assert rules.convert_to_lowercase is True
        assert rules.clean_special_characters is True
        assert rules.preserve_extensions is True
        assert rules.max_filename_length == 255
        assert rules.custom_replacements == {}
    
    def test_rules_validation(self):
        """Test normalization rules validation"""
        rules = NormalizationRulesConfig()
        
        is_valid, errors, warnings = rules.validate()
        assert is_valid
        assert len(errors) == 0
        
        # Test invalid rules
        rules.max_filename_length = -1
        is_valid, errors, warnings = rules.validate()
        assert not is_valid
        assert len(errors) > 0
    
    def test_custom_replacements(self):
        """Test custom character replacements"""
        rules = NormalizationRulesConfig()
        rules.custom_replacements = {'ñ': 'n', 'ç': 'c'}
        
        is_valid, errors, warnings = rules.validate()
        assert is_valid
        
        # Test invalid replacements
        rules.custom_replacements = {123: 'invalid'}
        is_valid, errors, warnings = rules.validate()
        assert not is_valid


class TestUIPreferences:
    """Test UIPreferences model"""
    
    def test_default_preferences(self):
        """Test default UI preferences"""
        prefs = UIPreferences()
        
        assert prefs.window_width == 600
        assert prefs.window_height == 500
        assert prefs.theme == "default"
        assert prefs.max_recent_folders == 10
        assert prefs.confirm_operations is True
    
    def test_preferences_validation(self):
        """Test UI preferences validation"""
        prefs = UIPreferences()
        
        is_valid, errors, warnings = prefs.validate()
        assert is_valid
        
        # Test invalid preferences
        prefs.window_width = 100  # Too small
        is_valid, errors, warnings = prefs.validate()
        assert not is_valid
        assert len(errors) > 0


class TestOperationSettings:
    """Test OperationSettings model"""
    
    def test_default_settings(self):
        """Test default operation settings"""
        settings = OperationSettings()
        
        assert settings.dry_run_by_default is True
        assert settings.create_backups is True
        assert settings.skip_hidden_files is True
        assert settings.large_operation_threshold == 100
    
    def test_settings_validation(self):
        """Test operation settings validation"""
        settings = OperationSettings()
        
        is_valid, errors, warnings = settings.validate()
        assert is_valid
        
        # Test invalid settings
        settings.max_concurrent_operations = 0
        is_valid, errors, warnings = settings.validate()
        assert not is_valid


class TestRecentFolder:
    """Test RecentFolder model"""
    
    def test_recent_folder_creation(self):
        """Test creating recent folder entry"""
        now = datetime.now()
        folder = RecentFolder(path="/test/path", last_accessed=now)
        
        assert folder.path == "/test/path"
        assert folder.last_accessed == now
        assert folder.access_count == 1
        assert folder.display_name == "path"
    
    def test_recent_folder_serialization(self):
        """Test recent folder serialization"""
        now = datetime.now()
        folder = RecentFolder(path="/test/path", last_accessed=now)
        
        folder_dict = folder.to_dict()
        assert isinstance(folder_dict, dict)
        assert folder_dict['path'] == "/test/path"
        assert 'last_accessed' in folder_dict
        
        folder2 = RecentFolder.from_dict(folder_dict)
        assert folder2.path == folder.path
        assert folder2.access_count == folder.access_count


class TestConfigRepository:
    """Test ConfigRepository persistence layer"""
    
    def setup_method(self):
        """Setup test database"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.db_service = DatabaseService(self.db_path)
        self.repository = ConfigRepository(self.db_service)
    
    def teardown_method(self):
        """Cleanup test database"""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
    
    def test_load_default_configuration(self):
        """Test loading default configuration when none exists"""
        config = self.repository.load_configuration()
        
        assert isinstance(config, AppConfiguration)
        assert config.version == "1.0"
    
    def test_save_and_load_configuration(self):
        """Test saving và loading configuration"""
        # Create test configuration
        config = AppConfiguration()
        config.add_recent_folder("/test/folder")
        config.normalization_rules.remove_diacritics = False
        
        # Save configuration
        success = self.repository.save_configuration(config)
        assert success
        
        # Load configuration
        loaded_config = self.repository.load_configuration()
        
        assert loaded_config.normalization_rules.remove_diacritics is False
        assert len(loaded_config.recent_folders) == 1
        # Use normalized path for comparison on Windows
        expected_path = os.path.abspath("/test/folder") if os.name == 'nt' else "/test/folder"
        assert loaded_config.recent_folders[0].path == expected_path
    
    def test_reset_to_defaults(self):
        """Test resetting to default configuration"""
        # Save custom configuration
        config = AppConfiguration()
        config.add_recent_folder("/test")
        self.repository.save_configuration(config)
        
        # Reset to defaults
        default_config = self.repository.reset_to_defaults()
        
        assert len(default_config.recent_folders) == 0
        assert default_config.normalization_rules.remove_diacritics is True
    
    def test_add_recent_folder(self):
        """Test adding recent folder directly"""
        test_path = "/test/path"
        success = self.repository.add_recent_folder(test_path)
        assert success
        
        config = self.repository.load_configuration()
        assert len(config.recent_folders) == 1
        expected_path = normalize_test_path(test_path)
        assert config.recent_folders[0].path == expected_path
    
    def test_export_import_configuration(self):
        """Test configuration export and import"""
        # Create test configuration
        config = AppConfiguration()
        config.add_recent_folder("/test/export")
        self.repository.save_configuration(config)
        
        # Export configuration
        json_str = self.repository.export_configuration()
        assert json_str
        
        # Verify JSON is valid
        config_data = json.loads(json_str)
        assert 'recent_folders' in config_data
        
        # Reset và import
        self.repository.reset_to_defaults()
        success = self.repository.import_configuration(json_str)
        assert success
        
        # Verify imported configuration
        imported_config = self.repository.load_configuration()
        assert len(imported_config.recent_folders) == 1
        expected_path = normalize_test_path("/test/export")
        assert imported_config.recent_folders[0].path == expected_path
    
    def test_configuration_backup_restore(self):
        """Test configuration backup và restore functionality"""
        # Create test configuration
        config = AppConfiguration()
        config.add_recent_folder("/backup/test")
        self.repository.save_configuration(config)
        
        # List backups (should be empty initially)
        backups = self.repository.list_backups()
        initial_count = len(backups)
        
        # Test backup creation via reset (creates backup automatically)
        self.repository.reset_to_defaults()
        
        # Check backup was created
        backups = self.repository.list_backups()
        assert len(backups) > initial_count
        
        # Test restore
        if backups:
            backup_name = backups[0]['name']
            success = self.repository.restore_backup(backup_name)
            assert success
            
            # Verify restored configuration
            restored_config = self.repository.load_configuration()
            assert len(restored_config.recent_folders) == 1


class TestConfigService:
    """Test ConfigService high-level operations"""
    
    def setup_method(self):
        """Setup test service"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.service = ConfigService(db_path=self.db_path)
    
    def teardown_method(self):
        """Cleanup test database"""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
    
    def test_get_current_config(self):
        """Test getting current configuration"""
        config = self.service.get_current_config()
        
        assert isinstance(config, AppConfiguration)
        assert config.version == "1.0"
    
    def test_update_normalization_rules(self):
        """Test updating normalization rules"""
        rules = self.service.get_normalization_rules()
        rules.remove_diacritics = False
        
        success = self.service.update_normalization_rules(rules)
        assert success
        
        updated_rules = self.service.get_normalization_rules()
        assert updated_rules.remove_diacritics is False
    
    def test_update_ui_preferences(self):
        """Test updating UI preferences"""
        prefs = self.service.get_ui_preferences()
        prefs.window_width = 800
        
        success = self.service.update_ui_preferences(prefs)
        assert success
        
        updated_prefs = self.service.get_ui_preferences()
        assert updated_prefs.window_width == 800
    
    def test_recent_folders_management(self):
        """Test recent folders operations"""
        # Add recent folder
        success = self.service.add_recent_folder("/service/test")
        assert success
        
        # Get recent folders
        folders = self.service.get_recent_folders()
        assert len(folders) == 1
        expected_path = normalize_test_path("/service/test")
        assert folders[0] == expected_path
        
        # Clean recent folders (no effect since path doesn't exist)
        with patch('os.path.exists', return_value=False):
            removed = self.service.clean_recent_folders()
            assert removed == 1
            
            folders_after = self.service.get_recent_folders()
            assert len(folders_after) == 0
    
    def test_reset_to_defaults(self):
        """Test resetting service to defaults"""
        # Modify configuration
        self.service.add_recent_folder("/before/reset")
        
        # Reset
        success = self.service.reset_to_defaults()
        assert success
        
        # Verify reset
        config = self.service.get_current_config()
        assert len(config.recent_folders) == 0
    
    def test_change_listeners(self):
        """Test configuration change listeners"""
        listener_called = False
        received_config = None
        
        def test_listener(config):
            nonlocal listener_called, received_config
            listener_called = True
            received_config = config
        
        # Add listener
        self.service.add_change_listener(test_listener)
        
        # Make change
        rules = self.service.get_normalization_rules()
        rules.remove_diacritics = False
        self.service.update_normalization_rules(rules)
        
        # Verify listener was called
        assert listener_called
        assert received_config is not None
        assert received_config.normalization_rules.remove_diacritics is False
        
        # Remove listener
        self.service.remove_change_listener(test_listener)
    
    def test_window_geometry_update(self):
        """Test window geometry updates"""
        success = self.service.update_window_geometry(
            width=1024, height=768, x=100, y=50, maximized=True
        )
        assert success
        
        prefs = self.service.get_ui_preferences()
        assert prefs.window_width == 1024
        assert prefs.window_height == 768
        assert prefs.window_x == 100
        assert prefs.window_y == 50
        assert prefs.window_maximized is True
    
    def test_service_info(self):
        """Test getting service information"""
        info = self.service.get_service_info()
        
        assert isinstance(info, dict)
        assert 'current_config_version' in info
        assert 'recent_folders_count' in info
    
    def test_configuration_validation(self):
        """Test configuration validation through service"""
        validation = self.service.validate_current_configuration()
        
        assert isinstance(validation, dict)
        assert 'is_valid' in validation
        assert 'errors' in validation
        assert 'warnings' in validation
        assert validation['is_valid'] is True


@pytest.mark.integration
class TestUserPreferencesIntegration:
    """Integration tests for user preferences system"""
    
    def setup_method(self):
        """Setup integration test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        # Create service with clean database
        self.service = ConfigService(db_path=self.db_path)
    
    def teardown_method(self):
        """Cleanup integration test"""
        try:
            os.unlink(self.db_path)
        except OSError:
            pass
    
    def test_complete_settings_workflow(self):
        """Test complete user preferences workflow"""
        # 1. Start với default configuration
        config = self.service.get_current_config()
        assert config.normalization_rules.remove_diacritics is True
        assert len(config.recent_folders) == 0
        
        # 2. Update normalization rules
        rules = config.normalization_rules
        rules.remove_diacritics = False
        rules.custom_replacements = {'ñ': 'n'}
        success = self.service.update_normalization_rules(rules)
        assert success
        
        # 3. Update UI preferences
        ui_prefs = config.ui_preferences
        ui_prefs.window_width = 1200
        ui_prefs.theme = "dark"
        success = self.service.update_ui_preferences(ui_prefs)
        assert success
        
        # 4. Add recent folders
        self.service.add_recent_folder("/workflow/test1")
        self.service.add_recent_folder("/workflow/test2")
        
        # 5. Verify all changes persisted
        updated_config = self.service.get_current_config()
        assert updated_config.normalization_rules.remove_diacritics is False
        assert updated_config.normalization_rules.custom_replacements['ñ'] == 'n'
        assert updated_config.ui_preferences.window_width == 1200
        assert updated_config.ui_preferences.theme == "dark"
        assert len(updated_config.recent_folders) == 2
        
        # 6. Test export/import workflow
        json_export = self.service.export_configuration()
        assert json_export
        
        # Reset và import
        self.service.reset_to_defaults()
        import_success = self.service.import_configuration(json_export)
        assert import_success
        
        # Verify imported configuration matches
        final_config = self.service.get_current_config()
        assert final_config.normalization_rules.remove_diacritics is False
        assert final_config.ui_preferences.window_width == 1200
        assert len(final_config.recent_folders) == 2
    
    def test_settings_persistence_workflow(self):
        """Test settings persistence across service restarts"""
        # Create initial configuration
        self.service.add_recent_folder("/persistence/test")
        rules = self.service.get_normalization_rules()
        rules.max_filename_length = 100
        self.service.update_normalization_rules(rules)
        
        # Simulate service restart
        self.service.shutdown()
        new_service = ConfigService(db_path=self.db_path)
        
        # Verify settings persisted
        config = new_service.get_current_config()
        assert len(config.recent_folders) == 1
        expected_path = normalize_test_path("/persistence/test")
        assert config.recent_folders[0].path == expected_path
        assert config.normalization_rules.max_filename_length == 100
        
        new_service.shutdown()
    
    def test_configuration_error_recovery(self):
        """Test error recovery in configuration system"""
        # Test invalid configuration handling
        with patch.object(self.service.repository, 'load_configuration') as mock_load:
            mock_load.side_effect = Exception("Database error")
            
            # Service should handle error gracefully
            config = self.service.get_current_config()
            assert isinstance(config, AppConfiguration)
        
        # Test validation error handling
        rules = self.service.get_normalization_rules()
        rules.max_filename_length = -1  # Invalid
        
        success = self.service.update_normalization_rules(rules)
        assert success is False  # Should reject invalid configuration


if __name__ == "__main__":
    # Run tests với pytest
    pytest.main([__file__, "-v"])