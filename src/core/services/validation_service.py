"""
Comprehensive Pre-Operation Validation Service

Validates file names, paths, and operations before execution to prevent errors.
Provides detailed validation results with suggestions for fixing issues.
"""

import os
import re
import unicodedata
from pathlib import Path, PurePath
from typing import List, Dict, Set, Optional, Tuple
import logging

from ..models.error_models import (
    ValidationResult, ValidationError, ValidationErrorCode, ErrorSeverity
)

# Configure logging
logger = logging.getLogger(__name__)


class FileNameValidator:
    """
    Comprehensive file name validator with Windows compatibility
    """
    
    # Windows reserved names (case-insensitive)
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    # Invalid characters for Windows file names
    INVALID_CHARS = {'<', '>', ':', '"', '|', '?', '*', '\\', '/'}
    INVALID_CHARS_PATTERN = r'[<>:"|?*\\/]'
    
    # Control characters (ASCII 0-31)
    CONTROL_CHARS = set(chr(i) for i in range(32))
    
    # Windows path length limits
    MAX_PATH_LENGTH = 260
    MAX_FILENAME_LENGTH = 255
    MAX_COMPONENT_LENGTH = 255  # Individual directory/file name
    
    # Dangerous extensions that might be blocked
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.com', '.pif', '.scr', '.vbs', '.js',
        '.jar', '.msi', '.dll', '.sys', '.drv'
    }
    
    def __init__(self):
        self._validation_cache: Dict[str, ValidationResult] = {}
        self._cache_max_size = 1000
    
    def validate_filename(self, filename: str, check_extensions: bool = True) -> ValidationResult:
        """
        Comprehensive filename validation
        
        Args:
            filename: The filename to validate
            check_extensions: Whether to check for dangerous extensions
            
        Returns:
            ValidationResult with errors and warnings
        """
        # Check cache first
        cache_key = f"{filename}:{check_extensions}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        result = ValidationResult(is_valid=True)
        
        # Basic checks
        if not filename:
            result.add_error(
                ValidationErrorCode.TOO_SHORT,
                "Filename cannot be empty",
                "filename",
                filename,
                "Provide a valid filename"
            )
            return self._cache_result(cache_key, result)
        
        if not filename.strip():
            result.add_error(
                ValidationErrorCode.TOO_SHORT,
                "Filename cannot be only whitespace",
                "filename", 
                filename,
                "Provide a filename with actual characters"
            )
            return self._cache_result(cache_key, result)
        
        # Length validation
        self._validate_filename_length(filename, result)
        
        # Character validation
        self._validate_characters(filename, result)
        
        # Reserved name validation
        self._validate_reserved_names(filename, result)
        
        # Extension validation
        if check_extensions:
            self._validate_extension(filename, result)
        
        # Path traversal validation
        self._validate_path_traversal(filename, result)
        
        # Normalization warnings
        self._check_normalization_issues(filename, result)
        
        return self._cache_result(cache_key, result)
    
    def validate_path_length(self, full_path: str) -> ValidationResult:
        """
        Validate full path length against Windows limitations
        
        Args:
            full_path: The complete file path to validate
            
        Returns:
            ValidationResult with path length validation
        """
        result = ValidationResult(is_valid=True)
        
        # Normalize path
        normalized_path = os.path.abspath(full_path)
        path_length = len(normalized_path)
        
        if path_length > self.MAX_PATH_LENGTH:
            excess_chars = path_length - self.MAX_PATH_LENGTH
            result.add_error(
                ValidationErrorCode.TOO_LONG,
                f"Path is too long by {excess_chars} characters ({path_length}/{self.MAX_PATH_LENGTH})",
                "path",
                full_path,
                "Use shorter folder names or move to a location with a shorter path"
            )
        elif path_length > self.MAX_PATH_LENGTH * 0.9:  # Warning at 90%
            result.add_warning(
                ValidationErrorCode.TOO_LONG,
                f"Path is approaching maximum length ({path_length}/{self.MAX_PATH_LENGTH})",
                "path",
                full_path,
                "Consider using shorter folder names"
            )
        
        # Validate individual path components
        path_obj = PurePath(normalized_path)
        for component in path_obj.parts:
            if len(component) > self.MAX_COMPONENT_LENGTH:
                result.add_error(
                    ValidationErrorCode.TOO_LONG,
                    f"Path component '{component}' is too long ({len(component)}/{self.MAX_COMPONENT_LENGTH})",
                    "path_component",
                    component,
                    "Use a shorter folder or file name"
                )
        
        return result
    
    def detect_duplicate_names(self, target_names: List[str], 
                              existing_names: Set[str] = None) -> Dict[str, List[str]]:
        """
        Detect duplicate names in target list and against existing files
        
        Args:
            target_names: List of target file names
            existing_names: Set of existing file names to check against
            
        Returns:
            Dictionary mapping lowercase names to lists of original names that would conflict
        """
        conflicts = {}
        seen_names = {}
        existing_names = existing_names or set()
        
        # Check for duplicates within target names (case-insensitive on Windows)
        for name in target_names:
            lower_name = name.lower()
            if lower_name in seen_names:
                if lower_name not in conflicts:
                    conflicts[lower_name] = [seen_names[lower_name]]
                conflicts[lower_name].append(name)
            else:
                seen_names[lower_name] = name
        
        # Check against existing names
        for name in target_names:
            lower_name = name.lower()
            if any(existing.lower() == lower_name for existing in existing_names):
                if lower_name not in conflicts:
                    conflicts[lower_name] = []
                conflicts[lower_name].append(name)
        
        return conflicts
    
    def suggest_filename_fix(self, filename: str) -> str:
        """
        Suggest a fixed version of an invalid filename
        
        Args:
            filename: The invalid filename
            
        Returns:
            Suggested fixed filename
        """
        if not filename:
            return "unnamed_file"
        
        fixed = filename.strip()
        
        # Remove invalid characters
        fixed = re.sub(self.INVALID_CHARS_PATTERN, '_', fixed)
        
        # Remove control characters
        fixed = ''.join(c for c in fixed if c not in self.CONTROL_CHARS)
        
        # Handle reserved names
        name_without_ext = os.path.splitext(fixed)[0].upper()
        if name_without_ext in self.RESERVED_NAMES:
            fixed = f"{fixed}_file"
        
        # Handle length issues
        if len(fixed) > self.MAX_FILENAME_LENGTH:
            name, ext = os.path.splitext(fixed)
            max_name_length = self.MAX_FILENAME_LENGTH - len(ext)
            fixed = name[:max_name_length] + ext
        
        # Handle empty result
        if not fixed or fixed.isspace():
            fixed = "unnamed_file"
        
        # Remove trailing dots and spaces (Windows doesn't allow these)
        fixed = fixed.rstrip('. ')
        
        if not fixed:
            fixed = "unnamed_file"
        
        return fixed
    
    def _validate_filename_length(self, filename: str, result: ValidationResult):
        """Validate filename length"""
        if len(filename) > self.MAX_FILENAME_LENGTH:
            excess_chars = len(filename) - self.MAX_FILENAME_LENGTH
            result.add_error(
                ValidationErrorCode.TOO_LONG,
                f"Filename is too long by {excess_chars} characters ({len(filename)}/{self.MAX_FILENAME_LENGTH})",
                "filename",
                filename,
                f"Shorten filename to {self.MAX_FILENAME_LENGTH} characters or less"
            )
        elif len(filename) > self.MAX_FILENAME_LENGTH * 0.9:  # Warning at 90%
            result.add_warning(
                ValidationErrorCode.TOO_LONG,
                f"Filename is approaching maximum length ({len(filename)}/{self.MAX_FILENAME_LENGTH})",
                "filename",
                filename,
                "Consider using a shorter filename"
            )
    
    def _validate_characters(self, filename: str, result: ValidationResult):
        """Validate characters in filename"""
        invalid_chars_found = set()
        control_chars_found = set()
        
        for char in filename:
            if char in self.INVALID_CHARS:
                invalid_chars_found.add(char)
            elif char in self.CONTROL_CHARS:
                control_chars_found.add(repr(char))
        
        if invalid_chars_found:
            chars_str = ', '.join(f"'{c}'" for c in sorted(invalid_chars_found))
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                f"Filename contains invalid characters: {chars_str}",
                "filename",
                filename,
                f"Replace invalid characters with underscores or remove them"
            )
        
        if control_chars_found:
            chars_str = ', '.join(sorted(control_chars_found))
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                f"Filename contains control characters: {chars_str}",
                "filename", 
                filename,
                "Remove control characters from filename"
            )
        
        # Check for trailing dots and spaces (Windows issue)
        if filename.endswith('.') or filename.endswith(' '):
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Filename cannot end with dot or space",
                "filename",
                filename,
                "Remove trailing dots and spaces"
            )
    
    def _validate_reserved_names(self, filename: str, result: ValidationResult):
        """Validate against Windows reserved names"""
        # Check base name without extension
        name_without_ext = os.path.splitext(filename)[0].upper()
        
        if name_without_ext in self.RESERVED_NAMES:
            result.add_error(
                ValidationErrorCode.RESERVED_NAME,
                f"'{filename}' uses a reserved Windows name",
                "filename",
                filename,
                f"Add a prefix or suffix to avoid the reserved name '{name_without_ext}'"
            )
    
    def _validate_extension(self, filename: str, result: ValidationResult):
        """Validate file extension"""
        ext = os.path.splitext(filename)[1].lower()
        
        if ext in self.DANGEROUS_EXTENSIONS:
            result.add_warning(
                ValidationErrorCode.UNSAFE_EXTENSION,
                f"Extension '{ext}' may be blocked by security software",
                "extension",
                ext,
                "Consider using a different extension if the file is not executable"
            )
    
    def _validate_path_traversal(self, filename: str, result: ValidationResult):
        """Check for path traversal attempts"""
        if '..' in filename or filename.startswith('/') or filename.startswith('\\'):
            result.add_error(
                ValidationErrorCode.PATH_TRAVERSAL,
                "Filename contains path traversal characters",
                "filename",
                filename,
                "Remove '..' and path separators from filename"
            )
    
    def _check_normalization_issues(self, filename: str, result: ValidationResult):
        """Check for Unicode normalization issues"""
        try:
            # Check if filename is properly normalized
            nfc_form = unicodedata.normalize('NFC', filename)
            if filename != nfc_form:
                result.add_warning(
                    ValidationErrorCode.INVALID_CHARACTER,
                    "Filename contains non-normalized Unicode characters",
                    "filename",
                    filename,
                    "Normalize Unicode characters in filename"
                )
            
            # Check for mixed scripts that might cause confusion
            scripts = set()
            for char in filename:
                if char.isalpha():
                    script = unicodedata.name(char, '').split()[0]
                    scripts.add(script)
            
            if len(scripts) > 2:  # Allow mixing of Latin with one other script
                result.add_warning(
                    ValidationErrorCode.INVALID_CHARACTER,
                    "Filename mixes multiple writing scripts",
                    "filename",
                    filename,
                    "Use consistent character script in filename"
                )
        
        except ValueError:
            # Invalid Unicode character
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Filename contains invalid Unicode characters",
                "filename",
                filename,
                "Remove or replace invalid Unicode characters"
            )
    
    def _cache_result(self, cache_key: str, result: ValidationResult) -> ValidationResult:
        """Cache validation result with size limit"""
        if len(self._validation_cache) >= self._cache_max_size:
            # Remove oldest entries (simple FIFO)
            keys_to_remove = list(self._validation_cache.keys())[:100]
            for key in keys_to_remove:
                del self._validation_cache[key]
        
        self._validation_cache[cache_key] = result
        return result


