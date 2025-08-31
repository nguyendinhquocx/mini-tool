"""
Drag and Drop Handler Component

Handles folder drag-and-drop operations with visual feedback and validation.
Integrates with Windows Explorer drag-drop functionality.
"""

import tkinter as tk
from tkinter import ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
from typing import Callable, Optional, List, Dict, Any
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DragVisualFeedback:
    """Visual feedback states for drag operations"""
    
    DRAG_STATES = {
        'idle': {
            'bg': '#f0f0f0', 
            'border': '1px solid #ccc',
            'relief': tk.FLAT,
            'cursor': 'arrow'
        },
        'drag_over_valid': {
            'bg': '#e7f3ff', 
            'border': '2px dashed #007acc',
            'relief': tk.RAISED,
            'cursor': 'hand2'
        },
        'drag_over_invalid': {
            'bg': '#ffe7e7', 
            'border': '2px dashed #cc0000',
            'relief': tk.SUNKEN,
            'cursor': 'no'
        },
        'drop_success': {
            'bg': '#e7ffe7', 
            'border': '2px solid #00cc00',
            'relief': tk.RAISED,
            'cursor': 'hand2'
        }
    }
    
    @classmethod
    def apply_state(cls, widget: tk.Widget, state: str):
        """Apply visual state to widget"""
        if state not in cls.DRAG_STATES:
            state = 'idle'
        
        style_config = cls.DRAG_STATES[state]
        
        try:
            if hasattr(widget, 'configure'):
                # Apply background if supported
                if 'bg' in style_config:
                    try:
                        widget.configure(bg=style_config['bg'])
                    except tk.TclError:
                        # Some ttk widgets don't support bg
                        pass
                
                # Apply relief if supported
                if 'relief' in style_config:
                    try:
                        widget.configure(relief=style_config['relief'])
                    except tk.TclError:
                        pass
                
                # Apply cursor
                if 'cursor' in style_config:
                    try:
                        widget.configure(cursor=style_config['cursor'])
                    except tk.TclError:
                        pass
                        
        except Exception as e:
            logger.warning(f"Could not apply drag state {state}: {e}")


