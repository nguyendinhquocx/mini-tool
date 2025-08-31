"""
Error handling utilities for UI components with advanced error handling integration
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable
import logging

from ...core.models.error_models import ApplicationError, ValidationResult
from ...core.utils.error_handler import ApplicationErrorException
from .advanced_error_handler import AdvancedErrorHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ErrorHandler:
    """Centralized error handling for UI components with advanced recovery options"""
    
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
    def handle_application_error(app_error: ApplicationError, parent: Optional[tk.Widget] = None) -> Optional[str]:
        """Handle ApplicationError with advanced recovery options"""
        return AdvancedErrorHandler.handle_application_error(app_error, parent)
    
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
    def handle_validation_result(result: ValidationResult, parent: Optional[tk.Widget] = None) -> bool:
        """Handle ValidationResult with advanced dialog"""
        return AdvancedErrorHandler.handle_validation_result(result, parent)
    
    @staticmethod
    def safe_execute(func: Callable, context: str = "Operation", 
                    show_dialog: bool = True, parent: Optional[tk.Widget] = None,
                    default_return=None):
        """Safely execute a function with error handling"""
        try:
            return func()
        except ApplicationErrorException as e:
            if show_dialog:
                recovery_action = ErrorHandler.handle_application_error(e.application_error, parent)
                return recovery_action if recovery_action else default_return
            return default_return
        except Exception as e:
            ErrorHandler.handle_ui_error(e, context, show_dialog, parent)
            return default_return
    
    @staticmethod
    def safe_execute_with_recovery(func: Callable, context: str = "Operation", 
                                 parent: Optional[tk.Widget] = None,
                                 default_return=None):
        """Execute function with advanced error handling and recovery options"""
        return AdvancedErrorHandler.safe_execute_with_recovery(func, context, parent, default_return)