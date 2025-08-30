# Testing Strategy

## Testing Pyramid
```
        E2E Tests (UI Automation)
       /                        \
  Integration Tests (File Ops + UI)
 /                                    \
Unit Tests (Services + Utils)  Component Tests (UI)
```

## Test Organization

### Unit Tests
```
tests/unit/
├── test_file_service.py        # File operations business logic
├── test_normalize_service.py   # Vietnamese text processing
├── test_config_service.py      # Configuration management
├── test_history_service.py     # Operation history tracking
├── test_repositories.py        # Data access layer
└── test_utils.py              # Utility functions
```

### Integration Tests
```
tests/integration/
├── test_file_operations_flow.py    # End-to-end file operations
├── test_ui_file_interaction.py     # UI + file system integration
├── test_database_operations.py     # Database + service integration
└── test_error_recovery_flow.py     # Error handling workflows
```

### E2E Tests
```
tests/e2e/
├── test_complete_rename_workflow.py   # Full user journey testing
├── test_settings_management.py        # Configuration UI flows
├── test_error_scenarios.py            # Error handling user experience
└── test_undo_operations.py           # Undo functionality workflows
```

## Test Examples

### Frontend Component Test
```python
import pytest
from tkinter import Tk
from unittest.mock import Mock, patch
from src.ui.components.file_preview import FilePreviewComponent
from src.core.models.file_info import FileInfo, RenamePreview

class TestFilePreviewComponent:
    @pytest.fixture
    def root_window(self):
        root = Tk()
        yield root
        root.destroy()
    
    @pytest.fixture
    def mock_state_callback(self):
        return Mock()
    
    def test_file_preview_display(self, root_window, mock_state_callback):
        # Arrange
        component = FilePreviewComponent(root_window, mock_state_callback)
        preview_data = [
            RenamePreview(
                original="Nguễn ĐINH qucs# File.txt",
                processed="nguen dinh qucs file.txt",
                status="ready"
            )
        ]
        
        # Act
        component.update_data(preview_data)
        
        # Assert
        tree_widget = component.preview_tree
        children = tree_widget.get_children()
        assert len(children) == 1
        
        item_values = tree_widget.item(children[0])['values']
        assert item_values[0] == "Nguễn ĐINH qucs# File.txt"
        assert item_values[1] == "nguen dinh qucs file.txt"
        assert item_values[2] == "ready"
    
    def test_conflict_highlighting(self, root_window, mock_state_callback):
        # Test duplicate name conflict detection
        component = FilePreviewComponent(root_window, mock_state_callback)
        preview_data = [
            RenamePreview(
                original="File (1).txt",
                processed="file.txt", 
                status="conflict"
            ),
            RenamePreview(
                original="File (2).txt",
                processed="file.txt",
                status="conflict"
            )
        ]
        
        component.update_data(preview_data)
        
        # Verify conflict highlighting
        tree_widget = component.preview_tree
        for child in tree_widget.get_children():
            tags = tree_widget.item(child)['tags']
            assert 'conflict' in tags
```

### Backend API Test
```python
import pytest
import tempfile
import os
from pathlib import Path
from src.core.services.file_service import FileService
from src.core.models.file_info import FileInfo
from src.core.models.operation import NormalizationRules

class TestFileService:
    @pytest.fixture
    async def file_service(self):
        return FileService()
    
    @pytest.fixture
    def temp_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files với Vietnamese names
            test_files = [
                "Nguễn Văn A.txt",
                "Tài liệu (QUAN TRỌNG).docx", 
                "File#test*special.pdf"
            ]
            
            for filename in test_files:
                Path(temp_dir) / filename).touch()
            
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_scan_directory(self, file_service, temp_directory):
        # Act
        files = await file_service.scan_directory(temp_directory)
        
        # Assert
        assert len(files) == 3
        assert all(isinstance(f, FileInfo) for f in files)
        
        filenames = [f.name for f in files]
        assert "Nguễn Văn A.txt" in filenames
        assert "Tài liệu (QUAN TRỌNG).docx" in filenames
        assert "File#test*special.pdf" in filenames
    
    @pytest.mark.asyncio
    async def test_vietnamese_normalization_preview(
        self, 
        file_service, 
        temp_directory
    ):
        # Arrange
        files = await file_service.scan_directory(temp_directory)
        rules = NormalizationRules(
            remove_diacritics=True,
            lowercase=True,
            clean_special_chars=True
        )
        
        # Act
        previews = await file_service.generate_preview(files, rules)
        
        # Assert
        assert len(previews) == 3
        
        # Check specific transformations
        preview_map = {p.original: p.processed for p in previews}
        assert preview_map["Nguễn Văn A.txt"] == "nguyen van a.txt"
        assert preview_map["Tài liệu (QUAN TRỌNG).docx"] == "tai lieu quan trong.docx"
        assert preview_map["File#test*special.pdf"] == "file test special.pdf"
    
    @pytest.mark.asyncio
    async def test_batch_rename_execution(
        self,
        file_service,
        temp_directory
    ):
        # Arrange
        files = await file_service.scan_directory(temp_directory)
        rules = NormalizationRules(remove_diacritics=True, lowercase=True)
        previews = await file_service.generate_preview(files, rules)
        
        progress_updates = []
        def progress_callback(percent: float, current_file: str):
            progress_updates.append((percent, current_file))
        
        # Act
        result = await file_service.execute_batch_rename(
            previews,
            progress_callback
        )
        
        # Assert
        assert result.success_count == 3
        assert result.error_count == 0
        assert len(progress_updates) >= 3  # At least one update per file
        
        # Verify files were actually renamed
        actual_files = os.listdir(temp_directory)
        assert "nguyen van a.txt" in actual_files
        assert "tai lieu quan trong.docx" in actual_files
```

