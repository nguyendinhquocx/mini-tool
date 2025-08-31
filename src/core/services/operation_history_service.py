"""
Operation History Service

Manages persistent storage and retrieval of batch operation history.
Provides undo functionality for reversing completed operations.
"""

import os
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

from ..models.operation import BatchOperation, OperationType
from ..models.file_info import FileProcessingRecord, OperationStatus
from .database_service import DatabaseService

# Configure logging
logger = logging.getLogger(__name__)


class OperationHistoryService:
    """
    Service for managing operation history and undo functionality
    
    Features:
    - Persistent operation history storage
    - Detailed file operation tracking
    - Undo operation support
    - History cleanup and maintenance
    - Operation statistics and reporting
    """
    
    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or DatabaseService()
        
    def save_operation(self, operation: BatchOperation, 
                      file_records: List[FileProcessingRecord]) -> bool:
        """
        Save completed operation to history
        
        Args:
            operation: Batch operation to save
            file_records: List of individual file processing records
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Prepare operation data
            operation_data = (
                operation.operation_id,
                operation.operation_name,
                operation.operation_type.value,
                operation.source_directory,
                operation.target_directory,
                operation.total_files,
                operation.successful_operations,
                operation.failed_operations,
                operation.skipped_operations,
                operation.dry_run,
                'completed' if operation.is_completed() else 'failed',
                operation.created_at.isoformat() if operation.created_at else None,
                operation.started_at.isoformat() if operation.started_at else None,
                operation.completed_at.isoformat() if operation.completed_at else None,
                operation.get_duration(),
                json.dumps(operation.normalization_rules.to_dict()),
                json.dumps(operation.operation_log),
                json.dumps(operation.error_log),
                None  # error_summary will be generated if needed
            )
            
            # Insert operation record
            self.db.execute_update('''
                INSERT OR REPLACE INTO operation_history (
                    operation_id, operation_name, operation_type, source_directory,
                    target_directory, total_files, successful_files, failed_files,
                    skipped_files, dry_run, status, created_at, started_at,
                    completed_at, duration_seconds, normalization_rules,
                    operation_log, error_log, error_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', operation_data)
            
            # Save individual file records
            file_data = []
            for record in file_records:
                file_data.append((
                    operation.operation_id,
                    record.source_path,
                    record.original_name,
                    record.processed_name,
                    record.operation_status.value,
                    record.error_message,
                    json.dumps(record.processing_steps),
                    record.backup_path,
                    record.backup_created,
                    record.started_at.isoformat() if record.started_at else None,
                    record.completed_at.isoformat() if record.completed_at else None,
                    record.processing_duration
                ))
                
            if file_data:
                self.db.execute_many('''
                    INSERT INTO file_operations (
                        operation_id, file_path, original_name, new_name,
                        operation_status, error_message, processing_steps,
                        backup_path, backup_created, started_at, completed_at,
                        duration_seconds
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', file_data)
                
            logger.info(f"Saved operation {operation.operation_id} with {len(file_records)} file records")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save operation {operation.operation_id}: {e}")
            return False
            
    def get_operation_history(self, limit: int = 50, 
                            operation_type: Optional[OperationType] = None,
                            days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Get operation history with optional filtering
        
        Args:
            limit: Maximum number of operations to return
            operation_type: Filter by operation type
            days_back: Only return operations from last N days
            
        Returns:
            List of operation history records
        """
        # Build query with optional filters
        query = '''
            SELECT * FROM operation_history 
            WHERE created_at >= datetime('now', '-{} days')
        '''.format(days_back)
        
        params = []
        
        if operation_type:
            query += ' AND operation_type = ?'
            params.append(operation_type.value)
            
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        rows = self.db.fetch_all(query, tuple(params))
        
        # Convert to dictionaries with parsed JSON fields
        operations = []
        for row in rows:
            op_dict = dict(row)
            
            # Parse JSON fields
            if op_dict['normalization_rules']:
                op_dict['normalization_rules'] = json.loads(op_dict['normalization_rules'])
            if op_dict['operation_log']:
                op_dict['operation_log'] = json.loads(op_dict['operation_log'])
            if op_dict['error_log']:
                op_dict['error_log'] = json.loads(op_dict['error_log'])
                
            operations.append(op_dict)
            
        return operations
        
    def get_operation_details(self, operation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific operation
        
        Args:
            operation_id: Operation to retrieve
            
        Returns:
            Operation details with file records, or None if not found
        """
        # Get operation record
        op_row = self.db.fetch_one(
            'SELECT * FROM operation_history WHERE operation_id = ?',
            (operation_id,)
        )
        
        if not op_row:
            return None
            
        operation = dict(op_row)
        
        # Parse JSON fields
        if operation['normalization_rules']:
            operation['normalization_rules'] = json.loads(operation['normalization_rules'])
        if operation['operation_log']:
            operation['operation_log'] = json.loads(operation['operation_log'])
        if operation['error_log']:
            operation['error_log'] = json.loads(operation['error_log'])
            
        # Get file operation records
        file_rows = self.db.fetch_all(
            '''SELECT * FROM file_operations 
               WHERE operation_id = ? 
               ORDER BY started_at''',
            (operation_id,)
        )
        
        file_records = []
        for row in file_rows:
            file_record = dict(row)
            if file_record['processing_steps']:
                file_record['processing_steps'] = json.loads(file_record['processing_steps'])
            file_records.append(file_record)
            
        operation['file_records'] = file_records
        return operation
        
    def can_undo_operation(self, operation_id: str) -> Tuple[bool, str]:
        """
        Check if an operation can be undone
        
        Args:
            operation_id: Operation to check
            
        Returns:
            Tuple of (can_undo, reason)
        """
        operation = self.get_operation_details(operation_id)
        
        if not operation:
            return False, "Operation not found"
            
        if operation['dry_run']:
            return False, "Cannot undo dry run operation"
            
        if operation['successful_files'] == 0:
            return False, "No successful operations to undo"
            
        # Check if files still exist and can be reverted
        successful_files = [
            record for record in operation['file_records'] 
            if record['operation_status'] == OperationStatus.SUCCESS.value
        ]
        
        missing_files = []
        readonly_files = []
        
        for record in successful_files:
            current_path = os.path.join(
                operation['source_directory'], 
                record['new_name']
            )
            original_path = os.path.join(
                operation['source_directory'],
                record['original_name']
            )
            
            # Check if current file exists
            if not os.path.exists(current_path):
                missing_files.append(record['new_name'])
                continue
                
            # Check if we can write to restore original name
            if os.path.exists(original_path) and not os.access(original_path, os.W_OK):
                readonly_files.append(record['original_name'])
                
        if missing_files:
            return False, f"Files missing: {', '.join(missing_files[:3])}{'...' if len(missing_files) > 3 else ''}"
            
        if readonly_files:
            return False, f"Files readonly: {', '.join(readonly_files[:3])}{'...' if len(readonly_files) > 3 else ''}"
            
        # Check if operation is too old (safety measure)
        if operation['completed_at']:
            completed_time = datetime.fromisoformat(operation['completed_at'])
            if datetime.now() - completed_time > timedelta(days=7):
                return False, "Operation too old (>7 days)"
                
        return True, "Operation can be undone"
        
    def undo_operation(self, operation_id: str, 
                      progress_callback: Optional[callable] = None) -> Tuple[bool, str, List[str]]:
        """
        Undo a completed operation by reverting file names
        
        Args:
            operation_id: Operation to undo
            progress_callback: Optional callback for progress updates
            
        Returns:
            Tuple of (success, message, failed_files)
        """
        # Check if operation can be undone
        can_undo, reason = self.can_undo_operation(operation_id)
        if not can_undo:
            return False, reason, []
            
        operation = self.get_operation_details(operation_id)
        successful_files = [
            record for record in operation['file_records'] 
            if record['operation_status'] == OperationStatus.SUCCESS.value
        ]
        
        failed_files = []
        reverted_count = 0
        
        try:
            for i, record in enumerate(successful_files):
                if progress_callback:
                    progress = (i / len(successful_files)) * 100
                    progress_callback(progress, f"Reverting {record['new_name']}")
                    
                current_path = os.path.join(
                    operation['source_directory'],
                    record['new_name']
                )
                original_path = os.path.join(
                    operation['source_directory'],
                    record['original_name']
                )
                
                try:
                    # Revert file name
                    if os.path.exists(current_path):
                        os.rename(current_path, original_path)
                        reverted_count += 1
                        logger.info(f"Reverted {record['new_name']} → {record['original_name']}")
                    else:
                        failed_files.append(f"{record['new_name']} (file not found)")
                        
                except Exception as e:
                    failed_files.append(f"{record['new_name']} ({str(e)})")
                    logger.error(f"Failed to revert {record['new_name']}: {e}")
                    
            # Create undo operation record
            undo_operation = BatchOperation(
                operation_type=OperationType.RESTORE,
                normalization_rules=operation['normalization_rules'],
                source_directory=operation['source_directory'],
                total_files=len(successful_files),
                operation_name=f"Undo: {operation['operation_name']}"
            )
            
            undo_operation.successful_operations = reverted_count
            undo_operation.failed_operations = len(failed_files)
            undo_operation.start_operation()
            undo_operation.complete_operation()
            undo_operation.log_message(f"Undid operation {operation_id}")
            
            if failed_files:
                for failed in failed_files:
                    undo_operation.log_error(f"Failed to revert: {failed}")
                    
            # Save undo operation to history
            self.save_operation(undo_operation, [])
            
            if progress_callback:
                progress_callback(100.0, "Undo completed")
                
            if failed_files:
                return True, f"Partially undone: {reverted_count} reverted, {len(failed_files)} failed", failed_files
            else:
                return True, f"Successfully undone: {reverted_count} files reverted", []
                
        except Exception as e:
            logger.error(f"Undo operation failed: {e}")
            return False, f"Undo failed: {str(e)}", failed_files
            
    def cleanup_old_operations(self, days_to_keep: int = 30) -> int:
        """
        Clean up old operation records
        
        Args:
            days_to_keep: Number of days of history to keep
            
        Returns:
            Number of operations removed
        """
        try:
            # Get operations to delete
            old_ops = self.db.fetch_all(
                "SELECT operation_id FROM operation_history WHERE created_at < datetime('now', '-{} days')".format(days_to_keep)
            )
            
            if not old_ops:
                return 0
                
            operation_ids = [row['operation_id'] for row in old_ops]
            
            # Delete file records first (foreign key constraint)
            self.db.execute_update(
                f"DELETE FROM file_operations WHERE operation_id IN ({','.join(['?'] * len(operation_ids))})",
                tuple(operation_ids)
            )
            
            # Delete operation records
            deleted_count = self.db.execute_update(
                f"DELETE FROM operation_history WHERE operation_id IN ({','.join(['?'] * len(operation_ids))})",
                tuple(operation_ids)
            )
            
            logger.info(f"Cleaned up {deleted_count} old operations older than {days_to_keep} days")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup old operations: {e}")
            return 0
            
    def get_operation_statistics(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Get operation statistics for the specified period
        
        Args:
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with various statistics
        """
        stats = {}
        
        # Total operations
        total_ops = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM operation_history WHERE created_at >= datetime('now', '-{} days')".format(days_back)
        )
        stats['total_operations'] = total_ops['count'] if total_ops else 0
        
        # Operations by type
        type_stats = self.db.fetch_all(
            "SELECT operation_type, COUNT(*) as count FROM operation_history WHERE created_at >= datetime('now', '-{} days') GROUP BY operation_type".format(days_back)
        )
        stats['operations_by_type'] = {row['operation_type']: row['count'] for row in type_stats}
        
        # Success rate
        success_stats = self.db.fetch_one(
            '''SELECT 
                SUM(successful_files) as total_success,
                SUM(failed_files) as total_failures,
                SUM(total_files) as total_processed
               FROM operation_history 
               WHERE created_at >= datetime('now', '-{} days')'''.format(days_back)
        )
        
        if success_stats and success_stats['total_processed']:
            stats['success_rate'] = (success_stats['total_success'] / success_stats['total_processed']) * 100
            stats['total_files_processed'] = success_stats['total_processed']
            stats['total_successes'] = success_stats['total_success']
            stats['total_failures'] = success_stats['total_failures']
        else:
            stats['success_rate'] = 0.0
            stats['total_files_processed'] = 0
            stats['total_successes'] = 0
            stats['total_failures'] = 0
            
        # Average duration
        duration_stats = self.db.fetch_one(
            "SELECT AVG(duration_seconds) as avg_duration FROM operation_history WHERE created_at >= datetime('now', '-{} days') AND duration_seconds IS NOT NULL".format(days_back)
        )
        stats['average_duration_seconds'] = duration_stats['avg_duration'] if duration_stats and duration_stats['avg_duration'] else 0.0
        
        return stats


