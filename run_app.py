#!/usr/bin/env python3
"""
Production launcher for File Rename Tool with proper Unicode handling
"""

import sys
import os
import locale
from pathlib import Path

# Set UTF-8 encoding for proper Unicode support on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'C.UTF-8')
    except:
        pass  # Continue with default locale

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import and launch main application
if __name__ == "__main__":
    try:
        # Try to import the main application
        from src.ui.components.app_controller import AppController
        
        # Disable console logging to prevent encoding issues with Vietnamese paths
        import logging
        logging.getLogger().handlers = []  # Remove console handlers
        
        # Create and start application controller (it creates its own window)
        app = AppController()
        
        # Keep running until user closes the application
        app.main_window.root.mainloop()
        
    except ImportError as e:
        import tkinter as tk
        import tkinter.messagebox as msgbox
        error_msg = f"Import Error:\n{str(e)}\n\nPlease ensure all dependencies are installed:\npip install -r requirements.txt"
        
        # Show simple error dialog
        root = tk.Tk()
        root.withdraw()  # Hide root window
        msgbox.showerror("Import Error", error_msg)
        
    except Exception as e:
        import tkinter as tk
        import tkinter.messagebox as msgbox
        error_msg = f"Application Error:\n{str(e)}\n\nError Type: {type(e).__name__}"
        
        # Show error dialog
        try:
            root = tk.Tk()
            root.withdraw()  # Hide root window
            msgbox.showerror("Application Error", error_msg)
        except:
            pass
        
        # Log to file instead of console to avoid encoding issues
        try:
            with open("error_log.txt", "w", encoding="utf-8") as f:
                import traceback
                f.write(f"Application Error: {e}\n")
                f.write(f"Error Type: {type(e).__name__}\n")
                f.write("Full traceback:\n")
                traceback.print_exc(file=f)
        except:
            pass  # Ignore logging errors