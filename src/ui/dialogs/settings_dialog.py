"""
Settings Dialog

Main settings dialog với tabbed interface for configuring application preferences,
normalization rules, operation settings, và UI preferences.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional, Dict, Any, Callable, List
import logging

from ...core.services.config_service import ConfigService
from ...core.models.config import (
    AppConfiguration, NormalizationRulesConfig, 
    UIPreferences, OperationSettings
)

logger = logging.getLogger(__name__)


class SettingsDialog:
    """
    Main settings dialog với tabbed interface
    
    Provides user-friendly interface for configuring:
    - Normalization rules
    - UI preferences  
    - Operation settings
    - Recent folders management
    """
    
    def __init__(self, parent: tk.Tk, config_service: ConfigService):
        """
        Initialize settings dialog
        
        Args:
            parent: Parent window
            config_service: Configuration service instance
        """
        self.parent = parent
        self.config_service = config_service
        self.dialog = None
        self.notebook = None
        
        # Current configuration (working copy)
        self.current_config = self.config_service.get_current_config()
        self.working_config = None
        
        # UI components references
        self.ui_components = {}
        
        # Change tracking
        self.has_changes = False
        self.change_callbacks = []
        
        # Result
        self.result = None
    
    def show(self) -> Optional[AppConfiguration]:
        """
        Show settings dialog modally
        
        Returns:
            Updated configuration if applied, None if cancelled
        """
        self._create_dialog()
        self._setup_ui()
        self._load_current_values()
        
        # Center dialog on parent
        self._center_dialog()
        
        # Make modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Wait for dialog to close
        self.parent.wait_window(self.dialog)
        
        return self.result
    
    def _create_dialog(self):
        """Create main dialog window"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Settings")
        self.dialog.geometry("600x500")
        self.dialog.minsize(550, 450)
        self.dialog.resizable(True, True)
        
        # Handle window close
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
    
    def _setup_ui(self):
        """Setup dialog UI components"""
        # Main container
        main_frame = ttk.Frame(self.dialog)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create tabbed notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        
        # Create tabs
        self._create_normalization_tab()
        self._create_ui_preferences_tab()
        self._create_operation_settings_tab()
        self._create_recent_folders_tab()
        self._create_advanced_tab()
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, sticky="ew")
        
        # Buttons
        ttk.Button(
            button_frame, text="Reset to Defaults", 
            command=self._on_reset_defaults
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            button_frame, text="Import...", 
            command=self._on_import_config
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            button_frame, text="Export...", 
            command=self._on_export_config
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        # Right-aligned buttons
        ttk.Button(
            button_frame, text="Cancel", 
            command=self._on_cancel
        ).pack(side=tk.RIGHT)
        
        ttk.Button(
            button_frame, text="OK", 
            command=self._on_ok
        ).pack(side=tk.RIGHT, padx=(0, 10))
        
        ttk.Button(
            button_frame, text="Apply", 
            command=self._on_apply
        ).pack(side=tk.RIGHT, padx=(0, 5))
    
    def _create_normalization_tab(self):
        """Create normalization rules configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Normalization Rules")
        
        # Scrollable frame
        canvas = tk.Canvas(tab)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Normalization options
        rules_frame = ttk.LabelFrame(scrollable_frame, text="Text Processing Rules")
        rules_frame.pack(fill="x", padx=10, pady=5)
        
        self.ui_components['remove_diacritics'] = tk.BooleanVar()
        ttk.Checkbutton(
            rules_frame, text="Remove Vietnamese diacritics (ủ → u, đ → d)",
            variable=self.ui_components['remove_diacritics'],
            command=self._on_setting_changed
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['convert_to_lowercase'] = tk.BooleanVar()
        ttk.Checkbutton(
            rules_frame, text="Convert to lowercase",
            variable=self.ui_components['convert_to_lowercase'],
            command=self._on_setting_changed
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['clean_special_characters'] = tk.BooleanVar()
        ttk.Checkbutton(
            rules_frame, text="Clean special characters",
            variable=self.ui_components['clean_special_characters'],
            command=self._on_setting_changed
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['normalize_whitespace'] = tk.BooleanVar()
        ttk.Checkbutton(
            rules_frame, text="Normalize whitespace",
            variable=self.ui_components['normalize_whitespace'],
            command=self._on_setting_changed
        ).pack(anchor="w", padx=10, pady=2)
        
        # File handling options
        file_frame = ttk.LabelFrame(scrollable_frame, text="File Handling")
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.ui_components['preserve_extensions'] = tk.BooleanVar()
        ttk.Checkbutton(
            file_frame, text="Preserve file extensions",
            variable=self.ui_components['preserve_extensions'],
            command=self._on_setting_changed
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['preserve_numbers'] = tk.BooleanVar()
        ttk.Checkbutton(
            file_frame, text="Preserve numbers in filenames",
            variable=self.ui_components['preserve_numbers'],
            command=self._on_setting_changed
        ).pack(anchor="w", padx=10, pady=2)
        
        # Filename length limits
        limits_frame = ttk.LabelFrame(scrollable_frame, text="Filename Length Limits")
        limits_frame.pack(fill="x", padx=10, pady=5)
        
        # Max filename length
        max_length_frame = ttk.Frame(limits_frame)
        max_length_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(max_length_frame, text="Maximum filename length:").pack(side="left")
        self.ui_components['max_filename_length'] = tk.StringVar()
        max_length_entry = ttk.Entry(
            max_length_frame, textvariable=self.ui_components['max_filename_length'],
            width=10
        )
        max_length_entry.pack(side="left", padx=(10, 5))
        max_length_entry.bind('<KeyRelease>', lambda e: self._on_setting_changed())
        ttk.Label(max_length_frame, text="characters").pack(side="left")
        
        # Custom replacements section
        custom_frame = ttk.LabelFrame(scrollable_frame, text="Custom Character Replacements")
        custom_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Custom replacements will be implemented in separate method
        self._create_custom_replacements_ui(custom_frame)
        
        # Preview section
        preview_frame = ttk.LabelFrame(scrollable_frame, text="Preview")
        preview_frame.pack(fill="x", padx=10, pady=5)
        
        preview_input_frame = ttk.Frame(preview_frame)
        preview_input_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(preview_input_frame, text="Test text:").pack(side="left")
        self.ui_components['preview_input'] = tk.StringVar(value="Tệp tiếng Việt - Test File.txt")
        preview_entry = ttk.Entry(
            preview_input_frame, textvariable=self.ui_components['preview_input'],
            width=30
        )
        preview_entry.pack(side="left", fill="x", expand=True, padx=(10, 5))
        preview_entry.bind('<KeyRelease>', lambda e: self._update_preview())
        
        ttk.Button(
            preview_input_frame, text="Update Preview",
            command=self._update_preview
        ).pack(side="right")
        
        # Preview result
        self.ui_components['preview_result'] = tk.StringVar()
        result_frame = ttk.Frame(preview_frame)
        result_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(result_frame, text="Result:").pack(side="left")
        ttk.Label(
            result_frame, textvariable=self.ui_components['preview_result'],
            foreground="blue", font=("Arial", 10, "bold")
        ).pack(side="left", padx=(10, 0))
    
    def _create_custom_replacements_ui(self, parent):
        """Create custom character replacements UI"""
        # Custom replacements listbox với add/remove functionality
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Listbox với scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True)
        
        self.ui_components['custom_replacements_listbox'] = tk.Listbox(list_container, height=6)
        replacements_scrollbar = ttk.Scrollbar(list_container, orient="vertical")
        
        self.ui_components['custom_replacements_listbox'].configure(
            yscrollcommand=replacements_scrollbar.set
        )
        replacements_scrollbar.configure(
            command=self.ui_components['custom_replacements_listbox'].yview
        )
        
        self.ui_components['custom_replacements_listbox'].pack(
            side="left", fill="both", expand=True
        )
        replacements_scrollbar.pack(side="right", fill="y")
        
        # Add/Remove buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill="x", pady=(5, 0))
        
        ttk.Button(
            button_frame, text="Add Replacement", 
            command=self._add_custom_replacement
        ).pack(side="left")
        
        ttk.Button(
            button_frame, text="Edit Selected", 
            command=self._edit_custom_replacement
        ).pack(side="left", padx=(5, 0))
        
        ttk.Button(
            button_frame, text="Remove Selected", 
            command=self._remove_custom_replacement
        ).pack(side="left", padx=(5, 0))
        
        # Store custom replacements data
        self.custom_replacements_data = {}
    
    def _create_ui_preferences_tab(self):
        """Create UI preferences configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="UI Preferences")
        
        # Window settings
        window_frame = ttk.LabelFrame(tab, text="Window Settings")
        window_frame.pack(fill="x", padx=10, pady=5)
        
        # Default window size
        size_frame = ttk.Frame(window_frame)
        size_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(size_frame, text="Default window size:").grid(row=0, column=0, sticky="w")
        
        self.ui_components['window_width'] = tk.StringVar()
        ttk.Entry(
            size_frame, textvariable=self.ui_components['window_width'], width=8
        ).grid(row=0, column=1, padx=(10, 5), sticky="w")
        
        ttk.Label(size_frame, text="×").grid(row=0, column=2)
        
        self.ui_components['window_height'] = tk.StringVar()
        ttk.Entry(
            size_frame, textvariable=self.ui_components['window_height'], width=8
        ).grid(row=0, column=3, padx=(5, 5), sticky="w")
        
        ttk.Label(size_frame, text="pixels").grid(row=0, column=4, sticky="w")
        
        # Font settings
        font_frame = ttk.LabelFrame(tab, text="Font Settings")
        font_frame.pack(fill="x", padx=10, pady=5)
        
        font_config_frame = ttk.Frame(font_frame)
        font_config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(font_config_frame, text="Font family:").grid(row=0, column=0, sticky="w")
        self.ui_components['font_family'] = ttk.Combobox(
            font_config_frame, values=["Arial", "Helvetica", "Times New Roman", "Courier New"],
            state="readonly", width=15
        )
        self.ui_components['font_family'].grid(row=0, column=1, padx=(10, 20), sticky="w")
        
        ttk.Label(font_config_frame, text="Size:").grid(row=0, column=2, sticky="w")
        self.ui_components['font_size'] = ttk.Combobox(
            font_config_frame, values=["8", "9", "10", "11", "12", "14", "16"],
            state="readonly", width=5
        )
        self.ui_components['font_size'].grid(row=0, column=3, padx=(10, 0), sticky="w")
        
        # Theme settings
        theme_frame = ttk.LabelFrame(tab, text="Appearance")
        theme_frame.pack(fill="x", padx=10, pady=5)
        
        theme_config_frame = ttk.Frame(theme_frame)
        theme_config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(theme_config_frame, text="Theme:").pack(side="left")
        self.ui_components['theme'] = ttk.Combobox(
            theme_config_frame, values=["default", "light", "dark"],
            state="readonly", width=15
        )
        self.ui_components['theme'].pack(side="left", padx=(10, 0))
        
        # Confirmation settings
        confirm_frame = ttk.LabelFrame(tab, text="Confirmation Dialogs")
        confirm_frame.pack(fill="x", padx=10, pady=5)
        
        self.ui_components['confirm_operations'] = tk.BooleanVar()
        ttk.Checkbutton(
            confirm_frame, text="Confirm file operations",
            variable=self.ui_components['confirm_operations']
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['confirm_reset'] = tk.BooleanVar()
        ttk.Checkbutton(
            confirm_frame, text="Confirm settings reset",
            variable=self.ui_components['confirm_reset']
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['show_preview_dialog'] = tk.BooleanVar()
        ttk.Checkbutton(
            confirm_frame, text="Show preview dialog before operations",
            variable=self.ui_components['show_preview_dialog']
        ).pack(anchor="w", padx=10, pady=2)
    
    def _create_operation_settings_tab(self):
        """Create operation settings configuration tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Operations")
        
        # Default behavior
        behavior_frame = ttk.LabelFrame(tab, text="Default Behavior")
        behavior_frame.pack(fill="x", padx=10, pady=5)
        
        self.ui_components['dry_run_by_default'] = tk.BooleanVar()
        ttk.Checkbutton(
            behavior_frame, text="Enable dry run mode by default (preview only)",
            variable=self.ui_components['dry_run_by_default']
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['create_backups'] = tk.BooleanVar()
        ttk.Checkbutton(
            behavior_frame, text="Create backups before renaming files",
            variable=self.ui_components['create_backups']
        ).pack(anchor="w", padx=10, pady=2)
        
        # Safety settings
        safety_frame = ttk.LabelFrame(tab, text="Safety Settings")
        safety_frame.pack(fill="x", padx=10, pady=5)
        
        self.ui_components['skip_hidden_files'] = tk.BooleanVar()
        ttk.Checkbutton(
            safety_frame, text="Skip hidden files",
            variable=self.ui_components['skip_hidden_files']
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['skip_system_files'] = tk.BooleanVar()
        ttk.Checkbutton(
            safety_frame, text="Skip system files",
            variable=self.ui_components['skip_system_files']
        ).pack(anchor="w", padx=10, pady=2)
        
        self.ui_components['require_confirmation_for_large_operations'] = tk.BooleanVar()
        ttk.Checkbutton(
            safety_frame, text="Require confirmation for large operations",
            variable=self.ui_components['require_confirmation_for_large_operations']
        ).pack(anchor="w", padx=10, pady=2)
        
        # Large operation threshold
        threshold_frame = ttk.Frame(safety_frame)
        threshold_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(threshold_frame, text="Large operation threshold:").pack(side="left")
        self.ui_components['large_operation_threshold'] = tk.StringVar()
        ttk.Entry(
            threshold_frame, textvariable=self.ui_components['large_operation_threshold'],
            width=8
        ).pack(side="left", padx=(10, 5))
        ttk.Label(threshold_frame, text="files").pack(side="left")
    
    def _create_recent_folders_tab(self):
        """Create recent folders management tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Recent Folders")
        
        # Recent folders settings
        settings_frame = ttk.LabelFrame(tab, text="Recent Folders Settings")
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        max_folders_frame = ttk.Frame(settings_frame)
        max_folders_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(max_folders_frame, text="Maximum recent folders:").pack(side="left")
        self.ui_components['max_recent_folders'] = tk.StringVar()
        ttk.Entry(
            max_folders_frame, textvariable=self.ui_components['max_recent_folders'],
            width=8
        ).pack(side="left", padx=(10, 5))
        
        self.ui_components['recent_folders_in_menu'] = tk.BooleanVar()
        ttk.Checkbutton(
            settings_frame, text="Show recent folders in main menu",
            variable=self.ui_components['recent_folders_in_menu']
        ).pack(anchor="w", padx=10, pady=5)
        
        # Recent folders list
        list_frame = ttk.LabelFrame(tab, text="Recent Folders List")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Listbox với scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.ui_components['recent_folders_listbox'] = tk.Listbox(list_container)
        folders_scrollbar = ttk.Scrollbar(list_container, orient="vertical")
        
        self.ui_components['recent_folders_listbox'].configure(
            yscrollcommand=folders_scrollbar.set
        )
        folders_scrollbar.configure(
            command=self.ui_components['recent_folders_listbox'].yview
        )
        
        self.ui_components['recent_folders_listbox'].pack(
            side="left", fill="both", expand=True
        )
        folders_scrollbar.pack(side="right", fill="y")
        
        # Management buttons
        button_frame = ttk.Frame(list_frame)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ttk.Button(
            button_frame, text="Remove Selected",
            command=self._remove_recent_folder
        ).pack(side="left")
        
        ttk.Button(
            button_frame, text="Clear All",
            command=self._clear_recent_folders
        ).pack(side="left", padx=(10, 0))
        
        ttk.Button(
            button_frame, text="Clean Non-existing",
            command=self._clean_recent_folders
        ).pack(side="left", padx=(10, 0))
    
    def _create_advanced_tab(self):
        """Create advanced settings tab"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Advanced")
        
        # Configuration management
        config_frame = ttk.LabelFrame(tab, text="Configuration Management")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        # Configuration info
        info_frame = ttk.Frame(config_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        self.ui_components['config_info'] = tk.StringVar()
        ttk.Label(
            info_frame, textvariable=self.ui_components['config_info'],
            font=("Arial", 9)
        ).pack(anchor="w")
        
        # Backup management
        backup_frame = ttk.LabelFrame(tab, text="Configuration Backups")
        backup_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Backups list
        backup_list_frame = ttk.Frame(backup_frame)
        backup_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.ui_components['backups_listbox'] = tk.Listbox(backup_list_frame, height=8)
        backup_scrollbar = ttk.Scrollbar(backup_list_frame, orient="vertical")
        
        self.ui_components['backups_listbox'].configure(
            yscrollcommand=backup_scrollbar.set
        )
        backup_scrollbar.configure(
            command=self.ui_components['backups_listbox'].yview
        )
        
        self.ui_components['backups_listbox'].pack(
            side="left", fill="both", expand=True
        )
        backup_scrollbar.pack(side="right", fill="y")
        
        # Backup management buttons
        backup_button_frame = ttk.Frame(backup_frame)
        backup_button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        ttk.Button(
            backup_button_frame, text="Create Backup",
            command=self._create_backup
        ).pack(side="left")
        
        ttk.Button(
            backup_button_frame, text="Restore Selected",
            command=self._restore_backup
        ).pack(side="left", padx=(10, 0))
        
        ttk.Button(
            backup_button_frame, text="Delete Selected",
            command=self._delete_backup
        ).pack(side="left", padx=(10, 0))
        
        ttk.Button(
            backup_button_frame, text="Refresh List",
            command=self._refresh_backups_list
        ).pack(side="right")
    
    def _load_current_values(self):
        """Load current configuration values into UI components"""
        try:
            config = self.current_config
            
            # Normalization rules
            rules = config.normalization_rules
            self.ui_components['remove_diacritics'].set(rules.remove_diacritics)
            self.ui_components['convert_to_lowercase'].set(rules.convert_to_lowercase)
            self.ui_components['clean_special_characters'].set(rules.clean_special_characters)
            self.ui_components['normalize_whitespace'].set(rules.normalize_whitespace)
            self.ui_components['preserve_extensions'].set(rules.preserve_extensions)
            self.ui_components['preserve_numbers'].set(rules.preserve_numbers)
            self.ui_components['max_filename_length'].set(str(rules.max_filename_length))
            
            # Load custom replacements
            self._load_custom_replacements(rules.custom_replacements)
            
            # UI preferences
            ui_prefs = config.ui_preferences
            self.ui_components['window_width'].set(str(ui_prefs.window_width))
            self.ui_components['window_height'].set(str(ui_prefs.window_height))
            self.ui_components['font_family'].set(ui_prefs.font_family)
            self.ui_components['font_size'].set(str(ui_prefs.font_size))
            self.ui_components['theme'].set(ui_prefs.theme)
            self.ui_components['confirm_operations'].set(ui_prefs.confirm_operations)
            self.ui_components['confirm_reset'].set(ui_prefs.confirm_reset)
            self.ui_components['show_preview_dialog'].set(ui_prefs.show_preview_dialog)
            self.ui_components['max_recent_folders'].set(str(ui_prefs.max_recent_folders))
            self.ui_components['recent_folders_in_menu'].set(ui_prefs.recent_folders_in_menu)
            
            # Operation settings
            op_settings = config.operation_settings
            self.ui_components['dry_run_by_default'].set(op_settings.dry_run_by_default)
            self.ui_components['create_backups'].set(op_settings.create_backups)
            self.ui_components['skip_hidden_files'].set(op_settings.skip_hidden_files)
            self.ui_components['skip_system_files'].set(op_settings.skip_system_files)
            self.ui_components['require_confirmation_for_large_operations'].set(
                op_settings.require_confirmation_for_large_operations
            )
            self.ui_components['large_operation_threshold'].set(str(op_settings.large_operation_threshold))
            
            # Recent folders list
            self._load_recent_folders_list()
            
            # Configuration info
            self._update_config_info()
            
            # Backups list
            self._refresh_backups_list()
            
            # Update preview
            self._update_preview()
            
        except Exception as e:
            logger.error(f"Error loading current values: {e}")
            messagebox.showerror("Error", f"Failed to load settings: {str(e)}")
    
    def _load_custom_replacements(self, replacements: Dict[str, str]):
        """Load custom replacements into listbox"""
        self.custom_replacements_data = replacements.copy()
        listbox = self.ui_components['custom_replacements_listbox']
        listbox.delete(0, tk.END)
        
        for char, replacement in replacements.items():
            display_text = f"'{char}' → '{replacement}'"
            listbox.insert(tk.END, display_text)
    
    def _load_recent_folders_list(self):
        """Load recent folders into listbox"""
        listbox = self.ui_components['recent_folders_listbox']
        listbox.delete(0, tk.END)
        
        for folder in self.current_config.recent_folders:
            display_text = f"{folder.display_name} ({folder.path})"
            listbox.insert(tk.END, display_text)
    
    def _update_config_info(self):
        """Update configuration information display"""
        try:
            info = self.config_service.get_service_info()
            config = self.current_config
            
            info_text = (
                f"Configuration Version: {config.version}\n"
                f"Last Updated: {config.last_updated.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Recent Folders: {len(config.recent_folders)}\n"
                f"Database: {info.get('repository_info', {}).get('database_path', 'Unknown')}"
            )
            
            self.ui_components['config_info'].set(info_text)
            
        except Exception as e:
            logger.error(f"Error updating config info: {e}")
            self.ui_components['config_info'].set("Configuration info unavailable")
    
    def _refresh_backups_list(self):
        """Refresh configuration backups list"""
        try:
            listbox = self.ui_components['backups_listbox']
            listbox.delete(0, tk.END)
            
            backups = self.config_service.list_backups()
            for backup in backups:
                display_text = f"{backup['timestamp']} - {backup['created_at']}"
                listbox.insert(tk.END, display_text)
                
        except Exception as e:
            logger.error(f"Error refreshing backups list: {e}")
    
    def _center_dialog(self):
        """Center dialog on parent window"""
        self.dialog.update_idletasks()
        
        # Get parent window position và size
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        # Get dialog size
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        
        # Calculate center position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
    
    def _on_setting_changed(self):
        """Handle setting change"""
        self.has_changes = True
        self._update_preview()
    
    def _update_preview(self):
        """Update normalization preview"""
        try:
            # Get current rules from UI
            rules = self._get_normalization_rules_from_ui()
            
            # Get test text
            test_text = self.ui_components['preview_input'].get()
            
            if not test_text:
                self.ui_components['preview_result'].set("")
                return
            
            # Apply normalization (simplified preview)
            from ...core.services.normalize_service import VietnameseNormalizer
            normalizer = VietnameseNormalizer(rules)
            
            result = normalizer.normalize_filename(test_text)
            self.ui_components['preview_result'].set(result)
            
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.ui_components['preview_result'].set("Preview error")
    
    def _get_normalization_rules_from_ui(self) -> NormalizationRulesConfig:
        """Get normalization rules from UI components"""
        try:
            max_length = int(self.ui_components['max_filename_length'].get() or "255")
        except ValueError:
            max_length = 255
        
        return NormalizationRulesConfig(
            remove_diacritics=self.ui_components['remove_diacritics'].get(),
            convert_to_lowercase=self.ui_components['convert_to_lowercase'].get(),
            clean_special_characters=self.ui_components['clean_special_characters'].get(),
            normalize_whitespace=self.ui_components['normalize_whitespace'].get(),
            preserve_extensions=self.ui_components['preserve_extensions'].get(),
            preserve_numbers=self.ui_components['preserve_numbers'].get(),
            max_filename_length=max_length,
            custom_replacements=self.custom_replacements_data.copy()
        )
    
    def _get_ui_preferences_from_ui(self) -> UIPreferences:
        """Get UI preferences from UI components"""
        try:
            width = int(self.ui_components['window_width'].get() or "600")
            height = int(self.ui_components['window_height'].get() or "500")
            font_size = int(self.ui_components['font_size'].get() or "10")
            max_folders = int(self.ui_components['max_recent_folders'].get() or "10")
        except ValueError as e:
            logger.warning(f"Invalid UI preferences values: {e}")
            width, height, font_size, max_folders = 600, 500, 10, 10
        
        return UIPreferences(
            window_width=width,
            window_height=height,
            font_family=self.ui_components['font_family'].get() or "Arial",
            font_size=font_size,
            theme=self.ui_components['theme'].get() or "default",
            confirm_operations=self.ui_components['confirm_operations'].get(),
            confirm_reset=self.ui_components['confirm_reset'].get(),
            show_preview_dialog=self.ui_components['show_preview_dialog'].get(),
            max_recent_folders=max_folders,
            recent_folders_in_menu=self.ui_components['recent_folders_in_menu'].get()
        )
    
    def _get_operation_settings_from_ui(self) -> OperationSettings:
        """Get operation settings from UI components"""
        try:
            threshold = int(self.ui_components['large_operation_threshold'].get() or "100")
        except ValueError:
            threshold = 100
        
        return OperationSettings(
            dry_run_by_default=self.ui_components['dry_run_by_default'].get(),
            create_backups=self.ui_components['create_backups'].get(),
            skip_hidden_files=self.ui_components['skip_hidden_files'].get(),
            skip_system_files=self.ui_components['skip_system_files'].get(),
            require_confirmation_for_large_operations=self.ui_components['require_confirmation_for_large_operations'].get(),
            large_operation_threshold=threshold
        )
    
    def _get_updated_configuration(self) -> AppConfiguration:
        """Get updated configuration from all UI components"""
        config = self.current_config
        
        # Update với values từ UI
        config.normalization_rules = self._get_normalization_rules_from_ui()
        config.ui_preferences = self._get_ui_preferences_from_ui()
        config.operation_settings = self._get_operation_settings_from_ui()
        
        return config
    
    def _add_custom_replacement(self):
        """Add new custom character replacement"""
        dialog = CustomReplacementDialog(self.dialog)
        result = dialog.show()
        
        if result:
            char, replacement = result
            if char in self.custom_replacements_data:
                if not messagebox.askyesno(
                    "Replace Existing",
                    f"Replacement for '{char}' already exists. Replace it?"
                ):
                    return
            
            self.custom_replacements_data[char] = replacement
            self._load_custom_replacements(self.custom_replacements_data)
            self._on_setting_changed()
    
    def _edit_custom_replacement(self):
        """Edit selected custom replacement"""
        listbox = self.ui_components['custom_replacements_listbox']
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a replacement to edit.")
            return
        
        # Get selected replacement
        index = selection[0]
        replacements_list = list(self.custom_replacements_data.items())
        char, replacement = replacements_list[index]
        
        dialog = CustomReplacementDialog(self.dialog, char, replacement)
        result = dialog.show()
        
        if result:
            new_char, new_replacement = result
            
            # Remove old mapping
            del self.custom_replacements_data[char]
            
            # Add new mapping
            self.custom_replacements_data[new_char] = new_replacement
            
            self._load_custom_replacements(self.custom_replacements_data)
            self._on_setting_changed()
    
    def _remove_custom_replacement(self):
        """Remove selected custom replacement"""
        listbox = self.ui_components['custom_replacements_listbox']
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a replacement to remove.")
            return
        
        index = selection[0]
        replacements_list = list(self.custom_replacements_data.items())
        char, replacement = replacements_list[index]
        
        if messagebox.askyesno(
            "Confirm Removal", 
            f"Remove replacement '{char}' → '{replacement}'?"
        ):
            del self.custom_replacements_data[char]
            self._load_custom_replacements(self.custom_replacements_data)
            self._on_setting_changed()
    
    def _remove_recent_folder(self):
        """Remove selected recent folder"""
        listbox = self.ui_components['recent_folders_listbox']
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a folder to remove.")
            return
        
        index = selection[0]
        folder = self.current_config.recent_folders[index]
        
        if messagebox.askyesno(
            "Confirm Removal",
            f"Remove '{folder.display_name}' từ recent folders?"
        ):
            del self.current_config.recent_folders[index]
            self._load_recent_folders_list()
            self._on_setting_changed()
    
    def _clear_recent_folders(self):
        """Clear all recent folders"""
        if not self.current_config.recent_folders:
            messagebox.showinfo("No Folders", "Recent folders list is already empty.")
            return
        
        if messagebox.askyesno(
            "Confirm Clear All",
            f"Remove all {len(self.current_config.recent_folders)} recent folders?"
        ):
            self.current_config.recent_folders.clear()
            self._load_recent_folders_list()
            self._on_setting_changed()
    
    def _clean_recent_folders(self):
        """Clean non-existing recent folders"""
        removed_count = self.current_config.clean_recent_folders()
        
        if removed_count > 0:
            self._load_recent_folders_list()
            self._on_setting_changed()
            messagebox.showinfo("Cleaned", f"Removed {removed_count} non-existing folders.")
        else:
            messagebox.showinfo("No Changes", "All recent folders still exist.")
    
    def _create_backup(self):
        """Create configuration backup"""
        try:
            if self.config_service.backup_configuration():
                self._refresh_backups_list()
                messagebox.showinfo("Success", "Configuration backup created successfully.")
            else:
                messagebox.showerror("Error", "Failed to create configuration backup.")
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            messagebox.showerror("Error", f"Failed to create backup: {str(e)}")
    
    def _restore_backup(self):
        """Restore selected configuration backup"""
        listbox = self.ui_components['backups_listbox']
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showwarning("No Selection", "Please select a backup to restore.")
            return
        
        backups = self.config_service.list_backups()
        if not backups or selection[0] >= len(backups):
            messagebox.showerror("Error", "Invalid backup selection.")
            return
        
        backup = backups[selection[0]]
        
        if messagebox.askyesno(
            "Confirm Restore",
            f"Restore configuration từ backup {backup['timestamp']}?\n\n"
            "This will replace current settings."
        ):
            try:
                if self.config_service.restore_backup(backup['name']):
                    # Reload current configuration
                    self.current_config = self.config_service.get_current_config()
                    self._load_current_values()
                    self._on_setting_changed()
                    messagebox.showinfo("Success", "Configuration restored successfully.")
                else:
                    messagebox.showerror("Error", "Failed to restore configuration backup.")
            except Exception as e:
                logger.error(f"Error restoring backup: {e}")
                messagebox.showerror("Error", f"Failed to restore backup: {str(e)}")
    
    def _delete_backup(self):
        """Delete selected configuration backup"""
        messagebox.showinfo("Not Implemented", "Backup deletion feature coming soon.")
    
    def _on_reset_defaults(self):
        """Reset settings to defaults"""
        if messagebox.askyesno(
            "Confirm Reset",
            "Reset all settings to default values?\n\nThis action cannot be undone."
        ):
            try:
                # Create backup before reset
                self.config_service.backup_configuration()
                
                # Reset configuration
                default_config = self.config_service.reset_to_defaults()
                
                # Update current configuration
                self.current_config = default_config
                
                # Reload UI values
                self._load_current_values()
                self._on_setting_changed()
                
                messagebox.showinfo("Success", "Settings reset to defaults successfully.")
                
            except Exception as e:
                logger.error(f"Error resetting to defaults: {e}")
                messagebox.showerror("Error", f"Failed to reset settings: {str(e)}")
    
    def _on_import_config(self):
        """Import configuration từ file"""
        file_path = filedialog.askopenfilename(
            title="Import Configuration",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.dialog
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_str = f.read()
                
                if self.config_service.import_configuration(json_str):
                    # Reload current configuration
                    self.current_config = self.config_service.get_current_config()
                    self._load_current_values()
                    self._on_setting_changed()
                    messagebox.showinfo("Success", "Configuration imported successfully.")
                else:
                    messagebox.showerror("Error", "Failed to import configuration.")
                    
            except Exception as e:
                logger.error(f"Error importing config: {e}")
                messagebox.showerror("Error", f"Failed to import configuration: {str(e)}")
    
    def _on_export_config(self):
        """Export configuration to file"""
        file_path = filedialog.asksaveasfilename(
            title="Export Configuration",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self.dialog
        )
        
        if file_path:
            try:
                json_str = self.config_service.export_configuration()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_str)
                
                messagebox.showinfo("Success", f"Configuration exported to {file_path}")
                
            except Exception as e:
                logger.error(f"Error exporting config: {e}")
                messagebox.showerror("Error", f"Failed to export configuration: {str(e)}")
    
    def _on_apply(self):
        """Apply current settings"""
        try:
            # Get updated configuration
            updated_config = self._get_updated_configuration()
            
            # Validate configuration
            is_valid, errors, warnings = updated_config.validate()
            
            if not is_valid:
                messagebox.showerror(
                    "Invalid Settings",
                    "Cannot apply settings:\n\n" + "\n".join(errors)
                )
                return
            
            if warnings:
                if not messagebox.askyesno(
                    "Settings Warnings",
                    "Settings have warnings:\n\n" + "\n".join(warnings) + "\n\nApply anyway?"
                ):
                    return
            
            # Apply configuration
            if self.config_service.update_configuration(updated_config):
                self.current_config = updated_config
                self.has_changes = False
                messagebox.showinfo("Success", "Settings applied successfully.")
            else:
                messagebox.showerror("Error", "Failed to apply settings.")
                
        except Exception as e:
            logger.error(f"Error applying settings: {e}")
            messagebox.showerror("Error", f"Failed to apply settings: {str(e)}")
    
    def _on_ok(self):
        """Apply settings và close dialog"""
        self._on_apply()
        if not self.has_changes:  # Only close if apply was successful
            self.result = self.current_config
            self.dialog.destroy()
    
    def _on_cancel(self):
        """Cancel và close dialog"""
        if self.has_changes:
            if not messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes. Discard them?"
            ):
                return
        
        self.dialog.destroy()


class CustomReplacementDialog:
    """Dialog for adding/editing custom character replacements"""
    
    def __init__(self, parent: tk.Toplevel, char: str = "", replacement: str = ""):
        self.parent = parent
        self.dialog = None
        self.char_var = tk.StringVar(value=char)
        self.replacement_var = tk.StringVar(value=replacement)
        self.result = None
    
    def show(self) -> Optional[tuple]:
        """Show dialog và return result"""
        self._create_dialog()
        self._setup_ui()
        
        # Center và make modal
        self._center_dialog()
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Focus on first entry
        self.char_entry.focus()
        
        # Wait for dialog
        self.parent.wait_window(self.dialog)
        
        return self.result
    
    def _create_dialog(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Custom Character Replacement")
        self.dialog.geometry("400x150")
        self.dialog.resizable(False, False)
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
    
    def _setup_ui(self):
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Character input
        ttk.Label(main_frame, text="Character to replace:").grid(row=0, column=0, sticky="w", pady=5)
        self.char_entry = ttk.Entry(main_frame, textvariable=self.char_var, width=10)
        self.char_entry.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)
        
        # Replacement input
        ttk.Label(main_frame, text="Replace with:").grid(row=1, column=0, sticky="w", pady=5)
        self.replacement_entry = ttk.Entry(main_frame, textvariable=self.replacement_var, width=20)
        self.replacement_entry.grid(row=1, column=1, sticky="w", padx=(10, 0), pady=5)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="OK", command=self._on_ok).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(side="left", padx=5)
        
        # Bind Enter key
        self.dialog.bind('<Return>', lambda e: self._on_ok())
    
    def _center_dialog(self):
        self.dialog.update_idletasks()
        parent_x = self.parent.winfo_x()
        parent_y = self.parent.winfo_y()
        parent_width = self.parent.winfo_width()
        parent_height = self.parent.winfo_height()
        
        dialog_width = self.dialog.winfo_reqwidth()
        dialog_height = self.dialog.winfo_reqheight()
        
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _on_ok(self):
        char = self.char_var.get().strip()
        replacement = self.replacement_var.get()
        
        if not char:
            messagebox.showerror("Invalid Input", "Character cannot be empty.")
            return
        
        if len(char) > 1:
            messagebox.showerror("Invalid Input", "Please enter only one character.")
            return
        
        self.result = (char, replacement)
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.dialog.destroy()


# Example usage
if __name__ == "__main__":
    def test_settings_dialog():
        """Test settings dialog"""
        import tempfile
        import os
        from ...core.services.config_service import ConfigService
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            # Create root window
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            # Create config service
            config_service = ConfigService(db_path=db_path)
            
            # Show settings dialog
            dialog = SettingsDialog(root, config_service)
            result = dialog.show()
            
            if result:
                print("Settings updated successfully")
                print(f"Config version: {result.version}")
            else:
                print("Settings cancelled")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass
    
    # Uncomment to test
    # test_settings_dialog()