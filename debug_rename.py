#!/usr/bin/env python3
"""
Debug script để kiểm tra lỗi đổi tên file cụ thể
"""

import os
import sys
import unidecode

def debug_rename_issue():
    # Test file path
    current_folder = r"d:\pcloud\code\window\mini tool"
    test_file = "image copy 4.png"
    
    print("=== DEBUG RENAME ISSUE ===")
    print(f"Current folder: {current_folder}")
    print(f"Test file: {test_file}")
    
    # Check if file exists
    full_path = os.path.join(current_folder, test_file)
    print(f"Full path: {full_path}")
    print(f"File exists: {os.path.exists(full_path)}")
    
    if os.path.exists(full_path):
        try:
            # Get file info
            stat = os.stat(full_path)
            print(f"File size: {stat.st_size} bytes")
            print(f"File permissions: {oct(stat.st_mode)}")
        except Exception as e:
            print(f"Error getting file info: {e}")
    
    # Test normalization
    print(f"\n=== NORMALIZATION TEST ===")
    name, ext = os.path.splitext(test_file)
    print(f"Original name: '{name}'")
    print(f"Extension: '{ext}'")
    
    # Apply normalization
    normalized = unidecode.unidecode(name)
    print(f"After unidecode: '{normalized}'")
    
    # Clean special chars
    replacements = {
        '!': '', '@': ' at ', '#': ' hash ', '$': ' dollar ',
        '%': ' percent ', '^': '', '&': ' and ', '*': '',
        '(': '', ')': '', '[': '', ']': '', '{': '', '}': '',
        '|': ' ', '\\': ' ', '/': '', '?': '', '<': '', '>': '',
        '"': '', "'": '', '`': '', '~': '', '+': ' plus ',
        '=': ' equals ', ';': '', ':': '', ',': ''
    }
    
    for char, replacement in replacements.items():
        normalized = normalized.replace(char, replacement)
    
    print(f"After cleaning special chars: '{normalized}'")
    
    # Normalize whitespace
    normalized = ' '.join(normalized.split()).strip()
    print(f"After whitespace normalization: '{normalized}'")
    
    # Lowercase
    normalized = normalized.lower()
    print(f"After lowercase: '{normalized}'")
    
    # Final name
    final_name = normalized + ext
    print(f"Final normalized name: '{final_name}'")
    
    # Check target path
    target_path = os.path.join(current_folder, final_name)
    print(f"Target path: {target_path}")
    print(f"Target exists: {os.path.exists(target_path)}")
    
    # Test rename operation
    if os.path.exists(full_path) and not os.path.exists(target_path):
        try:
            print(f"\n=== TESTING RENAME ===")
            print(f"From: {full_path}")
            print(f"To: {target_path}")
            
            # Don't actually rename, just test
            print("Would perform: os.rename(full_path, target_path)")
            print("Test successful - no obvious issues found")
            
        except Exception as e:
            print(f"Rename test failed: {e}")
    else:
        if not os.path.exists(full_path):
            print("ERROR: Source file doesn't exist!")
        if os.path.exists(target_path):
            print("ERROR: Target file already exists!")
    
    # List all files in directory
    print(f"\n=== DIRECTORY CONTENTS ===")
    try:
        files = os.listdir(current_folder)
        image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))]
        print(f"Image files found: {len(image_files)}")
        for f in image_files:
            print(f"  - {f}")
    except Exception as e:
        print(f"Error listing directory: {e}")

if __name__ == "__main__":
    debug_rename_issue()