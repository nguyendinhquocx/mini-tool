"""
Vietnamese Text Normalization Service

Provides comprehensive Vietnamese text processing capabilities including:
- Diacritic removal (ủ → u, đ → d, etc.)
- Case conversion and whitespace normalization
- Special character handling
- File extension preservation
- Edge case handling
"""

import re
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from unidecode import unidecode
import logging

from ..models.config import NormalizationRulesConfig

# Configure logging
logger = logging.getLogger(__name__)


@dataclass  
class NormalizationRules:
    """Configuration for Vietnamese text normalization rules"""
    remove_diacritics: bool = True
    lowercase_conversion: bool = True
    clean_special_chars: bool = True
    normalize_whitespace: bool = True
    preserve_extensions: bool = True
    
    # Advanced options
    preserve_case_for_extensions: bool = True
    preserve_numbers: bool = True
    preserve_english_words: bool = True
    
    # Processing limits
    max_filename_length: int = 255
    min_filename_length: int = 1
    
    # Special character replacement patterns
    safe_char_replacements: Dict[str, str] = None
    custom_replacements: Dict[str, str] = None
    
    def __post_init__(self):
        if self.safe_char_replacements is None:
            self.safe_char_replacements = {
                '!': '',
                '@': ' at ',
                '#': ' hash ',
                '$': ' dollar ',
                '%': ' percent ',
                '^': '',
                '&': ' and ',
                '*': '',
                '(': '',
                ')': '',
                '[': '',
                ']': '',
                '{': '',
                '}': '',
                '|': ' ',
                '\\': ' ',
                '/': '-',  # Convert to dash (smart handling for dates)
                '?': '',
                '<': '',
                '>': '',
                '"': '',
                "'": '',
                '`': '',
                '~': '',
                '+': ' plus ',
                '=': ' equals ',
                ';': '',
                ':': '',
                ',': '',
                '-': '',  # Remove hyphens (except in dates)
                '_': ' ',  # Convert underscores to spaces
            }
        
        if self.custom_replacements is None:
            self.custom_replacements = {}
    
    def merge_custom_replacements(self) -> Dict[str, str]:
        """Merge custom replacements with safe replacements"""
        if self.custom_replacements:
            # Custom replacements take precedence
            merged = self.safe_char_replacements.copy()
            merged.update(self.custom_replacements)
            return merged
        return self.safe_char_replacements
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate normalization rules configuration
        
        Returns:
            Validation results with errors and warnings
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if at least one normalization rule is enabled
        normalization_enabled = any([
            self.remove_diacritics,
            self.lowercase_conversion,
            self.clean_special_chars,
            self.normalize_whitespace
        ])
        
        if not normalization_enabled:
            validation['warnings'].append("No normalization rules enabled")
        
        # Validate filename length constraints
        if self.max_filename_length < self.min_filename_length:
            validation['errors'].append("Max filename length must be >= min filename length")
            validation['valid'] = False
        
        if self.max_filename_length > 260:  # Windows path limit
            validation['warnings'].append("Max filename length exceeds Windows limit (260)")
        
        if self.min_filename_length < 1:
            validation['errors'].append("Min filename length must be at least 1")
            validation['valid'] = False
        
        # Validate character replacements
        all_replacements = self.merge_custom_replacements()
        for char, replacement in all_replacements.items():
            if not isinstance(char, str) or not isinstance(replacement, str):
                validation['errors'].append(f"Invalid character mapping: {char} -> {replacement}")
                validation['valid'] = False
        
        return validation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'remove_diacritics': self.remove_diacritics,
            'lowercase_conversion': self.lowercase_conversion,
            'clean_special_chars': self.clean_special_chars,
            'normalize_whitespace': self.normalize_whitespace,
            'preserve_extensions': self.preserve_extensions,
            'preserve_case_for_extensions': self.preserve_case_for_extensions,
            'preserve_numbers': self.preserve_numbers,
            'preserve_english_words': self.preserve_english_words,
            'max_filename_length': self.max_filename_length,
            'min_filename_length': self.min_filename_length,
            'safe_char_replacements': self.safe_char_replacements,
            'custom_replacements': self.custom_replacements
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NormalizationRules':
        """Create from dictionary"""
        return cls(**data)


