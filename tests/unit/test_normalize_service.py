"""
Unit tests for Vietnamese Text Normalization Service

Tests comprehensive Vietnamese text processing including:
- Diacritics removal 
- Case conversion
- Special character handling
- Whitespace normalization
- File extension preservation
- Edge case handling
"""

import pytest
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.services.normalize_service import VietnameseNormalizer, NormalizationRules


class TestVietnameseNormalizer:
    @pytest.fixture
    def normalizer(self):
        return VietnameseNormalizer()
    
    @pytest.fixture
    def default_rules(self):
        return NormalizationRules()
    
    def test_remove_diacritics_basic(self, normalizer):
        """Test basic Vietnamese diacritics removal"""
        test_cases = [
            ("ủ", "u"),
            ("đ", "d"),
            ("Đ", "D"),
            ("Nguyễn", "Nguyen"),
            ("Tài liệu", "Tai lieu"),
            ("Phạm Văn Hùng", "Pham Van Hung"),
            ("QUAN TRỌNG", "QUAN TRONG"),
            ("Hồ Chí Minh", "Ho Chi Minh"),
        ]
        
        for input_text, expected in test_cases:
            result = normalizer.remove_diacritics(input_text)
            assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
    
    def test_remove_diacritics_comprehensive(self, normalizer):
        """Test comprehensive Vietnamese character set"""
        # All Vietnamese vowels with diacritics
        vowel_tests = [
            # a variations
            ("áàảãạ", "aaaaa"),
            ("ÁÀẢÃẠ", "AAAAA"),
            ("ắằẳẵặ", "aaaaa"),
            ("ẮẰẲẴẶ", "AAAAA"),
            ("ấầẩẫậ", "aaaaa"),
            ("ẤẦẨẪẬ", "AAAAA"),
            
            # e variations  
            ("éèẻẽẹ", "eeeee"),
            ("ÉÈẺẼẸ", "EEEEE"),
            ("ếềểễệ", "eeeee"),
            ("ẾỀỂỄỆ", "EEEEE"),
            
            # i variations
            ("íìỉĩị", "iiiii"),
            ("ÍÌỈĨỊ", "IIIII"),
            
            # o variations
            ("óòỏõọ", "ooooo"),
            ("ÓÒỎÕỌ", "OOOOO"),
            ("ốồổỗộ", "ooooo"),
            ("ỐỒỔỖỘ", "OOOOO"),
            ("ớờởỡợ", "ooooo"),
            ("ỚỜỞỠỢ", "OOOOO"),
            
            # u variations
            ("úùủũụ", "uuuuu"),
            ("ÚÙỦŨỤ", "UUUUU"),
            ("ứừửữự", "uuuuu"),
            ("ỨỪỬỮỰ", "UUUUU"),
            
            # y variations
            ("ýỳỷỹỵ", "yyyyy"),
            ("ÝỲỶỸỴ", "YYYYY"),
        ]
        
        for input_text, expected in vowel_tests:
            result = normalizer.remove_diacritics(input_text)
            assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
    
    def test_apply_case_rules(self, normalizer):
        """Test case conversion rules"""
        test_cases = [
            ("Hello World", "hello world"),
            ("TRANG CHỦ", "trang chủ"),  # Vietnamese chars case converted
            ("MiXeD CaSe", "mixed case"),
            ("123ABC", "123abc"),
            ("", ""),
        ]
        
        for input_text, expected in test_cases:
            result = normalizer.apply_case_rules(input_text)
            assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
    
    def test_clean_special_chars(self, normalizer):
        """Test special character cleaning"""
        test_cases = [
            ("file!name", "filename"),
            ("document@test", "document at test"),
            ("file#123", "file hash 123"),
            ("data$report", "data dollar report"),
            ("test%value", "test percent value"),
            ("name&surname", "name and surname"),
            ("file*copy", "filecopy"),
            ("doc(final)", "docfinal"),
            ("test[1]", "test1"),
            ("data{new}", "datanew"),
            ("file|backup", "file backup"),
            ("path\\name", "path name"),
            ("url/path", "url-path"),
            ("query?param", "queryparam"),
            ("file<temp>", "filetemp"),
            ('file"quoted"', "filequoted"),
            ("file'name'", "filename"),
            ("file`test`", "filetest"),
            ("config~old", "configold"),
            ("value+extra", "value plus extra"),
            ("formula=result", "formula equals result"),
            ("list;items", "listitems"),
            ("time:format", "timeformat"),
            ("file,name", "filename"),
        ]
        
        for input_text, expected in test_cases:
            result = normalizer.clean_special_chars(input_text)
            assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
    
    def test_normalize_whitespace(self, normalizer):
        """Test whitespace normalization"""
        test_cases = [
            ("  hello  world  ", "hello world"),
            ("multiple   spaces", "multiple spaces"),
            ("\t\n\r mixed \t\n whitespace \r\n", "mixed whitespace"),
            ("single space", "single space"),
            ("", ""),
            ("   ", ""),
            ("word", "word"),
        ]
        
        for input_text, expected in test_cases:
            result = normalizer._normalize_whitespace(input_text)
            assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
    
    def test_normalize_text_complete_pipeline(self, normalizer, default_rules):
        """Test complete normalization pipeline"""
        test_cases = [
            # Basic Vietnamese normalization
            ("Nguyễn Văn A", "nguyen van a"),
            ("Tài liệu QUAN TRỌNG", "tai lieu quan trong"),
            ("Phạm   Thị   Hoa", "pham thi hoa"),
            
            # With special characters
            ("File@test#123.txt", "file at test hash 123.txt"),
            ("Document (FINAL)!", "document final"),
            ("Data$report%2023", "data dollar report percent 2023"),
            
            # Complex mixed cases
            ("Báo cáo Tài chính 2023 (FINAL VERSION)!!!", "bao cao tai chinh 2023 final version"),
            ("Hướng dẫn Sử dụng & Cài đặt", "huong dan su dung and cai dat"),
            
            # Edge cases
            ("", ""),
            ("123", "123"),
            ("ABC", "abc"),
        ]
        
        for input_text, expected in test_cases:
            result = normalizer.normalize_text(input_text, default_rules)
            assert result == expected, f"Failed for '{input_text}': got '{result}', expected '{expected}'"
    
    def test_normalize_filename_with_extension(self, normalizer, default_rules):
        """Test filename normalization with extension preservation"""
        test_cases = [
            ("Tài liệu.txt", "tai lieu.txt"),
            ("Báo cáo (FINAL).docx", "bao cao final.docx"),
            ("Data@file#test.pdf", "data at file hash test.pdf"),
            ("Image_Ảnh_Đẹp.jpg", "image anh dep.jpg"),
            ("NoExtension", "noextension"),
            (".hidden", ".hidden"),
            ("file.with.multiple.dots.txt", "file.with.multiple.dots.txt"),
        ]
        
        for input_filename, expected in test_cases:
            result = normalizer.normalize_filename(input_filename, default_rules)
            assert result == expected, f"Failed for '{input_filename}': got '{result}', expected '{expected}'"
    
    def test_normalize_filename_no_extension_preservation(self, normalizer):
        """Test filename normalization without extension preservation"""
        rules = NormalizationRules(preserve_extensions=False)
        
        test_cases = [
            ("File.TXT", "file.txt"),
            ("Document.DOCX", "document.docx"),
            ("Tài liệu.PDF", "tai lieu.pdf"),
        ]
        
        for input_filename, expected in test_cases:
            result = normalizer.normalize_filename(input_filename, rules)
            assert result == expected, f"Failed for '{input_filename}': got '{result}', expected '{expected}'"
    
    def test_edge_cases(self, normalizer, default_rules):
        """Test edge case handling"""
        # Empty and null cases
        assert normalizer.normalize_text("", default_rules) == ""
        assert normalizer.normalize_text("   ", default_rules) == ""
        
        # Only special characters
        assert normalizer.normalize_text("!@#$%^&*()", default_rules) == "at hash dollar percent and"
        
        # Only numbers
        assert normalizer.normalize_text("123456", default_rules) == "123456"
        
        # Mixed language content
        mixed_text = "Hello Xin chào 123 !@#"
        result = normalizer.normalize_text(mixed_text, default_rules)
        assert "hello" in result
        assert "xin chao" in result
        assert "123" in result
        
        # Very long text
        long_text = "Đây là một văn bản rất dài " * 20
        result = normalizer.normalize_text(long_text, default_rules)
        assert len(result) > 0
        assert "day la mot van ban rat dai" in result
    
    def test_invalid_inputs(self, normalizer):
        """Test invalid input handling"""
        with pytest.raises(ValueError):
            normalizer.normalize_text(123)
        
        with pytest.raises(ValueError): 
            normalizer.normalize_text(None)
        
        with pytest.raises(ValueError):
            normalizer.normalize_text([])
    
    def test_preview_normalization(self, normalizer, default_rules):
        """Test normalization preview functionality"""
        preview = normalizer.preview_normalization("Tài liệu QUAN TRỌNG!!!", default_rules)
        
        assert 'original' in preview
        assert 'steps' in preview
        assert 'final_result' in preview
        
        assert preview['original'] == "Tài liệu QUAN TRỌNG!!!"
        assert preview['final_result'] == "tai lieu quan trong"
        assert len(preview['steps']) > 0
        
        # Check that each step shows transformation
        for step in preview['steps']:
            assert 'step' in step
            assert 'before' in step
            assert 'after' in step
    
    def test_custom_character_replacements(self, normalizer):
        """Test custom character replacement rules"""
        custom_rules = NormalizationRules(
            custom_replacements={'@': '_AT_', '#': '_HASH_'}
        )
        
        result = normalizer.clean_special_chars("test@email#tag", custom_rules.merge_custom_replacements()) 
        assert result == "test_AT_email_HASH_tag"
    
    def test_normalization_rules_validation(self):
        """Test normalization rules validation"""
        # Valid rules
        valid_rules = NormalizationRules()
        validation = valid_rules.validate()
        assert validation['valid'] is True
        
        # Invalid rules - bad filename lengths
        invalid_rules = NormalizationRules(max_filename_length=5, min_filename_length=10)
        validation = invalid_rules.validate()
        assert validation['valid'] is False
        assert len(validation['errors']) > 0
        
        # Rules with no normalization enabled
        no_norm_rules = NormalizationRules(
            remove_diacritics=False,
            lowercase_conversion=False,
            clean_special_chars=False,
            normalize_whitespace=False
        )
        validation = no_norm_rules.validate()
        assert len(validation['warnings']) > 0
    
    def test_vietnamese_currency_symbol(self, normalizer):
        """Test Vietnamese currency symbol handling"""
        result = normalizer.remove_diacritics("Giá: 1.000.000₫")
        assert "dong" in result.lower()
        assert "₫" not in result
    
    def test_real_world_filenames(self, normalizer, default_rules):
        """Test with real-world Vietnamese filenames"""
        real_filenames = [
            "Báo cáo tài chính quý 4 năm 2023.xlsx",
            "Hướng dẫn sử dụng phần mềm (phiên bản mới).pdf", 
            "Danh sách nhân viên - Cập nhật tháng 12.docx",
            "Ảnh đại diện profile (1024x1024).jpg",
            "Tài liệu kỹ thuật & Hướng dẫn vận hành.txt",
            "Báo giá sản phẩm mới - Có hiệu lực từ 01/01/2024.pdf",
        ]
        
        expected_results = [
            "bao cao tai chinh quy 4 nam 2023.xlsx",
            "huong dan su dung phan mem phien ban moi.pdf",
            "danh sach nhan vien cap nhat thang 12.docx", 
            "anh dai dien profile 1024x1024.jpg",
            "tai lieu ky thuat and huong dan van hanh.txt",
            "bao gia san pham moi co hieu luc tu 01-01-2024.pdf",
        ]
        
        for filename, expected in zip(real_filenames, expected_results):
            result = normalizer.normalize_filename(filename, default_rules)
            assert result == expected, f"Failed for '{filename}': got '{result}', expected '{expected}'"


