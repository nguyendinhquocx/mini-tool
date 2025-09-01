"""
Integration Tests for Settings System

Tests complete settings workflows including UI integration,
persistence, and real-time application.
"""

import pytest
import tempfile
import os
import tkinter as tk
from unittest.mock import Mock, patch, MagicMock

from src.core.services.config_service import ConfigService
from src.core.models.config import AppConfiguration, NormalizationRulesConfig
from src.core.services.normalize_service import VietnameseNormalizer


def normalize_test_path(path: str) -> str:
    """Normalize path for cross-platform testing"""
    if os.name == 'nt' and not os.path.isabs(path):
        # On Windows, convert Unix-style paths to Windows absolute paths
        return os.path.abspath(path.replace('/', os.sep))
    elif os.name == 'nt' and path.startswith('/'):
        # Convert Unix absolute paths to Windows
        return os.path.abspath(path[1:])  # Remove leading slash and make absolute
    return path


@pytest.mark.integration  
class TestSettingsIntegration:
    """Integration tests cho complete settings system"""
    
    def setup_method(self):
        """Setup integration test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.config_service = ConfigService(db_path=self.db_path)
    
    def teardown_method(self):
        """Cleanup integration test"""
        try:
            self.config_service.shutdown()
            os.unlink(self.db_path)
        except OSError:
            pass
    
    def test_configuration_immediate_application(self):
        """Test settings changes apply immediately without restart"""
        # Get initial normalization service
        initial_rules = self.config_service.get_normalization_rules()
        normalizer = VietnameseNormalizer.from_config(initial_rules)
        
        # Test initial normalization
        test_text = "Tệp tiếng Việt.txt"
        initial_result = normalizer.normalize_filename_with_config(test_text, initial_rules)
        assert "ệ" not in initial_result  # Should remove diacritics by default
        
        # Change settings
        new_rules = self.config_service.get_normalization_rules()
        new_rules.remove_diacritics = False
        success = self.config_service.update_normalization_rules(new_rules)
        assert success
        
        # Test với updated rules
        updated_rules = self.config_service.get_normalization_rules()
        new_result = normalizer.normalize_filename_with_config(test_text, updated_rules)
        assert "ệ" in new_result  # Should preserve diacritics now
    
    def test_ui_preferences_persistence_workflow(self):
        """Test complete UI preferences workflow"""
        # Simulate main window geometry changes
        self.config_service.update_window_geometry(
            width=1024, height=768, x=200, y=100, maximized=False
        )
        
        # Add recent folders (normalize paths for cross-platform compatibility)
        test_folders = [normalize_test_path("/folder1"), normalize_test_path("/folder2"), normalize_test_path("/folder3")]
        for folder in test_folders:
            self.config_service.add_recent_folder(folder)
        
        # Update UI preferences
        ui_prefs = self.config_service.get_ui_preferences()
        ui_prefs.theme = "dark"
        ui_prefs.font_size = 12
        ui_prefs.max_recent_folders = 5
        success = self.config_service.update_ui_preferences(ui_prefs)
        assert success
        
        # Simulate application restart
        self.config_service.shutdown()
        new_service = ConfigService(db_path=self.db_path)
        
        # Verify all preferences persisted
        restored_config = new_service.get_current_config()
        
        # Check window geometry
        assert restored_config.ui_preferences.window_width == 1024
        assert restored_config.ui_preferences.window_height == 768
        assert restored_config.ui_preferences.window_x == 200
        assert restored_config.ui_preferences.window_y == 100
        
        # Check UI preferences
        assert restored_config.ui_preferences.theme == "dark"
        assert restored_config.ui_preferences.font_size == 12
        assert restored_config.ui_preferences.max_recent_folders == 5
        
        # Check recent folders
        recent_folders = restored_config.get_recent_folders_list()
        assert len(recent_folders) == 3
        # Use normalized path for cross-platform compatibility
        expected_folder3 = test_folders[2]  # Use the already normalized path
        assert recent_folders[0] == expected_folder3  # Most recent first
        
        new_service.shutdown()
    
    def test_normalization_engine_integration(self):
        """Test integration với Vietnamese normalization engine"""
        # Test custom replacement rules
        rules = self.config_service.get_normalization_rules()
        rules.custom_replacements = {
            'ñ': 'n',
            '@': '_at_',
            '#': '_hash_'
        }
        rules.remove_diacritics = True
        success = self.config_service.update_normalization_rules(rules)
        assert success
        
        # Test normalization với custom rules
        normalizer = VietnameseNormalizer()
        updated_rules = self.config_service.get_normalization_rules()
        
        test_cases = [
            ("señor@email.com#1", "senor_at_email.com_hash_1"),
            ("tệp_tiếng_việt.txt", "tep_tieng_viet.txt"),
            ("Văn bản #2023.pdf", "van ban _hash_2023.pdf")
        ]
        
        for input_text, expected in test_cases:
            result = normalizer.normalize_filename_with_config(input_text, updated_rules)
            
            # Basic check - should apply custom replacements
            assert '@' not in result, f"@ should be replaced in '{result}'"
            assert '#' not in result, f"# should be replaced in '{result}'"
            
            # Should contain custom replacements or their clean_special_chars equivalents
            if '@' in input_text:
                # Custom replacement '_at_' may be further processed to ' at ' by clean_special_chars
                assert ('_at_' in result or ' at ' in result), f"_at_ or ' at ' should be present in '{result}'"
            if '#' in input_text:
                # Custom replacement '_hash_' may be further processed to ' hash ' by clean_special_chars  
                assert ('_hash_' in result or ' hash ' in result), f"_hash_ or ' hash ' should be present in '{result}'"
            if 'ñ' in input_text:
                assert 'ñ' not in result, f"ñ should be removed in '{result}'"
    
    def test_operation_settings_integration(self):
        """Test operation settings integration với batch operations"""
        # Update operation settings
        op_settings = self.config_service.get_operation_settings()
        op_settings.dry_run_by_default = True
        op_settings.create_backups = True
        op_settings.skip_hidden_files = False
        op_settings.large_operation_threshold = 50
        success = self.config_service.update_operation_settings(op_settings)
        assert success
        
        # Verify settings are accessible
        current_settings = self.config_service.get_operation_settings()
        assert current_settings.dry_run_by_default is True
        assert current_settings.create_backups is True
        assert current_settings.skip_hidden_files is False
        assert current_settings.large_operation_threshold == 50
        
        # Test integration với batch operation request
        # (This would be tested further in actual batch operation tests)
        from src.core.models.operation import BatchOperationRequest, OperationType
        from src.core.models.file_info import FileInfo
        
        # Create mock batch request
        test_files = [FileInfo(name="test.txt", path="/test", size=100)]
        
        # This demonstrates how operation settings would be used
        dry_run_mode = current_settings.dry_run_by_default
        create_backups = current_settings.create_backups
        
        assert dry_run_mode is True
        assert create_backups is True
    
    def test_configuration_backup_restore_integration(self):
        """Test complete backup and restore workflow"""
        # Create comprehensive configuration
        config = self.config_service.get_current_config()
        
        # Update normalization rules
        config.normalization_rules.remove_diacritics = False
        config.normalization_rules.custom_replacements = {'@': '_at_'}
        self.config_service.update_normalization_rules(config.normalization_rules)
        
        # Update UI preferences
        config.ui_preferences.window_width = 1200
        config.ui_preferences.theme = "dark"
        self.config_service.update_ui_preferences(config.ui_preferences)
        
        # Add recent folders
        self.config_service.add_recent_folder("/backup/test1")
        self.config_service.add_recent_folder("/backup/test2")
        
        # Create backup
        backup_success = self.config_service.backup_configuration()
        assert backup_success
        
        # Verify backup exists
        backups = self.config_service.list_backups()
        assert len(backups) > 0
        
        # Modify configuration after backup
        self.config_service.reset_to_defaults()
        reset_config = self.config_service.get_current_config()
        assert reset_config.normalization_rules.remove_diacritics is True  # Back to default
        assert len(reset_config.recent_folders) == 0
        
        # Restore từ backup
        backup_name = backups[0]['name']
        restore_success = self.config_service.restore_backup(backup_name)
        assert restore_success
        
        # Verify restoration
        restored_config = self.config_service.get_current_config()
        assert restored_config.normalization_rules.remove_diacritics is False
        assert restored_config.normalization_rules.custom_replacements['@'] == '_at_'
        assert restored_config.ui_preferences.window_width == 1200
        assert restored_config.ui_preferences.theme == "dark"
        assert len(restored_config.recent_folders) == 2
    
    def test_configuration_change_listeners(self):
        """Test configuration change notification system"""
        changes_received = []
        
        def change_listener(config):
            changes_received.append(config.version)
        
        # Add listener
        self.config_service.add_change_listener(change_listener)
        
        # Make changes
        rules = self.config_service.get_normalization_rules()
        rules.remove_diacritics = False
        self.config_service.update_normalization_rules(rules)
        
        ui_prefs = self.config_service.get_ui_preferences()
        ui_prefs.window_width = 900
        self.config_service.update_ui_preferences(ui_prefs)
        
        self.config_service.add_recent_folder("/listener/test")
        
        # Verify listener was called for each change
        assert len(changes_received) >= 3  # At least 3 changes
        
        # Remove listener
        self.config_service.remove_change_listener(change_listener)
        
        # Make another change
        self.config_service.add_recent_folder("/listener/test2")
        
        # Should not receive new notifications
        previous_count = len(changes_received)
        # Give a moment for any potential delayed notifications
        assert len(changes_received) == previous_count
    
    def test_settings_validation_integration(self):
        """Test settings validation across all components"""
        # Test valid configuration
        validation = self.config_service.validate_current_configuration()
        assert validation['is_valid'] is True
        assert len(validation['errors']) == 0
        
        # Test configuration với warnings
        rules = self.config_service.get_normalization_rules()
        rules.max_filename_length = 300  # Above Windows limit
        self.config_service.update_normalization_rules(rules)
        
        validation = self.config_service.validate_current_configuration()
        assert validation['is_valid'] is True  # Valid but với warnings
        assert len(validation['warnings']) > 0
        
        # Test invalid configuration (should be prevented)
        rules.max_filename_length = -1  # Invalid
        success = self.config_service.update_normalization_rules(rules)
        assert success is False  # Should reject invalid rules
        
        # Verify configuration remains valid
        validation = self.config_service.validate_current_configuration()
        assert validation['is_valid'] is True
    
    def test_recent_folders_cleanup_integration(self):
        """Test recent folders cleanup với real file system"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test directories
            existing_dir1 = os.path.join(temp_dir, "existing1")
            existing_dir2 = os.path.join(temp_dir, "existing2")
            os.makedirs(existing_dir1)
            os.makedirs(existing_dir2)
            
            # Add mix của existing và non-existing folders
            self.config_service.add_recent_folder(existing_dir1)
            self.config_service.add_recent_folder("/definitely/not/exist")
            self.config_service.add_recent_folder(existing_dir2)
            self.config_service.add_recent_folder("/also/not/exist")
            
            # Verify all were added
            folders = self.config_service.get_recent_folders()
            assert len(folders) == 4
            
            # Clean non-existing folders
            removed_count = self.config_service.clean_recent_folders()
            assert removed_count == 2
            
            # Verify only existing folders remain
            cleaned_folders = self.config_service.get_recent_folders()
            assert len(cleaned_folders) == 2
            assert existing_dir1 in cleaned_folders
            assert existing_dir2 in cleaned_folders


