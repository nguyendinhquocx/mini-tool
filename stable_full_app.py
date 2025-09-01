#!/usr/bin/env python3
"""
Vietnamese File Rename Tool - Stable Full-Featured Version
Based on PRD and Epic 2 completion requirements with stable architecture
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

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass

class ConfigService:
    """Configuration service with file-based storage"""
    def __init__(self):
        self.config_file = "app_config.json"
        self.config = self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {"recent_folders": [], "max_recent": 10}
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    def add_recent_folder(self, folder_path: str):
        recent = self.config["recent_folders"]
        if folder_path in recent:
            recent.remove(folder_path)
        recent.insert(0, folder_path)
        recent = recent[:self.config["max_recent"]]
        self.config["recent_folders"] = recent
        self.save_config()

class HistoryService:
    """Operation history service with SQLite storage"""
    def __init__(self):
        self.db_file = "operation_history.db"
        self.init_db()
    
    def init_db(self):
        try:
            conn = sqlite3.connect(self.db_file)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY,
                    timestamp TEXT,
                    operation_type TEXT,
                    folder_path TEXT,
                    files_count INTEGER,
                    success_count INTEGER,
                    details TEXT
                )
            ''')
            conn.commit()
            conn.close()
        except:
            pass
    
    def save_operation(self, operation_type: str, folder_path: str, 
                      files_count: int, success_count: int, details: str = ""):
        try:
            conn = sqlite3.connect(self.db_file)
            conn.execute('''
                INSERT INTO operations 
                (timestamp, operation_type, folder_path, files_count, success_count, details)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), operation_type, folder_path, 
                  files_count, success_count, details))
            conn.commit()
            conn.close()
        except:
            pass
    
    def get_last_operation(self):
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.execute('''
                SELECT * FROM operations ORDER BY timestamp DESC LIMIT 1
            ''')
            result = cursor.fetchone()
            conn.close()
            return result
        except:
            return None

class VietnameseNormalizer:
    """Vietnamese text normalization with caching"""
    def __init__(self):
        self.cache = {}
    
    def normalize_filename(self, filename: str) -> str:
        if filename in self.cache:
            return self.cache[filename]
        
        name, ext = os.path.splitext(filename)
        
        # Remove diacritics
        normalized = unidecode.unidecode(name)
        
        # Clean special characters
        normalized = self._clean_special_chars(normalized)
        
        # Normalize whitespace
        normalized = ' '.join(normalized.split())
        normalized = normalized.strip()
        
        result = normalized + ext
        self.cache[filename] = result
        return result
    
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

class ProgressDialog:
    """Progress dialog for batch operations"""
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.dialog = None
        self.progress_var = None
        self.status_var = None
        self.cancelled = False
    
    def show(self, title: str = "Processing..."):
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(title)
        self.dialog.geometry("400x150")
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
        
        # Cancel button
        cancel_button = tk.Button(
            self.dialog, 
            text="Cancel", 
            command=self._cancel
        )
        cancel_button.pack(pady=10)
        
        return self
    
    def update_progress(self, percentage: float, status: str = ""):
        if self.dialog and self.progress_var:
            self.progress_var.set(percentage)
            if status and self.status_var:
                self.status_var.set(status)
            self.dialog.update()
    
    def _cancel(self):
        self.cancelled = True
    
    def is_cancelled(self):
        return self.cancelled
    
    def close(self):
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None

class StableFileRenameApp:
    """Main application class with stable architecture"""
    
    def __init__(self):
        # Clear command line arguments to prevent tkinter option conflicts
        original_argv = sys.argv.copy()
        sys.argv = [sys.argv[0]]  # Keep only the script name
        
        try:
            self.root = tk.Tk()
        finally:
            # Restore original arguments
            sys.argv = original_argv
        self.root.title("Vietnamese File Rename Tool - Full Featured")
        self.root.geometry("900x700")
        
        # Services
        self.config_service = ConfigService()
        self.history_service = HistoryService()
        self.normalizer = VietnameseNormalizer()
        
        # State
        self.current_folder = ""
        self.files_data = []
        self.preview_data = []
        
        # UI Components
        self.folder_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Select a folder to begin")
        
        self.setup_ui()
        self.setup_bindings()
    
    def setup_ui(self):
        """Setup the user interface"""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Folder selection section
        folder_frame = ttk.LabelFrame(main_frame, text="Folder Selection", padding="10")
        folder_frame.pack(fill=tk.X, pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Label(folder_frame, text="Folder:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
        
        self.folder_entry = ttk.Entry(folder_frame, textvariable=self.folder_var, state="readonly")
        self.folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.browse_button = ttk.Button(folder_frame, text="Browse", command=self.browse_folder)
        self.browse_button.grid(row=0, column=2)
        
        # Recent folders dropdown
        ttk.Label(folder_frame, text="Recent:").grid(row=1, column=0, padx=(0, 5), sticky=tk.W, pady=(5, 0))
        
        self.recent_combo = ttk.Combobox(folder_frame, state="readonly")
        self.recent_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5), pady=(5, 0))
        self.recent_combo.bind('<<ComboboxSelected>>', self.on_recent_selected)
        self.update_recent_folders()
        
        # File preview section
        preview_frame = ttk.LabelFrame(main_frame, text="File Rename Preview", padding="10")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Treeview for file preview
        columns = ("current", "new", "status")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show='headings', height=15)
        self.tree.heading('current', text='Current Name')
        self.tree.heading('new', text='New Name (Normalized)')
        self.tree.heading('status', text='Status')
        
        self.tree.column('current', width=300)
        self.tree.column('new', width=300)
        self.tree.column('status', width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        # Status and action section
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X)
        
        # Status label
        self.status_label = ttk.Label(action_frame, textvariable=self.status_var)
        self.status_label.pack(side=tk.LEFT)
        
        # Action buttons
        button_frame = ttk.Frame(action_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.rename_button = ttk.Button(button_frame, text="Rename Files", 
                                       command=self.rename_files, state="disabled")
        self.rename_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.undo_button = ttk.Button(button_frame, text="Undo Last Operation", 
                                     command=self.undo_last, state="disabled")
        self.undo_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.export_button = ttk.Button(button_frame, text="Export List", 
                                       command=self.export_preview)
        self.export_button.pack(side=tk.LEFT)
    
    def setup_bindings(self):
        """Setup event bindings"""
        self.folder_var.trace('w', self.on_folder_changed)
        
        # Check for last operation to enable undo
        if self.history_service.get_last_operation():
            self.undo_button.config(state="normal")
    
    def browse_folder(self):
        """Browse for folder with error handling"""
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
    
    def on_folder_changed(self, *args):
        """Handle folder path changes with immediate UI feedback"""
        folder_path = self.folder_var.get()
        if not folder_path or not os.path.exists(folder_path):
            self.clear_preview()
            return
        
        self.current_folder = folder_path
        self.status_var.set("Loading files...")
        self.rename_button.config(state="disabled")
        
        # Force UI update before processing
        self.root.update_idletasks()
        
        # Process in background thread
        def load_files():
            try:
                self.load_files_from_folder(folder_path)
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Error loading files: {str(e)}"))
        
        thread = threading.Thread(target=load_files, daemon=True)
        thread.start()
    
    def load_files_from_folder(self, folder_path: str):
        """Load and process files from folder"""
        try:
            # Get all files
            all_items = os.listdir(folder_path)
            files = [item for item in all_items 
                    if os.path.isfile(os.path.join(folder_path, item))]
            
            # Limit for performance
            if len(files) > 1000:
                files = files[:1000]
                self.root.after(0, lambda: self.status_var.set(
                    f"Showing first 1000 of {len(all_items)} files"
                ))
            
            # Process files
            preview_data = []
            for i, filename in enumerate(files):
                try:
                    normalized = self.normalizer.normalize_filename(filename)
                    status = "Ready" if filename != normalized else "No change"
                    
                    # Check for conflicts
                    if normalized != filename and normalized in files:
                        status = "Conflict!"
                    
                    preview_data.append({
                        'current': filename,
                        'new': normalized,
                        'status': status,
                        'changed': filename != normalized
                    })
                    
                    # Update progress every 50 files
                    if i % 50 == 0:
                        progress = (i / len(files)) * 100
                        self.root.after(0, lambda p=progress: 
                                      self.status_var.set(f"Processing... {p:.0f}%"))
                        
                except Exception as e:
                    preview_data.append({
                        'current': filename,
                        'new': filename,
                        'status': f"Error: {str(e)[:20]}",
                        'changed': False
                    })
            
            # Update UI in main thread
            self.root.after(0, lambda: self.update_preview_display(preview_data))
            
        except Exception as e:
            self.root.after(0, lambda: self.show_error(f"Error processing folder: {str(e)}"))
    
    def update_preview_display(self, preview_data: List[Dict]):
        """Update the preview display with processed data"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Add new items
            self.preview_data = preview_data
            changes_count = sum(1 for item in preview_data if item['changed'])
            
            for item in preview_data:
                # Color code based on status
                tags = []
                if item['status'] == "Conflict!":
                    tags = ['conflict']
                elif item['changed']:
                    tags = ['changed']
                
                self.tree.insert('', 'end', values=(
                    item['current'], item['new'], item['status']
                ), tags=tags)
            
            # Configure tags
            self.tree.tag_configure('conflict', background='#ffcccc')
            self.tree.tag_configure('changed', background='#ccffcc')
            
            # Update status and buttons
            total = len(preview_data)
            self.status_var.set(f"Found {total} files, {changes_count} will be renamed")
            self.rename_button.config(state="normal" if changes_count > 0 else "disabled")
            
        except Exception as e:
            self.show_error(f"Error updating display: {str(e)}")
    
    def rename_files(self):
        """Execute batch rename operation"""
        if not self.preview_data or not self.current_folder:
            return
        
        # Count files to rename
        files_to_rename = [item for item in self.preview_data 
                          if item['changed'] and item['status'] != "Conflict!"]
        
        if not files_to_rename:
            messagebox.showinfo("Info", "No files need to be renamed.")
            return
        
        # Confirm operation
        result = messagebox.askyesno(
            "Confirm Rename", 
            f"Rename {len(files_to_rename)} files?\n\nThis action can be undone."
        )
        
        if not result:
            return
        
        # Show progress dialog
        progress = ProgressDialog(self.root)
        progress.show("Renaming Files")
        
        # Execute in background
        def rename_operation():
            try:
                self.execute_rename_operation(files_to_rename, progress)
            except Exception as e:
                self.root.after(0, lambda: self.show_error(f"Rename operation failed: {str(e)}"))
            finally:
                self.root.after(0, progress.close)
        
        thread = threading.Thread(target=rename_operation, daemon=True)
        thread.start()
    
    def execute_rename_operation(self, files_to_rename: List[Dict], progress: ProgressDialog):
        """Execute the actual rename operation"""
        success_count = 0
        details = []
        
        total = len(files_to_rename)
        
        for i, item in enumerate(files_to_rename):
            if progress.is_cancelled():
                break
            
            try:
                old_path = os.path.join(self.current_folder, item['current'])
                new_path = os.path.join(self.current_folder, item['new'])
                
                if not os.path.exists(new_path):
                    os.rename(old_path, new_path)
                    success_count += 1
                    details.append(f"✓ {item['current']} → {item['new']}")
                else:
                    details.append(f"✗ {item['current']} → target exists")
                
            except Exception as e:
                details.append(f"✗ {item['current']} → error: {str(e)}")
            
            # Update progress
            percentage = ((i + 1) / total) * 100
            status = f"Renaming {i + 1}/{total}..."
            self.root.after(0, lambda p=percentage, s=status: progress.update_progress(p, s))
        
        # Save operation to history
        self.history_service.save_operation(
            "batch_rename", self.current_folder, total, success_count,
            "\n".join(details)
        )
        
        # Update UI
        self.root.after(0, lambda: self.after_rename_operation(success_count, total))
    
    def after_rename_operation(self, success_count: int, total: int):
        """Handle post-rename operations"""
        messagebox.showinfo("Operation Complete", 
                           f"Renamed {success_count} of {total} files successfully.")
        
        # Enable undo button
        self.undo_button.config(state="normal")
        
        # Refresh the current folder
        if self.current_folder:
            self.folder_var.set("")  # Clear to trigger refresh
            self.folder_var.set(self.current_folder)
    
    def undo_last(self):
        """Undo the last operation"""
        last_op = self.history_service.get_last_operation()
        if not last_op:
            messagebox.showinfo("Info", "No operation to undo.")
            return
        
        # Parse operation details
        details = last_op[6].split('\n') if last_op[6] else []
        successful_renames = [line for line in details if line.startswith('✓')]
        
        if not successful_renames:
            messagebox.showinfo("Info", "No successful renames to undo.")
            return
        
        # Confirm undo
        result = messagebox.askyesno(
            "Confirm Undo",
            f"Undo {len(successful_renames)} file renames from the last operation?"
        )
        
        if not result:
            return
        
        # Execute undo
        try:
            undo_count = 0
            for line in successful_renames:
                # Parse: "✓ oldname → newname"
                if ' → ' in line:
                    parts = line[2:].split(' → ')  # Remove "✓ " prefix
                    if len(parts) == 2:
                        old_name, new_name = parts
                        old_path = os.path.join(self.current_folder, new_name)
                        new_path = os.path.join(self.current_folder, old_name)
                        
                        if os.path.exists(old_path) and not os.path.exists(new_path):
                            os.rename(old_path, new_path)
                            undo_count += 1
            
            messagebox.showinfo("Undo Complete", f"Undid {undo_count} file renames.")
            
            # Refresh display
            if self.current_folder:
                self.folder_var.set("")
                self.folder_var.set(self.current_folder)
            
        except Exception as e:
            messagebox.showerror("Undo Error", f"Error during undo: {str(e)}")
    
    def export_preview(self):
        """Export preview list to Excel/CSV"""
        if not self.preview_data:
            messagebox.showinfo("Info", "No preview data to export.")
            return
        
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv")],
                title="Export Preview List"
            )
            
            if not file_path:
                return
            
            # Create DataFrame
            df = pd.DataFrame(self.preview_data)
            
            # Export based on file extension
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            
            messagebox.showinfo("Export Complete", f"Preview exported to: {file_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Error exporting: {str(e)}")
    
    def clear_preview(self):
        """Clear the preview display"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.preview_data = []
        self.status_var.set("No folder selected")
        self.rename_button.config(state="disabled")
    
    def show_error(self, message: str):
        """Show error message"""
        messagebox.showerror("Error", message)
        self.status_var.set("Error occurred")
    
    def run(self):
        """Start the application"""
        try:
            self.root.mainloop()
        except Exception as e:
            messagebox.showerror("Critical Error", f"Application error: {str(e)}")

if __name__ == "__main__":
    try:
        app = StableFileRenameApp()
        app.run()
    except Exception as e:
        import traceback
        error_msg = f"Failed to start application: {str(e)}"
        
        # Try to show error dialog
        try:
            root = tk.Tk()
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