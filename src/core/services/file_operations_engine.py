"""
File Operations Engine

Integrates Vietnamese normalization with file operations workflow.
Provides comprehensive file processing capabilities including:
- Folder scanning and file discovery
- Vietnamese text normalization
- Rename preview generation
- Batch file operations
- Error handling and logging
"""

import os
from typing import List, Optional, Dict, Any, Generator, Callable
from pathlib import Path
import logging

from ..models.file_info import FileInfo, RenamePreview, FileProcessingRecord, FileType, OperationStatus
from ..models.operation import NormalizationRules, BatchOperation, OperationType
from .normalize_service import VietnameseNormalizer

# Configure logging
logger = logging.getLogger(__name__)


class FileOperationsEngine:
    """
    Core file operations engine with Vietnamese normalization integration
    """
    
    def __init__(self, normalizer: Optional[VietnameseNormalizer] = None):
        self.normalizer = normalizer or VietnameseNormalizer()
        self._operation_history: List[BatchOperation] = []
        self._current_operation_cancelled = False
    
    def scan_folder_contents(self, folder_path: str, recursive: bool = False, 
                           include_hidden: bool = False) -> List[FileInfo]:
        """
        Scan folder and return comprehensive file information
        
        Args:
            folder_path: Path to scan
            recursive: Include subdirectories
            include_hidden: Include hidden files
            
        Returns:
            List of FileInfo objects
            
        Raises:
            ValueError: If folder path is invalid
            PermissionError: If folder cannot be accessed
        """
        if not folder_path or not os.path.exists(folder_path):
            raise ValueError(f"Invalid folder path: {folder_path}")
            
        if not os.path.isdir(folder_path):
            raise ValueError(f"Path is not a directory: {folder_path}")
            
        if not os.access(folder_path, os.R_OK):
            raise PermissionError(f"Cannot read folder: {folder_path}")
        
        files_info = []
        
        try:
            if recursive:
                # Use os.walk for recursive scanning
                for root, dirs, files in os.walk(folder_path):
                    # Process directories
                    for dir_name in dirs:
                        dir_path = os.path.join(root, dir_name)
                        if self._should_include_file(dir_name, include_hidden):
                            try:
                                file_info = FileInfo.from_path(dir_path)
                                files_info.append(file_info)
                            except Exception as e:
                                logger.warning(f"Skipping directory {dir_path}: {e}")
                    
                    # Process files
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        if self._should_include_file(file_name, include_hidden):
                            try:
                                file_info = FileInfo.from_path(file_path)
                                files_info.append(file_info)
                            except Exception as e:
                                logger.warning(f"Skipping file {file_path}: {e}")
            else:
                # Single level scanning
                items = os.listdir(folder_path)
                items.sort()  # Consistent ordering
                
                for item in items:
                    item_path = os.path.join(folder_path, item)
                    if self._should_include_file(item, include_hidden):
                        try:
                            file_info = FileInfo.from_path(item_path)
                            files_info.append(file_info)
                        except Exception as e:
                            logger.warning(f"Skipping item {item_path}: {e}")
                            
        except Exception as e:
            logger.error(f"Error scanning folder {folder_path}: {e}")
            raise
        
        logger.info(f"Scanned {len(files_info)} items in {folder_path}")
        return files_info
    
    def _should_include_file(self, filename: str, include_hidden: bool) -> bool:
        """Check if file should be included based on criteria"""
        if not include_hidden and filename.startswith('.'):
            return False
        return True
    
    def preview_rename(self, files: List[FileInfo], 
                      rules: Optional[NormalizationRules] = None) -> List[RenamePreview]:
        """
        Generate rename previews for files using Vietnamese normalization
        
        Args:
            files: List of files to preview
            rules: Normalization rules to apply
            
        Returns:
            List of RenamePreview objects
        """
        if not files:
            return []
            
        active_rules = rules or NormalizationRules()
        previews = []
        
        for file_info in files:
            try:
                preview = self._generate_single_preview(file_info, active_rules)
                previews.append(preview)
            except Exception as e:
                logger.error(f"Failed to generate preview for {file_info.name}: {e}")
                # Create error preview
                error_preview = RenamePreview(
                    file_info=file_info,
                    normalized_name=file_info.name,
                    normalized_full_path=file_info.path
                )
                error_preview.add_warning(f"Preview generation failed: {e}")
                previews.append(error_preview)
        
        return previews
    
    def _generate_single_preview(self, file_info: FileInfo, 
                                rules: NormalizationRules) -> RenamePreview:
        """Generate preview for a single file"""
        # Apply normalization to filename
        if file_info.file_type == FileType.FILE and rules.preserve_extensions:
            normalized_name = self.normalizer.normalize_filename(file_info.name, rules)
        else:
            normalized_name = self.normalizer.normalize_text(file_info.name, rules)
        
        # Calculate new full path
        parent_dir = os.path.dirname(file_info.path)
        normalized_full_path = os.path.join(parent_dir, normalized_name)
        
        # Create preview
        preview = RenamePreview(
            file_info=file_info,
            normalized_name=normalized_name,
            normalized_full_path=normalized_full_path
        )
        
        # Check for changes and add descriptions
        if normalized_name != file_info.name:
            preview.add_change_description(f"Normalized: {file_info.name} → {normalized_name}")
            
            # Get detailed normalization steps
            norm_preview = self.normalizer.preview_normalization(
                file_info.name_without_extension, rules
            )
            for step in norm_preview.get('steps', []):
                if step['before'] != step['after']:
                    preview.add_change_description(f"{step['step']}: {step['before']} → {step['after']}")
        
        # Check for conflicts
        preview.check_target_conflicts()
        
        # Add validation warnings
        if len(normalized_name) > rules.max_filename_length:
            preview.add_warning(f"Filename exceeds max length ({rules.max_filename_length})")
        
        if len(normalized_name) < rules.min_filename_length:
            preview.add_warning(f"Filename below min length ({rules.min_filename_length})")
        
        # Check for readonly/permissions
        if file_info.is_readonly and not rules.skip_readonly_files:
            preview.add_warning("File is read-only")
            
        return preview
    
    def execute_batch_rename(self, previews: List[RenamePreview], 
                           operation_config: Optional[BatchOperation] = None,
                           progress_callback: Optional[Callable[[float, str], None]] = None) -> BatchOperation:
        """
        Execute batch rename operation based on previews
        
        Args:
            previews: List of rename previews
            operation_config: Optional batch operation configuration
            progress_callback: Optional callback for progress updates (percentage, current_file)
            
        Returns:
            Completed BatchOperation with results
        """
        if not previews:
            raise ValueError("No previews provided for batch operation")
        
        # Create or use provided operation config
        if operation_config is None:
            operation_config = BatchOperation(
                operation_type=OperationType.BATCH_RENAME,
                normalization_rules=NormalizationRules(),
                total_files=len(previews)
            )
        
        operation_config.start_operation()
        processing_records = []
        self._current_operation_cancelled = False
        
        try:
            for i, preview in enumerate(previews):
                # Check for cancellation
                if self._current_operation_cancelled:
                    operation_config.log_message("Operation cancelled by user")
                    break
                
                # Update progress callback if provided
                if progress_callback:
                    progress_percentage = (i / len(previews)) * 100
                    progress_callback(progress_percentage, preview.original_name)
                
                record = self._execute_single_rename(preview, operation_config)
                processing_records.append(record)
                
                # Update operation progress
                success = record.operation_status == OperationStatus.SUCCESS
                skipped = record.operation_status == OperationStatus.SKIPPED
                operation_config.increment_progress(success, skipped)
                
            # Final progress update
            if progress_callback and not self._current_operation_cancelled:
                progress_callback(100.0, "Operation completed")
                
        except Exception as e:
            operation_config.log_error(f"Batch operation failed: {e}")
            logger.error(f"Batch rename failed: {e}")
        
        finally:
            operation_config.complete_operation()
        
        # Add to history
        self._operation_history.append(operation_config)
        
        return operation_config
    
    def _execute_single_rename(self, preview: RenamePreview, 
                             operation: BatchOperation) -> FileProcessingRecord:
        """Execute single file rename operation"""
        record = FileProcessingRecord(
            file_info=preview.file_info,
            original_name=preview.original_name,
            processed_name=preview.normalized_name,
            operation_status=OperationStatus.PENDING,
            operation_id=operation.operation_id,
            source_path=preview.file_info.path,
            target_path=preview.normalized_full_path
        )
        
        record.start_processing()
        
        try:
            # Pre-flight checks
            if not preview.has_changes:
                record.operation_status = OperationStatus.SKIPPED
                record.add_processing_step("skip", {"reason": "No changes needed"})
                operation.log_message(f"Skipped {preview.original_name} (no changes)")
                return record
            
            # Check for conflicts
            if preview.will_overwrite and not operation.normalization_rules.confirm_overwrite:
                record.operation_status = OperationStatus.SKIPPED
                record.add_processing_step("skip", {"reason": "Would overwrite existing file"})
                operation.log_message(f"Skipped {preview.original_name} (would overwrite)")
                return record
            
            # Check readonly files
            if (preview.file_info.is_readonly and 
                operation.normalization_rules.skip_readonly_files):
                record.operation_status = OperationStatus.SKIPPED
                record.add_processing_step("skip", {"reason": "File is read-only"})
                operation.log_message(f"Skipped {preview.original_name} (read-only)")
                return record
            
            # Execute rename if not dry run
            if not operation.dry_run:
                # Create backup if requested
                if operation.normalization_rules.create_backup:
                    backup_path = f"{record.source_path}.backup"
                    try:
                        os.rename(record.source_path, backup_path)
                        record.backup_created = True
                        record.backup_path = backup_path
                        record.add_processing_step("backup", {"backup_path": backup_path})
                        
                        # Rename backup to target
                        os.rename(backup_path, record.target_path)
                        
                    except Exception as backup_error:
                        # Restore from backup if rename failed
                        if record.backup_created and os.path.exists(backup_path):
                            try:
                                os.rename(backup_path, record.source_path)
                                record.backup_created = False
                            except Exception:
                                logger.error(f"Failed to restore backup: {backup_path}")
                        raise backup_error
                else:
                    # Direct rename
                    os.rename(record.source_path, record.target_path)
                
                record.add_processing_step("rename", {
                    "from": record.source_path,
                    "to": record.target_path
                })
                
                operation.log_message(f"Renamed: {preview.original_name} → {preview.normalized_name}")
            else:
                record.add_processing_step("dry_run", {"would_rename_to": record.target_path})
                operation.log_message(f"[DRY RUN] Would rename: {preview.original_name} → {preview.normalized_name}")
            
            record.complete_processing(success=True)
            
        except Exception as e:
            error_msg = f"Failed to rename {preview.original_name}: {e}"
            record.complete_processing(success=False, error=error_msg)
            operation.log_error(error_msg)
            logger.error(error_msg)
        
        return record
    
    def get_operation_history(self) -> List[BatchOperation]:
        """Get history of batch operations"""
        return self._operation_history.copy()
    
    def cancel_current_operation(self):
        """Cancel the currently running batch operation"""
        self._current_operation_cancelled = True
        logger.info("Batch operation cancellation requested")
    
    def detect_and_resolve_conflicts(self, previews: List[RenamePreview]) -> List[RenamePreview]:
        """
        Detect duplicate names and resolve conflicts with automatic numbering
        
        Args:
            previews: List of rename previews to check for conflicts
            
        Returns:
            List of previews with conflicts resolved
        """
        # Track normalized names to detect duplicates
        name_counts = {}
        resolved_previews = []
        
        for preview in previews:
            normalized_name = preview.normalized_name
            parent_dir = os.path.dirname(preview.normalized_full_path)
            
            # Check if this normalized name already exists
            if normalized_name in name_counts:
                # Generate unique name with counter
                name_without_ext, ext = os.path.splitext(normalized_name)
                counter = name_counts[normalized_name]
                unique_name = f"{name_without_ext}_{counter}{ext}"
                
                # Update preview with unique name
                preview.normalized_name = unique_name
                preview.normalized_full_path = os.path.join(parent_dir, unique_name)
                preview.add_change_description(f"Resolved duplicate name: {normalized_name} → {unique_name}")
                
                name_counts[normalized_name] += 1
                name_counts[unique_name] = 1
                
            else:
                name_counts[normalized_name] = 1
                
            # Check if target already exists in file system
            if os.path.exists(preview.normalized_full_path) and preview.normalized_full_path != preview.file_info.path:
                # File exists and it's not the same file - generate unique name
                name_without_ext, ext = os.path.splitext(preview.normalized_name)
                counter = 1
                
                while True:
                    unique_name = f"{name_without_ext}_{counter}{ext}"
                    unique_path = os.path.join(parent_dir, unique_name)
                    
                    if not os.path.exists(unique_path):
                        preview.normalized_name = unique_name
                        preview.normalized_full_path = unique_path
                        preview.add_change_description(f"Resolved file system conflict: {unique_name}")
                        break
                        
                    counter += 1
                    
                    # Safety limit to prevent infinite loop
                    if counter > 9999:
                        preview.add_warning("Could not resolve file system conflict")
                        break
                        
            resolved_previews.append(preview)
            
        return resolved_previews
    
    def validate_operation(self, files: List[FileInfo], 
                         rules: NormalizationRules) -> Dict[str, Any]:
        """
        Validate a batch operation before execution
        
        Args:
            files: Files to process
            rules: Normalization rules
            
        Returns:
            Validation results
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'file_count': len(files),
            'estimated_changes': 0
        }
        
        # Validate rules
        rules_validation = rules.validate()
        if not rules_validation['valid']:
            validation['valid'] = False
            validation['errors'].extend(rules_validation['errors'])
        validation['warnings'].extend(rules_validation['warnings'])
        
        # Check file access and estimate changes
        for file_info in files:
            # Check file accessibility
            if not os.access(file_info.path, os.R_OK):
                validation['errors'].append(f"Cannot read file: {file_info.name}")
                validation['valid'] = False
                continue
            
            # Estimate if file will be changed
            if file_info.file_type == FileType.FILE:
                normalized = self.normalizer.normalize_filename(file_info.name, rules)
            else:
                normalized = self.normalizer.normalize_text(file_info.name, rules)
            
            if normalized != file_info.name:
                validation['estimated_changes'] += 1
        
        if validation['estimated_changes'] == 0:
            validation['warnings'].append("No files will be changed with current rules")
        
        return validation