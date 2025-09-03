#!/usr/bin/env python3
"""
Test conflict detection cases
"""

import os
import tempfile
import shutil

def test_conflict_scenarios():
    """Test different conflict scenarios"""
    
    # Create temp directory for testing
    test_dir = tempfile.mkdtemp(prefix="conflict_test_")
    print(f"Test directory: {test_dir}")
    
    try:
        # Scenario 1: Case-only change (Windows specific)
        print("\n=== SCENARIO 1: Case-only change ===")
        original1 = os.path.join(test_dir, "Image Copy.png")
        target1 = os.path.join(test_dir, "image copy.png")
        
        with open(original1, 'w') as f:
            f.write("test content")
        
        print(f"Original: {original1}")
        print(f"Target: {target1}")
        print(f"Original exists: {os.path.exists(original1)}")
        print(f"Target exists: {os.path.exists(target1)}")
        print(f"Same path (case-insensitive): {os.path.abspath(original1).lower() == os.path.abspath(target1).lower()}")
        
        # Scenario 2: True conflict (different files)
        print("\n=== SCENARIO 2: True conflict ===")
        original2 = os.path.join(test_dir, "SPECIAL!FILE.txt") 
        target2 = os.path.join(test_dir, "special file.txt")
        existing2 = target2  # Create existing file with same target name
        
        with open(original2, 'w') as f:
            f.write("original content")
        with open(existing2, 'w') as f:
            f.write("existing content")
        
        print(f"Original: {original2}")
        print(f"Target: {target2}")
        print(f"Original exists: {os.path.exists(original2)}")
        print(f"Target exists: {os.path.exists(target2)}")
        print(f"Same path (case-insensitive): {os.path.abspath(original2).lower() == os.path.abspath(target2).lower()}")
        
        # Scenario 3: No conflict (new name)
        print("\n=== SCENARIO 3: No conflict ===")
        original3 = os.path.join(test_dir, "Unique File Name.doc")
        target3 = os.path.join(test_dir, "unique file name.doc")
        
        with open(original3, 'w') as f:
            f.write("unique content")
        
        print(f"Original: {original3}")
        print(f"Target: {target3}")
        print(f"Original exists: {os.path.exists(original3)}")
        print(f"Target exists: {os.path.exists(target3)}")
        print(f"Safe to rename: {not os.path.exists(target3)}")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"\nCleaned up: {test_dir}")

if __name__ == "__main__":
    test_conflict_scenarios()