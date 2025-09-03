#!/usr/bin/env python3
"""
Verify filtering logic for rename operation
"""

# Sample preview data like what the app would have
preview_data = [
    {
        'filename': 'image copy 5.png',
        'selected': True,
        'changed': False,  # Same name after normalization
        'status': 'Không đổi'
    },
    {
        'filename': 'Image Copy.png',
        'selected': True, 
        'changed': True,  # Will become 'image copy.png'
        'status': 'Sẵn sàng'
    },
    {
        'filename': 'SPECIAL!@#FILE.txt',
        'selected': True,
        'changed': True,  # Will become 'special file.txt'
        'status': 'Sẵn sàng'
    },
    {
        'filename': 'conflict_file.txt',
        'selected': True,
        'changed': True,
        'status': 'Trùng tên!'  # This should be excluded
    }
]

def test_filtering_logic():
    print("=== TESTING RENAME FILTERING LOGIC ===")
    
    # This is the same logic from rename_files() method
    files_to_rename = [item for item in preview_data 
                      if item['selected'] and item['changed'] and item['status'] != "Trùng tên!"]
    
    print(f"Total files in preview: {len(preview_data)}")
    print(f"Files that will be renamed: {len(files_to_rename)}")
    
    print("\n=== FILES TO BE RENAMED ===")
    for item in files_to_rename:
        print(f"✓ {item['filename']} (Status: {item['status']})")
    
    print("\n=== FILES TO BE SKIPPED ===")
    skipped = [item for item in preview_data if item not in files_to_rename]
    for item in skipped:
        reasons = []
        if not item['selected']:
            reasons.append("not selected")
        if not item['changed']:
            reasons.append("no change needed")
        if item['status'] == "Trùng tên!":
            reasons.append("name conflict")
        
        reason = " + ".join(reasons)
        print(f"⏭ {item['filename']} (Reason: {reason})")
    
    print(f"\n=== SUMMARY ===")
    print(f"Files to rename: {len(files_to_rename)}")
    print(f"Files to skip: {len(skipped)}")
    
    # Verify image copy 5.png is correctly skipped
    image_copy_5 = next((item for item in preview_data if item['filename'] == 'image copy 5.png'), None)
    if image_copy_5:
        is_skipped = image_copy_5 not in files_to_rename
        print(f"\n✓ image copy 5.png correctly skipped: {is_skipped}")
    
if __name__ == "__main__":
    test_filtering_logic()