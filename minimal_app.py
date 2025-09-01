#!/usr/bin/env python3
"""
Minimal working File Rename Tool
Simplified version that actually works
"""

import os
import sys
import locale
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from pathlib import Path
import unidecode

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass

class MinimalFileRenameTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("File Rename Tool - Minimal Version")
        self.root.geometry("800x600")
        
        # Variables
        self.folder_path = tk.StringVar()
        self.files_data = []
        
        self.create_gui()
        
    def create_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Folder selection
        folder_frame = ttk.Frame(main_frame)
        folder_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        folder_frame.columnconfigure(1, weight=1)
        
        ttk.Label(folder_frame, text="Folder:").grid(row=0, column=0, padx=(0, 5))
        ttk.Entry(folder_frame, textvariable=self.folder_path, state="readonly").grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(folder_frame, text="Browse", command=self.browse_folder).grid(row=0, column=2)
        
        # File list
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for file preview
        columns = ("current", "new")
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        self.tree.heading('current', text='Current Name')
        self.tree.heading('new', text='New Name (Vietnamese Normalized)')
        self.tree.column('current', width=300)
        self.tree.column('new', width=300)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Select a folder to begin")
        self.status_label.grid(row=2, column=0, pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0)
        
        ttk.Button(button_frame, text="Rename Files", command=self.rename_files, state="disabled").grid(row=0, column=0, padx=(0, 5))
        self.rename_button = ttk.Button(button_frame, text="Rename Files", command=self.rename_files, state="disabled")
        self.rename_button.grid(row=0, column=0, padx=(0, 5))
        
        ttk.Button(button_frame, text="Exit", command=self.root.quit).grid(row=0, column=1)
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
    
    def browse_folder(self):
        """Browse for folder"""
        try:
            folder = filedialog.askdirectory(title="Select folder with files to rename")
            if folder:
                self.folder_path.set(folder)
                self.load_files_async(folder)
        except Exception as e:
            messagebox.showerror("Error", f"Error selecting folder: {e}")
    
    def load_files_async(self, folder):
        """Load files in background thread"""
        self.status_label.config(text="Loading files...")
        self.rename_button.config(state="disabled")
        
        def load_files():
            try:
                files = []
                for item in os.listdir(folder):
                    if os.path.isfile(os.path.join(folder, item)):
                        # Generate normalized name
                        normalized = self.normalize_vietnamese(item)
                        files.append((item, normalized))
                
                # Update UI in main thread
                self.root.after(0, self.update_file_list, files)
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error loading files: {e}"))
        
        # Start background thread
        thread = threading.Thread(target=load_files, daemon=True)
        thread.start()
    
    def update_file_list(self, files):
        """Update file list in UI thread"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add new items
        self.files_data = files
        for current, new in files:
            self.tree.insert('', 'end', values=(current, new))
        
        self.status_label.config(text=f"Found {len(files)} files")
        self.rename_button.config(state="normal" if files else "disabled")
    
    def normalize_vietnamese(self, filename):
        """Simple Vietnamese normalization"""
        name, ext = os.path.splitext(filename)
        
        # Remove diacritics
        normalized = unidecode.unidecode(name)
        
        # Clean up
        normalized = normalized.strip()
        
        return normalized + ext
    
    def rename_files(self):
        """Rename files"""
        if not self.files_data:
            return
        
        folder = self.folder_path.get()
        if not folder:
            return
        
        result = messagebox.askyesno("Confirm", f"Rename {len(self.files_data)} files?")
        if not result:
            return
        
        try:
            renamed_count = 0
            for current, new in self.files_data:
                if current != new:
                    old_path = os.path.join(folder, current)
                    new_path = os.path.join(folder, new)
                    
                    if not os.path.exists(new_path):
                        os.rename(old_path, new_path)
                        renamed_count += 1
            
            messagebox.showinfo("Success", f"Renamed {renamed_count} files successfully!")
            self.load_files_async(folder)  # Refresh list
            
        except Exception as e:
            messagebox.showerror("Error", f"Error renaming files: {e}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = MinimalFileRenameTool()
        app.run()
    except Exception as e:
        import traceback
        with open("minimal_app_error.txt", "w", encoding="utf-8") as f:
            f.write(f"Error: {e}\n")
            traceback.print_exc(file=f)
        
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Error", f"Application failed to start: {e}")
        except:
            pass