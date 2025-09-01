#!/usr/bin/env python3
"""
Vietnamese File Rename Tool - Complete 3-Epic Version
Full-featured stable application với tất cả Epic 1, 2, và 3 features
"""

import os
import sys
import locale
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Callable
import unidecode
import pandas as pd
import webbrowser
from tkinter.font import Font

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass

# Application metadata
APP_NAME = "Vietnamese File Rename Tool"
APP_VERSION = "3.0.0"
APP_AUTHOR = "File Rename Tool Team"
APP_DESCRIPTION = "Professional Vietnamese file rename utility with advanced normalization"

class ConfigService:
    """Enhanced configuration service with user preferences"""
    def __init__(self):
        self.config_dir = Path.home() / ".file_rename_tool"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.config = self.load_config()
    
    def load_config(self):
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        
        return {
            "recent_folders": [],
            "max_recent": 10,
            "window_geometry": "900x700",
            "window_position": None,
            "normalization": {
                "remove_diacritics": True,
                "lowercase_conversion": True,
                "clean_special_chars": True,
                "normalize_whitespace": True,
                "preserve_extensions": True,
                "custom_replacements": {}
            },
            "ui": {
                "theme": "default",
                "font_size": 10,
                "show_tooltips": True,
                "auto_preview": True
            },
            "performance": {
                "max_files": 5000,
                "batch_size": 100,
                "enable_caching": True
            }
        }
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def add_recent_folder(self, folder_path: str):
        recent = self.config["recent_folders"]
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)
        recent = recent[:self.config["max_recent"]]
        self.config["recent_folders"] = recent
        self.save_config()
    
    def get_normalization_rules(self):
        return self.config["normalization"]
    
    def update_normalization_rules(self, rules: dict):
        self.config["normalization"].update(rules)
        self.save_config()

