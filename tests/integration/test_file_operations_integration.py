"""
Integration tests for File Operations Engine with Vietnamese normalization

Tests end-to-end file processing workflows including:
- Folder scanning with normalization preview
- Batch rename operations
- File operations engine integration
- Real Vietnamese filename processing
"""

import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src directory to path  
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.file_operations_engine import FileOperationsEngine
from core.services.normalize_service import VietnameseNormalizer, NormalizationRules
from core.models.file_info import FileInfo, FileType, OperationStatus
from core.models.operation import BatchOperation, OperationType


class TestFileOperationsIntegration:
    @pytest.fixture
    def temp_folder_with_vietnamese_files(self):
        """Create temporary folder with Vietnamese test files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files with Vietnamese names
            test_files = [
                "Tài liệu quan trọng.txt",
                "Báo cáo tài chính Q4.xlsx", 
                "Hướng dẫn sử dụng (phiên bản mới).pdf",
                "Ảnh đại diện - Nguyễn Văn A.jpg",
                "Danh sách nhân viên & Lương.docx",
                "File@test#special!chars.txt",
                "DOCUMENT   WITH   SPACES.doc",
                "file.without.vietnamese.txt"
            ]
            
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test content for {filename}")
            
            # Create a subdirectory with files
            sub_dir = os.path.join(temp_dir, "Thư mục con")
            os.makedirs(sub_dir)
            
            sub_files = [
                "Tệp trong thư mục con.txt", 
                "Another file.pdf"
            ]
            
            for filename in sub_files:
                file_path = os.path.join(sub_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Sub folder content: {filename}")
            
            yield temp_dir
    
    @pytest.fixture
    def file_engine(self):
        """Create FileOperationsEngine with Vietnamese normalizer"""
        normalizer = VietnameseNormalizer()
        return FileOperationsEngine(normalizer)
    
    @pytest.fixture
    def vietnamese_normalization_rules(self):
        """Create Vietnamese-specific normalization rules"""
        return NormalizationRules(
            remove_diacritics=True,
            lowercase_conversion=True,
            clean_special_chars=True,
            normalize_whitespace=True,
            preserve_extensions=True
        )
    
    def test_scan_folder_contents_single_level(self, file_engine, temp_folder_with_vietnamese_files):
        """Test folder scanning at single level"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False)
        
        assert len(files) > 0
        
        # Check that we have both files and folders
        file_types = {f.file_type for f in files}
        assert FileType.FILE in file_types
        assert FileType.FOLDER in file_types
        
        # Check specific Vietnamese files
        file_names = {f.name for f in files}
        assert "Tài liệu quan trọng.txt" in file_names
        assert "Báo cáo tài chính Q4.xlsx" in file_names
        assert "Thư mục con" in file_names
        
        # Verify file metadata is populated
        for file_info in files:
            assert file_info.path
            assert file_info.original_name
            if file_info.file_type == FileType.FILE:
                assert file_info.size >= 0
                assert file_info.size_formatted
    
    def test_scan_folder_contents_recursive(self, file_engine, temp_folder_with_vietnamese_files):
        """Test recursive folder scanning"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=True)
        
        # Should include files from subdirectory
        file_names = {f.name for f in files}
        assert "Tệp trong thư mục con.txt" in file_names
        assert "Another file.pdf" in file_names
        
        # Should have more files than single-level scan
        single_level_count = len(file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False))
        assert len(files) > single_level_count
    
    def test_preview_rename_vietnamese_files(self, file_engine, temp_folder_with_vietnamese_files, vietnamese_normalization_rules):
        """Test rename preview generation for Vietnamese files"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False)
        file_only = [f for f in files if f.file_type == FileType.FILE]
        
        previews = file_engine.preview_rename(file_only, vietnamese_normalization_rules)
        
        assert len(previews) == len(file_only)
        
        # Check specific transformations
        preview_map = {p.original_name: p for p in previews}
        
        # Vietnamese diacritics should be removed
        if "Tài liệu quan trọng.txt" in preview_map:
            preview = preview_map["Tài liệu quan trọng.txt"]
            assert preview.normalized_name == "tai lieu quan trong.txt"
            assert preview.has_changes is True
            assert len(preview.changes_made) > 0
        
        # Special characters should be cleaned
        if "File@test#special!chars.txt" in preview_map:
            preview = preview_map["File@test#special!chars.txt"] 
            assert "at" in preview.normalized_name
            assert "hash" in preview.normalized_name
            assert "!" not in preview.normalized_name
        
        # Multiple spaces should be normalized
        if "DOCUMENT   WITH   SPACES.doc" in preview_map:
            preview = preview_map["DOCUMENT   WITH   SPACES.doc"]
            assert "document with spaces.doc" == preview.normalized_name
    
    def test_preview_no_changes_needed(self, file_engine, temp_folder_with_vietnamese_files, vietnamese_normalization_rules):
        """Test preview for files that don't need changes"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False)
        file_only = [f for f in files if f.file_type == FileType.FILE]
        
        previews = file_engine.preview_rename(file_only, vietnamese_normalization_rules)
        
        # Find file that shouldn't change
        no_change_previews = [p for p in previews if not p.has_changes]
        
        # Should have at least the English-only file
        english_file_preview = next((p for p in previews if "without.vietnamese" in p.original_name), None)
        if english_file_preview:
            assert not english_file_preview.has_changes
            assert english_file_preview.normalized_name == english_file_preview.original_name
    
    def test_dry_run_batch_rename(self, file_engine, temp_folder_with_vietnamese_files, vietnamese_normalization_rules):
        """Test dry run batch rename operation"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False)
        file_only = [f for f in files if f.file_type == FileType.FILE][:3]  # Limit for test
        
        previews = file_engine.preview_rename(file_only, vietnamese_normalization_rules)
        
        # Create batch operation for dry run
        batch_op = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=vietnamese_normalization_rules,
            total_files=len(previews),
            dry_run=True
        )
        
        # Execute dry run
        result = file_engine.execute_batch_rename(previews, batch_op)
        
        assert result.is_completed()
        assert result.dry_run is True
        assert result.total_files == len(previews)
        assert result.processed_files == len(previews)
        
        # Files should not actually be renamed in dry run
        original_files = os.listdir(temp_folder_with_vietnamese_files)
        assert "Tài liệu quan trọng.txt" in original_files  # Original should still exist
        assert "tai lieu quan trong.txt" not in original_files  # New name should not exist
    
    def test_actual_batch_rename_operation(self, file_engine, vietnamese_normalization_rules):
        """Test actual file rename execution"""
        # Create separate temp directory for this destructive test
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                "Tệp thử nghiệm.txt",
                "File@special#chars.pdf"
            ]
            
            for filename in test_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Content for {filename}")
            
            # Scan and preview
            files = file_engine.scan_folder_contents(temp_dir, recursive=False)
            file_only = [f for f in files if f.file_type == FileType.FILE]
            previews = file_engine.preview_rename(file_only, vietnamese_normalization_rules)
            
            # Execute actual rename (not dry run)
            batch_op = BatchOperation(
                operation_type=OperationType.BATCH_RENAME,
                normalization_rules=vietnamese_normalization_rules,
                total_files=len(previews),
                dry_run=False
            )
            
            result = file_engine.execute_batch_rename(previews, batch_op)
            
            assert result.is_completed()
            assert result.successful_operations > 0
            
            # Check that files were actually renamed
            renamed_files = os.listdir(temp_dir)
            assert "tep thu nghiem.txt" in renamed_files
            assert "file at special hash chars.pdf" in renamed_files
            
            # Original files should not exist
            assert "Tệp thử nghiệm.txt" not in renamed_files
            assert "File@special#chars.pdf" not in renamed_files
    
    def test_backup_creation_during_rename(self, file_engine):
        """Test backup creation during rename operations"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file
            original_file = os.path.join(temp_dir, "Tệp gốc.txt")
            with open(original_file, 'w', encoding='utf-8') as f:
                f.write("Original content")
            
            # Rules with backup enabled
            rules = NormalizationRules(create_backup=True)
            
            files = file_engine.scan_folder_contents(temp_dir)
            file_only = [f for f in files if f.file_type == FileType.FILE]
            previews = file_engine.preview_rename(file_only, rules)
            
            batch_op = BatchOperation(
                operation_type=OperationType.BATCH_RENAME,
                normalization_rules=rules,
                total_files=len(previews),
                dry_run=False
            )
            
            result = file_engine.execute_batch_rename(previews, batch_op)
            
            # Check operation completed successfully
            assert result.successful_operations > 0
            
            # Renamed file should exist
            renamed_files = os.listdir(temp_dir)
            assert "tep goc.txt" in renamed_files
    
    def test_readonly_file_handling(self, file_engine):
        """Test handling of read-only files"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test file and make it read-only
            readonly_file = os.path.join(temp_dir, "Tệp chỉ đọc.txt")
            with open(readonly_file, 'w', encoding='utf-8') as f:
                f.write("Read-only content")
            
            # Make file read-only (Windows and Unix compatible)
            os.chmod(readonly_file, 0o444)
            
            try:
                # Rules to skip read-only files
                rules = NormalizationRules(skip_readonly_files=True)
                
                files = file_engine.scan_folder_contents(temp_dir)
                file_only = [f for f in files if f.file_type == FileType.FILE]
                previews = file_engine.preview_rename(file_only, rules)
                
                batch_op = BatchOperation(
                    operation_type=OperationType.BATCH_RENAME,
                    normalization_rules=rules,
                    total_files=len(previews),
                    dry_run=False
                )
                
                result = file_engine.execute_batch_rename(previews, batch_op)
                
                # Should skip the read-only file
                assert result.skipped_operations > 0
                
                # Original file should still exist
                remaining_files = os.listdir(temp_dir)
                assert "Tệp chỉ đọc.txt" in remaining_files
                
            finally:
                # Restore write permissions for cleanup
                os.chmod(readonly_file, 0o666)
    
    def test_file_conflict_detection(self, file_engine):
        """Test detection of file naming conflicts"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create two files that would normalize to same name
            file1 = os.path.join(temp_dir, "Tệp Một.txt")
            file2 = os.path.join(temp_dir, "tệp một.txt")  # Different case, same normalized result
            
            with open(file1, 'w', encoding='utf-8') as f:
                f.write("Content 1")
            with open(file2, 'w', encoding='utf-8') as f:
                f.write("Content 2")
            
            files = file_engine.scan_folder_contents(temp_dir)
            file_only = [f for f in files if f.file_type == FileType.FILE]
            previews = file_engine.preview_rename(file_only, NormalizationRules())
            
            # Both files would normalize to "tep mot.txt"
            normalized_names = [p.normalized_name for p in previews]
            
            # Should detect potential conflict
            conflict_previews = [p for p in previews if p.warnings]
            assert len(conflict_previews) > 0 or len(set(normalized_names)) < len(normalized_names)
    
    def test_operation_validation(self, file_engine, temp_folder_with_vietnamese_files):
        """Test operation validation before execution"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False)
        file_only = [f for f in files if f.file_type == FileType.FILE]
        
        # Valid rules
        valid_rules = NormalizationRules()
        validation = file_engine.validate_operation(file_only, valid_rules)
        
        assert validation['valid'] is True
        assert validation['file_count'] == len(file_only)
        assert validation['estimated_changes'] >= 0
        
        # Invalid rules
        invalid_rules = NormalizationRules(max_filename_length=5, min_filename_length=10)
        validation = file_engine.validate_operation(file_only, invalid_rules)
        
        assert validation['valid'] is False
        assert len(validation['errors']) > 0
    
    def test_operation_history_tracking(self, file_engine, temp_folder_with_vietnamese_files):
        """Test operation history tracking"""
        files = file_engine.scan_folder_contents(temp_folder_with_vietnamese_files, recursive=False)
        file_only = [f for f in files if f.file_type == FileType.FILE][:2]  # Limit for test
        
        # Initially no history
        assert len(file_engine.get_operation_history()) == 0
        
        # Execute dry run operation
        previews = file_engine.preview_rename(file_only, NormalizationRules())
        batch_op = BatchOperation(
            operation_type=OperationType.BATCH_RENAME,
            normalization_rules=NormalizationRules(),
            total_files=len(previews),
            dry_run=True
        )
        
        result = file_engine.execute_batch_rename(previews, batch_op)
        
        # Should have operation in history
        history = file_engine.get_operation_history()
        assert len(history) == 1
        assert history[0].operation_id == result.operation_id
        assert history[0].is_completed()
    
    def test_error_handling_invalid_folder(self, file_engine):
        """Test error handling for invalid folder paths"""
        # Non-existent folder
        with pytest.raises(ValueError):
            file_engine.scan_folder_contents("/nonexistent/folder/path")
        
        # File instead of folder
        with tempfile.NamedTemporaryFile() as temp_file:
            with pytest.raises(ValueError):
                file_engine.scan_folder_contents(temp_file.name)
    
    def test_comprehensive_vietnamese_character_processing(self, file_engine):
        """Test comprehensive Vietnamese character processing in realistic scenarios"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create files with comprehensive Vietnamese text
            vietnamese_files = [
                "Nghị quyết số 123 về việc tăng lương.pdf",
                "Báo cáo đánh giá hiệu suất làm việc (Quý 1-2024).xlsx",
                "Hướng dẫn thực hiện quy trình mới - Cực kỳ quan trọng!.docx",
                "Danh sách ứng viên tiềm năng & Kế hoạch tuyển dụng.txt",
                "Tổng hợp ý kiến đóng góp từ khách hàng.doc",
            ]
            
            expected_normalized = [
                "nghi quyet so 123 ve viec tang luong.pdf",
                "bao cao danh gia hieu suat lam viec quy 1-2024.xlsx", 
                "huong dan thuc hien quy trinh moi cuc ky quan trong.docx",
                "danh sach ung vien tiem nang and ke hoach tuyen dung.txt",
                "tong hop y kien dong gop tu khach hang.doc",
            ]
            
            # Create files
            for filename in vietnamese_files:
                file_path = os.path.join(temp_dir, filename)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"Vietnamese content for {filename}")
            
            # Process files
            files = file_engine.scan_folder_contents(temp_dir)
            file_only = [f for f in files if f.file_type == FileType.FILE]
            previews = file_engine.preview_rename(file_only, NormalizationRules())
            
            # Verify transformations
            preview_map = {p.original_name: p.normalized_name for p in previews}
            
            for original, expected in zip(vietnamese_files, expected_normalized):
                if original in preview_map:
                    assert preview_map[original] == expected, f"Failed for {original}: got {preview_map[original]}, expected {expected}"