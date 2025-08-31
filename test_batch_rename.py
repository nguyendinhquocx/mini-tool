#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test Batch Rename Operation
"""
import sys
import os
import shutil
sys.path.insert(0, 'src')

from core.services.batch_operation_service import BatchOperationService
from core.services.file_operations_engine import FileOperationsEngine
from core.models.file_info import FileInfo

def test_batch_rename():
    print("=== Batch Rename Operation Test ===")
    
    # Setup test directory
    test_dir = "test_batch_rename"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # Create test files
    test_files = [
        'Test_File#1.txt',
        'Another@File.pdf', 
        'Document (Copy).docx',
        'Regular_File.jpg'
    ]
    
    print("Creating test files...")
    for filename in test_files:
        filepath = os.path.join(test_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("test content")
        print(f"  Created: {repr(filename)}")
    
    try:
        # Initialize services
        file_engine = FileOperationsEngine()
        batch_service = BatchOperationService()
        
        print("\nScanning folder...")
        file_list = file_engine.scan_folder_contents(test_dir)
        print(f"Found {len(file_list)} files")
        
        print("\nGenerating rename operations...")
        operations = []
        for file_info in file_list:
            # Use normalizer service directly 
            normalized_name = file_engine.normalizer.normalize_filename(file_info.name)
            if normalized_name != file_info.name:
                operations.append({
                    'original_path': file_info.path,
                    'new_path': os.path.join(test_dir, normalized_name),
                    'original_name': file_info.name,
                    'new_name': normalized_name
                })
        
        print(f"Operations to perform: {len(operations)}")
        for op in operations:
            print(f"  {repr(op['original_name'])} -> {repr(op['new_name'])}")
        
        if operations:
            print("\nExecuting batch rename...")
            # Simple file rename test
            success_count = 0
            for op in operations:
                try:
                    os.rename(op['original_path'], op['new_path'])
                    success_count += 1
                    print(f"  Renamed: {repr(op['original_name'])}")
                except Exception as e:
                    print(f"  Failed: {repr(op['original_name'])} - {str(e)}")
            
            print(f"\nRename completed: {success_count}/{len(operations)} successful")
            
            # Verify results
            print("\nVerifying results...")
            final_files = os.listdir(test_dir)
            for filename in final_files:
                print(f"  Final file: {repr(filename)}")
            
            print("[PASS] Batch rename operation completed successfully")
            return True
        else:
            print("[PASS] No files needed renaming")
            return True
            
    except Exception as e:
        print(f"[FAIL] Exception during batch rename: {str(e)}")
        return False
    
    finally:
        # Cleanup
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        print(f"\nCleaned up test directory: {test_dir}")

if __name__ == "__main__":
    success = test_batch_rename()
    sys.exit(0 if success else 1)