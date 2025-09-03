#!/usr/bin/env python3
"""
Debug image copy 6.png issue
"""

import os
import sys
import unidecode
import traceback

# Add UTF-8 encoding for console output
os.environ['PYTHONIOENCODING'] = 'utf-8'

def debug_image_6():
    try:
        current_folder = r"d:\pcloud\code\window\mini tool"
        test_file = "image copy 6.png"
        
        print("=== DEBUG IMAGE COPY 6.PNG ===")
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
            except Exception as e:
                print(f"Error getting file info: {e}")
        
        # Test normalization step by step
        print(f"\n=== STEP-BY-STEP NORMALIZATION ===")
        name, ext = os.path.splitext(test_file)
        print(f"1. Original name: '{name}'")
        print(f"2. Extension: '{ext}'")
        
        result = name
        
        # Step 1: Remove diacritics
        try:
            result = unidecode.unidecode(result)
            print(f"3. After unidecode: '{result}'")
        except Exception as e:
            print(f"3. ERROR in unidecode: {e}")
            return
        
        # Step 2: Clean special chars (simplified)
        try:
            # Only test basic replacements to avoid issues
            simple_replacements = {' ': ' '}  # Keep spaces as is for now
            for old, new in simple_replacements.items():
                result = result.replace(old, new)
            print(f"4. After basic cleaning: '{result}'")
        except Exception as e:
            print(f"4. ERROR in cleaning: {e}")
            return
        
        # Step 3: Normalize whitespace
        try:
            result = ' '.join(result.split()).strip()
            print(f"5. After whitespace normalization: '{result}'")
        except Exception as e:
            print(f"5. ERROR in whitespace normalization: {e}")
            return
        
        # Step 4: Lowercase
        try:
            result = result.lower()
            print(f"6. After lowercase: '{result}'")
        except Exception as e:
            print(f"6. ERROR in lowercase: {e}")
            return
        
        # Step 5: Add extension
        try:
            final_name = result + ext
            print(f"7. Final result: '{final_name}'")
        except Exception as e:
            print(f"7. ERROR adding extension: {e}")
            return
        
        # Check if change is needed
        needs_change = (test_file != final_name)
        print(f"8. Needs change: {needs_change}")
        print(f"   Original: '{test_file}'")
        print(f"   Final:    '{final_name}'")
        
        if needs_change:
            target_path = os.path.join(current_folder, final_name)
            print(f"9. Target path: {target_path}")
            print(f"10. Target exists: {os.path.exists(target_path)}")
            
            if not os.path.exists(target_path):
                print("SUCCESS: File can be renamed")
                
                # Test actual rename operation (simulate only)
                print("\n=== SIMULATED RENAME TEST ===")
                print(f"Would rename:")
                print(f"  From: {full_path}")
                print(f"  To:   {target_path}")
                print("Simulation complete - no actual rename performed")
                
            else:
                print("CONFLICT: Target file already exists")
        else:
            print("NO ACTION: File doesn't need renaming")
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_image_6()