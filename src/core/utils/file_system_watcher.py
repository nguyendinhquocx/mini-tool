"""
File System Watcher

Monitors file system changes với debounced notifications
và efficient change detection for selected directories.
"""

import os
import time
import threading
from typing import Callable, Dict, List, Optional, Set
from dataclasses import dataclass
from collections import defaultdict
import logging

# Conditional imports for different platforms
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = None
    FileSystemEvent = None

logger = logging.getLogger(__name__)


@dataclass
class FileSystemChange:
    """Represents a file system change event"""
    path: str
    event_type: str  # 'created', 'modified', 'deleted', 'moved'
    is_directory: bool = False
    old_path: Optional[str] = None  # For move events
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class ChangeBuffer:
    """Buffers changes để implement debouncing"""
    
    def __init__(self, debounce_delay: float = 0.5):
        self.debounce_delay = debounce_delay
        self._changes: Dict[str, FileSystemChange] = {}
        self._timers: Dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[List[FileSystemChange]], None]] = []
    
    def add_callback(self, callback: Callable[[List[FileSystemChange]], None]):
        """Add callback for debounced changes"""
        self._callbacks.append(callback)
    
    def add_change(self, change: FileSystemChange):
        """Add change to buffer"""
        with self._lock:
            # Cancel existing timer for this path
            if change.path in self._timers:
                self._timers[change.path].cancel()
            
            # Store/update change
            self._changes[change.path] = change
            
            # Schedule debounced callback
            timer = threading.Timer(self.debounce_delay, self._flush_change, args=[change.path])
            self._timers[change.path] = timer
            timer.start()
    
    def _flush_change(self, path: str):
        """Flush single change after debounce delay"""
        with self._lock:
            if path in self._changes:
                change = self._changes.pop(path)
                if path in self._timers:
                    del self._timers[path]
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback([change])
                    except Exception as e:
                        logger.error(f"Error in change callback: {e}")
    
    def flush_all(self):
        """Flush all pending changes immediately"""
        with self._lock:
            if not self._changes:
                return
            
            # Cancel all timers
            for timer in self._timers.values():
                timer.cancel()
            
            # Collect all changes
            changes = list(self._changes.values())
            self._changes.clear()
            self._timers.clear()
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    callback(changes)
                except Exception as e:
                    logger.error(f"Error in change callback: {e}")
    
    def clear(self):
        """Clear all pending changes"""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._changes.clear()
            self._timers.clear()


class WatchdogFileSystemWatcher(FileSystemEventHandler):
    """
    File system watcher using watchdog library
    """
    
    def __init__(
        self,
        debounce_delay: float = 0.5,
        watch_directories: bool = True,
        watch_files: bool = True
    ):
        super().__init__()
        self.debounce_delay = debounce_delay
        self.watch_directories = watch_directories
        self.watch_files = watch_files
        
        self.change_buffer = ChangeBuffer(debounce_delay)
        self.observer: Optional[Observer] = None
        self._watched_paths: Set[str] = set()
        self._running = False
        
        logger.info(f"WatchdogFileSystemWatcher initialized (debounce: {debounce_delay}s)")
    
    def add_callback(self, callback: Callable[[List[FileSystemChange]], None]):
        """Add callback for file system changes"""
        self.change_buffer.add_callback(callback)
    
    def start_watching(self, path: str, recursive: bool = True) -> bool:
        """
        Start watching a path
        
        Args:
            path: Directory path to watch
            recursive: Watch subdirectories
            
        Returns:
            True if successfully started watching
        """
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            return False
        
        if not os.path.isdir(path):
            logger.error(f"Path is not a directory: {path}")
            return False
        
        try:
            if not self._running:
                self.observer = Observer()
                self.observer.start()
                self._running = True
                logger.info("File system observer started")
            
            # Add watch
            self.observer.schedule(self, path, recursive=recursive)
            self._watched_paths.add(path)
            
            logger.info(f"Started watching: {path} (recursive: {recursive})")
            return True
            
        except Exception as e:
            logger.error(f"Error starting watch for {path}: {e}")
            return False
    
    def stop_watching(self, path: str):
        """Stop watching a specific path"""
        if path in self._watched_paths:
            try:
                # Note: watchdog doesn't provide direct way to remove specific path
                # We would need to restart observer with remaining paths
                self._watched_paths.discard(path)
                logger.info(f"Stopped watching: {path}")
            except Exception as e:
                logger.error(f"Error stopping watch for {path}: {e}")
    
    def stop_all(self):
        """Stop all watching"""
        if self.observer and self._running:
            try:
                self.observer.stop()
                self.observer.join(timeout=5.0)
                self._running = False
                self._watched_paths.clear()
                self.change_buffer.clear()
                logger.info("File system watching stopped")
            except Exception as e:
                logger.error(f"Error stopping file system watcher: {e}")
    
    def on_created(self, event: FileSystemEvent):
        """Handle file/directory creation"""
        if self._should_process_event(event):
            change = FileSystemChange(
                path=event.src_path,
                event_type='created',
                is_directory=event.is_directory
            )
            self.change_buffer.add_change(change)
            logger.debug(f"File created: {event.src_path}")
    
    def on_deleted(self, event: FileSystemEvent):
        """Handle file/directory deletion"""
        if self._should_process_event(event):
            change = FileSystemChange(
                path=event.src_path,
                event_type='deleted',
                is_directory=event.is_directory
            )
            self.change_buffer.add_change(change)
            logger.debug(f"File deleted: {event.src_path}")
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file/directory modification"""
        if self._should_process_event(event):
            change = FileSystemChange(
                path=event.src_path,
                event_type='modified',
                is_directory=event.is_directory
            )
            self.change_buffer.add_change(change)
            logger.debug(f"File modified: {event.src_path}")
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file/directory move/rename"""
        if self._should_process_event(event):
            change = FileSystemChange(
                path=event.dest_path,
                event_type='moved',
                is_directory=event.is_directory,
                old_path=event.src_path
            )
            self.change_buffer.add_change(change)
            logger.debug(f"File moved: {event.src_path} -> {event.dest_path}")
    
    def _should_process_event(self, event: FileSystemEvent) -> bool:
        """Check if event should be processed"""
        if event.is_directory and not self.watch_directories:
            return False
        
        if not event.is_directory and not self.watch_files:
            return False
        
        # Filter out temporary files và system files
        filename = os.path.basename(event.src_path)
        if filename.startswith('.') or filename.endswith('.tmp') or filename.endswith('.temp'):
            return False
        
        return True
    
    def get_watched_paths(self) -> Set[str]:
        """Get currently watched paths"""
        return self._watched_paths.copy()
    
    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._running


