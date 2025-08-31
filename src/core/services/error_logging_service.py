"""
Comprehensive Error Logging Service

Provides sophisticated error logging, analysis, and reporting capabilities
with structured logging, correlation tracking, and performance metrics.
"""

import logging
import logging.handlers
import json
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum
import sqlite3
import traceback

from ..models.error_models import ApplicationError, ErrorCode, ErrorSeverity
from ..models.operation import OperationResult, OperationStatus
from .database_service import DatabaseService


class LogLevel(Enum):
    """Enhanced log levels"""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
    FATAL = 60


@dataclass
class ErrorLogEntry:
    """Structured error log entry"""
    timestamp: datetime
    session_id: str
    operation_id: Optional[str]
    error_id: str
    error_code: str
    severity: str
    message: str
    user_message: str
    file_path: Optional[str]
    
    # Technical details
    technical_details: Optional[str]
    stack_trace: Optional[str]
    system_info: Dict[str, Any]
    operation_context: Dict[str, Any]
    
    # Correlation and tracking
    correlation_id: Optional[str]
    parent_error_id: Optional[str]
    user_session_id: Optional[str]
    
    # Performance metrics
    processing_time_ms: Optional[float]
    memory_usage_mb: Optional[float]
    cpu_usage_percent: Optional[float]
    
    # Resolution tracking
    resolution_status: Optional[str] = None
    resolution_strategy: Optional[str] = None
    resolution_time: Optional[datetime] = None
    user_feedback: Optional[str] = None


@dataclass
class ErrorAnalysis:
    """Error analysis and patterns"""
    total_errors: int
    error_rate_per_hour: float
    most_common_errors: List[tuple]  # (error_code, count)
    error_trends: Dict[str, List[int]]  # hour -> count
    affected_operations: Set[str]
    critical_error_count: int
    recovery_success_rate: float
    
    # Performance impact
    avg_processing_time: float
    error_correlation_patterns: Dict[str, List[str]]
    
    # Recommendations
    suggested_improvements: List[str]
    high_risk_operations: List[str]


class ErrorMetricsCollector:
    """Collects and analyzes error metrics"""
    
    def __init__(self, window_hours: int = 24):
        self.window_hours = window_hours
        self._metrics_lock = threading.Lock()
        self._error_counts = defaultdict(int)
        self._hourly_counts = deque(maxlen=window_hours)
        self._processing_times = deque(maxlen=1000)
        self._correlation_map = defaultdict(list)
        
        # Initialize hourly buckets
        for _ in range(window_hours):
            self._hourly_counts.append(0)
        
        self._last_hour_update = datetime.now().hour
    
    def record_error(self, entry: ErrorLogEntry):
        """Record error for metrics analysis"""
        with self._metrics_lock:
            # Update error counts
            self._error_counts[entry.error_code] += 1
            
            # Update hourly counts
            current_hour = datetime.now().hour
            if current_hour != self._last_hour_update:
                # New hour, rotate counts
                self._hourly_counts.append(0)
                self._last_hour_update = current_hour
            
            self._hourly_counts[-1] += 1
            
            # Record processing time
            if entry.processing_time_ms:
                self._processing_times.append(entry.processing_time_ms)
            
            # Record correlations
            if entry.correlation_id and entry.operation_id:
                self._correlation_map[entry.correlation_id].append(entry.operation_id)
    
    def get_analysis(self) -> ErrorAnalysis:
        """Generate error analysis"""
        with self._metrics_lock:
            total_errors = sum(self._error_counts.values())
            
            # Calculate error rate
            hours_with_data = min(len(self._hourly_counts), self.window_hours)
            error_rate = total_errors / max(1, hours_with_data)
            
            # Most common errors
            most_common = sorted(self._error_counts.items(), 
                               key=lambda x: x[1], reverse=True)[:10]
            
            # Processing time metrics
            avg_processing_time = 0.0
            if self._processing_times:
                avg_processing_time = sum(self._processing_times) / len(self._processing_times)
            
            return ErrorAnalysis(
                total_errors=total_errors,
                error_rate_per_hour=error_rate,
                most_common_errors=most_common,
                error_trends=self._calculate_trends(),
                affected_operations=set(),
                critical_error_count=self._error_counts.get('CRITICAL', 0),
                recovery_success_rate=0.0,  # Would be calculated from resolution data
                avg_processing_time=avg_processing_time,
                error_correlation_patterns=dict(self._correlation_map),
                suggested_improvements=[],
                high_risk_operations=[]
            )
    
    def _calculate_trends(self) -> Dict[str, List[int]]:
        """Calculate error trends over time"""
        trends = {}
        
        # Simple hourly trend
        hourly_data = list(self._hourly_counts)
        trends['hourly'] = hourly_data
        
        return trends


