"""Version information for File Rename Tool"""

__version__ = "1.0.0"
__title__ = "File Rename Tool"
__description__ = "Vietnamese file rename tool với desktop GUI"
__author__ = "File Rename Tool Team"
__copyright__ = "2025 File Rename Tool Team"

# Build metadata - populated during build process
BUILD_DATE = "2025-08-31T13:58:35.607219"
BUILD_COMMIT = "12ca2fb"
BUILD_VERSION = __version__

# Application metadata for PyInstaller
APP_NAME = "FileRenameTool"
APP_VERSION = __version__
APP_DESCRIPTION = __description__
APP_AUTHOR = __author__
APP_COPYRIGHT = f"Copyright © 2025 {__author__}"

def get_version_info():
    """Get formatted version information"""
    return {
        'version': __version__,
        'title': __title__,
        'description': __description__,
        'author': __author__,
        'copyright': __copyright__,
        'build_date': BUILD_DATE,
        'build_commit': BUILD_COMMIT
    }