class PollingFileSystemWatcher:
    """
    Fallback file system watcher using polling
    (for when watchdog is not available)
    """
    
    def __init__(
        self,
        polling_interval: float = 2.0,
        debounce_delay: float = 0.5
    ):
        self.polling_interval = polling_interval
        self.debounce_delay = debounce_delay
        
        self.change_buffer = ChangeBuffer(debounce_delay)
        self._watched_paths: Dict[str, Dict[str, float]] = {}  # path -> {file: mtime}
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        
        logger.info(f"PollingFileSystemWatcher initialized (interval: {polling_interval}s)")
    
    def add_callback(self, callback: Callable[[List[FileSystemChange]], None]):
        """Add callback for file system changes"""
        self.change_buffer.add_callback(callback)
    
    def start_watching(self, path: str, recursive: bool = True) -> bool:
        """Start watching a path using polling"""
        if not os.path.exists(path):
            logger.error(f"Path does not exist: {path}")
            return False
        
        if not os.path.isdir(path):
            logger.error(f"Path is not a directory: {path}")
            return False
        
        # Start polling thread if not running
        if not self._running:
            self._start_polling()
        
        # Scan initial state
        self._watched_paths[path] = self._scan_directory(path, recursive)
        
        logger.info(f"Started polling: {path} (recursive: {recursive})")
        return True
    
    def stop_watching(self, path: str):
        """Stop watching a specific path"""
        if path in self._watched_paths:
            del self._watched_paths[path]
            logger.info(f"Stopped watching: {path}")
    
    def stop_all(self):
        """Stop all watching"""
        if self._running:
            self._stop_event.set()
            if self._polling_thread and self._polling_thread.is_alive():
                self._polling_thread.join(timeout=5.0)
            
            self._running = False
            self._watched_paths.clear()
            self.change_buffer.clear()
            logger.info("Polling file system watcher stopped")
    
    def _start_polling(self):
        """Start the polling thread"""
        self._running = True
        self._stop_event.clear()
        
        def polling_loop():
            logger.info("File system polling started")
            
            while not self._stop_event.is_set():
                try:
                    self._poll_changes()
                    
                    # Wait for next poll
                    if self._stop_event.wait(self.polling_interval):
                        break  # Stop event was set
                        
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    time.sleep(self.polling_interval)
            
            logger.info("File system polling stopped")
        
        self._polling_thread = threading.Thread(target=polling_loop, daemon=True)
        self._polling_thread.start()
    
    def _poll_changes(self):
        """Poll for changes in watched directories"""
        for watch_path in list(self._watched_paths.keys()):
            try:
                old_state = self._watched_paths[watch_path]
                new_state = self._scan_directory(watch_path, recursive=True)
                
                # Compare states và detect changes
                changes = self._detect_changes(old_state, new_state, watch_path)
                
                # Update state
                self._watched_paths[watch_path] = new_state
                
                # Report changes
                for change in changes:
                    self.change_buffer.add_change(change)
                    
            except Exception as e:
                logger.error(f"Error polling {watch_path}: {e}")
    
    def _scan_directory(self, path: str, recursive: bool) -> Dict[str, float]:
        """Scan directory và return file -> mtime mapping"""
        file_times = {}
        
        try:
            if recursive:
                for root, dirs, files in os.walk(path):
                    for filename in files:
                        file_path = os.path.join(root, filename)
                        try:
                            mtime = os.path.getmtime(file_path)
                            file_times[file_path] = mtime
                        except (OSError, PermissionError):
                            continue
            else:
                for item in os.listdir(path):
                    item_path = os.path.join(path, item)
                    if os.path.isfile(item_path):
                        try:
                            mtime = os.path.getmtime(item_path)
                            file_times[item_path] = mtime
                        except (OSError, PermissionError):
                            continue
        except Exception as e:
            logger.error(f"Error scanning directory {path}: {e}")
        
        return file_times
    
    def _detect_changes(
        self,
        old_state: Dict[str, float],
        new_state: Dict[str, float],
        watch_path: str
    ) -> List[FileSystemChange]:
        """Detect changes between old và new states"""
        changes = []
        
        # Find created files
        for file_path in new_state:
            if file_path not in old_state:
                changes.append(FileSystemChange(
                    path=file_path,
                    event_type='created',
                    is_directory=False
                ))
        
        # Find deleted files  
        for file_path in old_state:
            if file_path not in new_state:
                changes.append(FileSystemChange(
                    path=file_path,
                    event_type='deleted',
                    is_directory=False
                ))
        
        # Find modified files
        for file_path in new_state:
            if (file_path in old_state and 
                abs(new_state[file_path] - old_state[file_path]) > 1.0):  # 1 second tolerance
                changes.append(FileSystemChange(
                    path=file_path,
                    event_type='modified',
                    is_directory=False
                ))
        
        return changes
    
    def get_watched_paths(self) -> Set[str]:
        """Get currently watched paths"""
        return set(self._watched_paths.keys())
    
    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._running