class DragDropHandler:
    """
    Main drag-and-drop handler for folder operations
    """
    
    def __init__(self, target_widget: tk.Widget, 
                 on_folder_dropped: Callable[[str], None],
                 validation_callback: Optional[Callable[[str], bool]] = None,
                 drag_drop_validator=None):
        """
        Initialize drag-drop handler
        
        Args:
            target_widget: Widget to enable drag-drop on
            on_folder_dropped: Callback when valid folder is dropped
            validation_callback: Optional callback to validate dropped items
            drag_drop_validator: Optional specialized drag-drop validator
        """
        self.target_widget = target_widget
        self.on_folder_dropped = on_folder_dropped
        self.validation_callback = validation_callback or self._default_validation
        self.drag_drop_validator = drag_drop_validator
        
        self.is_drag_active = False
        self.current_drag_valid = False
        self.visual_feedback = DragVisualFeedback()
        
        self._setup_drop_target()
        self._apply_initial_state()
    
    def _setup_drop_target(self):
        """Configure widget to accept drag-drop events"""
        try:
            # Verify widget supports drag-drop before proceeding
            if not hasattr(self.target_widget, 'drop_target_register'):
                logger.warning("Widget does not support drag-drop operations")
                return
            
            # Register for file drops
            self.target_widget.drop_target_register(DND_FILES)
            
            # Bind drag-drop events
            self.target_widget.dnd_bind('<<DropEnter>>', self._on_drag_enter)
            self.target_widget.dnd_bind('<<DropPosition>>', self._on_drag_position)  
            self.target_widget.dnd_bind('<<DropLeave>>', self._on_drag_leave)
            self.target_widget.dnd_bind('<<Drop>>', self._on_drop)
            
            logger.info("Drag-drop events configured successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup drag-drop: {e}")
            # Don't raise - allow application to continue without drag-drop
            self.target_widget = None
    
    def _apply_initial_state(self):
        """Apply initial idle visual state"""
        self.visual_feedback.apply_state(self.target_widget, 'idle')
    
    def _on_drag_enter(self, event):
        """Handle drag enter event"""
        try:
            self.is_drag_active = True
            dropped_data = self._extract_dropped_data(event)
            
            if dropped_data:
                self.current_drag_valid = self._validate_drag_data(dropped_data)
                state = 'drag_over_valid' if self.current_drag_valid else 'drag_over_invalid'
            else:
                self.current_drag_valid = False
                state = 'drag_over_invalid'
            
            self.visual_feedback.apply_state(self.target_widget, state)
            logger.debug(f"Drag enter: valid={self.current_drag_valid}")
            
        except Exception as e:
            logger.error(f"Error in drag enter: {e}")
            self._reset_drag_state()
    
    def _on_drag_position(self, event):
        """Handle drag position event (while dragging over)"""
        try:
            if not self.is_drag_active:
                self._on_drag_enter(event)
                
        except Exception as e:
            logger.error(f"Error in drag position: {e}")
    
    def _on_drag_leave(self, event):
        """Handle drag leave event"""
        try:
            self._reset_drag_state()
            logger.debug("Drag leave")
            
        except Exception as e:
            logger.error(f"Error in drag leave: {e}")
            self._reset_drag_state()
    
    def _on_drop(self, event):
        """Handle drop event"""
        try:
            dropped_data = self._extract_dropped_data(event)
            
            if dropped_data and self._validate_drag_data(dropped_data):
                # Show success state briefly
                self.visual_feedback.apply_state(self.target_widget, 'drop_success')
                
                # Process the drop
                folder_path = dropped_data[0] if dropped_data else None
                if folder_path:
                    logger.info(f"Processing dropped folder: {folder_path}")
                    self.on_folder_dropped(folder_path)
                
                # Reset to idle after short delay
                self.target_widget.after(500, self._reset_drag_state)
            else:
                logger.warning("Invalid drop data received")
                self._reset_drag_state()
                
        except Exception as e:
            logger.error(f"Error processing drop: {e}")
            self._reset_drag_state()
    
    def _extract_dropped_data(self, event) -> Optional[List[str]]:
        """Extract file paths from drop event"""
        try:
            if not hasattr(event, 'data') or not event.data:
                return None
            
            # Parse dropped file paths
            dropped_data = event.data
            
            # Handle different data formats
            if isinstance(dropped_data, str):
                # Split multiple paths (typically space or newline separated)
                paths = [path.strip('{}').strip('"').strip("'") for path in dropped_data.split()]
                paths = [path for path in paths if path]  # Remove empty strings
            elif isinstance(dropped_data, (list, tuple)):
                paths = [str(path).strip('{}').strip('"').strip("'") for path in dropped_data]
            else:
                logger.warning(f"Unexpected drop data format: {type(dropped_data)}")
                return None
            
            # Filter out empty paths and normalize
            valid_paths = []
            for path in paths:
                if path and os.path.exists(path):
                    valid_paths.append(os.path.abspath(path))
            
            return valid_paths if valid_paths else None
            
        except Exception as e:
            logger.error(f"Error extracting drop data: {e}")
            return None
    
    def _validate_drag_data(self, paths: List[str]) -> bool:
        """Validate dropped paths using advanced validation"""
        try:
            if not paths:
                return False
            
            # Use drag-drop validator if available
            if self.drag_drop_validator:
                validation_results = self.drag_drop_validator.validate_multiple_drops(paths)
                
                # Find the first valid result
                for path, result in validation_results.items():
                    if result.is_valid:
                        return True
                
                # Log validation errors for debugging
                for path, result in validation_results.items():
                    if result.errors:
                        for error in result.errors:
                            logger.debug(f"Validation error for {path}: {error.message}")
                
                return False
            
            # Fallback to simple validation
            if len(paths) != 1:
                logger.debug("Multiple items dropped, only single folder accepted")
                return False
            
            path = paths[0]
            
            # Use custom validation if provided
            if self.validation_callback:
                return self.validation_callback(path)
            
            return self._default_validation(path)
            
        except Exception as e:
            logger.error(f"Error validating drag data: {e}")
            return False
    
    def _default_validation(self, path: str) -> bool:
        """Default validation - check if path is an accessible folder"""
        try:
            if not path or not os.path.exists(path):
                return False
            
            if not os.path.isdir(path):
                return False
            
            if not os.access(path, os.R_OK):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error in default validation: {e}")
            return False
    
    def _reset_drag_state(self):
        """Reset drag state to idle"""
        self.is_drag_active = False
        self.current_drag_valid = False
        self.visual_feedback.apply_state(self.target_widget, 'idle')
    
    def destroy(self):
        """Clean up drag-drop handling"""
        try:
            if hasattr(self.target_widget, 'drop_target_unregister'):
                self.target_widget.drop_target_unregister()
            
            self._reset_drag_state()
            logger.info("Drag-drop handler destroyed")
            
        except Exception as e:
            logger.error(f"Error destroying drag-drop handler: {e}")