# Example usage and testing
if __name__ == "__main__":
    def test_operation_history_service():
        """Test the operation history service"""
        import tempfile
        from ..models.operation import NormalizationRules
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
            
        try:
            # Initialize services
            db_service = DatabaseService(db_path)
            history_service = OperationHistoryService(db_service)
            
            # Create test operation
            operation = BatchOperation(
                operation_type=OperationType.BATCH_RENAME,
                normalization_rules=NormalizationRules(),
                source_directory="/test/path",
                total_files=3
            )
            
            operation.start_operation()
            operation.successful_operations = 2
            operation.failed_operations = 1
            operation.complete_operation()
            
            # Create test file records
            from ..models.file_info import FileInfo, FileProcessingRecord
            
            file_records = [
                FileProcessingRecord(
                    file_info=FileInfo("test1.txt", "test1.txt", "/test/path/test1.txt", None),
                    original_name="test1.txt",
                    processed_name="test1_normalized.txt",
                    operation_status=OperationStatus.SUCCESS,
                    operation_id=operation.operation_id,
                    source_path="/test/path/test1.txt",
                    target_path="/test/path/test1_normalized.txt"
                )
            ]
            
            # Test saving operation
            success = history_service.save_operation(operation, file_records)
            assert success, "Failed to save operation"
            
            # Test retrieving history
            history = history_service.get_operation_history()
            assert len(history) == 1, "Expected 1 operation in history"
            assert history[0]['operation_id'] == operation.operation_id
            
            # Test getting operation details
            details = history_service.get_operation_details(operation.operation_id)
            assert details is not None, "Failed to get operation details"
            assert len(details['file_records']) == 1
            
            # Test statistics
            stats = history_service.get_operation_statistics()
            assert stats['total_operations'] == 1
            assert stats['total_files_processed'] == 3
            
            print("Operation history service test completed successfully")
            
        finally:
            # Cleanup
            try:
                os.unlink(db_path)
            except OSError:
                pass
                
    test_operation_history_service()