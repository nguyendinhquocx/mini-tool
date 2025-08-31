"""
Settings Panel Component

Lightweight settings panel component for quick access to common settings
from main window toolbar hoặc menu.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable
import logging

from ...core.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class QuickSettingsPanel:
    """
    Quick settings panel for common configuration options
    
    Provides quick access to frequently used settings without
    opening the full settings dialog.
    """
    
    def __init__(self, parent: tk.Widget, config_service: ConfigService):
        """
        Initialize quick settings panel
        
        Args:
            parent: Parent widget
            config_service: Configuration service instance
        """
        self.parent = parent
        self.config_service = config_service
        self.panel = None
        
        # UI components
        self.ui_components = {}
        
        # Change callback
        self.change_callback: Optional[Callable] = None
    
    def create_panel(self, title: str = "Quick Settings") -> ttk.LabelFrame:
        """
        Create và return settings panel widget
        
        Args:
            title: Panel title
            
        Returns:
            Settings panel widget
        """
        self.panel = ttk.LabelFrame(self.parent, text=title)
        self._setup_ui()
        self._load_current_values()
        
        return self.panel
    
    def _setup_ui(self):
        """Setup panel UI components"""
        # Normalization quick toggles
        norm_frame = ttk.Frame(self.panel)
        norm_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(norm_frame, text="Normalization:").pack(side="left")
        
        self.ui_components['remove_diacritics'] = tk.BooleanVar()
        ttk.Checkbutton(
            norm_frame, text="Remove diacritics",
            variable=self.ui_components['remove_diacritics'],
            command=self._on_setting_changed
        ).pack(side="left", padx=(10, 5))
        
        self.ui_components['convert_to_lowercase'] = tk.BooleanVar()
        ttk.Checkbutton(
            norm_frame, text="Lowercase",
            variable=self.ui_components['convert_to_lowercase'],
            command=self._on_setting_changed
        ).pack(side="left", padx=5)
        
        # Operation mode toggle
        mode_frame = ttk.Frame(self.panel)
        mode_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(mode_frame, text="Mode:").pack(side="left")
        
        self.ui_components['dry_run_by_default'] = tk.BooleanVar()
        ttk.Checkbutton(
            mode_frame, text="Dry run (preview only)",
            variable=self.ui_components['dry_run_by_default'],
            command=self._on_setting_changed
        ).pack(side="left", padx=(10, 0))
        
        # Buttons frame
        button_frame = ttk.Frame(self.panel)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(
            button_frame, text="Full Settings...",
            command=self._open_full_settings
        ).pack(side="right")
        
        ttk.Button(
            button_frame, text="Reset",
            command=self._reset_to_defaults
        ).pack(side="right", padx=(0, 5))
    
    def _load_current_values(self):
        """Load current configuration values"""
        try:
            config = self.config_service.get_current_config()
            
            # Load normalization rules
            rules = config.normalization_rules
            self.ui_components['remove_diacritics'].set(rules.remove_diacritics)
            self.ui_components['convert_to_lowercase'].set(rules.convert_to_lowercase)
            
            # Load operation settings
            op_settings = config.operation_settings
            self.ui_components['dry_run_by_default'].set(op_settings.dry_run_by_default)
            
        except Exception as e:
            logger.error(f"Error loading current values: {e}")
    
    def _on_setting_changed(self):
        """Handle setting change"""
        try:
            # Get current configuration
            config = self.config_service.get_current_config()
            
            # Update normalization rules
            config.normalization_rules.remove_diacritics = self.ui_components['remove_diacritics'].get()
            config.normalization_rules.convert_to_lowercase = self.ui_components['convert_to_lowercase'].get()
            
            # Update operation settings
            config.operation_settings.dry_run_by_default = self.ui_components['dry_run_by_default'].get()
            
            # Save configuration
            if self.config_service.update_configuration(config, notify_listeners=True):
                logger.debug("Quick settings updated")
                
                # Call change callback if provided
                if self.change_callback:
                    self.change_callback()
            else:
                logger.error("Failed to update quick settings")
                # Reload values on failure
                self._load_current_values()
                
        except Exception as e:
            logger.error(f"Error updating quick settings: {e}")
            self._load_current_values()
    
    def _reset_to_defaults(self):
        """Reset settings to defaults"""
        try:
            if self.config_service.reset_to_defaults():
                self._load_current_values()
                if self.change_callback:
                    self.change_callback()
        except Exception as e:
            logger.error(f"Error resetting to defaults: {e}")
    
    def _open_full_settings(self):
        """Open full settings dialog"""
        try:
            from ..dialogs.settings_dialog import SettingsDialog
            
            # Find root window
            root = self.panel
            while root.master:
                root = root.master
            
            # Open settings dialog
            dialog = SettingsDialog(root, self.config_service)
            result = dialog.show()
            
            if result:
                # Reload quick settings
                self._load_current_values()
                if self.change_callback:
                    self.change_callback()
                    
        except Exception as e:
            logger.error(f"Error opening full settings: {e}")
    
    def set_change_callback(self, callback: Callable):
        """
        Set callback to be called when settings change
        
        Args:
            callback: Function to call when settings change
        """
        self.change_callback = callback
    
    def refresh(self):
        """Refresh panel với current configuration values"""
        self._load_current_values()
    
    def get_panel(self) -> Optional[ttk.LabelFrame]:
        """
        Get panel widget
        
        Returns:
            Panel widget or None if not created
        """
        return self.panel


class SettingsMenuIntegration:
    """
    Helper class for integrating settings into application menu
    """
    
    def __init__(self, config_service: ConfigService):
        """
        Initialize settings menu integration
        
        Args:
            config_service: Configuration service instance
        """
        self.config_service = config_service
    
    def add_settings_menu(self, menubar: tk.Menu, parent_window: tk.Tk):
        """
        Add settings menu to menubar
        
        Args:
            menubar: Main application menubar
            parent_window: Parent window for dialogs
        """
        try:
            # Create settings menu
            settings_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Settings", menu=settings_menu)
            
            # Add menu items
            settings_menu.add_command(
                label="Preferences...", 
                command=lambda: self._open_settings_dialog(parent_window),
                accelerator="Ctrl+,"
            )
            
            settings_menu.add_separator()
            
            # Quick toggle options
            settings_menu.add_checkbutton(
                label="Remove Diacritics",
                command=lambda: self._toggle_normalization_rule('remove_diacritics')
            )
            
            settings_menu.add_checkbutton(
                label="Convert to Lowercase", 
                command=lambda: self._toggle_normalization_rule('convert_to_lowercase')
            )
            
            settings_menu.add_separator()
            
            settings_menu.add_checkbutton(
                label="Dry Run Mode",
                command=lambda: self._toggle_operation_setting('dry_run_by_default')
            )
            
            settings_menu.add_separator()
            
            # Recent folders submenu
            recent_menu = tk.Menu(settings_menu, tearoff=0)
            settings_menu.add_cascade(label="Recent Folders", menu=recent_menu)
            
            self._populate_recent_folders_menu(recent_menu)
            
            settings_menu.add_separator()
            
            settings_menu.add_command(
                label="Reset to Defaults",
                command=self._reset_to_defaults
            )
            
            # Bind keyboard shortcut
            parent_window.bind('<Control-comma>', 
                             lambda e: self._open_settings_dialog(parent_window))
            
        except Exception as e:
            logger.error(f"Error adding settings menu: {e}")
    
    def _open_settings_dialog(self, parent_window: tk.Tk):
        """Open full settings dialog"""
        try:
            from ..dialogs.settings_dialog import SettingsDialog
            
            dialog = SettingsDialog(parent_window, self.config_service)
            dialog.show()
            
        except Exception as e:
            logger.error(f"Error opening settings dialog: {e}")
    
    def _toggle_normalization_rule(self, rule_name: str):
        """Toggle normalization rule"""
        try:
            config = self.config_service.get_current_config()
            current_value = getattr(config.normalization_rules, rule_name)
            setattr(config.normalization_rules, rule_name, not current_value)
            
            self.config_service.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Error toggling normalization rule '{rule_name}': {e}")
    
    def _toggle_operation_setting(self, setting_name: str):
        """Toggle operation setting"""
        try:
            config = self.config_service.get_current_config()
            current_value = getattr(config.operation_settings, setting_name)
            setattr(config.operation_settings, setting_name, not current_value)
            
            self.config_service.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Error toggling operation setting '{setting_name}': {e}")
    
    def _populate_recent_folders_menu(self, menu: tk.Menu):
        """Populate recent folders menu"""
        try:
            # Clear existing items
            menu.delete(0, tk.END)
            
            recent_folders = self.config_service.get_recent_folders()
            
            if not recent_folders:
                menu.add_command(label="(No recent folders)", state="disabled")
                return
            
            # Add recent folders (limit to 10 most recent)
            for i, folder_path in enumerate(recent_folders[:10]):
                # Truncate long paths for display
                display_path = folder_path
                if len(display_path) > 50:
                    display_path = "..." + display_path[-47:]
                
                menu.add_command(
                    label=f"{i+1}. {display_path}",
                    command=lambda path=folder_path: self._select_recent_folder(path)
                )
            
            menu.add_separator()
            menu.add_command(
                label="Clear Recent Folders",
                command=self._clear_recent_folders
            )
            
        except Exception as e:
            logger.error(f"Error populating recent folders menu: {e}")
    
    def _select_recent_folder(self, folder_path: str):
        """Select recent folder (to be implemented by application)"""
        logger.info(f"Recent folder selected: {folder_path}")
        # This would be connected to main application folder selection
    
    def _clear_recent_folders(self):
        """Clear recent folders list"""
        try:
            config = self.config_service.get_current_config()
            config.recent_folders.clear()
            self.config_service.update_configuration(config)
            
        except Exception as e:
            logger.error(f"Error clearing recent folders: {e}")
    
    def _reset_to_defaults(self):
        """Reset configuration to defaults"""
        try:
            self.config_service.reset_to_defaults()
        except Exception as e:
            logger.error(f"Error resetting to defaults: {e}")


# Example usage
if __name__ == "__main__":
    def test_settings_panel():
        """Test settings panel"""
        import tempfile
        import os
        from ...core.services.config_service import ConfigService
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Create test window
            root = tk.Tk()
            root.title("Settings Panel Test")
            root.geometry("400x200")
            
            # Create config service
            config_service = ConfigService(db_path=db_path)
            
            # Create settings panel
            panel_component = QuickSettingsPanel(root, config_service)
            panel = panel_component.create_panel()
            panel.pack(fill="x", padx=10, pady=10)
            
            # Create menubar with settings
            menubar = tk.Menu(root)
            root.config(menu=menubar)
            
            menu_integration = SettingsMenuIntegration(config_service)
            menu_integration.add_settings_menu(menubar, root)
            
            # Run
            root.mainloop()
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    # Uncomment to test
    # test_settings_panel()