class DatabaseErrorLogger:
    """Database-backed error logging"""
    
    def __init__(self, db_service: DatabaseService):
        self.db = db_service
        self._ensure_error_tables()
    
    def _ensure_error_tables(self):
        """Ensure error logging tables exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS error_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            session_id TEXT NOT NULL,
            operation_id TEXT,
            error_id TEXT NOT NULL,
            error_code TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            user_message TEXT NOT NULL,
            file_path TEXT,
            technical_details TEXT,
            stack_trace TEXT,
            system_info TEXT,
            operation_context TEXT,
            correlation_id TEXT,
            parent_error_id TEXT,
            user_session_id TEXT,
            processing_time_ms REAL,
            memory_usage_mb REAL,
            cpu_usage_percent REAL,
            resolution_status TEXT,
            resolution_strategy TEXT,
            resolution_time TEXT,
            user_feedback TEXT
        )
        """
        
        create_index_sql = [
            "CREATE INDEX IF NOT EXISTS idx_error_timestamp ON error_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_error_code ON error_logs(error_code)",
            "CREATE INDEX IF NOT EXISTS idx_error_severity ON error_logs(severity)",
            "CREATE INDEX IF NOT EXISTS idx_operation_id ON error_logs(operation_id)",
            "CREATE INDEX IF NOT EXISTS idx_correlation_id ON error_logs(correlation_id)"
        ]
        
        with self.db._get_connection() as conn:
            conn.execute(create_table_sql)
            for index_sql in create_index_sql:
                conn.execute(index_sql)
            conn.commit()
    
    def log_error(self, entry: ErrorLogEntry):
        """Store error log entry in database"""
        insert_sql = """
        INSERT INTO error_logs (
            timestamp, session_id, operation_id, error_id, error_code, severity,
            message, user_message, file_path, technical_details, stack_trace,
            system_info, operation_context, correlation_id, parent_error_id,
            user_session_id, processing_time_ms, memory_usage_mb, cpu_usage_percent,
            resolution_status, resolution_strategy, resolution_time, user_feedback
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        values = (
            entry.timestamp.isoformat(),
            entry.session_id,
            entry.operation_id,
            entry.error_id,
            entry.error_code,
            entry.severity,
            entry.message,
            entry.user_message,
            entry.file_path,
            entry.technical_details,
            entry.stack_trace,
            json.dumps(entry.system_info),
            json.dumps(entry.operation_context),
            entry.correlation_id,
            entry.parent_error_id,
            entry.user_session_id,
            entry.processing_time_ms,
            entry.memory_usage_mb,
            entry.cpu_usage_percent,
            entry.resolution_status,
            entry.resolution_strategy,
            entry.resolution_time.isoformat() if entry.resolution_time else None,
            entry.user_feedback
        )
        
        with self.db._get_connection() as conn:
            conn.execute(insert_sql, values)
            conn.commit()
    
    def get_errors(self, limit: int = 100, severity: Optional[str] = None,
                   operation_id: Optional[str] = None, 
                   since: Optional[datetime] = None) -> List[ErrorLogEntry]:
        """Retrieve error logs with filtering"""
        where_clauses = []
        params = []
        
        if severity:
            where_clauses.append("severity = ?")
            params.append(severity)
        
        if operation_id:
            where_clauses.append("operation_id = ?")
            params.append(operation_id)
        
        if since:
            where_clauses.append("timestamp >= ?")
            params.append(since.isoformat())
        
        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query_sql = f"""
        SELECT * FROM error_logs 
        {where_sql}
        ORDER BY timestamp DESC 
        LIMIT ?
        """
        params.append(limit)
        
        with self.db._get_connection() as conn:
            cursor = conn.execute(query_sql, params)
            rows = cursor.fetchall()
            
            errors = []
            for row in rows:
                entry = ErrorLogEntry(
                    timestamp=datetime.fromisoformat(row[1]),
                    session_id=row[2],
                    operation_id=row[3],
                    error_id=row[4],
                    error_code=row[5],
                    severity=row[6],
                    message=row[7],
                    user_message=row[8],
                    file_path=row[9],
                    technical_details=row[10],
                    stack_trace=row[11],
                    system_info=json.loads(row[12]) if row[12] else {},
                    operation_context=json.loads(row[13]) if row[13] else {},
                    correlation_id=row[14],
                    parent_error_id=row[15],
                    user_session_id=row[16],
                    processing_time_ms=row[17],
                    memory_usage_mb=row[18],
                    cpu_usage_percent=row[19],
                    resolution_status=row[20],
                    resolution_strategy=row[21],
                    resolution_time=datetime.fromisoformat(row[22]) if row[22] else None,
                    user_feedback=row[23]
                )
                errors.append(entry)
            
            return errors


class ComprehensiveErrorLoggingService:
    """Main error logging service with multiple output destinations"""
    
    def __init__(self, log_directory: str = "logs", 
                 database_service: Optional[DatabaseService] = None):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        # Initialize components
        self.db_logger = DatabaseErrorLogger(database_service or DatabaseService())
        self.metrics_collector = ErrorMetricsCollector()
        
        # Session tracking
        self.session_id = self._generate_session_id()
        self.start_time = datetime.now()
        
        # Configure file logging
        self._setup_file_logging()
        
        # Error correlation tracking
        self._correlation_counter = 0
        self._correlation_lock = threading.Lock()
        
        # Callbacks for real-time monitoring
        self.error_callbacks: List[Callable[[ErrorLogEntry], None]] = []
        
    def _generate_session_id(self) -> str:
        """Generate unique session identifier"""
        return f"session_{int(time.time())}_{id(self)}"
    
    def _setup_file_logging(self):
        """Setup file-based logging with rotation"""
        log_file = self.log_directory / "file_rename_tool.log"
        error_log_file = self.log_directory / "errors.log"
        
        # Main application logger
        self.app_logger = logging.getLogger('file_rename_tool')
        self.app_logger.setLevel(logging.DEBUG)
        
        # Rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5  # 10MB files, keep 5
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Error-only file handler
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file, maxBytes=5*1024*1024, backupCount=3  # 5MB files, keep 3
        )
        error_handler.setLevel(logging.ERROR)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        
        self.app_logger.addHandler(file_handler)
        self.app_logger.addHandler(error_handler)
    
    def log_application_error(self, error: ApplicationError, 
                            operation_id: Optional[str] = None,
                            processing_time_ms: Optional[float] = None,
                            system_metrics: Optional[Dict[str, Any]] = None) -> str:
        """Log an ApplicationError with comprehensive details"""
        
        # Generate correlation ID if needed
        correlation_id = error.correlation_id or self._generate_correlation_id()
        
        # Collect system information
        system_info = self._collect_system_info()
        if system_metrics:
            system_info.update(system_metrics)
        
        # Create log entry
        entry = ErrorLogEntry(
            timestamp=datetime.now(),
            session_id=self.session_id,
            operation_id=operation_id,
            error_id=str(id(error)),
            error_code=error.code.value,
            severity=error.severity.value,
            message=error.message,
            user_message=error.to_user_message(),
            file_path=error.file_path,
            technical_details=error.technical_details,
            stack_trace=traceback.format_exc() if error.exception_info else None,
            system_info=system_info,
            operation_context=error.operation_context,
            correlation_id=correlation_id,
            parent_error_id=error.parent_error_id,
            user_session_id=None,  # Could be set from UI layer
            processing_time_ms=processing_time_ms,
            memory_usage_mb=system_info.get('memory_usage_mb'),
            cpu_usage_percent=system_info.get('cpu_usage_percent')
        )
        
        # Log to all destinations
        self._log_to_file(entry)
        self.db_logger.log_error(entry)
        self.metrics_collector.record_error(entry)
        
        # Notify callbacks
        for callback in self.error_callbacks:
            try:
                callback(entry)
            except Exception as e:
                self.app_logger.error(f"Error in callback: {e}")
        
        return correlation_id
    
    def log_operation_result(self, result: OperationResult):
        """Log operation completion with result analysis"""
        log_level = logging.INFO
        message = f"Operation {result.operation_id} completed"
        
        if result.status == OperationStatus.FAILED:
            log_level = logging.ERROR
            message = f"Operation {result.operation_id} failed"
        elif result.status == OperationStatus.PARTIAL_SUCCESS:
            log_level = logging.WARNING
            message = f"Operation {result.operation_id} partially successful"
        
        # Add metrics to message
        if hasattr(result, 'success_count') and hasattr(result, 'total_files'):
            success_rate = (result.success_count / result.total_files) * 100 if result.total_files > 0 else 0
            message += f" - Success rate: {success_rate:.1f}%"
        
        self.app_logger.log(log_level, message, extra={
            'operation_id': result.operation_id,
            'status': result.status.value,
            'session_id': self.session_id
        })
    
    def _log_to_file(self, entry: ErrorLogEntry):
        """Log entry to file with appropriate level"""
        level_map = {
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        
        level = level_map.get(entry.severity, logging.ERROR)
        
        # Create structured log message
        log_data = {
            'error_id': entry.error_id,
            'error_code': entry.error_code,
            'file_path': entry.file_path,
            'operation_id': entry.operation_id,
            'correlation_id': entry.correlation_id,
            'session_id': entry.session_id
        }
        
        self.app_logger.log(level, entry.message, extra=log_data)
    
    def _generate_correlation_id(self) -> str:
        """Generate correlation ID for tracking related errors"""
        with self._correlation_lock:
            self._correlation_counter += 1
            return f"corr_{self.session_id}_{self._correlation_counter}"
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for logging"""
        import platform
        import psutil
        
        try:
            process = psutil.Process()
            
            return {
                'platform': platform.system(),
                'platform_version': platform.version(),
                'python_version': platform.python_version(),
                'memory_usage_mb': process.memory_info().rss / 1024 / 1024,
                'cpu_usage_percent': process.cpu_percent(),
                'thread_count': process.num_threads(),
                'disk_usage': {
                    'free_gb': psutil.disk_usage('.').free / 1024 / 1024 / 1024,
                    'total_gb': psutil.disk_usage('.').total / 1024 / 1024 / 1024
                }
            }
        except Exception as e:
            return {
                'platform': platform.system(),
                'error': f"Could not collect system info: {e}"
            }
    
    def get_error_analysis(self, hours: int = 24) -> ErrorAnalysis:
        """Get comprehensive error analysis"""
        return self.metrics_collector.get_analysis()
    
    def get_recent_errors(self, limit: int = 50) -> List[ErrorLogEntry]:
        """Get recent errors from database"""
        return self.db_logger.get_errors(limit=limit)
    
    def get_errors_for_operation(self, operation_id: str) -> List[ErrorLogEntry]:
        """Get all errors for specific operation"""
        return self.db_logger.get_errors(operation_id=operation_id, limit=1000)
    
    def add_error_callback(self, callback: Callable[[ErrorLogEntry], None]):
        """Add callback for real-time error monitoring"""
        self.error_callbacks.append(callback)
    
    def update_error_resolution(self, correlation_id: str, 
                              resolution_status: str,
                              resolution_strategy: Optional[str] = None,
                              user_feedback: Optional[str] = None):
        """Update error resolution information"""
        # This would update the database record
        # Implementation depends on specific database schema
        pass
    
    def export_error_report(self, output_file: str, 
                          since: Optional[datetime] = None,
                          format: str = 'json') -> str:
        """Export error report to file"""
        since = since or (datetime.now() - timedelta(days=7))
        errors = self.db_logger.get_errors(limit=10000, since=since)
        
        if format.lower() == 'json':
            report_data = {
                'export_time': datetime.now().isoformat(),
                'session_id': self.session_id,
                'period_start': since.isoformat(),
                'period_end': datetime.now().isoformat(),
                'total_errors': len(errors),
                'analysis': asdict(self.get_error_analysis()),
                'errors': [asdict(error) for error in errors]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, default=str)
        
        return output_file
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Clean up old log entries"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        delete_sql = "DELETE FROM error_logs WHERE timestamp < ?"
        
        with self.db_logger.db._get_connection() as conn:
            cursor = conn.execute(delete_sql, (cutoff_date.isoformat(),))
            deleted_count = cursor.rowcount
            conn.commit()
        
        self.app_logger.info(f"Cleaned up {deleted_count} old error log entries")
        return deleted_count


# Global instance for application-wide error logging
_global_error_logging_service: Optional[ComprehensiveErrorLoggingService] = None


def get_error_logging_service() -> ComprehensiveErrorLoggingService:
    """Get global error logging service instance"""
    global _global_error_logging_service
    if _global_error_logging_service is None:
        _global_error_logging_service = ComprehensiveErrorLoggingService()
    return _global_error_logging_service


def log_application_error(error: ApplicationError, 
                        operation_id: Optional[str] = None,
                        processing_time_ms: Optional[float] = None) -> str:
    """Convenience function for logging application errors"""
    return get_error_logging_service().log_application_error(
        error, operation_id, processing_time_ms
    )