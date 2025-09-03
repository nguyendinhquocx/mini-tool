#!/usr/bin/env python3
"""
Debug file path issues for files in subfolders
"""

import os

def test_file_path_logic():
    """Test the exact logic used in the app"""
    
    # Simulate app data for file in subfolder
    current_folder = r"d:\pcloud\code\window\mini tool"
    
    # Test scenarios
    test_cases = [
        # Case 1: File in root folder
        {
            'filename': 'image copy 3.png',
            'current': 'image copy 3.png', 
            'relative_path': '',
            'description': 'File in root folder'
        },
        # Case 2: File in subfolder (how it might appear in app)
        {
            'filename': 'image copy 3.png',
            'current': 'subfolder\\image copy 3.png',  # Display path
            'relative_path': 'subfolder',
            'description': 'File in subfolder'
        },
        # Case 3: File with no relative_path but current shows path
        {
            'filename': 'image copy 3.png',
            'current': 'some\\path\\image copy 3.png',
            'relative_path': '',
            'description': 'Current contains path but no relative_path'
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n=== TEST CASE {i}: {case['description']} ===")
        
        # Extract data like the app does
        data_item = case
        actual_filename = data_item.get('filename', data_item['current'])
        
        print(f"Filename field: '{data_item.get('filename', 'N/A')}'")
        print(f"Current field: '{data_item.get('current', 'N/A')}'")
        print(f"Relative path field: '{data_item.get('relative_path', 'N/A')}'")
        print(f"Actual filename used: '{actual_filename}'")
        
        # Build paths like the app logic
        if data_item.get('relative_path'):
            file_path = os.path.join(current_folder, data_item['relative_path'], actual_filename)
            folder_path = os.path.join(current_folder, data_item['relative_path'])
        else:
            file_path = os.path.join(current_folder, actual_filename)
            folder_path = current_folder
        
        print(f"Computed file path: {file_path}")
        print(f"Computed folder path: {folder_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        # Alternative logic: Extract from current path
        current_path = data_item['current']
        if '\\' in current_path or '/' in current_path:
            # Current contains path info
            alt_file_path = os.path.join(current_folder, current_path)
            print(f"Alternative path (from current): {alt_file_path}")
            print(f"Alt path exists: {os.path.exists(alt_file_path)}")

if __name__ == "__main__":
    test_file_path_logic()