#!/usr/bin/env python3
"""
Working launcher with proper Unicode handling
"""

import sys
import os
import locale
from pathlib import Path

# Set UTF-8 encoding for proper Unicode support
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass  # Continue with default

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

if __name__ == "__main__":
    try:
        # Import and launch with proper error handling
        from src.ui.components.app_controller import AppController
        
        # Launch app
        app = AppController()
        app.main_window.root.mainloop()
        
    except Exception as e:
        import tkinter.messagebox as msgbox
        error_msg = f"Application Error:\n{str(e)}\n\nError Type: {type(e).__name__}"
        msgbox.showerror("Application Error", error_msg)
        
        # Log to file instead of console
        with open("error_log.txt", "w", encoding="utf-8") as f:
            import traceback
            f.write(f"Application Error: {e}\n")
            f.write(f"Error Type: {type(e).__name__}\n")
            f.write("Full traceback:\n")
            traceback.print_exc(file=f)