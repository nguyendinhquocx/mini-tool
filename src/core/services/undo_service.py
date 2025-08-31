"""
Enhanced Undo Service

Provides comprehensive undo functionality with atomic operations, external modification
detection, name conflict resolution, and integration with the progress system.
"""

import os
import json
import shutil
import tempfile
from typing import Optional, Dict, Any, List, Tuple, Callable
from datetime import datetime, timedelta
import logging
import hashlib

from ..models.undo_models import (
    UndoEligibility, UndoEligibilityReason, UndoExecutionPlan, UndoOperationMetadata,
    UndoOperationResult, UndoExecutionStatus, FileValidationResult, NameConflict
)
from ..models.operation import OperationResult, CancellationToken, OperationCancelledException
from .database_service import DatabaseService
from .operation_history_service import OperationHistoryService

# Configure logging
logger = logging.getLogger(__name__)


class FileModificationValidator:
    """Validates files for external modifications with validation caching"""
    
    def __init__(self):
        self._validation_cache = {}  # Cache recent validations to improve performance
        self._cache_max_age = 300  # 5 minutes cache
    
    @staticmethod
    def calculate_file_checksum(file_path: str) -> Optional[str]:
        """Calculate SHA256 checksum of file for integrity validation"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (OSError, IOError) as e:
            logger.warning(f"Could not calculate checksum for {file_path}: {e}")
            return None
    
    def validate_operation_files(self, operation_id: str, db_service: DatabaseService) -> List[FileValidationResult]:
        """Validate all files in an operation for external modifications"""
        results = []
        
        # Get file operations for this operation
        file_ops = db_service.fetch_all(
            '''SELECT file_path, original_name, new_name, original_modified_time 
               FROM file_operations 
               WHERE operation_id = ? AND operation_status = 'success' ''',
            (operation_id,)
        )
        
        for file_op in file_ops:
            current_path = os.path.join(
                os.path.dirname(file_op['file_path']), 
                file_op['new_name']
            )
            
            original_modified_time = datetime.fromisoformat(file_op['original_modified_time'])
            
            result = self.validate_file_integrity(
                current_path, 
                file_op['original_name'], 
                file_op['new_name'],
                original_modified_time
            )
            results.append(result)
        
        return results
    
    def validate_file_integrity(self, current_path: str, original_name: str, 
                              current_name: str, expected_modified_time: datetime) -> FileValidationResult:
        """Validate a single file for external modifications"""
        if not os.path.exists(current_path):
            return FileValidationResult(
                file_path=current_path,
                original_name=original_name,
                current_name=current_name,
                original_modified_time=expected_modified_time,
                current_modified_time=None,
                is_valid=False,
                validation_error="File no longer exists",
                can_be_restored=False
            )
        
        try:
            current_stat = os.stat(current_path)
            current_modified_time = datetime.fromtimestamp(current_stat.st_mtime)
            
            # Check for external modifications (allow 2 second tolerance)
            time_diff = abs((current_modified_time - expected_modified_time).total_seconds())
            was_modified = time_diff > 2.0
            
            # Check for name conflicts
            directory = os.path.dirname(current_path)
            target_path = os.path.join(directory, original_name)
            conflict_exists = os.path.exists(target_path) and target_path != current_path
            
            return FileValidationResult(
                file_path=current_path,
                original_name=original_name,
                current_name=current_name,
                original_modified_time=expected_modified_time,
                current_modified_time=current_modified_time,
                is_valid=not was_modified and not conflict_exists,
                validation_error=self._get_validation_error_message(was_modified, conflict_exists),
                can_be_restored=not conflict_exists,
                conflict_with_existing=conflict_exists,
                existing_file_path=target_path if conflict_exists else None
            )
            
        except OSError as e:
            return FileValidationResult(
                file_path=current_path,
                original_name=original_name,
                current_name=current_name,
                original_modified_time=expected_modified_time,
                current_modified_time=None,
                is_valid=False,
                validation_error=f"File system error: {e}",
                can_be_restored=False
            )
    
    def _get_validation_error_message(self, was_modified: bool, conflict_exists: bool) -> Optional[str]:
        """Generate appropriate validation error message"""
        if was_modified and conflict_exists:
            return "File modified externally and name conflict exists"
        elif was_modified:
            return "File modified externally"
        elif conflict_exists:
            return "Name conflict with existing file"
        return None
    
    def detect_external_changes(self, operation_id: str, db_service: DatabaseService) -> List[str]:
        """Detect files that have been modified externally since operation"""
        validations = self.validate_operation_files(operation_id, db_service)
        return [v.file_path for v in validations if v.was_modified_externally]


class UndoConflictResolver:
    """Handles name conflicts during undo operations"""
    
    def detect_name_conflicts(self, undo_plan: UndoExecutionPlan) -> List[NameConflict]:
        """Detect name conflicts in the undo plan"""
        conflicts = []
        
        for current_path, original_name, target_path in undo_plan.file_mappings:
            if os.path.exists(target_path) and target_path != current_path:
                conflict = NameConflict(
                    original_file=original_name,
                    conflicting_file=os.path.basename(target_path),
                    original_path=current_path,
                    conflicting_path=target_path
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def resolve_conflicts_with_temp_names(self, conflicts: List[NameConflict]) -> Dict[str, str]:
        """Resolve conflicts by generating temporary names"""
        temp_mappings = {}
        
        for conflict in conflicts:
            temp_name = conflict.suggest_temp_name()
            temp_mappings[conflict.conflicting_file] = temp_name
            conflict.resolution_strategy = "temp_rename"
            
        return temp_mappings
    
    def execute_atomic_rename_sequence(self, file_mappings: List[Tuple[str, str, str]], 
                                     temp_mappings: Dict[str, str],
                                     progress_callback: Optional[Callable[[float, str], None]] = None,
                                     cancellation_token: Optional[CancellationToken] = None) -> UndoOperationResult:
        """Execute atomic rename sequence with conflict resolution"""
        total_files = len(file_mappings)
        completed_renames = []
        
        try:
            # Phase 1: Move conflicting files to temporary names
            for i, (current_path, original_name, target_path) in enumerate(file_mappings):
                if cancellation_token:
                    cancellation_token.check_cancelled()
                
                if progress_callback:
                    progress_callback(
                        (i / total_files) * 50,  # First 50% for conflict resolution
                        f"Resolving conflicts for {original_name}"
                    )
                
                conflicting_file = os.path.basename(target_path)
                if conflicting_file in temp_mappings:
                    temp_name = temp_mappings[conflicting_file]
                    temp_path = os.path.join(os.path.dirname(target_path), temp_name)
                    
                    if os.path.exists(target_path):
                        os.rename(target_path, temp_path)
                        completed_renames.append((target_path, temp_path))
            
            # Phase 2: Rename files to their original names
            for i, (current_path, original_name, target_path) in enumerate(file_mappings):
                if cancellation_token:
                    cancellation_token.check_cancelled()
                
                if progress_callback:
                    progress_callback(
                        50 + (i / total_files) * 50,  # Second 50% for actual renames
                        f"Restoring {original_name}"
                    )
                
                if os.path.exists(current_path):
                    os.rename(current_path, target_path)
                    completed_renames.append((current_path, target_path))
            
            # Success - create result
            result = UndoOperationResult(
                operation_id=f"undo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                original_operation_id="temp",
                execution_status=UndoExecutionStatus.COMPLETED,
                total_files=total_files,
                successful_restorations=total_files
            )
            
            for current_path, original_name, target_path in file_mappings:
                result.add_successful_restoration(
                    os.path.basename(current_path), 
                    original_name
                )
            
            return result
            
        except Exception as e:
            # Rollback completed renames
            logger.error(f"Atomic rename sequence failed: {e}, rolling back")
            for original_path, renamed_path in reversed(completed_renames):
                try:
                    if os.path.exists(renamed_path):
                        os.rename(renamed_path, original_path)
                except Exception as rollback_error:
                    logger.error(f"Rollback failed for {renamed_path}: {rollback_error}")
            
            # Create failure result
            result = UndoOperationResult(
                operation_id=f"undo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                original_operation_id="temp",
                execution_status=UndoExecutionStatus.FAILED,
                total_files=total_files,
                failed_restorations=total_files,
                error_message=str(e)
            )
            
            return result


class UndoService:
    """
    Enhanced service for managing undo operations with comprehensive validation,
    atomic execution, and external modification detection.
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None,
                 operation_history_service: Optional[OperationHistoryService] = None):
        self.db = database_service or DatabaseService()
        self.history_service = operation_history_service or OperationHistoryService(self.db)
        self.file_validator = FileModificationValidator()
        self.conflict_resolver = UndoConflictResolver()
        
        # Default expiry time for undo operations (7 days)
        self.default_undo_expiry_days = 7
    
    def can_undo_operation(self, operation_id: str) -> UndoEligibility:
        """
        Comprehensive check if an operation can be undone with detailed eligibility information
        """
        # Get operation details
        operation = self.history_service.get_operation_details(operation_id)
        
        if not operation:
            return UndoEligibility(
                can_undo=False,
                primary_reason=UndoEligibilityReason.OPERATION_NOT_FOUND.value,
                all_reasons=["Operation not found in history"]
            )
        
        eligibility = UndoEligibility(
            can_undo=True,
            primary_reason="Operation can be undone",
            total_files=operation.get('total_files', 0)
        )
        
        # Check basic eligibility
        if operation.get('dry_run', False):
            eligibility.can_undo = False
            eligibility.primary_reason = UndoEligibilityReason.DRY_RUN_OPERATION.value
            eligibility.all_reasons.append("Cannot undo dry run operations")
            return eligibility
        
        if operation.get('successful_files', 0) == 0:
            eligibility.can_undo = False
            eligibility.primary_reason = UndoEligibilityReason.NO_SUCCESSFUL_FILES.value
            eligibility.all_reasons.append("No successful operations to undo")
            return eligibility
        
        # Check if operation is too old
        if operation.get('completed_at'):
            completed_time = datetime.fromisoformat(operation['completed_at'])
            if datetime.now() - completed_time > timedelta(days=self.default_undo_expiry_days):
                eligibility.can_undo = False
                eligibility.primary_reason = UndoEligibilityReason.OPERATION_TOO_OLD.value
                eligibility.all_reasons.append(f"Operation older than {self.default_undo_expiry_days} days")
                return eligibility
        
        # Validate files for external modifications and conflicts
        validations = self.file_validator.validate_operation_files(operation_id, self.db)
        eligibility.file_validations = validations
        
        for validation in validations:
            if validation.is_valid:
                eligibility.valid_files += 1
            else:
                eligibility.invalid_files += 1
                
                if not os.path.exists(validation.file_path):
                    eligibility.add_invalid_file(validation.file_path, "missing")
                elif validation.was_modified_externally:
                    eligibility.add_invalid_file(validation.file_path, "modified")
                elif validation.conflict_with_existing:
                    eligibility.add_invalid_file(validation.file_path, "conflict")
                elif "readonly" in validation.validation_error.lower() if validation.validation_error else False:
                    eligibility.add_invalid_file(validation.file_path, "readonly")
        
        # Determine final eligibility
        if eligibility.invalid_files > 0:
            eligibility.can_undo = False
            
            if eligibility.missing_files:
                eligibility.primary_reason = UndoEligibilityReason.FILES_MISSING.value
            elif eligibility.modified_files:
                eligibility.primary_reason = UndoEligibilityReason.FILES_MODIFIED_EXTERNALLY.value
            elif eligibility.conflicting_files:
                eligibility.primary_reason = UndoEligibilityReason.NAME_CONFLICTS_EXIST.value
            elif eligibility.readonly_files:
                eligibility.primary_reason = UndoEligibilityReason.FILES_READONLY.value
        
        return eligibility
    
    def create_undo_plan(self, operation_id: str) -> UndoExecutionPlan:
        """
        Create detailed execution plan for undo operation
        """
        operation = self.history_service.get_operation_details(operation_id)
        if not operation:
            raise ValueError(f"Operation {operation_id} not found")
        
        undo_operation_id = f"undo_{operation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        plan = UndoExecutionPlan(
            operation_id=operation_id,
            undo_operation_id=undo_operation_id,
            total_files=0
        )
        
        # Add file mappings for successful operations
        successful_files = [
            record for record in operation.get('file_records', [])
            if record.get('operation_status') == 'success'
        ]
        
        for record in successful_files:
            current_path = os.path.join(
                operation['source_directory'],
                record['new_name']
            )
            plan.add_file_mapping(current_path, record['original_name'])
        
        plan.total_files = len(plan.file_mappings)
        
        # Detect name conflicts
        conflicts = self.conflict_resolver.detect_name_conflicts(plan)
        for conflict in conflicts:
            plan.add_name_conflict(conflict)
        
        # Estimate execution time
        plan.estimate_execution_time()
        
        return plan
    
    def execute_undo_operation(self,
                              operation_id: str,
                              progress_callback: Optional[Callable[[float, str], None]] = None,
                              cancellation_token: Optional[CancellationToken] = None) -> UndoOperationResult:
        """
        Execute undo operation with atomic behavior and progress tracking
        """
        # Create undo result
        undo_operation_id = f"undo_{operation_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        result = UndoOperationResult(
            operation_id=undo_operation_id,
            original_operation_id=operation_id,
            execution_status=UndoExecutionStatus.NOT_STARTED
        )
        
        try:
            # Phase 1: Validation
            result.execution_status = UndoExecutionStatus.VALIDATING
            if progress_callback:
                progress_callback(10.0, "Validating undo eligibility")
            
            eligibility = self.can_undo_operation(operation_id)
            if not eligibility.can_undo:
                result.execution_status = UndoExecutionStatus.FAILED
                result.error_message = eligibility.get_summary_message()
                return result
            
            # Phase 2: Create execution plan
            result.execution_status = UndoExecutionStatus.PREPARING
            if progress_callback:
                progress_callback(20.0, "Creating undo execution plan")
            
            plan = self.create_undo_plan(operation_id)
            result.total_files = plan.total_files
            
            # Phase 3: Execute atomic undo
            result.start_execution()
            
            if plan.name_conflicts:
                # Resolve conflicts with temporary names
                temp_mappings = self.conflict_resolver.resolve_conflicts_with_temp_names(plan.name_conflicts)
                atomic_result = self.conflict_resolver.execute_atomic_rename_sequence(
                    plan.file_mappings,
                    temp_mappings,
                    lambda p, msg: progress_callback(20 + p * 0.7, msg) if progress_callback else None,
                    cancellation_token
                )
            else:
                # Simple rename sequence
                atomic_result = self._execute_simple_rename_sequence(
                    plan.file_mappings,
                    lambda p, msg: progress_callback(20 + p * 0.7, msg) if progress_callback else None,
                    cancellation_token
                )
            
            # Update result with atomic execution results
            result.successful_restorations = atomic_result.successful_restorations
            result.failed_restorations = atomic_result.failed_restorations
            result.restored_files = atomic_result.restored_files
            result.failed_files = atomic_result.failed_files
            
            # Phase 4: Save undo operation to history
            if progress_callback:
                progress_callback(95.0, "Saving undo operation")
            
            self._save_undo_operation_to_history(result, plan)
            
            # Mark original operation as undone
            self._mark_operation_as_undone(operation_id, undo_operation_id)
            
            result.complete_execution(atomic_result.execution_status == UndoExecutionStatus.COMPLETED)
            
            if progress_callback:
                progress_callback(100.0, result.completion_message)
            
            return result
            
        except OperationCancelledException as e:
            result.cancel_execution(e.reason)
            return result
        except Exception as e:
            logger.error(f"Undo operation failed: {e}", exc_info=True)
            result.execution_status = UndoExecutionStatus.FAILED
            result.error_message = f"Undo operation failed: {str(e)}"
            result.fatal_error = True
            result.complete_execution(False)
            return result
    
    def _execute_simple_rename_sequence(self,
                                      file_mappings: List[Tuple[str, str, str]],
                                      progress_callback: Optional[Callable[[float, str], None]] = None,
                                      cancellation_token: Optional[CancellationToken] = None) -> UndoOperationResult:
        """Execute simple rename sequence without conflicts"""
        total_files = len(file_mappings)
        result = UndoOperationResult(
            operation_id=f"undo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            original_operation_id="temp",
            execution_status=UndoExecutionStatus.EXECUTING,
            total_files=total_files
        )
        
        completed_renames = []
        
        try:
            for i, (current_path, original_name, target_path) in enumerate(file_mappings):
                if cancellation_token:
                    cancellation_token.check_cancelled()
                
                if progress_callback:
                    progress_callback(
                        (i / total_files) * 100,
                        f"Restoring {original_name}"
                    )
                
                try:
                    if os.path.exists(current_path):
                        os.rename(current_path, target_path)
                        result.add_successful_restoration(os.path.basename(current_path), original_name)
                        completed_renames.append((current_path, target_path))
                    else:
                        result.add_failed_restoration(
                            os.path.basename(current_path),
                            "File no longer exists"
                        )
                        
                except Exception as e:
                    result.add_failed_restoration(
                        os.path.basename(current_path),
                        str(e)
                    )
                    logger.error(f"Failed to rename {current_path} to {target_path}: {e}")
            
            result.execution_status = UndoExecutionStatus.COMPLETED
            return result
            
        except OperationCancelledException:
            # Rollback completed renames
            for current_path, target_path in reversed(completed_renames):
                try:
                    if os.path.exists(target_path):
                        os.rename(target_path, current_path)
                except Exception as rollback_error:
                    logger.error(f"Rollback failed for {target_path}: {rollback_error}")
            
            result.execution_status = UndoExecutionStatus.CANCELLED
            raise
        except Exception as e:
            # Rollback completed renames
            for current_path, target_path in reversed(completed_renames):
                try:
                    if os.path.exists(target_path):
                        os.rename(target_path, current_path)
                except Exception as rollback_error:
                    logger.error(f"Rollback failed for {target_path}: {rollback_error}")
            
            result.execution_status = UndoExecutionStatus.FAILED
            result.error_message = str(e)
            return result
    
    def _save_undo_operation_to_history(self, result: UndoOperationResult, plan: UndoExecutionPlan):
        """Save undo operation to database history"""
        try:
            self.db.execute_update('''
                INSERT INTO undo_operations (
                    undo_operation_id, original_operation_id, folder_path,
                    total_files, successful_restorations, failed_restorations,
                    skipped_files, execution_status, created_at, started_at,
                    completed_at, duration_seconds, was_cancelled,
                    cancellation_reason, error_message, file_mappings,
                    restored_files, failed_files
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result.operation_id,
                result.original_operation_id,
                plan.file_mappings[0][0].split(os.sep)[:-1] if plan.file_mappings else "",  # folder path
                result.total_files,
                result.successful_restorations,
                result.failed_restorations,
                result.skipped_files,
                result.execution_status.value,
                datetime.now().isoformat(),
                result.start_time.isoformat() if result.start_time else None,
                result.end_time.isoformat() if result.end_time else None,
                result.total_duration,
                result.was_cancelled,
                result.cancellation_reason,
                result.error_message,
                json.dumps([{"current": m[0], "original": m[1], "target": m[2]} for m in plan.file_mappings]),
                json.dumps(result.restored_files),
                json.dumps(result.failed_files)
            ))
            
        except Exception as e:
            logger.error(f"Failed to save undo operation to history: {e}")
    
    def _mark_operation_as_undone(self, operation_id: str, undo_operation_id: str):
        """Mark original operation as undone in database"""
        try:
            self.db.execute_update('''
                UPDATE operation_history 
                SET can_be_undone = 0, undo_operation_id = ? 
                WHERE operation_id = ?
            ''', (undo_operation_id, operation_id))
            
        except Exception as e:
            logger.error(f"Failed to mark operation as undone: {e}")
    
    def get_last_undoable_operation(self, folder_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the most recent operation that can be undone"""
        query = '''
            SELECT * FROM operation_history 
            WHERE can_be_undone = 1 AND dry_run = 0 AND successful_files > 0
        '''
        params = []
        
        if folder_path:
            query += ' AND source_directory = ?'
            params.append(folder_path)
            
        query += ' ORDER BY completed_at DESC LIMIT 1'
        
        operation = self.db.fetch_one(query, tuple(params))
        
        if operation:
            # Quick validation check
            eligibility = self.can_undo_operation(operation['operation_id'])
            if eligibility.can_undo:
                return dict(operation)
                
        return None
    
    def cleanup_expired_undo_operations(self) -> int:
        """Clean up expired undo operations and update eligibility"""
        expiry_time = datetime.now() - timedelta(days=self.default_undo_expiry_days)
        
        try:
            # Mark expired operations as non-undoable
            updated_count = self.db.execute_update('''
                UPDATE operation_history 
                SET can_be_undone = 0 
                WHERE can_be_undone = 1 
                  AND completed_at < ?
                  AND completed_at IS NOT NULL
            ''', (expiry_time.isoformat(),))
            
            # Clean up old undo operation records
            deleted_count = self.db.execute_update('''
                DELETE FROM undo_operations 
                WHERE created_at < ?
            ''', (expiry_time.isoformat(),))
            
            # Clean up old validation cache entries
            self.db.execute_update('''
                DELETE FROM file_validation_cache 
                WHERE last_validated_time < ?
            ''', (expiry_time.isoformat(),))
            
            logger.info(f"Cleaned up {updated_count} expired undo operations, deleted {deleted_count} old undo records")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired undo operations: {e}")
            return 0
    
    def get_undo_operation_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get history of undo operations"""
        try:
            rows = self.db.fetch_all('''
                SELECT * FROM undo_operations 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            operations = []
            for row in rows:
                op_dict = dict(row)
                
                # Parse JSON fields
                if op_dict['file_mappings']:
                    op_dict['file_mappings'] = json.loads(op_dict['file_mappings'])
                if op_dict['restored_files']:
                    op_dict['restored_files'] = json.loads(op_dict['restored_files'])
                if op_dict['failed_files']:
                    op_dict['failed_files'] = json.loads(op_dict['failed_files'])
                    
                operations.append(op_dict)
            
            return operations
            
        except Exception as e:
            logger.error(f"Failed to get undo operation history: {e}")
            return []