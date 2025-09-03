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
        try:
            # Create a safe cache key
            rules_hash = hash(str(sorted(self.rules.items())))
            cache_key = f"{filename}_{rules_hash}"
            if cache_key in self.cache:
                return self.cache[cache_key]
        except Exception:
            # If cache key creation fails, continue without caching
            cache_key = None
        
        name, ext = os.path.splitext(filename)
        
        # Apply normalization rules with error handling
        result = name
        
        try:
            if self.rules.get("remove_diacritics", True):
                result = unidecode.unidecode(result)
        except Exception as e:
            print(f"Warning: Failed to remove diacritics from '{result}': {e}")
            # Continue with original text if unidecode fails
        
        try:
            if self.rules.get("clean_special_chars", True):
                result = self._clean_special_chars(result)
        except Exception as e:
            print(f"Warning: Failed to clean special chars from '{result}': {e}")
        
        try:
            if self.rules.get("normalize_whitespace", True):
                result = ' '.join(result.split())
                result = result.strip()
        except Exception as e:
            print(f"Warning: Failed to normalize whitespace in '{result}': {e}")
        
        try:
            if self.rules.get("lowercase_conversion", True):
                result = result.lower()
        except Exception as e:
            print(f"Warning: Failed to convert to lowercase '{result}': {e}")
        
        # Apply custom replacements
        custom_replacements = self.rules.get("custom_replacements", {})
        for old, new in custom_replacements.items():
            result = result.replace(old, new)
        
        # Handle extensions
        if self.rules.get("preserve_extensions", True):
            final_result = result + ext
        else:
            final_result = result + ext.lower()
        
        # Cache result if possible
        if cache_key:
            try:
                self.cache[cache_key] = final_result
            except Exception:
                pass  # Ignore cache errors
        
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
        self.dialog.title("Cài Đặt & Tùy Chỉnh")
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
        notebook.add(norm_frame, text="Chuẩn Hóa")
        self.create_normalization_tab(norm_frame)
        
        # UI Preferences tab
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="Giao Diện")
        self.create_ui_tab(ui_frame)
        
        # Performance tab
        perf_frame = ttk.Frame(notebook)
        notebook.add(perf_frame, text="Hiệu Năng")
        self.create_performance_tab(perf_frame)
        
        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(button_frame, text="Khôi Phục Mặc Định", 
                  command=self.reset_defaults).pack(side=tk.LEFT)
        
        ttk.Button(button_frame, text="Hủy", 
                  command=self.cancel).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Áp Dụng", 
                  command=self.apply).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="OK", 
                  command=self.ok).pack(side=tk.RIGHT)
    
    def create_normalization_tab(self, parent):
        """Create normalization settings tab"""
        config = self.config_service.config["normalization"]
        
        # Checkboxes for normalization options
        self.norm_vars = {}
        
        options = [
            ("remove_diacritics", "Loại bỏ dấu tiếng Việt (ủ → u, đ → d)"),
            ("lowercase_conversion", "Chuyển thành chữ thường"),
            ("clean_special_chars", "Loại bỏ ký tự đặc biệt"),
            ("normalize_whitespace", "Chuẩn hóa khoảng trắng"),
            ("preserve_extensions", "Giữ nguyên phần mở rộng file")
        ]
        
        for i, (key, label) in enumerate(options):
            var = tk.BooleanVar(value=config.get(key, True))
            self.norm_vars[key] = var
            ttk.Checkbutton(parent, text=label, variable=var).pack(
                anchor=tk.W, padx=10, pady=5
            )
        
        # Custom replacements
        ttk.Label(parent, text="Thay Thế Ký Tự Tùy Chỉnh:").pack(
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
        ttk.Label(parent, text="Kích thước lô xử lý:").pack(anchor=tk.W, padx=10, pady=(20, 5))
        self.batch_size_var = tk.IntVar(value=config.get("batch_size", 100))
        ttk.Entry(parent, textvariable=self.batch_size_var).pack(anchor=tk.W, padx=20, pady=5)
        
        # Enable caching
        self.caching_var = tk.BooleanVar(value=config.get("enable_caching", True))
        ttk.Checkbutton(parent, text="Enable normalization caching", 
                       variable=self.caching_var).pack(anchor=tk.W, padx=10, pady=(20, 5))
    
    def reset_defaults(self):
        """Reset all settings to defaults"""
        result = messagebox.askyesno("Khôi Phục Cài Đặt", 
                                    "Khôi phục tất cả cài đặt về giá trị mặc định?")
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
            messagebox.showinfo("Cài Đặt", "Đã áp dụng cài đặt thành công!")
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi khi áp dụng cài đặt: {e}")
    
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
        dialog.title(f"Về {APP_NAME}")
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
        stats_text = f"""Thống kê:
Tổng thao tác: {stats['total_operations']}
File đã xử lý: {stats['total_files']}
Đổi tên thành công: {stats['total_successes']}"""
        
        ttk.Label(dialog, text=stats_text, justify=tk.LEFT).pack(pady=20)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)