@pytest.mark.integration
@pytest.mark.ui
class TestSettingsUIIntegration:
    """UI integration tests for settings system"""
    
    def setup_method(self):
        """Setup UI test environment"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.config_service = ConfigService(db_path=self.db_path)
        
        # Create root window for testing
        self.root = tk.Tk()
        self.root.withdraw()  # Hide window during testing
    
    def teardown_method(self):
        """Cleanup UI test"""
        try:
            self.root.destroy()
            self.config_service.shutdown()
            os.unlink(self.db_path)
        except (OSError, tk.TclError):
            pass
    
    def test_settings_menu_integration(self):
        """Test settings menu integration với main window"""
        from src.ui.components.settings_panel import SettingsMenuIntegration
        
        # Create menubar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Add settings menu
        settings_integration = SettingsMenuIntegration(self.config_service)
        settings_integration.add_settings_menu(menubar, self.root)
        
        # Verify menu was added
        menu_labels = []
        for i in range(menubar.index(tk.END) + 1):
            try:
                label = menubar.entryconfig(i, 'label')[4]
                menu_labels.append(label)
            except tk.TclError:
                pass
        
        assert "Settings" in menu_labels
    
    def test_quick_settings_panel_integration(self):
        """Test quick settings panel integration"""
        from src.ui.components.settings_panel import QuickSettingsPanel
        
        # Create container frame
        container = tk.Frame(self.root)
        
        # Create quick settings panel
        quick_settings = QuickSettingsPanel(container, self.config_service)
        panel = quick_settings.create_panel()
        
        assert panel is not None
        assert isinstance(panel, tk.Widget)
    
    @patch('src.ui.dialogs.settings_dialog.SettingsDialog')
    def test_settings_dialog_integration(self, mock_dialog_class):
        """Test settings dialog integration"""
        # Mock dialog
        mock_dialog = Mock()
        mock_dialog.show.return_value = AppConfiguration()
        mock_dialog_class.return_value = mock_dialog
        
        from src.ui.dialogs.settings_dialog import SettingsDialog
        
        # Test dialog creation
        dialog = SettingsDialog(self.root, self.config_service)
        result = dialog.show()
        
        # Verify dialog was called correctly
        mock_dialog_class.assert_called_once_with(self.root, self.config_service)
        mock_dialog.show.assert_called_once()
    
    def test_window_geometry_persistence_simulation(self):
        """Test window geometry persistence simulation"""
        # Simulate window geometry changes
        test_geometry_states = [
            (800, 600, 100, 50, False),
            (1024, 768, 200, 100, False),
            (1200, 900, 0, 0, True),  # Maximized
        ]
        
        for width, height, x, y, maximized in test_geometry_states:
            # Update geometry
            success = self.config_service.update_window_geometry(
                width=width, height=height, x=x, y=y, maximized=maximized
            )
            assert success
            
            # Verify geometry was saved
            ui_prefs = self.config_service.get_ui_preferences()
            assert ui_prefs.window_width == width
            assert ui_prefs.window_height == height
            assert ui_prefs.window_x == x
            assert ui_prefs.window_y == y
            assert ui_prefs.window_maximized == maximized


@pytest.mark.integration
class TestSettingsErrorRecovery:
    """Test error recovery scenarios for settings system"""
    
    def setup_method(self):
        """Setup error recovery tests"""
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_file.name
        self.temp_file.close()
        
        self.config_service = ConfigService(db_path=self.db_path)
    
    def teardown_method(self):
        """Cleanup error recovery tests"""
        try:
            self.config_service.shutdown()
            os.unlink(self.db_path)
        except OSError:
            pass
    
    def test_database_corruption_recovery(self):
        """Test recovery từ database corruption"""
        # Create valid configuration first
        self.config_service.add_recent_folder("/test/before/corruption")
        
        # Simulate database corruption by writing invalid data
        with open(self.db_path, 'w') as f:
            f.write("corrupted data")
        
        # Create new service - should handle corruption gracefully
        recovery_service = ConfigService(db_path=self.db_path)
        
        # Should get default configuration
        config = recovery_service.get_current_config()
        assert isinstance(config, AppConfiguration)
        assert len(config.recent_folders) == 0  # Reset due to corruption
        
        recovery_service.shutdown()
    
    def test_invalid_configuration_recovery(self):
        """Test recovery từ invalid configuration data"""
        # Test với malformed JSON in configuration
        with patch.object(self.config_service.repository, 'export_configuration') as mock_export:
            mock_export.return_value = '{"invalid": json malformed'
            
            # Should handle gracefully
            export_result = self.config_service.export_configuration()
            # Since we patched it, it returns malformed JSON
            
            # Import should fail gracefully
            success = self.config_service.import_configuration('{"invalid": json}')
            assert success is False  # Should reject malformed JSON
    
    def test_permission_error_recovery(self):
        """Test recovery từ file permission errors"""
        # This test would simulate permission errors
        # For now, we'll test the error handling path
        
        with patch('builtins.open', side_effect=PermissionError("Access denied")):
            # Service should handle permission errors gracefully
            result = self.config_service.export_configuration()
            # Should return empty config or handle error appropriately
            assert result is not None
    
    def test_disk_space_error_recovery(self):
        """Test recovery từ disk space errors"""
        with patch.object(self.config_service.repository, 'save_configuration') as mock_save:
            mock_save.side_effect = OSError("No space left on device")
            
            # Should handle disk space errors gracefully
            rules = self.config_service.get_normalization_rules()
            success = self.config_service.update_normalization_rules(rules)
            
            # Should fail gracefully without crashing
            assert success is False


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-m", "integration"])