class PreOperationValidator:
    """
    Complete pre-operation validation for batch rename operations
    """
    
    def __init__(self):
        self.filename_validator = FileNameValidator()
    
    def validate_batch_operation(self, source_dir: str, 
                                target_filenames: Dict[str, str]) -> Dict[str, ValidationResult]:
        """
        Validate entire batch operation before execution
        
        Args:
            source_dir: Source directory path
            target_filenames: Dictionary mapping original filename to target filename
            
        Returns:
            Dictionary mapping original filename to validation results
        """
        results = {}
        
        # Get existing files in directory
        existing_files = set()
        if os.path.exists(source_dir):
            try:
                existing_files = set(os.listdir(source_dir))
            except OSError as e:
                logger.warning(f"Could not list directory {source_dir}: {e}")
        
        # Remove source files from existing set (they will be renamed)
        for original_name in target_filenames.keys():
            existing_files.discard(original_name)
        
        # Validate each target filename
        for original_name, target_name in target_filenames.items():
            result = ValidationResult(is_valid=True)
            
            # Validate filename format
            filename_result = self.filename_validator.validate_filename(target_name)
            result.errors.extend(filename_result.errors)
            result.warnings.extend(filename_result.warnings)
            result.is_valid = result.is_valid and filename_result.is_valid
            
            # Validate full path length
            full_target_path = os.path.join(source_dir, target_name)
            path_result = self.filename_validator.validate_path_length(full_target_path)
            result.errors.extend(path_result.errors)
            result.warnings.extend(path_result.warnings)
            result.is_valid = result.is_valid and path_result.is_valid
            
            results[original_name] = result
        
        # Check for duplicate names
        target_names = list(target_filenames.values())
        conflicts = self.filename_validator.detect_duplicate_names(target_names, existing_files)
        
        for conflicted_name, conflict_list in conflicts.items():
            for conflict in conflict_list:
                # Find original name that maps to this conflict
                for orig_name, target_name in target_filenames.items():
                    if target_name == conflict:
                        if orig_name in results:
                            results[orig_name].add_error(
                                ValidationErrorCode.DUPLICATE_NAME,
                                f"Target name '{target_name}' conflicts with existing files",
                                "filename",
                                target_name,
                                "Choose a different name or rename the conflicting file"
                            )
        
        return results
    
    def validate_directory_access(self, directory: str) -> ValidationResult:
        """
        Validate that directory is accessible for operations
        
        Args:
            directory: Directory path to validate
            
        Returns:
            ValidationResult for directory access
        """
        result = ValidationResult(is_valid=True)
        
        if not directory:
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Directory path cannot be empty",
                "directory",
                directory,
                "Select a valid directory"
            )
            return result
        
        # Check if directory exists
        if not os.path.exists(directory):
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Directory does not exist",
                "directory",
                directory,
                "Select an existing directory"
            )
            return result
        
        # Check if it's actually a directory
        if not os.path.isdir(directory):
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Path is not a directory",
                "directory", 
                directory,
                "Select a directory, not a file"
            )
            return result
        
        # Check read access
        if not os.access(directory, os.R_OK):
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Directory is not readable",
                "directory",
                directory,
                "Check directory permissions or run as administrator"
            )
        
        # Check write access
        if not os.access(directory, os.W_OK):
            result.add_error(
                ValidationErrorCode.INVALID_CHARACTER,
                "Directory is not writable",
                "directory",
                directory,
                "Check directory permissions or run as administrator"
            )
        
        return result
    
    def get_validation_summary(self, validation_results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """
        Get summary of validation results
        
        Args:
            validation_results: Dictionary of validation results
            
        Returns:
            Summary dictionary with counts and statistics
        """
        total_files = len(validation_results)
        valid_files = sum(1 for r in validation_results.values() if r.is_valid)
        files_with_errors = sum(1 for r in validation_results.values() if r.errors)
        files_with_warnings = sum(1 for r in validation_results.values() if r.warnings)
        
        total_errors = sum(len(r.errors) for r in validation_results.values())
        total_warnings = sum(len(r.warnings) for r in validation_results.values())
        
        # Count error types
        error_type_counts = {}
        for result in validation_results.values():
            for error in result.errors:
                error_type_counts[error.code.value] = error_type_counts.get(error.code.value, 0) + 1
        
        blocking_files = sum(1 for r in validation_results.values() if r.has_blocking_errors())
        
        return {
            'total_files': total_files,
            'valid_files': valid_files,
            'files_with_errors': files_with_errors,
            'files_with_warnings': files_with_warnings,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'error_type_counts': error_type_counts,
            'blocking_files': blocking_files,
            'can_proceed': blocking_files == 0,
            'validation_passed': files_with_errors == 0
        }


# Global validator instance
_global_validator = PreOperationValidator()


def get_validator() -> PreOperationValidator:
    """Get the global pre-operation validator"""
    return _global_validator