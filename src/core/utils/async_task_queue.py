"""
Asynchronous Task Queue System

Provides background task processing, priority scheduling, và cancellation
support for non-blocking operations.
"""

import asyncio
import threading
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set, Union
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = 0    # System critical tasks
    HIGH = 1        # User-initiated actions
    NORMAL = 2      # Regular operations  
    LOW = 3         # Background maintenance
    IDLE = 4        # Run when nothing else to do


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class TaskResult:
    """Result of task execution"""
    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[Exception] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class Task:
    """Async task wrapper"""
    task_id: str
    coroutine: Coroutine
    priority: TaskPriority
    name: str = ""
    timeout_seconds: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 0
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.name:
            self.name = f"Task-{self.task_id[:8]}"


class CancellationToken:
    """Token for cancelling long-running operations"""
    
    def __init__(self):
        self._cancelled = False
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()
    
    def cancel(self):
        """Cancel the operation"""
        with self._lock:
            if not self._cancelled:
                self._cancelled = True
                for callback in self._callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f"Error in cancellation callback: {e}")
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled"""
        return self._cancelled
    
    def add_callback(self, callback: Callable[[], None]):
        """Add callback to be called when cancelled"""
        with self._lock:
            if self._cancelled:
                callback()
            else:
                self._callbacks.append(callback)
    
    def throw_if_cancelled(self):
        """Raise exception if cancelled"""
        if self._cancelled:
            raise asyncio.CancelledError("Operation was cancelled")


class AsyncTaskQueue:
    """
    Asynchronous task queue với priority scheduling
    """
    
    def __init__(
        self,
        max_concurrent_tasks: int = 10,
        enable_priorities: bool = True,
        default_timeout: float = 300.0  # 5 minutes
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.enable_priorities = enable_priorities
        self.default_timeout = default_timeout
        
        # Task management
        self._task_queues: Dict[TaskPriority, asyncio.Queue] = {
            priority: asyncio.Queue() for priority in TaskPriority
        }
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._completed_tasks: Dict[str, TaskResult] = {}
        self._task_semaphore = asyncio.Semaphore(max_concurrent_tasks)
        
        # Event loop management
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = asyncio.Event()
        self._worker_tasks: List[asyncio.Task] = []
        
        # Statistics
        self._stats = {
            'tasks_submitted': 0,
            'tasks_completed': 0,
            'tasks_failed': 0,
            'tasks_cancelled': 0,
            'total_execution_time': 0.0
        }
        
        self._running = False
        
        logger.info(f"AsyncTaskQueue initialized với {max_concurrent_tasks} max concurrent tasks")
    
    def start(self):
        """Start the task queue processing"""
        if self._running:
            logger.warning("Task queue already running")
            return
        
        self._running = True
        
        def run_event_loop():
            """Run event loop trong separate thread"""
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            try:
                # Start worker tasks
                self._start_workers()
                
                # Run until shutdown
                self._loop.run_until_complete(self._shutdown_event.wait())
                
            except Exception as e:
                logger.error(f"Error in event loop: {e}")
            finally:
                self._loop.close()
        
        self._loop_thread = threading.Thread(target=run_event_loop, daemon=True)
        self._loop_thread.start()
        
        # Wait for loop to be ready
        timeout = 5.0
        start_time = time.time()
        while self._loop is None and (time.time() - start_time) < timeout:
            time.sleep(0.01)
        
        if self._loop is None:
            raise RuntimeError("Failed to start event loop")
        
        logger.info("Task queue started")
    
    def _start_workers(self):
        """Start worker coroutines"""
        for i in range(self.max_concurrent_tasks):
            worker_task = self._loop.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(worker_task)
        
        logger.debug(f"Started {len(self._worker_tasks)} worker tasks")
    
    async def _worker(self, worker_name: str):
        """Worker coroutine to process tasks"""
        logger.debug(f"Worker {worker_name} started")
        
        try:
            while not self._shutdown_event.is_set():
                task = await self._get_next_task()
                
                if task is None:
                    # No task available, wait a bit
                    await asyncio.sleep(0.1)
                    continue
                
                # Process task
                await self._process_task(task)
                
        except asyncio.CancelledError:
            logger.debug(f"Worker {worker_name} cancelled")
        except Exception as e:
            logger.error(f"Error in worker {worker_name}: {e}")
        finally:
            logger.debug(f"Worker {worker_name} stopped")
    
    async def _get_next_task(self) -> Optional[Task]:
        """Get next task from priority queues"""
        if self.enable_priorities:
            # Check queues in priority order
            for priority in TaskPriority:
                queue = self._task_queues[priority]
                try:
                    task = queue.get_nowait()
                    return task
                except asyncio.QueueEmpty:
                    continue
        else:
            # Just use NORMAL priority queue
            queue = self._task_queues[TaskPriority.NORMAL]
            try:
                task = queue.get_nowait()
                return task
            except asyncio.QueueEmpty:
                pass
        
        return None
    
    async def _process_task(self, task: Task):
        """Process a single task"""
        async with self._task_semaphore:
            start_time = time.time()
            task_result = TaskResult(
                task_id=task.task_id,
                status=TaskStatus.RUNNING,
                start_time=start_time
            )
            
            try:
                logger.debug(f"Starting task {task.name} ({task.task_id})")
                
                # Store running task
                running_task = asyncio.current_task()
                self._running_tasks[task.task_id] = running_task
                
                # Execute với timeout
                if task.timeout_seconds:
                    timeout = task.timeout_seconds
                else:
                    timeout = self.default_timeout
                
                result = await asyncio.wait_for(task.coroutine, timeout=timeout)
                
                # Task completed successfully
                end_time = time.time()
                task_result.status = TaskStatus.COMPLETED
                task_result.result = result
                task_result.end_time = end_time
                
                self._stats['tasks_completed'] += 1
                self._stats['total_execution_time'] += (end_time - start_time)
                
                logger.debug(f"Task {task.name} completed in {end_time - start_time:.2f}s")
                
            except asyncio.TimeoutError:
                logger.warning(f"Task {task.name} timed out after {timeout}s")
                task_result.status = TaskStatus.FAILED
                task_result.error = TimeoutError(f"Task timed out after {timeout}s")
                task_result.end_time = time.time()
                self._stats['tasks_failed'] += 1
                
            except asyncio.CancelledError:
                logger.info(f"Task {task.name} was cancelled")
                task_result.status = TaskStatus.CANCELLED
                task_result.end_time = time.time()
                self._stats['tasks_cancelled'] += 1
                
            except Exception as e:
                logger.error(f"Task {task.name} failed: {e}")
                task_result.status = TaskStatus.FAILED
                task_result.error = e
                task_result.end_time = time.time()
                self._stats['tasks_failed'] += 1
                
                # Retry logic
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    logger.info(f"Retrying task {task.name} (attempt {task.retry_count + 1})")
                    await self.submit_task(task.coroutine, task.priority, task.name, 
                                          timeout_seconds=task.timeout_seconds,
                                          max_retries=task.max_retries - task.retry_count)
                    return
                
            finally:
                # Clean up
                if task.task_id in self._running_tasks:
                    del self._running_tasks[task.task_id]
                
                # Store result
                self._completed_tasks[task.task_id] = task_result
                
                # Cleanup old completed tasks (keep last 1000)
                if len(self._completed_tasks) > 1000:
                    oldest_tasks = sorted(
                        self._completed_tasks.items(),
                        key=lambda x: x[1].start_time or 0
                    )[:100]
                    for task_id, _ in oldest_tasks:
                        del self._completed_tasks[task_id]
    
    def submit_task(
        self,
        coroutine: Coroutine,
        priority: TaskPriority = TaskPriority.NORMAL,
        name: str = "",
        timeout_seconds: Optional[float] = None,
        max_retries: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Submit task for async execution
        
        Args:
            coroutine: Coroutine to execute
            priority: Task priority
            name: Optional task name
            timeout_seconds: Optional timeout override
            max_retries: Maximum retry attempts
            metadata: Optional task metadata
            
        Returns:
            Task ID for tracking
        """
        if not self._running:
            raise RuntimeError("Task queue is not running")
        
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            coroutine=coroutine,
            priority=priority,
            name=name,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        # Submit to appropriate queue
        queue = self._task_queues[priority]
        
        def submit():
            self._loop.call_soon_threadsafe(queue.put_nowait, task)
        
        if self._loop and self._loop.is_running():
            submit()
        else:
            raise RuntimeError("Event loop not available")
        
        self._stats['tasks_submitted'] += 1
        
        logger.debug(f"Submitted task {task.name} ({task_id}) với priority {priority.name}")
        
        return task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task
        
        Args:
            task_id: ID of task to cancel
            
        Returns:
            True if task was cancelled, False if not found or already completed
        """
        if task_id in self._running_tasks:
            running_task = self._running_tasks[task_id]
            running_task.cancel()
            logger.info(f"Cancelled task {task_id}")
            return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[TaskResult]:
        """Get status of a task"""
        if task_id in self._completed_tasks:
            return self._completed_tasks[task_id]
        
        if task_id in self._running_tasks:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.RUNNING
            )
        
        return None
    
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[TaskResult]:
        """
        Wait for task completion (blocking)
        
        Args:
            task_id: Task ID to wait for
            timeout: Optional timeout in seconds
            
        Returns:
            Task result or None if timeout
        """
        start_time = time.time()
        
        while True:
            result = self.get_task_status(task_id)
            
            if result and result.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return result
            
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            time.sleep(0.1)
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        queue_sizes = {}
        for priority, queue in self._task_queues.items():
            queue_sizes[priority.name] = queue.qsize()
        
        return {
            'running_tasks': len(self._running_tasks),
            'completed_tasks': len(self._completed_tasks),
            'queue_sizes': queue_sizes,
            'max_concurrent': self.max_concurrent_tasks,
            'statistics': self._stats.copy()
        }
    
    def clear_completed_tasks(self):
        """Clear completed task history"""
        self._completed_tasks.clear()
        logger.info("Cleared completed task history")
    
    async def shutdown(self, timeout: float = 10.0):
        """
        Shutdown task queue gracefully
        
        Args:
            timeout: Maximum time to wait for tasks to complete
        """
        if not self._running:
            return
        
        logger.info("Shutting down task queue...")
        
        # Cancel all running tasks
        for task_id, task in self._running_tasks.items():
            logger.debug(f"Cancelling running task {task_id}")
            task.cancel()
        
        # Wait for tasks to complete (với timeout)
        if self._running_tasks:
            try:
                await asyncio.wait_for(
                    self._wait_for_tasks_completion(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                logger.warning(f"Some tasks did not complete within {timeout}s")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel worker tasks
        for worker_task in self._worker_tasks:
            worker_task.cancel()
        
        # Wait for workers to stop
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        self._running = False
        logger.info("Task queue shutdown complete")
    
    async def _wait_for_tasks_completion(self):
        """Wait for all running tasks to complete"""
        while self._running_tasks:
            await asyncio.sleep(0.1)
    
    def force_shutdown(self):
        """Force immediate shutdown (non-blocking)"""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        
        self._running = False
        logger.warning("Task queue force shutdown")


class TaskManager:
    """
    High-level task management interface
    """
    
    def __init__(self, task_queue: Optional[AsyncTaskQueue] = None):
        self.task_queue = task_queue or AsyncTaskQueue()
        self._cancellation_tokens: Dict[str, CancellationToken] = {}
        
        if not self.task_queue._running:
            self.task_queue.start()
    
    @asynccontextmanager
    async def cancellable_task(self, name: str = ""):
        """Context manager for cancellable tasks"""
        token = CancellationToken()
        token_id = str(uuid.uuid4())
        self._cancellation_tokens[token_id] = token
        
        try:
            yield token
        finally:
            if token_id in self._cancellation_tokens:
                del self._cancellation_tokens[token_id]
    
    def submit_file_operation(
        self,
        operation_coro: Coroutine,
        operation_name: str = "",
        priority: TaskPriority = TaskPriority.HIGH
    ) -> str:
        """Submit file-related operation"""
        return self.task_queue.submit_task(
            operation_coro,
            priority=priority,
            name=f"FileOp: {operation_name}",
            timeout_seconds=600.0,  # 10 minutes for file operations
            max_retries=1
        )
    
    def submit_background_task(
        self,
        task_coro: Coroutine,
        task_name: str = ""
    ) -> str:
        """Submit background maintenance task"""
        return self.task_queue.submit_task(
            task_coro,
            priority=TaskPriority.LOW,
            name=f"Background: {task_name}",
            timeout_seconds=3600.0,  # 1 hour for background tasks
            max_retries=0
        )
    
    def submit_ui_task(
        self,
        ui_coro: Coroutine,
        task_name: str = ""
    ) -> str:
        """Submit UI-related task"""
        return self.task_queue.submit_task(
            ui_coro,
            priority=TaskPriority.HIGH,
            name=f"UI: {task_name}",
            timeout_seconds=30.0,  # Quick timeout for UI tasks
            max_retries=0
        )
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        return self.task_queue.cancel_task(task_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        queue_stats = self.task_queue.get_queue_stats()
        
        return {
            'queue_stats': queue_stats,
            'cancellation_tokens': len(self._cancellation_tokens)
        }
    
    async def shutdown(self):
        """Shutdown task manager"""
        await self.task_queue.shutdown()


# Global instance
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get global TaskManager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def set_task_manager(manager: TaskManager):
    """Set global TaskManager instance"""
    global _task_manager
    _task_manager = manager