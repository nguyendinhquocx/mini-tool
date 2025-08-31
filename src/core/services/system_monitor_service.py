"""
System Monitoring Service

Monitors disk space, network connectivity, and system resources
to provide proactive warnings and graceful error handling.
"""

import os
import shutil
import time
import threading
from pathlib import Path, PurePath
from typing import Dict, Optional, List, Callable, Any, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import subprocess
import sys

# Configure logging
logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """Network connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    UNKNOWN = "unknown"


class DriveType(Enum):
    """Types of drives"""
    LOCAL = "local"
    NETWORK = "network"
    REMOVABLE = "removable"
    UNKNOWN = "unknown"


@dataclass
class DiskSpaceInfo:
    """Disk space information"""
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    used_percentage: float
    drive_type: DriveType
    last_checked: datetime = field(default_factory=datetime.now)
    
    @property
    def total_mb(self) -> float:
        return self.total_bytes / (1024 * 1024)
    
    @property
    def used_mb(self) -> float:
        return self.used_bytes / (1024 * 1024)
    
    @property
    def free_mb(self) -> float:
        return self.free_bytes / (1024 * 1024)
    
    @property
    def is_low_space(self) -> bool:
        """Check if disk space is critically low"""
        return self.free_bytes < 100 * 1024 * 1024 or self.used_percentage > 95
    
    @property
    def is_warning_space(self) -> bool:
        """Check if disk space is in warning range"""
        return self.free_bytes < 500 * 1024 * 1024 or self.used_percentage > 85


@dataclass
class NetworkDriveInfo:
    """Network drive information"""
    local_path: str
    remote_path: str
    status: ConnectionStatus
    last_checked: datetime = field(default_factory=datetime.now)
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None


class DiskSpaceMonitor:
    """
    Monitor disk space across different drives and provide warnings
    """
    
    def __init__(self):
        self._disk_info_cache: Dict[str, DiskSpaceInfo] = {}
        self._cache_duration = timedelta(minutes=1)  # Cache for 1 minute
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[DiskSpaceInfo], None]] = []
    
    def get_disk_space(self, path: str) -> Optional[DiskSpaceInfo]:
        """
        Get disk space information for a given path
        
        Args:
            path: Path to check (file or directory)
            
        Returns:
            DiskSpaceInfo object or None if path is invalid
        """
        try:
            # Normalize path to get the root drive
            abs_path = os.path.abspath(path)
            drive_path = os.path.splitdrive(abs_path)[0] + os.sep
            
            # Check cache first
            cached_info = self._disk_info_cache.get(drive_path)
            if (cached_info and 
                datetime.now() - cached_info.last_checked < self._cache_duration):
                return cached_info
            
            # Get disk usage
            total, used, free = shutil.disk_usage(abs_path)
            used_percentage = (used / total) * 100 if total > 0 else 0
            
            # Determine drive type
            drive_type = self._get_drive_type(drive_path)
            
            disk_info = DiskSpaceInfo(
                path=drive_path,
                total_bytes=total,
                used_bytes=used,
                free_bytes=free,
                used_percentage=used_percentage,
                drive_type=drive_type
            )
            
            # Update cache
            self._disk_info_cache[drive_path] = disk_info
            
            return disk_info
            
        except (OSError, ValueError) as e:
            logger.error(f"Failed to get disk space for {path}: {e}")
            return None
    
    def estimate_space_required(self, file_operations: List[Dict[str, Any]]) -> int:
        """
        Estimate disk space required for file operations
        
        Args:
            file_operations: List of file operation dictionaries with 'source' and 'target' paths
            
        Returns:
            Estimated bytes required
        """
        total_required = 0
        
        for operation in file_operations:
            source_path = operation.get('source', '')
            target_path = operation.get('target', '')
            
            try:
                if os.path.exists(source_path):
                    file_size = os.path.getsize(source_path)
                    
                    # If target is on a different drive, we need full file size
                    source_drive = os.path.splitdrive(os.path.abspath(source_path))[0]
                    target_drive = os.path.splitdrive(os.path.abspath(target_path))[0]
                    
                    if source_drive.lower() != target_drive.lower():
                        total_required += file_size
                    # For same-drive renames, minimal additional space needed
                    else:
                        total_required += max(1024, file_size * 0.01)  # 1% overhead minimum 1KB
                        
            except (OSError, ValueError) as e:
                logger.warning(f"Could not get size for {source_path}: {e}")
                # Assume 1MB per file if we can't determine size
                total_required += 1024 * 1024
        
        return int(total_required)
    
    def check_sufficient_space(self, path: str, required_bytes: int) -> tuple[bool, Optional[DiskSpaceInfo]]:
        """
        Check if there's sufficient disk space for an operation
        
        Args:
            path: Path where operation will occur
            required_bytes: Bytes required for operation
            
        Returns:
            Tuple of (sufficient_space, disk_info)
        """
        disk_info = self.get_disk_space(path)
        if not disk_info:
            return False, None
        
        # Add 10% buffer to required space
        buffer_space = max(100 * 1024 * 1024, required_bytes * 0.1)  # 100MB or 10% buffer
        total_needed = required_bytes + buffer_space
        
        return disk_info.free_bytes >= total_needed, disk_info
    
    def start_monitoring(self, paths: List[str], callback: Callable[[DiskSpaceInfo], None]):
        """
        Start continuous monitoring of disk space for specified paths
        
        Args:
            paths: List of paths to monitor
            callback: Function to call when disk space changes significantly
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._callbacks.append(callback)
        
        def monitor_loop():
            previous_info = {}
            
            while self._monitoring:
                for path in paths:
                    try:
                        current_info = self.get_disk_space(path)
                        if not current_info:
                            continue
                        
                        drive_path = current_info.path
                        prev_info = previous_info.get(drive_path)
                        
                        # Check for significant changes
                        if (not prev_info or 
                            abs(current_info.used_percentage - prev_info.used_percentage) > 1.0 or
                            current_info.is_low_space != prev_info.is_low_space):
                            
                            for cb in self._callbacks:
                                try:
                                    cb(current_info)
                                except Exception as e:
                                    logger.error(f"Monitoring callback failed: {e}")
                            
                            previous_info[drive_path] = current_info
                    
                    except Exception as e:
                        logger.error(f"Error monitoring {path}: {e}")
                
                time.sleep(30)  # Check every 30 seconds
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop disk space monitoring"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
    
    def _get_drive_type(self, drive_path: str) -> DriveType:
        """Determine the type of drive"""
        try:
            if sys.platform.startswith('win'):
                # On Windows, check if it's a network drive
                if self._is_network_path_windows(drive_path):
                    return DriveType.NETWORK
                
                # Check if it's removable
                import ctypes
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                if drive_type == 2:  # DRIVE_REMOVABLE
                    return DriveType.REMOVABLE
                elif drive_type == 4:  # DRIVE_REMOTE
                    return DriveType.NETWORK
                else:
                    return DriveType.LOCAL
            else:
                # On Unix-like systems
                if os.path.ismount(drive_path):
                    # Check mount type from /proc/mounts if available
                    try:
                        with open('/proc/mounts', 'r') as f:
                            for line in f:
                                parts = line.split()
                                if len(parts) >= 3 and parts[1] == drive_path:
                                    fs_type = parts[2]
                                    if fs_type in ['nfs', 'cifs', 'smbfs']:
                                        return DriveType.NETWORK
                                    return DriveType.LOCAL
                    except (OSError, IOError):
                        pass
                
                return DriveType.LOCAL
                
        except Exception as e:
            logger.warning(f"Could not determine drive type for {drive_path}: {e}")
            return DriveType.UNKNOWN
    
    def _is_network_path_windows(self, path: str) -> bool:
        """Check if path is a network path on Windows"""
        return path.startswith('\\\\') or (len(path) >= 2 and path[1] == ':' and 
                                          ord(path[0].upper()) >= ord('Z'))


