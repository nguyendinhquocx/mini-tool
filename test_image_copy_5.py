#!/usr/bin/env python3
"""
Test script cho file image copy 5.png
"""

import os
import sys
import unidecode

def test_image_copy_5():
    current_folder = r"d:\pcloud\code\window\mini tool"
    test_file = "image copy 5.png"
    
    print("=== TEST IMAGE COPY 5.PNG ===")
    print(f"Current folder: {current_folder}")
    print(f"Test file: {test_file}")
    
    # Check if file exists
    full_path = os.path.join(current_folder, test_file)
    print(f"Full path: {full_path}")
    print(f"File exists: {os.path.exists(full_path)}")
    
    if not os.path.exists(full_path):
        # Create test file
        print("Creating test file...")
        try:
            with open(full_path, 'wb') as f:
                # Write some dummy PNG data
                f.write(b'\x89PNG\r\n\x1a\n')  # PNG header
                f.write(b'0' * 1000)  # Dummy data
            print(f"Created test file: {full_path}")
        except Exception as e:
            print(f"Failed to create test file: {e}")
            return
    
    # Test normalization
    print(f"\n=== NORMALIZATION TEST ===")
    name, ext = os.path.splitext(test_file)
    print(f"Original name: '{name}'")
    print(f"Extension: '{ext}'")
    
    # Apply normalization like the app does
    try:
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
        
        # Check if change is needed
        needs_change = (test_file != final_name)
        print(f"Needs change: {needs_change}")
        
        if needs_change:
            target_path = os.path.join(current_folder, final_name)
            print(f"Target path: {target_path}")
            print(f"Target exists: {os.path.exists(target_path)}")
            
            if not os.path.exists(target_path):
                print("✅ File can be renamed successfully")
            else:
                print("❌ Target file already exists!")
        else:
            print("ℹ️  File doesn't need to be renamed")
            
    except Exception as e:
        print(f"❌ Normalization failed: {e}")

if __name__ == "__main__":
    test_image_copy_5()