class HistoryService:
    """Enhanced operation history with better tracking"""
    def __init__(self, config_dir: Path):
        self.db_file = config_dir / "operation_history.db"
        self.init_db()
    
    def init_db(self):
        try:
            conn = sqlite3.connect(str(self.db_file))
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    operation_type TEXT,
                    folder_path TEXT,
                    files_count INTEGER,
                    success_count INTEGER,
                    failed_count INTEGER,
                    details TEXT,
                    duration_ms INTEGER
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database init error: {e}")
    
    def save_operation(self, operation_type: str, folder_path: str, 
                      files_count: int, success_count: int, failed_count: int = 0,
                      details: str = "", duration_ms: int = 0):
        try:
            conn = sqlite3.connect(str(self.db_file))
            conn.execute('''
                INSERT INTO operations 
                (timestamp, operation_type, folder_path, files_count, success_count, failed_count, details, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), operation_type, folder_path, 
                  files_count, success_count, failed_count, details, duration_ms))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Save operation error: {e}")
    
    def get_last_operation(self):
        try:
            conn = sqlite3.connect(str(self.db_file))
            cursor = conn.execute('''
                SELECT * FROM operations ORDER BY timestamp DESC LIMIT 1
            ''')
            result = cursor.fetchone()
            conn.close()
            return result
        except:
            return None
    
    def get_operation_stats(self):
        try:
            conn = sqlite3.connect(str(self.db_file))
            cursor = conn.execute('''
                SELECT COUNT(*) as total_operations,
                       SUM(files_count) as total_files,
                       SUM(success_count) as total_successes
                FROM operations
            ''')
            result = cursor.fetchone()
            conn.close()
            return {
                'total_operations': result[0] or 0,
                'total_files': result[1] or 0,
                'total_successes': result[2] or 0
            }
        except:
            return {'total_operations': 0, 'total_files': 0, 'total_successes': 0}

class VietnameseNormalizer:
    """Enhanced Vietnamese normalization với custom rules"""
    def __init__(self, rules: dict = None):
        self.cache = {}
        self.rules = rules or {}
    
    def update_rules(self, rules: dict):
        self.rules = rules
        self.cache.clear()  # Clear cache when rules change
    
    def normalize_filename(self, filename: str) -> str:
        cache_key = f"{filename}_{hash(str(self.rules))}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        name, ext = os.path.splitext(filename)
        
        # Apply normalization rules
        result = name
        
        if self.rules.get("remove_diacritics", True):
            result = unidecode.unidecode(result)
        
        if self.rules.get("clean_special_chars", True):
            result = self._clean_special_chars(result)
        
        if self.rules.get("normalize_whitespace", True):
            result = ' '.join(result.split())
            result = result.strip()
        
        if self.rules.get("lowercase_conversion", True):
            result = result.lower()
        
        # Apply custom replacements
        custom_replacements = self.rules.get("custom_replacements", {})
        for old, new in custom_replacements.items():
            result = result.replace(old, new)
        
        # Handle extensions
        if self.rules.get("preserve_extensions", True):
            final_result = result + ext
        else:
            final_result = result + ext.lower()
        
        self.cache[cache_key] = final_result
        return final_result
    
    def _clean_special_chars(self, text: str) -> str:
        replacements = {
            '!': '', '@': ' at ', '#': ' hash ', '$': ' dollar ',
            '%': ' percent ', '^': '', '&': ' and ', '*': '',
            '(': '', ')': '', '[': '', ']': '', '{': '', '}': '',
            '|': ' ', '\\': ' ', '/': '', '?': '', '<': '', '>': '',
            '"': '', "'": '', '`': '', '~': '', '+': ' plus ',
            '=': ' equals ', ';': '', ':': '', ',': ''
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text

class DragDropHandler:
    """Drag and drop functionality for folders"""
    def __init__(self, parent, callback):
        self.parent = parent
        self.callback = callback
        self.setup_drag_drop()
    
    def setup_drag_drop(self):
        try:
            # Try to import tkinterdnd2 if available
            import tkinterdnd2
            
            # Enable drag and drop
            self.parent.drop_target_register(tkinterdnd2.DND_FILES)
            self.parent.dnd_bind('<<Drop>>', self.on_drop)
            self.parent.dnd_bind('<<DragEnter>>', self.on_drag_enter)
            self.parent.dnd_bind('<<DragLeave>>', self.on_drag_leave)
            
        except ImportError:
            print("Drag-drop setup failed: tkinterdnd2 not available - using alternative method")
            self.setup_windows_drag_drop()
    
    def setup_windows_drag_drop(self):
        """Windows-specific drag drop using windnd if available"""
        try:
            import windnd
            windnd.hook_dropfiles(self.parent, func=self.on_windows_drop)
            print("Using windnd for drag-drop support")
        except ImportError:
            print("windnd not available, using manual folder selection")
            self.setup_manual_drag_drop()
    
    def setup_manual_drag_drop(self):
        """Manual drag drop fallback"""
        # Add keyboard shortcut for folder selection
        self.parent.bind('<Control-o>', lambda e: self.show_folder_dialog())
        
    def show_folder_dialog(self):
        """Show folder selection dialog"""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select folder to rename files")
        if folder:
            self.callback(folder)
    
    def on_windows_drop(self, files):
        """Handle Windows drag-drop events via windnd"""
        if files and len(files) > 0:
            folder_path = files[0]
            if os.path.isdir(folder_path):
                self.callback(folder_path)
            else:
                messagebox.showwarning("Invalid Drop", "Please drop a folder, not files.")
    
    def on_drop(self, event):
        """Handle file drop"""
        try:
            files = self.parent.tk.splitlist(event.data)
            if files:
                folder_path = files[0]
                if os.path.isdir(folder_path):
                    self.callback(folder_path)
                    return
            messagebox.showwarning("Invalid Drop", "Please drop a folder, not files.")
        except Exception as e:
            messagebox.showerror("Drop Error", f"Error handling drop: {e}")
    
    def on_drag_enter(self, event):
        """Visual feedback on drag enter"""
        try:
            self.parent.configure(relief='ridge', borderwidth=2)
        except:
            self.parent.configure(relief='ridge')
    
    def on_drag_leave(self, event):
        """Remove visual feedback on drag leave"""
        try:
            self.parent.configure(relief='flat', borderwidth=1)
        except:
            self.parent.configure(relief='flat')
    
    def on_click(self, event):
        pass
    
    def on_drag_motion(self, event):
        pass
    
    def on_release(self, event):
        pass

class SettingsDialog:
    """User preferences and settings dialog"""
    def __init__(self, parent, config_service: ConfigService):
        self.parent = parent
        self.config_service = config_service
        self.dialog = None
        
    def show(self):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Settings & Preferences")
        self.dialog.geometry("500x600")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 100,
            self.parent.winfo_rooty() + 50
        ))
        
        # Create notebook for tabs
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Normalization tab
        norm_frame = ttk.Frame(notebook)
        notebook.add(norm_frame, text="Normalization")
        self.create_normalization_tab(norm_frame)
        
        # UI Preferences tab
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="Interface")
        self.create_ui_tab(ui_frame)
        
        # Performance tab
        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="Performance")
        self.create_performance_tab(perf_frame)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Reset to Defaults", 
                  command=self.reset_defaults).pack(side=tk.LEFT)
        
        ttk.Button(button_frame, text="Cancel", 
                  command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Apply", 
                  command=self.apply).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", 
                  command=self.ok).pack(side=tk.RIGHT)
    
    def create_normalization_tab(self, parent):
        """Create normalization settings tab"""
        config = self.config_service.config["normalization"]
        
        # Checkboxes for normalization options
        self.norm_vars = {}
        
        options = [
            ("remove_diacritics", "Remove Vietnamese diacritics (ủ → u, đ → d)"),
            ("lowercase_conversion", "Convert to lowercase"),
            ("clean_special_chars", "Clean special characters"),
            ("normalize_whitespace", "Normalize whitespace"),
            ("preserve_extensions", "Preserve file extensions")
        ]
        
        for i, (key, label) in enumerate(options):
            var = tk.BooleanVar(value=config.get(key, True))
            self.norm_vars[key] = var
            ttk.Checkbutton(parent, text=label, variable=var).pack(
                anchor=tk.W, padx=10, pady=5
            )
        
        # Custom replacements
        ttk.Label(parent, text="Custom Character Replacements:").pack(
            anchor=tk.W, padx=10, pady=(20, 5)
        )
        
        custom_frame = ttk.Frame(parent)
        custom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.custom_text = tk.Text(custom_frame, height=8)
        self.custom_text.pack(fill=tk.BOTH, expand=True)
        
        # Load custom replacements
        custom_replacements = config.get("custom_replacements", {})
        custom_text = "\n".join([f"{k} = {v}" for k, v in custom_replacements.items()])
        self.custom_text.insert(tk.END, custom_text)
    
    def create_ui_tab(self, parent):
        """Create UI preferences tab"""
        config = self.config_service.config["ui"]
        
        # Theme selection
        ttk.Label(parent, text="Theme:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.theme_var = tk.StringVar(value=config.get("theme", "default"))
        theme_combo = ttk.Combobox(parent, textvariable=self.theme_var, 
                                  values=["default", "dark", "light"])
        theme_combo.pack(anchor=tk.W, padx=20, pady=5)
        
        # Font size
        ttk.Label(parent, text="Font Size:").pack(anchor=tk.W, padx=10, pady=(20, 5))
        self.font_var = tk.IntVar(value=config.get("font_size", 10))
        font_scale = ttk.Scale(parent, from_=8, to=16, variable=self.font_var, orient=tk.HORIZONTAL)
        font_scale.pack(fill=tk.X, padx=20, pady=5)
        
        # Other UI options
        self.ui_vars = {}
        ui_options = [
            ("show_tooltips", "Show tooltips"),
            ("auto_preview", "Auto-generate preview when folder selected")
        ]
        
        for key, label in ui_options:
            var = tk.BooleanVar(value=config.get(key, True))
            self.ui_vars[key] = var
            ttk.Checkbutton(parent, text=label, variable=var).pack(
                anchor=tk.W, padx=10, pady=5
            )
    
    def create_performance_tab(self, parent):
        """Create performance settings tab"""
        config = self.config_service.config["performance"]
        
        # Max files
        ttk.Label(parent, text="Maximum files to process:").pack(anchor=tk.W, padx=10, pady=(10, 5))
        self.max_files_var = tk.IntVar(value=config.get("max_files", 5000))
        ttk.Entry(parent, textvariable=self.max_files_var).pack(anchor=tk.W, padx=20, pady=5)
        
        # Batch size
        ttk.Label(parent, text="Processing batch size:").pack(anchor=tk.W, padx=10, pady=(20, 5))
        self.batch_size_var = tk.IntVar(value=config.get("batch_size", 100))
        ttk.Entry(parent, textvariable=self.batch_size_var).pack(anchor=tk.W, padx=20, pady=5)
        
        # Enable caching
        self.caching_var = tk.BooleanVar(value=config.get("enable_caching", True))
        ttk.Checkbutton(parent, text="Enable normalization caching", 
                       variable=self.caching_var).pack(anchor=tk.W, padx=10, pady=(20, 5))
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        result = messagebox.askyesno("Reset Settings", 
                                    "Reset all settings to default values?")
        if result:
            # Reset to default config
            default_config = ConfigService().load_config()
            self.config_service.config.update(default_config)
            self.config_service.save_config()
            
            # Close and reopen dialog
            self.dialog.destroy()
            self.show()
    
    def apply(self):
        """Apply settings"""
        try:
            # Update normalization settings
            for key, var in self.norm_vars.items():
                self.config_service.config["normalization"][key] = var.get()
            
            # Parse custom replacements
            custom_text = self.custom_text.get(1.0, tk.END).strip()
            custom_replacements = {}
            if custom_text:
                for line in custom_text.split('\n'):
                    if ' = ' in line:
                        key, value = line.split(' = ', 1)
                        custom_replacements[key.strip()] = value.strip()
            
            self.config_service.config["normalization"]["custom_replacements"] = custom_replacements
            
            # Update UI settings
            self.config_service.config["ui"]["theme"] = self.theme_var.get()
            self.config_service.config["ui"]["font_size"] = self.font_var.get()
            
            for key, var in self.ui_vars.items():
                self.config_service.config["ui"][key] = var.get()
            
            # Update performance settings
            self.config_service.config["performance"]["max_files"] = self.max_files_var.get()
            self.config_service.config["performance"]["batch_size"] = self.batch_size_var.get()
            self.config_service.config["performance"]["enable_caching"] = self.caching_var.get()
            
            self.config_service.save_config()
            messagebox.showinfo("Settings", "Settings applied successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error applying settings: {e}")
    
    def ok(self):
        """Apply and close"""
        self.apply()
        self.dialog.destroy()
    
    def cancel(self):
        """Close without applying"""
        self.dialog.destroy()

class AboutDialog:
    """About dialog với application info"""
    def __init__(self, parent, history_service):
        self.parent = parent
        self.history_service = history_service
    
    def show(self):
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"About {APP_NAME}")
        dialog.geometry("400x300")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center dialog
        dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 150,
            self.parent.winfo_rooty() + 100
        ))
        
        # App info
        ttk.Label(dialog, text=APP_NAME, font=('Arial', 16, 'bold')).pack(pady=20)
        ttk.Label(dialog, text=f"Version {APP_VERSION}").pack()
        ttk.Label(dialog, text=f"By {APP_AUTHOR}").pack(pady=(0, 20))
        ttk.Label(dialog, text=APP_DESCRIPTION, wraplength=350).pack(pady=10)
        
        # Statistics
        stats = self.history_service.get_operation_stats()
        stats_text = f"""Statistics:
Total Operations: {stats['total_operations']}
Files Processed: {stats['total_files']}
Successful Renames: {stats['total_successes']}"""
        
        ttk.Label(dialog, text=stats_text, justify=tk.LEFT).pack(pady=20)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

class ProgressDialog:
    """Enhanced progress dialog với more features"""
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.dialog = None
        self.progress_var = None
        self.status_var = None
        self.time_var = None
        self.cancelled = False
        self.start_time = None
    
    def show(self, title: str = "Processing...", estimated_total: int = 0):
        self.start_time = time.time()
        
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(title)
        self.dialog.geometry("450x200")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            self.dialog, 
            variable=self.progress_var, 
            maximum=100
        )
        progress_bar.pack(pady=20, padx=20, fill=tk.X)
        
        # Status label
        self.status_var = tk.StringVar(value="Starting...")
        status_label = tk.Label(self.dialog, textvariable=self.status_var)
        status_label.pack(pady=10)
        
        # Time information
        self.time_var = tk.StringVar(value="Estimated time: calculating...")
        time_label = tk.Label(self.dialog, textvariable=self.time_var, font=('Arial', 9))
        time_label.pack(pady=5)
        
        # Cancel button
        cancel_button = tk.Button(
            self.dialog, 
            text="Cancel", 
            command=self._cancel
        )
        cancel_button.pack(pady=10)
        
        return self
    
    def update_progress(self, percentage: float, status: str = "", current: int = 0, total: int = 0):
        if self.dialog and self.progress_var:
            self.progress_var.set(percentage)
            if status and self.status_var:
                self.status_var.set(status)
            
            # Update time estimation
            if self.start_time and percentage > 0:
                elapsed = time.time() - self.start_time
                if percentage < 100:
                    estimated_total = elapsed * (100 / percentage)
                    remaining = estimated_total - elapsed
                    self.time_var.set(f"Elapsed: {elapsed:.1f}s, Remaining: {remaining:.1f}s")
                else:
                    self.time_var.set(f"Completed in {elapsed:.1f}s")
            
            self.dialog.update()
    
    def _cancel(self):
        self.cancelled = True
        if self.status_var:
            self.status_var.set("Cancelling...")
    
    def is_cancelled(self):
        return self.cancelled
    
    def close(self):
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None

class CompleteFileRenameApp:
    """Complete application với all 3 Epic features"""
    
    def __init__(self):
        # Clear command line arguments to prevent tkinter option conflicts
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # Keep only the script name
        
        try:
            # Try to use TkinterDnD for drag-drop support, fallback to regular Tk
            try:
                from tkinterdnd2 import TkinterDnD
                self.root = TkinterDnD.Tk()
                print("Using TkinterDnD for enhanced drag-drop support")
            except ImportError:
                self.root = tk.Tk()
                print("Using standard Tk (limited drag-drop support)")
        finally:
            # Restore original arguments
            sys.argv = original_argv
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        
        # Services
        self.config_service = ConfigService()
        self.history_service = HistoryService(self.config_service.config_dir)
        
        # Restore window geometry
        geometry = self.config_service.config.get("window_geometry", "900x700")
        self.root.geometry(geometry)
        
        # Initialize normalizer với current rules
        self.normalizer = VietnameseNormalizer(self.config_service.get_normalization_rules())
        
        # State
        self.current_folder = ""
        self.files_data = []
        self.preview_data = []
        
        # UI Components
        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Chọn thư mục để bắt đầu")
        self.include_subfolders_var = tk.BooleanVar(value=False)
        self.max_depth_var = tk.IntVar(value=3)
        
        self.setup_ui()
        self.setup_bindings()
        self.setup_drag_drop()
        
        # Load recent folders
        self.update_recent_folders()
        
        # Bind window events
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Setup complete user interface"""
        # Menu bar
        self.create_menu_bar()
        
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Folder selection section với drag-drop visual
        folder_frame = ttk.LabelFrame(main_frame, text="Chọn Thư Mục (Kéo thả thư mục vào đây hoặc nhấn Ctrl+O)", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)
        
        # Configure for drag-drop visual feedback  
        try:
            folder_frame.configure(relief='flat', borderwidth=1)
        except:
            folder_frame.configure(relief='flat')
        
        ttk.Label(folder_frame, text="Thư mục:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, state="readonly")
        self.folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_button = ttk.Button(folder_frame, text="Duyệt", command=self.browse_folder)
        self.browse_button.grid(row=0, column=2)
        
        # Recent folders dropdown
        ttk.Label(folder_frame, text="Gần đây:").grid(row=1, column=0, padx=(0, 5), sticky=tk.W, pady=(5, 0))
        
        self.recent_combo = ttk.Combobox(folder_frame, state="readonly")
        self.recent_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_selected)
        
        # Subfolder options
        options_frame = ttk.Frame(folder_frame)
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.include_subfolders_cb = ttk.Checkbutton(
            options_frame, 
            text="Bao gồm thư mục con", 
            variable=self.include_subfolders_var,
            command=self.on_subfolder_option_changed
        )
        self.include_subfolders_cb.pack(side=tk.LEFT)
        
        # Depth limit
        ttk.Label(options_frame, text="Độ sâu tối đa:").pack(side=tk.LEFT, padx=(20, 5))
        depth_spin = ttk.Spinbox(
            options_frame, 
            from_=1, 
            to=5, 
            width=5, 
            textvariable=self.max_depth_var,
            command=self.on_subfolder_option_changed
        )
        depth_spin.pack(side=tk.LEFT)
        
        # File preview section with enhanced info
        preview_frame = ttk.LabelFrame(main_frame, text="Xem Trước Đổi Tên File", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Preview toolbar
        toolbar_frame = ttk.Frame(preview_frame)
        toolbar_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar_frame, text="Làm Mới", command=self.refresh_preview).pack(side=tk.LEFT)
        ttk.Button(toolbar_frame, text="Chọn Tất Cả", command=self.select_all).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Button(toolbar_frame, text="Bỏ Chọn Tất Cả", command=self.deselect_all).pack(side=tk.LEFT, padx=(5, 0))
        
        # File count label
        self.file_count_var = tk.StringVar(value="Chưa tải file nào")
        ttk.Label(toolbar_frame, textvariable=self.file_count_var).pack(side=tk.RIGHT)
        
        # Create container frame for tree and scrollbars
        tree_container = ttk.Frame(preview_frame)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        # Treeview for file preview với more columns
        columns = ("selected", "current", "new", "status", "size")
        self.tree = ttk.Treeview(tree_container, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.tree.heading('selected', text='✓')
        self.tree.heading('current', text='Tên Hiện Tại')
        self.tree.heading('new', text='Tên Mới (Chuẩn Hóa)')
        self.tree.heading('status', text='Trạng Thái')
        self.tree.heading('size', text='Kích Thước')
        
        self.tree.column('selected', width=30, anchor='center')
        self.tree.column('current', width=250)
        self.tree.column('new', width=250)
        self.tree.column('status', width=100)
        self.tree.column('size', width=80)
        
        # Scrollbars in tree container
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        tree_container.columnconfigure(0, weight=1)
        tree_container.rowconfigure(0, weight=1)
        
        # Bind tree events
        self.tree.bind('<Double-1>', self.toggle_selection)
        
        # Status and action section
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        
        # Status label
        self.status_label = ttk.Label(action_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # Action buttons
        button_frame = ttk.Frame(action_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.rename_button = ttk.Button(button_frame, text="Đổi Tên File Đã Chọn", 
                                       command=self.rename_files, state="disabled")
        self.rename_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.undo_button = ttk.Button(button_frame, text="Hoàn Tác Thao Tác Cuối", 
                                     command=self.undo_last, state="disabled")
        self.undo_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_button = ttk.Button(button_frame, text="Xuất Danh Sách", 
                                       command=self.export_preview)
        self.export_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.settings_button = ttk.Button(button_frame, text="Cài Đặt", 
                                         command=self.show_settings)
        self.settings_button.pack(side=tk.LEFT)
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Folder...", command=self.browse_folder, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Export Preview...", command=self.export_preview, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="Deselect All", command=self.deselect_all, accelerator="Ctrl+D")
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings...", command=self.show_settings, accelerator="Ctrl+,")
        
        # Operation menu
        operation_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Operation", menu=operation_menu)
        operation_menu.add_command(label="Rename Files", command=self.rename_files, accelerator="F5")
        operation_menu.add_command(label="Undo Last Operation", command=self.undo_last, accelerator="Ctrl+Z")
        operation_menu.add_separator()
        operation_menu.add_command(label="Refresh Preview", command=self.refresh_preview, accelerator="F5")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self.show_help)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.browse_folder())
        self.root.bind('<Control-e>', lambda e: self.export_preview())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-d>', lambda e: self.deselect_all())
        self.root.bind('<F5>', lambda e: self.refresh_preview())
        self.root.bind('<Control-z>', lambda e: self.undo_last())
        self.root.bind('<Control-comma>', lambda e: self.show_settings())
    
    def setup_drag_drop(self):
        """Setup drag and drop functionality"""
        try:
            self.drag_handler = DragDropHandler(self.root, self.on_folder_dropped)
        except Exception as e:
            print(f"Drag-drop setup failed: {e}")
    
    def on_folder_dropped(self, folder_path: str):
        """Handle folder dropped onto application"""
        if os.path.isdir(folder_path):
            self.folder_var.set(folder_path)
            self.config_service.add_recent_folder(folder_path)
            self.update_recent_folders()
        else:
            messagebox.showwarning("Invalid Drop", "Please drop a folder, not a file.")
    
    def setup_bindings(self):
        """Setup event bindings"""
        self.folder_var.trace('w', self.on_folder_changed)
        
        # Check for last operation to enable undo
        if self.history_service.get_last_operation():
            self.undo_button.config(state="normal")
    
    def show_settings(self):
        """Show settings dialog"""
        settings = SettingsDialog(self.root, self.config_service)
        settings.show()
        
        # Update normalizer with new rules after settings change
        self.normalizer.update_rules(self.config_service.get_normalization_rules())
    
    def show_about(self):
        """Show about dialog"""
        about = AboutDialog(self.root, self.history_service)
        about.show()
    
    def show_help(self):
        """Show help documentation"""
        help_text = f"""
{APP_NAME} v{APP_VERSION} - User Guide

BASIC USAGE:
1. Select a folder using Browse button or drag-and-drop
2. Review the preview of proposed file renames
3. Select/deselect files as needed
4. Click "Rename Selected Files" to execute

FEATURES:
• Vietnamese text normalization (removes diacritics)
• Drag-and-drop folder support
• Undo functionality for safety
• Custom normalization rules
• Export preview to Excel/CSV
• Recent folders for quick access

KEYBOARD SHORTCUTS:
Ctrl+O - Select folder
Ctrl+A - Select all files
Ctrl+D - Deselect all files  
F5 - Refresh preview
Ctrl+Z - Undo last operation
Ctrl+E - Export preview
Ctrl+, - Open settings

NORMALIZATION RULES:
• Removes Vietnamese diacritics (ủ → u, đ → d)
• Cleans special characters
• Normalizes whitespace
• Optional lowercase conversion
• Custom character replacements

SAFETY FEATURES:
• Preview before rename
• Undo last operation
• Conflict detection
• Progress tracking with cancel
• Operation history

For more help, visit the project documentation.
        """
        
        help_dialog = tk.Toplevel(self.root)
        help_dialog.title("User Guide")
        help_dialog.geometry("600x500")
        help_dialog.transient(self.root)
        
        text_widget = tk.Text(help_dialog, wrap=tk.WORD, padx=10, pady=10)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, help_text.strip())
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(help_dialog, text="Close", command=help_dialog.destroy).pack(pady=10)
    
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts = """
Keyboard Shortcuts:

Ctrl+O      Select folder
Ctrl+A      Select all files
Ctrl+D      Deselect all files
Ctrl+E      Export preview list
Ctrl+Z      Undo last operation
Ctrl+,      Open settings
Ctrl+Q      Exit application
F5          Refresh preview/Rename files
Double-click Toggle file selection
        """
        messagebox.showinfo("Keyboard Shortcuts", shortcuts.strip())
    
    def browse_folder(self):
        """Browse for folder with enhanced error handling"""
        try:
            folder = filedialog.askdirectory(
                title="Select folder containing files to rename",
                initialdir=self.current_folder or os.getcwd()
            )
            
            if folder:
                self.folder_var.set(folder)
                self.config_service.add_recent_folder(folder)
                self.update_recent_folders()
                
        except Exception as e:
            messagebox.showerror("Error", f"Error selecting folder: {str(e)}")
    
    def on_recent_selected(self, event=None):
        """Handle recent folder selection"""
        selection = self.recent_combo.get()
        if selection and os.path.exists(selection):
            self.folder_var.set(selection)
        elif selection:
            messagebox.showwarning("Warning", f"Folder no longer exists: {selection}")
            self.update_recent_folders()
    
    def update_recent_folders(self):
        """Update recent folders combo"""
        recent = [f for f in self.config_service.config["recent_folders"] 
                 if os.path.exists(f)]
        self.recent_combo['values'] = recent
        
        # Update config if some folders no longer exist
        if len(recent) != len(self.config_service.config["recent_folders"]):
            self.config_service.config["recent_folders"] = recent
            self.config_service.save_config()
    
    def on_subfolder_option_changed(self):
        """Handle subfolder option changes - refresh preview if folder is selected"""
        if self.current_folder and os.path.exists(self.current_folder):
            # Trigger refresh by setting folder again
            folder = self.current_folder
            self.folder_var.set("")  # Clear to trigger refresh
            self.folder_var.set(folder)
    
    def on_folder_changed(self, *args):
        """Handle folder path changes với immediate UI feedback"""
        folder_path = self.folder_var.get()
        if not folder_path or not os.path.exists(folder_path):
            self.clear_preview()
            return
        
        self.current_folder = folder_path
        self.status_var.set("Đang tải danh sách file...")
        self.rename_button.config(state="disabled")
        
        # Force UI update before processing
        self.root.update_idletasks()
        
        # Process in background thread với performance limits
        def load_files():
            try:
                max_files = self.config_service.config["performance"].get("max_files", 5000)
                self.load_files_from_folder(folder_path, max_files)
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Error loading files: {str(e)}"))
        
        thread = threading.Thread(target=load_files, daemon=True)
        thread.start()
    
    def _scan_folder_recursive(self, folder_path: str, max_depth: int, max_files: int):
        """Recursively scan folder for files với depth và file count limits"""
        files = []
        
        def scan_directory(current_path: str, current_depth: int, relative_path: str = ""):
            if current_depth > max_depth or len(files) >= max_files:
                return
                
            try:
                items = os.listdir(current_path)
                for item in items:
                    if len(files) >= max_files:
                        break
                        
                    item_path = os.path.join(current_path, item)
                    
                    try:
                        if os.path.isfile(item_path):
                            size = os.path.getsize(item_path)
                            files.append((item, size, relative_path))  # Store relative directory path
                        elif os.path.isdir(item_path) and current_depth < max_depth:
                            # Recursively scan subdirectory
                            sub_relative_path = os.path.join(relative_path, item) if relative_path else item
                            scan_directory(item_path, current_depth + 1, sub_relative_path)
                    except (PermissionError, OSError):
                        # Skip inaccessible files/folders
                        continue
                        
            except (PermissionError, OSError):
                # Skip inaccessible directories
                pass
        
        scan_directory(folder_path, 1)
        return files
    
    def _show_large_operation_warning(self, file_count: int, include_subfolders: bool, message: str):
        """Show warning for large operations"""
        from tkinter import messagebox
        
        title = "Large Operation Warning"
        detailed_msg = (f"{message}\n\n"
                       f"Tips for large operations:\n"
                       f"• Consider using smaller max depth\n"
                       f"• Check 'Performance' settings\n"
                       f"• Operation can be cancelled if needed")
        
        # Just show info, don't block processing
        messagebox.showinfo(title, detailed_msg)
    
    def load_files_from_folder(self, folder_path: str, max_files: int = 5000):
        """Load and process files from folder với performance optimization"""
        try:
            start_time = time.time()
            
            # Get all files (with optional recursive scan)
            files = []
            include_subfolders = self.include_subfolders_var.get()
            max_depth = self.max_depth_var.get() if include_subfolders else 1
            
            if include_subfolders:
                # Recursive scan với depth limit
                files = self._scan_folder_recursive(folder_path, max_depth, max_files)
            else:
                # Shallow scan (original behavior)
                all_items = os.listdir(folder_path)
                for item in all_items:
                    item_path = os.path.join(folder_path, item)
                    if os.path.isfile(item_path):
                        try:
                            size = os.path.getsize(item_path)
                            files.append((item, size, ""))  # Empty relative path for root files
                        except:
                            files.append((item, 0, ""))
            
            # Apply performance limit và warnings
            original_count = len(files)
            
            # Warning for large operations
            if original_count > 1000:
                include_text = "with subfolders" if include_subfolders else ""
                warning_msg = (f"Found {original_count} files {include_text}. "
                              f"This may take longer to process. Continue?")
                
                # Show warning on main thread
                self.root.after(0, lambda: self._show_large_operation_warning(
                    original_count, include_subfolders, warning_msg
                ))
            
            if len(files) > max_files:
                files = files[:max_files]
                self.root.after(0, lambda: self.status_var.set(
                    f"Showing first {max_files} of {original_count} files (adjust in settings)"
                ))
            
            # Process files in batches
            preview_data = []
            batch_size = self.config_service.config["performance"].get("batch_size", 100)
            
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                batch_preview = []
                
                for file_data in batch:
                    # Handle both (filename, size) and (filename, size, relative_path) formats
                    if len(file_data) == 3:
                        filename, size, relative_path = file_data
                    else:
                        filename, size = file_data
                        relative_path = ""
                    
                    try:
                        normalized = self.normalizer.normalize_filename(filename)
                        status = "Sẵn sàng" if filename != normalized else "Không đổi"
                        
                        # Check for conflicts within the same directory
                        existing_files = [f[0] for f in files if (len(f) >= 3 and f[2] == relative_path) or (len(f) == 2 and relative_path == "")]
                        if normalized != filename and normalized in existing_files:
                            status = "Trùng tên!"
                        
                        # Format file size
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        
                        # Display path: show relative path if exists
                        display_current = os.path.join(relative_path, filename) if relative_path else filename
                        display_new = os.path.join(relative_path, normalized) if relative_path else normalized
                        
                        batch_preview.append({
                            'selected': True,
                            'current': display_current,
                            'new': display_new,
                            'status': status,
                            'size': size_str,
                            'changed': filename != normalized,
                            'filename': filename,  # Store original filename for processing
                            'relative_path': relative_path  # Store relative path for processing
                        })
                        
                    except Exception as e:
                        display_current = os.path.join(relative_path, filename) if relative_path else filename
                        
                        batch_preview.append({
                            'selected': False,
                            'current': display_current,
                            'new': display_current,
                            'status': f"Lỗi: {str(e)[:20]}",
                            'size': "0 B",
                            'changed': False,
                            'filename': filename,
                            'relative_path': relative_path
                        })
                
                preview_data.extend(batch_preview)
                
                # Update progress
                progress = ((i + batch_size) / len(files)) * 100
                self.root.after(0, lambda p=progress: 
                              self.status_var.set(f"Đang xử lý... {min(p, 100):.0f}%"))
            
            # Update UI in main thread
            processing_time = time.time() - start_time
            self.root.after(0, lambda: self.update_preview_display(preview_data, processing_time))
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"Error processing folder: {str(e)}"))
    
    def update_preview_display(self, preview_data: List[Dict], processing_time: float = 0):
        """Update the preview display với processed data"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Add new items
            self.preview_data = preview_data
            changes_count = sum(1 for item in preview_data if item['changed'])
            selected_count = sum(1 for item in preview_data if item['selected'])
            
            for item in preview_data:
                # Color code based on status
                tags = []
                if item['status'] == "Trùng tên!":
                    tags = ['conflict']
                elif item['changed'] and item['selected']:
                    tags = ['changed']
                elif not item['selected']:
                    tags = ['deselected']
                
                # Show selection status
                selection_mark = "✓" if item['selected'] else "○"
                
                self.tree.insert('', 'end', values=(
                    selection_mark, item['current'], item['new'], item['status'], item['size']
                ), tags=tags)
            
            # Configure tags with colors
            self.tree.tag_configure('conflict', background='#ffcccc')
            self.tree.tag_configure('changed', background='#ccffcc')
            self.tree.tag_configure('deselected', foreground='gray')
            
            # Update status and buttons
            total = len(preview_data)
            time_info = f" (processed in {processing_time:.1f}s)" if processing_time > 0.1 else ""
            self.status_var.set(f"Tìm thấy {total} file, {changes_count} cần đổi tên, {selected_count} đã chọn{time_info}")
            
            self.file_count_var.set(f"{selected_count}/{total} file đã chọn")
            
            self.rename_button.config(state="normal" if selected_count > 0 and changes_count > 0 else "disabled")
            
        except Exception as e:
            self.show_error(f"Error updating display: {str(e)}")
    
    def toggle_selection(self, event):
        """Toggle selection of clicked file"""
        item = self.tree.selection()[0]
        if item:
            # Find corresponding data item
            item_index = self.tree.index(item)
            if 0 <= item_index < len(self.preview_data):
                # Toggle selection
                self.preview_data[item_index]['selected'] = not self.preview_data[item_index]['selected']
                
                # Update display
                current_values = list(self.tree.item(item)['values'])
                current_values[0] = "✓" if self.preview_data[item_index]['selected'] else "○"
                self.tree.item(item, values=current_values)
                
                # Update tags
                if self.preview_data[item_index]['selected']:
                    if self.preview_data[item_index]['status'] == "Trùng tên!":
                        self.tree.item(item, tags=['conflict'])
                    elif self.preview_data[item_index]['changed']:
                        self.tree.item(item, tags=['changed'])
                    else:
                        self.tree.item(item, tags=[])
                else:
                    self.tree.item(item, tags=['deselected'])
                
                # Update counters
                self.update_counters()
    
    def select_all(self):
        """Select all files"""
        for i, item in enumerate(self.preview_data):
            item['selected'] = True
        self.refresh_display()
    
    def deselect_all(self):
        """Deselect all files"""
        for i, item in enumerate(self.preview_data):
            item['selected'] = False
        self.refresh_display()
    
    def refresh_display(self):
        """Refresh the current display"""
        if self.preview_data:
            self.update_preview_display(self.preview_data)
    
    def refresh_preview(self):
        """Refresh preview by reloading folder"""
        if self.current_folder:
            folder = self.current_folder
            self.folder_var.set("")  # Clear to trigger refresh
            self.folder_var.set(folder)
    
    def update_counters(self):
        """Update file counters"""
        if self.preview_data:
            selected_count = sum(1 for item in self.preview_data if item['selected'])
            changes_count = sum(1 for item in self.preview_data if item['changed'] and item['selected'])
            total = len(self.preview_data)
            
            self.file_count_var.set(f"{selected_count}/{total} file đã chọn")
            self.rename_button.config(state="normal" if changes_count > 0 else "disabled")
    
    def rename_files(self):
        """Execute batch rename operation với enhanced progress tracking"""
        if not self.preview_data or not self.current_folder:
            return
        
        # Get selected files to rename
        files_to_rename = [item for item in self.preview_data 
                          if item['selected'] and item['changed'] and item['status'] != "Trùng tên!"]
        
        if not files_to_rename:
            messagebox.showinfo("Thông báo", "Không có file nào được chọn để đổi tên.")
            return
        
        # Show conflicts warning
        conflicts = [item for item in self.preview_data 
                    if item['selected'] and item['status'] == "Trùng tên!"]
        if conflicts:
            result = messagebox.askyesno(
                "Phát hiện xung đột",
                f"Tìm thấy {len(conflicts)} file có xung đột tên sẽ được bỏ qua.\n\n"
                f"Tiếp tục đổi tên {len(files_to_rename)} file?"
            )
            if not result:
                return
        
        # Confirm operation
        result = messagebox.askyesno(
            "Xác nhận đổi tên", 
            f"Đổi tên {len(files_to_rename)} file đã chọn?\n\n"
            f"Thao tác này có thể hoàn tác bằng 'Hoàn Tác Thao Tác Cuối'."
        )
        
        if not result:
            return
        
        # Show enhanced progress dialog
        progress = ProgressDialog(self.root)
        progress.show("Đang Đổi Tên File", len(files_to_rename))
        
        # Execute in background
        def rename_operation():
            try:
                start_time = time.time()
                self.execute_rename_operation(files_to_rename, progress)
                duration = int((time.time() - start_time) * 1000)
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Rename operation failed: {str(e)}"))
            finally:
                self.root.after(0, progress.close)
        
        thread = threading.Thread(target=rename_operation, daemon=True)
        thread.start()
    
    def execute_rename_operation(self, files_to_rename: List[Dict], progress: ProgressDialog):
        """Execute the actual rename operation với detailed tracking"""
        success_count = 0
        failed_count = 0
        details = []
        
        total = len(files_to_rename)
        start_time = time.time()
        
        for i, item in enumerate(files_to_rename):
            if progress.is_cancelled():
                details.append("--- Operation cancelled by user ---")
                break
            
            try:
                # Handle files with relative paths
                if 'relative_path' in item and item['relative_path']:
                    # File in subdirectory
                    old_filename = item['filename']
                    new_filename = self.normalizer.normalize_filename(old_filename)
                    
                    old_path = os.path.join(self.current_folder, item['relative_path'], old_filename)
                    new_path = os.path.join(self.current_folder, item['relative_path'], new_filename)
                else:
                    # File in root directory (backward compatibility)
                    old_path = os.path.join(self.current_folder, item['current'])
                    new_path = os.path.join(self.current_folder, item['new'])
                
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    success_count += 1
                    details.append(f"✓ {item['current']} → {item['new']}")
                else:
                    failed_count += 1
                    details.append(f"✗ {item['current']} → target exists")
                
            except PermissionError:
                failed_count += 1
                details.append(f"✗ {item['current']} → permission denied")
            except Exception as e:
                failed_count += 1
                details.append(f"✗ {item['current']} → error: {str(e)[:50]}")
            
            # Update progress với detailed info
            percentage = ((i + 1) / total) * 100
            status = f"Đang xử lý {item['current'][:30]}..."
            self.root.after(0, lambda p=percentage, s=status, c=i+1, t=total: 
                          progress.update_progress(p, s, c, t))
        
        # Save operation to history với more details
        duration_ms = int((time.time() - start_time) * 1000)
        self.history_service.save_operation(
            "batch_rename", self.current_folder, total, success_count, failed_count,
            "\n".join(details), duration_ms
        )
        
        # Update UI
        self.root.after(0, lambda: self.after_rename_operation(success_count, failed_count, total))
    
    def after_rename_operation(self, success_count: int, failed_count: int, total: int):
        """Handle post-rename operations với detailed results"""
        if failed_count > 0:
            messagebox.showwarning("Hoàn thành với lỗi", 
                                 f"Đổi tên thành công {success_count}/{total} file.\n"
                                 f"{failed_count} file không thể đổi tên.")
        else:
            messagebox.showinfo("Hoàn thành", 
                              f"Đã đổi tên thành công {success_count} file.")
        
        # Enable undo button
        self.undo_button.config(state="normal")
        
        # Refresh the current folder
        if self.current_folder:
            self.refresh_preview()
    
    def undo_last(self):
        """Undo the last operation với enhanced feedback"""
        last_op = self.history_service.get_last_operation()
        if not last_op:
            messagebox.showinfo("Info", "No operation to undo.")
            return
        
        # Parse operation details
        details = last_op[7].split('\n') if last_op[7] else []  # Updated index for new schema
        successful_renames = [line for line in details if line.startswith('✓')]
        
        if not successful_renames:
            messagebox.showinfo("Info", "No successful renames to undo in the last operation.")
            return
        
        # Show operation info
        op_time = datetime.fromisoformat(last_op[1]).strftime("%Y-%m-%d %H:%M:%S")
        result = messagebox.askyesno(
            "Confirm Undo",
            f"Undo last operation?\n\n"
            f"Operation: {last_op[2]} on {op_time}\n"
            f"Folder: {last_op[3]}\n"
            f"Files to restore: {len(successful_renames)}\n\n"
            f"This will restore the original filenames."
        )
        
        if not result:
            return
        
        # Execute undo với progress tracking
        progress = ProgressDialog(self.root)
        progress.show("Undoing Operation", len(successful_renames))
        
        def undo_operation():
            try:
                undo_count = 0
                failed_count = 0
                undo_details = []
                
                for i, line in enumerate(successful_renames):
                    if progress.is_cancelled():
                        break
                    
                    # Parse: "✓ oldname → newname"
                    if ' → ' in line:
                        parts = line[2:].split(' → ')  # Remove "✓ " prefix
                        if len(parts) == 2:
                            old_name, new_name = parts
                            old_path = os.path.join(self.current_folder, new_name)
                            new_path = os.path.join(self.current_folder, old_name)
                            
                            try:
                                if os.path.exists(old_path) and not os.path.exists(new_path):
                                    os.rename(old_path, new_path)
                                    undo_count += 1
                                    undo_details.append(f"↶ {new_name} → {old_name}")
                                else:
                                    failed_count += 1
                                    undo_details.append(f"✗ Could not restore {old_name}")
                            except Exception as e:
                                failed_count += 1
                                undo_details.append(f"✗ Error restoring {old_name}: {str(e)[:30]}")
                    
                    # Update progress
                    percentage = ((i + 1) / len(successful_renames)) * 100
                    status = f"Restoring files..."
                    self.root.after(0, lambda p=percentage, s=status: progress.update_progress(p, s))
                
                # Save undo operation to history
                self.history_service.save_operation(
                    "undo_rename", self.current_folder, len(successful_renames), 
                    undo_count, failed_count, "\n".join(undo_details)
                )
                
                # Show results
                if failed_count > 0:
                    self.root.after(0, lambda: messagebox.showwarning("Undo Complete with Errors",
                                    f"Restored {undo_count} files.\n{failed_count} files could not be restored."))
                else:
                    self.root.after(0, lambda: messagebox.showinfo("Undo Complete", 
                                    f"Successfully restored {undo_count} files to their original names."))
                
                # Refresh display
                self.root.after(0, self.refresh_preview)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Undo Error", f"Error during undo: {str(e)}"))
            finally:
                self.root.after(0, progress.close)
        
        thread = threading.Thread(target=undo_operation, daemon=True)
        thread.start()
    
    def export_preview(self):
        """Export preview list to Excel/CSV với more options"""
        if not self.preview_data:
            messagebox.showinfo("Info", "No preview data to export.")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Preview List"
            )
            
            if not file_path:
                return
            
            # Prepare data for export
            export_data = []
            for item in self.preview_data:
                export_data.append({
                    'Selected': 'Yes' if item['selected'] else 'No',
                    'Current Name': item['current'],
                    'New Name': item['new'],
                    'Status': item['status'],
                    'Size': item['size'],
                    'Will Change': 'Yes' if item['changed'] else 'No'
                })
            
            # Create DataFrame
            df = pd.DataFrame(export_data)
            
            # Export based on file extension
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            messagebox.showinfo("Export Complete", 
                              f"Preview exported to: {os.path.basename(file_path)}\n\n"
                              f"Exported {len(export_data)} files.")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting: {str(e)}")
    
    def clear_preview(self):
        """Clear the preview display"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.preview_data = []
        self.status_var.set("Chưa chọn thư mục")
        self.file_count_var.set("Chưa tải file nào")
        self.rename_button.config(state="disabled")
    
    def show_error(self, message: str):
        """Show error message"""
        messagebox.showerror("Lỗi", message)
        self.status_var.set("Đã xảy ra lỗi")
    
    def on_closing(self):
        """Handle application closing"""
        # Save window geometry
        self.config_service.config["window_geometry"] = self.root.geometry()
        self.config_service.save_config()
        
        # Close application
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Critical Error", f"Application error: {str(e)}")

if __name__ == "__main__":
    # Clear command line arguments at startup to prevent any tkinter option conflicts
    original_argv = sys.argv.copy()
    sys.argv = [sys.argv[0]]  # Keep only script name
    
    try:
        app = CompleteFileRenameApp()
        app.run()
    except Exception as e:
        import traceback
        error_msg = f"Failed to start application: {str(e)}"
        
        # Try to show error dialog
        try:
            # Clear command line arguments to prevent tkinter option conflicts
            original_argv = sys.argv.copy()
            sys.argv = [sys.argv[0]]
            
            try:
                root = tk.Tk()
            finally:
                sys.argv = original_argv
            root.withdraw()
            messagebox.showerror("Startup Error", error_msg)
        except:
            print(error_msg)
        
        # Log to file
        try:
            with open("startup_error.txt", "w", encoding="utf-8") as f:
                f.write(f"Startup Error: {e}\n")
                traceback.print_exc(file=f)
        except:
            pass