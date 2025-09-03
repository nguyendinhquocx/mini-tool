"""
Version Management System for File Rename Tool

Enhanced version management with comprehensive application metadata.
"""

import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


# Basic version information (legacy compatibility)
__version__ = "1.0.0"
__title__ = "Mini Tool File"
__description__ = "Vietnamese File Normalization Utility"
__author__ = "File Rename Tool Team"
__copyright__ = "2025 File Rename Tool Team"

# Build metadata - populated during build process
BUILD_DATE = "2025-09-04T01:11:53.970781"
BUILD_COMMIT = "6e7fc1c"
BUILD_VERSION = __version__

# Application metadata for PyInstaller
APP_NAME = "MiniToolFile"
APP_VERSION = __version__
APP_DESCRIPTION = __description__
APP_AUTHOR = __author__
APP_COPYRIGHT = f"Copyright © 2025 {__author__}"


@dataclass
class VersionInfo:
    """Application version information dataclass"""
    major: int
    minor: int
    patch: int
    build: str = ""
    release_date: str = ""
    
    def __str__(self) -> str:
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version_str += f".{self.build}"
        return version_str
    
    @property
    def semantic_version(self) -> str:
        """Return semantic version string (MAJOR.MINOR.PATCH)"""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @property
    def display_version(self) -> str:
        """Return user-friendly version string"""
        if self.build and self.build != "release":
            return f"{self.semantic_version} ({self.build})"
        return self.semantic_version
    
    @property
    def file_version(self) -> tuple:
        """Return version as tuple for Windows file info"""
        return (self.major, self.minor, self.patch, 0)


class VersionManager:
    """Manages application version information"""
    
    def __init__(self, version_file: Optional[Path] = None):
        if version_file is None:
            version_file = Path(__file__).parent / "version.json"
        
        self.version_file = version_file
        self._ensure_version_file()
    
    def get_current_version(self) -> VersionInfo:
        """Load current version information from file"""
        try:
            with open(self.version_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return VersionInfo(**data)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            # Return version from constants if file doesn't exist
            parts = __version__.split('.')
            return VersionInfo(
                major=int(parts[0]),
                minor=int(parts[1]),
                patch=int(parts[2]),
                build="development",
                release_date=BUILD_DATE
            )
    
    def save_version(self, version_info: VersionInfo) -> None:
        """Save version information to file"""
        self.version_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.version_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(version_info), f, indent=2, ensure_ascii=False)
    
    def _ensure_version_file(self) -> None:
        """Ensure version file exists with default values"""
        if not self.version_file.exists():
            parts = __version__.split('.')
            default_version = VersionInfo(
                major=int(parts[0]),
                minor=int(parts[1]),
                patch=int(parts[2]),
                build="development",
                release_date=BUILD_DATE
            )
            self.save_version(default_version)


# Global version manager instance
_version_manager: Optional[VersionManager] = None

def get_version_manager() -> VersionManager:
    """Get global version manager instance"""
    global _version_manager
    if _version_manager is None:
        _version_manager = VersionManager()
    return _version_manager

def get_current_version() -> VersionInfo:
    """Get current application version"""
    return get_version_manager().get_current_version()

def get_version_string() -> str:
    """Get current version as string"""
    return str(get_current_version())

def get_display_version() -> str:
    """Get user-friendly version string"""
    return get_current_version().display_version

def get_version_info():
    """Get formatted version information (legacy compatibility)"""
    version = get_current_version()
    return {
        'version': version.semantic_version,
        'title': __title__,
        'description': __description__,
        'author': __author__,
        'copyright': __copyright__,
        'build_date': version.release_date,
        'build_commit': BUILD_COMMIT,
        'display_version': version.display_version
    }