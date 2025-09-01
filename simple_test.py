#!/usr/bin/env python3
"""
Simple test launcher to debug UI issue
"""

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os

def browse_folder():
    """Simple folder browser test"""
    try:
        folder_path = filedialog.askdirectory(title="Select folder")
        if folder_path:
            folder_var.set(folder_path)
            files = os.listdir(folder_path)
            result_label.config(text=f"Found {len(files)} items")
    except Exception as e:
        messagebox.showerror("Error", f"Error: {e}")

# Create simple GUI
root = tk.Tk()
root.title("Simple Test")
root.geometry("400x200")

# Folder selection
ttk.Label(root, text="Folder:").pack(pady=5)
folder_var = tk.StringVar()
folder_frame = ttk.Frame(root)
folder_frame.pack(fill=tk.X, padx=10)

ttk.Entry(folder_frame, textvariable=folder_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
ttk.Button(folder_frame, text="Browse", command=browse_folder).pack(side=tk.RIGHT)

# Result
result_label = ttk.Label(root, text="No folder selected")
result_label.pack(pady=20)

if __name__ == "__main__":
    root.mainloop()