class FileSystemWatcher:
    """
    Unified file system watcher interface
    """
    
    def __init__(
        self,
        debounce_delay: float = 0.5,
        prefer_watchdog: bool = True,
        polling_interval: float = 2.0
    ):
        self.debounce_delay = debounce_delay
        self.prefer_watchdog = prefer_watchdog
        self.polling_interval = polling_interval
        
        # Choose implementation
        if WATCHDOG_AVAILABLE and prefer_watchdog:
            self._impl = WatchdogFileSystemWatcher(debounce_delay)
            self._implementation = "watchdog"
            logger.info("Using watchdog file system watcher")
        else:
            self._impl = PollingFileSystemWatcher(polling_interval, debounce_delay)
            self._implementation = "polling"
            logger.info("Using polling file system watcher")
    
    def add_callback(self, callback: Callable[[List[FileSystemChange]], None]):
        """Add callback for file system changes"""
        self._impl.add_callback(callback)
    
    def start_watching(self, path: str, recursive: bool = True) -> bool:
        """Start watching a path"""
        return self._impl.start_watching(path, recursive)
    
    def stop_watching(self, path: str):
        """Stop watching a specific path"""
        self._impl.stop_watching(path)
    
    def stop_all(self):
        """Stop all watching"""
        self._impl.stop_all()
    
    def get_watched_paths(self) -> Set[str]:
        """Get currently watched paths"""
        return self._impl.get_watched_paths()
    
    def is_running(self) -> bool:
        """Check if watcher is running"""
        return self._impl.is_running()
    
    def get_implementation(self) -> str:
        """Get current implementation being used"""
        return self._implementation
    
    def flush_pending_changes(self):
        """Flush any pending debounced changes immediately"""
        self._impl.change_buffer.flush_all()


# Global instance
_file_system_watcher: Optional[FileSystemWatcher] = None


def get_file_system_watcher() -> FileSystemWatcher:
    """Get global FileSystemWatcher instance"""
    global _file_system_watcher
    if _file_system_watcher is None:
        _file_system_watcher = FileSystemWatcher()
    return _file_system_watcher


def set_file_system_watcher(watcher: FileSystemWatcher):
    """Set global FileSystemWatcher instance"""
    global _file_system_watcher
    if _file_system_watcher is not None:
        _file_system_watcher.stop_all()
    _file_system_watcher = watcher