class NetworkDriveMonitor:
    """
    Monitor network drive connectivity and provide connection status
    """
    
    def __init__(self):
        self._network_drives: Dict[str, NetworkDriveInfo] = {}
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[NetworkDriveInfo], None]] = []
    
    def is_network_path(self, path: str) -> bool:
        """
        Check if a path points to a network location
        
        Args:
            path: Path to check
            
        Returns:
            True if path is a network location
        """
        try:
            abs_path = os.path.abspath(path)
            
            if sys.platform.startswith('win'):
                # UNC paths
                if abs_path.startswith('\\\\'):
                    return True
                
                # Mapped network drives (check with WMI or net use)
                drive_letter = abs_path[:2]
                return self._is_mapped_network_drive_windows(drive_letter)
            else:
                # Unix-like systems - check if it's a network mount
                return self._is_network_mount_unix(abs_path)
                
        except Exception as e:
            logger.warning(f"Could not determine if {path} is network path: {e}")
            return False
    
    def check_connectivity(self, network_path: str) -> NetworkDriveInfo:
        """
        Check connectivity to a network path
        
        Args:
            network_path: Path to network location
            
        Returns:
            NetworkDriveInfo with connection status
        """
        start_time = time.time()
        
        try:
            # Try to access the path
            if os.path.exists(network_path):
                # Try to list directory or get file stats
                if os.path.isdir(network_path):
                    os.listdir(network_path)
                else:
                    os.stat(network_path)
                
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                return NetworkDriveInfo(
                    local_path=network_path,
                    remote_path=self._get_remote_path(network_path),
                    status=ConnectionStatus.CONNECTED,
                    response_time_ms=response_time
                )
            else:
                return NetworkDriveInfo(
                    local_path=network_path,
                    remote_path=self._get_remote_path(network_path),
                    status=ConnectionStatus.DISCONNECTED,
                    error_message="Path not accessible"
                )
                
        except (OSError, IOError) as e:
            return NetworkDriveInfo(
                local_path=network_path,
                remote_path=self._get_remote_path(network_path),
                status=ConnectionStatus.DISCONNECTED,
                error_message=str(e),
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    def reconnect_network_drive(self, drive_info: NetworkDriveInfo) -> bool:
        """
        Attempt to reconnect a network drive
        
        Args:
            drive_info: Network drive information
            
        Returns:
            True if reconnection successful
        """
        try:
            if sys.platform.startswith('win'):
                # On Windows, try to reconnect mapped drive
                if len(drive_info.local_path) >= 2 and drive_info.local_path[1] == ':':
                    drive_letter = drive_info.local_path[:2]
                    if drive_info.remote_path:
                        # Use net use command to reconnect
                        result = subprocess.run([
                            'net', 'use', drive_letter, drive_info.remote_path, '/persistent:no'
                        ], capture_output=True, text=True, timeout=30)
                        return result.returncode == 0
            
            # For UNC paths, just check if accessible again
            return os.path.exists(drive_info.local_path)
            
        except Exception as e:
            logger.error(f"Failed to reconnect network drive {drive_info.local_path}: {e}")
            return False
    
    def start_monitoring(self, network_paths: List[str], 
                        callback: Callable[[NetworkDriveInfo], None]):
        """
        Start monitoring network drive connectivity
        
        Args:
            network_paths: List of network paths to monitor
            callback: Function to call when connection status changes
        """
        if self._monitoring:
            return
        
        self._monitoring = True
        self._callbacks.append(callback)
        
        def monitor_loop():
            while self._monitoring:
                for path in network_paths:
                    try:
                        current_info = self.check_connectivity(path)
                        previous_info = self._network_drives.get(path)
                        
                        # Check for status changes
                        if (not previous_info or 
                            current_info.status != previous_info.status):
                            
                            for cb in self._callbacks:
                                try:
                                    cb(current_info)
                                except Exception as e:
                                    logger.error(f"Network monitoring callback failed: {e}")
                        
                        self._network_drives[path] = current_info
                    
                    except Exception as e:
                        logger.error(f"Error monitoring network path {path}: {e}")
                
                time.sleep(15)  # Check every 15 seconds
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop network drive monitoring"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5)
    
    def _is_mapped_network_drive_windows(self, drive_letter: str) -> bool:
        """Check if drive letter is a mapped network drive on Windows"""
        try:
            result = subprocess.run(['net', 'use', drive_letter], 
                                  capture_output=True, text=True, timeout=10)
            return 'Remote' in result.stdout
        except Exception:
            return False
    
    def _is_network_mount_unix(self, path: str) -> bool:
        """Check if path is on a network mount on Unix-like systems"""
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 3:
                        mount_point = parts[1]
                        fs_type = parts[2]
                        if (path.startswith(mount_point) and 
                            fs_type in ['nfs', 'cifs', 'smbfs', 'nfs4']):
                            return True
            return False
        except (OSError, IOError):
            return False
    
    def _get_remote_path(self, local_path: str) -> str:
        """Get the remote path for a local network path"""
        try:
            if sys.platform.startswith('win'):
                if local_path.startswith('\\\\'):
                    return local_path  # UNC path is already the remote path
                
                # For mapped drives, query the remote path
                drive_letter = local_path[:2]
                result = subprocess.run(['net', 'use', drive_letter], 
                                      capture_output=True, text=True, timeout=10)
                for line in result.stdout.split('\n'):
                    if 'Remote' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[-1]
            
            return local_path
        except Exception:
            return local_path


class SystemMonitorService:
    """
    Combined system monitoring service for disk space and network connectivity
    """
    
    def __init__(self):
        self.disk_monitor = DiskSpaceMonitor()
        self.network_monitor = NetworkDriveMonitor()
        self._warning_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
    
    def add_warning_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Add callback for system warnings"""
        self._warning_callbacks.append(callback)
    
    def check_system_readiness(self, operation_paths: List[str], 
                              required_space: int = 0) -> Dict[str, Any]:
        """
        Check if system is ready for file operations
        
        Args:
            operation_paths: List of paths that will be used in operations
            required_space: Estimated space required in bytes
            
        Returns:
            Dictionary with readiness status and issues
        """
        readiness = {
            'ready': True,
            'warnings': [],
            'errors': [],
            'disk_info': {},
            'network_info': {}
        }
        
        # Check disk space for each unique drive
        drives_checked = set()
        for path in operation_paths:
            try:
                drive_path = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
                if drive_path not in drives_checked:
                    drives_checked.add(drive_path)
                    
                    disk_info = self.disk_monitor.get_disk_space(path)
                    if disk_info:
                        readiness['disk_info'][drive_path] = disk_info
                        
                        # Check if space is sufficient
                        if required_space > 0:
                            sufficient, _ = self.disk_monitor.check_sufficient_space(path, required_space)
                            if not sufficient:
                                readiness['errors'].append(
                                    f"Insufficient disk space on {drive_path}. "
                                    f"Required: {required_space // (1024*1024)}MB, "
                                    f"Available: {disk_info.free_mb:.0f}MB"
                                )
                                readiness['ready'] = False
                        
                        # Check for low space warnings
                        if disk_info.is_low_space:
                            readiness['warnings'].append(
                                f"Critically low disk space on {drive_path} ({disk_info.used_percentage:.1f}% used)"
                            )
                        elif disk_info.is_warning_space:
                            readiness['warnings'].append(
                                f"Low disk space on {drive_path} ({disk_info.used_percentage:.1f}% used)"
                            )
            
            except Exception as e:
                readiness['warnings'].append(f"Could not check disk space for {path}: {e}")
        
        # Check network connectivity
        for path in operation_paths:
            if self.network_monitor.is_network_path(path):
                network_info = self.network_monitor.check_connectivity(path)
                readiness['network_info'][path] = network_info
                
                if network_info.status != ConnectionStatus.CONNECTED:
                    readiness['errors'].append(
                        f"Network path {path} is not accessible: {network_info.error_message}"
                    )
                    readiness['ready'] = False
                elif network_info.response_time_ms and network_info.response_time_ms > 5000:
                    readiness['warnings'].append(
                        f"Slow network response for {path} ({network_info.response_time_ms:.0f}ms)"
                    )
        
        return readiness
    
    def start_monitoring(self, operation_paths: List[str]):
        """Start monitoring system resources for given paths"""
        # Separate local and network paths
        local_paths = []
        network_paths = []
        
        for path in operation_paths:
            if self.network_monitor.is_network_path(path):
                network_paths.append(path)
            else:
                local_paths.append(path)
        
        # Start disk monitoring
        if local_paths:
            self.disk_monitor.start_monitoring(
                local_paths, 
                self._handle_disk_warning
            )
        
        # Start network monitoring
        if network_paths:
            self.network_monitor.start_monitoring(
                network_paths, 
                self._handle_network_warning
            )
    
    def stop_monitoring(self):
        """Stop all system monitoring"""
        self.disk_monitor.stop_monitoring()
        self.network_monitor.stop_monitoring()
    
    def _handle_disk_warning(self, disk_info: DiskSpaceInfo):
        """Handle disk space warnings"""
        if disk_info.is_low_space:
            self._notify_warning("disk_space_critical", {
                'drive': disk_info.path,
                'free_mb': disk_info.free_mb,
                'used_percentage': disk_info.used_percentage
            })
        elif disk_info.is_warning_space:
            self._notify_warning("disk_space_low", {
                'drive': disk_info.path,
                'free_mb': disk_info.free_mb,
                'used_percentage': disk_info.used_percentage
            })
    
    def _handle_network_warning(self, network_info: NetworkDriveInfo):
        """Handle network connectivity warnings"""
        if network_info.status == ConnectionStatus.DISCONNECTED:
            self._notify_warning("network_disconnected", {
                'path': network_info.local_path,
                'error': network_info.error_message
            })
        elif network_info.status == ConnectionStatus.CONNECTED:
            self._notify_warning("network_reconnected", {
                'path': network_info.local_path,
                'response_time_ms': network_info.response_time_ms
            })
    
    def _notify_warning(self, warning_type: str, details: Dict[str, Any]):
        """Notify registered callbacks about system warnings"""
        for callback in self._warning_callbacks:
            try:
                callback(warning_type, details)
            except Exception as e:
                logger.error(f"Warning callback failed: {e}")


# Global system monitor instance
_global_system_monitor = SystemMonitorService()


def get_system_monitor() -> SystemMonitorService:
    """Get the global system monitor instance"""
    return _global_system_monitor