class VietnameseNormalizer:
    """Vietnamese text normalization engine"""
    
    # Vietnamese-specific character mappings for edge cases
    VIETNAMESE_CHAR_MAP = {
        'đ': 'd',
        'Đ': 'D',
        # Additional Vietnamese characters that need special handling
        '₫': 'dong',  # Vietnamese currency symbol
    }
    
    def __init__(self, rules: Optional[NormalizationRules] = None):
        self.rules = rules or NormalizationRules()
        
    @classmethod
    def from_config(cls, config_rules: NormalizationRulesConfig) -> 'VietnameseNormalizer':
        """
        Create normalizer từ configuration rules
        
        Args:
            config_rules: NormalizationRulesConfig instance từ configuration system
            
        Returns:
            VietnameseNormalizer instance
        """
        # Convert NormalizationRulesConfig to NormalizationRules
        rules = NormalizationRules(
            remove_diacritics=config_rules.remove_diacritics,
            lowercase_conversion=config_rules.convert_to_lowercase,
            clean_special_chars=config_rules.clean_special_characters,
            normalize_whitespace=config_rules.normalize_whitespace,
            preserve_extensions=config_rules.preserve_extensions,
            preserve_case_for_extensions=config_rules.preserve_case_for_extensions,
            preserve_numbers=config_rules.preserve_numbers,
            preserve_english_words=config_rules.preserve_english_words,
            max_filename_length=config_rules.max_filename_length,
            min_filename_length=config_rules.min_filename_length,
            custom_replacements=config_rules.custom_replacements.copy()
        )
        return cls(rules)
        
    def normalize_text_with_config(self, text: str, config_rules: NormalizationRulesConfig) -> str:
        """
        Apply Vietnamese normalization với configuration rules
        
        Args:
            text: Input text to normalize
            config_rules: Configuration rules từ settings system
            
        Returns:
            Normalized text string
        """
        # Convert config rules to internal format
        rules = self._convert_config_to_rules(config_rules)
        return self.normalize_text(text, rules)
    
    def normalize_filename_with_config(self, filename: str, config_rules: NormalizationRulesConfig) -> str:
        """
        Normalize filename với configuration rules
        
        Args:
            filename: Original filename
            config_rules: Configuration rules từ settings system
            
        Returns:
            Normalized filename
        """
        # Convert config rules to internal format
        rules = self._convert_config_to_rules(config_rules)
        return self.normalize_filename(filename, rules)
    
    def _convert_config_to_rules(self, config_rules: NormalizationRulesConfig) -> NormalizationRules:
        """Convert NormalizationRulesConfig to internal NormalizationRules"""
        return NormalizationRules(
            remove_diacritics=config_rules.remove_diacritics,
            lowercase_conversion=config_rules.convert_to_lowercase,
            clean_special_chars=config_rules.clean_special_characters,
            normalize_whitespace=config_rules.normalize_whitespace,
            preserve_extensions=config_rules.preserve_extensions,
            preserve_case_for_extensions=config_rules.preserve_case_for_extensions,
            preserve_numbers=config_rules.preserve_numbers,
            preserve_english_words=config_rules.preserve_english_words,
            max_filename_length=config_rules.max_filename_length,
            min_filename_length=config_rules.min_filename_length,
            custom_replacements=config_rules.custom_replacements.copy()
        )

    def normalize_text(self, text: str, rules: Optional[NormalizationRules] = None) -> str:
        """
        Apply complete Vietnamese normalization pipeline to text
        
        Args:
            text: Input text to normalize
            rules: Optional normalization rules (uses instance rules if None)
            
        Returns:
            Normalized text string
            
        Raises:
            ValueError: If text input is invalid
        """
        if not isinstance(text, str):
            raise ValueError("Input must be a string")
            
        if not text.strip():
            return ""
            
        active_rules = rules or self.rules
        result = text
        
        try:
            # Apply normalization pipeline
            # Apply custom replacements first, before other processing
            if active_rules.custom_replacements:
                result = self._apply_custom_replacements(result, active_rules.custom_replacements)
            
            if active_rules.remove_diacritics:
                result = self.remove_diacritics(result)
                
            if active_rules.lowercase_conversion:
                result = self.apply_case_rules(result)
                
            if active_rules.clean_special_chars:
                # Merge safe char replacements but exclude custom replacements (already applied)
                safe_chars_only = active_rules.safe_char_replacements or {}
                result = self.clean_special_chars(result, safe_chars_only)
                
            if active_rules.normalize_whitespace:
                result = self._normalize_whitespace(result)
                
            return result
            
        except Exception as e:
            logger.error(f"Normalization failed for text '{text[:50]}...': {e}")
            raise
    
    def normalize_filename(self, filename: str, rules: Optional[NormalizationRules] = None) -> str:
        """
        Normalize filename while preserving file extension
        
        Args:
            filename: Original filename
            rules: Optional normalization rules
            
        Returns:
            Normalized filename with original extension
        """
        if not filename:
            return ""
            
        active_rules = rules or self.rules
        
        if active_rules.preserve_extensions:
            # Extract filename and extension (only valid file extensions)
            name, ext = os.path.splitext(filename)
            
            # Check if extension is a valid file extension (alphanumeric, common extensions)
            valid_ext = ext and len(ext) <= 5 and ext[1:].isalpha() and not any(c in ext for c in ['@', '#', '!', '?'])
            
            if valid_ext:
                # Normalize only the name portion  
                normalized_name = self.normalize_text(name, active_rules)
                # Recombine with original extension (optionally normalized)
                if active_rules.preserve_case_for_extensions:
                    return normalized_name + ext
                else:
                    return normalized_name + ext.lower()
            else:
                # No valid extension found, normalize entire filename
                return self.normalize_text(filename, active_rules)
        else:
            # Don't preserve extensions, normalize everything
            return self.normalize_text(filename, active_rules)
    
    def remove_diacritics(self, text: str) -> str:
        """
        Remove Vietnamese diacritics and special characters
        
        Args:
            text: Text with potential diacritics
            
        Returns:
            Text with diacritics removed
        """
        if not text:
            return ""
            
        # Apply Vietnamese-specific character mappings first
        result = text
        for viet_char, replacement in self.VIETNAMESE_CHAR_MAP.items():
            result = result.replace(viet_char, replacement)
        
        # Apply general Unicode normalization
        try:
            result = unidecode(result)
        except Exception as e:
            logger.warning(f"Unidecode failed for '{text}': {e}")
            # Fallback: keep original if unidecode fails
            pass
            
        return result
    
    def apply_case_rules(self, text: str) -> str:
        """
        Apply case conversion rules
        
        Args:
            text: Input text
            
        Returns:
            Text with case rules applied
        """
        if not text:
            return ""
            
        return text.lower()
    
    def clean_special_chars(self, text: str, replacements: Optional[Dict[str, str]] = None) -> str:
        """
        Clean and replace special characters with smart date handling
        
        Args:
            text: Text to clean
            replacements: Character replacement mapping
            
        Returns:
            Text with special characters cleaned
        """
        if not text:
            return ""
            
        # Use provided replacements or default to safe char replacements only
        # (custom replacements should already be applied separately)
        char_map = replacements or self.rules.safe_char_replacements
        result = text
        
        # Apply all character replacements except hyphens first
        for char, replacement in char_map.items():
            if char != '-':
                result = result.replace(char, replacement)
        
        # Handle hyphens with date-aware logic
        if '-' in char_map:
            import re
            # Protect date patterns during hyphen removal
            date_pattern = r'\b\d{2}-\d{2}-\d{4}\b'
            dates = re.findall(date_pattern, result)
            placeholders = {}
            
            # Replace dates with placeholders
            for i, date in enumerate(dates):
                placeholder = f'__DATE{i}__'
                result = result.replace(date, placeholder, 1)
                placeholders[placeholder] = date
            
            # Remove hyphens from non-date content
            result = result.replace('-', char_map['-'])
            
            # Restore date patterns
            for placeholder, date in placeholders.items():
                result = result.replace(placeholder, date)
            
        return result
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace: collapse multiple spaces, trim edges
        
        Args:
            text: Text to normalize
            
        Returns:
            Text with normalized whitespace
        """
        if not text:
            return ""
            
        # Collapse multiple whitespace characters to single space
        result = re.sub(r'\s+', ' ', text)
        
        # Trim leading and trailing whitespace
        result = result.strip()
        
        return result
    
    def _apply_custom_replacements(self, text: str, custom_replacements: Dict[str, str]) -> str:
        """
        Apply custom character replacements
        
        Args:
            text: Text to process
            custom_replacements: Dictionary of custom replacements
            
        Returns:
            Text with custom replacements applied
        """
        if not text or not custom_replacements:
            return text
            
        result = text
        for char, replacement in custom_replacements.items():
            result = result.replace(char, replacement)
        
        return result
    
    def preview_normalization(self, text: str, rules: Optional[NormalizationRules] = None) -> Dict[str, Any]:
        """
        Generate normalization preview showing step-by-step transformation
        
        Args:
            text: Original text
            rules: Normalization rules to apply
            
        Returns:
            Dictionary containing original text, normalized result, and step details
        """
        active_rules = rules or self.rules
        
        preview = {
            'original': text,
            'steps': [],
            'final_result': ''
        }
        
        try:
            current = text
            
            if active_rules.remove_diacritics:
                after_diacritics = self.remove_diacritics(current)
                preview['steps'].append({
                    'step': 'Remove Diacritics',
                    'before': current,
                    'after': after_diacritics
                })
                current = after_diacritics
                
            if active_rules.lowercase_conversion:
                after_case = self.apply_case_rules(current)
                preview['steps'].append({
                    'step': 'Lowercase Conversion',
                    'before': current,
                    'after': after_case
                })
                current = after_case
                
            if active_rules.clean_special_chars:
                after_special = self.clean_special_chars(current, active_rules.safe_char_replacements)
                preview['steps'].append({
                    'step': 'Clean Special Characters',
                    'before': current,
                    'after': after_special
                })
                current = after_special
                
            if active_rules.normalize_whitespace:
                after_whitespace = self._normalize_whitespace(current)
                preview['steps'].append({
                    'step': 'Normalize Whitespace',
                    'before': current,
                    'after': after_whitespace
                })
                current = after_whitespace
                
            preview['final_result'] = current
            
        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            preview['error'] = str(e)
            
        return preview
    
    def validate_rules(self, rules: NormalizationRules) -> Dict[str, Any]:
        """
        Validate normalization rules configuration
        
        Args:
            rules: Rules to validate
            
        Returns:
            Validation results with errors and warnings
        """
        validation = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check if at least one normalization rule is enabled
        if not any([
            rules.remove_diacritics,
            rules.lowercase_conversion, 
            rules.clean_special_chars,
            rules.normalize_whitespace
        ]):
            validation['warnings'].append("No normalization rules enabled")
            
        # Validate character replacement mappings
        if rules.safe_char_replacements:
            for char, replacement in rules.safe_char_replacements.items():
                if not isinstance(char, str) or not isinstance(replacement, str):
                    validation['errors'].append(f"Invalid character mapping: {char} -> {replacement}")
                    validation['valid'] = False
                    
        return validation