### E2E Test
```python
import pytest
import tempfile
import os
from pathlib import Path
import tkinter as tk
from unittest.mock import patch
from src.main import FileRenameApplication

class TestCompleteRenameWorkflow:
    @pytest.fixture
    def temp_directory_with_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create realistic test scenario
            test_files = [
                "Báo cáo tháng 12 (FINAL).docx",
                "Hình ảnh đẹp nhất năm 2024!.jpg",
                "Tài liệu_quan#trọng***.pdf"
            ]
            
            for filename in test_files:
                (Path(temp_dir) / filename).touch()
            
            yield temp_dir
    
    @pytest.mark.asyncio
    async def test_complete_rename_workflow(
        self, 
        temp_directory_with_files
    ):
        """Test complete user workflow from folder selection to rename completion"""
        
        # Initialize application
        app = FileRenameApplication()
        await app.initialize()
        
        try:
            # Step 1: Select folder
            await app.select_folder(temp_directory_with_files)
            assert app.state.selected_folder == temp_directory_with_files
            assert len(app.state.files_preview) == 3
            
            # Step 2: Verify preview generation
            preview_files = app.state.files_preview
            original_names = [f['original'] for f in preview_files]
            processed_names = [f['processed'] for f in preview_files]
            
            assert "Báo cáo tháng 12 (FINAL).docx" in original_names
            assert "bao cao thang 12 final.docx" in processed_names
            
            # Step 3: Execute rename operation
            progress_updates = []
            
            def track_progress(percent, current_file):
                progress_updates.append((percent, current_file))
            
            result = await app.execute_rename_operation(
                progress_callback=track_progress
            )
            
            # Verify operation success
            assert result.success_count == 3
            assert result.error_count == 0
            assert len(progress_updates) >= 3
            
            # Step 4: Verify files were actually renamed on disk
            actual_files = os.listdir(temp_directory_with_files)
            assert "bao cao thang 12 final.docx" in actual_files
            assert "hinh anh dep nhat nam 2024.jpg" in actual_files
            assert "tai lieu quan trong.pdf" in actual_files
            
            # Step 5: Test undo functionality
            undo_result = await app.undo_last_operation()
            assert undo_result.success
            
            # Verify original files restored
            restored_files = os.listdir(temp_directory_with_files)
            assert "Báo cáo tháng 12 (FINAL).docx" in restored_files
            assert "Hình ảnh đẹp nhất năm 2024!.jpg" in restored_files
            assert "Tài liệu_quan#trọng***.pdf" in restored_files
            
        finally:
            await app.cleanup()
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(
        self,
        temp_directory_with_files
    ):
        """Test error handling và recovery when some files fail to rename"""
        
        app = FileRenameApplication()
        await app.initialize()
        
        try:
            await app.select_folder(temp_directory_with_files)
            
            # Simulate file lock by opening one file
            locked_file_path = Path(temp_directory_with_files) / "Báo cáo tháng 12 (FINAL).docx"
            with open(locked_file_path, 'r') as locked_file:
                
                # Attempt rename operation
                result = await app.execute_rename_operation()
                
                # Verify partial success handling
                assert result.success_count == 2  # 2 files renamed successfully
                assert result.error_count == 1    # 1 file failed (locked)
                
                # Verify error details available
                assert len(result.error_details) == 1
                assert "permission" in result.error_details[0].lower()
                
                # Test recovery options presented to user
                recovery_options = app.get_recovery_options()
                assert "retry_failed" in recovery_options
                assert "undo_successful" in recovery_options
            
            # After file is released, test retry functionality
            retry_result = await app.retry_failed_operations()
            assert retry_result.success_count == 1
            assert retry_result.error_count == 0
            
        finally:
            await app.cleanup()
```
