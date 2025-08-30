#!/usr/bin/env python3
"""
File Rename Tool - Main Entry Point

A desktop application for batch file renaming with an intuitive folder selection
and file list display functionality.
"""

import sys
import os
import argparse
import tkinter as tk
from tkinter import messagebox

# Add src directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from ui.components.app_controller import AppController
except ImportError as e:
    print(f"Error importing application components: {e}")
    sys.exit(1)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="File Rename Tool - Desktop application for batch file renaming"
    )
    parser.add_argument(
        "--folder", 
        type=str, 
        help="Initial folder path to display",
        metavar="PATH"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="File Rename Tool 2.0"  # Should sync with packaging/version.py
    )
    
    return parser.parse_args()


def validate_initial_folder(folder_path: str) -> bool:
    if not folder_path:
        return True  # No folder specified, that's fine
    
    if not os.path.exists(folder_path):
        messagebox.showerror(
            "Invalid Folder",
            f"The specified folder does not exist:\n{folder_path}"
        )
        return False
    
    if not os.path.isdir(folder_path):
        messagebox.showerror(
            "Invalid Folder", 
            f"The specified path is not a folder:\n{folder_path}"
        )
        return False
    
    if not os.access(folder_path, os.R_OK):
        messagebox.showerror(
            "Access Denied",
            f"Cannot access the specified folder:\n{folder_path}"
        )
        return False
    
    return True


def main():
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Validate initial folder if provided
        if args.folder and not validate_initial_folder(args.folder):
            return 1
        
        # Create and configure application
        app_controller = AppController()
        
        # Set initial folder if provided
        if args.folder:
            try:
                app_controller.set_initial_folder(args.folder)
            except Exception as e:
                messagebox.showwarning(
                    "Folder Loading Warning",
                    f"Could not load initial folder:\n{args.folder}\n\nError: {str(e)}"
                )
        
        # Run application
        app_controller.run()
        
        return 0
        
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        return 130
        
    except Exception as e:
        error_msg = f"Critical error starting application: {str(e)}"
        print(error_msg)
        
        # Try to show error dialog if possible
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Critical Error", error_msg)
            root.destroy()
        except:
            pass  # Fallback to console error already printed
        
        return 1


if __name__ == "__main__":
    sys.exit(main())