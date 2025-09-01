#!/usr/bin/env python3
"""
Simple launcher for File Rename Tool
"""

import sys
import os
import tkinter as tk
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import and launch main application
if __name__ == "__main__":
    try:
        # Try to import the main application
        from src.ui.components.app_controller import AppController
        
        # Create and start application controller (it creates its own window)
        app = AppController()
        
        # Start the application
        print("Starting File Rename Tool...")
        print("Select a folder to begin renaming files")
        
        app.run()
        
    except ImportError as e:
        print(f"❌ Error importing application: {e}")
        
        # Fallback - create a simple demo interface
        print("⚠️  Running fallback interface...")
        
        root = tk.Tk()
        root.title("File Rename Tool (Fallback Mode)")
        root.geometry("600x400")
        
        label = tk.Label(root, text="File Rename Tool\n(Fallback Mode)", 
                        font=('Arial', 16, 'bold'))
        label.pack(pady=50)
        
        info_label = tk.Label(root, 
                            text="The full application could not load.\nPlease check your Python environment.",
                            font=('Arial', 10))
        info_label.pack(pady=20)
        
        root.mainloop()
        
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()