class FindReplaceDialog:
    """Find & Replace dialog for custom text replacements"""
    
    def __init__(self, parent, config_service):
        self.parent = parent
        self.config_service = config_service
        self.dialog = None
        self.replacements = {}  # Store find->replace mappings
        
    def show(self):
        """Show the Find & Replace dialog"""
        if self.dialog:
            self.dialog.lift()
            return
            
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Find & Replace - Custom Text Replacements")
        self.dialog.geometry("650x500")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (
            self.parent.winfo_rootx() + 50,
            self.parent.winfo_rooty() + 50
        ))
        
        self.setup_ui()
        self.load_current_replacements()
        
        # Bind close event
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_ui(self):
        """Setup the dialog UI"""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = ttk.Label(main_frame, text="Tạo quy tắc thay thế/xoá từ trong tên file (để trống 'Replace with' để xoá từ)", 
                                font=('TkDefaultFont', 9))
        instructions.pack(anchor=tk.W, pady=(0, 10))
        
        # Input frame
        input_frame = ttk.LabelFrame(main_frame, text="Thêm quy tắc mới", padding="10")
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Find text
        ttk.Label(input_frame, text="Tìm:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.find_var = tk.StringVar()
        self.find_entry = ttk.Entry(input_frame, textvariable=self.find_var, width=30)
        self.find_entry.grid(row=0, column=1, padx=(0, 10), sticky=(tk.W, tk.E))
        
        # Replace text
        ttk.Label(input_frame, text="Thay thế:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.replace_var = tk.StringVar()
        self.replace_entry = ttk.Entry(input_frame, textvariable=self.replace_var, width=30)
        self.replace_entry.grid(row=0, column=3, padx=(0, 10), sticky=(tk.W, tk.E))
        
        # Add button
        add_button = ttk.Button(input_frame, text="Thêm", command=self.add_replacement)
        add_button.grid(row=0, column=4)
        
        # Configure column weights
        input_frame.columnconfigure(1, weight=1)
        input_frame.columnconfigure(3, weight=1)
        
        # Replacements list frame
        list_frame = ttk.LabelFrame(main_frame, text="Quy tắc hiện tại", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for replacements
        columns = ('find', 'replace', 'action')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # Define headings
        self.tree.heading('find', text='Tìm')
        self.tree.heading('replace', text='Thay thế')
        self.tree.heading('action', text='Hành động')
        
        # Define column widths
        self.tree.column('find', width=200)
        self.tree.column('replace', width=200)  
        self.tree.column('action', width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click to edit
        self.tree.bind('<Double-1>', self.edit_replacement)
        self.tree.bind('<Delete>', self.delete_replacement)
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Left side buttons
        ttk.Button(button_frame, text="Xoá đã chọn", command=self.delete_replacement).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Xoá tất cả", command=self.clear_all).pack(side=tk.LEFT)
        
        # Right side buttons  
        ttk.Button(button_frame, text="Huỷ", command=self.on_close).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Áp dụng", command=self.apply_replacements).pack(side=tk.RIGHT)
        
        # Focus on find entry
        self.find_entry.focus_set()
        
        # Bind Enter key to add
        self.find_entry.bind('<Return>', lambda e: self.add_replacement())
        self.replace_entry.bind('<Return>', lambda e: self.add_replacement())
    
    def load_current_replacements(self):
        """Load current custom replacements from config"""
        current_replacements = self.config_service.config["normalization"].get("custom_replacements", {})
        self.replacements = current_replacements.copy()
        self.refresh_tree()
    
    def refresh_tree(self):
        """Refresh the treeview with current replacements"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add current replacements
        for find_text, replace_text in self.replacements.items():
            action = "Xoá" if replace_text == "" else "Thay thế"
            display_replace = "(xoá)" if replace_text == "" else replace_text
            self.tree.insert('', tk.END, values=(find_text, display_replace, action))
    
    def add_replacement(self):
        """Add a new replacement rule"""
        find_text = self.find_var.get().strip()
        replace_text = self.replace_var.get()
        
        if not find_text:
            messagebox.showwarning("Lỗi", "Vui lòng nhập từ cần tìm")
            self.find_entry.focus_set()
            return
        
        # Add to replacements dict
        self.replacements[find_text] = replace_text
        
        # Clear inputs
        self.find_var.set("")
        self.replace_var.set("")
        
        # Refresh display
        self.refresh_tree()
        
        # Focus back to find entry
        self.find_entry.focus_set()
    
    def edit_replacement(self, event):
        """Edit selected replacement by double-click"""
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        values = self.tree.item(item)['values']
        find_text = values[0]
        replace_text = values[1]
        
        # Handle (xoá) display
        if replace_text == "(xoá)":
            replace_text = ""
        
        # Populate entry fields
        self.find_var.set(find_text)
        self.replace_var.set(replace_text)
        
        # Remove from list (will be re-added when user clicks Add)
        del self.replacements[find_text]
        self.refresh_tree()
        
        # Focus on find entry
        self.find_entry.focus_set()
    
    def delete_replacement(self, event=None):
        """Delete selected replacement"""
        selection = self.tree.selection()
        if not selection:
            return
            
        item = selection[0]
        find_text = self.tree.item(item)['values'][0]
        
        # Remove from replacements dict
        if find_text in self.replacements:
            del self.replacements[find_text]
        
        # Refresh display
        self.refresh_tree()
    
    def clear_all(self):
        """Clear all replacements"""
        if messagebox.askyesno("Xác nhận", "Xoá tất cả quy tắc thay thế?"):
            self.replacements.clear()
            self.refresh_tree()
    
    def apply_replacements(self):
        """Apply the replacements to config and close"""
        # Update config
        self.config_service.config["normalization"]["custom_replacements"] = self.replacements.copy()
        self.config_service.save_config()
        
        # Show confirmation
        count = len(self.replacements)
        messagebox.showinfo("Thành công", f"Đã áp dụng {count} quy tắc thay thế.\n\nQuy tắc sẽ được sử dụng trong các lần đổi tên tiếp theo.")
        
        # Close dialog
        self.on_close()
    
    def on_close(self):
        """Handle dialog close"""
        self.dialog.grab_release()
        self.dialog.destroy()
        self.dialog = None

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
    
    def show(self, title: str = "Đang xử lý...", estimated_total: int = 0):
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
        self.status_var = tk.StringVar(value="Đang bắt đầu...")
        status_label = tk.Label(self.dialog, textvariable=self.status_var)
        status_label.pack(pady=10)
        
        # Time information
        self.time_var = tk.StringVar(value="Estimated time: calculating...")
        time_label = tk.Label(self.dialog, textvariable=self.time_var, font=('Arial', 9))
        time_label.pack(pady=5)
        
        # Cancel button
        cancel_button = tk.Button(
            self.dialog, 
            text="Hủy", 
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
            self.status_var.set("Đang hủy...")
    
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
        self.status_var = tk.StringVar(value="Chọn thư mục")
        self.include_subfolders_var = tk.BooleanVar(value=False)
        self.max_depth_var = tk.IntVar(value=10)
        
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
        folder_frame = ttk.LabelFrame(main_frame, text="Thư Mục", padding="10")
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
        
        # Bind double-click to open browse folder
        self.folder_entry.bind('<Double-Button-1>', lambda e: self.browse_folder())
        folder_frame.bind('<Double-Button-1>', lambda e: self.browse_folder())
        
        # Add hover effect for visual feedback
        def on_enter(e):
            if hasattr(e.widget, 'configure'):
                try:
                    e.widget.configure(cursor='hand2')
                except:
                    pass
        
        def on_leave(e):
            if hasattr(e.widget, 'configure'):
                try:
                    e.widget.configure(cursor='')
                except:
                    pass
        
        self.folder_entry.bind('<Enter>', on_enter)
        self.folder_entry.bind('<Leave>', on_leave)
        folder_frame.bind('<Enter>', on_enter) 
        folder_frame.bind('<Leave>', on_leave)
        
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
        
        # Depth limit (will be shown/hidden based on subfolder checkbox)
        self.depth_label = ttk.Label(options_frame, text="Độ sâu tối đa:")
        self.depth_label.pack(side=tk.LEFT, padx=(20, 5))
        
        self.depth_spin = ttk.Spinbox(
            options_frame, 
            from_=1, 
            to=10, 
            width=5, 
            textvariable=self.max_depth_var,
            command=self.on_subfolder_option_changed
        )
        self.depth_spin.pack(side=tk.LEFT)
        
        # Initially hide depth controls since subfolders is False by default
        self.depth_label.pack_forget()
        self.depth_spin.pack_forget()
        
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
        self.tree.bind('<Double-1>', self.on_double_click)
        self.tree.bind('<KeyPress-F2>', self.on_edit_key)
        self.tree.bind('<Button-3>', self.on_right_click)  # Right-click context menu
        
        # Status and action section
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        
        # Status label
        self.status_label = ttk.Label(action_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # Action buttons
        # Workflow buttons (new scan-first approach)
        workflow_frame = ttk.LabelFrame(action_frame, text="Quick Scan")
        workflow_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        workflow_buttons_frame = ttk.Frame(workflow_frame)
        workflow_buttons_frame.pack(pady=5)
        
        self.quick_scan_button = ttk.Button(workflow_buttons_frame, text="Scan", 
                                          command=self.start_quick_scan)
        self.quick_scan_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_scan_button = ttk.Button(workflow_buttons_frame, text="Xuất file", 
                                           command=self.export_scan_results, state="disabled")
        self.export_scan_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.import_list_button = ttk.Button(workflow_buttons_frame, text="Nhập file", 
                                           command=self.import_rename_list)
        self.import_list_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Find & Replace button
        self.find_replace_button = ttk.Button(workflow_buttons_frame, text="Find & Replace", 
                                            command=self.show_find_replace)
        self.find_replace_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Traditional buttons (existing functionality)
        button_frame = ttk.Frame(action_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.rename_button = ttk.Button(button_frame, text="Đổi Tên", 
                                       command=self.rename_files, state="disabled")
        self.rename_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.undo_button = ttk.Button(button_frame, text="Hoàn Tác", 
                                     command=self.undo_last, state="disabled")
        self.undo_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_button = ttk.Button(button_frame, text="Xuất", 
                                       command=self.export_preview)
        self.export_button.pack(side=tk.LEFT)
    
    def create_menu_bar(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tập Tin", menu=file_menu)
        file_menu.add_command(label="Chọn Thư Mục...", command=self.browse_folder, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Xuất Danh Sách...", command=self.export_preview, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Thoát", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Chỉnh Sửa", menu=edit_menu)
        edit_menu.add_command(label="Chọn Tất Cả", command=self.select_all, accelerator="Ctrl+A")
        edit_menu.add_command(label="Bỏ Chọn Tất Cả", command=self.deselect_all, accelerator="Ctrl+D")
        edit_menu.add_separator()
        edit_menu.add_command(label="Tìm & Thay Thế...", command=self.show_find_replace, accelerator="Ctrl+H")
        edit_menu.add_separator()
        edit_menu.add_command(label="Cài Đặt...", command=self.show_settings, accelerator="Ctrl+,")
        
        # Operation menu
        operation_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Thao Tác", menu=operation_menu)
        operation_menu.add_command(label="Đổi Tên File", command=self.rename_files, accelerator="F5")
        operation_menu.add_command(label="Hoàn Tác Thao Tác Cuối", command=self.undo_last, accelerator="Ctrl+Z")
        operation_menu.add_separator()
        operation_menu.add_command(label="Làm Mới Xem Trước", command=self.refresh_preview, accelerator="F5")
        operation_menu.add_separator()
        operation_menu.add_command(label="Quick Scan", command=self.start_quick_scan, accelerator="F4")
        operation_menu.add_command(label="Export Files Need Renaming", command=self.export_scan_results, accelerator="Ctrl+Shift+E")
        operation_menu.add_command(label="Import Rename List", command=self.import_rename_list, accelerator="Ctrl+Shift+I")
        operation_menu.add_separator()
        operation_menu.add_command(label="Mở Thư Mục Chứa File", command=self.open_selected_file_location, accelerator="Ctrl+L")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Trợ Giúp", menu=help_menu)
        help_menu.add_command(label="Hướng Dẫn Sử Dụng", command=self.show_help)
        help_menu.add_command(label="Phím Tắt", command=self.show_shortcuts)
        help_menu.add_separator()
        help_menu.add_command(label="Về Chương Trình", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.root.bind('<Control-o>', lambda e: self.browse_folder())
        self.root.bind('<Control-e>', lambda e: self.export_preview())
        self.root.bind('<Control-q>', lambda e: self.on_closing())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-d>', lambda e: self.deselect_all())
        self.root.bind('<F5>', lambda e: self.refresh_preview())
        self.root.bind('<Control-z>', lambda e: self.undo_last())
        self.root.bind('<Control-comma>', lambda e: self.show_settings())
        self.root.bind('<Control-l>', lambda e: self.open_selected_file_location())
        self.root.bind('<F4>', lambda e: self.start_quick_scan())
        self.root.bind('<Control-Shift-E>', lambda e: self.export_scan_results())
        self.root.bind('<Control-Shift-I>', lambda e: self.import_rename_list())
        self.root.bind('<Control-h>', lambda e: self.show_find_replace())
    
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
    
    def show_find_replace(self):
        """Show find and replace dialog"""
        find_replace = FindReplaceDialog(self.root, self.config_service)
        find_replace.show()
        
        # Update normalizer with new replacement rules after dialog closes
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
Ctrl+L - Open file location in explorer
Ctrl+, - Open settings

CONTEXT MENU (Right-click):
• Edit filename (F2)
• Open file location in explorer
• Copy file path to clipboard
• Reset to automatic normalization

UI SHORTCUTS:
• Double-click folder path to browse for new folder
• Drag and drop folders onto the application

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
Ctrl+L      Open file location in explorer
Ctrl+Z      Undo last operation
Ctrl+,      Open settings
Ctrl+Q      Exit application
F5          Refresh preview/Rename files
F2          Edit filename (when file selected)
Double-click Toggle file selection
Right-click Context menu with file operations
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
        """Handle subfolder option changes - show/hide depth controls and refresh"""
        # Show/hide depth controls based on subfolder checkbox
        if self.include_subfolders_var.get():
            self.depth_label.pack(side=tk.LEFT, padx=(20, 5))
            self.depth_spin.pack(side=tk.LEFT)
        else:
            self.depth_label.pack_forget()
            self.depth_spin.pack_forget()
        
        # Refresh preview if folder is selected
        if self.current_folder and os.path.exists(self.current_folder):
            # Trigger refresh by setting folder again
            folder = self.current_folder
            self.folder_var.set("")  # Clear to trigger refresh
            self.folder_var.set(folder)
    
    def start_quick_scan(self):
        """Start quick scan in background thread - auto browse if no folder selected"""
        if not self.current_folder or not os.path.exists(self.current_folder):
            # Auto-open browse dialog instead of showing warning
            self.browse_folder()
            # Check again after browse
            if not self.current_folder or not os.path.exists(self.current_folder):
                return  # User cancelled browse dialog
        
        # Run quick scan in background
        import threading
        thread = threading.Thread(target=self.quick_scan_folder, args=(self.current_folder,), daemon=True)
        thread.start()

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
    
    def quick_scan_folder(self, folder_path: str):
        """Quick scan to find only files that need renaming - no UI loading"""
        try:
            start_time = time.time()
            
            # Get scan settings
            include_subfolders = self.include_subfolders_var.get()
            max_depth = self.max_depth_var.get() if include_subfolders else 1
            
            # Quick scan without UI updates
            files_need_renaming = []
            total_files_scanned = 0
            
            # Show progress dialog
            progress = ProgressDialog(self.root)
            progress.show("Quick Scan - Tìm files cần đổi tên", 0)
            
            def scan_directory(current_path: str, current_depth: int, relative_path: str = ""):
                nonlocal total_files_scanned, files_need_renaming
                
                if current_depth > max_depth or progress.is_cancelled():
                    return
                    
                try:
                    items = os.listdir(current_path)
                    for item in items:
                        if progress.is_cancelled():
                            break
                            
                        item_path = os.path.join(current_path, item)
                        
                        try:
                            if os.path.isfile(item_path):
                                total_files_scanned += 1
                                
                                # Quick normalization check
                                normalized = self.normalizer.normalize_filename(item)
                                needs_rename = (item != normalized)
                                
                                if needs_rename:
                                    size = os.path.getsize(item_path)
                                    files_need_renaming.append({
                                        'original_name': item,
                                        'suggested_name': normalized,
                                        'relative_path': relative_path,
                                        'full_path': item_path,
                                        'size': size
                                    })
                                
                                # Update progress every 50 files
                                if total_files_scanned % 50 == 0:
                                    status = f"Scanned {total_files_scanned} files, found {len(files_need_renaming)} need renaming"
                                    progress.update_progress(0, status)  # Indeterminate progress
                                    
                            elif os.path.isdir(item_path) and current_depth < max_depth:
                                sub_relative_path = os.path.join(relative_path, item) if relative_path else item
                                scan_directory(item_path, current_depth + 1, sub_relative_path)
                                
                        except (PermissionError, OSError):
                            continue
                            
                except (PermissionError, OSError):
                    pass
            
            # Execute scan
            scan_directory(folder_path, 1)
            
            progress.close()
            
            # Show results
            scan_time = time.time() - start_time
            self.show_scan_results(files_need_renaming, total_files_scanned, scan_time)
            
            # Store scan results for export
            self.scan_results = files_need_renaming
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            messagebox.showerror("Quick Scan Error", f"Error during scan: {str(e)}")
    
    def show_scan_results(self, files_need_renaming: list, total_scanned: int, scan_time: float):
        """Display scan results summary"""
        need_rename_count = len(files_need_renaming)
        no_change_count = total_scanned - need_rename_count
        
        result_msg = f"""Quick Scan Complete!
        
Scan Time: {scan_time:.1f} seconds
Total Files Scanned: {total_scanned:,}

Files Need Renaming: {need_rename_count:,}
Files Already OK: {no_change_count:,}

Next Steps:
• Click "Export Files Need Renaming" to save list
• Review and edit the Excel file if needed  
• Import the list back to rename files"""
        
        messagebox.showinfo("Scan Results", result_msg)
        
        # Update status
        self.status_var.set(f"Scan complete: {need_rename_count:,} of {total_scanned:,} files need renaming")
        
        # Enable export button
        if hasattr(self, 'export_scan_button'):
            self.export_scan_button.config(state="normal" if need_rename_count > 0 else "disabled")

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
                        # Build target path to check if it already exists on disk
                        if relative_path:
                            target_path = os.path.join(self.current_folder, relative_path, normalized)
                            original_path = os.path.join(self.current_folder, relative_path, filename)
                        else:
                            target_path = os.path.join(self.current_folder, normalized)
                            original_path = os.path.join(self.current_folder, filename)
                        
                        # Check for conflicts: target exists but is not the same as original (case-sensitive)
                        if normalized != filename:
                            if os.path.exists(target_path) and os.path.abspath(target_path).lower() != os.path.abspath(original_path).lower():
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
                            'relative_path': relative_path,  # Store relative path for processing
                            'custom_name': None,  # Track manual edits
                            'is_manual': False  # Flag for manual vs auto normalization
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
                            'relative_path': relative_path,
                            'custom_name': None,
                            'is_manual': False
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
                elif item.get('is_manual', False) and item['selected']:
                    tags = ['manual']  # Manual edits get blue background
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
            self.tree.tag_configure('manual', background='#cceeff')  # Light blue for manual edits
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
        selection = self.tree.selection()
        if not selection:
            # No item selected, try to get item from click position
            item = self.tree.identify('item', event.x, event.y)
            if item:
                self.tree.selection_set(item)
            else:
                return
        else:
            item = selection[0]
        
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
                    elif self.preview_data[item_index].get('is_manual', False):
                        self.tree.item(item, tags=['manual'])
                    elif self.preview_data[item_index]['changed']:
                        self.tree.item(item, tags=['changed'])
                    else:
                        self.tree.item(item, tags=[])
                else:
                    self.tree.item(item, tags=['deselected'])
                
                # Update counters
                self.update_counters()
    
    def on_double_click(self, event):
        """Handle double-click events - toggle selection or edit"""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            # Column #3 is "new" (0-based: selected, current, new, status, size)
            if column == "#3":  # "new" column
                item = self.tree.identify('item', event.x, event.y)
                if item:
                    self.edit_filename(item)
                return
        
        # Fall back to toggle selection
        self.toggle_selection(event)
    
    def on_edit_key(self, event):
        """Handle F2 key press for editing"""
        selection = self.tree.selection()
        if selection:
            self.edit_filename(selection[0])
    
    def edit_filename(self, item):
        """Start editing filename for given item"""
        if not item or not self.preview_data:
            return
        
        try:
            item_index = self.tree.index(item)
            if not (0 <= item_index < len(self.preview_data)):
                return
                
            data_item = self.preview_data[item_index]
            
            # Don't edit if there's an error
            if "Lỗi:" in data_item['status']:
                return
                
            # Get current position in tree
            bbox = self.tree.bbox(item, column="new")
            if not bbox:
                return
                
            # Create edit popup
            self.show_edit_popup(item, item_index, bbox, data_item)
            
        except Exception as e:
            print(f"Error starting edit: {e}")
    
    def show_edit_popup(self, item, item_index, bbox, data_item):
        """Show popup entry for editing filename"""
        x, y, width, height = bbox
        
        # Create popup frame
        popup = tk.Toplevel(self.root)
        popup.wm_overrideredirect(True)
        
        # Position popup over the cell
        tree_x = self.tree.winfo_rootx()
        tree_y = self.tree.winfo_rooty()
        popup.geometry(f"{width}x{height}+{tree_x + x}+{tree_y + y}")
        
        # Get current filename (without path for editing) - separate name and extension
        original_filename = data_item['filename']
        name_part, ext_part = os.path.splitext(original_filename)
        
        # Handle files without extension (like screenshot files)
        if not ext_part:
            # Try to detect actual file type if possible
            ext_part = self.detect_file_extension(data_item, original_filename)
        
        # For editing, show the full name if no extension, otherwise just name part
        if data_item.get('custom_name'):
            if ext_part:
                # Has extension - edit only name part
                custom_name_part, _ = os.path.splitext(data_item['custom_name'])
                current_name = custom_name_part
            else:
                # No extension - edit full name
                current_name = data_item['custom_name']
        else:
            if ext_part:
                # Has extension - edit only name part
                current_name = name_part
            else:
                # No extension - edit full name
                current_name = original_filename
        
        # Create frame for entry and extension label
        edit_frame = tk.Frame(popup)
        edit_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create entry widget
        entry = tk.Entry(edit_frame, borderwidth=1, highlightthickness=1)
        entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        entry.insert(0, current_name)
        entry.select_range(0, tk.END)
        entry.focus_set()
        
        # Show extension as label (non-editable)
        if ext_part:
            ext_label = tk.Label(edit_frame, text=ext_part, fg='gray')
            ext_label.pack(side=tk.RIGHT)
        
        def save_edit():
            new_name = entry.get().strip()
            popup.destroy()
            if new_name and new_name != current_name:
                if ext_part:
                    # Has extension - append it
                    new_name_with_ext = new_name + ext_part
                else:
                    # No extension - use name as is
                    new_name_with_ext = new_name
                self.apply_manual_edit(item_index, new_name_with_ext, ext_part)
        
        def cancel_edit():
            popup.destroy()
        
        # Bind events
        entry.bind('<Return>', lambda e: save_edit())
        entry.bind('<Escape>', lambda e: cancel_edit())
        entry.bind('<FocusOut>', lambda e: save_edit())
    
    def apply_manual_edit(self, item_index, new_name, original_ext=""):
        """Apply manual filename edit with validation"""
        if not (0 <= item_index < len(self.preview_data)):
            return
            
        data_item = self.preview_data[item_index]
        
        # Validate filename (now includes extension)
        validation_result = self.validate_filename(new_name, data_item, item_index)
        if not validation_result['valid']:
            messagebox.showerror("Tên File Không Hợp Lệ", validation_result['message'])
            return
        
        # Handle extension preservation
        original_name, original_ext = os.path.splitext(data_item['filename'])
        new_name_part, new_ext = os.path.splitext(new_name)
        
        # If original file had no extension, allow editing without extension
        if not original_ext:
            # For files without extension, accept the name as-is
            # But if user added an extension, keep it
            pass  # new_name stays as user provided
        else:
            # If user didn't specify extension but original had one, use original
            if not new_ext and original_ext:
                new_name = new_name_part + original_ext
        
        # Apply the edit
        relative_path = data_item['relative_path']
        if relative_path:
            display_new = os.path.join(relative_path, new_name)
        else:
            display_new = new_name
            
        # Update data
        data_item['custom_name'] = new_name
        data_item['new'] = display_new
        data_item['is_manual'] = True
        data_item['changed'] = new_name != data_item['filename']
        data_item['status'] = "Tùy chỉnh" if data_item['changed'] else "Không đổi"
        
        # Refresh display
        self.refresh_display()
        
    def validate_filename(self, name, data_item, item_index):
        """Validate filename for safety and conflicts"""
        if not name.strip():
            return {'valid': False, 'message': "Tên file không được để trống"}
        
        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in name for char in invalid_chars):
            return {'valid': False, 'message': f"Tên file chứa ký tự không hợp lệ: {invalid_chars}"}
        
        # Check for reserved names (Windows)
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        name_base = name.split('.')[0].upper()
        if name_base in reserved_names:
            return {'valid': False, 'message': f"'{name_base}' là tên file hệ thống không được phép"}
        
        # Ensure extension is preserved for validation
        original_name, original_ext = os.path.splitext(data_item['filename'])
        name_part, ext_part = os.path.splitext(name)
        
        # If no extension provided, add original extension
        if not ext_part and original_ext:
            name = name_part + original_ext
        
        # Check for conflicts with other files in same directory
        relative_path = data_item['relative_path']
        for i, other_item in enumerate(self.preview_data):
            if i == item_index:  # Skip self
                continue
            if other_item['relative_path'] == relative_path:  # Same directory
                other_new_name = other_item.get('custom_name') or self.normalizer.normalize_filename(other_item['filename'])
                if other_new_name.lower() == name.lower():
                    return {'valid': False, 'message': f"Tên file trùng với file khác trong cùng thư mục: '{other_new_name}'"}
        
        # Check for conflict with existing files on disk (basic check)
        full_path = os.path.join(self.current_folder, relative_path, name) if relative_path else os.path.join(self.current_folder, name)
        original_path = os.path.join(self.current_folder, relative_path, data_item['filename']) if relative_path else os.path.join(self.current_folder, data_item['filename'])
        
        if os.path.exists(full_path) and full_path.lower() != original_path.lower():
            return {'valid': False, 'message': f"File đã tồn tại trên đĩa: '{name}'"}
        
        return {'valid': True, 'message': ''}
    
    def detect_file_extension(self, data_item, filename):
        """Try to detect file extension for files without extension"""
        # For now, simple heuristic based on filename patterns
        # This could be enhanced with actual file content detection
        
        lower_name = filename.lower()
        
        # Screenshot patterns
        if 'screenshot' in lower_name:
            return '.jpg'  # Most screenshots are JPG
            
        # Image patterns (common image file patterns without extensions)
        if any(pattern in lower_name for pattern in ['img_', 'image_', 'photo_', 'pic_']):
            return '.jpg'
            
        # Document patterns
        if any(pattern in lower_name for pattern in ['doc_', 'document_', 'report_']):
            return '.pdf'
            
        # Try to detect from actual file if it exists
        if hasattr(self, 'current_folder') and self.current_folder:
            relative_path = data_item.get('relative_path', '')
            if relative_path:
                full_path = os.path.join(self.current_folder, relative_path, filename)
            else:
                full_path = os.path.join(self.current_folder, filename)
                
            if os.path.exists(full_path):
                try:
                    # Try to read file header to detect type
                    with open(full_path, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'\xff\xd8\xff'):  # JPEG
                            return '.jpg'
                        elif header.startswith(b'\x89PNG'):  # PNG
                            return '.png'
                        elif header.startswith(b'GIF8'):  # GIF
                            return '.gif'
                        elif header.startswith(b'%PDF'):  # PDF
                            return '.pdf'
                except:
                    pass  # If can't read, ignore
        
        # Default: no extension detected
        return ""
    
    def on_right_click(self, event):
        """Handle right-click for context menu"""
        item = self.tree.identify('item', event.x, event.y)
        if item:
            # Select the item
            self.tree.selection_set(item)
            
            # Create context menu
            context_menu = tk.Menu(self.root, tearoff=0)
            context_menu.add_command(label="Chỉnh Sửa Tên (F2)", command=lambda: self.edit_filename(item))
            context_menu.add_separator()
            
            # Check if this item has manual edit and add file operations
            item_index = self.tree.index(item)
            if 0 <= item_index < len(self.preview_data):
                data_item = self.preview_data[item_index]
                
                # File location options
                context_menu.add_command(label="Mở Thư Mục Chứa File", 
                                       command=lambda: self.open_file_location(item_index))
                context_menu.add_command(label="Sao Chép Đường Dẫn File", 
                                       command=lambda: self.copy_file_path(item_index))
                context_menu.add_separator()
                
                # Manual edit options
                if data_item.get('is_manual', False):
                    context_menu.add_command(label="Khôi Phục Tự Động", 
                                           command=lambda: self.reset_to_auto(item_index))
            
            # Show context menu
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def open_file_location(self, item_index):
        """Mở thư mục chứa file được chọn"""
        if not (0 <= item_index < len(self.preview_data)):
            return
        
        data_item = self.preview_data[item_index]
        
        try:
            # Smart path building - handle both relative_path and path in current field
            if data_item.get('relative_path'):
                # Case 1: Explicit relative_path field
                actual_filename = data_item.get('filename', os.path.basename(data_item['current']))
                file_path = os.path.join(self.current_folder, data_item['relative_path'], actual_filename)
                folder_path = os.path.join(self.current_folder, data_item['relative_path'])
            else:
                # Case 2: Path info might be in 'current' field
                current_path = data_item['current']
                if '\\' in current_path or '/' in current_path:
                    # Current contains path - use it directly
                    file_path = os.path.join(self.current_folder, current_path)
                    folder_path = os.path.dirname(file_path)
                else:
                    # Simple filename in root
                    file_path = os.path.join(self.current_folder, current_path)
                    folder_path = self.current_folder
            
            # Convert to absolute path for safety
            file_path = os.path.abspath(file_path)
            folder_path = os.path.abspath(folder_path)
            
            
            # Check if file exists
            if not os.path.exists(file_path):
                messagebox.showwarning("File không tồn tại", 
                                     f"Không thể tìm thấy file:\n{file_path}")
                return
            
            # Open file explorer and select the file
            import subprocess
            import platform
            
            system = platform.system()
            if system == "Windows":
                # Use Windows Explorer to select file
                subprocess.run(['explorer', '/select,', file_path], check=False)
            elif system == "Darwin":  # macOS
                subprocess.run(['open', '-R', file_path], check=False)
            else:  # Linux and others
                subprocess.run(['xdg-open', folder_path], check=False)
                
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {str(e)}")
    
    def open_selected_file_location(self):
        """Mở thư mục của file đang được chọn (keyboard shortcut)"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Thông báo", "Vui lòng chọn một file trong danh sách.")
            return
        
        try:
            item = selection[0]
            item_index = self.tree.index(item)
            self.open_file_location(item_index)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {str(e)}")
    
    def copy_file_path(self, item_index):
        """Sao chép đường dẫn file vào clipboard"""
        if not (0 <= item_index < len(self.preview_data)):
            return
        
        data_item = self.preview_data[item_index]
        
        try:
            # Smart path building - handle both relative_path and path in current field
            if data_item.get('relative_path'):
                # Case 1: Explicit relative_path field
                actual_filename = data_item.get('filename', os.path.basename(data_item['current']))
                file_path = os.path.join(self.current_folder, data_item['relative_path'], actual_filename)
            else:
                # Case 2: Path info might be in 'current' field
                current_path = data_item['current']
                if '\\' in current_path or '/' in current_path:
                    # Current contains path - use it directly
                    file_path = os.path.join(self.current_folder, current_path)
                else:
                    # Simple filename in root
                    file_path = os.path.join(self.current_folder, current_path)
            
            # Convert to absolute path
            abs_path = os.path.abspath(file_path)
            
            # Copy to clipboard silently
            self.root.clipboard_clear()
            self.root.clipboard_append(abs_path)
            self.root.update()  # Keep clipboard after window closes
            
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể sao chép đường dẫn: {str(e)}")
    
    def reset_to_auto(self, item_index):
        """Reset filename to automatic normalization"""
        if not (0 <= item_index < len(self.preview_data)):
            return
            
        data_item = self.preview_data[item_index]
        
        # Reset to automatic normalization
        normalized = self.normalizer.normalize_filename(data_item['filename'])
        relative_path = data_item['relative_path']
        
        if relative_path:
            display_new = os.path.join(relative_path, normalized)
        else:
            display_new = normalized
            
        # Update data
        data_item['custom_name'] = None
        data_item['new'] = display_new
        data_item['is_manual'] = False
        data_item['changed'] = data_item['filename'] != normalized
        data_item['status'] = "Sẵn sàng" if data_item['changed'] else "Không đổi"
        
        # Re-check for conflicts
        existing_files = [item.get('custom_name') or self.normalizer.normalize_filename(item['filename']) 
                         for i, item in enumerate(self.preview_data) 
                         if i != item_index and item['relative_path'] == relative_path]
        if normalized != data_item['filename'] and normalized in existing_files:
            data_item['status'] = "Trùng tên!"
        
        # Refresh display
        self.refresh_display()
    
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
                error_msg = f"Rename operation failed: {str(e)}"
                self.root.after(0, lambda msg=error_msg: self.show_error(msg))
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
                # Get the original filename and new filename
                old_filename = item['filename']
                
                # Priority: custom_name > suggested_name (from import) > normalize
                if item.get('custom_name'):
                    new_filename = item['custom_name']
                elif item.get('suggested_name'):
                    new_filename = item['suggested_name']
                else:
                    new_filename = self.normalizer.normalize_filename(old_filename)
                
                # Skip if names are the same (no change needed)
                if old_filename == new_filename:
                    continue
                
                # Handle path building - prioritize full_path for imported files
                if item.get('full_path') and os.path.exists(item['full_path']):
                    # For imported files, use the validated full path
                    old_path = item['full_path']
                    new_path = os.path.join(os.path.dirname(old_path), new_filename)
                elif 'relative_path' in item and item['relative_path']:
                    # File in subdirectory (traditional workflow)
                    old_path = os.path.join(self.current_folder, item['relative_path'], old_filename)
                    new_path = os.path.join(self.current_folder, item['relative_path'], new_filename)
                else:
                    # File in root directory (traditional workflow)
                    old_path = os.path.join(self.current_folder, old_filename)
                    new_path = os.path.join(self.current_folder, new_filename)
                
                # Debug info
                print(f"Rename attempt: {old_filename} -> {new_filename}")
                print(f"  Old path: {old_path}")  
                print(f"  New path: {new_path}")
                print(f"  Old exists: {os.path.exists(old_path)}")
                
                # Check if source file exists
                if not os.path.exists(old_path):
                    failed_count += 1
                    details.append(f"✗ {old_filename} → source file not found")
                    continue
                
                # Check if target already exists (handle case-insensitive filesystems)
                if os.path.exists(new_path):
                    # Check if it's the same file (case-only change on Windows)
                    if os.path.abspath(new_path).lower() == os.path.abspath(old_path).lower():
                        # Case-only rename on case-insensitive filesystem
                        # Need to do a two-step rename to avoid conflicts
                        try:
                            temp_path = old_path + ".tmp_rename"
                            os.rename(old_path, temp_path)
                            os.rename(temp_path, new_path)
                            success_count += 1
                            details.append(f"✓ {old_filename} → {new_filename} (case change)")
                            continue
                        except Exception as e:
                            failed_count += 1
                            details.append(f"✗ {old_filename} → case rename failed: {str(e)[:30]}")
                            continue
                    else:
                        # True conflict - different file with same name
                        failed_count += 1
                        details.append(f"✗ {old_filename} → target already exists: {new_filename}")
                        continue
                
                # Perform rename
                os.rename(old_path, new_path)
                success_count += 1
                details.append(f"✓ {old_filename} → {new_filename}")
                
            except PermissionError:
                failed_count += 1
                details.append(f"✗ {old_filename} → permission denied")
            except FileNotFoundError:
                failed_count += 1
                details.append(f"✗ {old_filename} → file not found")
            except FileExistsError:
                failed_count += 1
                details.append(f"✗ {old_filename} → target file already exists")
            except Exception as e:
                failed_count += 1
                error_msg = str(e)
                details.append(f"✗ {old_filename} → error: {error_msg[:50]}")
            
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
    
    def export_scan_results(self):
        """Export only files that need renaming from quick scan"""
        if not hasattr(self, 'scan_results') or not self.scan_results:
            messagebox.showinfo("No Scan Data", "Please run Quick Scan first to find files that need renaming.")
            return
        
        try:
            # Generate default filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"files_need_renaming_{timestamp}"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Files Need Renaming",
                initialfile=default_filename
            )
            
            if not file_path:
                return
            
            # Prepare data for export
            export_data = []
            for item in self.scan_results:
                try:
                    # Format file size
                    size = item['size']
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    
                    # Ensure consistent path formatting
                    original_path = os.path.join(item['relative_path'], item['original_name']) if item['relative_path'] else item['original_name']
                    full_path = os.path.abspath(item['full_path'])  # Normalize path
                    
                    export_data.append({
                        'Original Path': original_path,
                        'Current Name': item['original_name'],
                        'Suggested Name': item['suggested_name'],
                        'Relative Path': item['relative_path'] or '',  # Ensure empty string not None
                        'Full Path': full_path,
                        'Size': size_str,
                        'Action': 'RENAME'  # User can change to SKIP
                    })
                except Exception as item_error:
                    print(f"Error processing scan item: {item_error}")
                    continue
            
            # Export based on file extension
            if file_path.endswith('.xlsx'):
                try:
                    import pandas as pd
                    df = pd.DataFrame(export_data)
                    df.to_excel(file_path, index=False)
                except ImportError:
                    file_path = file_path.replace('.xlsx', '.csv')
                    self._export_to_csv(export_data, file_path)
            else:
                self._export_to_csv(export_data, file_path)
            
            messagebox.showinfo("Export Complete", 
                              f"Exported {len(export_data)} files need renaming to:\n{os.path.basename(file_path)}\n\n" +
                              "Next steps:\n" +
                              "1. Review and edit the file\n" +
                              "2. Change 'Action' to 'SKIP' for files you don't want to rename\n" +
                              "3. Import the file back using 'Import Rename List'")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting scan results: {str(e)}")
    
    def import_rename_list(self):
        """Import rename list from Excel/CSV for targeted renaming"""
        try:
            file_path = filedialog.askopenfilename(
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                title="Import Rename List"
            )
            
            if not file_path:
                return
            
            # Read the file
            import_data = []
            try:
                if file_path.endswith('.xlsx'):
                    import pandas as pd
                    df = pd.read_excel(file_path)
                else:
                    import pandas as pd
                    df = pd.read_csv(file_path, encoding='utf-8-sig')
                
                # Convert to list of dicts
                import_data = df.to_dict('records')
                
            except ImportError:
                # Fallback to CSV without pandas
                if file_path.endswith('.xlsx'):
                    messagebox.showerror("Import Error", "Cannot read Excel files without pandas library. Please use CSV format.")
                    return
                
                import csv
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    import_data = list(reader)
            
            # Validate and process import data
            valid_items = []
            for row in import_data:
                try:
                    # Check required columns
                    if not all(col in row for col in ['Current Name', 'Suggested Name', 'Full Path', 'Action']):
                        continue
                    
                    # Skip items marked as SKIP
                    if str(row.get('Action', '')).upper() == 'SKIP':
                        continue
                    
                    # Validate file exists - normalize path first
                    full_path = os.path.abspath(row['Full Path'].strip())
                    if not os.path.exists(full_path):
                        print(f"File not found: {full_path}")
                        # Try alternative path construction if full path fails
                        if self.current_folder and row.get('Relative Path'):
                            alt_path = os.path.join(self.current_folder, row['Relative Path'], row['Current Name'])
                            alt_path = os.path.abspath(alt_path)
                            if os.path.exists(alt_path):
                                full_path = alt_path
                                print(f"Found alternative path: {alt_path}")
                            else:
                                continue
                        elif self.current_folder:
                            alt_path = os.path.join(self.current_folder, row['Current Name'])
                            alt_path = os.path.abspath(alt_path)
                            if os.path.exists(alt_path):
                                full_path = alt_path
                                print(f"Found alternative path: {alt_path}")
                            else:
                                continue
                        else:
                            continue
                    
                    # Add to valid items
                    valid_items.append({
                        'filename': row['Current Name'],
                        'suggested_name': row['Suggested Name'],
                        'full_path': full_path,
                        'relative_path': row.get('Relative Path', ''),
                        'current': row.get('Original Path', row['Current Name']),
                        'new': row['Suggested Name'],
                        'selected': True,
                        'changed': row['Current Name'] != row['Suggested Name'],
                        'status': 'Từ import list',
                        'size': self._get_file_size_str(full_path),
                        'is_manual': False,
                        'custom_name': None
                    })
                    
                    print(f"Added to import: {row['Current Name']} -> {row['Suggested Name']} at {full_path}")
                    
                except Exception as row_error:
                    print(f"Error processing row: {row_error}")
                    continue
            
            if not valid_items:
                messagebox.showwarning("No Valid Data", 
                                     "No valid rename operations found in the import file.\n\n" +
                                     "Please check:\n" +
                                     "• File has required columns\n" + 
                                     "• Files still exist on disk\n" +
                                     "• Action is set to RENAME (not SKIP)")
                return
            
            # Load into preview
            self.preview_data = valid_items
            self.update_preview_display(valid_items)
            
            # Update status
            self.status_var.set(f"Imported {len(valid_items)} files from rename list")
            
            # Enable rename button
            self.rename_button.config(state="normal")
            
            messagebox.showinfo("Import Complete", 
                              f"Successfully imported {len(valid_items)} files for renaming.\n\n" +
                              "Review the list and click 'Rename Selected Files' to proceed.")
            
        except Exception as e:
            messagebox.showerror("Import Error", f"Error importing rename list: {str(e)}")
    
    def _get_file_size_str(self, file_path: str) -> str:
        """Get formatted file size string"""
        try:
            size = os.path.getsize(file_path)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except:
            return "0 B"

    def export_preview(self):
        """Export preview list to Excel/CSV với more options"""
        if not self.preview_data:
            messagebox.showinfo("Info", "No preview data to export.")
            return
        
        try:
            # Generate default filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"file_{timestamp}"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Preview List",
                initialfile=default_filename
            )
            
            if not file_path:
                return
            
            # Prepare data for export - clean unicode strings
            export_data = []
            for item in self.preview_data:
                try:
                    export_data.append({
                        'Selected': 'Yes' if item['selected'] else 'No',
                        'Current Name': str(item['current']).encode('utf-8', errors='replace').decode('utf-8'),
                        'New Name': str(item['new']).encode('utf-8', errors='replace').decode('utf-8'),
                        'Status': str(item['status']).encode('utf-8', errors='replace').decode('utf-8'),
                        'Size': str(item['size']),
                        'Will Change': 'Yes' if item['changed'] else 'No'
                    })
                except Exception as item_error:
                    print(f"Error processing item: {item_error}")
                    continue
            
            # Export based on file extension
            if file_path.endswith('.xlsx'):
                try:
                    # Try pandas first
                    import pandas as pd
                    df = pd.DataFrame(export_data)
                    df.to_excel(file_path, index=False)
                except ImportError:
                    # Fallback to CSV if pandas not available
                    file_path = file_path.replace('.xlsx', '.csv')
                    self._export_to_csv(export_data, file_path)
            else:
                # Export to CSV
                self._export_to_csv(export_data, file_path)
            
            messagebox.showinfo("Export Complete", 
                              f"Exported {len(export_data)} files to:\n{os.path.basename(file_path)}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting: {str(e)}")
    
    def _export_to_csv(self, data, file_path):
        """Export data to CSV without pandas dependency"""
        import csv
        
        if not data:
            return
        
        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = data[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
    
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