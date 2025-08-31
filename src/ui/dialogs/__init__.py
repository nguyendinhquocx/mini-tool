"""
UI Dialogs Package

Contains dialog components for file operations:
- ProgressDialog: Progress feedback for batch operations
- ResultDialog: Operation results and summaries  
- ConfirmDialog: User confirmations
"""

from .progress_dialog import ProgressDialog, ProgressInfo
from .result_dialog import ResultDialog, OperationResult

__all__ = ['ProgressDialog', 'ProgressInfo', 'ResultDialog', 'OperationResult']