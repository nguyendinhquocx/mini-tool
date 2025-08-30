"""
Error handling utilities for UI components
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for UI components"""
    
    @staticmethod
    def handle_ui_error(error: Exception, context: str = "UI Operation", 
                       show_dialog: bool = True, parent: Optional[tk.Widget] = None):
        """Handle UI errors with consistent logging and user feedback"""
        error_msg = f"{context}: {str(error)}"
        
        # Log error
        logger.error(error_msg, exc_info=True)
        
        # Show user dialog if requested
        if show_dialog:
            try:
                messagebox.showerror("Error", error_msg, parent=parent)
            except Exception:
                # Fallback if dialog fails
                print(f"Error dialog failed. Original error: {error_msg}")
    
    @staticmethod
    def handle_validation_error(message: str, show_dialog: bool = True, 
                               parent: Optional[tk.Widget] = None):
        """Handle validation errors"""
        logger.warning(f"Validation error: {message}")
        
        if show_dialog:
            try:
                messagebox.showwarning("Validation Error", message, parent=parent)
            except Exception:
                print(f"Validation dialog failed. Message: {message}")
    
    @staticmethod
    def safe_execute(func: Callable, context: str = "Operation", 
                    show_dialog: bool = True, parent: Optional[tk.Widget] = None,
                    default_return=None):
        """Safely execute a function with error handling"""
        try:
            return func()
        except Exception as e:
            ErrorHandler.handle_ui_error(e, context, show_dialog, parent)
            return default_return