class FolderDropValidator:
    """
    Enhanced folder validation for drag-drop operations
    Integrates with existing validation service
    """
    
    def __init__(self, validation_service=None):
        """
        Initialize with optional validation service
        
        Args:
            validation_service: Existing validation service for integration
        """
        self.validation_service = validation_service
    
    def validate_dropped_item(self, path: str) -> Dict[str, Any]:
        """
        Comprehensive validation of dropped item
        
        Args:
            path: Path to validate
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'path': path
        }
        
        try:
            # Basic existence check
            if not os.path.exists(path):
                result['errors'].append("Path does not exist")
                result['is_valid'] = False
                return result
            
            # Folder check
            if not os.path.isdir(path):
                result['errors'].append("Path is not a folder")
                result['is_valid'] = False
                return result
            
            # Permission checks
            if not os.access(path, os.R_OK):
                result['errors'].append("Folder is not readable")
                result['is_valid'] = False
            
            if not os.access(path, os.W_OK):
                result['warnings'].append("Folder is not writable - operations may fail")
            
            # Use validation service if available
            if self.validation_service:
                try:
                    service_result = self.validation_service.validate_directory_access(path)
                    if hasattr(service_result, 'errors') and service_result.errors:
                        result['errors'].extend([str(error) for error in service_result.errors])
                        result['is_valid'] = False
                    
                    if hasattr(service_result, 'warnings') and service_result.warnings:
                        result['warnings'].extend([str(warning) for warning in service_result.warnings])
                        
                except Exception as e:
                    logger.warning(f"Validation service error: {e}")
            
            # Check folder contents
            try:
                files = os.listdir(path)
                if not files:
                    result['warnings'].append("Folder is empty")
                    
            except OSError as e:
                result['errors'].append(f"Cannot read folder contents: {str(e)}")
                result['is_valid'] = False
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating dropped item: {e}")
            result['errors'].append(f"Validation error: {str(e)}")
            result['is_valid'] = False
            return result
    
    def check_folder_permissions(self, path: str) -> bool:
        """
        Check if folder has required permissions
        
        Args:
            path: Folder path to check
            
        Returns:
            True if folder has read access
        """
        try:
            return os.path.exists(path) and os.path.isdir(path) and os.access(path, os.R_OK)
        except Exception:
            return False
    
    def validate_folder_contents(self, path: str) -> Dict[str, Any]:
        """
        Validate folder contents for processable files
        
        Args:
            path: Folder path to check
            
        Returns:
            Dictionary with content validation results
        """
        result = {
            'has_files': False,
            'file_count': 0,
            'processable_files': 0,
            'file_types': set(),
            'warnings': []
        }
        
        try:
            if not self.check_folder_permissions(path):
                result['warnings'].append("Cannot access folder")
                return result
            
            files = os.listdir(path)
            all_files = [f for f in files if os.path.isfile(os.path.join(path, f))]
            
            result['has_files'] = len(all_files) > 0
            result['file_count'] = len(all_files)
            
            # Count processable files (non-hidden, non-system)
            processable = []
            for file in all_files:
                if not file.startswith('.') and not file.startswith('~'):
                    processable.append(file)
                    # Track file extensions
                    ext = os.path.splitext(file)[1].lower()
                    if ext:
                        result['file_types'].add(ext)
            
            result['processable_files'] = len(processable)
            result['file_types'] = list(result['file_types'])
            
            if result['file_count'] == 0:
                result['warnings'].append("Folder is empty")
            elif result['processable_files'] == 0:
                result['warnings'].append("No processable files found (hidden/system files only)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating folder contents: {e}")
            result['warnings'].append(f"Error reading folder: {str(e)}")
            return result