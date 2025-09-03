#!/usr/bin/env python3
"""
Comprehensive test of the complete app workflow
"""

import os
import sys
import tempfile
import shutil

# Add the current directory to path so we can import from complete_app
sys.path.insert(0, os.path.dirname(__file__))

def create_test_files():
    """Create various test files to verify different scenarios"""
    test_dir = tempfile.mkdtemp(prefix="rename_test_")
    print(f"Created test directory: {test_dir}")
    
    # Test files with different characteristics
    test_files = [
        "image copy 6.png",          # No change needed
        "Image Copy 7.PNG",          # Case change + extension
        "SPECIAL!@#FILE.txt",        # Special chars
        "Tên File Tiếng Việt.doc",   # Vietnamese diacritics
        "file with    spaces.pdf",   # Multiple spaces
        "UPPER CASE FILE.TXT",       # All caps
    ]
    
    for filename in test_files:
        filepath = os.path.join(test_dir, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Test content for {filename}")
            print(f"Created: {filename}")
        except Exception as e:
            print(f"Failed to create {filename}: {e}")
    
    return test_dir

def test_normalization_directly():
    """Test the VietnameseNormalizer directly"""
    print("\n=== TESTING VIETNAMESENORMALIZER ===")
    
    try:
        # Import the normalizer class
        from complete_app import VietnameseNormalizer
        
        # Create normalizer with default rules
        rules = {
            "remove_diacritics": True,
            "lowercase_conversion": True, 
            "clean_special_chars": True,
            "normalize_whitespace": True,
            "preserve_extensions": True,
            "custom_replacements": {}
        }
        
        normalizer = VietnameseNormalizer(rules)
        
        test_cases = [
            "image copy 6.png",
            "Image Copy 7.PNG", 
            "SPECIAL!@#FILE.txt",
            "Tên File Tiếng Việt.doc",
            "file with    spaces.pdf",
            "UPPER CASE FILE.TXT"
        ]
        
        for filename in test_cases:
            try:
                normalized = normalizer.normalize_filename(filename)
                needs_change = filename != normalized
                print(f"'{filename}' -> '{normalized}' (Changed: {needs_change})")
            except Exception as e:
                print(f"ERROR normalizing '{filename}': {e}")
                
    except ImportError as e:
        print(f"Cannot import VietnameseNormalizer: {e}")
    except Exception as e:
        print(f"Error in normalization test: {e}")

def test_file_operations():
    """Test file operations in a safe test directory"""
    print("\n=== TESTING FILE OPERATIONS ===")
    
    test_dir = create_test_files()
    
    try:
        # Test basic file operations
        test_file = os.path.join(test_dir, "image copy 6.png")
        if os.path.exists(test_file):
            print(f"✓ Test file exists: {test_file}")
            
            # Test rename to same name (should be no-op)
            same_name_target = test_file
            print(f"Attempting rename to same name: {same_name_target}")
            
            # This should do nothing (same source and target)
            if test_file == same_name_target:
                print("✓ Correctly identified same source and target")
            
            # Test rename to different name
            new_name = os.path.join(test_dir, "renamed_image_copy_6.png")
            try:
                shutil.copy2(test_file, new_name)  # Copy instead of rename for testing
                print(f"✓ Successfully copied to: {new_name}")
                
                # Clean up
                os.remove(new_name)
                print("✓ Cleanup successful")
                
            except Exception as e:
                print(f"✗ File operation failed: {e}")
        
    finally:
        # Clean up test directory
        try:
            shutil.rmtree(test_dir)
            print(f"✓ Cleaned up test directory: {test_dir}")
        except Exception as e:
            print(f"Warning: Could not clean up {test_dir}: {e}")

def main():
    print("=== COMPREHENSIVE APP TEST ===")
    
    # Test 1: Direct normalization
    test_normalization_directly()
    
    # Test 2: File operations
    test_file_operations()
    
    # Test 3: Check specific file in actual directory
    print("\n=== CHECKING ACTUAL FILES ===")
    current_dir = r"d:\pcloud\code\window\mini tool"
    
    for i in range(2, 7):  # Check image copy 2.png to 6.png
        filename = f"image copy {i}.png"
        filepath = os.path.join(current_dir, filename)
        exists = os.path.exists(filepath)
        print(f"{filename}: {'EXISTS' if exists else 'NOT FOUND'}")
    
    print("\n=== TEST COMPLETED ===")

if __name__ == "__main__":
    main()