class TestNormalizationRules:
    def test_default_rules_initialization(self):
        """Test default rules initialization"""
        rules = NormalizationRules()
        
        assert rules.remove_diacritics is True
        assert rules.lowercase_conversion is True 
        assert rules.clean_special_chars is True
        assert rules.normalize_whitespace is True
        assert rules.preserve_extensions is True
        
        # Check default character replacements are populated
        assert len(rules.safe_char_replacements) > 0
        assert '@' in rules.safe_char_replacements
        assert rules.safe_char_replacements['@'] == ' at '
    
    def test_custom_rules(self):
        """Test custom rules configuration"""
        rules = NormalizationRules(
            remove_diacritics=False,
            lowercase_conversion=False,
            max_filename_length=100,
            custom_replacements={'@': '_EMAIL_'}
        )
        
        assert rules.remove_diacritics is False
        assert rules.lowercase_conversion is False
        assert rules.max_filename_length == 100
        assert rules.custom_replacements['@'] == '_EMAIL_'
    
    def test_rules_serialization(self):
        """Test rules to_dict and from_dict"""
        original_rules = NormalizationRules(
            remove_diacritics=True,
            custom_replacements={'@': '_at_'}
        )
        
        # Serialize to dict
        rules_dict = original_rules.to_dict()
        assert isinstance(rules_dict, dict)
        assert rules_dict['remove_diacritics'] is True
        assert '@' in rules_dict['custom_replacements']
        
        # Deserialize from dict
        restored_rules = NormalizationRules.from_dict(rules_dict)
        assert restored_rules.remove_diacritics is True
        assert restored_rules.custom_replacements['@'] == '_at_'