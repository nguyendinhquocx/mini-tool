#!/usr/bin/env python3
"""
Debug launcher to identify exact issue
"""

import sys
import os
import traceback
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("=== Debug Launcher ===")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}...")

try:
    print("\n1. Testing basic imports...")
    import tkinter as tk
    print("OK tkinter")
    
    import pandas as pd
    print("OK pandas")
    
    import unidecode
    print("OK unidecode")
    
    print("\n2. Testing app imports...")
    from src.ui.components.app_controller import AppController
    print("OK AppController import")
    
    print("\n3. Creating simple GUI...")
    root = tk.Tk()
    root.title("Debug Test")
    root.geometry("300x100")
    
    def test_browse():
        from tkinter import filedialog
        folder = filedialog.askdirectory()
        if folder:
            print(f"Selected folder: {folder}")
            # Test simple folder scan
            files = os.listdir(folder)
            print(f"Found {len(files)} items")
    
    tk.Button(root, text="Test Browse", command=test_browse).pack(pady=20)
    tk.Button(root, text="Close", command=root.quit).pack()
    
    print("OK Simple GUI created. Starting mainloop...")
    root.mainloop()
    print("OK GUI closed normally")
    
except Exception as e:
    print(f"\nERROR: {e}")
    print(f"Error type: {type(e).__name__}")
    print("Full traceback:")
    traceback.print_exc()
    
    # Keep console open on error
    input("\nPress Enter to exit...")